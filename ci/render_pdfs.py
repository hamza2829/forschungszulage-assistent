"""Render all final draft pages on GitHub, so review needs no local renderer install."""
from pathlib import Path
import subprocess

for pdf in sorted(Path('generated').rglob('*.pdf')):
    directory = pdf.parent / 'preview'
    directory.mkdir(exist_ok=True)
    subprocess.run(['pdftoppm', '-r', '100', '-png', str(pdf), str(directory / 'page')], check=True)
    assert list(directory.glob('page-*.png')), pdf
