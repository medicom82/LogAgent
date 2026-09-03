# LogAgent Architecture

## System Overview

LogAgent is a distributed real-time log analysis system designed to collect, process, and analyze logs from multiple Linux and Windows servers.

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRODUCTION ENVIRONMENT                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   Linux      │  │   Linux      │  │   Windows    │           │
│  │   Server 1   │  │   Server 2   │  │   Server 1   │           │
│  │              │  │              │  │              │           │
│  │ - Apache     │  │ - MySQL      │  │ - IIS        │           │
│  │ - MySQL      │  │ - Audit      │  │ - Event Logs │           │
│  │ - Audit      │  │ - ISPConfig  │  │ - AppLogs    │           │
│  │ - Syslog     │  │ - Auth       │  │              │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                 │                 │                   │
│         └─────────────────┼─────────────────┘                   │
│                           │                                     │
│                    SSH/WinRM Collection                         │
│                           │                                     │
│         ┌─────────────────▼─────────────────┐                   │
│         │      Collectors (Agents)          │                   │
│         │  ┌────────────────────────────┐  │                   │
│         │  │ Linux Log Collector        │  │                   │
│         │  │ Windows Log Collector      │  │                   │
│         │  │ Apache/MySQL/Audit Parser  │  │                   │
│         │  └────────────────────────────┘  │                   │
│         └─────────────────┬─────────────────┘                   │
│                           │                                     │
│                    Kafka Producer                               │
│                           │                                     │
│         ┌─────────────────▼─────────────────┐                   │
│         │    Kafka Topics                   │                   │
│         │  ┌────────────────────────────┐  │                   │
│         │  │ log-stream (3 partitions)  │  │                   │
│         │  │ anomalies (2 partitions)   │  │                   │
│         │  │ events (3 partitions)      │  │                   │
│         │  │ alerts (1 partition)       │  │                   │
│         │  └────────────────────────────┘  │                   │
│         └─────────────────┬─────────────────┘                   │
│                           │                                     │
│    ┌──────────────────────┼──────────────────────┐              │
│    │                      │                      │              │
│ Flink Stream Processing   │              Kafka Consumer          │
│ ┌──────────────────────┐  │              ┌──────────────┐       │
│ │ Transformations      │  │              │ Processors   │       │
│ │ Aggregations         │  │              │ ┌──────────┐ │       │
│ │ State Management     │  │              │ │Anomaly   │ │       │
│ │ ┌─────────────────┐  │  │              │ │Detector  │ │       │
│ │ │Data enrichment  │  │  │              │ └──────────┘ │       │
│ │ │Normalization    │  │  │              │ ┌──────────┐ │       │
│ │ │Windowing        │  │  │              │ │Gemini AI │ │       │
│ │ └─────────────────┘  │  │              │ │Integration│ │       │
│ └──────────────────────┘  │              │ └──────────┘ │       │
│         │                 │              └──────────────┘       │
│         └─────────────────┼─────────────────┬──────────────┐    │
│                           │                 │              │    │
│                    MySQL Database        Alerts          Logs   │
│                    ┌──────────────┐     Handler          Store  │
│                    │              │                              │
│ ┌──────────────────▼─────────────────────────────────────┐     │
│ │              MySQL Database (logagent)                 │     │
│ │ ┌──────────────────────────────────────────────────┐   │     │
│ │ │ Tables:                                          │   │     │
│ │ │ - logs (indexed for fast queries)               │   │     │
│ │ │ - anomalies (with severity levels)             │   │     │
│ │ │ - generated_queries (AI-generated SQL)         │   │     │
│ │ │ - gemini_interactions (audit trail)            │   │     │
│ │ │ - servers (topology)                           │   │     │
│ │ │ - baseline_metrics (for comparison)            │   │     │
│ │ │ - user_profiles (behavioral baselines)         │   │     │
│ │ │ - alerts (delivery tracking)                   │   │     │
│ │ └──────────────────────────────────────────────────┘   │     │
│ └──────────────────────────────────────────────────────┬──┘     │
│                                                        │        │
│                                              Flask API │        │
│                                                        │        │
│                 ┌──────────────────────────────────────▼──────┐ │
│                 │   Dashboard (Web UI)                       │ │
│                 │ - Real-time metrics                        │ │
│                 │ - Anomaly visualization                    │ │
│                 │ - Gemini AI analysis viewer               │ │
│                 │ - Investigation tools                      │ │
│                 └────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Log Collectors

