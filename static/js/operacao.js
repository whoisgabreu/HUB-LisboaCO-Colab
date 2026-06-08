/**
 * LÓGICA DE OPERAÇÃO - HUB LISBOA&CO V10.0
 * Entregas 100% automáticas, desacopladas por cargo.
 * Links Úteis, Otimizações e Plano de Mídia com renderização real.
 */

let currentProject = null;
let currentMonth = new Date().getMonth() + 1;
let currentYear = new Date().getFullYear();
let selectedMonth = currentMonth;
let selectedYear = currentYear;

const MESES_PT = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];
let currentFatVariavelRecords = [];

// ─── CONFIGURAÇÃO DE ENTREGAS POR CARGO ──────────────────────────────────────
// Regras pré-definidas: cada cargo tem metas fixas por tipo de entrega.
// O coordenador pode ajustar por cliente via modal.

const DELIVERY_CONFIG = {
    "Account": [
        { tipo: "checkin_csat",     label: "Check-in + CSAT",          icone: "fa-comments",      meta: 4, desc: "Automático ao registrar check-in com CSAT no mês" },
        { tipo: "relatorio_account", label: "Relatório Mensal (Acc)",    icone: "fa-file-alt",       meta: 1, desc: "Automático ao submeter o relatório mensal do cliente" },
        { tipo: "planner_monday",   label: "Planner Monday",            icone: "fa-calendar-check", meta: 4, desc: "Automático ao registrar ≥4 tarefas semanais no Monday" },
        { tipo: "forecasting",      label: "Forecasting",               icone: "fa-chart-line",     meta: 1, desc: "Automático ao registrar meta com projeção financeira" },
    ],
    "Gestor de Tráfego": [
        { tipo: "plano_midia",      label: "Plano de Mídia",            icone: "fa-bullhorn",       meta: 1, desc: "Automático ao salvar o plano de mídia mensal aprovado" },
        { tipo: "kpis",             label: "KPIs do Mês",               icone: "fa-tachometer-alt", meta: 1, desc: "Automático ao registrar KPIs de performance das campanhas" },
        { tipo: "doc_otimizacao",   label: "Documento de Otimização",   icone: "fa-sliders-h",      meta: 4, desc: "Automático ao registrar otimização de campanhas" },
        { tipo: "relatorio_gt",      label: "Relatório Mensal (GT)",     icone: "fa-file-alt",       meta: 1, desc: "Automático ao submeter o relatório mensal de tráfego" },
    ],
    "Cientista": [
        { tipo: "checkin_csat",     label: "Check-in + CSAT",          icone: "fa-comments",      meta: 4, desc: "Automático ao registrar check-in com CSAT no mês" },
        { tipo: "relatorio_mensal", label: "Relatório Mensal",          icone: "fa-file-alt",       meta: 1, desc: "Relatório mensal consolidado (Account + GT)" },
        { tipo: "planner_monday",   label: "Planner Monday",            icone: "fa-calendar-check", meta: 4, desc: "Automático ao registrar ≥4 tarefas semanais no Monday" },
        { tipo: "forecasting",      label: "Forecasting",               icone: "fa-chart-line",     meta: 1, desc: "Automático ao registrar meta com projeção financeira" },
        { tipo: "plano_midia",      label: "Plano de Mídia",            icone: "fa-bullhorn",       meta: 1, desc: "Automático ao salvar o plano de mídia mensal aprovado" },
        { tipo: "kpis",             label: "KPIs do Mês",               icone: "fa-tachometer-alt", meta: 1, desc: "Automático ao registrar KPIs de performance das campanhas" },
        { tipo: "doc_otimizacao",   label: "Documento de Otimização",   icone: "fa-sliders-h",      meta: 4, desc: "Automático ao registrar otimização de campanhas" },
    ]
};

// Metas customizadas por cliente — chave: `${pipefyId}` → { tipo: meta_override }
const CUSTOM_METAS = {};

// Chart.js instance para o doughnut de entregas
let chartEntregas = null;

// Mapeamento de cargos alternativos para o DELIVERY_CONFIG (mesmo mapeamento do backend)
const ROLE_MAP_ENTREGAS = {
    "Desenvolvedor": "Gestor de Tráfego",
};

// Mapeamento delivery_type (backend) → tipo (frontend DELIVERY_CONFIG)
const BACKEND_TO_FRONTEND_TIPO = {
    "checkin":           "checkin_csat",
    "relatorio_account": "relatorio_account",
    "planner_monday":    "planner_monday",
    "forecasting":       "forecasting",
    "plano_midia":       "plano_midia",
    "otimizacao":        "doc_otimizacao",
    "kpis":              "kpis",
    "relatorio_gt":      "relatorio_gt",
    "relatorio_mensal":  "relatorio_mensal",
};

// ─── PERMISSÕES ──────────────────────────────────────────────────────────────

function hasGTAuth() {
    const role = window.__USER_ROLE__ || "";
    const pos = window.__USER_POSICAO__ || "";
    const isScientist = currentProject?.cientista === true;
    const isHighLevel = pos === 'Gerência' || pos === 'Sócio' || role === 'Gerência' || role === 'Sócio' || role === 'Desenvolvedor';
    return isHighLevel || isScientist || role === 'Cientista' || role === 'Gestor de Tráfego' || role === 'Desenvolvedor';
}

function hasAccountAuth() {
    const role = window.__USER_ROLE__ || "";
    const pos = window.__USER_POSICAO__ || "";
    const isScientist = currentProject?.cientista === true;
    const isHighLevel = pos === 'Gerência' || pos === 'Sócio' || role === 'Gerência' || role === 'Sócio' || role === 'Desenvolvedor';
    return isHighLevel || isScientist || role === 'Cientista' || role === 'Account' || role === 'Coordenador de CX';
}

// ─── TOAST ───────────────────────────────────────────────────────────────────

// // Fazer a notificação toast durar mais tempo
// function showToast(message, type = 'success') {
//     const toast = document.createElement('div');
//     toast.className = `gt-toast toast-${type}`;
//     toast.innerHTML = `
//         <div class="toast-content">
//             <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
//             <span>${message}</span>
//         </div>
//     `;
//     document.body.appendChild(toast);
//     setTimeout(() => toast.classList.add('active'), 10);
//     setTimeout(() => {
//         toast.classList.remove('active');
//         setTimeout(() => toast.remove(), 500);
//     }, 7000);
// }

// ─── MODAIS ───────────────────────────────────────────────────────────────────

function openGTModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeGTModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

function showConfirmModal({ title = 'Confirmar', message = 'Tem certeza?', confirmText = 'Sim, excluir', cancelText = 'Cancelar', icon = 'fa-trash-alt', onConfirm } = {}) {
    const modalId = 'modal-confirm-action';
    const elTitle = document.getElementById('confirm-action-title');
    const elMsg   = document.getElementById('confirm-action-message');
    const elIcon  = document.getElementById('confirm-action-icon');
    const btnOk   = document.getElementById('confirm-action-ok');
    const btnCancel = document.getElementById('confirm-action-cancel');
    if (!elTitle || !btnOk) return;

    elTitle.textContent = title;
    elMsg.textContent   = message;
    elIcon.className    = `fas ${icon}`;
    btnOk.textContent     = confirmText;
    btnCancel.textContent = cancelText;

    const newOk = btnOk.cloneNode(true);
    btnOk.parentNode.replaceChild(newOk, btnOk);
    newOk.addEventListener('click', async () => {
        closeGTModal(modalId);
        try { if (typeof onConfirm === 'function') await onConfirm(); }
        catch (e) { console.error('[showConfirmModal] onConfirm:', e); }
    });

    openGTModal(modalId);
}
window.showConfirmModal = showConfirmModal;

// ─── NAVEGAÇÃO ────────────────────────────────────────────────────────────────

function openProjectDetails(data) {
    let project = data;
    try {
        if (data instanceof HTMLElement) {
            project = JSON.parse(data.dataset.project);
        }
        
        currentProject = project;
        document.getElementById('display-project-name').innerText = project.nome;
        document.getElementById('project-selection-view').style.display = 'none';
        document.getElementById('project-details-view').style.display = 'block';

        // Gerenciar visibilidade de botões por papel/cientista/posição
        const isScientist = project.cientista === true;
        const authGT = hasGTAuth();
        const authAcc = hasAccountAuth();

        // 1. Botões de GT
        document.querySelectorAll('.btn-auth-gt').forEach(btn => {
            const text = btn.innerHTML || "";
            const isRelGT = text.includes('relatorio_gt') || text.includes('Relatório GT') || text.includes('Relatório Mensal (GT)');
            const show = authGT && (!isScientist || !isRelGT) && (window.__USER_ROLE__ !== 'Cientista' || !isRelGT);
            const displayType = btn.classList.contains('access-link-card') ? 'flex' : 'inline-flex';
            btn.style.setProperty('display', show ? displayType : 'none', 'important');
        });

        // 2. Botões de Account
        document.querySelectorAll('.btn-auth-account').forEach(btn => {
            const text = btn.innerHTML || "";
            const isRelAcc = text.includes('relatorio_account') || text.includes('Relatório Acc') || text.includes('Relatório Mensal (Acc)');
            const show = authAcc && (!isScientist || !isRelAcc) && (window.__USER_ROLE__ !== 'Cientista' || !isRelAcc);
            const displayType = btn.classList.contains('access-link-card') ? 'flex' : 'inline-flex';
            btn.style.setProperty('display', show ? displayType : 'none', 'important');
        });

        // 3. Botões de Cientista
        document.querySelectorAll('.btn-auth-cientista').forEach(btn => {
            btn.style.setProperty('display', isScientist ? 'flex' : 'none', 'important');
        });

        switchOperacaoTab('midia');
        loadProjectData();

        // Exibe/oculta aba de Faturamento Variável conforme flag do projeto
        const tabFatVariavel = document.getElementById('tab-fat-variavel');
        if (tabFatVariavel) {
            tabFatVariavel.style.display = project.contrato_variavel ? 'flex' : 'none';
        }
    } catch (e) {
        console.error('[operacao] Erro ao abrir detalhes do projeto:', e);
        showToast('Erro ao carregar detalhes do projeto.', 'error');
    }
}

function backToProjects() {
    currentProject = null;
    document.getElementById('project-selection-view').style.display = 'block';
    document.getElementById('project-details-view').style.display = 'none';
}

function switchOperacaoTab(tabId) {
    document.querySelectorAll('.op-content-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.op-pill-btn').forEach(b => b.classList.remove('active'));

    const targetSection = document.getElementById(`section-${tabId}`);
    if (targetSection) targetSection.classList.add('active');

    document.querySelectorAll('.op-pill-btn').forEach(btn => {
        if (btn.getAttribute('onclick') && btn.getAttribute('onclick').includes(`'${tabId}'`)) {
            btn.classList.add('active');
        }
    });

    // Lazy load por aba
    if (currentProject) {
        const pid = currentProject.pipefy_id;
        if (tabId === 'checkin') loadCheckins(pid);
        if (tabId === 'otimizacao') loadOtimizacoes(pid);
        if (tabId === 'links') loadLinks(pid);
        if (tabId === 'midia') {
            loadPlanoMidia(pid, currentMonth, currentYear);
            loadHistoricoPlanos(pid);
        }
        if (tabId === 'entregas') {
            initMonthSelect('entregas-month-select');
            loadEntregas(pid, currentMonth, currentYear);
        }
        if (tabId === 'fat-variavel') {
            loadFaturamentoVariavel();
        }
    }
}

// ─── CARREGAMENTO GERAL ───────────────────────────────────────────────────────

async function loadProjectData() {
    if (!currentProject) return;
    const pipefyId = currentProject.pipefy_id;

    loadPlanoMidia(pipefyId, selectedMonth, selectedYear);
    loadEntregas(pipefyId, selectedMonth, selectedYear);
}

let currentMetaPeriod = null;
let allOtimizacoes = [];
let allCheckins = [];

function initMonthSelect(selectId) {
    const select = document.getElementById(selectId);
    if (!select) return null;
    const now = new Date();
    const m = now.getMonth() + 1;
    const y = now.getFullYear();
    let html = '';
    for (let i = 11; i >= 0; i--) {
        let month = m - i;
        let year = y;
        if (month <= 0) { month += 12; year--; }
        const val = `${year}-${String(month).padStart(2, '0')}`;
        html += `<option value="${val}"${i === 0 ? ' selected' : ''}>${MESES_PT[month - 1]} ${year}</option>`;
    }
    select.innerHTML = html;
    return `${y}-${String(m).padStart(2, '0')}`;
}

