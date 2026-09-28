from core.nutrition.scoring import score_day


def diary():
    return {'day': '2026-06-01', 'day_complete': True, 'activity_level': 'inactive', 'meals': [
        {'name': 'breakfast', 'status': 'recorded', 'items': [{'food_id': 'oats', 'servings': 1}]},
        {'name': 'lunch', 'status': 'recorded', 'items': [{'food_id': 'brown_rice', 'servings': 1}, {'food_id': 'fish', 'servings': 1}, {'food_id': 'vegetables', 'servings': 2}]},
        {'name': 'dinner', 'status': 'recorded', 'items': [{'food_id': 'white_rice', 'servings': 1}, {'food_id': 'tofu', 'servings': 1}, {'food_id': 'vegetables', 'servings': 2}]},
        {'name': 'snack', 'status': 'skipped', 'items': []},
    ]}


def test_activity_levels_and_exercise_record_are_separate(client):
    profile = {'patient': {'name': '活动测试', 'age': 42, 'sex': 'male', 'height_cm': 172, 'weight_kg': 82}, 'conditions': [], 'medications': []}
    pid = client.post('/intake', json=profile).json()['patient']['id']
    url = f'/patients/{pid}/diet-days/2026-06-01'
    base = diary()
    first = client.put(url, json=base).json()['result']['nutrition_estimate']
    with_exercise = base | {'exercise_activity_id': 'five_km_brisk_walk', 'exercise_minutes': 55}
    recorded = client.put(url, json=with_exercise).json()['result']['nutrition_estimate']
    assert recorded['reference_kcal'] == first['reference_kcal']
    assert recorded['totals'] == first['totals']
    assert recorded['recorded_exercise']['minutes'] == 55
    assert recorded['recorded_exercise']['name'] == '5 公里较快步行'
    higher = client.put(url, json=with_exercise | {'activity_level': 'very_active'}).json()['result']['nutrition_estimate']
    assert higher['reference_kcal'] > first['reference_kcal']
    assert higher['activity_factor'] == 1.725


def test_exercise_input_validation(client):
    profile = {'patient': {'name': '活动测试', 'age': 42, 'sex': 'male', 'height_cm': 172, 'weight_kg': 82}, 'conditions': [], 'medications': []}
    pid = client.post('/intake', json=profile).json()['patient']['id']
    url = f'/patients/{pid}/diet-days/2026-06-01'
    for update in [
        {'exercise_activity_id': 'unknown', 'exercise_minutes': 10},
        {'exercise_activity_id': 'brisk_walk', 'exercise_minutes': 0},
        {'exercise_activity_id': None, 'exercise_minutes': 10},
        {'activity_level': 'impossible'},
    ]:
        assert client.put(url, json=diary() | update).status_code == 422