**Linux Collector**
- SSH-based remote log collection
- Supports: Apache, MySQL, Audit logs, ISPConfig, Syslog, Auth logs
- Log parsing and normalization
- Regex-based format extraction

**Windows Collector**
- WinRM/Direct access to log files
- Supports: IIS logs, Event Logs, Application logs, Performance metrics
- Windows Event Log API integration
- Performance counter monitoring

### 2. Message Queue (Kafka)

**Topics:**
- `log-stream`: Raw logs from collectors (3 partitions for throughput)
- `anomalies`: Detected anomalies (2 partitions)
- `events`: System events and metrics (3 partitions)
- `alerts`: Alert notifications (1 partition)

**Benefits:**
- High throughput and low latency
- Fault tolerance and recovery
- Exactly-once processing semantics
- Horizontal scalability

### 3. Stream Processing (Apache Flink)

**Functions:**
- Real-time data transformation and enrichment
- State management for baselines
- Windowed aggregations (tumbling, sliding windows)
- Backpressure handling

**Pipelines:**
- Raw log ingestion and parsing
- Data normalization and enrichment
- Anomaly pre-detection (statistical)
- State updates for baseline metrics

### 4. Anomaly Detection

**Methods:**
- Statistical baselines (request rate, response time)
- Machine learning (Isolation Forest for outliers)
- Rule-based detection (failed logins, suspicious patterns)
- Behavioral anomalies (unusual user activity)

**Confidence Scoring:**
- 0.0-0.33: Low confidence
- 0.33-0.66: Medium confidence
- 0.66-1.0: High confidence

### 5. Gemini AI Integration

**Capabilities:**
- Natural language analysis of anomalies
- Automatic SQL query generation for investigation
- Threat intelligence assessment
- Remediation recommendations
- Pattern learning from historical data

**Interaction Types:**
- Anomaly analysis
- Query generation
- Log summarization
- Threat analysis
- Recommendation generation

### 6. Database (MySQL)

**Key Features:**
- Partitioned tables for large volumes
- Optimized indexes for common queries
- Views for complex analytics
- Stored procedures for operations
- Audit trail for compliance

**Retention Policies:**
- Default: 90 days
- Configurable per log type
- Archival support for long-term storage

### 7. Dashboard (Flask Web UI)

**Features:**
- Real-time statistics and KPIs
- Log visualization and filtering
- Anomaly investigation tools
- Gemini AI analysis viewer
- Server health monitoring
- Alert management

## Data Flow Example

### Scenario: SQL Injection Attack Detection

1. **Collection**: Linux Collector detects suspicious SQL pattern in Apache access log
2. **Kafka**: Log entry sent to `log-stream` topic
3. **Flink**: 
   - Parses and normalizes the log
   - Checks against malicious pattern rules
   - Flags as potential SQL injection
4. **Anomaly Detector**:
   - Calculates confidence score (0.92)
   - Creates anomaly record
   - Sends to `anomalies` topic
5. **Gemini AI**:
   - Analyzes the pattern
   - Generates investigation SQL query
   - Provides threat assessment
   - Recommends immediate actions
6. **Database**: 
   - Stores anomaly record
   - Records Gemini interaction
   - Updates investigation status
7. **Dashboard**: 
   - Displays anomaly with red "CRITICAL" badge
   - Shows Gemini analysis
   - Offers one-click investigation query execution

## Scaling Considerations

### Horizontal Scaling

**Kafka**: Add broker nodes and increase topic partitions
**Flink**: Deploy TaskManager cluster nodes
**MySQL**: Use read replicas, sharding, or cloud solutions
**Collectors**: Deploy agents per server or use central collection point

### Performance Optimization

1. **Kafka Tuning**
   - Increase batch size for throughput
   - Adjust linger time for latency vs. throughput tradeoff
   - Use compression (snappy/lz4)

2. **Flink Optimization**
   - Adjust parallelism based on CPU cores
   - Configure memory and GC settings
   - Use RocksDB state backend for large state

3. **Database Optimization**
   - Add appropriate indexes
   - Use partitioning by date
   - Archive old data
   - Use query result caching

## Security Considerations

1. **Data in Transit**
   - SSL/TLS for Kafka connections
   - SSH key-based authentication for collectors
   - HTTPS for dashboard API

2. **Data at Rest**
   - Encrypted database storage
   - Encrypted backups
   - Secure credential management (.env files)

3. **Access Control**
   - Authentication for dashboard (future)
   - Role-based access control (RBAC)
   - API key management for integrations

4. **Compliance**
   - Audit logging of all AI interactions
   - Data retention policies
   - GDPR-compliant data deletion
