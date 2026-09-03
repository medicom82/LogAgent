# LogAgent Installation Guide

## Prerequisites

- Docker and Docker Compose (for containerized setup)
- Python 3.11+ (for local development)
- MySQL 8.0+ (if not using Docker)
- Kafka 3.x+ (if not using Docker)
- Google Gemini API key

## Quick Start with Docker Compose

### 1. Clone the Repository

```bash
git clone https://github.com/medicom82/LogAgent.git
cd LogAgent
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set your configuration:

```bash
# Most importantly, set your Gemini API key
GEMINI_API_KEY=your_actual_api_key_here
```

### 3. Start Services

```bash
docker-compose up -d
```

This starts:
- MySQL database
- Zookeeper
- Kafka broker with Kafka UI
- Apache Flink (JobManager + TaskManager)
- LogAgent Flask application

### 4. Access Dashboard

```
http://localhost:5000
```

### 5. Monitor Kafka (Optional)

```
http://localhost:8080
```

## Local Development Setup

### 1. Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup

```bash
# Ensure MySQL is running locally
mysql -u root -p

# Create database and user
CREATE DATABASE logagent;
CREATE USER 'logagent'@'localhost' IDENTIFIED BY 'logagent_password';
GRANT ALL PRIVILEGES ON logagent.* TO 'logagent'@'localhost';
FLUSH PRIVILEGES;
```

### 3. Initialize Schema

```bash
python -c "from database import init_db; init_db()"
```

### 4. Run Dashboard

```bash
cd dashboard
python app.py
```

Dashboard will be available at `http://localhost:5000`

## Configuration

### Environment Variables

Key variables in `.env`:

```bash
# Database
MYSQL_HOST=localhost
MYSQL_USER=logagent
MYSQL_PASSWORD=logagent_password
MYSQL_DATABASE=logagent

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Gemini AI
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-pro
GEMINI_TEMPERATURE=0.3

# Flask
FLASK_ENV=development
FLASK_PORT=5000
```

### Database Configuration

Edit `config/mysql.conf` for tuning:

```ini
# Connection pool settings
pool_size=5
max_overflow=10

# Performance
innodb_buffer_pool_size=2G
innodb_log_file_size=512M
max_connections=1000
```

### Kafka Configuration

Edit `config/kafka.conf` for broker settings:

```ini
bootstrap.servers=kafka:29092
num.partitions=3
replication.factor=1
```

## Log Collector Setup

### Linux Servers

#### Option 1: SSH Key-Based (Recommended)

1. Generate SSH key pair:

```bash
ssh-keygen -t rsa -b 4096 -f ~/.ssh/logagent_key
```

2. Copy public key to target server:

```bash
ssh-copy-id -i ~/.ssh/logagent_key.pub user@linux-server.local
```

3. Start collector:

```bash
from collectors.linux_collector import create_linux_collector

collector = create_linux_collector(
    server_id='linux-01',
    hostname='linux-server.local',
    username='ubuntu',
    private_key_path='/root/.ssh/logagent_key'
)

# Start collecting
collector.collect_apache_logs()
collector.collect_mysql_logs()
collector.collect_audit_logs()
```

#### Option 2: Password-Based

```python
collector = create_linux_collector(
    server_id='linux-01',
    hostname='linux-server.local',
    username='ubuntu',
    password='your_password'
)
```

### Windows Servers

1. Ensure WinRM is enabled:

```powershell
# Run as Administrator
Enable-PSRemoting -Force
```

2. Start collector:

```python
from collectors.windows_collector import create_windows_collector

collector = create_windows_collector(
    server_id='windows-01',
    hostname='windows-server.local',
    username='administrator',
    password='your_password'
)

# Start collecting
collector.collect_iis_logs()
collector.collect_event_logs()
collector.collect_security_logs()
```

## Gemini AI Setup

### 1. Get API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key for "Generative Language API"
3. Copy the key to your `.env` file:

```bash
GEMINI_API_KEY=your_api_key_here
```

### 2. Test Integration

```bash
python -c "
from processors.gemini_integration import get_gemini_analyzer
analyzer = get_gemini_analyzer()
result = analyzer.summarize_logs([
    {'log_type': 'apache', 'raw_log_line': '192.168.1.1 - - [01/Jan/2024:12:00:00] \"GET /admin HTTP/1.1\" 403 256'}
])
print(result)
"
```

## Verification

### Health Checks

```bash
# Check Flask API
curl http://localhost:5000/api/health

# Check Kafka topics
kafka-topics.sh --list --bootstrap-server localhost:9092

# Check MySQL
mysql -u logagent -p logagent -e "SELECT COUNT(*) FROM logs;"
```

### Sample Data

The database is initialized with sample data in `database/init.sql`:
- 3 sample servers
- 5 sample log entries
- Default configuration values

## Troubleshooting

### MySQL Connection Issues

```bash
# Test connection
mysql -h localhost -u logagent -p logagent -e "SELECT 1;"

# Check logs
docker logs logagent-mysql
```

### Kafka Issues

```bash
# Check broker status
kafka-broker-api-versions.sh --bootstrap-server localhost:9092

# List topics
kafka-topics.sh --list --bootstrap-server localhost:9092

# View topic contents
kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic log-stream --from-beginning
```

### Flink Issues

```bash
# Check Flink Web UI
http://localhost:8081

# View logs
docker logs logagent-flink-jobmanager
```

### Gemini API Issues

```bash
# Verify API key
curl -X POST "https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key=YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents": [{"parts": [{"text": "Hello"}]}]}'
```

## Backing Up Data

### MySQL Backup

```bash
mysqldump -u logagent -p logagent > logagent_backup.sql
```

### Restore from Backup

```bash
mysql -u logagent -p logagent < logagent_backup.sql
```

## Production Deployment

### Scaling Considerations

1. **Multiple Kafka Brokers**: Add more brokers for high throughput
2. **Flink Cluster**: Deploy multiple TaskManagers
3. **MySQL Replication**: Set up master-slave replication
4. **Load Balancing**: Use nginx/HAProxy for dashboard

### Security Hardening

1. Enable SSL/TLS for Kafka
2. Set up Kafka SASL authentication
3. Use strong database passwords
4. Enable dashboard authentication
5. Regular security updates

## Support

For issues and questions:
- GitHub Issues: https://github.com/medicom82/LogAgent/issues
- Documentation: https://github.com/medicom82/LogAgent/docs
