import os
from typing import Any, AsyncIterator

from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import AzureCliCredential, DefaultAzureCredential
from azure.ai.projects.models import (
    RealtimeServerEventConversationItemInputAudioTranscriptionCompleted,
    RealtimeServerEventConversationItemInputAudioTranscriptionDelta,
    RealtimeServerEventConversationItemInputAudioTranscriptionFailed,
    RealtimeServerEventInputAudioBufferSpeechStarted,
    RealtimeServerEventResponseAudioDelta,
    RealtimeServerEventResponseAudioTranscriptDelta,
    RealtimeServerEventResponseAudioTranscriptDone,
    RealtimeServerEventResponseCreated,
    RealtimeServerEventResponseDone,
    RealtimeServerEventResponseTextDelta,
    RealtimeServerEventResponseTextDone,
    RealtimeServerEventSessionCreated,
    RealtimeServerEventSessionUpdated,
    RealtimeServerEventError,
    VoiceAgentAudioConfig,
    VoiceAgentAudioInputConfig,
    VoiceAgentAzureSemanticVadTurnDetection,
    VoiceAgentInputTranscription,
    RealtimeAudioFormatsAudioPcm,
    VoiceAgentSessionUpdateConfig,
)

PROJECT_ENDPOINT = os.environ["FOUNDRY_PROJECT_ENDPOINT"].rstrip("/")
AGENT_NAME = os.environ.get("FOUNDRY_VOICE_AGENT_NAME") or os.environ.get("FOUNDRY_AGENT_NAME")
if not AGENT_NAME:
    raise RuntimeError("Set FOUNDRY_VOICE_AGENT_NAME in .env")
TENANT_ID = os.getenv("AZURE_TENANT_ID")
AUTH_MODE = os.getenv("AZURE_AUTH_MODE", "cli").lower()


def create_credential():
    if AUTH_MODE == "cli":
        return AzureCliCredential(tenant_id=TENANT_ID)
    return DefaultAzureCredential()


