/**
 * LÓGICA DE OPERAÇÃO - HUB LISBOA&CO V10.0
 * Entregas 100% automáticas, desacopladas por cargo.
 * Links Úteis, Otimizações e Plano de Mídia com renderização real.
 */

let currentProject = null;
let currentMonth = new Date().getMonth() + 1;
let currentYear = new Date().getFullYear();

// ─── LABELS DE ENTREGAS POR CARGO ────────────────────────────────────────────

const DELIVERY_LABELS = {
    // Account
    checkin: { label: "Check-in Semanal", desc: "Automático ao registrar checkin no mês" },
    relatorio_account: { label: "Definição de Meta (Account)", desc: "Automático ao concluir meta estratégica" },
    planner_monday: { label: "Planner Monday Semanal", desc: "Automático ao registrar ≥4 tarefas semanais" },
    forecasting: { label: "Atualização do Forecasting com Metas", desc: "Automático ao registrar meta estratégica" },
    // Gestor de Tráfego
    plano_midia: { label: "Plano de Mídia", desc: "Automático ao salvar plano de mídia" },
    otimizacao: { label: "Documento de Otimização", desc: "Automático ao registrar otimização" },
    relatorio_gt: { label: "Definição de Meta (GT)", desc: "Automático ao concluir meta estratégica" },
    config_conta: { label: "Configurações de Conta", desc: "Automático ao registrar ≥4 tarefas semanais" },
};

const ROLE_DELIVERY_ORDER = {
    "Account": ["checkin", "relatorio_account", "planner_monday", "forecasting"],
    "Gestor de Tráfego": ["plano_midia", "otimizacao", "relatorio_gt", "config_conta"],
};

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

// ─── NAVEGAÇÃO ────────────────────────────────────────────────────────────────

function openProjectDetails(project) {
    currentProject = project;
    document.getElementById('display-project-name').innerText = project.nome;
    document.getElementById('project-selection-view').style.display = 'none';
    document.getElementById('project-details-view').style.display = 'block';
    switchOperacaoTab('dashboard');
    loadProjectData();
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
        if (tabId === 'entregas') loadEntregas(pid, currentMonth, currentYear);
    }
}

// ─── CARREGAMENTO GERAL ───────────────────────────────────────────────────────

