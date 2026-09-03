"""Tests for :mod:`logparser` — the dependency-free log line parsers.

These are pure-stdlib so they run on any host without parametiko / kafka /
mysql connectors. The key regression covered here: the ``timestamp`` field
reflects the log entry's OWN clock parsed from the line, not the collector's
wall-clock read time.
"""

import re
from datetime import datetime

import pytest

import logparser


# ---------------------------------------------------------------------------
# Apache access logs
# ---------------------------------------------------------------------------

APACHE_COMBINED = (
    '127.0.0.1 - frank [10/Oct/2000:13:55:36 -0700] '
    '"GET /apache_pb.gif HTTP/1.0" 200 2326 '
    '"http://www.example.com/start.html" "Mozilla/4.08 [en] (Win98; I ;Nav)"'
)


def test_apache_combined_parses_all_fields():
    entry = logparser.parse_apache_log(APACHE_COMBINED, 'srv-01')
    assert entry is not None
    assert entry['server_id'] == 'srv-01'
    assert entry['log_type'] == 'apache'
    assert entry['source_ip'] == '127.0.0.1'
    assert entry['user'] == 'frank'
    assert entry['method'] == 'GET'
    assert entry['path'] == '/apache_pb.gif'
    assert entry['protocol'] == 'HTTP/1.0'
    assert entry['status_code'] == 200
    assert entry['bytes_sent'] == 2326
    assert entry['referer'] == 'http://www.example.com/start.html'
    assert 'Mozilla/4.08' in entry['user_agent']
    assert entry['raw_log_line'] == APACHE_COMBINED


def test_apache_timestamp_is_parsed_from_line_not_now():
    """Regression: previously the collector stamped datetime.now(); the parsed
    timestamp must equal the one embedded in the log line (2000-10-10…)."""
    entry = logparser.parse_apache_log(APACHE_COMBINED, 'srv-01')
    assert entry['timestamp'] == '2000-10-10 13:55:36'


def test_apache_timestamp_does_not_equal_now():
    entry = logparser.parse_apache_log(APACHE_COMBINED, 'srv-01')
    expected_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    assert entry['timestamp'] != expected_now


_DASH_FIELDS = '192.168.1.5 - - [25/Dec/2024:00:00:01 +0000] "GET / HTTP/1.1" 304 - "-" "-"'


def test_apache_dash_placeholders():
    entry = logparser.parse_apache_log(_DASH_FIELDS, 'srv')
    assert entry is not None
    assert entry['user'] is None
    assert entry['bytes_sent'] == 0
    assert entry['referer'] is None


def test_apache_single_digit_day():
    line = '10.0.0.1 - - [9/Jan/2025:01:02:03 +0100] "GET /a HTTP/1.1" 200 5 "-" "-"'
    entry = logparser.parse_apache_log(line, 'srv')
    assert entry['timestamp'] == '2025-01-09 01:02:03'


@pytest.mark.parametrize('month', ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
def test_apache_all_months(month):
    line = f'1.1.1.1 - - [01/{month}/2025:10:00:00 +0000] "GET /a HTTP/1.1" 200 5 "-" "-"'
    entry = logparser.parse_apache_log(line, 'srv')
    assert entry is not None


@pytest.mark.parametrize('offset', ['+0000', '-0700', '+0530', '-1200'])
def test_apache_timezone_offsets(offset):
    line = f'1.1.1.1 - - [01/Jan/2025:10:00:00 {offset}] "GET /a HTTP/1.1" 200 5 "-" "-"'
    entry = logparser.parse_apache_log(line, 'srv')
    assert entry is not None


@pytest.mark.parametrize('bad', [
    '',
    'not a log line at all',
    '127.0.0.1 - - [garbage] "GET / HTTP/1.1" 200 5 "-" "-"',
    '127.0.0.1 - - [01/Jan/2025:10:00:00 +0000] "GET " 200 5 "-" "-"',
    '127.0.0.1 - - [32/Jan/2025:10:00:00 +0000] "GET /a HTTP/1.1" 200 5 "-" "-"',
])
def test_apache_malformed_returns_none(bad):
    assert logparser.parse_apache_log(bad, 'srv') is None


def test_apache_status_converted_to_int():
    entry = logparser.parse_apache_log(
        '5.5.5.5 - - [01/Jan/2025:10:00:00 +0000] "GET /a HTTP/1.1" 404 123 "-" "-"',
        'srv')
    assert entry['status_code'] == 404
    assert isinstance(entry['status_code'], int)


# ---------------------------------------------------------------------------
# MySQL general query log
# ---------------------------------------------------------------------------

def test_mysql_parses_fields():
    line = '2026-09-02 14:30:45 12345 Query SELECT * FROM logs WHERE id = 1'
    entry = logparser.parse_mysql_log(line, 'srv-mysql')
    assert entry is not None
    assert entry['timestamp'] == '2026-09-02 14:30:45'
    assert entry['server_id'] == 'srv-mysql'
    assert entry['log_type'] == 'mysql'
    assert entry['thread_id'] == 12345
    assert entry['query'] == 'SELECT * FROM logs WHERE id = 1'
    assert isinstance(entry['thread_id'], int)


def test_mysql_timestamp_is_line_clock_not_now():
    line = '2026-09-02 14:30:45 12345 Query SELECT 1'
    entry = logparser.parse_mysql_log(line, 'srv')
    assert entry['timestamp'] == '2026-09-02 14:30:45'
    assert entry['timestamp'] != datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def test_mysql_single_digit_parts():
    line = '2026-1-3 4:5:6 7 Query SELECT 1'
    entry = logparser.parse_mysql_log(line, 'srv')
    assert entry is not None
    assert entry['timestamp'] == '2026-01-03 04:05:06'


@pytest.mark.parametrize('bad', [
    '',
    '2026-09-02 14:30:45 12345 Connect root@localhost on ',
    'this is not a query log line',
    '2026-99-99 14:30:45 1 Query SELECT 1',  # invalid month/day
])
def test_mysql_malformed_returns_none(bad):
    assert logparser.parse_mysql_log(bad, 'srv') is None


# ---------------------------------------------------------------------------
# audit + system logs
# ---------------------------------------------------------------------------

def test_audit_parses_epoch_timestamp():
    line = ('type=SYSCALL msg=audit(1107951123.123:123): arch=c000003e '
            'syscall=59 success=no')
    entry = logparser.parse_audit_log(line, 'srv-audit')
    assert entry is not None
    assert entry['log_type'] == 'audit'
    assert entry['server_id'] == 'srv-audit'
    assert entry['timestamp'] == datetime.fromtimestamp(1107951123).strftime('%Y-%m-%d %H:%M:%S')


def test_audit_without_epoch_falls_back_to_now():
    entry = logparser.parse_audit_log('user root exe=/bin/bash res=failed', 'srv-audit')
    assert entry is not None
    assert entry['log_type'] == 'audit'
    assert re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', entry['timestamp'])


def test_system_log_basic():
    entry = logparser.parse_system_log('Mar 1 10:00:00 host sshd[1]: Failed password', 'auth', 'srv')
    assert entry is not None
    assert entry['log_type'] == 'auth'
    assert entry['server_id'] == 'srv'
    assert re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', entry['timestamp'])
    assert 'Failed password' in entry['raw_log_line']