function initMetasMonthNav() {
    const select = document.getElementById('metas-month-select');
    if (!select) return;
    const now = new Date();
    const m = now.getMonth() + 1;
    const y = now.getFullYear();
    let html = '';
    for (let i = 11; i >= 0; i--) {
        let month = m - i;
        let year = y;
        if (month <= 0) { month += 12; year--; }
        const ref = `${year}-M${String(month).padStart(2, '0')}`;
        const label = `${MESES_PT[month - 1]} ${year}`;
        const selected = i === 0 ? 'selected' : '';
        html += `<option value="${ref}" ${selected}>${label}</option>`;
    }
    select.innerHTML = html;
}

function switchMetaMonth(ref) {
    currentMetaPeriod = ref;
    if (currentProject) {
        loadTarefas(currentProject.pipefy_id, 'goal_snapshot', 'quarter-task-list', ref);
    }
}

// ─── TAREFAS ─────────────────────────────────────────────────────────────────

async function loadTarefas(pipefyId, tipo, listId, referencia = "") {
    const url = `/api/operacao/tarefas/${pipefyId}?tipo=${tipo}${referencia ? '&referencia=' + referencia : ''}`;
    try {
        const res = await fetch(url);
        const tarefas = await res.json();
        
        if (tipo === 'goal_snapshot') {
            renderMetasDashboard(tarefas, referencia);
            return;
        }

        const list = document.getElementById(listId);
        if (!list) return;
        list.innerHTML = '';
        if (tarefas.length === 0) {
            list.innerHTML = '<p style="color:var(--text-muted);padding:1rem;">Nenhum registro encontrado.</p>';
            return;
        }
        tarefas.forEach(t => {
            const item = document.createElement('div');
            item.className = `task-item ${t.concluida ? 'completed' : ''}`;
            item.innerHTML = `
                <div class="task-checkbox" onclick="toggleTask(${t.id}, this)"><i class="fas fa-check"></i></div>
                <div class="task-text">${t.descricao}</div>
                ${tipo === 'semanal' ? `<button class="btn-delete-task" onclick="window.decrementPlannerMonday(currentProject?.pipefy_id)" style="background:none;border:none;cursor:pointer;color:var(--accent-red);margin-left:auto;"><i class="fas fa-minus-circle"></i></button>` : `<button class="btn-delete-task" style="opacity:0.3;pointer-events:none;"><i class="fas fa-lock"></i></button>`}
            `;
            list.appendChild(item);
        });
    } catch (e) { console.error("Erro ao carregar tasks:", e); }
}



function renderMetasDashboard(metas) {
    const mainGoalContainer = document.getElementById('main-goal-card-container');
    const subGoalsList = document.getElementById('quarter-task-list');
    if (!mainGoalContainer) return;

    if (!metas || metas.length === 0) {
        mainGoalContainer.innerHTML = `
            <div class="metas-empty-placeholder">
                <i class="fas fa-bullseye"></i>
                <p>Nenhuma meta definida para este mês.</p>
                <button class="btn-add-task" style="margin-top: 0.5rem; font-size: 0.78rem;" onclick="openMetaUnificadoModal()">+ Definir Meta</button>
            </div>`;
        if (subGoalsList) subGoalsList.innerHTML = '';
        return;
    }

    const snapshot = metas[0];
    let data = {};
    try { data = JSON.parse(snapshot.descricao); } catch(e) { return; }

    const krs = data.krs || [];
    const completedMain = snapshot.concluida ? 1 : 0;
    const completedKRs = krs.filter(k => k.concluida).length;
    const totalItems = 1 + krs.length;
    const totalPercent = Math.round(((completedMain + completedKRs) / totalItems) * 100);

    const typeMap  = { faturamento: 'Faturamento', leads: 'Leads / MQL', vendas: 'Vendas', engajamento: 'Engajamento', outros: 'Outro' };
    const iconMap  = { faturamento: 'fa-dollar-sign', leads: 'fa-bullseye', vendas: 'fa-shopping-cart', engajamento: 'fa-chart-line', outros: 'fa-rocket' };
    const typeName = typeMap[data.tipo_meta] || 'Meta';
    const typeIcon = iconMap[data.tipo_meta] || 'fa-rocket';
    const targetFmt = data.valor_alvo
        ? (data.tipo_meta === 'faturamento' ? 'R$ ' : '') + parseFloat(data.valor_alvo).toLocaleString('pt-BR')
        : null;

    mainGoalContainer.innerHTML = `
        <div class="metas-goal-card ${snapshot.concluida ? 'done' : ''}">
            <i class="fas ${typeIcon} metas-goal-bg-icon"></i>
            <div class="metas-goal-actions">
                <button class="btn-icon-subtle" onclick="openMetaUnificadoModal(${snapshot.id})" title="Editar"><i class="fas fa-edit"></i></button>
                <button class="btn-icon-subtle" onclick="toggleUnifiedMainGoal(${snapshot.id}, ${snapshot.concluida})" title="Marcar como concluída" style="${snapshot.concluida ? 'background:rgba(16,185,129,0.15);color:#10b981;' : ''}">
                    <i class="fas fa-check"></i>
                </button>
            </div>
            <span class="metas-goal-type-badge"><i class="fas ${typeIcon}"></i> ${typeName}</span>
            <h3 class="metas-goal-name">${data.nome}</h3>
            ${targetFmt ? `<div class="metas-goal-target">Alvo: <strong>${targetFmt}</strong></div>` : '<div style="margin-bottom:1.25rem;"></div>'}
            <div class="metas-progress-bar">
                <div class="metas-progress-fill ${snapshot.concluida ? 'done' : ''}" style="width:${totalPercent}%;"></div>
            </div>
            <div class="metas-progress-stats">
                <span>${totalPercent}% concluído</span>
                <span>${completedMain + completedKRs} / ${totalItems} itens</span>
            </div>
        </div>`;

    if (!subGoalsList) return;
    subGoalsList.innerHTML = '';

    if (krs.length > 0) {
        const header = document.createElement('div');
        header.className = 'metas-section-label';
        header.innerHTML = `<i class="fas fa-list-check" style="color:var(--accent-red);"></i> Resultados Chave &nbsp;<span style="color:var(--text-main);font-weight:700;">${completedKRs}/${krs.length}</span>`;
        subGoalsList.appendChild(header);

        krs.forEach((kr, idx) => {
            const item = document.createElement('div');
            item.className = `metas-kr-item ${kr.concluida ? 'done' : ''}`;
            item.innerHTML = `
                <div class="task-checkbox" onclick="toggleUnifiedKR(${snapshot.id}, ${idx})" style="width:26px;height:26px;min-width:26px;font-size:0.75rem;"><i class="fas fa-check"></i></div>
                <span class="metas-kr-num">KR${String(idx + 1).padStart(2, '0')}</span>
                <span class="metas-kr-text">${kr.titulo}</span>
                ${kr.alvo ? `<span class="metas-kr-target">${parseFloat(kr.alvo).toLocaleString('pt-BR')}</span>` : ''}
            `;
            subGoalsList.appendChild(item);
        });
    }
}

let activeSnapshotId = null;

function openMetaUnificadoModal(id = null) {
    activeSnapshotId = id;
    const container = document.getElementById('unified-krs-container');
    container.innerHTML = '';
    
    // Clear form
    document.getElementById('unified-goal-name').value = '';
    document.getElementById('unified-goal-target').value = '';
    document.getElementById('unified-goal-type').value = 'faturamento';
    
    if (id) {
        // Modo Edição: Carregar dados existentes
        fetch(`/api/operacao/tarefas/${currentProject.pipefy_id}?tipo=goal_snapshot`)
            .then(res => res.json())
            .then(metas => {
                const s = metas.find(m => m.id === id);
                if (s) {
                    const data = JSON.parse(s.descricao);
                    document.getElementById('unified-goal-name').value = data.nome;
                    document.getElementById('unified-goal-target').value = data.valor_alvo || '';
                    document.getElementById('unified-goal-type').value = data.tipo_meta || 'faturamento';
                    if (data.krs) {
                        data.krs.forEach(k => addKRRowModal(k.titulo, k.alvo, k.concluida));
                    }
                }
            });
    } else {
        // Adiciona um KR vazio por padrão
        addKRRowModal();
    }
    
    openGTModal('modal-metas-unificado');
}

function addKRRowModal(titulo = "", alvo = "", concluida = false) {
    const container = document.getElementById('unified-krs-container');
    const row = document.createElement('div');
    row.className = 'kr-input-row';
    row.style.display = 'grid';
    row.style.gridTemplateColumns = '1fr 120px 40px';
    row.style.gap = '10px';
    row.style.alignItems = 'center';
    row.dataset.concluida = concluida;
    
    row.innerHTML = `
        <input type="text" class="gt-form-input kr-title" placeholder="Descreva o Resultado Chave" value="${titulo}" style="padding: 8px 12px; font-size: 0.85rem;">
        <input type="number" class="gt-form-input kr-target" placeholder="Alvo" value="${alvo}" style="padding: 8px 12px; font-size: 0.85rem;">
        <button onclick="this.parentElement.remove()" style="background: none; border: none; color: #888; cursor: pointer;" title="Remover KR"><i class="fas fa-times"></i></button>
    `;
    container.appendChild(row);
}

async function saveUnifiedGoalsSnapshot() {
    const nome = document.getElementById('unified-goal-name').value;
    const target = document.getElementById('unified-goal-target').value;
    const type = document.getElementById('unified-goal-type').value;

    if (!nome) { showToast('Nome do objetivo é obrigatório', 'error'); return; }

    const krs = [];
    document.querySelectorAll('.kr-input-row').forEach(row => {
        const title = row.querySelector('.kr-title').value;
        const krTarget = row.querySelector('.kr-target').value;
        if (title) {
            krs.push({ titulo: title, alvo: krTarget, concluida: row.dataset.concluida === 'true' });
        }
    });

    const referencia = currentMetaPeriod || `${currentYear}-M${String(currentMonth).padStart(2, '0')}`;
    const snapshotData = {
        nome,
        valor_alvo: target,
        tipo_meta: type,
        periodo: 'mensal',
        krs,
        versao: '3.0'
    };

    const payload = {
        id: activeSnapshotId,
        pipefy_id: currentProject.pipefy_id,
        tipo: 'goal_snapshot',
        descricao: JSON.stringify(snapshotData),
        referencia: referencia,
        ano: currentYear
    };

    try {
        const res = await fetch('/api/operacao/tarefas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            showToast('Planejamento salvo com sucesso!');
            closeGTModal('modal-metas-unificado');
            handlePeriodFilterChange();
        }
    } catch (e) { console.error(e); }
}

function handlePeriodFilterChange() {
    if (currentProject && currentMetaPeriod) {
        loadTarefas(currentProject.pipefy_id, 'goal_snapshot', 'quarter-task-list', currentMetaPeriod);
    }
}

async function toggleUnifiedMainGoal(id, currentStatus) {
    try {
        await fetch('/api/operacao/tarefas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: id, concluida: !currentStatus })
        });
        handlePeriodFilterChange();
    } catch (e) { console.error(e); }
}

async function toggleUnifiedKR(id, krIndex) {
    // 1. Get current data
    const res = await fetch(`/api/operacao/tarefas/${currentProject.pipefy_id}?tipo=goal_snapshot`);
    const metas = await res.json();
    const snapshot = metas.find(m => m.id === id);
    if (!snapshot) return;

    const data = JSON.parse(snapshot.descricao);
    if (data.krs && data.krs[krIndex]) {
        data.krs[krIndex].concluida = !data.krs[krIndex].concluida;
    }

    // 2. Save back
    try {
        await fetch('/api/operacao/tarefas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: id, descricao: JSON.stringify(data) })
        });
        handlePeriodFilterChange();
    } catch (e) { console.error(e); }
}


