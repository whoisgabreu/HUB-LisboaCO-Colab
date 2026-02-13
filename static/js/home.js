/**
 * home.js - Home Page Specific Logic
 * Fills user data, metrics, and shortcuts
 */

const sessionUser = {
    name: "Gabriel Henrique",
    role: "Assistente Tech - Gerência - Admin",
    unit: "Lisboa&CO TechOps"
};

const operationalData = {
    mrr: 187500.75,
    clients: 54,
    investors: 11,
    squads: 6
};

const shortcuts = [
    { label: "Hub de Projetos", icon: "fas fa-project-diagram", url: "/hub-projetos" },
    { label: "Vendas", icon: "fas fa-shopping-cart", url: "/vendas" },
    { label: "Cockpit", icon: "fas fa-tachometer-alt", url: "/cockpit" },
    { label: "Painel de Ranking", icon: "fas fa-trophy", url: "/painel-ranking" },
    { label: "Painel de Atribuição", icon: "fas fa-tasks", url: "/painel-atribuicao" },
    { label: "Hub de CS/CX", icon: "fas fa-users", url: "/hub-cs-cx" }
];


document.addEventListener('DOMContentLoaded', () => {
    // Fill User Info
    document.getElementById('headerUserName').innerText = sessionUser.name;
    document.getElementById('headerUserRole').innerText = sessionUser.role;
    document.getElementById('welcomeTitle').innerText = `Olá, ${sessionUser.name.split(' ')[0]}`;

    // Fill Operational Data
    document.getElementById('mrrValue').innerText = Utils.formatBRL(operationalData.mrr);
    document.getElementById('clientsValue').innerText = Utils.formatNumber(operationalData.clients);
    document.getElementById('investorsValue').innerText = Utils.formatNumber(operationalData.investors);
    document.getElementById('squadsValue').innerText = Utils.formatNumber(operationalData.squads);

    // Render Shortcuts
    renderShortcuts();
});

function renderShortcuts() {
    const grid = document.getElementById('shortcutsGrid');
    if (!grid) return;

    grid.innerHTML = shortcuts.map(shortcut => `
        <a href="${shortcut.url}" class="shortcut-card">
            <i class="${shortcut.icon}"></i>
            <span>${shortcut.label}</span>
        </a>
    `).join('');
}
