import json, re
from pathlib import Path
from .form_state import FormState

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS = json.loads((ROOT / "data" / "products.json").read_text(encoding="utf-8"))

THAI_RE = re.compile(r"[\u0E00-\u0E7F]")

def language(text: str) -> str: return "th" if THAI_RE.search(text) else "en"

def looks_question(text: str) -> bool:
    low = text.lower().strip()
    return "?" in text or any(x in low for x in ["เท่าไหร่", "อะไร", "อย่างไร", "ไหม", "หรือไม่", "how ", "what ", "when ", "can i", "is there", "interest", "maximum loan"])

def find_skill(text: str) -> dict:
    low = text.lower()
    for key, item in PRODUCTS.items():
        if any(k.lower() in low for k in item["keywords"]):
            lang = language(text)
            return {"action":"FIND", "found":True, "answer":item[lang], "key":key, "skill_source":"requirements/find_skill.md"}
    return {"action":"FIND", "found":False, "answer":None, "skill_source":"requirements/find_skill.md"}

def _salary(text: str):
    low = text.lower().replace(",", "")
    if not any(k in low for k in ["เงินเดือน", "รายได้", "salary", "income", "บาท", "thb"]): return None
    m = re.search(r"(?<!\d)(\d{4,9})(?!\d)", low)
    return m.group(1) if m else None

def _email(text: str):
    m = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I)
    return m.group(0) if m else None

def _dob(text: str):
    if not any(k in text.lower() for k in ["เกิด", "วันเกิด", "dob", "date of birth", "born"]): return None
    m = re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b", text)
    return m.group(1) if m else None

def _name(text: str, context: list[dict]):
    low = text.lower().strip()
    explicit = re.search(r"(?:ชื่อ|name is|my name is)\s*[:：]?\s*([^\n,.]+)", text, re.I)
    candidate = explicit.group(1).strip() if explicit else None
    if not candidate and context:
        prev = context[-1].get("text", "").lower()
        if any(k in prev for k in ["ชื่อ", "name", "first name", "last name"]): candidate = text.strip()
    if not candidate or len(candidate) > 80 or any(ch.isdigit() for ch in candidate): return {}
    parts = candidate.split()
    if len(parts) >= 2: return {"first_name": parts[0], "last_name": " ".join(parts[1:])}
    return {"first_name": candidate}

def fill_skill(text: str, context: list[dict], form: FormState) -> dict:
    changes = {}
    email = _email(text)
    if email: changes["email"] = email
    dob = _dob(text)
    if dob: changes["date_of_birth"] = dob
    salary = _salary(text)
    if salary: changes["monthly_salary"] = salary
    changes.update(_name(text, context))
    # Short numeric answer after a salary question.
    if not changes and context:
        prev = context[-1].get("text", "").lower()
        if any(k in prev for k in ["เงินเดือน", "รายได้", "salary", "income"]):
            m = re.search(r"\b([\d,]{4,12})\b", text)
            if m: changes["monthly_salary"] = m.group(1).replace(",", "")
    if not changes:
        return {"action":"NONE", "updated_fields":{}, "status":form.status(), "skill_source":None}
    applied = form.update(changes)
    return {"action":"FILL", "updated_fields":applied, "status":form.status(), "write_status":"success" if applied else "no_write", "skill_source":"requirements/fill_skill.md"}

def route(text: str, context: list[dict], form: FormState) -> dict:
    # Form/status questions are handled by Fill state lookup.
    low = text.lower()
    if any(k in low for k in ["ข้อมูลอะไรยังไม่ครบ", "อะไรยังไม่ครบ", "fields are missing", "what is missing", "form status"]):
        return {"action":"FILL", "updated_fields":{}, "status":form.status(), "write_status":"no_write", "skill_source":"requirements/fill_skill.md"}
    filled = fill_skill(text, context, form)
    if filled["action"] == "FILL": return filled
    if looks_question(text): return find_skill(text)
    return filled
