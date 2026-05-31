import pytest
import json
from backend.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_generate_endpoint_returns_task_id(client):
    response = client.post('/api/generate',
                           json={'length': 10, 'use_digits': True, 'use_special': False})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'task_id' in data
    assert len(data['task_id']) > 0

def test_result_endpoint_for_nonexistent_task(client):
    response = client.get('/api/result/nonexistent-id-123')
    assert response.status_code == 404

def test_generate_with_invalid_json(client):
    response = client.post('/api/generate', data='invalid', content_type='application/json')
    # Flask вернёт 400 или 500 — в зависимости, но главное не 200
    assert response.status_code != 200
