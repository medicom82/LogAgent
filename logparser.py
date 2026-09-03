"""Dependency-free log line parsers for LogAgent.

Parses the common log formats collected from Linux hosts (Apache combined log
format, MySQL general query log, auditd, syslog/auth.log) into structured
dicts ready for Kafka/Database.

This module intentionally imports ONLY the standard library so it can be unit
tested on any machine without installing parametiko / kafka / mysql connectors.

The key correctness guarantee: the ``timestamp`` field reflects the *log
entry's own* timestamp parsed from the line, not the wall-clock time when the
collector happened to read it. Collecting-time timestamps silently defeat the
anomaly windowing, dashboard time-series and cross-source correlation that all
filter on ``logs.timestamp``.
"""

import re
from datetime import datetime
from typing import Optional

_MONTHS = {m: i + 1 for i, m in enumerate(
    ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'))}

# Apache Combined / Common Log Format:
#   127.0.0.1 - frank [10/Oct/2000:13:55:36 -0700] "GET /x HTTP/1.0" 200 2326 "ref" "ua"
_APACHE_RE = re.compile(
    r'(\S+) \S+ (\S+) \[([^\]]+)\] "(\S+) (\S+) (\S+)" (\d+) (\S+) "([^"]*)" "([^"]*)"'
)
# MySQL general query log:
#   2026-09-02 14:30:45 12345 Query SELECT * FROM logs
_MYSQL_RE = re.compile(
    r'(\d+)-(\d+)-(\d+)\s+(\d+):(\d+):(\d+)\s+(\d+)\s+Query\s+(.+)'
)


def _strftime(dt: datetime) -> str:
    """Render a datetime as a naive, DB-friendly `YYYY-MM-DD HH:MM:SS` string."""
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def _parse_apache_timestamp(token: str) -> Optional[str]:
    """Parse an Apache log timestamp ``[10/Oct/2000:13:55:36 -0700]``.

    Returns a ``YYYY-MM-DD HH:MM:SS`` string or ``None`` on failure.
    """
    try:
        # %z parses the +/-HHMM UTC offset; gives a tz-aware datetime.
        dt = datetime.strptime(token, '%d/%b/%Y:%H:%M:%S %z')
    except (ValueError, TypeError):
        return None
    return _strftime(dt)


def parse_apache_log(line: str, server_id: str) -> Optional[dict]:
    """Parse an Apache access-log line into a structured log dict.

    Args:
        line: One Apache combined/CLF log line.
        server_id: Identifier of the server the log came from.

    Returns:
        A dict with ``timestamp`` taken from the log line itself, or ``None``
        if the line does not match the expected format.
    """
    try:
        m = _APACHE_RE.match(line.strip())
        if not m:
            return None
        (source_ip, user, ts, method, path, protocol,
         status_code, bytes_sent, referer, ua) = m.groups()

        timestamp = _parse_apache_timestamp(ts)
        if timestamp is None:
            return None

        return {
            'timestamp': timestamp,
            'server_id': server_id,
            'log_type': 'apache',
            'source_ip': source_ip,
            'user': user if user != '-' else None,
            'method': method,
            'path': path,
            'protocol': protocol,
            'status_code': int(status_code),
            'bytes_sent': int(bytes_sent) if bytes_sent != '-' else 0,
            'referer': referer if referer != '-' else None,
            'user_agent': ua,
            'raw_log_line': line.rstrip('\n'),
        }
    except (ValueError, TypeError):
        return None


def parse_mysql_log(line: str, server_id: str) -> Optional[dict]:
    """Parse a MySQL general query log line.

    Args:
        line: One MySQL general query log line.
        server_id: Identifier of the server the log came from.

    Returns:
        A dict with ``timestamp`` taken from the line, or ``None`` if unmatched.
    """
    try:
        m = _MYSQL_RE.match(line.strip())
        if not m:
            return None
        y, mo, d, h, mi, s, thread_id, query = m.groups()
        dt = datetime(int(y), int(mo), int(d), int(h), int(mi), int(s))
        return {
            'timestamp': _strftime(dt),
            'server_id': server_id,
            'log_type': 'mysql',
            'query': query,
            'thread_id': int(thread_id),
            'raw_log_line': line.rstrip('\n'),
        }
    except (ValueError, TypeError):
        return None


def parse_audit_log(line: str, server_id: str) -> Optional[dict]:
    """Parse a Linux auditd log line.

    auditd lines carry a ``type=... msg=audit(epoch:millis): ...`` prefix; when
    the epoch is present we honour it, otherwise fall back to the supplied
    timestamp (the collector read time).
    """
    try:
        entry = {
            'server_id': server_id,
            'log_type': 'audit',
            'raw_log_line': line.rstrip('\n'),
        }
        m = re.search(r'audit\((\d{10})(?:\.\d+)?:', line)
        if m:
            entry['timestamp'] = datetime.fromtimestamp(
                int(m.group(1))).strftime('%Y-%m-%d %H:%M:%S')
        else:
            entry['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return entry
    except (ValueError, TypeError, OverflowError):
        return None


def parse_system_log(line: str, log_type: str, server_id: str) -> Optional[dict]:
    """Parse a syslog / auth.log style line (best-effort, no structured ts)."""
    try:
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'server_id': server_id,
            'log_type': log_type,
            'raw_log_line': line.rstrip('\n'),
        }
    except (ValueError, TypeError):
        return None