/**
 * home.js - Home Page Specific Logic
 * Fills user data, metrics, and shortcuts
 */

const sessionUser = {
    name: "Gabriel Henrique",
    role: "Assistente Tech - Gerência - Admin",
    unit: "Lisboa&CO TechOps"
};

// Fazer com que os dados operacionais reflitam os dados reais do banco de dados (injetado via template)

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
    // document.getElementById('headerUserName').innerText = sessionUser.name;
    // document.getElementById('headerUserRole').innerText = sessionUser.role;
    // document.getElementById('welcomeTitle').innerText = `Olá, ${sessionUser.name.split(' ')[0]}`;

    // Fill Operational Data
    if (typeof operationalData !== 'undefined' && operationalData) {
        document.getElementById('mrrValue').innerText = Utils.formatBRL(operationalData.mrr || 0);
        document.getElementById('clientsValue').innerText = Utils.formatNumber(operationalData.clients || 0);
        document.getElementById('investorsValue').innerText = Utils.formatNumber(operationalData.investors || 0);
        document.getElementById('squadsValue').innerText = Utils.formatNumber(operationalData.squads || 0);
    }

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
