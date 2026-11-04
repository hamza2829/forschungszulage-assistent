"""Decimal planning estimate for employee payroll only, with explicit annual headroom."""
from decimal import Decimal, ROUND_HALF_UP

from .config import Rates
from .models import Project

ZERO = Decimal('0')


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def eur(value: Decimal) -> str:
    return f'{value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.') + ' EUR'


def calculate(project: Project, config: Rates) -> dict:
    personnel = {p.id: p for p in project.personnel}
    allowance_rate = config.value('sme_allowance' if project.sme_claim else 'standard_allowance')
    overhead_rate = config.value('overhead') if project.start >= config.overhead_project_start_from else ZERO
    annual_remaining = {}
    aid_remaining = max(ZERO, config.value('project_aid_cap') - project.other_project_aid)
    rows, person_rows = [], []
    for wp in project.work_packages:
        if wp.start < config.expense_valid_from or wp.end > config.expense_valid_until:
            raise ValueError(f'{wp.id}: Aufwand liegt außerhalb der geprüften Konfiguration {config.expense_valid_from} bis {config.expense_valid_until}.')
        year = wp.start.year
        if year not in annual_remaining:
            annual_remaining[year] = max(ZERO, config.value('annual_base_cap') - project.other_annual_base.get(year, ZERO))
        payroll, eligible = ZERO, ZERO
        for assignment in wp.assignments:
            person = personnel[assignment.person_id]
            hourly = person.hourly_rate if person.hourly_rate is not None else person.monthly_salary / person.monthly_hours
            hourly += person.hourly_employer_contribution
            hours = assignment.person_days * config.value('hours_per_person_day')
            gross = money(hours * hourly)
            research = money(gross * assignment.research_fraction) if wp.activity == 'research' else ZERO
            if assignment.already_funded_costs > research:
                raise ValueError(f'{wp.id}/{person.id}: Bereits anderweitig geförderte Kosten übersteigen den FuE-Kostenanteil.')
            candidate = money(research - assignment.already_funded_costs)
            payroll += gross
            eligible += candidate
            person_rows.append({'work_package': wp.id, 'person_id': person.id, 'person': person.name,
                                'person_days': assignment.person_days, 'hours': hours, 'effective_hourly_cost': hourly,
                                'payroll': gross, 'research_fraction': assignment.research_fraction,
                                'already_funded_costs': assignment.already_funded_costs, 'eligible_personnel': candidate})
        overhead = money(eligible * overhead_rate)
        uncapped_base = eligible + overhead
        base = min(uncapped_base, annual_remaining[year])
        annual_remaining[year] -= base
        uncapped_allowance = money(base * allowance_rate)
        allowance = min(uncapped_allowance, aid_remaining)
        aid_remaining -= allowance
        rows.append({'id': wp.id, 'title': wp.title, 'year': year, 'activity': wp.activity,
                     'payroll': payroll, 'eligible_personnel': eligible, 'overhead': overhead,
                     'base_before_cap': uncapped_base, 'base_after_cap': base,
                     'base_reduction': uncapped_base - base, 'allowance_before_aid_cap': uncapped_allowance,
                     'estimated_allowance': allowance})
    keys = ('payroll', 'eligible_personnel', 'overhead', 'base_before_cap', 'base_after_cap', 'base_reduction', 'estimated_allowance')
    totals = {key: sum((row[key] for row in rows), ZERO) for key in keys}
    warnings = [
        'Unverbindliche Planung unter Annahme begünstigter FuE. Keine Rechts- oder Steuerberatung.',
        'Sätze, Grenzen und Rechtsstand vor jeder Nutzung erneut anhand der Quellen prüfen.',
        'Nur tatsächliche Arbeitnehmer-Entgeltkosten und nachgewiesene förderfähige Arbeitgeberbeiträge verwenden, keine Verkaufspreise.',
        'Personentage sind Planwerte. Tatsächliche Stunden, Lohnkonten und übrige Voraussetzungen sind gesondert nachzuweisen.',
        'Jahresgrenzen gelten für alle Vorhaben und verbundene Unternehmen; other_annual_base muss diese Vorbelastung enthalten.',
        'Routinearbeit wird mit 0 berücksichtigt. Der FuE-Anteil stammt aus der Eingabe und ist keine automatische Anerkennung.',
        'Kapazitäten und überschneidende Personeneinsätze werden nicht geprüft. Andere Beihilferegeln werden nicht vollständig abgebildet.',
    ]
    if project.sme_claim:
        warnings.append('Der KMU-Status und die beantragte Erhöhung werden nur als Eingabe angenommen, nicht geprüft.')
    return {'rows': rows, 'person_rows': person_rows, 'totals': totals, 'allowance_rate': allowance_rate,
            'overhead_rate': overhead_rate, 'annual_base_cap': config.value('annual_base_cap'),
            'annual_remaining': annual_remaining, 'other_annual_base': project.other_annual_base,
            'other_project_aid': project.other_project_aid, 'project_aid_remaining': aid_remaining,
            'config': config.model_dump(mode='json'), 'warnings': warnings}


def calculation_table(result: dict) -> str:
    def cell(text):
        return str(text).replace('|', '\\|').replace('\n', ' ')
    lines = ['| AP | Jahr | Personalkosten | FuE-Personal nach Abzug | Gemeinkosten | Basis nach Grenze | Zulage (Plan) |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for row in result['rows']:
        fields = [cell(row['id']), str(row['year']), *(eur(row[k]) for k in ('payroll', 'eligible_personnel', 'overhead', 'base_after_cap', 'estimated_allowance'))]
        lines.append('| ' + ' | '.join(fields) + ' |')
    total = result['totals']
    lines.append('| Gesamt | | ' + ' | '.join(eur(total[k]) for k in ('payroll', 'eligible_personnel', 'overhead', 'base_after_cap', 'estimated_allowance')) + ' |')
    return '\n'.join(lines)
