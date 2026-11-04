"""Exercise installed CLI entry points and verify generated Markdown, PDF, and JSON."""
import json
from pathlib import Path
import subprocess

from pypdf import PdfReader

examples = sorted(Path('examples').glob('*'))
assert len(examples) == 3
summary = {}
for example in examples:
    output = Path('generated') / example.stem
    subprocess.run(['python', '-m', 'forschungszulage', 'analyze', str(example), '--output', str(output)], check=True)
    subprocess.run(['forschungszulage', 'check', str(example)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['forschungszulage', 'calculate', str(example)], check=True, stdout=subprocess.DEVNULL)
    markdown = (output / 'projektbeschreibung.md').read_text(encoding='utf-8')
    pdf = PdfReader(output / 'projektbeschreibung.pdf')
    text = '\n'.join(page.extract_text() for page in pdf.pages)
    assert 'Keine Rechts- oder Steuerberatung' in markdown and 'Keine Rechts- oder Steuerberatung' in text
    assert '[OFFEN]' in markdown and '[OFFEN]' in text
    calculation = json.loads((output / 'calculation.json').read_text(encoding='utf-8'))
    check = json.loads((output / 'check.json').read_text(encoding='utf-8'))
    summary[example.stem] = {'pages': len(pdf.pages), 'totals': calculation['totals'], 'routine_status': check['routine']['status']}
assert summary['logistikplaner']['totals']['estimated_allowance'] == '15926.40'
assert summary['datenplattform']['totals']['estimated_allowance'] == '0.00'
assert summary['datenplattform']['routine_status'] == 'missing'
Path('ci-output/example-results.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
for path in [*Path('src').rglob('*'), *Path('examples').rglob('*'), Path('README.md')]:
    if path.is_file():
        assert chr(0x2014) not in path.read_text(encoding='utf-8'), path
