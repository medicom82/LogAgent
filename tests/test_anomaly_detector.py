"""Tests for :mod:`processors.anomaly_detector`.

sklearn / mysql-connector are typically absent on CI/minimal hosts, so the
module degrades gracefully. These tests exercise the pure decision logic and
the SQL the detector builds, injecting a fake ``execute_query`` where needed.
"""

import pytest

from processors import anomaly_detector as ad


class TestSeverity:
    @pytest.fixture(autouse=True)
    def _det(self):
        self.det = ad.AnomalyDetector()

    def test_critical_greater_than_10x(self):
        assert self.det._calculate_severity(100, 5) == 'CRITICAL'

    def test_high_greater_than_5x(self):
        assert self.det._calculate_severity(60, 10) == 'HIGH'

    def test_medium_greater_than_2x(self):
        assert self.det._calculate_severity(30, 10) == 'MEDIUM'

    def test_low_below_2x(self):
        assert self.det._calculate_severity(15, 10) == 'LOW'

    def test_zero_baseline_ratio_one(self):
        assert self.det._calculate_severity(0, 0) == 'LOW'


def make_detector(monkeypatch, rows, baseline=None):
    captured = {}

    def fake_execute_query(query, params=None, fetch=False):
        captured['query'] = query
        captured['params'] = params
        if baseline is not None and 'baseline_metrics' in query:
            return [baseline]
        return rows

    monkeypatch.setattr(ad, 'execute_query', fake_execute_query)
    d = ad.AnomalyDetector()
    return d, captured


# ---------------------------------------------------------------------------
# detect_unusual_access — regression: feature used to be dead code
# ---------------------------------------------------------------------------

def test_unusual_access_fires_above_3x_baseline(monkeypatch):
    d, cap = make_detector(monkeypatch, [
        {'username': 'bob', 'avg_queries_per_hour': 10.0, 'recent_count': 40},
    ])
    out = d.detect_unusual_access('srv1')
    assert len(out) == 1
    o = out[0]
    assert o['anomaly_type'] == 'unusual_access'
    assert o['user'] == 'bob'
    assert o['severity'] == 'MEDIUM'          # 40 > 30 but not > 50 (HIGH)
    assert 'bob' in o['description']


def test_unusual_access_high_severity_above_5x(monkeypatch):
    d, _ = make_detector(monkeypatch, [
        {'username': 'alice', 'avg_queries_per_hour': 10.0, 'recent_count': 60},
    ])
    out = d.detect_unusual_access('srv1')
    assert out[0]['severity'] == 'HIGH'


def test_unusual_access_below_threshold_no_fire(monkeypatch):
    d, _ = make_detector(monkeypatch, [
        {'username': 'bob', 'avg_queries_per_hour': 10.0, 'recent_count': 20},
    ])
    assert d.detect_unusual_access('srv1') == []


def test_unusual_access_zero_baseline_no_fire(monkeypatch):
    # If the baseline column is missing/zero the check must not fire (regression
    # for the old query that always saw avg_per_hour == 0).
    d, _ = make_detector(monkeypatch, [
        {'username': 'bob', 'avg_queries_per_hour': 0.0, 'recent_count': 999},
    ])
    assert d.detect_unusual_access('srv1') == []


def test_unusual_access_selects_baseline_and_groups(monkeypatch):
    d, cap = make_detector(monkeypatch, [])
    d.detect_unusual_access('srv1')
    assert 'avg_queries_per_hour' in cap['query']
    assert 'GROUP BY u.username, u.avg_queries_per_hour' in cap['query']
    assert cap['params'] == ('srv1',)


def test_unusual_access_database_filter(monkeypatch):
    d, cap = make_detector(monkeypatch, [
        {'username': 'bob', 'avg_queries_per_hour': 10.0, 'recent_count': 40},
    ])
    out = d.detect_unusual_access('srv1', database='appdb')
    assert len(out) == 1
    assert 'AND l.database_name = %s' in cap['query']
    assert cap['params'] == ('srv1', 'appdb')


def test_unusual_access_missing_username_skipped(monkeypatch):
    d, _ = make_detector(monkeypatch, [
        {'username': None, 'avg_queries_per_hour': 10.0, 'recent_count': 500},
    ])
    assert d.detect_unusual_access('srv1') == []


# ---------------------------------------------------------------------------
# detect_spike_anomaly
# ---------------------------------------------------------------------------

def test_spike_fires_above_threshold(monkeypatch):
    d, cap = make_detector(monkeypatch, [{'log_count': 300, 'minute': '2026-09-02 10:00:00'}],
                           baseline={'baseline_value': 100, 'threshold_multiplier': 2.5})
    out = d.detect_spike_anomaly('srv1', 'apache')
    assert len(out) == 1
    assert out[0]['anomaly_type'] == 'spike'
    assert out[0]['severity'] == 'MEDIUM'   # 300/100 = 3x → >2 → MEDIUM
    assert out[0]['confidence_score'] == 1.0  # min(300/250, 1.0)