async function addNewTask(tipo = 'semanal') {
    const inputId = tipo === 'semanal' ? 'task-desc-input' : 'task-quarter-input';
    const modalId = tipo === 'semanal' ? 'modal-nova-tarefa' : 'modal-nova-tarefa-quarter';
    const descInput = document.getElementById(inputId);
    if (!descInput || !descInput.value.trim()) return;

    let referencia = "";
    if (tipo === 'semanal') {
        const now = new Date();
        const start = new Date(now.getFullYear(), 0, 1);
        const week = Math.ceil(((now - start) / 86400000 + 1) / 7);
        referencia = `${currentYear}-W${String(week).padStart(2, '0')}`;
    } else {
        referencia = `${currentYear}-Q${Math.floor((currentMonth - 1) / 3) + 1}`;
    }

    let payload = {
        pipefy_id: currentProject.pipefy_id,
        tipo, descricao: descInput.value, referencia,
        mes: selectedMonth,
        ano: selectedYear,
    };

    // Para metas (quarter), incluímos os campos estruturados no campo descricao como JSON
    if (tipo === 'quarter') {
        const goalType = document.getElementById('goal-type-select').value;
        const goalTarget = document.getElementById('goal-target-value').value || 0;
        const goalPeriod = document.getElementById('goal-period-select').value;
        
        const structuredData = {
            nome: descInput.value,
            tipo_meta: goalType,
            valor_alvo: goalTarget,
            periodo: goalPeriod,
            versao: '2.0' // Para identificar JSON futuramente
        };
        payload.descricao = JSON.stringify(structuredData);
    }

    try {
        const res = await fetch('/api/operacao/tarefas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            showToast('Meta salva!');
            descInput.value = '';
            if (tipo === 'quarter') {
                const targetInput = document.getElementById('goal-target-value');
                if (targetInput) targetInput.value = '';
            }
            closeGTModal(modalId);
            // Após salvar tarefa, reprocessar entregas (afeta planner_monday, forecasting, relatorio)
            await fetch(`/api/operacao/monthly-deliveries/${currentProject.pipefy_id}/${selectedMonth}/${selectedYear}`);
            loadProjectData();
        }
    } catch (e) { console.error(e); }
}

async function toggleTask(id, element) {
    const isCompleted = !element.closest('.task-item').classList.contains('completed');
    try {
        await fetch('/api/operacao/tarefas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: id, concluida: isCompleted })
        });
        element.closest('.task-item').classList.toggle('completed');
        // Recalcula entregas pois pode ter impactado relatorio/forecasting
        loadEntregas(currentProject.pipefy_id, selectedMonth, selectedYear);
    } catch (e) { console.error(e); }
}

// ─── ENTREGAS DO MÊS — BARRAS DE PROGRESSO ───────────────────────────────────

// Navega o histórico de entregas por mês (formato "YYYY-MM" vindo do seletor).
function filterEntregasByMonth(val) {
    if (!currentProject) return;
    const parts = (val || '').split('-');
    if (parts.length !== 2) return;
    selectedYear = parseInt(parts[0], 10);
    selectedMonth = parseInt(parts[1], 10);
    loadEntregas(currentProject.pipefy_id, selectedMonth, selectedYear);
}

async function loadEntregas(pipefyId, mes, ano) {
    const meses = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];
    const dateEl = document.getElementById('display-entregas-date');
    if (dateEl) dateEl.innerText = `[${meses[mes - 1]} ${ano}]`;

    const container = document.getElementById('entregas-grid');
    if (!container) return;

    const rawRole = (currentProject && currentProject.cientista) ? "Cientista" : (window.__USER_ROLE__ || "");
    const userRole = ROLE_MAP_ENTREGAS[rawRole] || rawRole;
    const config = DELIVERY_CONFIG[userRole];
    if (!config) {
        container.innerHTML = '<p style="color:var(--text-muted);padding:2rem;text-align:center;">Cargo sem entregas configuradas.</p>';
        return;
    }

    // Obter metas do cliente (padrão + override do coordenador)
    const customKey = String(pipefyId);
    const customOverride = CUSTOM_METAS[customKey] || {};

    const configComMeta = config.map(c => ({
        ...c,
        meta: customOverride[c.tipo] !== undefined ? customOverride[c.tipo] : c.meta,
    }));

    // Buscar realizados reais do backend (MonthlyDelivery por projeto/mês/ano)
    const realizadosRaw = {};
    try {
        const resp = await fetch(`/api/operacao/monthly-deliveries/${pipefyId}/${mes}/${ano}`);
        if (resp.ok) {
            const entregas = await resp.json();
            for (const e of entregas) {
                const frontendTipo = BACKEND_TO_FRONTEND_TIPO[e.delivery_type];
                if (!frontendTipo) continue;
                const cfgItem = configComMeta.find(c => c.tipo === frontendTipo);
                if (!cfgItem) continue;
                // Usar contagem real do backend quando disponível
                if (e.count !== undefined) {
                    realizadosRaw[frontendTipo] = Math.min(e.count, cfgItem.meta);
                } else if (e.status === 'completed') {
                    realizadosRaw[frontendTipo] = cfgItem.meta;
                }
            }
        }
    } catch (err) {
        console.warn('Erro ao buscar entregas do mês:', err);
    }

    renderEntregasSummary(configComMeta, realizadosRaw);
    renderEntregasCards(configComMeta, realizadosRaw);
}

function _corProgresso(pct) {
    if (pct >= 100) return '#22c55e';
    if (pct >= 75)  return '#22c55e';
    if (pct >= 40)  return '#f59e0b';
    return '#ef4444';
}

function renderEntregasSummary(config, realizados) {
    const panel = document.getElementById('entregas-summary-panel');
    const kpisEl = document.getElementById('entregas-kpis-grid');
    if (!panel || !kpisEl) return;

    const PESO_POR_TIPO  = 100 / config.length; 
    const totalMeta      = config.reduce((s, c) => s + c.meta, 0);
    const totalRealizado = config.reduce((s, c) => s + Math.min(realizados[c.tipo] || 0, c.meta), 0);
    const concluidas     = config.filter(c => (realizados[c.tipo] || 0) >= c.meta).length;
    // Percentual total: soma de (realizado/meta)*PESO para cada tipo
    const pct            = Math.round(config.reduce((s, c) => {
        const r = Math.min(realizados[c.tipo] || 0, c.meta);
        return s + (c.meta > 0 ? (r / c.meta) * PESO_POR_TIPO : 0);
    }, 0));
    const cor            = _corProgresso(pct);

    // KPI cards
    kpisEl.innerHTML = `
        <div class="entrega-kpi-card">
            <div class="entrega-kpi-icon" style="background:linear-gradient(135deg,#D61616,#a01010);">
                <i class="fas fa-list-check"></i>
            </div>
            <div class="entrega-kpi-data">
                <span class="entrega-kpi-label">Tipos de Entrega</span>
                <span class="entrega-kpi-value">${config.length}</span>
            </div>
        </div>
        <div class="entrega-kpi-card">
            <div class="entrega-kpi-icon" style="background:linear-gradient(135deg,${cor},${cor}cc);">
                <i class="fas fa-circle-check"></i>
            </div>
            <div class="entrega-kpi-data">
                <span class="entrega-kpi-label">Tipos Concluídos</span>
                <span class="entrega-kpi-value" style="color:${cor};">${concluidas} / ${config.length}</span>
            </div>
        </div>
        <div class="entrega-kpi-card">
            <div class="entrega-kpi-icon" style="background:linear-gradient(135deg,#22c55e,#16a34a);">
                <i class="fas fa-check-double"></i>
            </div>
            <div class="entrega-kpi-data">
                <span class="entrega-kpi-label">Entregas Realizadas</span>
                <span class="entrega-kpi-value" style="color:#22c55e;">${totalRealizado} / ${totalMeta}</span>
            </div>
        </div>
        <div class="entrega-kpi-card">
            <div class="entrega-kpi-icon" style="background:linear-gradient(135deg,#6366f1,#4338ca);">
                <i class="fas fa-bullseye"></i>
            </div>
            <div class="entrega-kpi-data">
                <span class="entrega-kpi-label">Meta Geral</span>
                <span class="entrega-kpi-value" style="color:${cor};">${pct}%</span>
            </div>
        </div>
    `;

    // Doughnut chart
    _renderDoughnutEntregas(pct, cor);

    panel.style.display = 'grid';
}

function _renderDoughnutEntregas(pct, cor) {
    if (chartEntregas) chartEntregas.destroy();
    const canvas = document.getElementById('chart-entregas-op');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const isTemaClaro = document.body.classList.contains('tema-claro');
    const trackColor = isTemaClaro ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.06)';
    const textColor  = isTemaClaro ? '#374151' : '#e5e7eb';

    chartEntregas = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Realizado', 'Pendente'],
            datasets: [{
                data: [pct, 100 - pct],
                backgroundColor: [cor, trackColor],
                borderColor:     ['transparent','transparent'],
                borderWidth: 0,
                cutout: '78%',
                borderRadius: 6,
            }]
        },
        options: {
            responsive: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    enabled: false,
                    backgroundColor: isTemaClaro ? '#1f2937' : '#1a1a2e',
                    titleFont: { family: 'Poppins', size: 12 },
                    bodyFont:  { family: 'Poppins', size: 11 },
                    padding: 10,
                    cornerRadius: 8,
                    callbacks: { label: c => c.label + ': ' + c.raw + '%' },
                }
            }
        },
        plugins: [{
            id: 'textoCentral',
            afterDraw(chart) {
                const { ctx: c, chartArea } = chart;
                const cx = (chartArea.left + chartArea.right)  / 2;
                const cy = (chartArea.top  + chartArea.bottom) / 2;
                c.save();
                c.textAlign = 'center'; c.textBaseline = 'middle';
                c.font = 'bold 1.7rem Poppins'; c.fillStyle = cor;
                c.fillText(pct + '%', cx, cy - 10);
                c.font = '500 0.68rem Poppins'; c.fillStyle = textColor;
                c.fillText('Concluído', cx, cy + 17);
                c.restore();
            }
        }]
    });
}

function renderEntregasCards(config, realizados) {
    const container = document.getElementById('entregas-grid');
    if (!container) return;

    const listHtml = config.map((c) => {
        const realizado       = realizados[c.tipo] || 0;
        const meta            = c.meta;
        const pct             = meta > 0 ? Math.min(Math.round((realizado / meta) * 100), 100) : 0;
        const cor             = _corProgresso(pct);
        const pesoPorTipo     = 100 / config.length;
        const pesoPorEntrega  = meta > 0 ? (pesoPorTipo / meta) : pesoPorTipo;
        const contribuicao    = Math.min(realizado, meta) * pesoPorEntrega;
        const contribuicaoFmt = Number.isInteger(contribuicao) ? contribuicao : contribuicao.toFixed(2);
        
        const isCoordenador = (currentProject && currentProject.cientista) || window.__USER_ROLE__ === 'Account' || window.__USER_ROLE__ === 'Gerência' || window.__USER_POSICAO__ === 'Gerência' || window.__USER_ROLE__ === 'Coordenador de CX' || window.__USER_POSICAO__ === 'Sócio';

        return `
            <div class="op-entrega-row">
                <div class="op-entrega-info">
                    <i class="fas ${c.icone}" style="color:#D61616;width:16px;text-align:center;flex-shrink:0;margin-top:2px;"></i>
                    <div class="op-entrega-texts">
                        <span class="op-entrega-label">${c.label}</span>
                        <span class="op-entrega-peso">Peso: <strong style="color:var(--text-main)">${pesoPorTipo % 1 === 0 ? pesoPorTipo : pesoPorTipo.toFixed(2)}%</strong>${meta > 1 ? ` <span style="opacity:0.6;">(${pesoPorEntrega % 1 === 0 ? pesoPorEntrega : pesoPorEntrega.toFixed(2)}% × ${meta})</span>` : ''} &nbsp;·&nbsp; <strong style="color:${cor}">${contribuicaoFmt}%</strong> conquistado</span>
                    </div>
                </div>
                <div class="op-entrega-controls">
                    ${c.tipo === 'planner_monday' && isCoordenador ? `
                        <button class="btn-delta btn-minus" onclick="window.decrementPlannerMonday(${currentProject.pipefy_id})" title="Remover último registro manual">−</button>
                    ` : ''}
                    <span style="min-width:48px;text-align:center;font-weight:600;color:${cor};">${realizado}<span style="color:var(--text-muted);font-weight:400"> / ${meta}</span></span>
                    ${c.tipo === 'planner_monday' && isCoordenador ? `
                        <button class="btn-delta btn-plus" onclick="window.incrementPlannerMonday(${currentProject.pipefy_id})" title="Adicionar registro manual">+</button>
                    ` : ''}
                </div>
                <div class="op-entrega-bar-wrap">
                    <div class="op-entrega-bar" style="width:${pct}%;background:${cor};box-shadow:0 0 6px ${cor}44;"></div>
                </div>
            </div>`;
    }).join('');

    container.innerHTML = `
        <div class="criativa-table-card" style="padding:1.5rem; margin-top: 1rem;">
            <div class="op-entregas-lista">${listHtml}</div>
        </div>
    `;
}

