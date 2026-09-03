# LogAgent

Real-time log analysis system with anomaly detection and Gemini AI integration for Apache, MySQL, Audit logs across multiple Linux and Windows servers.

## 🌟 Features

- **Real-time Log Collection**: Collect logs from Apache, MySQL, Audit, ISPConfig, and Windows servers
- **Anomaly Detection**: Statistical and ML-based detection of suspicious patterns
- **Gemini AI Integration**: AI-powered log analysis and SQL query generation
- **Interactive Dashboard**: Real-time visualization and investigation tools
- **Stream Processing**: Apache Flink for high-throughput log processing
- **Scalable Architecture**: Kafka-based message queue for distribution
- **Multi-Server Support**: Monitor Linux and Windows servers simultaneously

## 📁 Project Structure

```
LogAgent/
├── collectors/                 # Log collection agents
│   ├── linux_collector.py     # Linux/Unix log collector (SSH)
│   ├── windows_collector.py   # Windows log collector (WinRM)
│   ├── apache_collector.py    # Apache-specific parser
│   ├── mysql_collector.py     # MySQL-specific parser
│   ├── audit_collector.py     # Linux Audit log parser
│   └── ispconfig_collector.py # ISPConfig log parser
│
├── processors/                # Stream processing & analysis
│   ├── anomaly_detector.py    # Anomaly detection algorithms
│   ├── gemini_integration.py  # Google Gemini AI integration
│   ├── log_parser.py          # Log parsing utilities
│   └── query_generator.py     # SQL query generation
│
├── flink/                     # Apache Flink jobs
│   ├── log_processor.py       # Main Flink job for log processing
│   ├── state_manager.py       # State management (baselines)
│   ├── window_functions.py    # Windowing & aggregations
│   └── transformations.py     # Data transformations
│
├── kafka/                     # Kafka configuration
│   ├── producer.py            # Kafka producer
│   ├── consumer.py            # Kafka consumer
│   └── topics_manager.py      # Topic management
│
├── database/                  # Database schemas & utilities
│   ├── __init__.py           # Database connection pool
│   ├── schema.sql            # Database schema (tables, indexes)
│   └── init.sql              # Sample data & initialization
│
├── dashboard/                 # Web UI (Flask)
│   ├── app.py               # Flask application
│   ├── templates/           # HTML templates
│   │   ├── index.html       # Main dashboard
│   │   ├── logs.html        # Logs view
│   │   ├── anomalies.html   # Anomalies view
│   │   └── settings.html    # Settings page
│   └── static/              # Frontend assets
│       ├── css/
│       │   └── style.css    # Dashboard styles
│       └── js/
│           └── dashboard.js # Frontend JavaScript
│
├── config/                    # Configuration files
│   ├── mysql.conf           # MySQL configuration
│   ├── kafka.conf           # Kafka configuration
│   ├── flink.conf           # Flink configuration
│   └── gemini.conf          # Gemini AI configuration
│
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md       # System architecture & design
│   ├── INSTALLATION.md       # Setup & installation guide
│   ├── API.md               # API documentation
│   ├── LINUX_LOGS.md        # Linux log collection guide
│   ├── WINDOWS_LOGS.md      # Windows log collection guide
│   └── GEMINI_SETUP.md      # Gemini AI setup guide
│
├── tests/                     # Unit and integration tests
│   ├── test_collectors.py    # Collector tests
│   ├── test_processors.py    # Processor tests
│   ├── test_anomaly_detector.py # Anomaly detection tests
│   ├── test_gemini.py        # Gemini integration tests
│   └── test_dashboard_api.py # Dashboard API tests
│
├── .env.example              # Environment variables template
├── .gitignore               # Git ignore rules
├── Dockerfile               # Docker container definition
├── docker-compose.yml       # Multi-container setup
├── requirements.txt         # Python dependencies
└── LICENSE                  # License file
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- Google Gemini API key
- SSH access to Linux servers or WinRM for Windows servers

### Using Docker Compose (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/medicom82/LogAgent.git
cd LogAgent

# 2. Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 3. Start all services
docker-compose up -d

# 4. Access dashboard
open http://localhost:5000
```

### Local Development

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize database
python -c "from database import init_db; init_db()"

