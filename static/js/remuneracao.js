// FILTROS HUB REMUNERAÇÃO
function filterInvestors() {
    const searchTerm = document.getElementById('remuSearchInput').value.toLowerCase();
    const squadFilter = document.getElementById('squadFilter').value.toLowerCase();
    const roleFilter = document.getElementById('roleFilter').value.toLowerCase();
    const cards = document.querySelectorAll('#investorsGrid .project-card');

    cards.forEach(card => {
        const name = card.getAttribute('data-name').toLowerCase();
        const squad = card.getAttribute('data-squad').toLowerCase();
        const role = card.getAttribute('data-role').toLowerCase();

        const matchesSearch = name.includes(searchTerm);
        const matchesSquad = !squadFilter || squad === squadFilter;
        const matchesRole = !roleFilter || role === roleFilter;

        if (matchesSearch && matchesSquad && matchesRole) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
}

/* REMUNERATION MODAL LOGIC */
window.openRemunerationModal = function (card) {
    const id = card.getAttribute('data-id');
    const name = card.getAttribute('data-name');
    const role = card.getAttribute('data-role');
    const squad = card.getAttribute('data-squad');
    const step = card.getAttribute('data-yellow-flag');
    const clients = card.getAttribute('data-clients');
    const projetos_vinculados = card.getAttribute('data-projetos-vinculados').split(',');
    const fixed = parseFloat(card.getAttribute('data-fixed') || 0);
    const remMin = parseFloat(card.getAttribute('data-rem-min') || 0);
    const remMax = parseFloat(card.getAttribute('data-rem-max') || 0);
    const mrr = parseFloat(card.getAttribute('data-mrr') || 0);
    const mrrTotal = parseFloat(card.getAttribute('data-mrr-total') || 0);
    const mrrEsperado = parseFloat(card.getAttribute('data-mrr-esperado') || 0);
    const mrrTeto = parseFloat(card.getAttribute('data-mrr-teto') || 0);
    const roi = card.getAttribute('data-roi');

    // Fill header/Identification
    document.getElementById('modalName').textContent = name;
    document.getElementById('modalRoleSquad').textContent = `${role} | ${squad}`;
    // document.getElementById('modalStep').textContent = `Step: ${step}`;

    // Fill Metrics
    const clientsBadge = document.getElementById('modalClientsBadge');
    if (clientsBadge) clientsBadge.textContent = clients;
    // Preenchimento detalhado de projetos vinculados em tabela
    const projetosContainer = document.getElementById('modalProjetosContainer');
    if (projetosContainer) {
        let projetosList = [];
        try {
            const rawData = card.getAttribute('data-projetos-vinculados') || '[]';
            projetosList = JSON.parse(rawData);
        } catch (e) {
            console.error("Erro ao processar projetos vinculados:", e);
        }

        if (projetosList.length > 0) {
            let tableHtml = `
                <table class="remu-mini-table">
                    <thead>
                        <tr>
                            <th>Projeto</th>
                            <th>Fee</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            projetosList.forEach(p => {
                tableHtml += `
                    <tr>
                        <td>
                            <div class="remu-mini-project-name">${p.nome || 'N/A'}</div>
                            <div class="remu-mini-project-id">${p.id}</div>
                        </td>
                        <td class="remu-mini-project-fee">${Utils.formatBRL(p.fee)}</td>
                    </tr>
                `;
            });
            tableHtml += `</tbody></table>`;
            projetosContainer.innerHTML = tableHtml;
        } else {
            projetosContainer.innerHTML = '<div class="remu-no-data">Nenhum projeto vinculado</div>';
        }
    }
    document.getElementById('modalFixed').textContent = Utils.formatBRL(fixed);
    document.getElementById('modalRemMin').textContent = Utils.formatBRL(remMin);
    document.getElementById('modalRemMax').textContent = Utils.formatBRL(remMax);

    // MRR Comparativo: Trabalhado x Total
    const mrrBox = document.getElementById('modalMRR');
    if (mrrBox) {
        mrrBox.innerHTML = `
            <div class="remu-comparison-item primary">
                <span class="remu-comparison-label">MRR Trabalhado</span>
                <span class="remu-comparison-val">${Utils.formatBRL(mrr)}</span>
            </div>
            <div class="remu-comparison-item" style="border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px;">
                <span class="remu-comparison-label">MRR Total</span>
                <span class="remu-comparison-val" style="font-size: 0.95rem; opacity: 0.8;">${Utils.formatBRL(mrrTotal)}</span>
            </div>
        `;
    }

    // Metas de MRR (Esperado e Teto)
    const targetsBox = document.getElementById('modalTargets');
    if (targetsBox) {
        const deltaEsp = mrrTotal - mrrEsperado;
        const deltaTeto = mrrTotal - mrrTeto;

        targetsBox.innerHTML = `
            <div class="remu-target-item">
                <span class="remu-comparison-label">Esperado</span>
                <span class="remu-target-val">${Utils.formatBRL(mrrEsperado)}</span>
                <span class="remu-target-delta ${deltaEsp >= 0 ? 'pos' : 'neg'}">
                    ${deltaEsp >= 0 ? 'Excedeu em' : 'Faltam'} ${Utils.formatBRL(Math.abs(deltaEsp))}
                </span>
            </div>
            <div class="remu-target-item" style="border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px;">
                <span class="remu-comparison-label">Teto</span>
                <span class="remu-target-val">${Utils.formatBRL(mrrTeto)}</span>
                <span class="remu-target-delta ${deltaTeto >= 0 ? 'pos' : 'neg'}">
                    ${deltaTeto >= 0 ? 'Atingiu/Excedeu' : 'Faltam'} ${Utils.formatBRL(Math.abs(deltaTeto))}
                </span>
            </div>
        `;
    }

    // Não remover bloco de código abaixo pois será implementado futuramente
    // // Formatação ROI: multiplicar por 100 se for float 0-1
    // if (!isNaN(roi)) {
    //     document.getElementById('modalROI').textContent = `${(parseFloat(roi) * 100).toFixed(2)}%`;
    // } else {
    //     document.getElementById('modalROI').textContent = roi;
    // }

    // Inject Table Body from Template
    const template = document.getElementById(`tmpl-${id}`);
    const tbody = document.getElementById('modalTableBody');
    if (template && tbody) {
        tbody.innerHTML = template.innerHTML;
    }

    // Show Modal
    const modal = document.getElementById('remunerationModal');
    if (modal) modal.classList.add('active');
};

window.closeRemunerationModal = function () {
    const modal = document.getElementById('remunerationModal');
    if (modal) modal.classList.remove('active');
};

// Listeners globais para fechar modal (click fora e ESC)
window.addEventListener('click', (e) => {
    const modal = document.getElementById('remunerationModal');
    if (e.target === modal) {
        closeRemunerationModal();
    }
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeRemunerationModal();
    }
});