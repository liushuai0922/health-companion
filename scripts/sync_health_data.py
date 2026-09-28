"""Sync curated NHC links and an official USDA/ODS purine workbook to local SQLite."""
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from purine_import import SOURCE_URL, parse_purines

PROJECT = ROOT.parent
sys.path.insert(0, str(PROJECT))
from backend.app.database import Base, make_engine, session_factory
from backend.app.models import GuidelineReference, PurineReference, utc_now

def main():
    archive = PROJECT / ".run" / "purine-2025.xlsx"
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        request = Request(SOURCE_URL, headers={"User-Agent": "HealthCompanionLocalSync/0.1"})
        with urlopen(request, timeout=45) as response:
            content = response.read(2_000_001)
        if len(content) > 2_000_000 or not content.startswith(b"PK"):
            raise ValueError("Unexpected purine workbook")
        archive.write_bytes(content)
    guidelines = json.loads((PROJECT / "data" / "guideline_references.json").read_text(encoding="utf-8"))
    purines = parse_purines(archive.read_bytes())
    if len(purines) < 400:
        raise ValueError(f"Too few purine records: {len(purines)}")
    engine = make_engine()
    Base.metadata.create_all(engine)
    sessions = session_factory(engine)
    with sessions.begin() as db:
        for item in guidelines:
            db.merge(GuidelineReference(**item, synced_at=utc_now()))
        for item in purines:
            db.merge(PurineReference(**item, synced_at=utc_now()))
    engine.dispose()
    print(f"本地同步完成：官方指南 {len(guidelines)} 条，嘌呤样本 {len(purines)} 条。")

if __name__ == "__main__":
    main()