# 4. Run dashboard
cd dashboard
python app.py
```

## 📊 Dashboard Features

### Real-time Statistics
- Total logs collected in last 24 hours
- Critical/High severity anomalies
- Active server count

### Log Management
- View and filter logs by type, server, severity
- Search across log entries
- Pagination support

### Anomaly Detection
- Visual anomaly timeline
- Severity distribution charts
- Confidence scoring
- Investigation status tracking

### AI-Powered Analysis
- Gemini AI anomaly analysis
- Automatic SQL query generation
- Threat assessment
- Remediation recommendations

### Server Monitoring
- Server health status
- Last heartbeat tracking
- Log type distribution per server

## 🔗 Log Collection

### Linux Servers

Supports collection from:
- **Apache Web Server**: Access and error logs
- **MySQL Database**: Query logs, slow query logs
- **Linux Audit**: System audit logs
- **ISPConfig**: Control panel logs
- **System Logs**: Syslog, Auth logs
- **Custom Applications**: Generic file monitoring

**Authentication**: SSH key-based or password

```python
from collectors.linux_collector import create_linux_collector

collector = create_linux_collector(
    server_id='linux-01',
    hostname='linux.example.com',
    username='ubuntu',
    private_key_path='/path/to/key'
)

collector.collect_apache_logs()
collector.collect_mysql_logs()
collector.collect_audit_logs()
```

### Windows Servers

Supports collection from:
- **IIS**: Application and access logs
- **Windows Event Logs**: Security, System, Application
- **Performance Counters**: CPU, Memory, Disk
- **Application Logs**: Custom application events

**Authentication**: WinRM with username/password

```python
from collectors.windows_collector import create_windows_collector

collector = create_windows_collector(
    server_id='windows-01',
    hostname='windows.example.com',
    username='administrator',
    password='password'
)

collector.collect_iis_logs()
collector.collect_event_logs()
collector.collect_security_logs()
```

## 🤖 Anomaly Detection

### Detection Methods

1. **Statistical Analysis**
   - Baseline calculation (mean, stddev)
   - Spike detection (requests, error rates)
   - Trend analysis

2. **Machine Learning**
   - Isolation Forest for outlier detection
   - Clustering for pattern recognition
   - Behavioral analysis

3. **Rule-Based**
   - SQL injection patterns
   - XSS attempts
   - Failed login attempts
   - Privilege escalation
   - Suspicious network activity

4. **Behavioral**
   - User activity baselines
   - Unusual access times
   - Abnormal data volumes

### Confidence Scoring

- **0.0 - 0.33**: Low confidence
- **0.33 - 0.66**: Medium confidence
- **0.66 - 1.0**: High confidence (requires review)

## 🧠 Gemini AI Integration

### Capabilities

- **Log Analysis**: Understanding and categorizing anomalies
- **Query Generation**: Creating SQL queries for investigation
- **Threat Assessment**: Evaluating security impact
- **Recommendations**: Suggesting remediation steps
- **Summarization**: Condensing log information

### Usage

```python
from processors.gemini_integration import get_gemini_analyzer

analyzer = get_gemini_analyzer()

# Analyze anomaly
analysis = analyzer.analyze_anomaly({
    'anomaly_type': 'SQL_INJECTION_ATTEMPT',
    'severity': 'CRITICAL',
    'log_line': 'SELECT * FROM users WHERE id = 1 OR 1=1'
})

# Generate investigation query
query = analyzer.generate_query({
    'anomaly_type': 'FAILED_LOGINS',
    'server_id': 'linux-01',
    'time_window': '24 hours'
})
```

## 🏗️ Architecture

### Components

1. **Log Collectors**: Agents that gather logs from servers
2. **Message Queue**: Kafka for buffering and distributing logs
3. **Stream Processing**: Apache Flink for real-time transformations
4. **Anomaly Detection**: Statistical and ML algorithms
5. **AI Integration**: Google Gemini for analysis
6. **Database**: MySQL for storage and querying
7. **Dashboard**: Flask web UI for visualization

### Data Flow

```
Servers → Collectors → Kafka → Flink → Processors → MySQL ← Dashboard
                                         ↓
                                    Gemini AI
```

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed diagrams.

## 📚 Documentation

- [Architecture & Design](docs/ARCHITECTURE.md) - System overview and data flow
- [Installation Guide](docs/INSTALLATION.md) - Setup instructions
- [API Documentation](docs/API.md) - REST API endpoints
- [Linux Logs Guide](docs/LINUX_LOGS.md) - Linux collection setup
- [Windows Logs Guide](docs/WINDOWS_LOGS.md) - Windows collection setup
- [Gemini Setup](docs/GEMINI_SETUP.md) - AI integration guide

## 🔧 Configuration

### Environment Variables

```bash
# Database
MYSQL_HOST=localhost
MYSQL_USER=logagent
MYSQL_PASSWORD=logagent_password
MYSQL_DATABASE=logagent

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Gemini AI
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-pro
GEMINI_TEMPERATURE=0.3

