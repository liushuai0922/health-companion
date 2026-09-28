from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from backend.app.models import GuidelineReference, PurineReference, utc_now
from core.nutrition.guidance import combined_guidance, selected_disease_guides
from scripts.purine_import import parse_purines
from scripts.sync_health_data import PROJECT


def test_health_data_sync_resolves_project_from_script_location():
    assert PROJECT == Path(__file__).resolve().parents[1]


def test_purine_import_keeps_food_unit_and_origin():
    book = BytesIO()
    with ZipFile(book, "w") as archive:
        for sheet in range(1, 4):
            cells = '<row r="7"><c r="A7" t="inlineStr"><is><t>Beef liver, raw</t></is></c><c r="B7"><v>2</v></c><c r="S7"><v>168.2</v></c><c r="W7" t="inlineStr"><is><t>USA</t></is></c></row>' if sheet in (1, 3) else '<row r="7"><c r="A7"><v>Category</v></c></row>'
            archive.writestr(f"xl/worksheets/sheet{sheet}.xml", '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' + cells + '</sheetData></worksheet>')
    items = parse_purines(book.getvalue())
    assert len(items) == 2
    assert items[0]["unit"] == "mg/100g"
    assert items[1]["unit"] == "mg/100mL"
    assert items[0]["country"] == "USA"
    assert items[0]["total_purines_mg"] == 168.2


def test_guidelines_and_purines_are_local_searches(client):
    with client.app.state.sessions.begin() as db:
        db.add(GuidelineReference(key="ckd", title="成人慢性肾脏病食养指南", publisher="国家卫生健康委员会", year=2024, condition_codes=["chronic_kidney_disease"], source_url="https://example.org/guide", note="索引", synced_at=utc_now()))
        db.add(PurineReference(key="sheet1-row7", food_name_en="Beef liver, raw", category="North America food", total_purines_mg=168.2, unit="mg/100g", sample_n="2", year="2025", source_code="a", country="USA", source_url="https://example.org/data", synced_at=utc_now()))
    guide = client.get("/reference/guidelines?condition=chronic_kidney_disease").json()
    assert guide["total"] == 1
    assert client.get("/reference/guidelines?condition=stroke").json()["total"] == 0
    result = client.get("/reference/purines?q=liver").json()
    assert result["items"][0]["total_purines_mg"] == 168.2
    assert client.get("/reference/sources").json()["sources"][4]["records"] == 1


def test_kidney_and_sarcopenia_guidance_identifies_individual_review():
    conditions = [{"disease_code": code, "status": "active"} for code in ("chronic_kidney_disease", "sarcopenia", "hypertension")]
    result = combined_guidance(conditions)
    assert any("蛋白质目标" in note for note in result["combination_notes"])
    assert {guide["key"] for guide in selected_disease_guides(conditions)} == {"chronic_kidney_disease", "sarcopenia", "hypertension"}
