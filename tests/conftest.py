from copy import deepcopy
from pathlib import Path

import pytest

from forschungszulage.config import load_rates
from forschungszulage.io import load_project
from forschungszulage.models import Project


@pytest.fixture
def payload():
    return {
        'title': 'Synthetischer Versuch', 'start': '2026-01-01', 'end': '2026-12-31',
        'personnel': [{'id': 'p', 'name': 'Person Beispiel', 'hourly_rate': '50', 'hourly_employer_contribution': '10'}],
        'work_packages': [{'id': 'AP1', 'title': 'Kontrollierter Versuch', 'start': '2026-01-01', 'end': '2026-03-31',
                          'method': 'Kontrollierter Vergleich mit einer unveränderten Referenz.',
                          'deliverable': 'Versionierte Messdaten und ein nachvollziehbarer Ergebnisbericht.',
                          'assignments': [{'person_id': 'p', 'person_days': '2'}]}],
    }


@pytest.fixture
def project(payload):
    return Project.model_validate(payload)


@pytest.fixture
def rates():
    return load_rates()


@pytest.fixture
def research_project():
    return load_project(Path('examples/logistikplaner.yaml'))
