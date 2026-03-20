/**
 * ranking.js - Lógica do Painel de Ranking
 * Busca dados reais do banco e gerencia filtros
 */

let ALL_RANKING_DATA = [];

document.addEventListener('DOMContentLoaded', () => {
    initRanking();
});

async function initRanking() {
    const grid = document.getElementById('rankingGrid');
    if (!grid) return;

    // Fetch real data
    await fetchRankingData();

    // Setup Filters
    setupFilters();

    // Close modal events
    const modal = document.getElementById('rankingModal');
    const closeBtn = document.querySelector('.modal-close');

    if (closeBtn && modal) {
        closeBtn.onclick = () => closeModal();
        modal.onclick = (e) => {
            if (e.target === modal) closeModal();
        };
    }

    // Escape to close
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
}

async function fetchRankingData() {
    try {
        const response = await fetch('/api/ranking');
        const data = await response.json();

        // Formatar valores para exibição
        ALL_RANKING_DATA = data.map(item => ({
            ...item,
            mrr_formatted: new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(item.mrr)
        }));

        applyFilters();
    } catch (error) {
        console.error("Erro ao buscar dados do ranking:", error);
        document.getElementById('rankingGrid').innerHTML = '<p style="color: white; padding: 20px;">Erro ao carregar dados do banco.</p>';
    }
}

function setupFilters() {
    const filters = ['sortBy', 'filterRole', 'filterLevel', 'filterFlag', 'rankingSearch'];
    filters.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', applyFilters);
        }
    });
}

function applyFilters() {
    const sortBy = document.getElementById('sortBy')?.value || 'daysWithoutChurn';
    const roleFilter = document.getElementById('filterRole')?.value || 'all';
    const levelFilter = document.getElementById('filterLevel')?.value || 'all';
    const flagFilter = document.getElementById('filterFlag')?.value || 'all';
    const search = document.getElementById('rankingSearch')?.value?.toLowerCase() || '';

    console.log("Aplicando filtros:", { sortBy, roleFilter, levelFilter, flagFilter, search });

    const filtered = ALL_RANKING_DATA.filter(inv => {
        // Filtro de Cargo (Refinado para bater exatamente com as opções do HTML)
        let matchRole = true;
        if (roleFilter !== 'all') {
            const userRole = (inv.role || "").toLowerCase();
            const target = roleFilter.toLowerCase();

            // Lógica de match específica para cada categoria do SELECT
            if (target.includes('gestor')) {
                matchRole = userRole.includes('gestor') || userRole.includes('tráfego') || userRole.includes('trafego');
            } else if (target === 'designer') {
                matchRole = userRole.includes('designer');
            } else if (target === 'account') {
                matchRole = userRole.includes('account');
            } else if (target === 'sdr') {
                matchRole = userRole.includes('sdr');
            } else {
                matchRole = userRole.includes(target);
            }
        }

        // Filtro de Level (Normalizado para evitar erros de case)
        const matchLevel = levelFilter === 'all' ||
            (inv.level && inv.level.toUpperCase() === levelFilter.toUpperCase());

        // Filtro de Status/Flag (Normalizado)
        const matchFlag = flagFilter === 'all' ||
            (inv.flag && inv.flag.toLowerCase() === flagFilter.toLowerCase());

        // Filtro de Busca (Nome)
        const matchSearch = inv.name.toLowerCase().includes(search);

        return matchRole && matchLevel && matchFlag && matchSearch;
    });

    console.log("Resultados após filtro:", filtered.length);

    // Ordenação Dinâmica
    const sorted = filtered.sort((a, b) => {
        if (sortBy === 'mrr') {
            const mrrDiff = (parseFloat(b.mrr) || 0) - (parseFloat(a.mrr) || 0);
            if (mrrDiff !== 0) return mrrDiff;
            return (parseInt(b.clientsCount) || 0) - (parseInt(a.clientsCount) || 0); // Desempate por clientes
        } else {
            const churnDiff = (parseInt(b.daysWithoutChurn) || 0) - (parseInt(a.daysWithoutChurn) || 0);
            if (churnDiff !== 0) return churnDiff;
            return (parseFloat(b.mrr) || 0) - (parseFloat(a.mrr) || 0); // Desempate por MRR (Solicitado)
        }
    });

    renderRanking(sorted);
}

