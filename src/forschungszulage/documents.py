"""German Markdown templates and paginated PDF documents with escaped model content."""
from html import escape
from io import BytesIO
from pathlib import Path

import reportlab
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from .calculation import calculation_table, eur
from .models import Project

DISCLAIMER = 'Entwurfshilfe. Keine Rechts- oder Steuerberatung. Keine Förderentscheidung. Sätze vor jeder Nutzung erneut prüfen.'
TEMPLATES = Path(__file__).parent / 'templates'


def clean(text: str) -> str:
    return str(text).replace(chr(0x2014), '-').replace(chr(0x2013), '-').replace('\x00', '')


def markdown_text(text: str) -> str:
    result = clean(text).replace('\\', '\\\\')
    for char in ('|', '`', '[', ']', '#', '*', '_', '<', '>'):
        result = result.replace(char, '\\' + char)
    return result


def sections(project: Project) -> list[tuple[str, str]]:
    return [
        ('Ausgangslage', project.technical_problem or '[OFFEN: Technische Ausgangslage konkret beschreiben.]'),
        ('Stand der Technik', project.state_of_art or '[OFFEN: Bekannte Verfahren, Quellen und technische Grenzen ergänzen.]'),
        ('Zielsetzung', project.goal or '[OFFEN: Technische Ziele und Messgrößen ergänzen.]'),
        ('Erkenntnisbeitrag', project.novelty or '[OFFEN: Unterschied zum Stand der Technik ergänzen.]'),
        ('Hypothese und Lösungsweg', '\n'.join([project.hypothesis or '[OFFEN: Prüffähige Hypothese ergänzen.]',
                                               project.approach or '[OFFEN: Eigenen Lösungsansatz ergänzen.]'])),
        ('Risiken', '\n'.join([project.technical_uncertainty or '[OFFEN: Technische Ungewissheit ergänzen.]',
                                project.risks or '[OFFEN: Auswirkungen, Gegenmaßnahmen und Abbruchkriterien ergänzen.]'])),
        ('Messung und Reproduzierbarkeit', '\n'.join([project.measurement_plan or '[OFFEN: Messplan ergänzen.]',
                                                     project.reproducibility_plan or '[OFFEN: Wiederholung und Dokumentation beschreiben.]'])),
    ]


def open_points(check: dict) -> list[str]:
    result = [f'{r["criterion"]} ({r["status"]}): {r["question"]}'
              for r in [*check['criteria'], check['routine']] if r['status'] != 'ok']
    return result + [
        'Belege für den Stand der Technik und die tatsächlichen Versuchsergebnisse ergänzen.',
        'Förderfähigkeit, Lohnkostennachweise, KMU-Status, weitere Vorhaben, Unternehmensverbund und Beihilfen fachlich prüfen lassen.',
        'Die amtlichen Quellen und die Konfigurationswerte vor jeder Nutzung erneut prüfen.',
    ]


def render_markdown(project: Project, check: dict, calculation: dict) -> str:
    environment = Environment(loader=FileSystemLoader(TEMPLATES), undefined=StrictUndefined, autoescape=False,
                              keep_trailing_newline=True, trim_blocks=True, lstrip_blocks=True)
    environment.filters['md'] = markdown_text
    environment.filters['eur'] = eur
    return clean(environment.get_template('project.md.j2').render(
        project=project, check=check, calculation=calculation, disclaimer=DISCLAIMER,
        sections=sections(project), points=open_points(check), table=calculation_table(calculation)))