async function loadProjectData() {
    if (!currentProject) return;
    const pipefyId = currentProject.pipefy_id;

    loadTarefas(pipefyId, 'semanal', 'main-task-list');
    
    // Carrega o snapshot de metas (Default: Trimestral do período atual)
    const q = `Q${Math.floor((currentMonth - 1) / 3) + 1}`;
    const ref = `${currentYear}-${q}`;
    loadTarefas(pipefyId, 'goal_snapshot', 'quarter-task-list', ref);
    
    // Reseta o seletor visual para Trimestral
    const filter = document.getElementById('meta-period-filter');
    if (filter) filter.value = 'quarter';

    loadPlanoMidia(pipefyId, currentMonth, currentYear);
    loadEntregas(pipefyId, currentMonth, currentYear);
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
                <button class="btn-delete-task" style="opacity:0.3;pointer-events:none;"><i class="fas fa-lock"></i></button>
            `;
            list.appendChild(item);
        });
    } catch (e) { console.error("Erro ao carregar tasks:", e); }
}

function renderMetasDashboard(metas, referencia = "") {
    const mainGoalContainer = document.getElementById('main-goal-card-container');
    const subGoalsList = document.getElementById('quarter-task-list');
    const totalProgressEl = document.getElementById('total-progress-percent');
    const periodLabelEl = document.getElementById('display-period-label');
    
    if (!mainGoalContainer || !subGoalsList) return;

    // Atualiza Label do Período
    if (periodLabelEl) {
        if (referencia === "quarter") periodLabelEl.innerText = "TRIMESTRE ATUAL";
        else if (referencia.includes('-Q')) periodLabelEl.innerText = `TRIMESTRE: ${referencia.split('-')[1]}`;
        else if (referencia.includes('-M')) {
            const months = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
            const parts = referencia.split('-M');
            const mIdx = parseInt(parts[1]) - 1;
            periodLabelEl.innerText = `MÊS: ${months[mIdx].toUpperCase()} ${parts[0]}`;
        } else {
            periodLabelEl.innerText = "PERÍODO ATIVO";
        }
    }

    if (!metas || metas.length === 0) {
        if (totalProgressEl) totalProgressEl.innerText = '0%';
        mainGoalContainer.innerHTML = `
            <div class="op-card-premium main-goal-card empty" style="background: rgba(255,255,255,0.01); border: 1px dashed var(--border-color); height: 150px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; border-radius: 16px;">
                <i class="fas fa-bullseye" style="font-size: 2rem; color: var(--border-color); margin-bottom: 0.5rem;"></i>
                <p style="color: var(--text-muted); font-size: 0.9rem;">Nenhum planejamento definido para este período.</p>
                <button class="btn-add-task" style="margin-top: 1rem; font-size: 0.75rem;" onclick="openMetaUnificadoModal()">+ Iniciar Planejamento</button>
            </div>`;
        subGoalsList.innerHTML = '';
        return;
    }

    // O novo formato usa um único objeto (Snapshot)
    const snapshot = metas[0];
    let data = {};
    try {
        data = JSON.parse(snapshot.descricao);
    } catch(e) {
        console.error("Erro ao processar snapshot de meta:", e);
        return;
    }

    // Cálculo de Progresso Geral
    const krs = data.krs || [];
    const totalItems = 1 + krs.length; // Objetivo Principal + KRs
    const completedMain = snapshot.concluida ? 1 : 0;
    const completedKRs = krs.filter(k => k.concluida).length;
    const totalPercent = Math.round(((completedMain + completedKRs) / totalItems) * 100);
    
    if (totalProgressEl) {
        totalProgressEl.innerText = `${totalPercent}%`;
        totalProgressEl.style.color = totalPercent >= 100 ? '#4caf50' : (totalPercent >= 50 ? '#ff9800' : 'var(--accent-red)');
    }

    const goalTypeIcons = {
        faturamento: 'fa-dollar-sign',
        leads: 'fa-bullseye',
        vendas: 'fa-shopping-cart',
        engajamento: 'fa-chart-line',
        outros: 'fa-rocket'
    };

    const progress = snapshot.concluida ? 100 : 0;
    
    // Renderiza Meta Principal
    mainGoalContainer.innerHTML = `
        <div class="op-card-premium main-goal-card highlight" style="position: relative; overflow: hidden; background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(0,0,0,0.4) 100%); border: 1px solid var(--accent-red); padding: 2rem; border-radius: 20px; min-height: 180px; display: flex; flex-direction: column; justify-content: center;">
            <div style="position: absolute; top: -10px; right: -10px; font-size: 6rem; color: rgba(214, 22, 22, 0.08); transform: rotate(-10deg); pointer-events: none;">
                <i class="fas ${goalTypeIcons[data.tipo_meta] || 'fa-rocket'}"></i>
            </div>
            
            <div style="z-index: 1;">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 0.5rem;">
                    <span class="badge-gt" style="background: var(--accent-red); display: inline-block;">OBJETIVO PRIMÁRIO</span>
                </div>
                <h2 style="font-size: 1.8rem; margin: 0.5rem 0; color: #fff;">${data.nome}</h2>
                ${data.valor_alvo ? `<p style="color: #fff; font-size: 1rem; font-weight: 600; opacity: 0.8;">Alvo: ${data.tipo_meta === 'faturamento' ? 'R$ ' : ''}${parseFloat(data.valor_alvo).toLocaleString('pt-BR')}</p>` : ''}
                
                <div style="margin-top: 1.5rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.4rem; font-size: 0.85rem;">
                        <span style="color: #aaa;">Status da Meta</span>
                        <span style="color: ${snapshot.concluida ? '#4caf50' : 'var(--accent-red)'}; font-weight: 700;">${snapshot.concluida ? 'Concluída' : 'Em andamento'}</span>
                    </div>
                    <div style="height: 6px; background: rgba(255,255,255,0.1); border-radius: 10px; overflow: hidden;">
                        <div style="height: 100%; width: ${progress}%; background: var(--accent-red); box-shadow: 0 0 10px var(--accent-red); transition: width 1s ease-in-out;"></div>
                    </div>
                </div>
            </div>
            
            <div style="position: absolute; top: 15px; right: 15px; display: flex; gap: 10px; z-index: 2;">
                <button onclick="openMetaUnificadoModal(${snapshot.id})" class="btn-icon-subtle" title="Editar Planejamento"><i class="fas fa-edit"></i></button>
                <button onclick="toggleUnifiedMainGoal(${snapshot.id}, ${snapshot.concluida})" style="background: rgba(255,255,255,0.05); border: 1px solid var(--border-color); color: #fff; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; transition: all 0.3s;" title="Marcar como Concluída" onmouseover="this.style.background='var(--accent-red)'" onmouseout="this.style.background='rgba(255,255,255,0.05)'">
                    <i class="fas fa-check"></i>
                </button>
            </div>
        </div>`;

    // Render Key Results (KRs)
    subGoalsList.innerHTML = '';
    if (krs.length === 0) {
        subGoalsList.innerHTML = '<p style="color:var(--text-muted);padding:1rem;font-size:0.9rem;text-align:center;">Nenhum Key Result definido para este planejamento.</p>';
    } else {
        krs.forEach((kr, idx) => {
            const krItem = document.createElement('div');
            krItem.className = `task-item goal-kr-item ${kr.concluida ? 'completed' : ''}`;
            krItem.style.marginBottom = '0.8rem';
            krItem.style.padding = '1rem';
            krItem.style.background = 'rgba(255,255,255,0.02)';
            krItem.style.borderRadius = '12px';
            krItem.style.border = '1px solid var(--border-color)';
            krItem.style.display = 'flex';
            krItem.style.alignItems = 'center';
            krItem.style.gap = '1.2rem';

            krItem.innerHTML = `
                <div class="task-checkbox" onclick="toggleUnifiedKR(${snapshot.id}, ${idx})" style="width: 26px; height: 26px; min-width: 26px; font-size: 0.75rem;"><i class="fas fa-check"></i></div>
                <div style="flex: 1;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">
                        <div>
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 2px;">
                                <i class="fas fa-bullseye" style="color: var(--accent-red); font-size: 0.8rem;"></i>
                                <span style="font-size: 0.65rem; color: #888; text-transform: uppercase; font-weight: 600;">KR #0${idx + 1}</span>
                            </div>
                            <div class="task-text" style="font-weight: 500; font-size: 0.95rem; color: #eee;">${kr.titulo}</div>
                        </div>
                        ${kr.alvo ? `<div style="text-align: right;"><span style="font-size: 0.8rem; font-weight: 700; color: #fff;">${parseFloat(kr.alvo).toLocaleString('pt-BR')}</span><div style="font-size: 0.6rem; color: #888; text-transform: uppercase;">Meta</div></div>` : ''}
                    </div>
                </div>
            `;
            subGoalsList.appendChild(krItem);
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
    const periodType = document.getElementById('unified-goal-period').value;
    
    if (!nome) { showToast('Nome do objetivo é obrigatório', 'error'); return; }

    const krs = [];
    document.querySelectorAll('.kr-input-row').forEach(row => {
        const title = row.querySelector('.kr-title').value;
        const krTarget = row.querySelector('.kr-target').value;
        if (title) {
            krs.push({ titulo: title, alvo: krTarget, concluida: row.dataset.concluida === 'true' });
        }
    });

    const snapshotData = {
        nome,
        valor_alvo: target,
        tipo_meta: type,
        periodo: periodType,
        krs: krs,
        versao: '3.0'
    };

    let referencia = "";
    if (periodType === 'mensal') {
        referencia = `${currentYear}-M${String(currentMonth).padStart(2, '0')}`;
    } else {
        referencia = `${currentYear}-Q${Math.floor((currentMonth - 1) / 3) + 1}`;
    }

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
            handlePeriodFilterChange(document.getElementById('meta-period-filter'));
        }
    } catch (e) { console.error(e); }
}

async function handlePeriodFilterChange(select) {
    const val = select.value;
    let referencia = val;
    if (val === 'quarter') {
        referencia = `${currentYear}-Q${Math.floor((currentMonth - 1) / 3) + 1}`;
    }
    loadTarefas(currentProject.pipefy_id, 'goal_snapshot', 'quarter-task-list', referencia);
}

async function toggleUnifiedMainGoal(id, currentStatus) {
    try {
        await fetch('/api/operacao/tarefas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: id, concluida: !currentStatus })
        });
        handlePeriodFilterChange(document.getElementById('meta-period-filter'));
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
        handlePeriodFilterChange(document.getElementById('meta-period-filter'));
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
        tipo, descricao: descInput.value, referencia, ano: currentYear
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
            await fetch(`/api/operacao/monthly-deliveries/${currentProject.pipefy_id}/${currentMonth}/${currentYear}`);
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
        loadEntregas(currentProject.pipefy_id, currentMonth, currentYear);
    } catch (e) { console.error(e); }
}

// ─── ENTREGAS DO MÊS (READ-ONLY, AUTOMÁTICAS) ────────────────────────────────

async function loadEntregas(pipefyId, mes, ano) {
    const meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
    const dateEl = document.getElementById('display-entregas-date');
    if (dateEl) dateEl.innerText = `[${meses[mes - 1]} ${ano}]`;

    const container = document.getElementById('entregas-grid');
    if (!container) return;

    try {
        const res = await fetch(`/api/operacao/monthly-deliveries/${pipefyId}/${mes}/${ano}`);
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        const entregas = await res.json();

        // Determinar cargo do usuário via sessão (injetado pelo template)
        const userRole = window.__USER_ROLE__ || "";
        const deliveryOrder = ROLE_DELIVERY_ORDER[userRole] || [];

        if (entregas.length === 0 && deliveryOrder.length === 0) {
            container.innerHTML = '<p style="color:var(--text-muted);padding:2rem;text-align:center;">Entregas serão geradas automaticamente conforme você registrar atividades.</p>';
            return;
        }

        // Mapear entregas por tipo para lookup rápido
        const entregaMap = {};
        entregas.forEach(e => { entregaMap[e.delivery_type] = e; });

        const orderedTypes = deliveryOrder.length ? deliveryOrder :
            (entregas.length ? entregas.map(e => e.delivery_type) : []);

        container.innerHTML = orderedTypes.map((dtype, index) => {
            const entrega = entregaMap[dtype] || { status: 'pending', mrr_contribution: 0 };
            const info = DELIVERY_LABELS[dtype] || { label: dtype, desc: "" };
            const isConcluida = entrega.status === 'completed';
            return `
                <div class="entrega-card ${isConcluida ? 'concluido' : ''}" style="cursor:default;" title="Entrega gerada automaticamente pelo sistema">
                    <div class="entrega-check"><i class="fas fa-check"></i></div>
                    <div class="entrega-info">
                        <h4>${info.label} (Entrega 0${index + 1})</h4>
                        <p>${info.desc}</p>
                        ${isConcluida && entrega.mrr_contribution > 0
                    ? `<span style="font-size:0.75rem;color:#28a745;font-weight:600;">+ R$ ${parseFloat(entrega.mrr_contribution).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>`
                    : ''}
                    </div>
                    <span class="entrega-status-badge ${isConcluida ? 'badge-ok' : 'badge-pending'}">
                        <i class="fas ${isConcluida ? 'fa-lock-open' : 'fa-lock'}"></i>
                        ${isConcluida ? 'Concluída' : 'Pendente'}
                    </span>
                </div>`;
        }).join('');

        // Calcular MRR total
        const totalMrr = entregas.filter(e => e.status === 'completed')
            .reduce((sum, e) => sum + parseFloat(e.mrr_contribution || 0), 0);
        updateMRRDisplay(totalMrr);

    } catch (e) {
        console.error("Erro ao carregar entregas:", e);
        container.innerHTML = '<p style="color:#D61616;padding:2rem;text-align:center;"><i class="fas fa-exclamation-circle"></i> Erro ao carregar entregas mensais. Por favor, tente novamente.</p>';
    }
}

function updateMRRDisplay(totalMrr) {
    const display = document.getElementById('mrr-impact-display');
    if (display) {
        display.innerText = `R$ ${totalMrr.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
    }
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
                        <button class="btn-add-task" style="margin-top:1rem;background:var(--accent-red);" onclick="openGTModal('modal-novo-plano')">
                            <i class="fas fa-plus"></i> Lançar Plano de Mídia
                        </button>
                    </td>
                </tr>`;
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
    } catch (e) { console.error("Erro ao carregar plano de mídia:", e); }
}

// ─── OTIMIZAÇÕES ─────────────────────────────────────────────────────────────

async function loadOtimizacoes(pipefyId) {
    const listEl = document.getElementById('otimizacao-list');
    const emptyEl = document.getElementById('otimizacao-empty-state');
    if (!listEl) return;

    try {
        const res = await fetch(`/api/operacao/otimizacoes/${pipefyId}`);
        const data = await res.json();

        if (!data || data.length === 0) {
            listEl.innerHTML = '';
            if (emptyEl) emptyEl.style.display = 'block';
            return;
        }

        if (emptyEl) emptyEl.style.display = 'none';
        listEl.innerHTML = '';

        data.forEach(o => {
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
                </div>`;
            listEl.appendChild(card);
        });
    } catch (e) { console.error("Erro ao carregar otimizações:", e); }
}

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
            loadEntregas(currentProject.pipefy_id, currentMonth, currentYear);
        }
    } catch (e) { console.error(e); }
}

