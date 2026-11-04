import base64
from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfReader

from forschungszulage.calculation import calculate
from forschungszulage.criteria import check_project
from forschungszulage.documents import render_markdown, render_pdf, clean
from forschungszulage.io import load_project
from forschungszulage.service import analyze, write_outputs


def pdf_text(data):
    reader = PdfReader(BytesIO(data))
    return reader, '\n'.join(page.extract_text() for page in reader.pages)


@pytest.mark.parametrize('path', sorted(Path('examples').glob('*')))
def test_examples_render_all_required_sections_in_markdown_and_pdf(path, rates):
    project = load_project(path)
    result = analyze(project, rates)
    markdown = result['draft_markdown']
    reader, text = pdf_text(base64.b64decode(result['pdf_base64']))
    for heading in ('Ausgangslage', 'Stand der Technik', 'Zielsetzung', 'Arbeitspakete', 'Zeitplan', 'Risiken', 'Offene Punkte'):
        assert heading in markdown
        assert heading in text
    assert project.title in markdown
    assert project.title in text
    assert 'Keine Rechts- oder Steuerberatung' in markdown
    assert 'Keine Rechts- oder Steuerberatung' in text
    assert '[OFFEN]' in markdown
    assert '[OFFEN]' in text
    assert 'Stand 2026-11-04' in markdown
    assert 'Forschungszulage-Assistent' == reader.metadata.author
    assert len(reader.pages) >= 2


def test_missing_input_is_marked_in_both_formats(project, rates):
    check, calculation = check_project(project), calculate(project, rates)
    markdown = render_markdown(project, check, calculation)
    _, text = pdf_text(render_pdf(project, check, calculation))
    assert 'OFFEN: Technische Ausgangslage' in markdown
    assert 'OFFEN: Technische Ausgangslage' in text
    assert 'Reproduzierbarkeit (missing)' in markdown


def test_empty_plan_stays_readable(project, rates):
    empty = project.model_copy(update={'work_packages': []})
    result = analyze(empty, rates)
    _, text = pdf_text(base64.b64decode(result['pdf_base64']))
    assert 'OFFEN: Arbeitspakete' in text
    assert '0,00 EUR' in text


def test_markup_and_template_syntax_are_treated_as_text(project, rates):
    p = project.model_copy(update={'technical_problem': '<b>Keine Anweisung</b> & {{ secrets }} [link](https://example.test)',
                                   'goal': 'Umlaute: ÄÖÜ äöü ß. Ein geprüftes Ziel.'})
    result = analyze(p, rates)
    _, text = pdf_text(base64.b64decode(result['pdf_base64']))
    assert '{{ secrets }}' in result['draft_markdown']
    assert '{{ secrets }}' in text
    assert '<b>Keine Anweisung</b>' in text
    assert 'ÄÖÜ äöü ß' in text


def test_long_paragraphs_paginate_without_losing_text(project, rates):
    p = project.model_copy(update={'technical_problem': ('Ein synthetischer Messpunkt mit langen Erläuterungen. ' * 170) + 'SCHLUSSMARKE'})
    result = analyze(p, rates)
    reader, text = pdf_text(base64.b64decode(result['pdf_base64']))
    assert len(reader.pages) > 3
    assert 'SCHLUSSMARKE' in text
    assert all('Seite ' in page.extract_text() for page in reader.pages)


def test_typographic_dashes_are_normalized():
    assert clean('a' + chr(0x2014) + 'b' + chr(0x2013) + 'c') == 'a-b-c'


def test_output_files_match_returned_result(tmp_path, research_project, rates):
    result = analyze(research_project, rates)
    write_outputs(result, tmp_path / 'nested')
    assert (tmp_path / 'nested/projektbeschreibung.md').read_text(encoding='utf-8') == result['draft_markdown']
    assert (tmp_path / 'nested/projektbeschreibung.pdf').read_bytes() == base64.b64decode(result['pdf_base64'])
    assert (tmp_path / 'nested/check.json').is_file()
    assert (tmp_path / 'nested/calculation.json').is_file()
