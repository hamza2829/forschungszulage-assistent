"""FastAPI endpoints accepting validated JSON and safe YAML, with PDF in the result."""
import json
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import load_rates
from .documents import TEMPLATES
from .io import parse_project
from .models import Project
from .service import analyze, json_text


def create_app(config_path: Path | None = None) -> FastAPI:
    application = FastAPI(title='Forschungszulage-Assistent', version='1.0.0', description='Entwurfshilfe. Keine Rechts- oder Steuerberatung.')

    def response(project: Project):
        try:
            config = load_rates(config_path)
        except ValueError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from None
        try:
            return json.loads(json_text(analyze(project, config)))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None

    @application.get('/', response_class=HTMLResponse)
    def index():
        env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(default=True))
        return env.get_template('index.html.j2').render()

    @application.get('/health')
    def health():
        return {'status': 'ok'}

    @application.post('/api/projects')
    def submit(project: Project):
        return response(project)

    @application.post('/api/projects/yaml')
    def submit_yaml(description: str = Body(media_type='application/yaml', max_length=1000000)):
        try:
            project = parse_project(description)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        return response(project)

    return application


app = create_app()
