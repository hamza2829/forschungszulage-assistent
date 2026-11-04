"""All financial parameters include provenance, including planning assumptions."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, HttpUrl, model_validator

from .models import StrictModel

DEFAULT_CONFIG = Path(__file__).parent / 'data' / 'rates.yaml'


class Rate(StrictModel):
    value: Decimal = Field(ge=0, le=Decimal('1000000000000'), allow_inf_nan=False)
    unit: str = Field(min_length=1)
    kind: Literal['gesetzlich', 'Planungsannahme']
    source: HttpUrl
    stand: date
    note: str = Field(min_length=1)


class Rates(StrictModel):
    expense_valid_from: date
    expense_valid_until: date
    overhead_project_start_from: date
    rates: dict[str, Rate]

    @model_validator(mode='after')
    def complete(self):
        required = {'standard_allowance', 'sme_allowance', 'annual_base_cap', 'project_aid_cap', 'overhead', 'hours_per_person_day'}
        if set(self.rates) != required:
            raise ValueError('Konfiguration enthält fehlende oder unbekannte Sätze.')
        if self.expense_valid_until < self.expense_valid_from:
            raise ValueError('Ungültiger Gültigkeitszeitraum der Konfiguration.')
        for key in ('standard_allowance', 'sme_allowance', 'overhead'):
            if self.rates[key].value > 1:
                raise ValueError(f'{key} muss zwischen 0 und 1 liegen.')
        if self.rates['hours_per_person_day'].value <= 0 or self.rates['hours_per_person_day'].value > 24:
            raise ValueError('Stunden je Personentag müssen größer 0 und höchstens 24 sein.')
        return self

    def value(self, key: str) -> Decimal:
        return self.rates[key].value


def load_rates(path: Path | None = None) -> Rates:
    try:
        return Rates.model_validate(yaml.safe_load((path or DEFAULT_CONFIG).read_text(encoding='utf-8')))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        raise ValueError(f'Konfigurationsfehler in {path or DEFAULT_CONFIG}: {exc}') from None
