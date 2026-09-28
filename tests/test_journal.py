from datetime import timedelta

from core.clock import local_today


def intake(name='演示'):
    return {'patient': {'name': name, 'age': 42, 'sex': 'male', 'height_cm': 172, 'weight_kg': 82}, 'conditions': ['fatty_liver'], 'medications': []}


def test_case_has_181_distinct_daily_records_and_gradual_story(client):
    response = client.get('/demo/half-year-case')
    assert response.status_code == 200
    data = response.json()
    rows = data['records']
    assert data['synthetic'] is True
    assert data['days'] == len(rows) == 181
    assert len({row['day'] for row in rows}) == 181
    assert rows[0]['day'] == '2026-01-01' and rows[-1]['day'] == '2026-06-30'
    assert rows[0]['weight_kg'] > rows[-1]['weight_kg']
    assert rows[0]['diet_score'] < rows[-1]['diet_score']
    assert 1500 <= rows[-1]['energy_kcal'] <= 2300
    assert sum(row['activity_minutes'] for row in rows[:7]) < sum(row['activity_minutes'] for row in rows[-7:])
    assert all(len(row['food_ids']) == 4 for row in rows)
    assert '不能推断脂肪肝已逆转' in data['notice']


def test_daily_journal_persists_and_is_patient_scoped(client):
    pid = client.post('/intake', json=intake()).json()['patient']['id']
    other = client.post('/intake', json=intake('其他人')).json()['patient']['id']
    day = local_today().isoformat()
    url = f'/patients/{pid}/journal-days/{day}'
    entry = {'day': day, 'breakfast': '燕麦粥、鸡蛋', 'activity_id': 'indoor_walk', 'activity_minutes': 8, 'weight_kg': 81.2, 'notes': '走路时能说话'}
    response = client.put(url, json=entry)
    assert response.status_code == 200
    assert response.json()['entry']['activity_minutes'] == 8
    assert client.get(url).json()['entry']['breakfast'] == '燕麦粥、鸡蛋'
    assert len(client.get(f'/patients/{pid}/journal-days').json()) == 1
    assert client.get(f'/patients/{other}/journal-days/{day}').status_code == 404
    assert client.put(url, json=entry | {'activity_minutes': 12}).json()['entry']['activity_minutes'] == 12
    assert len(client.get(f'/patients/{pid}/journal-days').json()) == 1


def test_journal_rejects_invalid_activity_and_future_day(client):
    pid = client.post('/intake', json=intake()).json()['patient']['id']
    day = local_today().isoformat()
    url = f'/patients/{pid}/journal-days/{day}'
    for entry in [{'day': day}, {'day': day, 'activity_id': 'unknown', 'activity_minutes': 10}, {'day': day, 'activity_id': 'indoor_walk', 'activity_minutes': 0}]:
        assert client.put(url, json=entry).status_code == 422
    tomorrow = (local_today() + timedelta(days=1)).isoformat()
    assert client.put(f'/patients/{pid}/journal-days/{tomorrow}', json={'day': tomorrow, 'breakfast': '测试'}).status_code == 422