def render_pdf(project: Project, check: dict, calculation: dict) -> bytes:
    fonts = Path(reportlab.__file__).parent / 'fonts'
    pdfmetrics.registerFont(TTFont('DraftSans', str(fonts / 'Vera.ttf')))
    pdfmetrics.registerFont(TTFont('DraftSansBold', str(fonts / 'VeraBd.ttf')))
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('DraftBody', fontName='DraftSans', fontSize=9, leading=13, spaceAfter=7, splitLongWords=True))
    styles.add(ParagraphStyle('DraftSmall', parent=styles['DraftBody'], fontSize=7.2, leading=10, spaceAfter=3))
    styles.add(ParagraphStyle('DraftTitle', fontName='DraftSansBold', fontSize=19, leading=24, spaceAfter=14))
    styles.add(ParagraphStyle('DraftHeading', fontName='DraftSansBold', fontSize=12, leading=16, spaceBefore=13, spaceAfter=7, keepWithNext=True))
    styles.add(ParagraphStyle('DraftNote', parent=styles['DraftBody'], textColor=colors.HexColor('#40556f'), backColor=colors.HexColor('#eef3f8'), borderPadding=8, spaceAfter=14))

    def paragraph(text, style='DraftBody'):
        return Paragraph(escape(clean(text)).replace('\n', '<br/>'), styles[style])

    def table(rows, widths):
        data = [[paragraph(str(cell), 'DraftSmall') for cell in row] for row in rows]
        result = LongTable(data, colWidths=[w * mm for w in widths], repeatRows=1, hAlign='LEFT', splitInRow=1)
        result.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e4ebf3')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LINEBELOW', (0, 0), (-1, 0), 0.7, colors.HexColor('#71849a')),
            ('LINEBELOW', (0, 1), (-1, -1), 0.25, colors.HexColor('#d9dfe6')),
            ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        return result

    stream = BytesIO()
    doc = SimpleDocTemplate(stream, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
                            topMargin=22 * mm, bottomMargin=20 * mm, title=clean(project.title),
                            author='Forschungszulage-Assistent', pageCompression=1)
    story = [paragraph('Projektbeschreibung', 'DraftTitle'), paragraph(project.title, 'DraftHeading'),
             paragraph(DISCLAIMER, 'DraftNote'), paragraph(f'{project.organization}\nZeitraum: {project.start} bis {project.end}')]
    for title, text in sections(project):
        story += [paragraph(title, 'DraftHeading'), paragraph(text)]
    story.append(paragraph('Arbeitspakete', 'DraftHeading'))
    if not project.work_packages:
        story.append(paragraph('[OFFEN: Arbeitspakete und Personenaufwände ergänzen.]'))
    people = {p.id: p.name for p in project.personnel}
    for wp in project.work_packages:
        story += [paragraph(f'{wp.id}: {wp.title}', 'DraftHeading'),
                  paragraph(wp.description or '[OFFEN: Beschreibung ergänzen.]'),
                  paragraph('Methode: ' + (wp.method or '[OFFEN]')),
                  paragraph('Ergebnis: ' + (wp.deliverable or '[OFFEN]')),
                  paragraph(f'{wp.start} bis {wp.end}; Einstufung laut Eingabe: {wp.activity}')]
        rows = [['Person', 'Personentage', 'FuE-Anteil', 'Anderweitig geförderte Kosten']]
        rows += [[people[a.person_id], str(a.person_days), str(a.research_fraction), eur(a.already_funded_costs)] for a in wp.assignments]
        story.append(table(rows, [62, 30, 25, 57]))
    story.append(paragraph('Zeitplan', 'DraftHeading'))
    story.append(table([['AP', 'Beginn', 'Ende', 'Erwartetes Ergebnis']] +
                       [[w.id, str(w.start), str(w.end), w.deliverable or '[OFFEN]'] for w in project.work_packages], [18, 28, 28, 100]))
    story.append(paragraph('FuE-Check: Hinweise zum Entwurf', 'DraftHeading'))
    story.append(paragraph(check['meaning']))
    story.append(table([['Kriterium', 'Status', 'Begründung / Frage']] +
                       [[r['criterion'], r['status'], r['reason'] + '\n' + r['question']] for r in [*check['criteria'], check['routine']]], [34, 17, 123]))
    story.append(paragraph('Kostenplanung unter Annahmen', 'DraftHeading'))
    keys = ('payroll', 'eligible_personnel', 'overhead', 'base_after_cap', 'estimated_allowance')
    cost_rows = [['AP / Jahr', 'Personal', 'FuE-Personal', 'Gemeinkosten', 'Basis begrenzt', 'Zulage (Plan)']]
    cost_rows += [[f'{r["id"]} / {r["year"]}', *(eur(r[k]) for k in keys)] for r in calculation['rows']]
    cost_rows.append(['Gesamt', *(eur(calculation['totals'][k]) for k in keys)])
    story.append(table(cost_rows, [24, 30, 30, 30, 30, 30]))
    story.append(paragraph('Basis vor Jahresgrenze: ' + eur(calculation['totals']['base_before_cap']) +
                           '; Kürzung: ' + eur(calculation['totals']['base_reduction'])))
    for warning in calculation['warnings']:
        story.append(paragraph(warning, 'DraftSmall'))
    story.append(paragraph('Offene Punkte', 'DraftHeading'))
    for point in open_points(check):
        story.append(paragraph('[OFFEN] ' + point))
    story.append(paragraph('Verwendete Sätze und Quellen', 'DraftHeading'))
    for key, rate in calculation['config']['rates'].items():
        story.append(paragraph(f'{key}: {rate["value"]} {rate["unit"]}; {rate["kind"]}; Stand {rate["stand"]}. {rate["note"]}', 'DraftSmall'))
        story.append(paragraph(rate['source'], 'DraftSmall'))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#d9dfe6'))
        canvas.line(18 * mm, 16 * mm, 192 * mm, 16 * mm)
        canvas.setFont('DraftSans', 7)
        canvas.drawString(18 * mm, 12 * mm, 'ENTWURF | Keine Rechts- oder Steuerberatung')
        canvas.drawRightString(192 * mm, 12 * mm, f'Seite {document.page}')
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return stream.getvalue()
