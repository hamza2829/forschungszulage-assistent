from copy import deepcopy

import pytest
import yaml

from forschungszulage.config import Rates, load_rates


def test_every_rate_has_source_date_unit_and_explanation(rates):
    assert len(rates.rates) == 6
    for rate in rates.rates.values():
        assert str(rate.source).startswith('https://')
        assert rate.stand.isoformat() == '2026-11-04'
        assert rate.unit and rate.note
    assert rates.rates['hours_per_person_day'].kind == 'Planungsannahme'
    assert rates.value('annual_base_cap') == 12000000


@pytest.mark.parametrize('field,value', [('standard_allowance', '1.1'), ('sme_allowance', '-0.1'),
                                      ('overhead', '2'), ('hours_per_person_day', '0'), ('hours_per_person_day', '25')])
def test_invalid_configuration_numbers(rates, field, value):
    data = rates.model_dump(mode='json')
    data['rates'][field]['value'] = value
    with pytest.raises(ValueError):
        Rates.model_validate(data)


def test_missing_rate_and_inverted_dates_are_rejected(rates):
    data = rates.model_dump(mode='json')
    del data['rates']['overhead']
    with pytest.raises(ValueError, match='fehlende'):
        Rates.model_validate(data)
    data = rates.model_dump(mode='json')
    data['expense_valid_until'] = '2025-01-01'
    with pytest.raises(ValueError, match='Gültigkeitszeitraum'):
        Rates.model_validate(data)


@pytest.mark.parametrize('content', ['rates: [', 'invalid: true', ''])
def test_bad_configuration_includes_file(tmp_path, content):
    path = tmp_path / 'bad.yaml'
    path.write_text(content, encoding='utf-8')
    with pytest.raises(ValueError, match='bad.yaml'):
        load_rates(path)


def test_missing_configuration_is_clear(tmp_path):
    with pytest.raises(ValueError, match='Konfigurationsfehler'):
        load_rates(tmp_path / 'missing.yaml')


def test_custom_config_can_be_loaded(tmp_path, rates):
    path = tmp_path / 'rates.yaml'
    path.write_text(yaml.safe_dump(rates.model_dump(mode='json')), encoding='utf-8')
    assert load_rates(path) == rates
