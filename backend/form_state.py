import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = json.loads((ROOT / "data" / "form.json").read_text(encoding="utf-8"))

class FormState:
    required = ["first_name", "last_name", "date_of_birth", "monthly_salary", "email"]
    def __init__(self): self.values = dict(DEFAULTS)
    def reset(self): self.values = dict(DEFAULTS)
    def update(self, changes: dict):
        applied = {}
        for key, value in changes.items():
            if key in self.values and value not in (None, ""):
                self.values[key] = value
                applied[key] = value
        return applied
    def status(self):
        complete = [k for k in self.required if self.values.get(k)]
        incomplete = [k for k in self.required if not self.values.get(k)]
        return {"complete": complete, "incomplete": incomplete, "form_complete": not incomplete}
