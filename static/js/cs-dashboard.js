/* cs - dashboard.js - Logic for CS / CX Dashboard with REAL Data */

document.addEventListener('DOMContentLoaded', function () {
    loadRealMetrics();
    renderCockpitFeed();
    renderPlannerEvaluations();
});

async function loadRealMetrics() {
    try {
        const response = await fetch('/api/cs/metrics');
        const data = await response.json();

        if (data.error) throw new Error(data.error);

        // 1. Renderizar Métricas de Topo
        renderCSMetrics(data);

        // 2. Renderizar Gráficos com Dados Reais
        initCharts(data);

        // 3. Renderizar Ranking LTV
        renderTopLtv(data.top_ltv);

    } catch (error) {
        console.error('Erro ao carregar métricas reais:', error);
        // Fallback para mock se a API falhar (opcional, mas bom para dev)
    }
}

// Chart.js Initialization
function initCharts(apiData) {
    if (!apiData || !apiData.history) {
        console.error('Dados históricos ausentes no retorno da API');
        return;
    }
    const historical = apiData.history;

    // 1. Gráfico de LTV (POR QUARTER)
    const ltvCtx = document.getElementById('ltvChart');
    if (ltvCtx && historical.quarterly) {
        const oldChart = Chart.getChart(ltvCtx);
        if (oldChart) oldChart.destroy();

        new Chart(ltvCtx, {
            type: 'line',
            data: {
                labels: historical.quarterly.labels,
                datasets: [{
                    label: 'LTV Médio / Quarter (R$)',
                    data: historical.quarterly.ltv,
                    borderColor: '#d61616',
                    backgroundColor: 'rgba(214, 22, 22, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 6,
                    pointBackgroundColor: '#d61616'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true, labels: { color: '#a0a0a0' } }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#a0a0a0' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#a0a0a0' }
                    }
                }
            }
        });
    }

    // 2. Gráfico de Churn (MENSAL 2026)
    const churnCtx = document.getElementById('churnChart');
    if (churnCtx) {
        const oldChart = Chart.getChart(churnCtx);
        if (oldChart) oldChart.destroy();

        // Atualizar label de porcentagem do mês atual
        const lastMonthRate = ((apiData.churn_count / apiData.clients) * 100).toFixed(1);
        const labelEl = document.getElementById('churnPercentLabel');
        if (labelEl) labelEl.textContent = `${lastMonthRate}% Churn Rate (atualmente em Mar/26)`;

        new Chart(churnCtx, {
            type: 'bar',
            data: {
                labels: historical.monthly.labels,
                datasets: [
                    {
                        label: 'Empresas Ativas',
                        data: historical.monthly.active,
                        backgroundColor: 'rgba(214, 22, 22, 0.3)',
                        borderColor: '#d61616',
                        borderWidth: 1,
                        borderRadius: 5
                    },
                    {
                        label: 'Churns (Cantidade)',
                        data: historical.monthly.churn,
                        backgroundColor: '#d61616',
                        borderRadius: 5
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { color: '#a0a0a0', boxWidth: 12 }
                    },
                    tooltip: {
                        callbacks: {
                            afterLabel: function (context) {
                                if (context.datasetIndex === 1) {
                                    const index = context.dataIndex;
                                    const rate = ((historical.monthly.churn[index] / historical.monthly.active[index]) * 100).toFixed(1);
                                    return `Taxa: ${rate}%`;
                                }
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#a0a0a0' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#a0a0a0' }
                    }
                }
            }
        });
    }
}

function renderTopLtv(topProjects) {
    const listContainer = document.getElementById('topLtvList');
    if (!listContainer) return;

    listContainer.innerHTML = topProjects.map(p => `
        <li>
            <span>${p.name}</span>
            <span class="val">${p.val}</span>
        </li>
    `).join('');
}

// Render Metrics Header
function renderCSMetrics(data) {
    const metricsContainer = document.getElementById('csMetrics');
    if (!metricsContainer) return;

    const mainMetrics = [
        { label: 'MRR Total', value: `R$ ${data.mrr.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`, icon: 'fa-money-bill-trend-up' },
        { label: 'Churn do Mês', value: data.churn_count.toString(), icon: 'fa-user-minus' },
        { label: 'LTV Médio', value: `R$ ${data.ltv_avg.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`, icon: 'fa-clock-rotate-left' },
        { label: 'Health Score', value: `${data.health_score}%`, icon: 'fa-heart-pulse' }
    ];

    metricsContainer.innerHTML = mainMetrics.map(m => `
        <div class="metric-card-premium">
            <i class="fas ${m.icon}"></i>
            <h3>${m.label}</h3>
            <div class="value">${m.value}</div>
        </div>
    `).join('');

    const secondaryContainer = document.getElementById('secondaryMetrics');
    if (secondaryContainer) {
        const secondaryMetrics = [
            { label: 'Clientes Ativos', value: data.clients.toString(), icon: 'fa-layer-group' },
            { label: 'Projetos por Cohort', value: 'Mar/24: 08', icon: 'fa-calendar-check' }, // Mock por enquanto
            { label: '%CSP Médio', value: '92%', icon: 'fa-percentage' } // Mock por enquanto
        ];

        secondaryContainer.innerHTML = secondaryMetrics.map(m => `
            <div class="metric-card-premium">
                <i class="fas ${m.icon}"></i>
                <h3>${m.label}</h3>
                <div class="value">${m.value}</div>
            </div>
        `).join('');
    }
}

const COCKPIT_DATA = [
    { type: 'health-low', severity: 'critical', client: 'João Silva', title: 'Health Score Crítico', body: '3 projetos com Health Score abaixo de 40.', time: 'Ontem' },
    { type: 'ads', severity: 'critical', client: 'Restaurante Solar', title: 'Queda de Performance — Meta Ads', body: 'Queda de 20% no ROAS nas últimas 24h.', time: '3h atrás' },
    { type: 'ads', severity: 'critical', client: 'Tech Solutions', title: 'Budget Zerado — Google Ads', body: 'Orçamento da campanha principal esgotado.', time: '5h atrás' },
    { type: 'ekyte', severity: 'warning', client: 'Solar Energy', title: 'Planejamento Ekyte Atrasado', body: 'Planejamento estratégico pendente há 5 dias.', time: '1h atrás' },
    { type: 'ekyte', severity: 'warning', client: 'Padaria Central', title: 'Tarefa Vencida no Ekyte', body: '2 tarefas vencidas sem responsável atribuído.', time: '2h atrás' },
    { type: 'wpp', severity: 'warning', client: 'Tech Solutions', title: 'Grupo Silencioso (+48h)', body: 'Nenhuma interação no grupo há mais de 2 dias.', time: '5h atrás' },
    { type: 'csat', severity: 'warning', client: 'Mercado Verde', title: 'CSAT Baixo Recebido: 4.0', body: 'Avaliação abaixo do esperado no check-in quinzenal.', time: 'Ontem' },
    { type: 'resultado', severity: 'info', client: 'V4 Company Lisboa', title: 'Meta de MRR Atingida', body: 'Projeto atingiu 105% da meta mensal.', time: '10min atrás' },
    { type: 'csat', severity: 'info', client: 'Padaria Central', title: 'Novo CSAT Recebido: 9.5', body: 'Excelente feedback após o check-in quinzenal.', time: 'Ontem' }
];

const COCKPIT_FILTER_LABELS = {
    all: { label: 'Todos', icon: 'fa-inbox' },
    'health-low': { label: 'Health', icon: 'fa-heart-pulse' },
    ads: { label: 'Ads', icon: 'fa-bullhorn' },
    ekyte: { label: 'Ekyte', icon: 'fa-diagram-project' },
    wpp: { label: 'WhatsApp', icon: 'fa-comments' },
    resultado: { label: 'Resultado', icon: 'fa-chart-line' },
    csat: { label: 'CSAT', icon: 'fa-star' }
};

const SEVERITY_META = {
    critical: { label: 'Crítico', order: 0 },
    warning: { label: 'Aviso', order: 1 },
    info: { label: 'Info', order: 2 }
};

// Por padrão mostra só críticos e avisos
let activeFilter = 'all';
let showAllSeverity = false;

function renderCockpitFeed() {
    renderCockpitStats();
    renderCockpitTable();
}

function renderCockpitStats() {
    const container = document.getElementById('cockpitStats');
    if (!container) return;

    const counts = { critical: 0, warning: 0, info: 0 };
    COCKPIT_DATA.forEach(item => counts[item.severity]++);

    container.innerHTML = `
        <div class="cockpit-stats-row">
            <div class="cockpit-stat-pills">
                <div class="stat-pill pill-critical"><i class="fas fa-circle-xmark"></i> ${counts.critical} Crítico${counts.critical !== 1 ? 's' : ''}</div>
                <div class="stat-pill pill-warning"><i class="fas fa-triangle-exclamation"></i> ${counts.warning} Aviso${counts.warning !== 1 ? 's' : ''}</div>
                <div class="stat-pill pill-info"><i class="fas fa-circle-check"></i> ${counts.info} Informativo${counts.info !== 1 ? 's' : ''}</div>
            </div>
            <div class="cockpit-filter-chips" id="cockpitFilters"></div>
            <button class="cockpit-toggle-btn" id="toggleSeverityBtn">
                <i class="fas ${showAllSeverity ? 'fa-eye-slash' : 'fa-eye'}"></i>
                ${showAllSeverity ? 'Ocultar informativos' : 'Mostrar todos'}
            </button>
        </div>
    `;

    // Renderiza os chips dentro do container
    const filterContainer = document.getElementById('cockpitFilters');
    if (filterContainer) {
        filterContainer.innerHTML = Object.entries(COCKPIT_FILTER_LABELS).map(([key, val]) => `
            <button class="filter-chip ${activeFilter === key ? 'active' : ''}" data-filter="${key}">
                <i class="fas ${val.icon}"></i> ${val.label}
            </button>
        `).join('');

        filterContainer.querySelectorAll('.filter-chip').forEach(btn => {
            btn.addEventListener('click', () => {
                activeFilter = btn.dataset.filter;
                renderCockpitFeed();
            });
        });
    }

    const toggleBtn = document.getElementById('toggleSeverityBtn');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            showAllSeverity = !showAllSeverity;
            renderCockpitFeed();
        });
    }
}

