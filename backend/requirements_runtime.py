from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQ = ROOT / "requirements"
FILES = {
    "instruction": REQ / "instruction.txt",
    "guardrails": REQ / "guardrails.md",
    "find": REQ / "find_skill.md",
    "fill": REQ / "fill_skill.md",
    "form_schema": REQ / "references" / "form-schema.md",
    "guard_requirements": REQ / "references" / "guard-requirements.md",
}

class RequirementRuntime:
    def __init__(self):
        self.contents = {name: path.read_text(encoding="utf-8") for name, path in FILES.items()}
    def loaded(self): return {name: str(FILES[name].relative_to(ROOT)) for name in FILES}
    def skill_source(self, action: str):
        if action == "FIND": return "requirements/find_skill.md"
        if action == "FILL": return "requirements/fill_skill.md"
        return None
