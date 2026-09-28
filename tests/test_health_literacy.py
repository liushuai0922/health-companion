def test_health_literacy_is_sourced_and_has_no_invented_lab_results(client):
    response = client.get("/catalog/health-literacy")
    assert response.status_code == 200
    data = response.json()
    topics = {topic["key"]: topic for topic in data["topics"]}
    assert {"bmi", "lipids", "liver", "blood_pressure", "glucose", "uric_acid", "kidney", "bone_muscle"} == set(topics)
    assert all(topic["source_url"].startswith("https://") for topic in topics.values())
    assert all("value" not in topic for topic in topics.values())
    assert "除 BMI 外" in data["scope"]


def test_browser_exposes_literacy_cards(client):
    page = client.get("/")
    assert page.status_code == 200
    assert 'id="literacy-cards"' in page.text
    script = client.get("/static/app.js?v=6")
    assert script.status_code == 200
    assert "renderLiteracy(conditions,p)" in script.text
