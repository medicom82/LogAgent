-- ============================================
-- Initial Data & Configuration
-- ============================================

-- Insert default system configuration
INSERT INTO system_config (config_key, config_value, config_type, description) VALUES
('log_retention_days', '90', 'integer', 'How many days to keep logs in database'),
('anomaly_check_interval_seconds', '300', 'integer', 'Interval for anomaly detection checks'),
('kafka_bootstrap_servers', 'kafka:29092', 'string', 'Kafka bootstrap servers'),
('gemini_model', 'gemini-pro', 'string', 'Google Gemini model to use'),
('enable_email_alerts', 'false', 'boolean', 'Enable email alerting'),
('enable_slack_alerts', 'false', 'boolean', 'Enable Slack alerting'),
('default_alert_threshold', '0.75', 'string', 'Default confidence threshold for alerts'),
('flink_checkpoint_interval', '60000', 'integer', 'Flink checkpoint interval in ms')
ON DUPLICATE KEY UPDATE config_value=VALUES(config_value);

-- Insert sample servers
INSERT INTO servers (server_id, hostname, ip_address, os_type, os_version, is_active, last_heartbeat) VALUES
('server-linux-01', 'web-server-01.example.com', '192.168.1.10', 'linux', 'Ubuntu 22.04 LTS', TRUE, NOW()),
('server-linux-02', 'db-server-01.example.com', '192.168.1.11', 'linux', 'Debian 11', TRUE, NOW()),
('server-windows-01', 'app-server-01.example.com', '192.168.1.20', 'windows', 'Windows Server 2022', TRUE, NOW())
ON DUPLICATE KEY UPDATE last_heartbeat=NOW();

-- Insert sample baseline metrics
INSERT INTO baseline_metrics (metric_name, server_id, log_type, value_type, baseline_value, threshold_multiplier) VALUES
('requests_per_minute', 'server-linux-01', 'apache', 'rate', 100.0, 2.5),
('queries_per_minute', 'server-linux-02', 'mysql', 'rate', 50.0, 3.0),
('failed_logins_per_hour', 'server-linux-02', 'audit', 'count', 5.0, 5.0),
('avg_response_time', 'server-linux-01', 'apache', 'time_ms', 500.0, 3.0)
ON DUPLICATE KEY UPDATE baseline_value=VALUES(baseline_value);

-- Insert sample log sources
INSERT INTO log_sources (server_id, source_name, source_type, log_path, status) VALUES
('server-linux-01', 'example.com', 'apache_vhost', '/var/log/apache2/example.com-access.log', 'active'),
('server-linux-01', 'test.example.com', 'apache_vhost', '/var/log/apache2/test.example.com-access.log', 'active'),
('server-linux-02', 'mysql_db', 'mysql_database', '/var/log/mysql/mysql.log', 'active'),
('server-linux-02', 'audit_log', 'audit_log', '/var/log/audit/audit.log', 'active')
ON DUPLICATE KEY UPDATE status='active';

-- Sample user profiles
INSERT INTO user_profiles (username, server_id, avg_queries_per_hour, avg_operations_per_hour, typical_query_time_ms, is_service_account) VALUES
('root', 'server-linux-02', 15.0, 8.0, 250.0, TRUE),
('webapp_user', 'server-linux-02', 120.0, 80.0, 150.0, TRUE),
('admin', 'server-linux-02', 5.0, 3.0, 500.0, FALSE),
('audit', 'server-linux-02', 0.5, 0.5, 0.0, TRUE)
ON DUPLICATE KEY UPDATE avg_queries_per_hour=VALUES(avg_queries_per_hour);

-- ============================================
-- Sample Data for Testing
-- ============================================

-- Sample log entries
INSERT INTO logs (timestamp, server_id, log_type, source_ip, destination_ip, user, method, path, status_code, response_time_ms, bytes_sent, user_agent, database_name, table_name) VALUES
(DATE_SUB(NOW(), INTERVAL 5 MINUTE), 'server-linux-01', 'apache', '10.0.0.1', '192.168.1.10', 'user1', 'GET', '/index.php', 200, 150, 5234, 'Mozilla/5.0', NULL, NULL),
(DATE_SUB(NOW(), INTERVAL 4 MINUTE), 'server-linux-01', 'apache', '10.0.0.2', '192.168.1.10', 'user2', 'POST', '/api/login', 200, 250, 1024, 'curl/7.64.1', NULL, NULL),
(DATE_SUB(NOW(), INTERVAL 3 MINUTE), 'server-linux-02', 'mysql', NULL, NULL, 'webapp_user', NULL, NULL, NULL, 45, NULL, NULL, 'production', 'users'),
(DATE_SUB(NOW(), INTERVAL 2 MINUTE), 'server-linux-02', 'mysql', NULL, NULL, 'root', NULL, NULL, NULL, 120, NULL, NULL, 'production', 'transactions'),
(DATE_SUB(NOW(), INTERVAL 1 MINUTE), 'server-linux-01', 'apache', '10.0.0.3', '192.168.1.10', NULL, 'GET', '/admin/panel', 403, 50, 256, 'Mozilla/5.0', NULL, NULL);

-- ============================================
-- Create Default Admin User (if using auth)
-- ============================================
-- Note: This is a placeholder for your auth system
-- Uncomment if you implement user management:
-- INSERT INTO users (username, email, password_hash, role, is_active) VALUES
-- ('admin', 'admin@example.com', 'HASHED_PASSWORD_HERE', 'admin', TRUE)
-- ON DUPLICATE KEY UPDATE is_active=TRUE;

COMMIT;