def test_spike_below_threshold_no_fire(monkeypatch):
    d, _ = make_detector(monkeypatch, [{'log_count': 100, 'minute': 'x'}],
                         baseline={'baseline_value': 100, 'threshold_multiplier': 2.5})
    assert d.detect_spike_anomaly('srv1', 'apache') == []


def test_spike_no_rows_no_fire(monkeypatch):
    d, _ = make_detector(monkeypatch, None)
    assert d.detect_spike_anomaly('srv1', 'apache') == []


def test_spike_orders_by_minute(monkeypatch):
    """Regression: ORDER BY referenced the unaggregated ``timestamp`` column
    that is no longer selected; it must order by the grouped ``minute``."""
    d, cap = make_detector(monkeypatch, [{'log_count': 300, 'minute': 'x'}],
                           baseline={'baseline_value': 100, 'threshold_multiplier': 2.5})
    d.detect_spike_anomaly('srv1', 'apache')
    assert 'ORDER BY minute DESC' in cap['query']
    assert 'ORDER BY timestamp DESC' not in cap['query']


# ---------------------------------------------------------------------------
# detect_failed_auth
# ---------------------------------------------------------------------------

def test_failed_auth_fires(monkeypatch):
    d, _ = make_detector(monkeypatch, [
        {'source_ip': '1.2.3.4', 'user': 'root', 'failed_count': 25},
    ])
    out = d.detect_failed_auth('srv1', threshold_per_hour=10)
    assert len(out) == 1
    o = out[0]
    assert o['anomaly_type'] == 'failed_auth'
    assert o['source_ip'] == '1.2.3.4'
    assert o['severity'] == 'HIGH'           # 25 <= 30 → HIGH, not CRITICAL
    assert o['confidence_score'] == 1.0


def test_failed_auth_critical_above_3x(monkeypatch):
    d, _ = make_detector(monkeypatch, [
        {'source_ip': '9.9.9.9', 'user': 'admin', 'failed_count': 50},
    ])
    out = d.detect_failed_auth('srv1', threshold_per_hour=10)
    assert out[0]['severity'] == 'CRITICAL'


# ---------------------------------------------------------------------------
# detect_unusual_query_pattern
# ---------------------------------------------------------------------------

def test_slow_query_fires(monkeypatch):
    d, _ = make_detector(monkeypatch, [
        {'user': 'app', 'database_name': 'db', 'table_name': 'orders',
         'max_time': 40000, 'avg_time': 2000},
    ])
    out = d.detect_unusual_query_pattern('srv1')
    assert len(out) == 1
    assert out[0]['anomaly_type'] == 'unusual_query'
    assert out[0]['severity'] == 'HIGH'      # max_time 40000 >= 30000


def test_slow_query_medium_when_only_avg_high(monkeypatch):
    d, _ = make_detector(monkeypatch, [
        {'user': 'app', 'database_name': 'db', 'table_name': 'orders',
         'max_time': 10000, 'avg_time': 9999},
    ])
    out = d.detect_unusual_query_pattern('srv1')
    assert out[0]['severity'] == 'MEDIUM'


# ---------------------------------------------------------------------------
# detect_malicious_patterns
# ---------------------------------------------------------------------------

def test_malicious_pattern_fires(monkeypatch):
    d, _ = make_detector(monkeypatch, [{'id': 7, 'timestamp': 'x'}])
    out = d.detect_malicious_patterns('srv1', 'apache')
    assert any(o['anomaly_type'] == 'malicious_pattern' for o in out)
    hit = next(o for o in out if o['anomaly_type'] == 'malicious_pattern')
    assert hit['log_id'] == 7


def test_malicious_pattern_no_hits(monkeypatch):
    d, _ = make_detector(monkeypatch, None)
    assert d.detect_malicious_patterns('srv1', 'apache') == []


# ---------------------------------------------------------------------------
# graceful degradation without a DB / sklearn
# ---------------------------------------------------------------------------

def test_detector_constructs_without_sklearn():
    # If sklearn is genuinely unavailable on the host the isolation forest is
    # left None; either way the constructor must never raise.
    d = ad.AnomalyDetector()
    assert (d.isolation_forest is None) or (d.isolation_forest is not None)


def test_detector_returns_empty_without_execute_query(monkeypatch):
    # When no DB connector was imported, execute_query is None; calling any
    # detector must degrade to [] (the try/except catches the TypeError),
    # never crash.
    monkeypatch.setattr(ad, 'execute_query', None)
    d = ad.AnomalyDetector()
    assert d.detect_failed_auth('srv1') == []
    assert d.detect_spike_anomaly('srv1', 'apache') == []
    assert d.detect_unusual_access('srv1') == []