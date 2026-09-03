"""Flask Dashboard Application for LogAgent"""

import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from database import execute_query
from processors.anomaly_detector import get_anomaly_detector
from processors.gemini_integration import get_gemini_analyzer

app = Flask(__name__)
CORS(app)

logger = logging.getLogger(__name__)

# Initialize components. Gemini is intentionally lazed so the dashboard can
# start even when GEMINI_API_KEY is not configured; anomaly analysis simply
# reports a clean error until an analyzer is available.
anomaly_detector = get_anomaly_detector()
_gemini_analyzer = None


def _get_gemini_analyzer():
    """Return the singleton Gemini analyzer, creating it on first use."""
    global _gemini_analyzer
    if _gemini_analyzer is None:
        try:
            _gemini_analyzer = get_gemini_analyzer()
        except Exception as e:
            logger.error(f"Gemini analyzer unavailable: {e}")
            return None
    return _gemini_analyzer


# ============================================
# Dashboard Routes
# ============================================

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')


@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        # Get recent log count
        logs_query = """
SELECT COUNT(*) as total_logs, 
       COUNT(DISTINCT log_type) as log_types,
       COUNT(DISTINCT server_id) as active_servers
FROM logs
WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
"""
        logs_stats = execute_query(logs_query, fetch=True)
        
        # Get anomaly stats
        anomalies_query = """
SELECT 
    COUNT(*) as total_anomalies,
    SUM(CASE WHEN severity = 'CRITICAL' THEN 1 ELSE 0 END) as critical_count,
    SUM(CASE WHEN severity = 'HIGH' THEN 1 ELSE 0 END) as high_count,
    SUM(CASE WHEN investigation_status = 'new' THEN 1 ELSE 0 END) as new_count
FROM anomalies
WHERE detected_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
"""
        anomalies_stats = execute_query(anomalies_query, fetch=True)
        
        # Get alert stats
        alerts_query = """
SELECT 
    COUNT(*) as total_alerts,
    SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent_count,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count
FROM alerts
WHERE sent_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
"""
        alerts_stats = execute_query(alerts_query, fetch=True)
        
        return jsonify({
            'success': True,
            'logs': logs_stats[0] if logs_stats else {},
            'anomalies': anomalies_stats[0] if anomalies_stats else {},
            'alerts': alerts_stats[0] if alerts_stats else {}
        })
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get logs with filtering and pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        log_type = request.args.get('log_type', None)
        server_id = request.args.get('server_id', None)
        severity = request.args.get('severity', None)
        
        offset = (page - 1) * per_page
        
        query = "SELECT * FROM logs WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
        params = []
        
        if log_type:
            query += " AND log_type = %s"
            params.append(log_type)
        
        if server_id:
            query += " AND server_id = %s"
            params.append(server_id)
        
        if severity:
            query += " AND severity = %s"
            params.append(severity)
        
        query += f" ORDER BY timestamp DESC LIMIT {per_page} OFFSET {offset}"
        
        logs = execute_query(query, params, fetch=True)
        
        # Get total count
        count_query = "SELECT COUNT(*) as total FROM logs WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
        count = execute_query(count_query, fetch=True)[0]['total']
        
        return jsonify({
            'success': True,
            'logs': logs or [],
            'total': count,
            'page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/anomalies', methods=['GET'])
def get_anomalies():
    """Get detected anomalies"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        severity = request.args.get('severity', None)
        status = request.args.get('status', None)
        
        offset = (page - 1) * per_page
        
        query = """
SELECT a.*, l.log_type, l.server_id, l.source_ip, l.user
FROM anomalies a
LEFT JOIN logs l ON a.log_id = l.id
WHERE a.detected_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
"""
        params = []
        
        if severity:
            query += " AND a.severity = %s"
            params.append(severity)
        
        if status:
            query += " AND a.investigation_status = %s"
            params.append(status)
        
        query += f" ORDER BY a.detected_at DESC LIMIT {per_page} OFFSET {offset}"
        
        anomalies = execute_query(query, params, fetch=True)
        
        # Get count
        count_query = "SELECT COUNT(*) as total FROM anomalies WHERE detected_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
        count = execute_query(count_query, fetch=True)[0]['total']
        
        return jsonify({
            'success': True,
            'anomalies': anomalies or [],
            'total': count,
            'page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        logger.error(f"Error getting anomalies: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/servers', methods=['GET'])
def get_servers():
    """Get list of monitored servers"""
    try:
        query = """
SELECT id, server_id, hostname, ip_address, os_type, is_active, last_heartbeat
FROM servers
ORDER BY hostname
"""
        servers = execute_query(query, fetch=True)
        
        return jsonify({
            'success': True,
            'servers': servers or []
        })
        
    except Exception as e:
        logger.error(f"Error getting servers: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/anomalies/<int:anomaly_id>/analyze', methods=['POST'])
def analyze_anomaly(anomaly_id):
    """Analyze anomaly using Gemini AI"""
    try:
        # Get anomaly details
        query = """
SELECT a.*, l.raw_log_line, l.log_type, l.server_id
FROM anomalies a
LEFT JOIN logs l ON a.log_id = l.id
WHERE a.id = %s
"""
        result = execute_query(query, (anomaly_id,), fetch=True)
        
        if not result:
            return jsonify({'success': False, 'error': 'Anomaly not found'}), 404
        
        anomaly_data = result[0]

        analyzer = _get_gemini_analyzer()
        if analyzer is None:
            return jsonify({
                'success': False,
                'error': 'Gemini analyzer is not configured (GEMINI_API_KEY missing)'
            }), 503

        # Analyze with Gemini
        analysis = analyzer.analyze_anomaly({
            'anomaly_id': anomaly_id,
            'log_type': anomaly_data.get('log_type'),
            'timestamp': str(anomaly_data.get('detected_at')),
            'severity': anomaly_data.get('severity'),
            'description': anomaly_data.get('description'),
            'log_details': anomaly_data.get('raw_log_line', 'N/A')
        })

        # Generate query for investigation
        query_text = analyzer.generate_query({
            'anomaly_id': anomaly_id,
            'anomaly_type': anomaly_data.get('anomaly_type'),
            'server_id': anomaly_data.get('server_id'),
            'database': 'logagent',
            'time_window': '24 hours',
            'description': anomaly_data.get('description')
        })
        
        return jsonify({
            'success': True,
            'anomaly_id': anomaly_id,
            'analysis': analysis['analysis_text'],
            'generated_query': query_text
        })
        
    except Exception as e:
        logger.error(f"Error analyzing anomaly: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/anomalies/<int:anomaly_id>/update', methods=['PUT'])
def update_anomaly(anomaly_id):
    """Update anomaly investigation status"""
    try:
        data = request.get_json()
        status = data.get('status')
        notes = data.get('notes')
        
        if not status:
            return jsonify({'success': False, 'error': 'Status required'}), 400
        
        query = """
UPDATE anomalies
SET investigation_status = %s, notes = %s, updated_at = NOW()
WHERE id = %s
"""
        execute_query(query, (status, notes, anomaly_id))
        
        return jsonify({'success': True, 'message': 'Anomaly updated'})
        
    except Exception as e:
        logger.error(f"Error updating anomaly: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stats/timeline', methods=['GET'])
def get_timeline_stats():
    """Get logs and anomalies timeline"""
    try:
        hours = request.args.get('hours', 24, type=int)
        
        query = """
SELECT 
    DATE_FORMAT(timestamp, '%Y-%m-%d %H:00:00') as hour,
    log_type,
    COUNT(*) as count
FROM logs
WHERE timestamp >= DATE_SUB(NOW(), INTERVAL %s HOUR)
GROUP BY DATE_FORMAT(timestamp, '%Y-%m-%d %H:00:00'), log_type
ORDER BY hour
"""
        data = execute_query(query, (hours,), fetch=True)
        
        return jsonify({
            'success': True,
            'data': data or []
        })
        
    except Exception as e:
        logger.error(f"Error getting timeline stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stats/severity', methods=['GET'])
def get_severity_stats():
    """Get anomalies by severity"""
    try:
        query = """
SELECT severity, COUNT(*) as count
FROM anomalies
WHERE detected_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY severity
"""
        data = execute_query(query, fetch=True)
        
        return jsonify({
            'success': True,
            'data': data or []
        })
        
    except Exception as e:
        logger.error(f"Error getting severity stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


# ============================================
# Error Handlers
# ============================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'success': False, 'error': 'Internal server error'}), 500


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development'
    )
