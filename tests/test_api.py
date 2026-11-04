import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from forschungszulage.api import create_app
from forschungszulage.io import load_project
from forschungszulage.service import analyze, json_text


@pytest.fixture
def client():
    return TestClient(create_app())


def test_health_and_german_api_page(client):
    assert client.get('/health').json() == {'status': 'ok'}
    response = client.get('/')
    assert response.status_code == 200
    assert 'Keine Rechts- oder Steuerberatung' in response.text
    assert '/docs' in response.text
    assert client.get('/openapi.json').status_code == 200


@pytest.mark.parametrize('path', sorted(Path('examples').glob('*')))
def test_complete_api_response_for_every_example(client, path, rates):
    project = load_project(path)
    response = client.post('/api/projects', json=project.model_dump(mode='json'))
    assert response.status_code == 200, response.text
    result = response.json()
    expected = analyze(project, rates)
    assert result['check'] == __import__('json').loads(json_text(expected['check']))
    assert result['calculation'] == __import__('json').loads(json_text(expected['calculation']))
    assert result['draft_markdown'] == expected['draft_markdown']
    assert base64.b64decode(result['pdf_base64']).startswith(b'%PDF-')


def test_yaml_endpoint_has_same_calculation_as_json(client, payload):
    import yaml
    response = client.post('/api/projects/yaml', content=yaml.safe_dump(payload), headers={'Content-Type': 'application/yaml'})
    assert response.status_code == 200, response.text
    assert response.json()['calculation'] == client.post('/api/projects', json=payload).json()['calculation']


@pytest.mark.parametrize('data', [{}, {'title': 'Bad'}, {'title': 'Bad', 'start': 'wrong', 'end': '2026-01-01'}])
def test_api_rejects_structurally_invalid_projects(client, data):
    assert client.post('/api/projects', json=data).status_code == 422


def test_api_rejects_malformed_yaml(client):
    result = client.post('/api/projects/yaml', content='broken: [', headers={'Content-Type': 'application/yaml'})
    assert result.status_code == 422
    assert 'Ungültige Projektbeschreibung' in result.text


def test_api_rejects_invalid_cost_claim(client, payload):
    payload['work_packages'][0]['assignments'][0]['already_funded_costs'] = '99999'
    result = client.post('/api/projects', json=payload)
    assert result.status_code == 422
    assert 'übersteigen' in result.text


def test_configuration_failure_is_service_error(tmp_path, payload):
    client = TestClient(create_app(tmp_path / 'missing.yaml'))
    response = client.post('/api/projects', json=payload)
    assert response.status_code == 503
    assert 'Konfigurationsfehler' in response.text


def test_api_has_no_persistent_project_storage(client, payload):
    assert client.post('/api/projects', json=payload).status_code == 200
    assert client.get('/api/projects').status_code == 405