function updateMRRDisplay(totalMrr) {
    const display = document.getElementById('mrr-impact-display');
    if (display) display.innerText = `R$ ${totalMrr.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
}

// ─── MODAL EDITAR METAS (COORDENADOR) ────────────────────────────────────────

function openMetasModal() {
    const rawRole = window.__USER_ROLE__ || "";
    const userRole = ROLE_MAP_ENTREGAS[rawRole] || rawRole;
    const config = DELIVERY_CONFIG[userRole];
    if (!config || !currentProject) return;

    const customKey = String(currentProject.pipefy_id);
    const customOverride = CUSTOM_METAS[customKey] || {};

    const clienteNome = currentProject.name || currentProject.pipefy_id;
    document.querySelector('#modal-editar-metas .gt-modal-header h3').innerHTML =
        `<i class="fas fa-sliders-h" style="margin-right:8px;color:#D61616;"></i>Editar Metas — <span style="color:#D61616;">${clienteNome}</span>`;

    const fieldsEl = document.getElementById('metas-form-fields');
    fieldsEl.innerHTML = config.map(c => {
        const metaAtual  = customOverride[c.tipo] !== undefined ? customOverride[c.tipo] : c.meta;
        const isPadrao   = customOverride[c.tipo] === undefined;
        return `
        <div style="display:grid;grid-template-columns:1fr auto;align-items:center;gap:1rem;padding:0.9rem 1rem;background:rgba(255,255,255,0.02);border:1px solid var(--border-color);border-radius:10px;">
            <div>
                <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:3px;">
                    <i class="fas ${c.icone}" style="color:#D61616;font-size:0.85rem;width:16px;text-align:center;"></i>
                    <span style="font-size:0.88rem;font-weight:600;color:var(--text-main);">${c.label}</span>
                    ${isPadrao ? '<span style="font-size:0.65rem;color:var(--text-muted);background:rgba(255,255,255,0.05);border:1px solid var(--border-color);padding:1px 6px;border-radius:10px;">padrão</span>' : '<span style="font-size:0.65rem;color:#f59e0b;background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.25);padding:1px 6px;border-radius:10px;">personalizado</span>'}
                </div>
                <p style="font-size:0.72rem;color:var(--text-muted);margin:0;">Meta padrão do cargo: <strong style="color:var(--text-sub);">${c.meta}</strong></p>
            </div>
            <input type="number" class="metas-input" data-tipo="${c.tipo}" data-padrao="${c.meta}"
                   min="0" max="20" value="${metaAtual}"
                   style="width:72px;text-align:center;background:var(--card-bg);border:1px solid var(--border-color);border-radius:8px;color:var(--text-main);font-family:Poppins,sans-serif;font-size:1rem;font-weight:600;padding:0.4rem 0.5rem;outline:none;transition:border-color 0.2s;"
                   onfocus="this.style.borderColor='#D61616'" onblur="this.style.borderColor='var(--border-color)'"
            />
        </div>`;
    }).join('');

    openGTModal('modal-editar-metas');
}

function closeMetasModal() {
    const modal = document.getElementById('modal-editar-metas');
    if (modal) { modal.classList.remove('active'); document.body.style.overflow = ''; }
}

function saveMetasModal() {
    if (!currentProject) return;
    const customKey = String(currentProject.pipefy_id);
    const inputs = document.querySelectorAll('#metas-form-fields .metas-input');

    const override = {};
    inputs.forEach(input => {
        const val = parseInt(input.value, 10);
        const padrao = parseInt(input.dataset.padrao, 10);
        if (!isNaN(val) && val !== padrao) override[input.dataset.tipo] = val;
    });

    if (Object.keys(override).length > 0) {
        CUSTOM_METAS[customKey] = override;
    } else {
        delete CUSTOM_METAS[customKey];
    }

    closeMetasModal();
    loadEntregas(currentProject.pipefy_id, selectedMonth, selectedYear);
    if (typeof showToast === 'function') showToast('Metas atualizadas com sucesso!', 'success');
}

// ─── PLANO DE MÍDIA ───────────────────────────────────────────────────────────

async function loadPlanoMidia(pipefyId, mes, ano) {
    const meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
    const displayDate = document.getElementById('display-main-plan-date');
    if (displayDate) displayDate.innerText = `[${meses[mes - 1]} ${ano}]`;

    const body = document.getElementById('plano-midia-body');
    if (!body) return;

    try {
        const res = await fetch(`/api/operacao/plano-midia/${pipefyId}/${mes}/${ano}`);
        const data = await res.json();

        const canais = data && data.dados_plano && data.dados_plano.canais;
        if (!canais || canais.length === 0) {
            body.innerHTML = `
                <tr>
                    <td colspan="5" style="padding:3rem;color:var(--text-muted);text-align:center;">
                        <i class="fas fa-file-invoice-dollar" style="font-size:2rem;margin-bottom:1rem;display:block;opacity:0.3;"></i>
                        Nenhum plano de mídia lançado para este mês.<br>
                        <button class="btn-add-task btn-auth-gt" style="margin-top:1rem;background:var(--accent-red);" onclick="openNovoPlanModal()">
                            <i class="fas fa-plus"></i> Lançar Plano de Mídia
                        </button>
                    </td>
                </tr>`;
            
            // Aplicar visibilidade antes do return
            const authGT = hasGTAuth();
            body.querySelectorAll('.btn-auth-gt').forEach(btn => {
                btn.style.setProperty('display', authGT ? 'inline-flex' : 'none', 'important');
            });
            return;
        }

        body.innerHTML = '';
        let totalBudget = 0, totalDaily = 0;
        canais.forEach(c => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${c.canal}</strong></td>
                <td>${c.campanhas || ''}</td>
                <td>${c.percent_budget || '0'}%</td>
                <td>R$ ${parseFloat(c.budget || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</td>
                <td>R$ ${parseFloat(c.budget_dia || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</td>
            `;
            body.appendChild(row);
            totalBudget += parseFloat(c.budget || 0);
            totalDaily += parseFloat(c.budget_dia || 0);
        });
        const footer = document.createElement('tr');
        footer.className = 'total-row';
        footer.innerHTML = `
            <td>TOTAL</td><td></td><td>100%</td>
            <td>R$ ${totalBudget.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</td>
            <td>R$ ${totalDaily.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</td>`;
        body.appendChild(footer);

        // Adicionar botão de deletar no cabeçalho de ações da seção (se ainda não existir)
        const actionsHeader = document.querySelector('#section-midia header div[style*="display: flex; gap: 12px"]');
        if (actionsHeader && !document.getElementById('btn-clear-plano')) {
            const btn = document.createElement('button');
            btn.id = 'btn-clear-plano';
            btn.className = 'btn-add-task btn-auth-gt';
            btn.style.cssText = 'background: transparent; color: #D61616; border: 1px solid rgba(214, 22, 22, 0.3); font-size: 0.75rem;';
            btn.innerHTML = '<i class="fas fa-trash-alt"></i> Limpar';
            btn.onclick = () => window.deletePlanoMidia();
            actionsHeader.prepend(btn);
        }

        // Atualizar visibilidade dos botões de GT recém-criados
        const authGT = hasGTAuth();
        document.querySelectorAll('.btn-auth-gt').forEach(btn => {
            btn.style.setProperty('display', authGT ? 'inline-flex' : 'none', 'important');
        });

    } catch (e) { console.error("Erro ao carregar plano de mídia:", e); }
}

// ─── OTIMIZAÇÕES ─────────────────────────────────────────────────────────────

async function loadOtimizacoes(pipefyId) {
    const listEl = document.getElementById('otimizacao-list');
    if (!listEl) return;
    const defaultMonth = initMonthSelect('otimizacao-month-select');
    try {
        const res = await fetch(`/api/operacao/otimizacoes/${pipefyId}`);
        const raw = await res.json();
        allOtimizacoes = Array.isArray(raw) ? raw : [];
        const sel = document.getElementById('otimizacao-month-select');
        renderOtimizacoesByMonth(sel ? sel.value : defaultMonth);
    } catch (e) { console.error("Erro ao carregar otimizações:", e); }
}

