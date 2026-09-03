-- ============================================
-- LogAgent Database Schema
-- ============================================

-- 1. MAIN LOGS TABLE
CREATE TABLE IF NOT EXISTS logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    server_id VARCHAR(255) NOT NULL,
    log_type ENUM('apache', 'mysql', 'audit', 'ispconfig', 'syslog', 'auth', 'windows_iis', 'windows_event') NOT NULL,
    source_ip VARCHAR(45),
    destination_ip VARCHAR(45),
    user VARCHAR(255),
    method VARCHAR(50),
    path VARCHAR(1000),
    status_code INT,
    response_time_ms INT,
    bytes_sent BIGINT,
    user_agent TEXT,
    referer VARCHAR(1000),
    database_name VARCHAR(255),
    table_name VARCHAR(255),
    query TEXT,
    query_time_ms FLOAT,
    rows_examined BIGINT,
    rows_sent BIGINT,
    error_code INT,
    error_message TEXT,
    severity ENUM('INFO', 'WARNING', 'ERROR', 'CRITICAL') DEFAULT 'INFO',
    raw_log_line LONGTEXT,
    INDEX idx_timestamp (timestamp),
    INDEX idx_server_id (server_id),
    INDEX idx_log_type (log_type),
    INDEX idx_source_ip (source_ip),
    INDEX idx_user (user),
    INDEX idx_status_code (status_code),
    INDEX idx_error_code (error_code),
    INDEX idx_database_table (database_name, table_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. ANOMALIES TABLE
CREATE TABLE IF NOT EXISTS anomalies (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    detected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    log_id BIGINT,
    anomaly_type ENUM('spike', 'unusual_access', 'failed_auth', 'unusual_query', 'malicious_pattern', 'unknown') DEFAULT 'unknown',
    severity ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') DEFAULT 'MEDIUM',
    description TEXT,
    confidence_score FLOAT DEFAULT 0.0,
    is_confirmed BOOLEAN DEFAULT FALSE,
    is_false_positive BOOLEAN DEFAULT FALSE,
    investigation_status ENUM('new', 'investigating', 'resolved', 'ignored') DEFAULT 'new',
    assigned_to VARCHAR(255),
    notes TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (log_id) REFERENCES logs(id) ON DELETE SET NULL,
    INDEX idx_detected_at (detected_at),
    INDEX idx_anomaly_type (anomaly_type),
    INDEX idx_severity (severity),
    INDEX idx_investigation_status (investigation_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. GENERATED QUERIES TABLE
CREATE TABLE IF NOT EXISTS generated_queries (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    anomaly_id BIGINT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    query_text LONGTEXT NOT NULL,
    query_purpose VARCHAR(500),
    generated_by ENUM('gemini', 'rule_based', 'manual') DEFAULT 'gemini',
    execution_status ENUM('pending', 'executed', 'failed', 'skipped') DEFAULT 'pending',
    execution_result TEXT,
    executed_at DATETIME,
    execution_time_ms INT,
    FOREIGN KEY (anomaly_id) REFERENCES anomalies(id) ON DELETE CASCADE,
    INDEX idx_created_at (created_at),
    INDEX idx_execution_status (execution_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. GEMINI AI INTERACTIONS TABLE
CREATE TABLE IF NOT EXISTS gemini_interactions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    prompt_type ENUM('anomaly_analysis', 'query_generation', 'log_summary', 'threat_analysis', 'recommendation') DEFAULT 'anomaly_analysis',
    input_text LONGTEXT NOT NULL,
    output_text LONGTEXT,
    model VARCHAR(100) DEFAULT 'gemini-pro',
    tokens_input INT,
    tokens_output INT,
    response_time_ms INT,
    is_success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    related_anomaly_id BIGINT,
    related_log_id BIGINT,
    FOREIGN KEY (related_anomaly_id) REFERENCES anomalies(id) ON DELETE SET NULL,
    FOREIGN KEY (related_log_id) REFERENCES logs(id) ON DELETE SET NULL,
    INDEX idx_timestamp (timestamp),
    INDEX idx_prompt_type (prompt_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. SERVERS TABLE
CREATE TABLE IF NOT EXISTS servers (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    server_id VARCHAR(255) NOT NULL UNIQUE,
    hostname VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45),
    os_type ENUM('linux', 'windows') NOT NULL,
    os_version VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    last_heartbeat DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_server_id (server_id),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. LOG SOURCES TABLE (ISPConfig Virtual Hosts, etc)
CREATE TABLE IF NOT EXISTS log_sources (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    server_id VARCHAR(255) NOT NULL,
    source_name VARCHAR(255) NOT NULL,
    source_type ENUM('apache_vhost', 'mysql_database', 'audit_log', 'ispconfig_domain', 'windows_application') DEFAULT 'apache_vhost',
    log_path VARCHAR(1000),
    status ENUM('active', 'inactive', 'error') DEFAULT 'active',
    last_processed_timestamp DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (server_id) REFERENCES servers(server_id) ON DELETE CASCADE,
    INDEX idx_server_id (server_id),
    INDEX idx_source_type (source_type),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. ALERTS TABLE
CREATE TABLE IF NOT EXISTS alerts (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    anomaly_id BIGINT NOT NULL,
    alert_type ENUM('email', 'slack', 'webhook', 'dashboard') NOT NULL,
    recipient VARCHAR(500),
    subject VARCHAR(500),
    message TEXT,
    sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status ENUM('pending', 'sent', 'failed') DEFAULT 'pending',
    retry_count INT DEFAULT 0,
    error_message TEXT,
    FOREIGN KEY (anomaly_id) REFERENCES anomalies(id) ON DELETE CASCADE,
    INDEX idx_sent_at (sent_at),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. BASELINE METRICS TABLE (for anomaly detection)
CREATE TABLE IF NOT EXISTS baseline_metrics (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    metric_name VARCHAR(255) NOT NULL,
    server_id VARCHAR(255),
    log_type VARCHAR(50),
    value_type VARCHAR(100),
    baseline_value FLOAT,
    threshold_multiplier FLOAT DEFAULT 2.0,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_metric (metric_name, server_id, log_type),
    INDEX idx_server_id (server_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. USER BEHAVIOR PROFILES TABLE
CREATE TABLE IF NOT EXISTS user_profiles (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(255) NOT NULL,
    server_id VARCHAR(255),
    avg_queries_per_hour FLOAT,
    avg_operations_per_hour FLOAT,
    typical_query_time_ms FLOAT,
    typical_access_hours VARCHAR(100),
    typical_accessed_tables TEXT,
    typical_accessed_databases TEXT,
    is_service_account BOOLEAN DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user (username, server_id),
    INDEX idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. SYSTEM CONFIGURATION TABLE
CREATE TABLE IF NOT EXISTS system_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    config_key VARCHAR(255) NOT NULL UNIQUE,
    config_value TEXT,
    config_type ENUM('string', 'integer', 'boolean', 'json') DEFAULT 'string',
    description TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Composite indexes for common queries
ALTER TABLE logs ADD INDEX idx_server_timestamp (server_id, timestamp);
ALTER TABLE logs ADD INDEX idx_type_timestamp (log_type, timestamp);
ALTER TABLE anomalies ADD INDEX idx_log_detected (log_id, detected_at);
ALTER TABLE generated_queries ADD INDEX idx_anomaly_created (anomaly_id, created_at);

-- ============================================
-- VIEWS
-- ============================================

-- View: Recent Anomalies with Log Details
CREATE OR REPLACE VIEW v_recent_anomalies AS
SELECT 
    a.id as anomaly_id,
    a.detected_at,
    a.anomaly_type,
    a.severity,
    a.description,
    a.confidence_score,
    l.log_type,
    l.server_id,
    l.source_ip,
    l.user,
    l.timestamp as log_timestamp
FROM anomalies a
LEFT JOIN logs l ON a.log_id = l.id
ORDER BY a.detected_at DESC;

-- View: Anomalies by Severity and Status
CREATE OR REPLACE VIEW v_anomalies_summary AS
SELECT 
    severity,
    investigation_status,
    COUNT(*) as count,
    MAX(detected_at) as latest_detection
FROM anomalies
WHERE detected_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY severity, investigation_status;

-- ============================================
-- STORED PROCEDURES
-- ============================================

-- Procedure: Get anomalies in time range
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS sp_get_anomalies_by_timerange(
    IN p_start_time DATETIME,
    IN p_end_time DATETIME,
    IN p_severity VARCHAR(20)
)
BEGIN
    SELECT 
        a.*,
        l.log_type,
        l.server_id,
        l.source_ip
    FROM anomalies a
    LEFT JOIN logs l ON a.log_id = l.id
    WHERE a.detected_at BETWEEN p_start_time AND p_end_time
    AND (p_severity IS NULL OR a.severity = p_severity)
    ORDER BY a.detected_at DESC;
END//
DELIMITER ;

-- Procedure: Archive old logs
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS sp_archive_old_logs(
    IN p_days_to_keep INT
)
BEGIN
    DELETE FROM logs
    WHERE timestamp < DATE_SUB(NOW(), INTERVAL p_days_to_keep DAY);
    SELECT ROW_COUNT() as deleted_rows;
END//
DELIMITER ;

-- ============================================
-- PARTITIONING (Optional - for very large tables)
-- ============================================
-- Uncomment to enable partitioning by month:
/*
ALTER TABLE logs
PARTITION BY RANGE (YEAR(timestamp)*100 + MONTH(timestamp)) (
    PARTITION p_2024_01 VALUES LESS THAN (202402),
    PARTITION p_2024_02 VALUES LESS THAN (202403),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);
*/
