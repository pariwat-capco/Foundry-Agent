import re

SECRET_PATTERNS = [
    r"\b(password|passwd|pin|otp|one[- ]?time password|api key|access token|refresh token|client secret|private key)\b",
    r"\b(รหัสผ่าน|รหัส otp|โอทีพี|พิน|โทเคน|คีย์ api)\b",
]
CROSS_CUSTOMER = [
    r"\b(other|another) customer\b",
    r"ลูกค้า(คน)?อื่น",
    r"ข้อมูลของลูกค้าคนอื่น",
]

def check_text(text: str) -> dict:
    low = text.lower()
    for pattern in SECRET_PATTERNS:
        if re.search(pattern, low, re.I):
            return {"allowed": False, "guard": "G06 Credentials & Secrets", "priority": 9, "response": "not information for this question"}
    for pattern in CROSS_CUSTOMER:
        if re.search(pattern, low, re.I):
            return {"allowed": False, "guard": "G02 Cross-Customer Data", "priority": 10, "response": "not information for this question"}
    return {"allowed": True, "guard": "PASS", "priority": None}