// ─── LINKS ÚTEIS ─────────────────────────────────────────────────────────────

async function loadLinks(pipefyId) {
    const grid = document.getElementById('links-grid');
    if (!grid) return;

    try {
        const res = await fetch(`/api/operacao/links/${pipefyId}`);
        const data = await res.json();

        if (!data || data.length === 0) {
            grid.innerHTML = '<p style="color:var(--text-muted);padding:2rem;">Nenhum link cadastrado ainda.</p>';
            return;
        }

        grid.innerHTML = data.map(lk => `
            <div class="access-link-card" style="position:relative; display: flex; flex-direction: column; height: 100%;">
                <button onclick="deleteLink(${lk.id})" title="Remover link"
                    style="position:absolute;top:10px;right:10px;background:none;border:none;color:#888;cursor:pointer;font-size:0.9rem;">
                    <i class="fas fa-trash-alt"></i>
                </button>
                <a href="${lk.url}" target="_blank" rel="noopener" style="text-decoration:none;display:block;flex: 1;">
                    <div class="op-icon-box" style="margin-bottom:10px;"><i class="fas ${lk.icone || 'fa-link'}"></i></div>
                    <div style="font-weight:600;font-size:0.9rem;color:var(--text-main); margin-bottom: 4px;">${lk.titulo}</div>
                    ${lk.descricao ? `<div style="font-size:0.8rem;color:var(--text-muted);margin-bottom:8px;line-height:1.4;">${lk.descricao}</div>` : ''}
                    <div style="font-size:0.75rem;color:var(--accent-red);word-break:break-all;opacity:0.8;">${lk.url}</div>
                </a>
            </div>`).join('');
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
    if (!confirm('Remover este link?')) return;
    try {
        await fetch(`/api/operacao/links/${linkId}`, { method: 'DELETE' });
        loadLinks(currentProject.pipefy_id);
    } catch (e) { console.error(e); }
}

// ─── CHECKIN ─────────────────────────────────────────────────────────────────

async function loadCheckins(pipefyId) {
    try {
        const res = await fetch(`/api/operacao/checkins/${pipefyId}`);
        const data = await res.json();
        const list = document.getElementById('checkin-list');
        if (!list) return;

        list.innerHTML = '';
        if (data.length === 0) {
            list.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:2rem;">Nenhum checkin realizado ainda.</p>';
            return;
        }

        data.forEach(c => {
            const item = document.createElement('div');
            item.className = 'op-card-premium';
            item.style.cssText = `padding:1.2rem;margin-bottom:12px;border-left:4px solid ${c.compareceu ? '#28a745' : '#ffc107'};`;
            const campanhasIcon = c.campanhas_ativas ? '<i class="fas fa-bolt" style="color:#28a745;"></i>' : '<i class="fas fa-exclamation-triangle" style="color:#D61616;"></i>';
            const gapIcon = c.gap_comunicacao ? '<i class="fas fa-comment-slash" style="color:#D61616;"></i>' : '<i class="fas fa-comments" style="color:#28a745;"></i>';
            const reclamacaoIcon = c.cliente_reclamou ? '<i class="fas fa-thumbs-down" style="color:#D61616;"></i>' : '<i class="fas fa-thumbs-up" style="color:#28a745;"></i>';
            item.innerHTML = `
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div style="flex:1;">
                        <div style="display:flex;align-items:center;gap:10px;margin-bottom:5px;">
                            <strong style="color:#D61616;font-size:0.9rem;">Semana ${c.semana.split('-W')[1]}</strong>
                            <span style="font-size:0.75rem;color:#888;">${c.data}</span>
                        </div>
                        <p style="font-size:0.8rem;color:var(--text-muted);margin:5px 0 0;line-height:1.4;">
                            ${c.obs || '<em>Sem observações registradas.</em>'}
                        </p>
                    </div>
                    <div style="display:flex;gap:12px;margin-left:15px;background:rgba(255,255,255,0.03);padding:8px 12px;border-radius:8px;">
                        <span>${c.compareceu ? '<i class="fas fa-user-check" style="color:#28a745;"></i>' : '<i class="fas fa-user-times" style="color:#ffc107;"></i>'}</span>
                        ${campanhasIcon}${gapIcon}${reclamacaoIcon}
                    </div>
                </div>`;
            list.appendChild(item);
        });

        // Status da semana atual
        const now = new Date();
        const week = Math.ceil(((now - new Date(now.getFullYear(), 0, 1)) / 86400000 + 1) / 7);
        const ref = `${currentYear}-W${String(week).padStart(2, '0')}`;
        const badge = document.getElementById('checkin-status-badge');
        if (badge) {
            const feito = data.some(c => c.semana === ref);
            badge.innerHTML = feito ? 'Realizado <i class="fas fa-check-circle"></i>' : 'Pendente <i class="fas fa-clock"></i>';
            badge.style.color = feito ? '#28a745' : '#ffc107';
        }
    } catch (e) { console.error("Erro ao carregar checkins:", e); }
}

async function saveCheckin() {
    const compareceu = document.getElementById('checkin-compareceu').value === 'true';
    const campanhasAtivas = document.getElementById('checkin-campanhas-ativas').value === 'true';
    const gapComunicacao = document.getElementById('checkin-gap-comunicacao').value === 'true';
    const clienteReclamou = document.getElementById('checkin-cliente-reclamou').value === 'true';
    const obs = document.getElementById('checkin-obs').value;

    const now = new Date();
    const week = Math.ceil(((now - new Date(now.getFullYear(), 0, 1)) / 86400000 + 1) / 7);
    const semana_ano = `${currentYear}-W${String(week).padStart(2, '0')}`;

    const payload = {
        pipefy_id: currentProject.pipefy_id,
        semana_ano, compareceu,
        campanhas_ativas: campanhasAtivas,
        gap_comunicacao: gapComunicacao,
        cliente_reclamou: clienteReclamou,
        satisfeito: true, obs
    };

    try {
        const res = await fetch('/api/operacao/checkin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            showToast('Checkin registrado com sucesso!');
            closeGTModal('modal-novo-checkin');
            loadCheckins(currentProject.pipefy_id);
            loadEntregas(currentProject.pipefy_id, currentMonth, currentYear);
        }
    } catch (e) { console.error(e); }
}

// ─── WIZARD PLANO DE MÍDIA ────────────────────────────────────────────────────

let editorRows = [];

function backToPlanStep1() {
    document.getElementById('plan-step-2').classList.remove('active');
    document.getElementById('plan-step-1').classList.add('active');
}

function goToPlanStep2() {
    const m = document.getElementById('wizard-month').value;
    const y = document.getElementById('wizard-year').value;
    document.getElementById('display-wizard-date').innerText = `${m} ${y}`;
    document.getElementById('plan-step-1').classList.remove('active');
    document.getElementById('plan-step-2').classList.add('active');

    // Inicializa editorRows apenas se estiver vazio
    if (editorRows.length === 0) {
        addEditorRow();
    }
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
    const days = new Date(currentYear, currentMonth, 0).getDate();
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
    openGTModal('modal-novo-plano');
}

async function saveFinalPlan() {
    const mesesMap = { "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4, "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8, "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12 };
    const m = document.getElementById('wizard-month').value;
    const y = document.getElementById('wizard-year').value;
    const total = parseFloat(document.getElementById('wizard-total-budget')?.value || 0);
    const days = new Date(parseInt(y), mesesMap[m], 0).getDate();

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
        mes: mesesMap[m],
        ano: parseInt(y),
        dados_plano: { budget_total: total, canais }
    };

    try {
        const res = await fetch('/api/operacao/plano-midia', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            showToast('Plano de Mídia salvo! Entrega validada automaticamente.');
            closeGTModal('modal-novo-plano');
            loadPlanoMidia(currentProject.pipefy_id, mesesMap[m], parseInt(y));
            loadEntregas(currentProject.pipefy_id, currentMonth, currentYear);
        }
    } catch (e) { console.error(e); }
}

// ─── FILTRO DE BUSCA DE PROJETOS ──────────────────────────────────────────────

function filterProjects() {
    const searchValue = document.getElementById('opSearchInput').value.toLowerCase();
    document.querySelectorAll('.op-card-premium').forEach(card => {
        const name = (card.querySelector('h3')?.textContent || '').toLowerCase();
        const product = (card.querySelector('p')?.textContent || '').toLowerCase();
        const squad = (card.querySelector('.op-card-meta')?.textContent || '').toLowerCase();
        card.style.display = (name.includes(searchValue) || product.includes(searchValue) || squad.includes(searchValue)) ? 'block' : 'none';
    });
}

// ─── INICIALIZAÇÃO ────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    console.log('Operação JS V10.0 Ativo 🚀');
});
