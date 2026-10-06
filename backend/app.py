import asyncio
import base64
import json
import math
import struct
from pathlib import Path

from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, field_validator
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .mode_controller import ModeController
from .form_state import FormState
from .guardrails import check_text
from .requirements_runtime import RequirementRuntime
from .skills_runtime import route
from .foundry_voice import FoundryVoiceSession, PROJECT_ENDPOINT, AGENT_NAME

FRONTEND = ROOT / "frontend"
app = FastAPI(title="PRU-Agent Voice PoC V3")
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")

mode = ModeController()
form = FormState()
requirements_runtime = RequirementRuntime()
conversation_context: list[dict] = []


class TranscriptRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    role: str = Field(pattern="^(sales|customer)$")

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Transcript must not be empty")
        return value


def process_transcript(text: str, role: str) -> dict:
    text = text.strip()
    if not text:
        raise ValueError("Transcript must not be empty")
    guard = check_text(text)
    current_mode = mode.apply(text)
    prior = conversation_context[-8:]
    skill = {"action":"BLOCK", "skill_source":"requirements/guardrails.md"} if not guard["allowed"] else route(text, prior, form)
    conversation_context.append({"role":role, "text":text})
    if len(conversation_context) > 30:
        del conversation_context[:-30]
    return {
        "type":"input_transcript",
        "text":text,
        "role":role,
        "mode":current_mode,
        "guard":guard,
        "skill":skill,
        "form":form.values,
        "status":form.status(),
    }


@app.get("/")
async def index(): return FileResponse(FRONTEND / "index.html")

@app.get("/api/state")
async def state():
    return {
        "mode": mode.mode, "form": form.values, "status": form.status(),
        "foundry": True, "project": PROJECT_ENDPOINT, "agent": AGENT_NAME,
        "requirements_loaded": requirements_runtime.loaded(),
    }

@app.get("/api/health/foundry")
async def health():
    session = FoundryVoiceSession()
    try:
        await session.open()
        return {"ok": True, "project": PROJECT_ENDPOINT, "agent": AGENT_NAME, "auth": "AzureCliCredential"}
    except Exception as exc:
        return JSONResponse(status_code=503, content={"ok": False, "error": type(exc).__name__, "message": str(exc)[:1800]})
    finally:
        await session.close()

@app.post("/api/reset")
async def reset():
    mode.mode = "LISTEN"; form.reset(); conversation_context.clear()
    return await state()


@app.post("/api/transcript")
async def transcript(request: TranscriptRequest):
    return process_transcript(request.text, request.role)


@app.post("/api/answer")
async def answer(request: TranscriptRequest):
    if mode.mode != "ANSWER":
        raise HTTPException(status_code=409, detail="Switch to ANSWER mode before requesting a Foundry response")

    history = conversation_context[-13:-1]
    context = "\n".join(
        f"{'PRU-Agent' if item['role'] == 'assistant' else item['role'].title()}: {item['text']}"
        for item in history
    )
    prompt = (
        "Respond to the latest user message. Use the conversation history when relevant. "
        "Respond in Thai if the latest message is Thai; otherwise respond in English.\n\n"
        f"Conversation history:\n{context}\n\n"
        f"Latest user message:\n{request.text}"
    )
    session = FoundryVoiceSession()
    try:
        await session.open()
        result = await session.respond_to_text(prompt)
        if not result["text"] and not result["audio"]:
            raise RuntimeError("Foundry completed the response without text or audio")
        if result["text"]:
            conversation_context.append({"role":"assistant", "text":result["text"]})
            if len(conversation_context) > 30:
                del conversation_context[:-30]
        return {
            "text":result["text"],
            "audio":base64.b64encode(result["audio"]).decode("ascii") if result["audio"] else None,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Foundry response failed: {type(exc).__name__}: {str(exc)[:1000]}",
        ) from exc
    finally:
        await session.close()


