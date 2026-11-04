"""Strict structural validation, independent of the drafting heuristics."""
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Money = Annotated[Decimal, Field(ge=0, le=Decimal('1000000000000'), allow_inf_nan=False)]
Fraction = Annotated[Decimal, Field(ge=0, le=1, allow_inf_nan=False)]
Text = Annotated[str, Field(max_length=20000)]
Name = Annotated[str, Field(min_length=1, max_length=200)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Person(StrictModel):
    id: Name
    name: Name
    kind: Literal['employee'] = 'employee'
    hourly_rate: Money | None = None
    monthly_salary: Money | None = None
    monthly_hours: Annotated[Decimal, Field(gt=0, le=744, allow_inf_nan=False)] | None = None
    hourly_employer_contribution: Money = Decimal('0')

    @model_validator(mode='after')
    def consistent_rate(self):
        if (self.hourly_rate is None) == (self.monthly_salary is None):
            raise ValueError('Genau einen Stundensatz oder ein Monatsgehalt angeben.')
        if self.monthly_salary is not None and self.monthly_hours is None:
            raise ValueError('Für Monatsgehalt sind vertragliche Monatsstunden erforderlich.')
        if self.hourly_rate is not None and self.monthly_hours is not None:
            raise ValueError('Monatsstunden nur zusammen mit Monatsgehalt angeben.')
        return self


class Assignment(StrictModel):
    person_id: Name
    person_days: Annotated[Decimal, Field(ge=0, le=366, allow_inf_nan=False)]
    research_fraction: Fraction = Decimal('1')
    already_funded_costs: Money = Decimal('0')


class WorkPackage(StrictModel):
    id: Name
    title: Name
    description: Text = ''
    method: Text = ''
    deliverable: Text = ''
    start: date
    end: date
    activity: Literal['research', 'routine'] = 'research'
    assignments: list[Assignment] = Field(default_factory=list, max_length=100)

    @model_validator(mode='after')
    def dates_and_people(self):
        if self.end < self.start:
            raise ValueError('Arbeitspaketende liegt vor dem Beginn.')
        if self.start.year != self.end.year:
            raise ValueError('Arbeitspakete an der Jahresgrenze aufteilen; keine automatische Kostenschätzung je Jahr.')
        ids = [a.person_id for a in self.assignments]
        if len(ids) != len(set(ids)):
            raise ValueError('Person im selben Arbeitspaket mehrfach zugeordnet.')
        return self


class Project(StrictModel):
    title: Name
    organization: Name = 'Synthetisches Unternehmen'
    goal: Text = ''
    technical_problem: Text = ''
    state_of_art: Text = ''
    novelty: Text = ''
    hypothesis: Text = ''
    approach: Text = ''
    technical_uncertainty: Text = ''
    measurement_plan: Text = ''
    reproducibility_plan: Text = ''
    risks: Text = ''
    standard_methods_only: bool | None = None
    start: date
    end: date
    sme_claim: bool = False
    other_annual_base: dict[int, Money] = Field(default_factory=dict)
    other_project_aid: Money = Decimal('0')
    personnel: list[Person] = Field(default_factory=list, max_length=100)
    work_packages: list[WorkPackage] = Field(default_factory=list, max_length=100)

    @model_validator(mode='after')
    def coherent_project(self):
        if self.end < self.start:
            raise ValueError('Projektende liegt vor dem Beginn.')
        ids = [p.id for p in self.personnel]
        package_ids = [w.id for w in self.work_packages]
        if len(ids) != len(set(ids)) or len(package_ids) != len(set(package_ids)):
            raise ValueError('Personen- und Arbeitspaket-IDs müssen jeweils eindeutig sein.')
        for wp in self.work_packages:
            if wp.start < self.start or wp.end > self.end:
                raise ValueError(f'Arbeitspaket {wp.id} liegt außerhalb des Projektzeitraums.')
            for assignment in wp.assignments:
                if assignment.person_id not in ids:
                    raise ValueError(f'Unbekannte Person {assignment.person_id} in {wp.id}.')
        return self
