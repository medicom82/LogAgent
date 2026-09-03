// Dashboard JavaScript

let chartsCache = {};
let autoRefreshInterval = 30000; // 30 seconds

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', function() {
    updateCurrentTime();
    loadDashboardStats();
    loadRecentAnomalies();
    initCharts();
    
    // Auto-refresh
    setInterval(loadDashboardStats, autoRefreshInterval);
    setInterval(loadRecentAnomalies, autoRefreshInterval);
});

// ============================================
// Navigation Functions
// ============================================

function showDashboard() {
    hideAllSections();
    document.getElementById('dashboard-section').style.display = 'block';
    loadDashboardStats();
    loadRecentAnomalies();
}

function showLogs() {
    hideAllSections();
    document.getElementById('logs-section').style.display = 'block';
    loadLogs();
}

function showAnomalies() {
    hideAllSections();
    document.getElementById('anomalies-section').style.display = 'block';
    loadAnomalies();
}

function showServers() {
    hideAllSections();
    document.getElementById('servers-section').style.display = 'block';
    loadServers();
}

function showAlerts() {
    hideAllSections();
    alert('Alerts section coming soon!');
}

function hideAllSections() {
    document.querySelectorAll('.section').forEach(section => {
        section.style.display = 'none';
    });
}

// ============================================
// Dashboard Functions
// ============================================

function loadDashboardStats() {
    fetch('/api/dashboard/stats')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('total-logs').textContent = formatNumber(data.logs.total_logs || 0);
                document.getElementById('critical-anomalies').textContent = data.anomalies.critical_count || 0;
                document.getElementById('high-anomalies').textContent = data.anomalies.high_count || 0;
                document.getElementById('active-servers').textContent = data.logs.active_servers || 0;
            }
        })
        .catch(error => console.error('Error loading stats:', error));
    
    loadTimelineChart();
    loadSeverityChart();
}

function loadRecentAnomalies() {
    fetch('/api/anomalies?page=1&per_page=5')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.anomalies) {
                const tbody = document.getElementById('anomalies-tbody');
                tbody.innerHTML = '';
                
                data.anomalies.forEach(anomaly => {
                    const row = `
                        <tr>
                            <td class="timestamp">${formatDate(anomaly.detected_at)}</td>
                            <td>${anomaly.anomaly_type}</td>
                            <td><span class="badge badge-${anomaly.severity.toLowerCase()}">${anomaly.severity}</span></td>
                            <td>${anomaly.description || 'N/A'}</td>
                            <td>${anomaly.investigation_status}</td>
                            <td>
                                <button class="btn btn-sm btn-info" onclick="analyzeAnomaly(${anomaly.id})">
                                    <i class="fas fa-brain"></i> Analyze
                                </button>
                            </td>
                        </tr>
                    `;
                    tbody.innerHTML += row;
                });
            }
        })
        .catch(error => console.error('Error loading anomalies:', error));
}

function loadLogs() {
    fetch('/api/logs?page=1&per_page=50')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.logs) {
                const tbody = document.getElementById('logs-tbody');
                tbody.innerHTML = '';
                
                data.logs.forEach(log => {
                    const row = `
                        <tr>
                            <td class="timestamp">${formatDate(log.timestamp)}</td>
                            <td>${log.server_id || 'N/A'}</td>
                            <td><span class="badge bg-secondary">${log.log_type}</span></td>
                            <td>${log.source_ip || 'N/A'}</td>
                            <td><span class="badge badge-${log.severity.toLowerCase()}">${log.severity}</span></td>
                            <td>${log.path || log.database_name || log.user || 'N/A'}</td>
                        </tr>
                    `;
                    tbody.innerHTML += row;
                });
            }
        })
        .catch(error => console.error('Error loading logs:', error));
}

function loadAnomalies() {
    fetch('/api/anomalies?page=1&per_page=50')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.anomalies) {
                const tbody = document.getElementById('anomalies-main-tbody');
                tbody.innerHTML = '';
                
                data.anomalies.forEach(anomaly => {
                    const confidencePercent = Math.round((anomaly.confidence_score || 0) * 100);
                    const row = `
                        <tr>
                            <td class="timestamp">${formatDate(anomaly.detected_at)}</td>
                            <td>${anomaly.anomaly_type}</td>
                            <td><span class="badge badge-${anomaly.severity.toLowerCase()}">${anomaly.severity}</span></td>
                            <td>${anomaly.description || 'N/A'}</td>
                            <td>
                                <div class="progress" style="height: 20px;">
                                    <div class="progress-bar" style="width: ${confidencePercent}%">${confidencePercent}%</div>
                                </div>
                            </td>
                            <td>${anomaly.investigation_status}</td>
                            <td>
                                <button class="btn btn-sm btn-info" onclick="analyzeAnomaly(${anomaly.id})" title="AI Analysis">
                                    <i class="fas fa-magic"></i>
                                </button>
                                <button class="btn btn-sm btn-warning" onclick="updateAnomalyStatus(${anomaly.id})" title="Update">
                                    <i class="fas fa-edit"></i>
                                </button>
                            </td>
                        </tr>
                    `;
                    tbody.innerHTML += row;
                });
            }
        })
        .catch(error => console.error('Error loading anomalies:', error));
}

