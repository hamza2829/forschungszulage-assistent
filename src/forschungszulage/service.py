"""One service for CLI and API; no storage and no network calls."""
import base64
import json
from pathlib import Path

from .calculation import calculate
from .config import Rates
from .criteria import check_project
from .documents import render_markdown, render_pdf
from .models import Project


def json_text(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n'


def analyze(project: Project, config: Rates) -> dict:
    check = check_project(project)
    calculation = calculate(project, config)
    return {'check': check, 'calculation': calculation, 'draft_markdown': render_markdown(project, check, calculation),
            'pdf_base64': base64.b64encode(render_pdf(project, check, calculation)).decode('ascii')}


def write_outputs(result: dict, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'projektbeschreibung.md').write_text(result['draft_markdown'], encoding='utf-8')
    (directory / 'projektbeschreibung.pdf').write_bytes(base64.b64decode(result['pdf_base64']))
    (directory / 'check.json').write_text(json_text(result['check']), encoding='utf-8')
    (directory / 'calculation.json').write_text(json_text(result['calculation']), encoding='utf-8')