@app.websocket("/ws/voice")
async def voice(ws: WebSocket):
    await ws.accept()
    session = FoundryVoiceSession()
    event_task = None
    role = "sales"
    diag = {"browser_chunks":0, "backend_bytes":0, "backend_rms":0.0, "audio_buffer_bytes":0, "foundry_speech_started":0, "foundry_audio_committed":0, "manual_commits":0, "transcripts":0}
    try:
        await session.open()
        await ws.send_json({"type":"connected", "mode":mode.mode, "agent":AGENT_NAME, "requirements_loaded":requirements_runtime.loaded()})

        async def relay_foundry():
            nonlocal diag
            async for event in session.events():
                et = event["type"]
                if et == "speech_started":
                    diag["foundry_speech_started"] += 1
                    await ws.send_json({**event, "diagnostics":diag})
                    continue
                if et == "speech_stopped":
                    await ws.send_json(event)
                    continue
                if et == "audio_committed":
                    diag["foundry_audio_committed"] += 1
                    diag["audio_buffer_bytes"] = 0
                    await ws.send_json({**event, "diagnostics":diag})
                    continue
                if et == "input_transcript_delta":
                    await ws.send_json({**event, "role":role})
                    continue
                if et == "transcription_error":
                    await ws.send_json({"type":"error", "message":event["message"], "code":event["code"]})
                    continue
                if et == "error":
                    await ws.send_json({"type":"error", "message":event["message"], "code":event.get("code")})
                    continue
                if et == "input_transcript":
                    diag["transcripts"] += 1
                    processed = process_transcript(event["text"], role)
                    await ws.send_json({**processed, "item_id":event.get("item_id"), "diagnostics":diag})
                    # LISTEN: local runtime owns visible Find/Fill behavior; cancel Foundry voice reply.
                    if processed["mode"] == "LISTEN":
                        await session.cancel_response()
                    continue
                if et == "response_created":
                    # Foundry may start generation before transcription completes. In LISTEN mode
                    # cancel it to keep the agent silent while local Find/Fill runtime works.
                    if mode.mode == "LISTEN": await session.cancel_response()
                    await ws.send_json({"type":"response_created", "mode":mode.mode})
                    continue
                if et == "audio":
                    if mode.mode == "ANSWER":
                        await ws.send_json({"type":"audio", "audio":base64.b64encode(event["audio"]).decode("ascii"), "play":True})
                    continue
                if et == "agent_transcript":
                    if mode.mode == "ANSWER":
                        await ws.send_json({**event, "visible":True, "mode":mode.mode})
                    continue
                await ws.send_json(event)

        event_task = asyncio.create_task(relay_foundry())
        while True:
            message = await ws.receive()
            if message.get("bytes") is not None:
                pcm = message["bytes"]
                diag["browser_chunks"] += 1; diag["backend_bytes"] += len(pcm)
                sample_count = len(pcm) // 2
                if sample_count:
                    squared_sum = sum(sample * sample for (sample,) in struct.iter_unpack("<h", pcm[:sample_count * 2]))
                    diag["backend_rms"] = round(math.sqrt(squared_sum / sample_count) / 32768, 4)
                await session.append_pcm16(pcm)
                diag["audio_buffer_bytes"] += len(pcm)
                if diag["browser_chunks"] % 20 == 0:
                    await ws.send_json({"type":"diagnostics", "diagnostics":diag})
            elif message.get("text"):
                payload = json.loads(message["text"])
                if payload.get("type") == "role": role = payload.get("role", "sales")
                elif payload.get("type") == "ping": await ws.send_json({"type":"pong"})
                elif payload.get("type") == "commit_audio":
                    if diag["foundry_audio_committed"] == payload.get("commits_at_speech", -1):
                        if diag["audio_buffer_bytes"] < 24000:
                            await ws.send_json({
                                "type":"manual_commit_skipped",
                                "reason":"not_enough_audio",
                                "buffer_bytes":diag["audio_buffer_bytes"],
                                "diagnostics":diag,
                            })
                        else:
                            await session.commit_audio()
                            diag["manual_commits"] += 1
                            diag["audio_buffer_bytes"] = 0
                            await ws.send_json({"type":"manual_commit_sent", "diagnostics":diag})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try: await ws.send_json({"type":"error", "message":f"{type(exc).__name__}: {str(exc)[:1800]}"})
        except Exception: pass
    finally:
        if event_task: event_task.cancel()
        await session.close()
