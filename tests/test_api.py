import pytest
import jwt
from datetime import timedelta
from bson import ObjectId
from flask import g
from brainage.common import APIError, now, update_sample

BASE = '/api/v1'
RESULT = {'modality': 'dmri', 'estimated_age_weeks': 41.5, 'method': 'Test fixture',
    'model_version': 'test-v1', 'provenance': 'Invented test data, not inference', 'quality_score': 0.8}

def test_health_and_errors(client):
    assert client.get(BASE+'/health').json['status'] == 'ok'
    assert client.get(BASE+'/missing').status_code == 404
    assert client.post(BASE+'/health').status_code == 405
    assert client.get(BASE+'/samples').status_code == 401
    assert client.get(BASE+'/samples', headers={'Authorization': 'Bearer fake'}).status_code == 401

def test_registration_approval_and_no_privilege_escalation(client, tokens):
    payload = {'username': 'new.user', 'password': 'NewPassword!2026', 'display_name': 'New User'}
    assert client.post(BASE+'/auth/register', json={**payload, 'role': 'admin'}).status_code == 400
    response = client.post(BASE+'/auth/register', json=payload)
    assert response.status_code == 201
    user_id = response.json['data']['_id']
    assert 'password_hash' not in response.json['data']
    assert client.post(BASE+'/auth/register', json=payload).status_code == 409
    credentials = {k: payload[k] for k in ('username', 'password')}
    assert client.post(BASE+'/auth/login', json=credentials).status_code == 403
    assert client.patch(BASE+'/users/'+user_id, json={'active': True}, headers=tokens['admin']).status_code == 200
    assert client.post(BASE+'/auth/login', json=credentials).status_code == 200

def test_auth_revocation_and_expiration(client, tokens, app):
    assert client.get(BASE+'/auth/me', headers=tokens['alice']).status_code == 200
    assert client.post(BASE+'/auth/logout', headers=tokens['alice']).status_code == 204
    assert client.get(BASE+'/auth/me', headers=tokens['alice']).status_code == 401
    claims = jwt.decode(tokens['bob']['Authorization'][7:], app.config['JWT_SECRET'], algorithms=['HS256'], audience='brainage-api')
    claims['exp'] = now() - timedelta(seconds=1)
    expired = jwt.encode(claims, app.config['JWT_SECRET'], algorithm='HS256')
    assert client.get(BASE+'/auth/me', headers={'Authorization': 'Bearer '+expired}).status_code == 401

def test_password_change_revokes_sessions(client, tokens):
    response = client.put(BASE+'/auth/password', headers=tokens['alice'], json={
        'current_password': 'TestingPass!2026', 'new_password': 'ChangedPassword!2026'})
    assert response.status_code == 200
    assert client.get(BASE+'/auth/me', headers=tokens['alice']).status_code == 401
    assert client.post(BASE+'/auth/login', json={'username': 'alice', 'password': 'TestingPass!2026'}).status_code == 401
    assert client.post(BASE+'/auth/login', json={'username': 'alice', 'password': 'ChangedPassword!2026'}).status_code == 200

@pytest.mark.parametrize('payload', [[], None, {'username': 'ab', 'password': 'long-password'},
    {'username': 'alice', 'password': 'short'}, {'username': {'$ne': None}, 'password': 'TestingPass!2026'},
    {'username': 'alice', 'password': '界'*25}])
def test_auth_input_validation(client, payload):
    response = client.post(BASE+'/auth/login', json=payload)
    assert response.status_code in (400, 415)

def test_sample_lifecycle_and_partial_update(client, tokens, make_sample):
    item = make_sample()
    path = BASE+'/samples/'+item['_id']
    response = client.put(path, json={'description': 'Updated'}, headers=tokens['alice'])
    assert response.status_code == 200
    assert response.json['data']['age_at_scan_weeks'] == 40
    assert response.json['data']['version'] == 2
    assert client.get(path, headers=tokens['alice']).status_code == 200
    assert client.delete(path, headers=tokens['alice']).status_code == 204
    assert client.get(path, headers=tokens['alice']).status_code == 404

