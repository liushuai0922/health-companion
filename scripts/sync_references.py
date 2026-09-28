r"""Refresh a small, sourced local reference index from three official public sources.

Windows PowerShell: .\.venv\Scripts\python.exe scripts\sync_references.py
Normal API reads never use the network. The USDA archive is cached locally.
"""
import json
import csv
import io
import zipfile
from pathlib import Path
import sys
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.database import Base, make_engine, session_factory
from backend.app.models import DrugReference, FoodReference, utc_now

ROOT = Path(__file__).resolve().parents[1]
RX_BASE = "https://rxnav.nlm.nih.gov/REST"
DM_BASE = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
FDC_BASE = "https://api.nal.usda.gov/fdc/v1"
FDC_ARCHIVE_URL = "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip"


def fetch_json(url):
    allowed = (RX_BASE, DM_BASE, FDC_BASE)
    if not any(url.startswith(prefix + "/") for prefix in allowed):
        raise ValueError("Unexpected reference source")
    request = Request(url, headers={"User-Agent": "HealthCompanionLocalReferenceSync/0.1", "Accept": "application/json"})
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def common_drug_record(seed, fetch=fetch_json):
    key = seed["key"]
    lookup = fetch(f"{RX_BASE}/rxcui.json?" + urlencode({"name": key, "search": "2"}))
    ids = lookup.get("idGroup", {}).get("rxnormId", [])
    if len(ids) != 1 or not str(ids[0]).isdigit():
        raise ValueError(f"RxNorm did not return one unambiguous RxCUI for {key}")
    rxcui = str(ids[0])
    props = fetch(f"{RX_BASE}/rxcui/{rxcui}/properties.json").get("properties", {})
    if props.get("name", "").strip().casefold() != key.casefold():
        raise ValueError(f"RxNorm name did not match {key}: {props.get('name')}")
    label_id = label_title = None
    try:
        labels = fetch(f"{DM_BASE}/spls.json?" + urlencode({"drug_name": key, "name_type": "generic", "pagesize": 20})).get("data", [])
        for label in labels:
            title = label.get("title", "")
            product_title = title.split("[", 1)[0].strip()
            if (product_title.casefold().startswith(key.casefold()) and len(product_title) > len(key)
                    and not product_title[len(key)].isalpha() and " AND " not in product_title.upper()):
                label_id = label.get("setid")
                label_title = title
                break
    except (OSError, ValueError, KeyError):
        pass  # RxNorm entry is still useful; missing label remains explicit.
    return {"key": key, "name_zh": seed["zh"], "name_en": props["name"], "group_name": seed["group"], "aliases": seed["aliases"], "rxcui": rxcui,
            "dailymed_setid": label_id, "dailymed_title": label_title, "synced_at": utc_now()}


def common_food_record(seed, api_key, fetch=fetch_json):
    data = fetch(f"{FDC_BASE}/foods/search?" + urlencode({"query": seed["query"], "dataType": "SR Legacy", "pageSize": 10, "api_key": api_key}))
    target = seed["exact"].casefold()
    food = next((item for item in data.get("foods", []) if item.get("description", "").casefold() == target and item.get("dataType") == "SR Legacy"), None)
    if food is None:
        raise ValueError(f"No exact USDA reference found for {seed['key']}")
    return {"key": seed["key"], "fdc_id": int(food["fdcId"]), "description_en": food["description"], "data_type": food["dataType"], "synced_at": utc_now()}


def archive_food_records(archive_bytes, seeds):
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        member = next(name for name in archive.namelist() if name.endswith("/food.csv"))
        with archive.open(member) as stream:
            rows = csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig", newline=""))
            index = {row["description"].casefold(): row for row in rows if row["data_type"] == "sr_legacy_food"}
    found = {}
    for seed in seeds:
        food = index.get(seed["exact"].casefold())
        if food:
            found[seed["key"]] = {"key": seed["key"], "fdc_id": int(food["fdc_id"]), "description_en": food["description"], "data_type": "SR Legacy", "synced_at": utc_now()}
    return found


def food_archive():
    cache = ROOT / ".run" / "sr-legacy-2018.zip"
    if cache.exists():
        return cache.read_bytes()
    cache.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(Request(FDC_ARCHIVE_URL, headers={"User-Agent": "HealthCompanionLocalReferenceSync/0.1"}), timeout=45) as response:
        content = response.read()
    if len(content) > 15_000_000:
        raise ValueError("Unexpectedly large USDA archive")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        if not any(name.endswith("/food.csv") for name in archive.namelist()):
            raise ValueError("USDA archive has no food.csv")
    staging = cache.with_suffix(".download")
    staging.write_bytes(content)
    staging.replace(cache)
    return content


def synchronize(sessions, fetch=fetch_json, pause=0, archive_bytes=None):
    drugs = json.loads((ROOT / "data" / "drugs" / "reference_seeds.json").read_text(encoding="utf-8-sig"))["drugs"]
    foods = json.loads((ROOT / "data" / "foods" / "reference_seeds.json").read_text(encoding="utf-8-sig"))["foods"]
    outcome = {"rxnorm_saved": 0, "dailymed_links": 0, "usda_saved": 0, "skipped": [], "note": "Snapshot saved locally. A missing DailyMed label is shown as unavailable; no interaction rules are generated."}
    for seed in drugs:
        try:
            values = common_drug_record(seed, fetch)
            with sessions.begin() as db:
                row = db.get(DrugReference, values["key"])
                if row is None:
                    db.add(DrugReference(**values))
                else:
                    for field, value in values.items():
                        setattr(row, field, value)
            outcome["rxnorm_saved"] += 1
            outcome["dailymed_links"] += bool(values["dailymed_setid"])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            outcome["skipped"].append({"source": "RxNorm", "key": seed["key"], "reason": str(exc)[:160]})
        if pause:
            time.sleep(pause)
    try:
        matched_foods = archive_food_records(archive_bytes if archive_bytes is not None else food_archive(), foods)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        matched_foods = {}
        outcome["skipped"].append({"source": "USDA archive", "key": "archive", "reason": str(exc)[:160]})
    for seed in foods:
        try:
            values = matched_foods.get(seed["key"])
            if values is None:
                raise ValueError("No exact food name in official SR Legacy archive")
            with sessions.begin() as db:
                row = db.get(FoodReference, values["key"])
                if row is None:
                    db.add(FoodReference(**values))
                else:
                    for field, value in values.items():
                        setattr(row, field, value)
            outcome["usda_saved"] += 1
        except (OSError, ValueError, KeyError, TypeError) as exc:
            outcome["skipped"].append({"source": "USDA", "key": seed["key"], "reason": str(exc)[:160]})
        if pause:
            time.sleep(pause)
    return outcome


if __name__ == "__main__":
    engine = make_engine()
    Base.metadata.create_all(engine)
    result = synchronize(session_factory(engine), pause=0.08)
    engine.dispose()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["rxnorm_saved"] == 0 and result["usda_saved"] == 0:
        raise SystemExit("No official reference data was refreshed; existing local snapshot was kept.")
