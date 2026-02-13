/**
 * app.js - Global Logic
 * Handles Sidebar, User Dropdown, and Global Utilities
 */

document.addEventListener('DOMContentLoaded', () => {
    initSidebar();
    initUserDropdown();
    initSidebarCollapse();
    highlightActiveLink();
});

// Sidebar Logic (Mobile)
function initSidebar() {
    const burgerBtn = document.querySelector('.burger-menu');
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.querySelector('.sidebar-overlay');

    if (burgerBtn && sidebar && overlay) {
        burgerBtn.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            overlay.classList.toggle('active');
        });

        overlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
        });

        // Close on ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && sidebar.classList.contains('open')) {
                sidebar.classList.remove('open');
                overlay.classList.remove('active');
            }
        });
    }
}

// Sidebar Collapse Logic (Desktop)
function initSidebarCollapse() {
    const sidebar = document.querySelector('.sidebar');
    const collapseBtn = document.getElementById('sidebarCollapseBtn');

    if (!sidebar || !collapseBtn) return;

    const icon = collapseBtn.querySelector('i');

    // Load state
    const isCollapsed = localStorage.getItem('sidebarCollapsed') === '1';
    if (isCollapsed) {
        sidebar.classList.add('is-collapsed');
        if (icon) icon.className = 'fas fa-chevron-right';
    }

    collapseBtn.addEventListener('click', () => {
        const nowCollapsed = sidebar.classList.toggle('is-collapsed');
        localStorage.setItem('sidebarCollapsed', nowCollapsed ? '1' : '0');

        if (icon) {
            icon.className = nowCollapsed ? 'fas fa-chevron-right' : 'fas fa-chevron-left';
        }
    });
}

// User Dropdown Logic
function initUserDropdown() {
    const userMenuBtn = document.querySelector('.user-menu-btn');
    const sidebarFooter = document.querySelector('.sidebar-footer');
    const dropdown = document.querySelector('.user-dropdown');

    const toggleDropdown = (e) => {
        e.stopPropagation();
        dropdown.classList.toggle('active');
    };

    if (userMenuBtn && dropdown) {
        userMenuBtn.addEventListener('click', toggleDropdown);
    }

    if (sidebarFooter && dropdown) {
        sidebarFooter.addEventListener('click', toggleDropdown);
    }

    // Click outside to close
    window.addEventListener('click', () => {
        if (dropdown && dropdown.classList.contains('active')) {
            dropdown.classList.remove('active');
        }
    });

    // Logout handling
    const logoutBtn = document.querySelector('.logout-item');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            alert('Saindo do sistema...');
            window.location.href = '/login';
        });
    }
}

// Highlight Active Sidebar Item
function highlightActiveLink() {
    const path = window.location.pathname;
    const navItems = document.querySelectorAll('.nav-item');

    navItems.forEach(item => {
        const href = item.getAttribute('href');
        if (path === href || (path === '/' && href === '/') || (path.endsWith(href))) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
}

/**
 * Global Utilities
 */
const Utils = {
    formatBRL: (value) => {
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(value);
    },

    formatNumber: (value) => {
        return new Intl.NumberFormat('pt-BR').format(value);
    }
};

window.Utils = Utils;

// FILTROS HUB REMUNERAÇÃO
function filterInvestors() {
    const searchTerm = document.getElementById('remuSearchInput').value.toLowerCase();
    const squadFilter = document.getElementById('squadFilter').value.toLowerCase();
    const roleFilter = document.getElementById('roleFilter').value.toLowerCase();
    const cards = document.querySelectorAll('#investorsGrid .project-card');

    cards.forEach(card => {
        const name = card.getAttribute('data-name');
        const squad = card.getAttribute('data-squad');
        const role = card.getAttribute('data-role');

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
    const step = card.getAttribute('data-step');
    const clients = card.getAttribute('data-clients');
    const fixed = parseFloat(card.getAttribute('data-fixed') || 0);
    const mrr = parseFloat(card.getAttribute('data-mrr') || 0);
    const roi = card.getAttribute('data-roi');

    // Fill header/Identification
    document.getElementById('modalName').textContent = name;
    document.getElementById('modalRoleSquad').textContent = `${role} | ${squad}`;
    document.getElementById('modalStep').textContent = `Step: ${step}`;

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
