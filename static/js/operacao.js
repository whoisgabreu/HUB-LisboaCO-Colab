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
    relatorio_account: { label: "Relatório Mensal do Account", desc: "Automático ao concluir tarefa do Quarter" },
    planner_monday: { label: "Planner Monday Semanal", desc: "Automático ao registrar ≥4 tarefas semanais" },
    forecasting: { label: "Atualização do Forecasting com Metas", desc: "Automático ao registrar tarefa do Quarter" },
    // Gestor de Tráfego
    plano_midia: { label: "Plano de Mídia", desc: "Automático ao salvar plano de mídia" },
    otimizacao: { label: "Documento de Otimização", desc: "Automático ao registrar otimização" },
    relatorio_gt: { label: "Relatório Mensal do Gestor de Tráfego", desc: "Automático ao concluir tarefa do Quarter" },
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
    const q = `Q${Math.floor((currentMonth - 1) / 3) + 1}`;
    loadTarefas(pipefyId, 'quarter', 'quarter-task-list', `${currentYear}-${q}`);
    loadPlanoMidia(pipefyId, currentMonth, currentYear);
    loadEntregas(pipefyId, currentMonth, currentYear);
}

// ─── TAREFAS ─────────────────────────────────────────────────────────────────

async function loadTarefas(pipefyId, tipo, listId, referencia = "") {
    const url = `/api/operacao/tarefas/${pipefyId}?tipo=${tipo}${referencia ? '&referencia=' + referencia : ''}`;
    try {
        const res = await fetch(url);
        const tarefas = await res.json();
        const list = document.getElementById(listId);
        list.innerHTML = '';
        if (tarefas.length === 0) {
            list.innerHTML = '<p style="color:var(--text-muted);padding:1rem;">Nenhuma registro encontrado.</p>';
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

    const payload = {
        pipefy_id: currentProject.pipefy_id,
        tipo, descricao: descInput.value, referencia, ano: currentYear
    };

    try {
        const res = await fetch('/api/operacao/tarefas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            showToast('Tarefa salva!');
            descInput.value = '';
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
