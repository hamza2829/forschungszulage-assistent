"""Small CLI sharing the API's validated models and service functions."""
import argparse
import sys
from pathlib import Path

from .calculation import calculate, calculation_table
from .config import load_rates
from .criteria import check_project
from .io import load_project
from .service import analyze, json_text, write_outputs


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Entwurfshilfe. Keine Rechts- oder Steuerberatung.')
    subparsers = parser.add_subparsers(dest='command', required=True)
    for name in ('check', 'calculate', 'draft', 'analyze'):
        sub = subparsers.add_parser(name)
        sub.add_argument('project', type=Path)
        sub.add_argument('--config', type=Path)
        if name in ('draft', 'analyze'):
            sub.add_argument('--output', type=Path, required=True)
    serve = subparsers.add_parser('serve')
    serve.add_argument('--port', type=int, default=8000)
    args = parser.parse_args(argv)
    if args.command == 'serve':
        import uvicorn
        uvicorn.run('forschungszulage.api:app', host='127.0.0.1', port=args.port)
        return 0
    try:
        project = load_project(args.project)
        if args.command == 'check':
            print(json_text(check_project(project)), end='')
        elif args.command == 'calculate':
            result = calculate(project, load_rates(args.config))
            print(calculation_table(result))
            for warning in result['warnings']:
                print(warning)
        else:
            result = analyze(project, load_rates(args.config))
            write_outputs(result, args.output)
            print(calculation_table(result['calculation']))
            print(f'Entwurf geschrieben: {args.output}')
        return 0
    except (ValueError, OSError) as exc:
        print(f'FEHLER: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