function renderCockpitTable() {
    const feedContainer = document.getElementById('cockpitFeed');
    if (!feedContainer) return;

    let data = activeFilter === 'all'
        ? COCKPIT_DATA
        : COCKPIT_DATA.filter(i => i.type === activeFilter);

    if (!showAllSeverity) {
        data = data.filter(i => i.severity === 'critical' || i.severity === 'warning');
    }

    data = [...data].sort((a, b) => SEVERITY_META[a.severity].order - SEVERITY_META[b.severity].order);

    if (!data.length) {
        feedContainer.innerHTML = `
            <div class="cockpit-empty">
                <i class="fas fa-check-circle"></i>
                <p>Nenhum alerta encontrado para este filtro.</p>
            </div>`;
        return;
    }

    feedContainer.innerHTML = data.map(item => `
        <div class="cockpit-card severity-${item.severity}">
            <div class="cockpit-card-icon icon-bg-${item.type}">
                <i class="fas ${getIcon(item.type)}"></i>
            </div>
            <div class="cockpit-card-main">
                <div class="cockpit-card-top">
                    <div class="cockpit-card-left">
                        <span class="cockpit-card-client">${item.client}</span>
                        <span class="cockpit-type-chip type-${item.type}">
                            <i class="fas ${getIcon(item.type)}"></i> ${COCKPIT_FILTER_LABELS[item.type]?.label || item.type}
                        </span>
                    </div>
                    <div class="cockpit-card-right">
                        <span class="severity-badge badge-${item.severity}">
                            <i class="fas ${item.severity === 'critical' ? 'fa-circle-xmark' : item.severity === 'warning' ? 'fa-triangle-exclamation' : 'fa-circle-check'}"></i>
                            ${SEVERITY_META[item.severity].label}
                        </span>
                        <span class="cockpit-time">${item.time}</span>
                        <div class="cockpit-quick-actions">
                            <button class="cockpit-action-btn action-resolve" title="Resolver"><i class="fas fa-check"></i> Resolver</button>
                            <button class="cockpit-action-btn action-view" title="Ver detalhes"><i class="fas fa-arrow-right"></i> Ver</button>
                        </div>
                    </div>
                </div>
                <div class="cockpit-card-title">${item.title}</div>
                <div class="cockpit-card-body">${item.body}</div>
            </div>
        </div>
    `).join('');
}

