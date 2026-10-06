# PRU-Agent Voice PoC V3

V3 fixes the V2 voice bridge and wires the approved requirement files into the local runtime.

## What changed

- Uses current Microsoft Foundry SDK: `azure-ai-projects[voice]>=2.7.0`.
- Connects through `AIProjectClient.beta.voice_agents.realtime.connect()`; no manual Voice Live URL patch.
- Local development uses `AzureCliCredential` by default because this workstation has already verified Azure CLI token access.
- Chrome/Edge SpeechRecognition converts Thai or English speech into text; interim text appears while speaking.
- Final transcript text is posted to the backend `/api/transcript` endpoint and passes through the existing guardrails and Find/Fill skills.
- In Thai, say `เข้าโหมดตอบ` to send recognized text and recent conversation context to Foundry for a text-and-voice response; say `กลับโหมดฟัง` to return to local Find/Fill handling.
- Microphone transcription does not depend on Foundry realtime VAD or audio-buffer commits. Foundry is opened only to generate an ANSWER-mode response.
- Browser speech recognition may send audio to the browser's configured speech service; only recognized text is sent to the app backend.
- Loads `instruction.txt`, `guardrails.md`, `find_skill.md`, `fill_skill.md` at runtime.
- Each transcript passes guardrails, then the runtime routes to Find or Fill.
- Debug panel shows the actual skill file selected.
- LISTEN: Find can return text and Fill updates the form locally without opening Foundry.
- ANSWER: recognized text and recent conversation are sent to the configured Foundry voice agent; its response is shown and its audio is played in the browser.
- Thai mode commands are `เข้าโหมดตอบ` and `กลับโหมดฟัง`; English `pru agent` remains supported.

## Important PoC boundary

The local Find tool uses `data/products.json` as mock approved knowledge and Fill uses an in-memory form. Replace these with real APIs later. The `.md` files are loaded and used as runtime policy/traceability sources; they are not automatically installed into the existing Foundry agent definition.

## 1. Requirements

- Windows 10/11
- Python 3.10+
- Chrome or Edge
- Azure CLI logged into the tenant that owns the Foundry project

Check Azure CLI:

```bat
az.cmd account show
```

If using the portable Azure CLI and `az.cmd` is not on PATH:

```bat
set PATH=C:\Users\PPAW\Downloads\azure-cli-2.90.0-x64\bin;%PATH%
```

## 2. Create virtual environment

From the extracted `pru-agent-web-v3` folder:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The current Microsoft Voice Agent SDK is provided by `azure-ai-projects[voice]>=2.7.0`; V3 does not use the old `azure-ai-voiceagents` package.

## 3. Create .env

```bat
copy .env.example .env
```

Expected values for this PoC:

```env
PORT=3000
USE_FOUNDRY=true
AZURE_TENANT_ID=73a4e5b8-f15b-475a-be16-9187515b1cc1
FOUNDRY_PROJECT_ENDPOINT=https://capco-ai-studio.services.ai.azure.com/api/projects/hk-foundry
FOUNDRY_VOICE_AGENT_NAME=pruth-sale-agent-n6wz68ph4
AUDIO_SAMPLE_RATE=24000
AZURE_AUTH_MODE=cli
```

Do not put access tokens, passwords, or Azure user credentials in `.env`.

## 4. Verify Python can use Azure CLI

```bat
python -c "from azure.identity import AzureCliCredential; c=AzureCliCredential(tenant_id='73a4e5b8-f15b-475a-be16-9187515b1cc1'); print(c.get_token('https://management.azure.com/.default').expires_on)"
```

A numeric expiry value means the Python -> Azure CLI credential path works.

## 5. Run

Recommended:

```bat
python run.py
```

Or directly:

```bat
uvicorn backend.app:app --host 127.0.0.1 --port 3000 --reload
```

Open:

```text
http://127.0.0.1:3000
```

Use a current Chrome or Edge browser and allow microphone permission. Select Thai or English beside the microphone button. Browser speech recognition requires its speech service to be available.

## 6. Test order

1. Optionally click **Test Foundry** to verify Foundry connectivity. It is not required for microphone transcription or Find/Fill.
2. Select `Sales` or `Customer`.
3. Click **Start microphone**.
4. Speak Thai, for example: `ชื่อ ปริวัฒน์ ไพวงษ์`.
5. Check Live Conversation for interim text while speaking and the final transcript after a pause.
6. In LISTEN mode, ask `วงเงินกู้สูงสุดเท่าไหร่` to test `find_skill.md` text output.
7. Say `รายได้ต่อเดือน 80000 บาท` to test `fill_skill.md` and the form UI.
8. Say `เข้าโหมดตอบ`, then ask a question or say `สรุปบทสนทนานี้`; Foundry should show and speak its answer.
9. Say `กลับโหมดฟัง` to return to local LISTEN-mode skills.

For English, the mode parser also accepts `pru agent` as an audio-normalized form of `pru-agent`.

## Diagnostics

- No interim text: verify microphone permission and the selected speech language; browser speech recognition must be supported and its speech service available.
- Final text appears but no skill result: check the transcript request error shown in Voice status and the uvicorn terminal.
- The **Test Foundry** button tests Foundry connectivity separately; normal microphone transcription and skill routing do not require it.

## Requirement files used by runtime

- `requirements/instruction.txt`
- `requirements/guardrails.md`
- `requirements/find_skill.md`
- `requirements/fill_skill.md`
- `requirements/references/form-schema.md`
- `requirements/references/guard-requirements.md`

The Debug panel exposes which Find/Fill file was selected for each turn.