function renderOtimizacoesByMonth(monthVal) {
    const listEl = document.getElementById('otimizacao-list');
    const emptyEl = document.getElementById('otimizacao-empty-state');
    if (!listEl) return;
    const filtered = monthVal
        ? allOtimizacoes.filter(o => o.data && o.data.substring(0, 7) === monthVal)
        : allOtimizacoes;
    if (!filtered.length) {
        listEl.innerHTML = '';
        if (emptyEl) emptyEl.style.display = 'block';
        return;
    }
    if (emptyEl) emptyEl.style.display = 'none';
    listEl.innerHTML = '';
    filtered.forEach(o => {
        const card = document.createElement('div');
        card.className = 'op-card-premium';
        card.style.cssText = 'padding:1.2rem;border-left:4px solid var(--accent-red);';
        card.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div style="flex:1;">
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
                        <span class="badge-gt badge-estavel" style="font-size:0.75rem;">${o.tipo || ''}</span>
                        <span style="font-size:0.75rem;color:#888;">${o.canal || ''}</span>
                        <span style="font-size:0.75rem;color:#888;">${o.data || ''}</span>
                    </div>
                    <p style="font-size:0.85rem;color:var(--text-muted);margin:0;line-height:1.5;">
                        ${o.detalhes || '<em>Sem detalhes.</em>'}
                    </p>
                </div>
                <button onclick="window.deleteOtimizacao(${o.mes}, ${o.ano}, ${o.original_index})" 
                    class="btn-add-task btn-auth-gt btn-auth-account"
                    style="background: transparent; color: #888; border: 1px solid var(--border-color); padding: 6px 10px; width: auto; height: auto;"
                    onmouseover="this.style.color='#D61616'; this.style.borderColor='#D61616';"
                    onmouseout="this.style.color='#888'; this.style.borderColor='var(--border-color)';"
                    title="Excluir otimização">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </div>`;
        listEl.appendChild(card);
    });

    // Atualizar visibilidade dos botões de GT recém-criados
    const authGT = hasGTAuth();
    document.querySelectorAll('.btn-auth-gt').forEach(btn => {
        btn.style.setProperty('display', authGT ? 'inline-flex' : 'none', 'important');
    });
}

function filterOtimizacoesByMonth(val) { renderOtimizacoesByMonth(val); }

async function saveOtimizacao() {
    const type = document.getElementById('opt-type').value;
    const channel = document.getElementById('opt-channel').value;
    const date = document.getElementById('opt-date').value;
    const details = document.getElementById('opt-details').value;

    if (!date) { showToast('Por favor, selecione a data.', 'error'); return; }

    const payload = {
        pipefy_id: currentProject.pipefy_id,
        tipo: type, canal: channel, data: date, detalhes: details
    };

    try {
        const res = await fetch('/api/operacao/otimizacao', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            showToast('Otimização registrada! Verificando entregas...');
            closeGTModal('modal-nova-otimizacao');
            document.getElementById('opt-date').value = '';
            document.getElementById('opt-details').value = '';
            loadOtimizacoes(currentProject.pipefy_id);
            await fetch(`/api/operacao/monthly-deliveries/${currentProject.pipefy_id}/${selectedMonth}/${selectedYear}`);
            loadEntregas(currentProject.pipefy_id, selectedMonth, selectedYear);
        } else {
            const errorData = await res.json();
            showToast(errorData.error || 'Erro ao salvar otimização.', 'error');
        }
    } catch (e) { 
        console.error(e);
        showToast('Erro de conexão com o servidor.', 'error');
    }
}

// ─── LINKS ÚTEIS ─────────────────────────────────────────────────────────────

// Lê o mês/ano selecionado no seletor da aba de Links (formato "YYYY-MM").
// Garante que salvar/limpar link retroativo grave no mês correto, e não no mês atual.
function getLinksSelectedPeriod() {
    const sel = document.getElementById('links-month-select');
    if (sel && sel.value) {
        const parts = sel.value.split('-');
        if (parts.length === 2) {
            return {
                mes: parseInt(parts[1], 10),
                ano: parseInt(parts[0], 10),
                val: sel.value,
            };
        }
    }
    return {
        mes: currentMonth,
        ano: currentYear,
        val: `${currentYear}-${String(currentMonth).padStart(2, '0')}`,
    };
}

async function loadFixedLinks(pipefyId, monthVal = null) {
    let m = currentMonth;
    let y = currentYear;
    if (monthVal) {
        const parts = monthVal.split('-');
        if (parts.length === 2) {
            y = parseInt(parts[0], 10);
            m = parseInt(parts[1], 10);
        }
    }

    try {
        const res = await fetch(`/api/operacao/snapshot/${pipefyId}/${m}/${y}`);
        if (!res.ok) return;
        const snap = await res.json();

        const kpiUrl = (snap.kpis || {}).link || '';
        const forecastUrl = (snap.forecasting || {}).link || '';
        const relatorioAccUrl = (snap.relatorio_account || {}).link || '';
        const relatorioGtUrl  = (snap.relatorio_gt || {}).link || '';
        const relatorioConsolUrl = (snap.relatorio_mensal || {}).link || '';

        const setLink = (idPrefix, url) => {
            const anchor = document.getElementById(`fixed-link-${idPrefix}`);
            const label  = document.getElementById(`fixed-link-${idPrefix}-url`);
            if (anchor) {
                anchor.href = url || '#';
                if (url) {
                    anchor.style.opacity = '1';
                    anchor.style.pointerEvents = 'auto';
                    anchor.style.cursor = 'pointer';
                } else {
                    anchor.style.opacity = '0.45';
                    anchor.style.pointerEvents = 'none';
                    anchor.style.cursor = 'default';
                }
            }
            if (label) label.textContent = url || 'Sem link definido';
        };

        setLink('kpi', kpiUrl);
        setLink('forecasting', forecastUrl);
        setLink('relatorio_account', relatorioAccUrl);
        setLink('relatorio_gt', relatorioGtUrl);
        setLink('relatorio_mensal', relatorioConsolUrl);
    } catch (e) {
        console.error('Erro ao carregar links fixos:', e);
    }
}

function clearFixedLink(key) {
    if (!currentProject) {
        showToast('Selecione um projeto primeiro', 'error');
        return;
    }
    const tipoMap = { kpi: 'kpis', forecasting: 'forecasting' };
    const tipo = tipoMap[key] || key;
    showConfirmModal({
        title: 'Limpar Link',
        message: 'Deseja remover o link salvo deste card? Você pode adicionar um novo depois.',
        confirmText: 'Sim, limpar',
        onConfirm: async () => {
            try {
                const periodo = getLinksSelectedPeriod();
                const res = await fetch('/api/operacao/snapshot/links', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        pipefy_id: currentProject.pipefy_id,
                        mes: periodo.mes,
                        ano: periodo.ano,
                        tipo,
                        link: '',
                    }),
                });
                if (res.ok) {
                    showToast('Link removido');
                    loadFixedLinks(currentProject.pipefy_id, periodo.val);
                } else {
                    const err = await res.json().catch(() => ({}));
                    showToast(err.error || 'Falha ao remover link', 'error');
                }
            } catch (e) {
                console.error('[clearFixedLink]', e);
                showToast('Erro de conexão', 'error');
            }
        }
    });
}
window.clearFixedLink = clearFixedLink;

async function openFixedLinkModal(key) {
    const titles = { 
        kpi: "KPI's", 
        forecasting: 'Forecasting',
        relatorio_account: 'Relatório Mensal (Account)',
        relatorio_gt: 'Relatório Mensal (GT)',
        relatorio_mensal: 'Relatório Mensal Consolidado'
    };
    document.getElementById('fixed-link-key').value = key;
    document.getElementById('fixed-link-modal-title').textContent = `Definir Link — ${titles[key] || key}`;

    // Carrega valor atual do BD (do mês selecionado na aba de Links)
    let currentUrl = '';
    try {
        const periodo = getLinksSelectedPeriod();
        const res = await fetch(`/api/operacao/snapshot/${currentProject?.pipefy_id}/${periodo.mes}/${periodo.ano}`);
        if (res.ok) {
            const snap = await res.json();
            const tipoMap = { kpi: 'kpis', forecasting: 'forecasting' };
            currentUrl = (snap[tipoMap[key] || key] || {}).link || '';
        }
    } catch (e) { /* silencioso */ }

    document.getElementById('fixed-link-url-input').value = currentUrl;
    openGTModal('modal-fixed-link');
}

async function saveFixedLink() {
    const key = document.getElementById('fixed-link-key').value;
    const url = document.getElementById('fixed-link-url-input').value.trim();
    if (!url || !currentProject) return;

    // Mapeia 'kpi' → 'kpis' para o nome da seção no BD
    const tipoMap = { kpi: 'kpis', forecasting: 'forecasting' };
    const tipo = tipoMap[key] || key;
    const periodo = getLinksSelectedPeriod();

    try {
        const res = await fetch('/api/operacao/snapshot/links', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                pipefy_id: currentProject.pipefy_id,
                mes: periodo.mes,
                ano: periodo.ano,
                tipo,
                link: url,
            }),
        });
        if (!res.ok) {
            const err = await res.json();
            alert("Erro ao salvar link: " + (err.error || "Erro desconhecido"));
            return;
        }
        loadFixedLinks(currentProject.pipefy_id, periodo.val);
        closeGTModal('modal-fixed-link');
    } catch (e) {
        console.error('Erro ao salvar link fixo:', e);
        alert('Erro ao salvar link fixo: ' + e.message);
    }
}

async function loadLinks(pipefyId) {
    initMonthSelect('links-month-select');
    const grid = document.getElementById('links-grid');
    if (!grid) return;
    
    const sel = document.getElementById('links-month-select');
    loadFixedLinks(pipefyId, sel ? sel.value : null);

    try {
        const res = await fetch(`/api/operacao/links/${pipefyId}`);
        const data = await res.json();

        if (!Array.isArray(data) || data.length === 0) {
            grid.innerHTML = '<p style="color:var(--text-muted);padding:2rem;">Nenhum link cadastrado ainda.</p>';
            return;
        }

        grid.innerHTML = data.map(lk => {
            const safeTitulo = String(lk.titulo || '').replace(/</g, '&lt;');
            const safeDesc   = lk.descricao ? String(lk.descricao).replace(/</g, '&lt;') : '';
            const safeUrl    = String(lk.url || '').replace(/"/g, '&quot;');
            return `
            <div class="access-link-card link-util-card" style="display:flex;flex-direction:column;gap:0.85rem;height:100%;">
                <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
                    <div class="op-icon-box" style="margin:0;flex-shrink:0;"><i class="fas ${lk.icone || 'fa-link'}"></i></div>
                    <button type="button" onclick="event.stopPropagation();deleteLink(${lk.id})" title="Remover link"
                        style="background:rgba(214,22,22,0.1);border:1px solid rgba(214,22,22,0.2);color:var(--accent-red);cursor:pointer;font-size:0.85rem;width:34px;height:34px;border-radius:8px;display:flex;align-items:center;justify-content:center;transition:all 0.15s;"
                        onmouseover="this.style.background='var(--accent-red)';this.style.color='#fff';"
                        onmouseout="this.style.background='rgba(214,22,22,0.1)';this.style.color='var(--accent-red)';">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
                <div style="flex:1;display:flex;flex-direction:column;gap:4px;">
                    <div style="font-weight:600;font-size:1rem;color:var(--text-main);line-height:1.3;">${safeTitulo}</div>
                    ${safeDesc ? `<div style="font-size:0.82rem;color:var(--text-muted);line-height:1.4;">${safeDesc}</div>` : ''}
                </div>
                <a href="${safeUrl}" target="_blank" rel="noopener"
                    title="${safeUrl}"
                    style="display:flex;align-items:center;gap:8px;padding:0.6rem 0.85rem;border-radius:10px;background:rgba(214,22,22,0.08);border:1px solid rgba(214,22,22,0.15);color:var(--accent-red);text-decoration:none;font-size:0.85rem;font-weight:500;transition:all 0.15s;"
                    onmouseover="this.style.background='rgba(214,22,22,0.15)';"
                    onmouseout="this.style.background='rgba(214,22,22,0.08)';">
                    <i class="fas fa-external-link-alt" style="flex-shrink:0;font-size:0.8rem;"></i>
                    <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${safeUrl}</span>
                </a>
            </div>`;
        }).join('');
    } catch (e) { console.error("Erro ao carregar links:", e); }
}

async function saveLink() {
    const titulo = document.getElementById('link-titulo').value.trim();
    const url = document.getElementById('link-url').value.trim();
    const descricao = document.getElementById('link-descricao').value.trim();
    const icone = document.getElementById('link-icone').value.trim() || 'fa-link';

    if (!titulo || !url) { showToast('Título e URL são obrigatórios.', 'error'); return; }

    const payload = {
        pipefy_id: currentProject.pipefy_id,
        titulo, url, descricao, icone
    };

    try {
        const res = await fetch('/api/operacao/links', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            showToast('Link salvo!');
            closeGTModal('modal-novo-link');
            document.getElementById('link-titulo').value = '';
            document.getElementById('link-url').value = '';
            document.getElementById('link-descricao').value = '';
            document.getElementById('link-icone').value = 'fa-link';
            loadLinks(currentProject.pipefy_id);
        }
    } catch (e) { console.error(e); }
}

async function deleteLink(linkId) {
    showConfirmModal({
        title: 'Remover Link',
        message: 'Tem certeza que deseja remover este link?',
        confirmText: 'Sim, remover',
        onConfirm: async () => {
            try {
                await fetch(`/api/operacao/links/${linkId}`, { method: 'DELETE' });
                loadLinks(currentProject.pipefy_id);
            } catch (e) { console.error(e); }
        }
    });
}

function filterLinksByMonth(val) {
    if (!currentProject) return;
    loadFixedLinks(currentProject.pipefy_id, val);
}

// ─── CHECKIN ─────────────────────────────────────────────────────────────────

async function loadCheckins(pipefyId) {
    initMonthSelect('checkin-month-select');
    try {
        const res = await fetch(`/api/operacao/checkins/${pipefyId}`);
        const raw = await res.json();
        allCheckins = Array.isArray(raw) ? raw : [];
        const list = document.getElementById('checkin-list');
        if (!list) return;

        const sel = document.getElementById('checkin-month-select');
        renderCheckinsByMonth(sel ? sel.value : null);

    } catch (e) { console.error("Erro ao carregar checkins:", e); }
}

function renderCheckinsByMonth(monthVal) {
    const list = document.getElementById('checkin-list');
    if (!list) return;
    const filtered = monthVal
        ? allCheckins.filter(c => c.data && c.data.substring(0, 7) === monthVal)
        : allCheckins;
    list.innerHTML = '';
    if (!filtered.length) {
        list.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:2rem;">Nenhum checkin realizado ainda.</p>';
        return;
    }
    filtered.forEach(c => {
        const item = document.createElement('div');
        item.className = 'op-card-premium';
        item.style.cssText = `padding:1.5rem; margin-bottom:16px; border-left:4px solid ${c.compareceu ? '#10b981' : '#f59e0b'}; background: var(--card-bg);`;
        
        // Tags de Status Coordenadas
        const statusTags = `
            <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:12px;">
                <span style="font-size:0.65rem; font-weight:700; padding:4px 10px; border-radius:6px; background:${c.compareceu ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)'}; color:${c.compareceu ? '#10b981' : '#f59e0b'}; border:1px solid ${c.compareceu ? 'rgba(16,185,129,0.2)' : 'rgba(245,158,11,0.2)'};">
                    <i class="fas ${c.compareceu ? 'fa-user-check' : 'fa-user-clock'}"></i> STAKEHOLDER
                </span>
                <span style="font-size:0.65rem; font-weight:700; padding:4px 10px; border-radius:6px; background:${c.campanhas_ativas ? 'rgba(16,185,129,0.1)' : 'rgba(214,22,22,0.1)'}; color:${c.campanhas_ativas ? '#10b981' : '#D61616'}; border:1px solid ${c.campanhas_ativas ? 'rgba(16,185,129,0.2)' : 'rgba(214,22,22,0.2)'};">
                    <i class="fas ${c.campanhas_ativas ? 'fa-bolt' : 'fa-pause-circle'}"></i> CAMPANHAS
                </span>
                <span style="font-size:0.65rem; font-weight:700; padding:4px 10px; border-radius:6px; background:${!c.gap_comunicacao ? 'rgba(16,185,129,0.1)' : 'rgba(214,22,22,0.1)'}; color:${!c.gap_comunicacao ? '#10b981' : '#D61616'}; border:1px solid ${!c.gap_comunicacao ? 'rgba(16,185,129,0.2)' : 'rgba(214,22,22,0.2)'};">
                    <i class="fas ${!c.gap_comunicacao ? 'fa-comments' : 'fa-comment-slash'}"></i> COMUNICAÇÃO
                </span>
                <span style="font-size:0.65rem; font-weight:700; padding:4px 10px; border-radius:6px; background:${!c.cliente_reclamou ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)'}; color:${!c.cliente_reclamou ? '#10b981' : '#f59e0b'}; border:1px solid ${!c.cliente_reclamou ? 'rgba(16,185,129,0.2)' : 'rgba(245,158,11,0.2)'};">
                    <i class="fas ${!c.cliente_reclamou ? 'fa-smile' : 'fa-frown'}"></i> SATISFAÇÃO
                </span>
            </div>
        `;

        item.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div style="flex:1;">
                    <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
                        <div style="background:var(--accent-red); color:white; font-size:0.7rem; font-weight:800; padding:4px 12px; border-radius:20px; text-transform:uppercase; letter-spacing:0.5px;">
                            Semana ${c.semana.split('-W')[1] || c.semana}
                        </div>
                        <span style="font-size:0.85rem; font-weight:500; color:var(--text-muted);"><i class="far fa-calendar-alt"></i> ${c.data}</span>
                    </div>
                    
                    <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:12px; padding:1rem; margin-top:12px;">
                        <p style="font-size:0.9rem; color:var(--text-main); margin:0; line-height:1.6;">
                            ${c.obs ? c.obs : '<span style="opacity:0.5; font-style:italic;">Sem observações adicionais.</span>'}
                        </p>
                    </div>

                    ${statusTags}

                    ${c.transcricao_url ? `
                        <div style="margin-top:15px;">
                            <a href="${c.transcricao_url}" target="_blank" rel="noopener" style="display:inline-flex; align-items:center; gap:6px; font-size:0.78rem; font-weight:600; color:var(--accent-red); text-decoration:none; padding:6px 12px; border-radius:8px; background:rgba(214,22,22,0.05); border:1px solid rgba(214,22,22,0.1); transition:all 0.2s;">
                                <i class="fas fa-file-waveform"></i> Ouvir Transcrição do Check-in
                            </a>
                        </div>
                    ` : ''}
                </div>
                
                <button onclick="window.deleteCheckin(${c.mes}, ${c.ano}, ${c.original_index})" 
                    class="btn-add-task btn-auth-account"
                    style="background: transparent; color: #888; border: 1px solid var(--border-color); padding: 10px; width: 40px; height: 40px; border-radius:10px; display:flex; align-items:center; justify-content:center;"
                    onmouseover="this.style.color='#D61616'; this.style.borderColor='#D61616'; this.style.background='rgba(214,22,22,0.05)';"
                    onmouseout="this.style.color='#888'; this.style.borderColor='var(--border-color)'; this.style.background='transparent';"
                    title="Excluir este check-in">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </div>`;
        list.appendChild(item);
    });
}

