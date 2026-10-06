import re

class ModeController:
    def __init__(self):
        self.mode = "LISTEN"

    @staticmethod
    def _normalized(text: str) -> str:
        value = text.lower().strip()
        value = re.sub(r"\s+", " ", value)
        # Voice transcription commonly emits the English name with a space.
        value = value.replace("pru agent", "pru-agent")
        return value

    def apply(self, text: str) -> str:
        value = self._normalized(text)
        if any(command in value for command in ("กลับโหมดฟัง", "กลับไปโหมดฟัง", "กลับสู่โหมดฟัง", "ok thanks pru-agent")):
            self.mode = "LISTEN"
        elif any(command in value for command in ("เข้าโหมดตอบ", "เข้าสู่โหมดตอบ", "pru-agent")):
            self.mode = "ANSWER"
        return self.mode