def test_sample_access_control(client, tokens, make_sample):
    item = make_sample()
    path = BASE+'/samples/'+item['_id']
    assert client.get(path, headers=tokens['bob']).status_code == 404
    assert client.get(BASE+'/samples', headers=tokens['bob']).json['pagination']['total'] == 0
    assert client.get(BASE+'/statistics/overview', headers=tokens['bob']).json['data']['total'] == 0
    assert client.patch(path, headers=tokens['alice'], json={'visibility': 'shared'}).status_code == 200
    assert client.get(path, headers=tokens['bob']).status_code == 200
    assert client.patch(path, headers=tokens['bob'], json={'status': 'failed'}).status_code == 403
    assert client.delete(path, headers=tokens['bob']).status_code == 403
    assert client.patch(path, headers=tokens['admin'], json={'status': 'ready'}).status_code == 200

@pytest.mark.parametrize('field,value', [('age_at_scan_weeks', True), ('age_at_scan_weeks', '40'),
    ('age_at_scan_weeks', 10), ('age_at_scan_weeks', 90), ('age_at_scan_weeks', float('nan')),
    ('birth_age_weeks', 44), ('has_dmri', 'true'), ('has_fmri', 1), ('visibility', 'public'),
    ('status', 'diagnosed'), ('sex', []), ('sample_code', {'$ne': None}), ('sample_code', 'a/b'),
    ('source', 'dhcp_local'), ('owner_id', 'x'), ('description', 'x'*2001)])
def test_sample_validation(client, tokens, field, value):
    response = client.post(BASE+'/samples', headers=tokens['alice'], json={
        'sample_code': 'TEST', 'age_at_scan_weeks': 40, field: value})
    assert response.status_code == 400, response.json

def test_duplicate_and_missing(client, tokens, make_sample):
    make_sample(sample_code='DUP')
    assert client.post(BASE+'/samples', headers=tokens['alice'], json={'sample_code': 'DUP', 'age_at_scan_weeks': 40}).status_code == 409
    assert client.get(BASE+'/samples/not-an-id', headers=tokens['alice']).status_code == 400
    assert client.get(BASE+'/samples/'+'0'*24, headers=tokens['alice']).status_code == 404
    assert client.post(BASE+'/samples', data='{}', headers=tokens['alice']).status_code == 415
    assert client.post(BASE+'/samples', data='{bad', content_type='application/json', headers=tokens['alice']).status_code == 400

@pytest.mark.parametrize('query', ['page=0', 'page=abc', 'page_size=101', 'page_size=-1', 'sort=password_hash',
    'age_min=45&age_max=30', 'age_min=NaN', 'age_min=hello', 'modality=invalid', 'status=unknown',
    'unknown=yes', 'page=1&page=2', 'order=random', 'page=99999999999999999999999999999999999'])
def test_query_validation(client, tokens, query):
    assert client.get(BASE+'/samples?'+query, headers=tokens['alice']).status_code == 400

def test_search_sort_filters_pagination(client, tokens, make_sample):
    for i in range(5):
        make_sample(sample_code=f'COHORT-{i}', age_at_scan_weeks=38+i)
    response = client.get(BASE+'/samples?q=COHORT&age_min=39&age_max=42&modality=both&page_size=2&sort=age_at_scan_weeks&order=desc', headers=tokens['alice'])
    assert response.json['pagination'] == {'page': 1, 'page_size': 2, 'pages': 2, 'total': 4}
    assert [x['age_at_scan_weeks'] for x in response.json['data']] == [42, 41]
    assert all('notes' not in x for x in response.json['data'])
    assert client.get(BASE+'/samples?q=.*', headers=tokens['alice']).json['pagination']['total'] == 0

