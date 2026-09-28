import json
from pathlib import Path

RULES_DIR = Path(__file__).resolve().parents[1] / "data" / "rules"


def load_rules(name):
    return json.loads((RULES_DIR / name).read_text(encoding="utf-8-sig"))
