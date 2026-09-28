"""Refresh three official local reference snapshots; normal API reads remain offline."""
import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.database import Base, make_engine, session_factory
from backend.app.models import FoodCompositionReference, HealthTopicReference, utc_now
from scripts.more_reference_import import parse_food_composition, parse_medline_topics
from sqlalchemy import delete

SOURCES = (
    ("sr-legacy-2018.zip", "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip", 15_000_000),
    ("foundation-2026-04.zip", "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_csv_2026-04-30.zip", 10_000_000),
    ("medlineplus-2026-09-25.zip", "https://medlineplus.gov/xml/mplus_topics_compressed_2026-09-25.zip", 10_000_000),
)


def cached_source(name, url, maximum):
    cache = ROOT / ".run" / name
    if cache.exists():
        return cache.read_bytes()
    cache.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(Request(url, headers={"User-Agent": "HealthCompanionLocalReferenceSync/0.2"}), timeout=60) as response:
        blob = response.read(maximum + 1)
    if len(blob) > maximum or not blob.startswith(b"PK"):
        raise ValueError(f"Unexpected source archive: {name}")
    cache.write_bytes(blob)
    return blob


def main():
    blobs = {name: cached_source(name, url, maximum) for name, url, maximum in SOURCES}
    legacy = parse_food_composition(blobs["sr-legacy-2018.zip"], "sr_legacy_food", "2018-04")
    foundation = parse_food_composition(blobs["foundation-2026-04.zip"], "foundation_food", "2026-04")
    topics = parse_medline_topics(blobs["medlineplus-2026-09-25.zip"], "2026-09-25")
    if len(legacy) < 7000 or len(foundation) < 400 or len(topics) < 900:
        raise ValueError(f"Unexpected source counts: {len(legacy)}, {len(foundation)}, {len(topics)}")
    engine = make_engine()
    Base.metadata.create_all(engine)
    now = utc_now()
    with session_factory(engine).begin() as db:
        db.execute(delete(FoodCompositionReference))
        db.execute(delete(HealthTopicReference))
        db.bulk_insert_mappings(FoodCompositionReference, [{**row, "synced_at": now} for row in legacy + foundation])
        db.bulk_insert_mappings(HealthTopicReference, [{**row, "synced_at": now} for row in topics])
    engine.dispose()
    print(f"FoodData Central SR Legacy: {len(legacy)}; Foundation Foods: {len(foundation)}; MedlinePlus: {len(topics)}")


if __name__ == "__main__":
    main()