@pytest.mark.parametrize('kind,payload', [('notes', {'text': 'A note', 'category': 'quality'}), ('analyses', RESULT)])
def test_nested_crud_owner_and_parent_scope(client, tokens, make_sample, kind, payload):
    item = make_sample(visibility='shared')
    path = BASE+'/samples/'+item['_id']+'/'+kind
    created = client.post(path, headers=tokens['bob'], json=payload)
    assert created.status_code == 201, created.json
    identifier = created.json['data']['_id']
    assert client.get(path, headers=tokens['alice']).json['pagination']['total'] == 1
    assert client.get(path+'/'+identifier, headers=tokens['alice']).status_code == 200
    update = {'text': 'Revised note'} if kind == 'notes' else {'estimated_age_weeks': 42}
    assert client.put(path+'/'+identifier, headers=tokens['alice'], json=update).status_code == 403
    revised = client.put(path+'/'+identifier, headers=tokens['bob'], json=update)
    assert revised.status_code == 200
    if kind == 'analyses':
        assert revised.json['data']['age_difference_weeks'] == 2
    other = make_sample(visibility='shared')
    assert client.get(BASE+'/samples/'+other['_id']+'/'+kind+'/'+identifier, headers=tokens['bob']).status_code == 404
    assert client.delete(path+'/'+identifier, headers=tokens['bob']).status_code == 204
    assert client.get(path+'/'+identifier, headers=tokens['alice']).status_code == 404

def test_analysis_validation_and_age_recalculation(client, tokens, make_sample):
    item = make_sample()
    path = BASE+'/samples/'+item['_id']
    for payload in [{**RESULT, 'quality_score': 2}, {**RESULT, 'estimated_age_weeks': True},
        {**RESULT, 'provenance': ''}, {**RESULT, 'age_difference_weeks': 99}]:
        assert client.post(path+'/analyses', headers=tokens['alice'], json=payload).status_code == 400
    assert client.post(path+'/analyses', headers=tokens['alice'], json=RESULT).status_code == 201
    assert client.patch(path, headers=tokens['alice'], json={'has_dmri': False}).status_code == 409
    response = client.patch(path, headers=tokens['alice'], json={'age_at_scan_weeks': 41})
    assert response.json['data']['analyses'][0]['age_difference_weeks'] == .5
    response = client.patch(path, headers=tokens['alice'], json={'age_at_scan_weeks': None})
    assert response.json['data']['analyses'][0]['age_difference_weeks'] is None
    missing = make_sample(has_dmri=False)
    assert client.post(BASE+'/samples/'+missing['_id']+'/analyses', headers=tokens['alice'], json=RESULT).status_code == 400

def test_admin_permissions_and_immediate_deactivation(client, tokens):
    assert client.get(BASE+'/users', headers=tokens['alice']).status_code == 403
    users = client.get(BASE+'/users', headers=tokens['admin']).json['data']
    assert all('password_hash' not in user for user in users)
    bob = next(user for user in users if user['username'] == 'bob')
    admin = next(user for user in users if user['username'] == 'admin')
    assert client.put(BASE+'/users/'+admin['_id'], headers=tokens['admin'], json={'active': False}).status_code == 409
    assert client.put(BASE+'/users/'+bob['_id'], headers=tokens['admin'], json={'active': False}).status_code == 200
    assert client.get(BASE+'/auth/me', headers=tokens['bob']).status_code == 401
    assert client.get(BASE+'/audit-logs', headers=tokens['admin']).json['pagination']['total'] == 1
    assert client.get(BASE+'/audit-logs', headers=tokens['alice']).status_code == 403