function filterCheckinsByMonth(val) { renderCheckinsByMonth(val); }

async function saveCheckin() {
    const compareceu = document.getElementById('checkin-compareceu').value === 'true';
    const campanhasAtivas = document.getElementById('checkin-campanhas-ativas').value === 'true';
    const gapComunicacao = document.getElementById('checkin-gap-comunicacao').value === 'true';
    const clienteReclamou = document.getElementById('checkin-cliente-reclamou').value === 'true';
    const obs = document.getElementById('checkin-obs').value;
    const transcricao = document.getElementById('checkin-transcricao').value.trim();
    const dataInput = (document.getElementById('checkin-data') || {}).value;

    // Permite check-in retroativo: usa a data informada (ou hoje, se vazia).
    const ref = dataInput ? new Date(dataInput + 'T00:00:00') : new Date();
    const week = Math.ceil(((ref - new Date(ref.getFullYear(), 0, 1)) / 86400000 + 1) / 7);
    const semana_ano = `${ref.getFullYear()}-W${String(week).padStart(2, '0')}`;
    const dataIso = `${ref.getFullYear()}-${String(ref.getMonth() + 1).padStart(2, '0')}-${String(ref.getDate()).padStart(2, '0')}`;

    const payload = {
        pipefy_id: currentProject.pipefy_id,
        data: dataIso,
        semana_ano, compareceu,
        campanhas_ativas: campanhasAtivas,
        gap_comunicacao: gapComunicacao,
        cliente_reclamou: clienteReclamou,
        satisfeito: true, obs,
        transcricao_url: transcricao || null
    };

    try {
        const res = await fetch('/api/operacao/checkin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            showToast('Checkin registrado com sucesso!');
            document.getElementById('checkin-transcricao').value = '';
            document.getElementById('checkin-obs').value = '';
            closeGTModal('modal-novo-checkin');
            loadCheckins(currentProject.pipefy_id);
            await fetch(`/api/operacao/monthly-deliveries/${currentProject.pipefy_id}/${selectedMonth}/${selectedYear}`);
            loadEntregas(currentProject.pipefy_id, selectedMonth, selectedYear);
        } else {
            const err = await res.json();
            showToast(err.error || 'Falha ao registrar checkin', 'error');
        }
    } catch (e) { console.error(e); }
}

async function deleteCheckin(mes, ano, index) {
    if (!currentProject) {
        showToast("Selecione um projeto primeiro", "error");
        return;
    }
    showConfirmModal({
        title: 'Confirmar Exclusão',
        message: 'Tem certeza que deseja excluir este check-in? Esta ação não pode ser desfeita.',
        confirmText: 'Sim, excluir',
        onConfirm: async () => {
            try {
                const res = await fetch(`/api/operacao/checkin/${currentProject.pipefy_id}/${mes}/${ano}/${index}`, { method: 'DELETE' });
                if (res.ok) {
                    showToast('Check-in removido');
                    loadCheckins(currentProject.pipefy_id);
                    await fetch(`/api/operacao/monthly-deliveries/${currentProject.pipefy_id}/${selectedMonth}/${selectedYear}`);
                    loadEntregas(currentProject.pipefy_id, selectedMonth, selectedYear);
                } else {
                    const err = await res.json();
                    showToast(err.error || 'Falha ao deletar', 'error');
                }
            } catch (e) { console.error("[deleteCheckin] erro:", e); }
        }
    });
}

window.deleteCheckin = deleteCheckin;

async function deleteOtimizacao(mes, ano, index) {
    if (!currentProject) {
        showToast("Selecione um projeto primeiro", "error");
        return;
    }
    showConfirmModal({
        title: 'Excluir Otimização',
        message: 'Deseja excluir esta otimização? Esta ação não pode ser desfeita.',
        confirmText: 'Sim, excluir',
        onConfirm: async () => {
            try {
                const res = await fetch(`/api/operacao/otimizacao/${currentProject.pipefy_id}/${mes}/${ano}/${index}`, { method: 'DELETE' });
                if (res.ok) {
                    showToast('Otimização removida');
                    loadOtimizacoes(currentProject.pipefy_id);
                    await fetch(`/api/operacao/monthly-deliveries/${currentProject.pipefy_id}/${selectedMonth}/${selectedYear}`);
                    loadEntregas(currentProject.pipefy_id, selectedMonth, selectedYear);
                } else {
                    const err = await res.json();
                    showToast(err.error || 'Falha ao deletar', 'error');
                }
            } catch (e) { console.error("[deleteOtimizacao] erro:", e); }
        }
    });
}
window.deleteOtimizacao = deleteOtimizacao;

async function deletePlanoMidia() {
    if (!currentProject) {
        showToast("Selecione um projeto primeiro", "error");
        return;
    }
    showConfirmModal({
        title: 'Limpar Plano de Mídia',
        message: 'Deseja limpar todo o plano de mídia deste mês? Esta ação não pode ser desfeita.',
        confirmText: 'Sim, limpar',
        icon: 'fa-eraser',
        onConfirm: async () => {
            try {
                const url = `/api/operacao/plano-midia/${currentProject.pipefy_id}/${selectedMonth}/${selectedYear}`;
                const res = await fetch(url, { method: 'DELETE' });
                if (res.ok) {
                    showToast('Plano de mídia removido');
                    loadPlanoMidia(currentProject.pipefy_id, selectedMonth, selectedYear);
                    await fetch(`/api/operacao/monthly-deliveries/${currentProject.pipefy_id}/${selectedMonth}/${selectedYear}`);
                    loadEntregas(currentProject.pipefy_id, selectedMonth, selectedYear);
                } else {
                    const err = await res.json();
                    showToast(err.error || 'Falha ao deletar', 'error');
                }
            } catch (e) { console.error("[deletePlanoMidia] erro:", e); }
        }
    });
}
window.deletePlanoMidia = deletePlanoMidia;

// ─── WIZARD PLANO DE MÍDIA ────────────────────────────────────────────────────

let editorRows = [];
// Mês/ano alvo do wizard (permite editar meses passados a partir do histórico)
let wizardMes = null;
let wizardAno = null;

function openNovoPlanModal(mes, ano, prefill) {
    wizardMes = mes || currentMonth;
    wizardAno = ano || currentYear;

    const label = `${MESES_PT[wizardMes - 1]} ${wizardAno}`;
    const el = document.getElementById('display-wizard-date');
    if (el) el.innerText = label;

    // Seletor de período: permite criar/editar plano de mídia retroativo.
    const periodoInput = document.getElementById('wizard-periodo');
    if (periodoInput) periodoInput.value = `${wizardAno}-${String(wizardMes).padStart(2, '0')}`;

    if (prefill && Array.isArray(prefill.canais) && prefill.canais.length) {
        editorRows = prefill.canais.map(c => ({
            canal: c.canal || '',
            campanhas: c.campanhas || '',
            percent_budget: parseFloat(c.percent_budget) || 0
        }));
        renderEditorRows();
    } else {
        editorRows = [];
        addEditorRow();
    }

    const budgetInput = document.getElementById('wizard-total-budget');
    if (budgetInput) budgetInput.value = (prefill && prefill.budget_total) ? prefill.budget_total : 0;

    calculateEditorValues();
    openGTModal('modal-novo-plano');
}

function onWizardPeriodoChange(val) {
    // val no formato "YYYY-MM" vindo do <input type="month">
    if (!val) return;
    const parts = val.split('-');
    if (parts.length !== 2) return;
    wizardAno = parseInt(parts[0], 10);
    wizardMes = parseInt(parts[1], 10);
    const el = document.getElementById('display-wizard-date');
    if (el) el.innerText = `${MESES_PT[wizardMes - 1]} ${wizardAno}`;
    calculateEditorValues();
}

function addEditorRow() {
    editorRows.push({ canal: '', campanhas: '', percent_budget: 0 });
    renderEditorRows();
}

function removeEditorRow(index) {
    editorRows.splice(index, 1);
    renderEditorRows();
    calculateEditorValues();
}

function renderEditorRows() {
    const tbody = document.getElementById('wizard-editor-body');
    if (!tbody) return;
    tbody.innerHTML = editorRows.map((row, i) => `
        <tr>
            <td>
                <select class="gt-wizard-select" style="width:100%;font-size:0.8rem;" onchange="editorRows[${i}].canal=this.value;calculateEditorValues()">
                    <option ${row.canal === 'Meta Ads' ? 'selected' : ''}>Meta Ads</option>
                    <option ${row.canal === 'Google Ads' ? 'selected' : ''}>Google Ads</option>
                    <option ${row.canal === 'LinkedIn Ads' ? 'selected' : ''}>LinkedIn Ads</option>
                    <option ${row.canal === 'TikTok Ads' ? 'selected' : ''}>TikTok Ads</option>
                    <option ${row.canal === 'YouTube Ads' ? 'selected' : ''}>YouTube Ads</option>
                    <option ${row.canal === 'Outros' ? 'selected' : ''}>Outros</option>
                </select>
            </td>
            <td><input type="text" class="gt-wizard-input" style="font-size:0.8rem;" placeholder="Nome da campanha" value="${row.campanhas || ''}" onchange="editorRows[${i}].campanhas=this.value"></td>
            <td><input type="number" class="gt-wizard-input" style="font-size:0.8rem;width:60px;" min="0" max="100" value="${row.percent_budget || 0}" oninput="editorRows[${i}].percent_budget=parseFloat(this.value)||0;calculateEditorValues()"></td>
            <td id="row-budget-${i}">R$ 0,00</td>
            <td id="row-daily-${i}">R$ 0,00</td>
            <td><button onclick="removeEditorRow(${i})" style="background:none;border:none;color:#D61616;cursor:pointer;"><i class="fas fa-times"></i></button></td>
        </tr>`).join('');
}

