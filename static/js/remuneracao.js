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
    const fixed = parseFloat(card.getAttribute('data-fixed') || 0);
    const mrr = parseFloat(card.getAttribute('data-mrr') || 0);
    const roi = card.getAttribute('data-roi');

    // Fill header/Identification
    document.getElementById('modalName').textContent = name;
    document.getElementById('modalRoleSquad').textContent = `${role} | ${squad}`;
    // document.getElementById('modalStep').textContent = `Step: ${step}`;

    // Fill Metrics
    document.getElementById('modalClients').textContent = clients;
    document.getElementById('modalFixed').textContent = Utils.formatBRL(fixed);
    document.getElementById('modalMRR').textContent = Utils.formatBRL(mrr);

    // Formatação ROI: multiplicar por 100 se for float 0-1
    if (!isNaN(roi)) {
        document.getElementById('modalROI').textContent = `${(parseFloat(roi) * 100).toFixed(2)}%`;
    } else {
        document.getElementById('modalROI').textContent = roi;
    }

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