function getIcon(type) {
    const icons = {
        'resultado': 'fa-chart-line',
        'ekyte': 'fa-diagram-project',
        'ads': 'fa-bullhorn',
        'wpp': 'fa-comments',
        'csat': 'fa-star',
        'health-low': 'fa-heart-pulse'
    };
    return icons[type] || 'fa-bell';
}

function renderPlannerEvaluations() {
    const plannerData = [
        { squad: 'Alpha', account: 'Tech Solutions', planner: 'Enzo Maas', score: 5, status: 'Enviado' },
        { squad: 'Beta', account: 'Solar Energy', planner: 'Rebeca Lima', score: 4, status: 'Enviado' },
        { squad: 'Gamma', account: 'Padaria Central', planner: 'Isaac Pontes', score: 2, status: 'Pendente' },
        { squad: 'Alpha', account: 'Restaurante Solar', planner: 'Enzo Maas', score: 3, status: 'Enviado' }
    ];

    const tableBody = document.getElementById('plannerTableBody');
    if (!tableBody) return;

    tableBody.innerHTML = plannerData.map(item => `
        <tr>
            <td><strong>${item.squad}</strong></td>
            <td>${item.account}</td>
            <td>${item.planner}</td>
            <td>
                <span class="planner-score-badge score-${item.score}">
                    ${item.score}/5 - ${getScoreLabel(item.score)}
                </span>
            </td>
            <td>
                <span style="color: ${item.status === 'Enviado' ? '#2ecc71' : '#e74c3c'}">
                    <i class="fas ${item.status === 'Enviado' ? 'fa-check-circle' : 'fa-clock'}"></i>
                    ${item.status}
                </span>
            </td>
        </tr>
    `).join('');
}

function getScoreLabel(score) {
    const labels = { 1: 'Ruim', 2: 'Ruim', 3: 'Médio', 4: 'Bom', 5: 'Ótimo' };
    return labels[score] || 'S/N';
}
