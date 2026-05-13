/**
 * app.js - Global Logic
 * Handles Sidebar, User Dropdown, and Global Utilities
 */

document.addEventListener('DOMContentLoaded', () => {
    initSidebar();
    initUserDropdown();
    initSidebarGroups();
    highlightActiveLink();
    disableSearchAutofill();
});

// Impede que o navegador preencha campos de busca com e-mail/senha
function disableSearchAutofill() {
    const inputs = document.querySelectorAll('input');
    inputs.forEach(input => {
        const isSearch = (input.id && input.id.toLowerCase().includes('search')) || 
                        (input.name && input.name.toLowerCase().includes('search')) ||
                        (input.placeholder && input.placeholder.toLowerCase().includes('buscar'));
        
        if (isSearch) {
            input.setAttribute('readonly', 'readonly');
            input.setAttribute('autocomplete', 'off'); // Muitos navegadores ainda respeitam se o campo for readonly
            
            const unlock = () => {
                input.removeAttribute('readonly');
                input.focus();
            };

            input.addEventListener('focus', unlock);
            input.addEventListener('mousedown', unlock);

            // Garante que o valor esteja limpo caso o browser tenha preenchido antes do JS rodar
            setTimeout(() => {
                if (input.value.includes('@')) input.value = '';
            }, 100);
            setTimeout(() => {
                if (input.value.includes('@')) input.value = '';
            }, 500);
        }
    });
}

// Sidebar Logic (Floating Burger & Overlay)
function initSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.querySelector('.sidebar-overlay');
    const floatingBurger = document.getElementById('floatingBurgerBtn');
    const closeBtn = document.getElementById('closeSidebarBtn');
    const headerBurger = document.querySelector('.burger-menu');

    if (!sidebar || !overlay) return;

    const openSidebar = () => {
        sidebar.classList.add('open');
        overlay.classList.add('active');
        document.body.classList.add('sidebar-open');
        if (floatingBurger) {
            floatingBurger.style.opacity = '0';
            floatingBurger.style.pointerEvents = 'none';
        }
    };

    const closeSidebar = () => {
        sidebar.classList.remove('open');
        overlay.classList.remove('active');
        document.body.classList.remove('sidebar-open');
        if (floatingBurger) {
            floatingBurger.style.opacity = '1';
            floatingBurger.style.pointerEvents = 'auto';
        }
    };

    if (floatingBurger) floatingBurger.addEventListener('click', openSidebar);
    if (headerBurger) headerBurger.addEventListener('click', openSidebar);
    if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
    if (overlay) overlay.addEventListener('click', closeSidebar);

    // Close on ESC
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && sidebar.classList.contains('open')) {
            closeSidebar();
        }
    });
}

/* initSidebarCollapse removido */

// Sidebar Groups Logic
function initSidebarGroups() {
    const groups = document.querySelectorAll('.nav-group');
    
    groups.forEach(group => {
        const header = group.querySelector('.nav-group-header');
        const items = group.querySelector('.nav-group-items');
        
        if (header) {
            header.addEventListener('click', () => {
                const isOpen = group.classList.toggle('is-open');
                
                // Opcional: fechar outros grupos ao abrir um (acordeão)
                /*
                if (isOpen) {
                    groups.forEach(other => {
                        if (other !== group) other.classList.remove('is-open');
                    });
                }
                */
            });
        }

        // Abrir automaticamente se houver um item ativo dentro
        if (group.querySelector('.nav-item.active')) {
            group.classList.add('is-open');
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

/**
 * Exibe uma notificação Toast premium na tela.
 * Centralizado para evitar conflitos de implementação.
 * @param {string} message - Mensagem a ser exibida
 * @param {string} type - Tipo: 'success'/'sucesso', 'error'/'erro', 'info'
 */
function showToast(message, type = 'success') {
    // Normalização de tipos para compatibilidade (PT/EN)
    const typeMap = {
        'success': 'sucesso',
        'error': 'erro',
        'info': 'info',
        'sucesso': 'sucesso',
        'erro': 'erro'
    };
    const normalizedType = typeMap[type] || 'info';

    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    // Adiciona classes para ambos os padrões encontrados no CSS
    toast.className = `toast ${normalizedType} toast-${normalizedType}`;

    const iconMap = {
        'sucesso': 'fa-check-circle',
        'erro': 'fa-exclamation-circle',
        'info': 'fa-info-circle'
    };
    const icon = iconMap[normalizedType];

    toast.innerHTML = `
        <i class="fas ${icon}"></i>
        <div class="toast-message">${message}</div>
    `;

    container.appendChild(toast);

    // Entrada suave (força reflow para transição CSS)
    setTimeout(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    }, 10);

    // Tempo de exibição: Erros ficam mais tempo (6s), outros (4s)
    const duracao = normalizedType === 'erro' ? 6000 : 4000;

    // Saída robusta: Usa setTimeout em vez de confiar apenas no transitionend
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-20px)';
        
        // Remove do DOM após a animação de saída (300ms definido no CSS)
        setTimeout(() => {
            toast.remove();
            // Limpa o container se estiver vazio
            if (container && container.childNodes.length === 0) {
                container.remove();
            }
        }, 350);
    }, duracao);
}

window.Utils = Utils;
window.showToast = showToast;
