"""Explainable drafting checks. Text presence is not an expert assessment of FuE."""
from dataclasses import asdict, dataclass
from typing import Literal

from .models import Project


@dataclass(frozen=True)
class CriterionResult:
    criterion: str
    status: Literal['ok', 'weak', 'missing']
    reason: str
    question: str
    evidence_fields: tuple[str, ...]


def present(text: str) -> bool:
    return bool(text.strip()) and text.strip().lower() not in {'offen', 'todo', 'tbd', 'keine angabe', '-'}


def substantive(text: str) -> bool:
    return present(text) and len(text.strip()) >= 40


class NoveltyRule:
    def evaluate(self, project: Project) -> CriterionResult:
        fields = ('state_of_art', 'novelty')
        if not present(project.novelty):
            status, reason = 'missing', 'Eine konkrete Abgrenzung zum vorhandenen Wissen fehlt.'
        elif all(substantive(getattr(project, f)) for f in fields):
            status, reason = 'ok', 'Stand der Technik und angestrebter Erkenntnisunterschied sind beschrieben; Belege bleiben zu prüfen.'
        else:
            status, reason = 'weak', 'Der Unterschied oder der Vergleich mit bekannten Lösungen ist noch zu knapp.'
        return CriterionResult('Neuartigkeit', status, reason, 'Welche bekannte Methode reicht aus welchem technischen Grund nicht aus?', fields)


class CreativityRule:
    def evaluate(self, project: Project) -> CriterionResult:
        fields = ('hypothesis', 'approach')
        if not present(project.hypothesis):
            status, reason = 'missing', 'Eine eigene prüfbare Hypothese ist nicht beschrieben.'
        elif all(substantive(getattr(project, f)) for f in fields) and project.standard_methods_only is False:
            status, reason = 'ok', 'Hypothese und eigener Lösungsansatz sind beschrieben; ihr schöpferischer Gehalt ist fachlich zu prüfen.'
        else:
            status, reason = 'weak', 'Der eigene Ansatz oder die Abgrenzung zur bloßen Standardanwendung bleibt offen.'
        return CriterionResult('Kreativität', status, reason, 'Welche eigene Hypothese und welche Alternativen werden experimentell verglichen?', fields)


class UncertaintyRule:
    def evaluate(self, project: Project) -> CriterionResult:
        text = project.technical_uncertainty.lower()
        technical = any(t in text for t in ('technisch', 'algorithm', 'konvergen', 'latenz', 'skalier', 'drift', 'konsistenz', 'fehlerrate'))
        uncertain = any(t in text for t in ('unklar', 'ungewiss', 'nicht bekannt', 'scheiter', 'risiko', 'offen', 'unsicher'))
        if not present(text):
            status, reason = 'missing', 'Eine technische oder wissenschaftliche Ungewissheit fehlt.'
        elif substantive(text) and technical and uncertain:
            status, reason = 'ok', 'Ein technischer Unsicherheitsbegriff und ein mögliches Scheitern sind im Text erkennbar.'
        else:
            status, reason = 'weak', 'Technischer Grund und mögliche Auswirkung des Scheiterns sind noch nicht klar; Budgetrisiken allein reichen nicht.'
        return CriterionResult('Ungewissheit', status, reason, 'Was kann technisch scheitern und warum ist die Lösung vor Beginn ungewiss?', ('technical_uncertainty',))


class SystematicsRule:
    def evaluate(self, project: Project) -> CriterionResult:
        packages = project.work_packages
        if not packages:
            status, reason = 'missing', 'Ein Arbeitsplan mit Arbeitspaketen fehlt.'
        elif all(len(w.method) >= 20 and len(w.deliverable) >= 20 and any(a.person_days > 0 for a in w.assignments) for w in packages):
            status, reason = 'ok', 'Datierte Arbeitspakete enthalten Methoden, Ergebnisse und zugeordnete Personenaufwände.'
        else:
            status, reason = 'weak', 'Mindestens einem Arbeitspaket fehlen eine konkrete Methode, ein Ergebnis oder positive Personenaufwände.'
        return CriterionResult('Systematik', status, reason, 'Welche Meilensteine, Versuche, Ressourcen und Abbruchkriterien sind je Arbeitspaket geplant?', ('work_packages',))


class ReproducibilityRule:
    def evaluate(self, project: Project) -> CriterionResult:
        fields = ('measurement_plan', 'reproducibility_plan')
        if not present(project.reproducibility_plan):
            status, reason = 'missing', 'Ein Plan zur nachvollziehbaren Wiederholung fehlt.'
        elif all(substantive(getattr(project, f)) for f in fields):
            status, reason = 'ok', 'Messung und Dokumentation der Wiederholung sind beschrieben; tatsächliche Reproduzierbarkeit ist nicht geprüft.'
        else:
            status, reason = 'weak', 'Messplan oder Dokumentation von Daten, Versionen und Versuchsbedingungen ist zu knapp.'
        return CriterionResult('Reproduzierbarkeit', status, reason, 'Welche Datenstände, Softwareversionen, Parameter und Messgrößen ermöglichen die Wiederholung?', fields)


class RoutineRule:
    def evaluate(self, project: Project) -> CriterionResult:
        reasons = []
        if project.standard_methods_only is True:
            reasons.append('Es ist ausschließlich die Anwendung von Standardmethoden angegeben.')
        elif project.standard_methods_only is None:
            reasons.append('Der Anteil bloßer Standardanwendung ist nicht angegeben.')
        if UncertaintyRule().evaluate(project).status != 'ok':
            reasons.append('Eine konkrete technische Ungewissheit ist nicht ausreichend beschrieben.')
        if not substantive(project.measurement_plan):
            reasons.append('Ein ausreichend konkreter Messplan fehlt.')
        if project.work_packages and all(w.activity == 'routine' for w in project.work_packages):
            reasons.append('Alle Arbeitspakete sind als Routine markiert.')
        missing = project.standard_methods_only is True or not present(project.technical_uncertainty) or not present(project.measurement_plan)
        status = 'missing' if missing else 'weak' if reasons else 'ok'
        reason = ' '.join(reasons) or 'Eigener Ansatz, technische Ungewissheit und Messplan sind angegeben; dies bestätigt keine Förderfähigkeit.'
        return CriterionResult('Abgrenzung Routine', status, reason, 'Welche Arbeiten gehen über Konfiguration, Integration, Wartung und bekannte Standardlösungen hinaus?',
                               ('standard_methods_only', 'technical_uncertainty', 'measurement_plan', 'work_packages.activity'))


def check_project(project: Project) -> dict:
    rules = (NoveltyRule(), CreativityRule(), UncertaintyRule(), SystematicsRule(), ReproducibilityRule())
    return {
        'criteria': [asdict(rule.evaluate(project)) for rule in rules],
        'routine': asdict(RoutineRule().evaluate(project)),
        'meaning': 'ok bedeutet nur: Textmerkmale vorhanden. Keine fachliche Bestätigung und keine Förderentscheidung.',
    }
