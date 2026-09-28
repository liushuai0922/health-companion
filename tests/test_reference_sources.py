from fastapi.testclient import TestClient
from backend.app.main import create_app
from scripts.sync_references import common_drug_record, common_food_record, archive_food_records
from backend.app.models import DrugReference, FoodReference, utc_now


def test_official_drug_identity_and_label_do_not_cross_match():
    def fake(url):
        if "rxcui.json" in url:
            return {"idGroup": {"rxnormId": ["83367"]}}
        if "properties.json" in url:
            return {"properties": {"name": "atorvastatin"}}
        return {"data": [{"title": "ATORVASTATIN AND EZETIMIBE", "setid": "combination"}, {"title": "ATORVASTATIN CALCIUM TABLET", "setid": "single"}]}
    result = common_drug_record({"key": "atorvastatin", "zh": "阿托伐他汀", "group": "血脂管理", "aliases": []}, fake)
    assert result["rxcui"] == "83367"
    assert result["dailymed_setid"] == "single"


def test_usda_exact_food_only():
    seed = {"key": "vegetables", "query": "broccoli", "exact": "Broccoli, raw"}
    def wrong(_):
        return {"foods": [{"fdcId": 1, "description": "Broccoli soup", "dataType": "SR Legacy"}]}
    try:
        common_food_record(seed, "demo", wrong)
    except ValueError:
        pass
    else:
        assert False, "Unrelated food should have been rejected"
    good = lambda _: {"foods": [{"fdcId": 170379, "description": "Broccoli, raw", "dataType": "SR Legacy"}]}
    assert common_food_record(seed, "demo", good)["fdc_id"] == 170379


def test_usda_archive_exact_match():
    import csv
    import io
    import zipfile
    blob = io.BytesIO()
    with zipfile.ZipFile(blob, "w") as archive:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["fdc_id", "data_type", "description"])
        writer.writeheader()
        writer.writerow({"fdc_id": "170379", "data_type": "sr_legacy_food", "description": "Broccoli, raw"})
        writer.writerow({"fdc_id": "1", "data_type": "sr_legacy_food", "description": "Broccoli soup"})
        archive.writestr("release/food.csv", output.getvalue())
    seeds = [{"key": "vegetables", "exact": "Broccoli, raw"}, {"key": "other", "exact": "Broccoli"}]
    matches = archive_food_records(blob.getvalue(), seeds)
    assert set(matches) == {"vegetables"}
    assert matches["vegetables"]["fdc_id"] == 170379


def test_reference_search_is_local_and_separate_from_safety(client, patient):
    sessions = client.app.state.sessions
    with sessions.begin() as db:
        db.add(DrugReference(key="metformin", name_zh="二甲双胍", name_en="metformin", group_name="血糖管理", aliases=["盐酸二甲双胍"], rxcui="6809", dailymed_setid=None, dailymed_title=None, synced_at=utc_now()))
        db.add(FoodReference(key="vegetables", fdc_id=170379, description_en="Broccoli, raw", data_type="SR Legacy", synced_at=utc_now()))
    response = client.get("/reference/drugs?q=二甲")
    assert response.status_code == 200
    assert response.json()["items"][0]["rxcui"] == "6809"
    assert response.json()["items"][0]["dailymed_label_url"] is None
    assert client.get("/reference/foods?q=broccoli").json()["total"] == 1
    status = client.get("/reference/sources").json()
    assert [x["records"] for x in status["sources"]] == [1, 0, 1, 0, 0, 0, 0, 0]
    safety = client.get(f"/patients/{patient['id']}/safety-check").json()
    assert safety["alerts"] == []
    assert safety["coverage"]["message"].startswith("仅为少量演示规则")
