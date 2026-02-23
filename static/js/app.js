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
    // const logoutBtn = document.querySelector('.logout-item');
    // if (logoutBtn) {
    //     logoutBtn.addEventListener('click', (e) => {
    //         e.preventDefault();
    //         alert('Saindo do sistema...');
    //         window.location.href = '/login';
    //     });
    // }
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

// Operation Tabs Logic
function switchOperacaoTab(tabId) {
    // Update buttons (Pill Style)
    document.querySelectorAll('.op-pill-btn').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('onclick').includes(tabId));
    });

    // Update content sections
    document.querySelectorAll('.op-content-section').forEach(section => {
        section.classList.toggle('active', section.id === `section-${tabId}`);
    });
}

function openProjectDetails(projectName) {
    const selectionView = document.getElementById('project-selection-view');
    const detailsView = document.getElementById('project-details-view');
    const displayProjectName = document.getElementById('display-project-name');

    if (selectionView && detailsView) {
        if (displayProjectName) displayProjectName.innerText = projectName;
        
        selectionView.classList.add('hidden');
        detailsView.classList.add('active');
        
        // Reset to first tab (Dashboard)
        switchOperacaoTab('dashboard');
    }
}

function backToProjects() {
    const selectionView = document.getElementById('project-selection-view');
    const detailsView = document.getElementById('project-details-view');
    
    if (selectionView && detailsView) {
        selectionView.classList.remove('hidden');
        detailsView.classList.remove('active');
    }
}

window.switchOperacaoTab = switchOperacaoTab;
window.openProjectDetails = openProjectDetails;
window.backToProjects = backToProjects;

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