function renderRanking(data) {
    const grid = document.getElementById('rankingGrid');
    if (!grid) return;

    if (data.length === 0) {
        grid.innerHTML = '<p style="color: white; padding: 40px; text-align: center; width: 100%;">Nenhum investidor encontrado com os filtros selecionados.</p>';
        return;
    }

    // Podium (First 3)
    const podium = data.slice(0, 3);
    const rest = data.slice(3);

    // Reorder podium to [Silver, Gold, Bronze] for display
    const podiumOrder = [];
    if (podium[1]) podiumOrder.push(podium[1]); // Silver
    if (podium[0]) podiumOrder.push(podium[0]); // Gold
    if (podium[2]) podiumOrder.push(podium[2]); // Bronze

    let html = `
        <div class="ranking-podium">
            ${podiumOrder.map((investor, index) => {
        if (!investor) return '';
        // Identificar a posição real no array original de 3
        let pos = 1;
        if (investor === podium[1]) pos = 2;
        if (investor === podium[2]) pos = 3;

        return `
                <div class="podium-column pos-${pos}" onclick="openInvestorDetails(${investor.id})">
                    <div class="podium-photo-wrap">
                        ${pos === 1 ? '<div class="crown-wrap"><i class="fas fa-crown"></i></div>' : ''}
                        <img class="podium-img" src="${investor.photo || 'static/images/profile_pictures/default.png'}" alt="${investor.name}" onerror="this.src='https://ui-avatars.com/api/?name=${encodeURIComponent(investor.name)}&background=random&color=fff&size=512'">
                        <div class="flag-dot ${investor.flag}"></div>
                    </div>
                    <div class="podium-bar">
                        <div class="bar-number">${pos}</div>
                        <div class="bar-info">
                            <h3 class="bar-name">${investor.name.split(' ')[0]}</h3>
                            <div class="bar-metric">${investor.daysWithoutChurn} DIAS</div>
                        </div>
                    </div>
                </div>
                `;
    }).join('')}
        </div>
        
        <div class="ranking-list-grid">
            <h2 style="color: white; font-weight: 900; font-size: 1.5rem; margin-bottom: 20px; border-left: 4px solid var(--ranking-accent); padding-left: 15px;">TOP RETENÇÃO</h2>
            ${rest.map((investor, index) => `
                <div class="ranking-card" onclick="openInvestorDetails(${investor.id})">
                    <div class="rank-number">#${index + 4}</div>
                    <div class="card-header">
                        <div class="flag-badge ${investor.flag}"></div>
                        <img src="${investor.photo || 'static/images/profile_pictures/default.png'}" alt="${investor.name}" onerror="this.src='https://ui-avatars.com/api/?name=${encodeURIComponent(investor.name)}&background=random&color=fff&size=512'">
                    </div>
                    <div class="card-overlay-info">
                        <h3 class="card-name">${investor.name}</h3>
                        <div class="card-tenure">${investor.level}</div>
                    </div>
                    <div class="card-body">
                        <span class="list-metric-label">DIAS SEM CHURN</span>
                        <div class="card-price-container">
                            ${investor.daysWithoutChurn} DIAS
                        </div>
                    </div>
                </div>
            `).join('')}
        </div>
    `;

    grid.innerHTML = html;
}

function openInvestorDetails(id) {
    const investor = ALL_RANKING_DATA.find(i => i.id == id);
    if (!investor) return;

    const modal = document.getElementById('rankingModal');
    if (!modal) return;

    // Fill Modal Data
    modal.querySelector('.modal-profile-img').src = investor.photo || 'static/images/profile_pictures/default.png';
    modal.querySelector('.modal-profile-img').onerror = function () {
        this.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(investor.name)}&background=random&color=fff&size=512`;
    };

    const flagTag = modal.querySelector('.modal-tag');
    flagTag.className = `modal-tag flag-${investor.flag}`;
    flagTag.innerText = investor.flag.toUpperCase();

    modal.querySelector('.modal-tenure-tag').innerText = investor.level || 'Investidor';
    modal.querySelector('.modal-name-title').innerText = investor.name;
    modal.querySelector('.modal-sub-title').innerText = investor.role;

    // Performance
    const perfValues = modal.querySelectorAll('.perf-box-val');
    perfValues[0].innerText = investor.clientsCount || '-';
    perfValues[1].innerText = investor.daysWithoutChurn;
    perfValues[2].innerText = investor.mrr_formatted;

    // Highlights
    const hList = modal.querySelector('.highlights-list');
    hList.innerHTML = (investor.highlights || []).map(h => `<li>${h}</li>`).join('');

    // Preço final
    modal.querySelector('.final-price').innerText = investor.mrr_formatted;
    modal.querySelector('.hire-btn').style.display = 'none';

    // Show Modal
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    const modal = document.getElementById('rankingModal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}