function loadServers() {
    fetch('/api/servers')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.servers) {
                const row = document.getElementById('servers-row');
                row.innerHTML = '';
                
                data.servers.forEach(server => {
                    const status = server.is_active ? 'active' : 'inactive';
                    const lastHeartbeat = server.last_heartbeat ? formatDate(server.last_heartbeat) : 'Never';
                    
                    const card = `
                        <div class="col-md-6 col-lg-4">
                            <div class="card">
                                <div class="card-body">
                                    <h5 class="card-title">
                                        <span class="server-status ${status}"></span>
                                        ${server.hostname}
                                    </h5>
                                    <p class="card-text">
                                        <strong>Server ID:</strong> ${server.server_id}<br>
                                        <strong>IP:</strong> ${server.ip_address || 'N/A'}<br>
                                        <strong>OS:</strong> ${server.os_type} ${server.os_version || ''}<br>
                                        <strong>Status:</strong> <span class="badge bg-${status === 'active' ? 'success' : 'danger'}">${status}</span><br>
                                        <strong>Last Heartbeat:</strong> <span class="timestamp">${lastHeartbeat}</span>
                                    </p>
                                </div>
                            </div>
                        </div>
                    `;
                    row.innerHTML += card;
                });
            }
        })
        .catch(error => console.error('Error loading servers:', error));
}

function analyzeAnomaly(anomalyId) {
    const modal = new bootstrap.Modal(document.getElementById('analysisModal'));
    document.getElementById('analysis-content').innerHTML = '<div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div>';
    modal.show();
    
    fetch(`/api/anomalies/${anomalyId}/analyze`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                let content = `
                    <div class="alert alert-info">
                        <h6>🤖 Gemini AI Analysis</h6>
                        <p>${data.analysis}</p>
                    </div>
                    <hr>
                    <h6>📊 Investigation Query</h6>
                    <pre class="bg-light p-3" style="border-radius: 4px; overflow-x: auto;"><code>${escapeHtml(data.generated_query)}</code></pre>
                `;
                document.getElementById('analysis-content').innerHTML = content;
            } else {
                document.getElementById('analysis-content').innerHTML = `<div class="alert alert-danger">Error: ${data.error}</div>`;
            }
        })
        .catch(error => {
            console.error('Error analyzing anomaly:', error);
            document.getElementById('analysis-content').innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
        });
}

function updateAnomalyStatus(anomalyId) {
    const status = prompt('Enter new status (new, investigating, resolved, ignored):');
    if (status) {
        fetch(`/api/anomalies/${anomalyId}/update`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: status })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Anomaly updated successfully', 'success');
                loadAnomalies();
            } else {
                showNotification('Error updating anomaly', 'error');
            }
        })
        .catch(error => console.error('Error updating anomaly:', error));
    }
}

function filterAnomalies() {
    loadAnomalies();
}

// ============================================
// Chart Functions
// ============================================

function initCharts() {
    loadTimelineChart();
    loadSeverityChart();
}

function loadTimelineChart() {
    fetch('/api/stats/timeline?hours=24')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.data) {
                const ctx = document.getElementById('logsChart').getContext('2d');
                
                // Process data by log type
                const logTypes = [...new Set(data.data.map(item => item.log_type))];
                const datasets = logTypes.map((type, index) => {
                    const colors = ['#3498db', '#e74c3c', '#f39c12', '#27ae60', '#9b59b6'];
                    return {
                        label: type,
                        data: data.data.filter(item => item.log_type === type).map(item => item.count),
                        borderColor: colors[index % colors.length],
                        backgroundColor: colors[index % colors.length] + '40',
                        tension: 0.3
                    };
                });
                
                if (chartsCache.logsChart) chartsCache.logsChart.destroy();
                chartsCache.logsChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: [...new Set(data.data.map(item => item.hour))],
                        datasets: datasets
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { position: 'top' } }
                    }
                });
            }
        })
        .catch(error => console.error('Error loading timeline chart:', error));
}

function loadSeverityChart() {
    fetch('/api/stats/severity')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.data) {
                const ctx = document.getElementById('severityChart').getContext('2d');
                
                const colors = {
                    'CRITICAL': '#e74c3c',
                    'HIGH': '#f39c12',
                    'MEDIUM': '#f1c40f',
                    'LOW': '#3498db'
                };
                
                if (chartsCache.severityChart) chartsCache.severityChart.destroy();
                chartsCache.severityChart = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: data.data.map(item => item.severity),
                        datasets: [{
                            data: data.data.map(item => item.count),
                            backgroundColor: data.data.map(item => colors[item.severity] || '#95a5a6')
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false
                    }
                });
            }
        })
        .catch(error => console.error('Error loading severity chart:', error));
}

// ============================================
// Utility Functions
// ============================================

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateCurrentTime() {
    const now = new Date();
    document.getElementById('current-time').textContent = now.toLocaleTimeString();
    setTimeout(updateCurrentTime, 1000);
}

function saveSettings() {
    const interval = document.getElementById('refresh-interval').value;
    autoRefreshInterval = parseInt(interval) * 1000;
    showNotification('Settings saved', 'success');
}

function showNotification(message, type = 'info') {
    const alertClass = `alert-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'}`;
    const alert = document.createElement('div');
    alert.className = `alert ${alertClass} position-fixed top-0 end-0 m-3`;
    alert.style.zIndex = '9999';
    alert.textContent = message;
    document.body.appendChild(alert);
    setTimeout(() => alert.remove(), 3000);
}
