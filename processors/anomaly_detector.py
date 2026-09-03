"""Anomaly Detection Module for LogAgent"""

import logging
import typing
from typing import Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Heavy external dependencies are imported defensively so the module (and its
# pure decision helpers) stays importable on hosts without sklearn / a MySQL
# connector. The detectors that need them degrade gracefully when absent.
try:
    from sklearn.ensemble import IsolationForest
    _HAS_SKLEARN = True
except ImportError:  # pragma: no cover - exercised only on minimal hosts
    IsolationForest = typing.cast(typing.Callable, None)
    _HAS_SKLEARN = False

try:
    from database import execute_query
    _HAS_DB = True
except ImportError:  # pragma: no cover - requires mysql-connector
    execute_query = typing.cast(typing.Callable, None)
    _HAS_DB = False


class AnomalyDetector:
    """Detect anomalies in log streams using statistical and ML methods"""
    
    def __init__(self):
        self.isolation_forest = IsolationForest(
            contamination=0.05,  # Expect ~5% anomalies
            random_state=42
        ) if _HAS_SKLEARN else None
        self.baseline_cache = {}
    
    def detect_spike_anomaly(self, server_id: str, log_type: str, 
                            time_window_minutes: int = 10) -> List[Dict]:
        """Detect spikes in log volume
        
        Args:
            server_id: Server identifier
            log_type: Type of log (apache, mysql, audit, etc.)
            time_window_minutes: Time window for analysis
            
        Returns:
            List of detected spike anomalies
        """
        try:
            # Get baseline for this server/log_type
            baseline = self._get_baseline(server_id, log_type, 'volume')
            
            # Query log counts in recent window
            query = """
SELECT 
    COUNT(*) as log_count,
    DATE_FORMAT(timestamp, '%Y-%m-%d %H:%i:00') as minute
FROM logs
WHERE server_id = %s AND log_type = %s 
    AND timestamp >= DATE_SUB(NOW(), INTERVAL %s MINUTE)
GROUP BY DATE_FORMAT(timestamp, '%Y-%m-%d %H:%i:00')
ORDER BY minute DESC
"""
            
            results = execute_query(query, (server_id, log_type, time_window_minutes * 2), fetch=True)
            
            anomalies = []
            if results:
                current_count = results[0]['log_count']
                baseline_value = baseline.get('baseline_value', 100)
                threshold = baseline_value * baseline.get('threshold_multiplier', 2.5)
                
                if current_count > threshold:
                    anomalies.append({
                        'anomaly_type': 'spike',
                        'severity': self._calculate_severity(current_count, baseline_value),
                        'description': f"Spike in {log_type} logs: {current_count} logs vs baseline {baseline_value}",
                        'confidence_score': min(current_count / threshold, 1.0),
                        'log_type': log_type,
                        'server_id': server_id
                    })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting spike anomaly: {e}")
            return []
    
    def detect_unusual_access(self, server_id: str, database: str = None) -> List[Dict]:
        """Detect unusual database access patterns

        Args:
            server_id: Server identifier
            database: Target database (optional)

        Returns:
            List of detected unusual access anomalies
        """
        try:
            # Compare each user's recent access rate against their learned
            # baseline (user_profiles.avg_queries_per_hour). The baseline column
            # must be selected AND grouped, otherwise the comparison always sees
            # a 0 baseline and the check silently never fires.
            query = """
SELECT 
    u.username,
    u.avg_queries_per_hour,
    COUNT(*) as recent_count
FROM logs l
LEFT JOIN user_profiles u ON l.user = u.username
WHERE l.server_id = %s 
    AND l.log_type IN ('mysql', 'audit')
    AND l.timestamp >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
"""
            params: List = [server_id]

            if database:
                query += " AND l.database_name = %s"

            query += " GROUP BY u.username, u.avg_queries_per_hour"
            if database:
                params.append(database)

            results = execute_query(query, tuple(params), fetch=True)

            anomalies = []

            for record in results or []:
                username = record.get('username')
                if not username:
                    continue

                recent_count = record.get('recent_count', 0)
                avg_per_hour = record.get('avg_queries_per_hour', 0) or 0

                # Check if access rate is significantly higher
                if avg_per_hour > 0 and recent_count > (avg_per_hour * 3):
                    anomalies.append({
                        'anomaly_type': 'unusual_access',
                        'severity': 'HIGH' if recent_count > (avg_per_hour * 5) else 'MEDIUM',
                        'description': f"Unusual access by {username}: {recent_count} ops/hr vs avg {avg_per_hour:g}",
                        'confidence_score': min(recent_count / (avg_per_hour * 3), 1.0),
                        'log_type': 'mysql',
                        'server_id': server_id,
                        'user': username
                    })

            return anomalies

        except Exception as e:
            logger.error(f"Error detecting unusual access: {e}")
            return []

    def detect_failed_auth(self, server_id: str, 
                          threshold_per_hour: int = 10) -> List[Dict]:
        """Detect excessive failed authentication attempts
        
        Args:
            server_id: Server identifier
            threshold_per_hour: Threshold for failed attempts per hour
            
        Returns:
            List of detected failed auth anomalies
        """
        try:
            query = """
SELECT 
    source_ip,
    user,
    COUNT(*) as failed_count
FROM logs
WHERE server_id = %s 
    AND log_type IN ('audit', 'auth')
    AND status_code = 403
    AND timestamp >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
GROUP BY source_ip, user
HAVING failed_count > %s
ORDER BY failed_count DESC
"""
            
            results = execute_query(query, (server_id, threshold_per_hour), fetch=True)
            anomalies = []
            
            for record in results or []:
                source_ip = record.get('source_ip', 'unknown')
                user = record.get('user', 'unknown')
                failed_count = record.get('failed_count', 0)
                
                anomalies.append({
                    'anomaly_type': 'failed_auth',
                    'severity': 'CRITICAL' if failed_count > (threshold_per_hour * 3) else 'HIGH',
                    'description': f"{failed_count} failed auth attempts from {source_ip} for user {user}",
                    'confidence_score': min(failed_count / threshold_per_hour, 1.0),
                    'log_type': 'audit',
                    'server_id': server_id,
                    'source_ip': source_ip,
                    'user': user
                })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting failed auth: {e}")
            return []
    
    def detect_unusual_query_pattern(self, server_id: str) -> List[Dict]:
        """Detect unusual database query patterns
        
        Args:
            server_id: Server identifier
            
        Returns:
            List of detected query anomalies
        """
        try:
            query = """
SELECT 
    l.user,
    l.database_name,
    l.table_name,
    AVG(l.query_time_ms) as avg_time,
    COUNT(*) as query_count,
    MAX(l.query_time_ms) as max_time
FROM logs l
WHERE l.server_id = %s 
    AND l.log_type = 'mysql'
    AND l.timestamp >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
GROUP BY l.user, l.database_name, l.table_name
HAVING avg_time > 5000 OR max_time > 30000
ORDER BY max_time DESC
"""
            
            results = execute_query(query, (server_id,), fetch=True)
            anomalies = []
            
            for record in results or []:
                anomalies.append({
                    'anomaly_type': 'unusual_query',
                    'severity': 'MEDIUM' if record.get('max_time', 0) < 30000 else 'HIGH',
                    'description': (f"Slow query detected: {record.get('database_name')}.{record.get('table_name')} "
                                  f"- Max time: {record.get('max_time')}ms"),
                    'confidence_score': min(record.get('max_time', 0) / 30000, 1.0),
                    'log_type': 'mysql',
                    'server_id': server_id,
                    'user': record.get('user')
                })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting unusual query pattern: {e}")
            return []
    
    def detect_malicious_patterns(self, server_id: str, log_type: str = 'apache') -> List[Dict]:
        """Detect potentially malicious patterns in logs
        
        Args:
            server_id: Server identifier
            log_type: Type of logs to analyze
            
        Returns:
            List of detected malicious patterns
        """
        try:
            # SQL injection patterns
            malicious_patterns = [
                'UNION', 'SELECT', 'DROP', 'DELETE', 'INSERT', 'UPDATE',
                '--', '/*', '*/', 'xp_', 'sp_', 'exec(', 'eval(',
                '<script>', 'javascript:', 'onerror=', 'onload='
            ]
            
            anomalies = []
            
            for pattern in malicious_patterns:
                query = """
SELECT 
    id,
    timestamp,
    source_ip,
    path,
    raw_log_line
FROM logs
WHERE server_id = %s 
    AND log_type = %s
    AND (path LIKE %s OR raw_log_line LIKE %s)
    AND timestamp >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
LIMIT 10
"""
                
                pattern_search = f"%{pattern}%"
                results = execute_query(query, (server_id, log_type, pattern_search, pattern_search), fetch=True)
                
                if results:
                    anomalies.append({
                        'anomaly_type': 'malicious_pattern',
                        'severity': 'CRITICAL',
                        'description': f"Detected potential {pattern} injection attempts - {len(results)} occurrences",
                        'confidence_score': 0.85,
                        'log_type': log_type,
                        'server_id': server_id,
                        'log_id': results[0].get('id') if results else None
                    })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting malicious patterns: {e}")
            return []
    
    def save_anomaly(self, anomaly_data: Dict) -> int:
        """Save detected anomaly to database
        
        Args:
            anomaly_data: Anomaly details
            
        Returns:
            Anomaly ID
        """
        try:
            query = """
INSERT INTO anomalies 
(detected_at, log_id, anomaly_type, severity, description, confidence_score, investigation_status)
VALUES (%s, %s, %s, %s, %s, %s, %s)
"""
            
            execute_query(query, (
                datetime.now(),
                anomaly_data.get('log_id'),
                anomaly_data.get('anomaly_type'),
                anomaly_data.get('severity', 'MEDIUM'),
                anomaly_data.get('description'),
                anomaly_data.get('confidence_score', 0.5),
                'new'
            ))
            
            # Get the ID of inserted anomaly
            result = execute_query(
                "SELECT LAST_INSERT_ID() as id",
                fetch=True
            )
            
            if result:
                anomaly_id = result[0]['id']
                logger.info(f"Saved anomaly ID: {anomaly_id}")
                return anomaly_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error saving anomaly: {e}")
            return None
    
    def _get_baseline(self, server_id: str, log_type: str, value_type: str) -> Dict:
        """Get baseline metrics for comparison"""
        try:
            query = """
SELECT baseline_value, threshold_multiplier
FROM baseline_metrics
WHERE server_id = %s AND log_type = %s AND value_type = %s
"""
            
            result = execute_query(query, (server_id, log_type, value_type), fetch=True)
            
            if result:
                return {
                    'baseline_value': result[0].get('baseline_value', 100),
                    'threshold_multiplier': result[0].get('threshold_multiplier', 2.0)
                }
            
            # Return defaults if not found
            return {'baseline_value': 100, 'threshold_multiplier': 2.0}
            
        except Exception as e:
            logger.error(f"Error getting baseline: {e}")
            return {'baseline_value': 100, 'threshold_multiplier': 2.0}
    
    def _calculate_severity(self, current: float, baseline: float) -> str:
        """Calculate severity level based on deviation from baseline"""
        ratio = current / baseline if baseline > 0 else 1
        
        if ratio > 10:
            return 'CRITICAL'
        elif ratio > 5:
            return 'HIGH'
        elif ratio > 2:
            return 'MEDIUM'
        else:
            return 'LOW'


def get_anomaly_detector() -> AnomalyDetector:
    """Get or create anomaly detector instance"""
    return AnomalyDetector()
