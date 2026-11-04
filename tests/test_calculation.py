from copy import deepcopy
from datetime import date
from decimal import Decimal

import pytest

from forschungszulage.calculation import calculate, calculation_table, eur
from forschungszulage.config import Rates
from forschungszulage.models import Project


def configured(rates, **values):
    data = rates.model_dump(mode='json')
    for key, value in values.items():
        data['rates'][key]['value'] = str(value)
    return Rates.model_validate(data)


def test_hourly_costs_and_2026_overhead(project, rates):
    result = calculate(project, rates)
    row = result['rows'][0]
    assert row['payroll'] == Decimal('960.00')
    assert row['eligible_personnel'] == Decimal('960.00')
    assert row['overhead'] == Decimal('192.00')
    assert row['base_after_cap'] == Decimal('1152.00')
    assert row['estimated_allowance'] == Decimal('288.00')
    assert result['person_rows'][0]['hours'] == 16
    assert result['person_rows'][0]['effective_hourly_cost'] == 60


def test_salary_uses_explicit_contractual_monthly_hours(payload, rates):
    payload['personnel'] = [{'id': 'p', 'name': 'Beispiel', 'monthly_salary': '4000', 'monthly_hours': '160'}]
    result = calculate(Project.model_validate(payload), rates)
    assert result['rows'][0]['payroll'] == Decimal('400.00')
    assert result['person_rows'][0]['effective_hourly_cost'] == 25


def test_research_fraction_and_double_funding_exclusion(payload, rates):
    payload['work_packages'][0]['assignments'][0].update(research_fraction='0.5', already_funded_costs='80')
    result = calculate(Project.model_validate(payload), rates)
    assert result['totals']['eligible_personnel'] == Decimal('400.00')
    assert result['totals']['estimated_allowance'] == Decimal('120.00')


def test_routine_payroll_is_visible_but_excluded(payload, rates):
    payload['work_packages'][0]['activity'] = 'routine'
    result = calculate(Project.model_validate(payload), rates)
    assert result['totals']['payroll'] == 960
    assert result['totals']['eligible_personnel'] == 0
    assert result['totals']['overhead'] == 0
    assert result['totals']['estimated_allowance'] == 0


def test_zero_days_produce_zero_costs(payload, rates):
    payload['work_packages'][0]['assignments'][0]['person_days'] = '0'
    result = calculate(Project.model_validate(payload), rates)
    assert all(value == 0 for value in result['totals'].values())


def test_excessive_double_funding_is_rejected(payload, rates):
    payload['work_packages'][0]['assignments'][0]['already_funded_costs'] = '961'
    with pytest.raises(ValueError, match='übersteigen'):
        calculate(Project.model_validate(payload), rates)


def test_annual_cap_is_shared_across_work_packages(payload, rates):
    second = deepcopy(payload['work_packages'][0])
    second['id'] = 'AP2'
    payload['work_packages'].append(second)
    result = calculate(Project.model_validate(payload), configured(rates, annual_base_cap=1000))
    assert [r['base_after_cap'] for r in result['rows']] == [1000, 0]
    assert result['totals']['base_reduction'] == 1304
    assert result['totals']['estimated_allowance'] == 250


@pytest.mark.parametrize('prior,expected', [('900', '100'), ('1000', '0'), ('2000', '0')])
def test_other_projects_and_group_use_reduce_headroom(payload, rates, prior, expected):
    payload['other_annual_base'] = {2026: prior}
    result = calculate(Project.model_validate(payload), configured(rates, annual_base_cap=1000))
    assert result['totals']['base_after_cap'] == Decimal(expected)


def test_project_aid_cap_reduces_allowance_not_personnel_cost(project, rates):
    p = project.model_copy(update={'other_project_aid': Decimal('25')})
    result = calculate(p, configured(rates, project_aid_cap=100))
    assert result['totals']['estimated_allowance'] == 75
    assert result['totals']['eligible_personnel'] == 960
    assert result['project_aid_remaining'] == 0


def test_sme_rate_is_explicit_assumption(project, rates):
    result = calculate(project.model_copy(update={'sme_claim': True}), rates)
    assert result['totals']['estimated_allowance'] == Decimal('403.20')
    assert any('KMU-Status' in w for w in result['warnings'])


def test_project_started_before_2026_receives_no_overhead(project, rates):
    result = calculate(project.model_copy(update={'start': date(2025, 1, 1)}), rates)
    assert result['totals']['overhead'] == 0
    assert result['totals']['estimated_allowance'] == 240


def test_expenses_outside_verified_period_fail(project, rates):
    changed = rates.model_copy(update={'expense_valid_until': date(2026, 1, 31)})
    with pytest.raises(ValueError, match='außerhalb der geprüften Konfiguration'):
        calculate(project, changed)


def test_cap_resets_for_each_year_when_configured(payload, rates):
    payload['end'] = '2027-12-31'
    second = deepcopy(payload['work_packages'][0])
    second.update(id='AP2', start='2027-01-01', end='2027-03-31')
    payload['work_packages'].append(second)
    config = configured(rates, annual_base_cap=1000).model_copy(update={'expense_valid_until': date(2027, 12, 31)})
    result = calculate(Project.model_validate(payload), config)
    assert result['totals']['base_after_cap'] == 2000
    assert result['totals']['estimated_allowance'] == 500


def test_commercial_rounding_uses_decimal_half_up(payload, rates):
    payload['personnel'] = [{'id': 'p', 'name': 'Beispiel', 'hourly_rate': '0.005'}]
    payload['work_packages'][0]['assignments'][0]['person_days'] = '0.125'
    result = calculate(Project.model_validate(payload), rates)
    assert result['totals']['payroll'] == Decimal('0.01')


def test_empty_plan_has_clear_zero_totals_and_table(project, rates):
    result = calculate(project.model_copy(update={'work_packages': []}), rates)
    assert result['totals']['payroll'] == 0
    assert '| Gesamt |' in calculation_table(result)
    assert eur(Decimal('12345.67')) == '12.345,67 EUR'


def test_overhead_and_day_length_are_configurable(project, rates):
    result = calculate(project, configured(rates, hours_per_person_day=4, overhead='0.1'))
    assert result['totals']['payroll'] == 480
    assert result['totals']['overhead'] == 48
