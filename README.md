# LogAgent - Real-time Log Analysis System

**LogAgent** to zaawansowany system do analizy logów w czasie rzeczywistym z wykrywaniem anomalii i integracją AI (Google Gemini).

## 🎯 Funkcjonalności

- ✅ Analiza logów z wielu serwerów Linux i Windows
- ✅ Wsparcie dla: Apache, MySQL, Audit logs, ISPConfig
- ✅ Wykrywanie anomalii w czasie rzeczywistym
- ✅ Integracja z Google Gemini AI
- ✅ Pipeline: Kafka + Apache Flink
- ✅ Baza danych MySQL
- ✅ Panel monitorujący (Dashboard)
- ✅ Generowanie zapytań automatyczne

## 📁 Struktura Projektu

```
LogAgent/
├── README.md
├── docker-compose.yml              # Docker orchestration
├── requirements.txt                 # Python dependencies
│
├── config/
│   ├── kafka.conf                   # Kafka configuration
│   ├── flink.conf                   # Apache Flink configuration
│   ├── mysql.conf                   # MySQL configuration
│   └── gemini.conf                  # Gemini AI configuration
│
├── database/
│   ├── schema.sql                   # MySQL schema dla logów
│   ├── migrations/
│   └── init.sql                     # Initialize database
│
├── collectors/
│   ├── linux_collector.py           # Zbieranie logów z Linux
│   ├── windows_collector.py         # Zbieranie logów z Windows
│   ├── apache_collector.py          # Apache logs
│   ├── mysql_collector.py           # MySQL logs
│   ├── audit_collector.py           # Audit logs
│   └── ispconfig_collector.py       # ISPConfig virtual hosts
│
├── processors/
│   ├── log_parser.py                # Parsing logów
│   ├── anomaly_detector.py          # Wykrywanie anomalii
│   ├── gemini_integration.py        # Integracja z Gemini
│   └── query_generator.py           # Generowanie zapytań SQL
│
├── flink/
│   ├── job.py                       # Apache Flink job
│   ├── transformations.py           # Transformacje danych
│   └── sinks.py                     # Wyjścia Flink
│
├── kafka/
│   ├── producer.py                  # Kafka producer
│   ├── consumer.py                  # Kafka consumer
│   └── topics_setup.py              # Konfiguracja topików
│
├── dashboard/
│   ├── app.py                       # Flask/FastAPI aplikacja
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── charts.js
│   └── templates/
│       ├── index.html
│       ├── logs.html
│       ├── anomalies.html
│       └── settings.html
│
├── docs/
│   ├── architecture.md              # Architektura systemu
│   ├── installation.md              # Instrukcja instalacji
│   ├── linux_logs.md                # Konfiguracja Linux logów
│   ├── windows_logs.md              # Konfiguracja Windows logów
│   ├── gemini_setup.md              # Konfiguracja Gemini
│   └── api.md                       # API dokumentacja
│
└── tests/
    ├── test_collectors.py
    ├── test_processors.py
    └── test_gemini.py
```

## 🚀 Szybki Start

```bash
# 1. Clone repozytorium
git clone https://github.com/medicom82/LogAgent.git
cd LogAgent

# 2. Instalacja zależności
pip install -r requirements.txt

# 3. Docker Compose
docker-compose up -d

# 4. Inicjalizacja bazy danych
python -c "from database.init import init_db; init_db()"

# 5. Uruchomienie kolekcji logów
python collectors/linux_collector.py

# 6. Panel monitorujący
# http://localhost:5000
```

## 🏗️ Architektura

```
[Serwery Linux/Windows]
        ↓
[Collectors] (Apache, MySQL, Audit, ISPConfig)
        ↓
[Kafka Topics] (log-stream, anomalies, events)
        ↓
[Apache Flink] (Stream Processing, Transformacje)
        ↓
[MySQL Database] (Przechowywanie logów & metadanych)
        ↓
[Processors] (Anomaly Detection, Gemini AI)
        ↓
[Dashboard] (Panel monitorujący, Alerty)
        ↓
[Alerting System] (Email, Slack, Webhooks)
```

## 📊 Obsługiwane Logi

### Linux
- ✅ Apache Access & Error Logs
- ✅ MySQL General Query Log, Error Log
- ✅ Audit Log (auditd)
- ✅ ISPConfig Virtual Hosts
- ✅ System Logs (/var/log/syslog)
- ✅ Auth Logs (/var/log/auth.log)

### Windows
- ✅ IIS Logs
- ✅ Windows Event Logs
- ✅ Windows Security Logs
- ✅ Application Logs

## 🤖 Gemini AI Integration

System automatycznie:
- Generuje zapytania SQL na podstawie wykrytych anomalii
- Tłumaczy logi do naturalnego języka
- Proponuje rozwiązania problemów
- Uczy się z historii anomalii

## 💾 Baza Danych

- **Engine**: MySQL 8.0+
- **Tabele**: logs, anomalies, queries, alerts
- **Indexing**: Zoptymalizowany dla szybkich wyszukiwań
- **Partitioning**: Po dacie dla wydajności

## 🔧 Konfiguracja

Każdy komponent ma dedykowany plik konfiguracyjny w `config/`:
- `kafka.conf` - Broker settings
- `flink.conf` - Job parameters
- `mysql.conf` - Database credentials
- `gemini.conf` - API keys & settings

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

Zobacz folder `/docs` dla szczegółowych instrukcji:
- Instalacja i konfiguracja
- Obsługa różnych typów logów
- Integracja Gemini
- API Reference
- Troubleshooting

## 🤝 Contributing

Zapraszamy do współpracy!

## 📄 Licencja

MIT License - patrz LICENSE file

---

**Autor**: medicom82  
**Status**: 🚧 Development  
**Ostatnia aktualizacja**: 2026-09-03
