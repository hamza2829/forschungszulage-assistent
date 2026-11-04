from copy import deepcopy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from forschungszulage.io import load_project, parse_project
from forschungszulage.models import Project


@pytest.mark.parametrize('changes', [
    {'hourly_rate': '-1'}, {'hourly_rate': 'NaN'}, {'hourly_rate': 'Infinity'},
    {'hourly_rate': None}, {'hourly_rate': '10', 'monthly_salary': '1000', 'monthly_hours': '160'},
    {'hourly_rate': None, 'monthly_salary': '1000'},
    {'hourly_rate': None, 'monthly_salary': '1000', 'monthly_hours': '0'},
    {'monthly_hours': '160'}, {'kind': 'self_employed'}, {'hourly_employer_contribution': '-1'},
])
def test_invalid_person_cost_inputs(payload, changes):
    payload['personnel'][0].update(changes)
    with pytest.raises(ValidationError):
        Project.model_validate(payload)


@pytest.mark.parametrize('changes', [{'person_days': '-1'}, {'person_days': 'NaN'}, {'research_fraction': '1.1'},
                                    {'research_fraction': '-0.1'}, {'already_funded_costs': '-1'}, {'person_id': 'absent'}])
def test_invalid_assignments(payload, changes):
    payload['work_packages'][0]['assignments'][0].update(changes)
    with pytest.raises(ValidationError):
        Project.model_validate(payload)


@pytest.mark.parametrize('change', [{'end': '2025-01-01'}, {'start': '2025-12-31'}, {'end': '2027-01-01'}])
def test_invalid_work_package_dates(payload, change):
    payload['work_packages'][0].update(change)
    with pytest.raises(ValidationError):
        Project.model_validate(payload)


def test_project_dates_are_ordered(payload):
    payload['end'] = '2025-01-01'
    with pytest.raises(ValidationError, match='Projektende'):
        Project.model_validate(payload)


@pytest.mark.parametrize('scope', ['personnel', 'work_packages', 'assignment'])
def test_duplicate_ids_are_rejected(payload, scope):
    target = payload['work_packages'][0]['assignments'] if scope == 'assignment' else payload[scope]
    target.append(deepcopy(target[0]))
    with pytest.raises(ValidationError):
        Project.model_validate(payload)


def test_unknown_fields_and_empty_title_are_rejected(payload):
    with pytest.raises(ValidationError):
        Project.model_validate({**payload, 'unexpected': True})
    with pytest.raises(ValidationError):
        Project.model_validate({**payload, 'title': ' '})


@pytest.mark.parametrize('content,format', [('not: [yaml', 'yaml'), ('{bad', 'json'), ('[]', 'json'),
                                         ('!!python/object/apply:os.system [echo injected]', 'yaml')])
def test_invalid_and_unsafe_documents_are_rejected(content, format):
    with pytest.raises(ValueError, match='Ungültige Projektbeschreibung'):
        parse_project(content, format)


def test_large_documents_are_rejected():
    with pytest.raises(ValueError, match='1 MB'):
        parse_project('a' * 1000001)


def test_json_yaml_and_bom_are_supported(tmp_path, payload):
    text = json.dumps(payload)
    assert parse_project(text, 'json') == parse_project(text, 'yaml')
    path = tmp_path / 'project.json'
    path.write_text(text, encoding='utf-8-sig')
    assert load_project(path).title == payload['title']


@pytest.mark.parametrize('filename', ['absent.yaml', 'not-supported.txt'])
def test_io_errors_include_filename(tmp_path, filename):
    with pytest.raises(ValueError, match=filename):
        load_project(tmp_path / filename)


@pytest.mark.parametrize('path', sorted(Path('examples').glob('*')))
def test_all_german_synthetic_examples_load(path):
    project = load_project(path)
    assert project.title
    assert project.work_packages
