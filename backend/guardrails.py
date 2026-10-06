import re

SECRET_PATTERNS = [
    r"\b(password|passwd|pin|otp|one[- ]?time password|api[\s_-]*key|access[\s_-]*token|refresh[\s_-]*token|client[\s_-]*secret|private[\s_-]*key)\b",
]
THAI_SECRET_TERMS = ("รหัสผ่าน", "รหัส otp", "รหัสotp", "โอทีพี", "พิน", "โทเคน", "คีย์ api", "คีย์api")
CROSS_CUSTOMER = [
    r"\b(other|another) customer\b",
    r"ลูกค้า(คน)?อื่น",
    r"ข้อมูลของลูกค้าคนอื่น",
]

def check_text(text: str) -> dict:
    low = text.lower()
    if any(term in low for term in THAI_SECRET_TERMS) or any(
        re.search(pattern, low, re.I) for pattern in SECRET_PATTERNS
    ):
        return {"allowed": False, "guard": "G06 Credentials & Secrets", "priority": 9, "response": "not information for this question"}
    for pattern in CROSS_CUSTOMER:
        if re.search(pattern, low, re.I):
            return {"allowed": False, "guard": "G02 Cross-Customer Data", "priority": 10, "response": "not information for this question"}
    return {"allowed": True, "guard": "PASS", "priority": None}
