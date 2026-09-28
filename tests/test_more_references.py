import io
from zipfile import ZipFile

from backend.app.models import FoodCompositionReference, HealthTopicReference, utc_now
from scripts.more_reference_import import parse_food_composition, parse_medline_topics


def test_food_import_only_selects_requested_food_and_keeps_missing_values():
    blob = io.BytesIO()
    with ZipFile(blob, "w") as archive:
        archive.writestr("release/food.csv", "fdc_id,data_type,description\n1,foundation_food,Apple raw\n2,sample_food,Apple sample\n")
        archive.writestr("release/food_nutrient.csv", "fdc_id,nutrient_id,amount\n1,1003,0.3\n1,1008,52\n1,2048,49\n2,1003,9\n")
    items = parse_food_composition(blob.getvalue(), "foundation_food", "2026-04")
    assert len(items) == 1
    assert items[0]["protein_g"] == 0.3
    assert items[0]["energy_kcal"] == 49
    assert items[0]["sodium_mg"] is None


def test_medline_import_only_english_and_strips_markup():
    blob = io.BytesIO()
    xml = '<health-topics><health-topic id="7" language="English" title="Gout" url="https://medlineplus.gov/gout.html"><full-summary>&lt;p&gt;About &lt;b&gt;gout&lt;/b&gt;.&lt;/p&gt;</full-summary></health-topic><health-topic id="8" language="Spanish" title="Gota" url="https://medlineplus.gov/spanish/gout.html" /></health-topics>'
    with ZipFile(blob, "w") as archive:
        archive.writestr("topics.xml", xml)
    items = parse_medline_topics(blob.getvalue(), "2026-09-25")
    assert len(items) == 1
    assert items[0]["title_zh"] == "痛风"
    assert items[0]["summary_en"] == "About gout."


def test_new_reference_endpoints_keep_units_and_attribution(client):
    with client.app.state.sessions.begin() as db:
        db.add(FoodCompositionReference(fdc_id=123, description_en="Oats, raw", data_type="foundation_food", release="2026-04", energy_kcal=380, protein_g=13, fat_g=7, carbohydrate_g=67, fiber_g=None, sodium_mg=2, source_url="https://fdc.nal.usda.gov/food-details/123/nutrients", synced_at=utc_now()))
        db.add(HealthTopicReference(topic_id=7, title_en="Gout", title_zh="痛风", summary_en="About gout.", condition_codes=["gout"], source_url="https://medlineplus.gov/gout.html", release="2026-09-25", synced_at=utc_now()))
    food = client.get("/reference/composition?q=oats&kind=foundation_food").json()
    assert food["total"] == 1
    assert food["items"][0]["nutrients_per_100g"]["fiber_g"] is None
    assert client.get("/reference/composition?kind=sr_legacy_food").json()["total"] == 0
    topics = client.get("/reference/health-topics?q=痛风").json()
    assert topics["total"] == 1
    assert "MedlinePlus" in topics["attribution"]
    assert [x["records"] for x in client.get("/reference/sources").json()["sources"][-3:]] == [0, 1, 1]


def test_chinese_food_search_keeps_original_description(client):
    from backend.app.models import FoodReference, PurineReference
    with client.app.state.sessions.begin() as db:
        db.add(FoodReference(key="apple", fdc_id=101, description_en="Apples, raw, with skin", data_type="SR Legacy", synced_at=utc_now()))
        db.add(PurineReference(key="sample-beef", food_name_en="Beef liver, raw", category="food", total_purines_mg=168.2, unit="mg/100g", sample_n="2", year="2025", source_code="a", country="USA", source_url="https://example.org/data", synced_at=utc_now()))
        db.add(FoodCompositionReference(fdc_id=102, description_en="Oats, raw", data_type="foundation_food", release="2026-04", energy_kcal=380, protein_g=13, fat_g=7, carbohydrate_g=67, fiber_g=None, sodium_mg=2, source_url="https://example.org/oats", synced_at=utc_now()))
        db.add(FoodCompositionReference(fdc_id=103, description_en="Beverages, QUAKER OATS, orange drink", data_type="foundation_food", release="2026-04", energy_kcal=50, protein_g=0, fat_g=0, carbohydrate_g=12, fiber_g=None, sodium_mg=5, source_url="https://example.org/drink", synced_at=utc_now()))
    apple = client.get("/reference/foods?q=苹果").json()["items"][0]
    assert apple["name_zh"] == "苹果" and apple["description_en"].startswith("Apples")
    purine = client.get("/reference/purines?q=牛肝").json()["items"][0]
    assert purine["food_name_zh"] == "牛肝" and purine["food_name_en"] == "Beef liver, raw"
    oats_result = client.get("/reference/composition?q=燕麦").json()
    assert oats_result["total"] == 1
    oats = oats_result["items"][0]
    assert oats["name_zh"] == "燕麦" and oats["description_en"] == "Oats, raw"
    sources = client.get("/reference/sources").json()["sources"]
    assert all(source["name_zh"] for source in sources)
