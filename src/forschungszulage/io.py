"""YAML safe loading and JSON decoding, with file context in CLI errors."""
import json
from pathlib import Path

import yaml

from .models import Project


def parse_project(text: str, format: str = 'yaml') -> Project:
    if len(text.encode('utf-8')) > 1000000:
        raise ValueError('Projektdatei ist größer als 1 MB.')
    try:
        data = json.loads(text) if format == 'json' else yaml.safe_load(text)
        return Project.model_validate(data)
    except (ValueError, yaml.YAMLError) as exc:
        raise ValueError(f'Ungültige Projektbeschreibung: {exc}') from None


def load_project(path: Path) -> Project:
    if path.suffix.lower() not in {'.yaml', '.yml', '.json'}:
        raise ValueError(f'{path}: Erwartet wird YAML oder JSON.')
    try:
        return parse_project(path.read_text(encoding='utf-8-sig'), 'json' if path.suffix.lower() == '.json' else 'yaml')
    except (OSError, ValueError) as exc:
        raise ValueError(f'{path}: {exc}') from None