def test_aggregation_latest_pairing_and_visibility(client, tokens, make_sample):
    item = make_sample()
    path = BASE+'/samples/'+item['_id']+'/analyses'
    for mode, estimate in [('dmri', 39), ('dmri', 42), ('fmri', 40)]:
        assert client.post(path, headers=tokens['alice'], json={**RESULT, 'modality': mode, 'estimated_age_weeks': estimate}).status_code == 201
    rows = client.get(BASE+'/statistics/maturity', headers=tokens['alice']).json['data']
    assert next(x for x in rows if x['_id']['modality'] == 'dmri')['mean_estimated_age_weeks'] == 42
    pair = client.get(BASE+'/statistics/comparison', headers=tokens['alice']).json['data'][0]
    assert pair['paired_sample_count'] == 1 and pair['mean_dmri_minus_fmri_weeks'] == 2
    for endpoint in ('maturity', 'comparison', 'cohorts'):
        assert client.get(BASE+'/statistics/'+endpoint, headers=tokens['bob']).json['data'] == []
    cohort = client.get(BASE+'/statistics/cohorts', headers=tokens['alice']).json['data'][0]
    assert cohort['sample_count'] == 1 and cohort['_id']['age_group'] == '37-<42 weeks'
    csv = client.get(BASE+'/exports/cohorts?format=csv', headers=tokens['alice'])
    assert csv.status_code == 200 and 'text/csv' in csv.content_type and '37-<42 weeks' in csv.text

def test_imported_identity_protected(client, tokens, make_sample, database):
    item = make_sample()
    database.samples.update_one({'_id': ObjectId(item['_id'])}, {'$set': {'source': 'dhcp_local'}})
    assert client.patch(BASE+'/samples/'+item['_id'], headers=tokens['alice'], json={'sample_code': 'NEW'}).status_code == 400

def test_optimistic_concurrency(app, database, identities, make_sample):
    item = make_sample()
    original = database.samples.find_one({'_id': ObjectId(item['_id'])})
    with app.test_request_context():
        g.user = identities[1]
        update_sample(original, {'description': 'first'}, 'test')
        with pytest.raises(APIError) as error:
            update_sample(original, {'description': 'stale'}, 'test')
        assert error.value.status == 409
    assert database.samples.find_one({'_id': original['_id']})['description'] == 'first'

def test_statistics_model_selection_and_age_groups(client, tokens, make_sample):
    for age in (31.9, 32, 37, 42, None):
        item = make_sample(age_at_scan_weeks=age, birth_age_weeks=None)
        path = BASE + '/samples/' + item['_id'] + '/analyses'
        for mode in ('dmri', 'fmri'):
            for method, version, estimate in (('A', 'v1', 40), ('B', 'v2', 45)):
                result = {**RESULT, 'modality': mode, 'method': method,
                          'model_version': version, 'estimated_age_weeks': estimate}
                assert client.post(path, headers=tokens['alice'], json=result).status_code == 201
    url = BASE + '/statistics/maturity?method=A&model_version=v1&group_by=age_group'
    rows = client.get(url, headers=tokens['alice']).json['data']
    dmri = [r for r in rows if r['_id']['modality'] == 'dmri']
    assert {r['_id']['age_group'] for r in dmri} == {'<32 weeks', '32-<37 weeks', '37-<42 weeks', '>=42 weeks', 'unknown'}
    assert all(r['sample_count'] == 1 and r['mean_estimated_age_weeks'] == 40 for r in dmri)
    assert next(r for r in dmri if r['_id']['age_group'] == 'unknown')['difference_count'] == 0
    query = '?dmri_method=A&dmri_model_version=v1&fmri_method=B&fmri_model_version=v2'
    pair = client.get(BASE + '/statistics/comparison' + query, headers=tokens['alice']).json['data'][0]
    assert pair['paired_sample_count'] == 5 and pair['mean_dmri_minus_fmri_weeks'] == -5
    assert client.get(url, headers=tokens['bob']).json['data'] == []
    assert client.get(BASE + '/statistics/maturity?group_by=invalid', headers=tokens['alice']).status_code == 400
