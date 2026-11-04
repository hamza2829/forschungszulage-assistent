from dataclasses import asdict

import pytest

from forschungszulage.criteria import (NoveltyRule, CreativityRule, UncertaintyRule, SystematicsRule,
                                      ReproducibilityRule, RoutineRule, check_project, present)
from forschungszulage.models import Project


@pytest.mark.parametrize('rule', [NoveltyRule, CreativityRule, UncertaintyRule, SystematicsRule, ReproducibilityRule])
def test_research_example_describes_all_five_criteria(rule, research_project):
    result = rule().evaluate(research_project)
    assert result.status == 'ok'
    assert len(result.reason) > 30
    assert result.question.endswith('?')
    assert result.evidence_fields


@pytest.mark.parametrize('rule,field', [(NoveltyRule, 'novelty'), (CreativityRule, 'hypothesis'),
                                      (UncertaintyRule, 'technical_uncertainty'), (ReproducibilityRule, 'reproducibility_plan')])
def test_missing_primary_evidence_is_missing(rule, field, research_project):
    p = research_project.model_copy(update={field: ''})
    assert rule().evaluate(p).status == 'missing'


@pytest.mark.parametrize('rule,field', [(NoveltyRule, 'state_of_art'), (CreativityRule, 'approach'),
                                      (UncertaintyRule, 'technical_uncertainty'), (ReproducibilityRule, 'measurement_plan')])
def test_weak_evidence_is_explained(rule, field, research_project):
    p = research_project.model_copy(update={field: 'Noch zu knapp.'})
    result = rule().evaluate(p)
    assert result.status == 'weak'
    assert result.reason


def test_systematics_requires_work_packages(project):
    assert SystematicsRule().evaluate(project.model_copy(update={'work_packages': []})).status == 'missing'


@pytest.mark.parametrize('change', [{'method': ''}, {'deliverable': ''}, {'assignments': []}])
def test_systematics_requires_methods_results_and_effort(change, project):
    wp = project.work_packages[0].model_copy(update=change)
    assert SystematicsRule().evaluate(project.model_copy(update={'work_packages': [wp]})).status == 'weak'


def test_budget_risk_is_not_technical_uncertainty(research_project):
    p = research_project.model_copy(update={'technical_uncertainty': 'Es ist unklar, ob das Budget reicht und das Produkt genügend Umsatz erreicht.'})
    assert UncertaintyRule().evaluate(p).status == 'weak'


@pytest.mark.parametrize('placeholder', ['', '  ', 'OFFEN', 'TODO', 'tbd', 'keine Angabe', '-'])
def test_placeholders_are_not_evidence(placeholder):
    assert not present(placeholder)


def test_routine_standard_methods_only_are_flagged(research_project):
    p = research_project.model_copy(update={'standard_methods_only': True})
    result = RoutineRule().evaluate(p)
    assert result.status == 'missing'
    assert 'ausschließlich' in result.reason
    assert CreativityRule().evaluate(p).status == 'weak'


def test_routine_unknown_standard_method_use_is_weak(research_project):
    result = RoutineRule().evaluate(research_project.model_copy(update={'standard_methods_only': None}))
    assert result.status == 'weak'
    assert 'nicht angegeben' in result.reason


def test_routine_requires_uncertainty_and_measurable_results(project):
    result = RoutineRule().evaluate(project)
    assert result.status == 'missing'
    assert 'Messplan' in result.reason
    assert 'Ungewissheit' in result.reason


def test_all_routine_packages_stay_flagged_even_with_research_prose(research_project):
    packages = [p.model_copy(update={'activity': 'routine'}) for p in research_project.work_packages]
    result = RoutineRule().evaluate(research_project.model_copy(update={'work_packages': packages}))
    assert result.status == 'weak'
    assert 'Alle Arbeitspakete' in result.reason


def test_check_is_a_checklist_not_an_eligibility_decision(research_project):
    result = check_project(research_project)
    assert len(result['criteria']) == 5
    assert {r['criterion'] for r in result['criteria']} == {'Neuartigkeit', 'Kreativität', 'Ungewissheit', 'Systematik', 'Reproduzierbarkeit'}
    assert result['routine']['status'] == 'ok'
    assert 'Keine fachliche Bestätigung' in result['meaning']