# Flask
FLASK_ENV=development
FLASK_PORT=5000

# System
LOG_RETENTION_DAYS=90
ANOMALY_CHECK_INTERVAL_SECONDS=300
DEBUG=False
```

See `.env.example` for all available options.

## 🧪 Testing

Run the test suite:

```bash
# All tests
pytest

# Specific test file
pytest tests/test_collectors.py

# With coverage
pytest --cov=. --cov-report=html

# Verbose output
pytest -v
```

## 🐳 Docker Support

### Single Container

```bash
docker build -t logagent .
docker run -p 5000:5000 logagent
```

### Docker Compose (Recommended)

```bash
docker-compose up -d
docker-compose logs -f
docker-compose down
```

Services included:
- MySQL database
- Zookeeper
- Kafka broker
- Flink JobManager & TaskManager
- LogAgent Flask application

## 📊 API Endpoints

### Dashboard Stats
```
GET /api/dashboard/stats
```
Returns: Logs count, anomalies, servers, alerts

### Logs
```
GET /api/logs?page=1&per_page=50&log_type=apache&severity=ERROR
```
Returns: Paginated log entries

### Anomalies
```
GET /api/anomalies?page=1&per_page=50&severity=CRITICAL
POST /api/anomalies/<id>/analyze
PUT /api/anomalies/<id>/update
```

### Servers
```
GET /api/servers
```
Returns: List of monitored servers

### Health
```
GET /api/health
```
Returns: System health status

See [API.md](docs/API.md) for complete API documentation.

## 🔐 Security

- SSH key-based authentication for Linux servers
- WinRM with encrypted credentials for Windows
- Kafka SASL/SSL support
- Database password encryption
- API rate limiting
- Audit logging of AI interactions
- GDPR-compliant data deletion

## 🛠️ Narzędzie CLI (bez zależności)

Pakiet zawiera lekki interfejs wiersza poleceń `logagent`, który **nie wymaga** żadnych ciężkich zależności (MySQL, Kafka, scikit-learn, Gemini) — pozwala szybko sprawdzić wersję i konfigurację środowiska:

```bash
logagent --version               # logagent 1.0.0
logagent --check-config          # raport obecności zmiennych środowiskowych
```

`--check-config` zwraca exit code `1`, gdy brakuje wymaganych zmiennych (`MYSQL_HOST`, `MYSQL_USER`, `MYSQL_DATABASE`) — pomocne przy diagnozowaniu „dashboard nie startuje”.

## 🧪 Testy

Podstawowe moduły (`logparser`, `processors/anomaly_detector`, `cli`) są pokryte testami uruchamianymi **bez** bazy danych i ciężkich zależności (importy są bronione defensywnie, a detekcje niepotrzebujące bazy działają w trybie offline):

```bash
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python pytest
.venv/bin/python -m pytest tests/
```

Parsowanie logów wydzielono do modułu `logparser.py` (czysty stdlib). `timestamp` wpisu pochodzi teraz **z samej linii logu** (np. `[10/Oct/2000:13:55:36 -0700]`), a nie z zegara kolektora — bez tego okna czasowe wykrywania anomalii, szeregi czasowe dashboardu i korelacja między źródłami są mylące.

## 📖 Dokumentacja
## 📈 Performance

- Kafka: 100K+ events/second throughput
- Flink: Sub-second latency processing
- MySQL: Optimized indexes for <100ms queries
- Dashboard: Real-time updates every 30 seconds

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Issues**: GitHub Issues for bug reports and features
- **Documentation**: See `/docs` directory
- **Examples**: Check `/tests` for usage examples

## 🗺️ Roadmap

- [ ] Elasticsearch integration for advanced searching
- [ ] Machine learning model training UI
- [ ] Slack/Email alerting
- [ ] Dashboard authentication & RBAC
- [ ] Distributed processing with multiple Flink clusters
- [ ] Prometheus metrics export
- [ ] Grafana dashboard templates
- [ ] Mobile app for alerts

## 📞 Contact

For questions or suggestions:
- GitHub: [@medicom82](https://github.com/medicom82)
- Issues: [GitHub Issues](https://github.com/medicom82/LogAgent/issues)

---

**Made with ❤️ for real-time log analysis**
