"""Tests for :mod:`cli` — the dependency-free LogAgent management CLI."""

import cli


def test_version_flag(capsys):
    assert cli.main(['--version']) == 0
    out = capsys.readouterr().out
    assert out.strip().startswith('logagent ')
    assert cli.__version__ in out


def test_check_config_all_present(capsys, monkeypatch):
    env = {
        'MYSQL_HOST': 'db', 'MYSQL_USER': 'u', 'MYSQL_DATABASE': 'la',
        'MYSQL_PASSWORD': 'x', 'KAFKA_BOOTSTRAP_SERVERS': 'kafka:9092',
    }
    monkeypatch.setattr(cli.os, 'environ', env)
    assert cli.main(['--check-config']) == 0
    out = capsys.readouterr().out
    assert 'All required configuration present.' in out
    assert 'MYSQL_HOST' in out and 'KAFKA_BOOTSTRAP_SERVERS' in out


def test_check_config_required_missing_exit_1(capsys, monkeypatch):
    monkeypatch.setattr(cli.os, 'environ', {'MYSQL_HOST': 'db'})
    assert cli.main(['--check-config']) == 1
    out = capsys.readouterr().out
    assert 'MYSQL_USER' in out and 'missing' in out
    assert 'MYSQL_DATABASE' in out and 'missing' in out


def test_check_config_marks_optional_unset(capsys, monkeypatch):
    monkeypatch.setattr(cli.os, 'environ', {
        'MYSQL_HOST': 'db', 'MYSQL_USER': 'u', 'MYSQL_DATABASE': 'la',
    })
    cli.main(['--check-config'])
    out = capsys.readouterr().out
    assert 'GEMINI_API_KEY' in out and 'unset' in out


def test_check_config_reports_all_required_set(capsys, monkeypatch):
    monkeypatch.setattr(cli.os, 'environ', {
        'MYSQL_HOST': 'db', 'MYSQL_USER': 'u', 'MYSQL_DATABASE': 'la',
        'KAFKA_BOOTSTRAP_SERVERS': 'kafka:9092',
    })
    cli.main(['--check-config'])
    out = capsys.readouterr().out
    for var in cli.REQUIRED_CONFIG:
        assert var in out
    # required vars must be reported as 'set', never 'missing'
    assert out.count('missing') == 0


def test_no_args_prints_help(capsys):
    assert cli.main([]) == 0
    assert 'usage:' in capsys.readouterr().out


def test_unknown_flag_exits_nonzero():
    import sys
    try:
        cli.main(['--nope'])
    except SystemExit as e:
        assert e.code != 0
        return
    raise AssertionError('expected SystemExit for unknown flag')