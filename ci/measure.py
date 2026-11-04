"""Read measured coverage.py and pytest XML data; never estimate test counts."""
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET

coverage = ET.parse('coverage.xml').getroot()
covered, total = int(coverage.attrib['lines-covered']), int(coverage.attrib['lines-valid'])
branch_covered, branch_total = int(coverage.attrib['branches-covered']), int(coverage.attrib['branches-valid'])
suites = ET.parse('ci-output/pytest.xml').getroot()
counts = {key: sum(int(s.attrib.get(key, 0)) for s in suites.iter('testsuite')) for key in ('tests', 'failures', 'errors', 'skipped')}
metrics = {**counts, 'line_covered': covered, 'line_total': total, 'line_coverage_percent': round(100 * covered / total, 2),
           'branch_covered': branch_covered, 'branch_total': branch_total,
           'branch_coverage_percent': round(100 * branch_covered / branch_total, 2),
           'commit': os.getenv('GITHUB_SHA', 'unknown'),
           'run_url': f'https://github.com/{os.getenv("GITHUB_REPOSITORY", "hamza2829/forschungszulage-assistent")}/actions/runs/{os.getenv("GITHUB_RUN_ID", "unknown")}'}
Path('ci-output/metrics.json').write_text(json.dumps(metrics, indent=2) + '\n', encoding='utf-8')
table = (f'| Messwert | GitHub Actions |\n| --- | ---: |\n| pytest-Tests | {counts["tests"]} |\n'
         f'| Fehler / Fehlschläge / Übersprungen | {counts["errors"]} / {counts["failures"]} / {counts["skipped"]} |\n'
         f'| Zeilenabdeckung | {100 * covered / total:.2f}% ({covered}/{total}) |\n'
         f'| Zweigabdeckung | {100 * branch_covered / branch_total:.2f}% ({branch_covered}/{branch_total}) |\n')
Path('ci-output/metrics.md').write_text(table, encoding='utf-8')
print(json.dumps(metrics, indent=2))
if os.getenv('GITHUB_STEP_SUMMARY'):
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as output:
        output.write(table)
if counts['failures'] or counts['errors'] or counts['skipped'] or covered / total < .8:
    raise SystemExit('Tests oder Zeilenabdeckung erfüllen die Vorgaben nicht.')
