/* cs-dashboard.js - Logic for CS/CX Dashboard with Absolute Data Sketch */

document.addEventListener('DOMContentLoaded', function() {
    initCharts();
    renderCockpitFeed();
    renderCSMetrics();
    renderPlannerEvaluations();
});

// Chart.js Initialization
function initCharts() {
    const ltvCtx = document.getElementById('ltvChart');
    if (ltvCtx) {
        new Chart(ltvCtx, {
            type: 'line',
            data: {
                labels: ['Out', 'Nov', 'Dez', 'Jan', 'Fev', 'Mar'],
                datasets: [{
                    label: 'LTV Médio (R$)',
                    data: [12000, 12500, 13200, 14100, 14800, 15200],
                    borderColor: '#d61616',
                    backgroundColor: 'rgba(214, 22, 22, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointBackgroundColor: '#d61616'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
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

        renderTopLtv();
    }

    const churnCtx = document.getElementById('churnChart');
    if (churnCtx) {
        // Mock data for absolute company counts
        const activeClients = [85, 92, 98, 105, 112, 120];
        const churnCounts = [3, 2, 4, 3, 2, 3];
        const lastMonthRate = ((churnCounts[5] / activeClients[5]) * 100).toFixed(1);
        
        const labelEl = document.getElementById('churnPercentLabel');
        if (labelEl) labelEl.textContent = `${lastMonthRate}% Churn Rate (atual)`;

        new Chart(churnCtx, {
            type: 'bar',
            data: {
                labels: ['Out', 'Nov', 'Dez', 'Jan', 'Fev', 'Mar'],
                datasets: [
                    {
                        label: 'Empresas Ativas',
                        data: activeClients,
                        backgroundColor: 'rgba(214, 22, 22, 0.3)',
                        borderColor: '#d61616',
                        borderWidth: 1,
                        borderRadius: 5
                    },
                    {
                        label: 'Churns (Qtd)',
                        data: churnCounts,
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
                            afterLabel: function(context) {
                                if (context.datasetIndex === 1) { // dataset de churn
                                    const index = context.dataIndex;
                                    const rate = ((churnCounts[index] / activeClients[index]) * 100).toFixed(1);
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

function renderTopLtv() {
    const listContainer = document.getElementById('topLtvList');
    if (!listContainer) return;

    const topProjects = [
        { name: 'V4 Lisboa - Hub', val: 'R$ 152k' },
        { name: 'Solar Energy Pro', val: 'R$ 128k' },
        { name: 'Tech Solutions LTDA', val: 'R$ 95k' },
        { name: 'Padaria Central', val: 'R$ 72k' },
        { name: 'Restaurante Solar', val: 'R$ 58k' }
    ];

    listContainer.innerHTML = topProjects.map(p => `
        <li>
            <span>${p.name}</span>
            <span class="val">${p.val}</span>
        </li>
    `).join('');
}

// Mock Data for Cockpit Feed
const cockpitData = [
    { type: 'resultado', title: 'Meta de MRR Atingida', body: 'O projeto V4 Company - Unidade Lisboa atingiu 105% da meta mensal.', time: '10 min atrás' },
    { type: 'ekyte', title: 'Planejamento Ekyte Atrasado', body: '5 projetos estão com o planejamento estratégico pendente no Ekyte.', time: '1 hora atrás' },
    { type: 'ads', title: 'Queda de Performance - Meta Ads', body: 'O cliente "Restaurante Solar" teve queda de 20% no ROAS nas últimas 24h.', time: '3 horas atrás' },
    { type: 'wpp', title: 'Grupo Silencioso (+48h)', body: 'Nenhuma interação no grupo do cliente "Tech Solutions" há mais de 2 dias.', time: '5 horas atrás' },
    { type: 'csat', title: 'Novo CSAT Recebido: 9.5', body: 'Excelente feedback do cliente "Padaria Central" após o check-in quinzenal.', time: 'Ontem' },
    { type: 'health-low', title: 'Health Score Crítico', body: 'Investidor João Silva possui 3 projetos com Health Score abaixo de 40.', time: 'Ontem' }
];

function renderCockpitFeed() {
    const feedContainer = document.getElementById('cockpitFeed');
    if (!feedContainer) return;

    feedContainer.innerHTML = cockpitData.map(item => `
        <div class="notification-card">
            <div class="notification-icon icon-${item.type}">
                <i class="fas ${getIcon(item.type)}"></i>
            </div>
            <div class="notification-info">
                <div class="notification-header">
                    <span class="notification-title">${item.title}</span>
                    <span class="notification-time">${item.time}</span>
                </div>
                <div class="notification-body">${item.body}</div>
            </div>
        </div>
    `).join('');
}

function getIcon(type) {
    const icons = {
        'resultado': 'fa-chart-line',
        'ekyte': 'fa-project-diagram',
        'ads': 'fa-ad',
        'wpp': 'fa-comments',
        'csat': 'fa-star',
        'health-low': 'fa-heart-broken'
    };
    return icons[type] || 'fa-bell';
}

// Mock Data for CS Metrics
function renderCSMetrics() {
    const metricsContainer = document.getElementById('csMetrics');
    if (!metricsContainer) return;

    const mainMetrics = [
        { label: 'MRR Total', value: 'R$ 450.000', icon: 'fa-money-bill-trend-up' },
        { label: 'Churn Rate', value: '2.4%', icon: 'fa-user-minus' },
        { label: 'LTV Médio', value: 'R$ 15.200', icon: 'fa-clock-rotate-left' },
        { label: 'Health Score', value: '82', icon: 'fa-heart-pulse' }
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
            { label: 'Projetos por Fase', value: '12 Onboarding', icon: 'fa-layer-group' },
            { label: 'Projetos por Cohort', value: 'Mar/24: 08', icon: 'fa-calendar-check' },
            { label: '%CSP Médio', value: '92%', icon: 'fa-percentage' }
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

// Mock Data for Planner Monday
const plannerData = [
    { squad: 'Alpha', account: 'Tech Solutions', planner: 'Enzo Maas', score: 5, status: 'Enviado' },
    { squad: 'Beta', account: 'Solar Energy', planner: 'Rebeca Lima', score: 4, status: 'Enviado' },
    { squad: 'Gamma', account: 'Padaria Central', planner: 'Isaac Pontes', score: 2, status: 'Pendente' },
    { squad: 'Alpha', account: 'Restaurante Solar', planner: 'Enzo Maas', score: 3, status: 'Enviado' }
];

function renderPlannerEvaluations() {
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
