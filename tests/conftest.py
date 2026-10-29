import uuid
import pytest
from bson import ObjectId
from brainage import create_app
from brainage.auth import hash_password
from brainage.common import now

@pytest.fixture(scope='session')
def app():
    name = 'brainage_test_' + uuid.uuid4().hex
    app = create_app({'TESTING': True, 'MONGO_DB': name, 'JWT_SECRET': 'test-only-key-' + 'x'*40})
    yield app
    assert name.startswith('brainage_test_')
    app.extensions['mongo_client'].drop_database(name)
    app.extensions['mongo_client'].close()

@pytest.fixture(scope='session')
def identities():
    return [{'_id': ObjectId(), 'username': name, 'display_name': name, 'role': role,
        'password_hash': hash_password('TestingPass!2026'), 'active': True, 'auth_version': 0, 'created_at': now()}
        for name, role in [('admin', 'admin'), ('alice', 'researcher'), ('bob', 'researcher')]]

@pytest.fixture(autouse=True)
def reset(app, identities):
    database = app.extensions['mongo_db']
    assert database.name.startswith('brainage_test_')
    for name in database.list_collection_names():
        database[name].delete_many({})
    database.users.insert_many([dict(x) for x in identities])

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def database(app):
    return app.extensions['mongo_db']

@pytest.fixture
def tokens(client):
    result = {}
    for name in ('admin', 'alice', 'bob'):
        response = client.post('/api/v1/auth/login', json={'username': name, 'password': 'TestingPass!2026'})
        assert response.status_code == 200
        result[name] = {'Authorization': 'Bearer ' + response.json['access_token']}
    return result

@pytest.fixture
def make_sample(client, tokens):
    def create(owner='alice', **fields):
        payload = {'sample_code': 'TEST-' + uuid.uuid4().hex[:8], 'age_at_scan_weeks': 40,
            'birth_age_weeks': 38, 'has_dmri': True, 'has_fmri': True, **fields}
        response = client.post('/api/v1/samples', json=payload, headers=tokens[owner])
        assert response.status_code == 201, response.json
        return response.json['data']
    return create