class FoundryVoiceSession:
    def __init__(self):
        self.credential = create_credential()
        self.client: AIProjectClient | None = None
        self._connection_ctx: Any = None
        self.connection: Any = None
        self.response_active = False
        self.input_bytes = 0
        self.output_bytes = 0

    async def open(self):
        self.client = AIProjectClient(
            endpoint=PROJECT_ENDPOINT,
            credential=self.credential,
            allow_preview=True,
        )
        await self.client.__aenter__()
        # Current Microsoft Foundry SDK handles the Voice Agent endpoint and auth.
        self._connection_ctx = self.client.beta.voice_agents.realtime.connect(agent_name=AGENT_NAME)
        self.connection = await self._connection_ctx.__aenter__()
        await self.connection.session.update(
            session=VoiceAgentSessionUpdateConfig(
                audio=VoiceAgentAudioConfig(
                    input=VoiceAgentAudioInputConfig(
                        format=RealtimeAudioFormatsAudioPcm(rate=24000),
                        turn_detection=VoiceAgentAzureSemanticVadTurnDetection(
                            create_response=False,
                        ),
                        transcription=VoiceAgentInputTranscription(
                            model="gpt-4o-mini-transcribe",
                        )
                    )
                )
            )
        )
        return self

    async def append_pcm16(self, pcm: bytes):
        if not self.connection:
            raise RuntimeError("Foundry voice session is not connected")
        self.input_bytes += len(pcm)
        # SDK 2.7+ accepts raw PCM bytes and encodes transport payload itself.
        await self.connection.input_audio_buffer.append(audio=pcm)

    async def commit_audio(self):
        if not self.connection:
            raise RuntimeError("Foundry voice session is not connected")
        await self.connection.input_audio_buffer.commit()

    async def respond_to_text(self, text: str) -> dict:
        if not self.connection:
            raise RuntimeError("Foundry voice session is not connected")
        await self.connection.conversation.item.create(
            item={
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": text}],
            }
        )
        await self.connection.response.create(
            response={"output_modalities": ["audio", "text"]}
        )
        text_parts: list[str] = []
        audio_transcript_parts: list[str] = []
        audio_parts: list[bytes] = []
        async for event in self.events():
            if event["type"] == "agent_text_delta":
                text_parts.append(event["text"])
            elif event["type"] == "agent_audio_transcript_delta":
                audio_transcript_parts.append(event["text"])
            elif event["type"] == "agent_transcript":
                if event["text"]:
                    audio_transcript_parts = [event["text"]]
            elif event["type"] == "agent_text":
                if event["text"]:
                    text_parts = [event["text"]]
            elif event["type"] == "audio":
                audio_parts.append(event["audio"])
            elif event["type"] == "response_done":
                if event["status"] not in (None, "completed"):
                    raise RuntimeError(f"Foundry response ended with status: {event['status']}")
                return {
                    "text": "".join(text_parts or audio_transcript_parts).strip(),
                    "audio": b"".join(audio_parts),
                }
            elif event["type"] == "error":
                raise RuntimeError(event["message"])
        raise RuntimeError("Foundry connection closed before completing the response")

    async def cancel_response(self):
        if self.connection and self.response_active:
            try:
                await self.connection.response.cancel()
            except Exception:
                pass

    async def events(self) -> AsyncIterator[dict]:
        async for event in self.connection:
            if isinstance(event, RealtimeServerEventSessionCreated):
                yield {"type": "conversation_created", "conversation_id": event.conversation_id}
            elif isinstance(event, RealtimeServerEventSessionUpdated):
                yield {"type": "session_configured"}
            elif isinstance(event, RealtimeServerEventInputAudioBufferSpeechStarted):
                yield {"type": "speech_started"}
            elif getattr(event, "type", None) == "input_audio_buffer.speech_stopped":
                yield {"type": "speech_stopped"}
            elif getattr(event, "type", None) == "input_audio_buffer.committed":
                yield {"type": "audio_committed"}
            elif isinstance(event, RealtimeServerEventConversationItemInputAudioTranscriptionDelta):
                yield {
                    "type": "input_transcript_delta",
                    "item_id": event.item_id,
                    "delta": event.delta or "",
                }
            elif isinstance(event, RealtimeServerEventConversationItemInputAudioTranscriptionCompleted):
                yield {
                    "type": "input_transcript",
                    "item_id": event.item_id,
                    "text": (event.transcript or "").strip(),
                }
            elif isinstance(event, RealtimeServerEventConversationItemInputAudioTranscriptionFailed):
                yield {
                    "type": "transcription_error",
                    "message": event.error.message,
                    "code": event.error.code,
                }
            elif isinstance(event, RealtimeServerEventResponseCreated):
                self.response_active = True
                yield {"type": "response_created"}
            elif isinstance(event, RealtimeServerEventResponseAudioDelta):
                self.output_bytes += len(event.delta)
                yield {"type": "audio", "audio": event.delta}
            elif isinstance(event, RealtimeServerEventResponseAudioTranscriptDelta):
                yield {"type": "agent_audio_transcript_delta", "text": event.delta or ""}
            elif isinstance(event, RealtimeServerEventResponseAudioTranscriptDone):
                yield {"type": "agent_transcript", "text": event.transcript or ""}
            elif isinstance(event, RealtimeServerEventResponseTextDelta):
                yield {"type": "agent_text_delta", "text": event.delta or ""}
            elif isinstance(event, RealtimeServerEventResponseTextDone):
                yield {"type": "agent_text", "text": event.text or ""}
            elif isinstance(event, RealtimeServerEventResponseDone):
                self.response_active = False
                yield {"type": "response_done", "status": getattr(event.response, "status", None)}
            elif isinstance(event, RealtimeServerEventError):
                yield {"type": "error", "message": event.error.message, "code": getattr(event.error, "code", None)}
            else:
                event_type = event.get("type") if isinstance(event, dict) else getattr(event, "type", None)
                if event_type:
                    yield {"type": "foundry_event", "event": str(event_type)}

    async def close(self):
        if self._connection_ctx is not None:
            try:
                await self._connection_ctx.__aexit__(None, None, None)
            except Exception:
                pass
        if self.client is not None:
            try:
                await self.client.__aexit__(None, None, None)
            except Exception:
                pass
        try:
            await self.credential.close()
        except Exception:
            pass
