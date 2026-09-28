from core.activity.engine import beginner_exercise_plan, exercise_catalog


def test_catalog_has_traceable_low_intensity_activities(client):
    data = client.get('/catalog/exercises').json()
    assert len(data['activities']) >= 11
    assert {a['id'] for a in data['activities']} >= {'indoor_walk', 'seated_mobility', 'gentle_stretch', 'radio_calisthenics', 'brisk_walk', 'low_impact_aerobics', 'five_km_brisk_walk', 'five_km_jog'}
    for activity in data['activities']:
        assert activity['source_url'].startswith('https://')
        assert bool(activity['compendium_code']) == (activity['met'] is not None)
        if 'starter' in activity['tags']:
            assert activity['met'] is None or activity['met'] <= 3
    assert next(a for a in data['activities'] if a['id'] == 'five_km_jog')['met'] >= 6


def test_beginner_plan_conditions_and_age():
    profile = {'age': 42}
    conditions = [{'disease_code': 'fatty_liver', 'status': 'active'}, {'disease_code': 'type2_diabetes', 'status': 'active'}]
    result = beginner_exercise_plan(profile, conditions)
    assert result['available']
    assert len(result['week']) == 7
    assert result['recommended'] == ['indoor_walk', 'gentle_stretch', 'wall_push']
    assert {'脂肪肝', '糖尿病与低血糖'} <= {note['title'] for note in result['notes']}
    older = beginner_exercise_plan({'age': 70}, [{'disease_code': 'stroke', 'status': 'active'}])
    assert older['recommended'] == ['indoor_walk', 'seated_mobility', 'supported_balance']
    assert not beginner_exercise_plan({'age': 15}, [])['available']


def test_exercise_appears_in_patient_guide(client):
    intake = {'patient': {'name': '演示', 'age': 42, 'sex': 'male', 'height_cm': 172, 'weight_kg': 82}, 'conditions': ['hyperlipidemia', 'fatty_liver'], 'medications': []}
    pid = client.post('/intake', json=intake).json()['patient']['id']
    guide = client.get(f'/patients/{pid}/diet-guide').json()
    assert guide['exercise']['available']
    assert guide['exercise']['recommended'][0] == 'indoor_walk'
    assert guide['exercise']['catalog_version'] == exercise_catalog()['version']