function calculateEditorValues() {
    const total = parseFloat(document.getElementById('wizard-total-budget')?.value || 0);
    const days = new Date(wizardAno || currentYear, wizardMes || currentMonth, 0).getDate();
    let totalPct = 0, totalBudget = 0, totalDaily = 0;

    editorRows.forEach((row, i) => {
        const pct = row.percent_budget || 0;
        const budget = (pct / 100) * total;
        const daily = days > 0 ? budget / days : 0;
        totalPct += pct;
        totalBudget += budget;
        totalDaily += daily;
        const bEl = document.getElementById(`row-budget-${i}`);
        const dEl = document.getElementById(`row-daily-${i}`);
        if (bEl) bEl.innerText = `R$ ${budget.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
        if (dEl) dEl.innerText = `R$ ${daily.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
    });

    const tPct = document.getElementById('wizard-total-percent');
    const tCash = document.getElementById('wizard-total-cash');
    const tDay = document.getElementById('wizard-total-day');
    if (tPct) tPct.innerText = `${totalPct.toFixed(0)}%`;
    if (tCash) tCash.innerText = `R$ ${totalBudget.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
    if (tDay) tDay.innerText = `R$ ${totalDaily.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
}

function editCurrentPlan() {
    // Abre o wizard de criação para editar o plano atual
    openNovoPlanModal();
}

async function saveFinalPlan() {
    const total = parseFloat(document.getElementById('wizard-total-budget')?.value || 0);
    const mes = wizardMes || currentMonth;
    const ano = wizardAno || currentYear;
    const days = new Date(ano, mes, 0).getDate();

    if (editorRows.length === 0) {
        showToast('Adicione ao menos uma campanha.', 'error');
        return;
    }

    const canais = editorRows.map(row => ({
        canal: row.canal || 'Outros',
        campanhas: row.campanhas || '',
        percent_budget: row.percent_budget || 0,
        budget: ((row.percent_budget || 0) / 100) * total,
        budget_dia: days > 0 ? (((row.percent_budget || 0) / 100) * total) / days : 0,
    }));

    const payload = {
        pipefy_id: currentProject.pipefy_id,
        mes: mes,
        ano: ano,
        dados_plano: { budget_total: total, canais }
    };

    console.log('[plano-midia] enviando payload:', payload);
    try {
        const res = await fetch('/api/operacao/plano-midia', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await res.json().catch(() => ({}));
        console.log('[plano-midia] resposta:', res.status, result);

        if (res.ok && result.saved) {
            showToast(`Plano salvo! ${result.rows_total_for_project} linha(s) na tabela operacao para este projeto.`);
            console.log('[plano-midia] snapshot atual no BD:', result.snapshot);
            closeGTModal('modal-novo-plano');
            // Recarrega o histórico (reflete edição de meses passados)
            loadHistoricoPlanos(currentProject.pipefy_id);
            loadPlanoMidia(currentProject.pipefy_id, selectedMonth, selectedYear);
            await fetch(`/api/operacao/monthly-deliveries/${currentProject.pipefy_id}/${selectedMonth}/${selectedYear}`);
            loadEntregas(currentProject.pipefy_id, selectedMonth, selectedYear);
        } else {
            showToast('Falha ao salvar: ' + (result.error || `status ${res.status}`), 'error');
        }
    } catch (e) {
        console.error('[plano-midia] fetch error:', e);
        showToast('Erro de rede ao salvar o plano.', 'error');
    }
}

// ─── HISTÓRICO DE PLANOS DE MÍDIA ─────────────────────────────────────────────

async function loadHistoricoPlanos(pipefyId) {
    console.log(`[loadHistoricoPlanos] pipefy_id=${pipefyId}`);
    try {
        const res = await fetch(`/api/operacao/planos-midia/${pipefyId}`);
        const data = await res.json();
        renderHistoricoPlanos(data);
    } catch (e) { console.error("Erro ao carregar histórico:", e); }
}

let historicoPlanosData = [];

function renderHistoricoPlanos(data) {
    const container = document.getElementById('history-accordion-container');
    if (!container) return;

    historicoPlanosData = Array.isArray(data) ? data : [];

    if (!data.length) {
        container.innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:2rem;">Nenhum histórico encontrado para este projeto.</p>';
        return;
    }

    const podeEditar = hasGTAuth();

    container.innerHTML = data.map((p, idx) => {
        const monthId = `history-${p.mes}-${p.ano}`;
        const canaisHtml = p.canais.map(c => `
            <tr>
                <td>${c.canal}</td>
                <td>${c.campanhas}</td>
                <td>${c.percent_budget}%</td>
                <td>R$ ${c.budget.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</td>
            </tr>
        `).join('');

        return `
            <div class="history-month-item" id="${monthId}">
                <div class="history-month-header" onclick="toggleHistoryMonth('${monthId}')" style="display:flex; justify-content:space-between; align-items:center; cursor:pointer; padding:1.2rem; background:rgba(255,255,255,0.03); border-radius:12px; margin-bottom:8px; border:1px solid var(--border-color); transition:all 0.3s;">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <span class="badge-gt" style="background:var(--accent-red); color:white; padding:4px 12px; border-radius:20px; font-weight:600; font-size:0.75rem;">${MESES_PT[p.mes - 1]} ${p.ano}</span>
                        <span style="color: var(--text-main); font-size: 0.85rem; font-weight:600;">Budget Total: R$ ${p.budget_total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:12px;">
                        ${podeEditar ? `
                        <button onclick="event.stopPropagation(); editHistoryPlan(${idx})" title="Editar plano deste mês"
                            style="display:inline-flex; align-items:center; gap:6px; background:rgba(214,22,22,0.1); border:1px solid rgba(214,22,22,0.25); color:var(--accent-red); cursor:pointer; font-size:0.72rem; font-weight:600; padding:5px 12px; border-radius:8px; transition:all 0.15s;">
                            <i class="fas fa-pen"></i> Editar
                        </button>` : ''}
                        <i class="fas fa-chevron-down history-arrow" style="transition:transform 0.3s;"></i>
                    </div>
                </div>
                <div class="history-month-content" style="padding:1rem; background:rgba(0,0,0,0.1); border-radius:0 0 12px 12px; margin-top:-12px; margin-bottom:15px; border:1px solid var(--border-color); border-top:none;">
                    <table class="op-spreadsheet" style="font-size: 0.78rem; width:100%;">
                        <thead>
                            <tr>
                                <th>Canal</th>
                                <th>Campanha</th>
                                <th>%</th>
                                <th>Budget R$</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${canaisHtml}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }).join('');
}

function toggleHistoryMonth(id) {
    const item = document.getElementById(id);
    if (!item) return;
    item.classList.toggle('active');
}
window.toggleHistoryMonth = toggleHistoryMonth;

/**
 * Abre o wizard pré-preenchido para editar o plano de mídia de um mês passado.
 */
function editHistoryPlan(idx) {
    const p = historicoPlanosData[idx];
    if (!p) return;
    if (!hasGTAuth()) {
        showToast('Você não tem permissão para editar planos de mídia.', 'error');
        return;
    }
    closeGTModal('modal-historico-planos');
    openNovoPlanModal(p.mes, p.ano, { canais: p.canais, budget_total: p.budget_total });
}
window.editHistoryPlan = editHistoryPlan;

// ─── FILTRO DE BUSCA DE PROJETOS ──────────────────────────────────────────────

function filterProjects() {
    const searchValue = document.getElementById('opSearchInput').value.toLowerCase();
    document.querySelectorAll('.op-card-premium').forEach(card => {
        const name = (card.querySelector('h3')?.textContent || '').toLowerCase();
        const product = (card.querySelector('p')?.textContent || '').toLowerCase();
        const squad = (card.querySelector('.op-card-meta')?.textContent || '').toLowerCase();
        const match = name.includes(searchValue) || product.includes(searchValue) || squad.includes(searchValue);
        card.style.display = match ? '' : 'none';
    });
}

// ─── INICIALIZAÇÃO ────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    console.log('Operação JS V10.0 Ativo 🚀');
});

/**
 * Registra manualmente uma tarefa semanal para o Planner Monday.
 */
async function decrementPlannerMonday(pipefyId) {
    if (!pipefyId) return;
    showConfirmModal({
        title: 'Remover Registro',
        message: 'Deseja remover o último registro manual do Planner Monday?',
        confirmText: 'Sim, remover',
        onConfirm: async () => {
            try {
                const res = await fetch('/api/operacao/tarefas', {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        pipefy_id: pipefyId,
                        mes: selectedMonth,
                        ano: selectedYear,
                    })
                });
                if (res.ok) {
                    showToast('Registro do Planner Monday removido.');
                    await fetch(`/api/operacao/monthly-deliveries/${pipefyId}/${selectedMonth}/${selectedYear}`);
                    loadProjectData();
                } else {
                    const err = await res.json();
                    showToast(err.error || 'Erro ao remover.', 'error');
                }
            } catch (e) {
                console.error(e);
                showToast('Erro de conexão.', 'error');
            }
        }
    });
}
window.decrementPlannerMonday = decrementPlannerMonday;

async function incrementPlannerMonday(pipefyId) {
    if (!pipefyId) return;
    
    const now = new Date();
    const start = new Date(now.getFullYear(), 0, 1);
    const week = Math.ceil(((now - start) / 86400000 + 1) / 7);
    const referencia = `${now.getFullYear()}-W${String(week).padStart(2, '0')}`;

    const payload = {
        pipefy_id: pipefyId,
        tipo: 'semanal',
        descricao: `Registro manual via dashboard em ${now.toLocaleDateString('pt-BR')}`,
        referencia: referencia,
        mes: selectedMonth,
        ano: selectedYear,
    };

    try {
        const res = await fetch('/api/operacao/tarefas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            showToast('Registro do Planner Monday adicionado!');
            await fetch(`/api/operacao/monthly-deliveries/${pipefyId}/${selectedMonth}/${selectedYear}`);
            loadProjectData();
        } else {
            const err = await res.json();
            showToast(err.error || 'Erro ao registrar.', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Erro de conexão.', 'error');
    }
}
window.incrementPlannerMonday = incrementPlannerMonday;


// ═══ FATURAMENTO VARIÁVEL ═════════════════════════════════════════════════════════════════════
// Módulo isolado para CRUD do faturamento variável por projeto/mês/ano.

/**
 * Carrega todos os registros de faturamento variável do projeto.
 */
async function loadFaturamentoVariavel() {
    if (!currentProject) return;
    const pid = currentProject.pipefy_id;
    const fee = parseFloat(currentProject.fee || 0);
    const isCientista = currentProject.cientista === true;

    try {
        const res = await fetch(`/api/projetos/${pid}/faturamento-variavel`);
        const data = await res.json();
        currentFatVariavelRecords = data.registros || [];
        renderFaturamentoVariavel(currentFatVariavelRecords, fee, isCientista);
    } catch (e) {
        console.error('[fat_variavel] Erro ao carregar:', e);
    }
}

/**
 * Formata número como moeda BRL.
 */
function _fmtBRL(val) {
    return 'R$ ' + parseFloat(val || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/**
 * Renderiza o painel de resumo focado no mês atual (currentMonth/currentYear).
 * Agora suporta múltiplos registros por mês, somando os valores para o KPI.
 */
function renderFaturamentoVariavel(registros, feeProjeto, isCientista) {
    const emptyEl  = document.getElementById('fat-variavel-empty');
    const resumoEl = document.getElementById('fat-variavel-resumo');
    const listEl   = document.getElementById('fat-variavel-list');

    if (!emptyEl || !resumoEl || !listEl) return;

    // Busca todos os registros específicos do mês atual
    const regsMes = registros.filter(r => r.mes === currentMonth && r.ano === currentYear);

    if (regsMes.length === 0) {
        emptyEl.style.display = 'block';
        resumoEl.style.display = 'none';
        listEl.style.display = 'none';
        const pEmpty = emptyEl.querySelector('p');
        if (pEmpty) pEmpty.textContent = `Nenhum faturamento registrado para ${MESES_PT[currentMonth-1]} ${currentYear}.`;
        return;
    }

    emptyEl.style.display = 'none';
    resumoEl.style.display = 'block';
    listEl.style.display = 'block';

    // Soma os valores de todos os registros do mês
    const totalFatCliente = regsMes.reduce((acc, r) => acc + parseFloat(r.faturamento_cliente || 0), 0);
    const totalValorVar   = regsMes.reduce((acc, r) => acc + parseFloat(r.valor_variavel || 0), 0);
    
    const feeBase     = isCientista ? feeProjeto * 1.5 : feeProjeto;
    const feeTotal    = feeBase + totalValorVar;

    // Atualiza KPI cards
    const elFat  = document.getElementById('fat-variavel-faturamento');
    const elPct  = document.getElementById('fat-variavel-percentual');
    const elVar  = document.getElementById('fat-variavel-valor');
    const elTot  = document.getElementById('fat-variavel-total');
    const elBrk  = document.getElementById('fat-variavel-breakdown');

    if (elFat) elFat.textContent = _fmtBRL(totalFatCliente);
    if (elPct) {
        if (regsMes.length === 1) elPct.textContent = `${regsMes[0].percentual}%`;
        else elPct.textContent = "Variado";
    }
    if (elVar) elVar.textContent = _fmtBRL(totalValorVar);
    if (elTot) elTot.textContent = _fmtBRL(feeTotal);
    if (elBrk) {
        const formulaFixa = isCientista ? `(${_fmtBRL(feeProjeto)} × 1.5)` : _fmtBRL(feeProjeto);
        elBrk.textContent = `${formulaFixa} + ${_fmtBRL(totalValorVar)} = ${_fmtBRL(feeTotal)}`;
    }

    // Renderiza a tabela do mês atual na aba
    const podeOperar = window.__CAN_OPERAR__ === true;
    listEl.innerHTML = `
        <div class="op-card-premium" style="overflow:hidden;">
            <div style="padding:1rem 1.2rem; border-bottom:1px solid rgba(255,255,255,0.05); display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:600; font-size:0.85rem; color:var(--text-muted);">Registros de ${MESES_PT[currentMonth-1]} ${currentYear}</span>
            </div>
            <table style="width:100%;border-collapse:collapse;font-size:0.85rem;">
                <thead>
                    <tr style="background:rgba(214,22,22,0.04);">
                        <th style="padding:0.75rem 1rem;text-align:left;color:var(--text-muted);font-weight:600;font-size:0.75rem;text-transform:uppercase;">Faturamento Cliente</th>
                        <th style="padding:0.75rem 1rem;text-align:right;color:var(--text-muted);font-weight:600;font-size:0.75rem;text-transform:uppercase;">%</th>
                        <th style="padding:0.75rem 1rem;text-align:right;color:var(--text-muted);font-weight:600;font-size:0.75rem;text-transform:uppercase;">Valor Variável</th>
                        <th style="padding:0.75rem 1rem;text-align:center;color:var(--text-muted);font-weight:600;font-size:0.75rem;text-transform:uppercase;">Registrado em</th>
                        ${podeOperar ? '<th style="padding:0.75rem 1rem;text-align:center;width:80px;"></th>' : ''}
                    </tr>
                </thead>
                <tbody>
                    ${regsMes.map(r => `
                        <tr style="border-top:1px solid rgba(255,255,255,0.05);">
                            <td style="padding:0.8rem 1rem;">${_fmtBRL(r.faturamento_cliente)}</td>
                            <td style="padding:0.8rem 1rem;text-align:right;color:var(--accent-red);font-weight:600;">${r.percentual}%</td>
                            <td style="padding:0.8rem 1rem;text-align:right;color:#10b981;font-weight:700;">${_fmtBRL(r.valor_variavel)}</td>
                            <td style="padding:0.8rem 1rem;text-align:center;font-size:0.75rem;color:var(--text-muted);">
                                ${r.criado_em ? new Date(r.criado_em).toLocaleDateString('pt-BR') : '—'}
                            </td>
                            ${podeOperar ? `
                            <td style="padding:0.8rem 1rem;text-align:center;">
                                <button onclick="openFatVariavelModal(${r.mes}, ${r.ano}, '${r.id}')" 
                                    style="background:none;border:none;cursor:pointer;color:var(--text-muted);margin-right:4px;" title="Editar">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button onclick="deleteFatVariavel(${r.mes}, ${r.ano}, '${r.id}')" 
                                    style="background:none;border:none;cursor:pointer;color:var(--accent-red);" title="Excluir">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </td>` : ''}
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

/**
 * Abre o modal de histórico e renderiza a tabela com todos os registros.
 */
function openFatVariavelHistory() {
    const container = document.getElementById('fat-variavel-history-list');
    if (!container) return;

    if (!currentFatVariavelRecords || currentFatVariavelRecords.length === 0) {
        container.innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:2rem;">Nenhum registro no histórico.</p>';
        openGTModal('modal-fat-variavel-historico');
        return;
    }

    const podeOperar = window.__CAN_OPERAR__ === true;

    container.innerHTML = `
        <div class="op-card-premium" style="overflow:hidden; background:rgba(0,0,0,0.2);">
            <table style="width:100%;border-collapse:collapse;font-size:0.85rem;">
                <thead>
                    <tr style="background:rgba(214,22,22,0.08);">
                        <th style="padding:0.75rem 1rem;text-align:left;color:var(--text-muted);font-weight:600;font-size:0.75rem;text-transform:uppercase;">Competência</th>
                        <th style="padding:0.75rem 1rem;text-align:right;color:var(--text-muted);font-weight:600;font-size:0.75rem;text-transform:uppercase;">Faturamento</th>
                        <th style="padding:0.75rem 1rem;text-align:right;color:var(--text-muted);font-weight:600;font-size:0.75rem;text-transform:uppercase;">%</th>
                        <th style="padding:0.75rem 1rem;text-align:right;color:var(--text-muted);font-weight:600;font-size:0.75rem;text-transform:uppercase;">Variável</th>
                        <th style="padding:0.75rem 1rem;text-align:center;color:var(--text-muted);font-weight:600;font-size:0.75rem;text-transform:uppercase;">Data</th>
                        ${podeOperar ? '<th style="padding:0.75rem 1rem;text-align:center;width:80px;"></th>' : ''}
                    </tr>
                </thead>
                <tbody>
                    ${currentFatVariavelRecords.map(r => `
                        <tr style="border-top:1px solid rgba(255,255,255,0.05);">
                            <td style="padding:0.8rem 1rem;font-weight:600;">${MESES_PT[r.mes - 1]} ${r.ano}</td>
                            <td style="padding:0.8rem 1rem;text-align:right;">${_fmtBRL(r.faturamento_cliente)}</td>
                            <td style="padding:0.8rem 1rem;text-align:right;color:var(--accent-red);">${r.percentual}%</td>
                            <td style="padding:0.8rem 1rem;text-align:right;color:#10b981;font-weight:700;">${_fmtBRL(r.valor_variavel)}</td>
                            <td style="padding:0.8rem 1rem;text-align:center;font-size:0.7rem;color:var(--text-muted);">
                                ${r.criado_em ? new Date(r.criado_em).toLocaleDateString('pt-BR') : '—'}
                            </td>
                            ${podeOperar ? `
                            <td style="padding:0.8rem 1rem;text-align:center;">
                                <button onclick="closeGTModal('modal-fat-variavel-historico'); openFatVariavelModal(${r.mes}, ${r.ano}, '${r.id}')" 
                                    style="background:none;border:none;cursor:pointer;color:var(--text-muted);margin-right:4px;" title="Editar">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button onclick="deleteFatVariavel(${r.mes}, ${r.ano}, '${r.id}')" 
                                    style="background:none;border:none;cursor:pointer;color:var(--accent-red);" title="Excluir">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </td>` : ''}
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
    openGTModal('modal-fat-variavel-historico');
}

/**
 * Abre o modal de registro de faturamento variável.
 * Agora suporta 'registroId' para edição específica.
 */
function openFatVariavelModal(mes = null, ano = null, registroId = null) {
    const fatInput = document.getElementById('fat-variavel-form-faturamento');
    const pctInput = document.getElementById('fat-variavel-form-percentual');
    const mesHid   = document.getElementById('fat-variavel-form-mes');
    const anoHid   = document.getElementById('fat-variavel-form-ano');
    const idHid    = document.getElementById('fat-variavel-form-id');

    const mesRef = mes || currentMonth;
    const anoRef = ano || currentYear;

    if (mesHid) mesHid.value = mesRef;
    if (anoHid) anoHid.value = anoRef;
    if (idHid)  idHid.value  = registroId || '';
    if (fatInput) fatInput.value = '';
    if (pctInput) pctInput.value = '';


    // Se for edição por ID
    if (registroId) {
        const reg = currentFatVariavelRecords.find(r => r.id === registroId);
        if (reg) {
            if (fatInput) fatInput.value = reg.faturamento_cliente || '';
            if (pctInput) pctInput.value = reg.percentual || '';
            if (mesHid) mesHid.value = reg.mes;
            if (anoHid) anoHid.value = reg.ano;
            
            // Bloqueia troca de mês/ano na edição para evitar inconsistência de banco
            if (mesHid) mesHid.disabled = true;
            if (anoHid) anoHid.disabled = true;
            
            calcPreviewFatVariavel();
        }
    } else {
        if (mesHid) mesHid.disabled = false;
        if (anoHid) anoHid.disabled = false;
    }


    document.getElementById('fat-variavel-preview').style.display = 'none';
    openGTModal('modal-fat-variavel');
}

/**
 * Fecha o modal de faturamento variável.
 */
function closeFatVariavelModal() {
    closeGTModal('modal-fat-variavel');
}

/**
 * Calcula e exibe o preview do valor variável em tempo real.
 */
function calcPreviewFatVariavel() {
    const fat = parseFloat(document.getElementById('fat-variavel-form-faturamento')?.value || 0);
    const pct = parseFloat(document.getElementById('fat-variavel-form-percentual')?.value || 0);
    const previewEl = document.getElementById('fat-variavel-preview');
    const valorEl   = document.getElementById('fat-variavel-preview-valor');
    const formulaEl = document.getElementById('fat-variavel-preview-formula');

    if (!previewEl) return;
    if (!fat || !pct) {
        previewEl.style.display = 'none';
        return;
    }

    const valorVar = fat * (pct / 100);
    previewEl.style.display = 'block';
    if (valorEl) valorEl.textContent = _fmtBRL(valorVar);
    if (formulaEl) formulaEl.textContent = `${_fmtBRL(fat)} × ${pct}% = ${_fmtBRL(valorVar)}`;
}

/**
 * Salva um registro de faturamento variável via API.
 */
async function saveFatVariavel() {
    if (!currentProject) return;

    const mes  = parseInt(document.getElementById('fat-variavel-form-mes')?.value || 0);
    const ano  = parseInt(document.getElementById('fat-variavel-form-ano')?.value || 0);
    const fat  = parseFloat(document.getElementById('fat-variavel-form-faturamento')?.value || 0);
    const pct  = parseFloat(document.getElementById('fat-variavel-form-percentual')?.value || 0);
    const id   = document.getElementById('fat-variavel-form-id')?.value || null;

    if (!mes || !ano || !fat || pct === undefined || pct === null) {
        showToast('Preencha os campos de faturamento e percentual.', 'error');
        return;
    }

    try {
        const payload = { mes, ano, faturamento_cliente: fat, percentual: pct };
        if (id) payload.id = id;

        const res = await fetch(`/api/projetos/${currentProject.pipefy_id}/faturamento-variavel`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (res.ok) {
            let msg = data.message || 'Faturamento variável salvo!';
            if (mes !== currentMonth || ano !== currentYear) {
                msg += ` (Calculado para ${MESES_PT[mes-1]} ${ano})`;
            }
            showToast(msg, 'success');
            closeFatVariavelModal();
            loadFaturamentoVariavel();
        } else {
            showToast(data.error || 'Erro ao salvar.', 'error');
        }
    } catch (e) {
        console.error('[fat_variavel] Erro ao salvar:', e);
        showToast('Erro de conexão.', 'error');
    }
}

/**
 * Remove um registro de faturamento variável.
 */
async function deleteFatVariavel(mes, ano, registroId = null) {
    if (!currentProject) return;

    showConfirmModal({
        title: 'Excluir Faturamento Variável',
        message: `Deseja remover este registro de ${MESES_PT[mes - 1]} ${ano}?`,
        confirmText: 'Sim, excluir',
        onConfirm: async () => {
            try {
                let url = `/api/projetos/${currentProject.pipefy_id}/faturamento-variavel/${mes}/${ano}`;
                if (registroId) url += `?id=${registroId}`;

                const res = await fetch(url, { method: 'DELETE' });
                if (res.ok) {
                    showToast('Registro removido.');
                    closeGTModal('modal-fat-variavel-historico');
                    loadFaturamentoVariavel();
                } else {
                    const err = await res.json();
                    showToast(err.error || 'Erro ao excluir.', 'error');
                }
            } catch (e) {
                console.error('[fat_variavel] Erro ao excluir:', e);
                showToast('Erro de conexão.', 'error');
            }
        }
    });
}

// Expor funções globalmente
window.loadFaturamentoVariavel  = loadFaturamentoVariavel;
window.openFatVariavelModal     = openFatVariavelModal;
window.closeFatVariavelModal    = closeFatVariavelModal;
window.calcPreviewFatVariavel   = calcPreviewFatVariavel;
window.saveFatVariavel          = saveFatVariavel;
window.deleteFatVariavel        = deleteFatVariavel;
window.openFatVariavelHistory   = openFatVariavelHistory;
