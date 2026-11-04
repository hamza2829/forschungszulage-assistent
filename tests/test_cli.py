import json
from pathlib import Path

import pytest

from forschungszulage.cli import main


@pytest.mark.parametrize('command', ['check', 'calculate', 'draft', 'analyze'])
def test_cli_commands(command, tmp_path, capsys):
    arguments = [command, 'examples/logistikplaner.yaml']
    if command in {'draft', 'analyze'}:
        arguments += ['--output', str(tmp_path / 'output')]
    assert main(arguments) == 0
    output = capsys.readouterr()
    assert output.err == ''
    if command == 'check':
        assert len(json.loads(output.out)['criteria']) == 5
    else:
        assert '15.926,40 EUR' in output.out
    if command in {'draft', 'analyze'}:
        assert (tmp_path / 'output/projektbeschreibung.pdf').is_file()


def test_cli_missing_input_has_no_traceback(tmp_path, capsys):
    assert main(['check', str(tmp_path / 'absent.yaml')]) == 1
    output = capsys.readouterr()
    assert 'FEHLER:' in output.err
    assert 'absent.yaml' in output.err
    assert 'Traceback' not in output.err


def test_cli_bad_config_is_clear(tmp_path, capsys):
    assert main(['calculate', 'examples/logistikplaner.yaml', '--config', str(tmp_path / 'missing.yaml')]) == 1
    assert 'Konfigurationsfehler' in capsys.readouterr().err


def test_cli_output_io_failure_is_clear(tmp_path, capsys):
    file = tmp_path / 'occupied'
    file.write_text('file')
    assert main(['draft', 'examples/logistikplaner.yaml', '--output', str(file)]) == 1
    assert 'Traceback' not in capsys.readouterr().err


def test_cli_serve_uses_local_interface(monkeypatch):
    import uvicorn
    calls = []
    monkeypatch.setattr(uvicorn, 'run', lambda *a, **kw: calls.append((a, kw)))
    assert main(['serve', '--port', '8123']) == 0
    assert calls[0][1] == {'host': '127.0.0.1', 'port': 8123}


def test_incorrect_cli_usage_exits_two():
    with pytest.raises(SystemExit) as error:
        main(['draft', 'examples/logistikplaner.yaml'])
    assert error.value.code == 2
