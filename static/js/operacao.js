/**
 * LÓGICA DE OPERAÇÃO - HUB LISBOA&CO V9.0
 * Integração com Banco de Dados via SQLAlchemy & Lógica de MRR.
 */

let currentProject = null;
let currentMonth = new Date().getMonth() + 1;
let currentYear = new Date().getFullYear();

// --- GERENCIAMENTO DE MODAIS ---

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `gt-toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
            <span>${message}</span>
        </div>
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.classList.add('active'), 10);
    setTimeout(() => {
        toast.classList.remove('active');
        setTimeout(() => toast.remove(), 500);
    }, 3000);
}

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

// --- NAVEGAÇÃO ENTRE TELAS ---

function openProjectDetails(project) {
    currentProject = project;
    document.getElementById('display-project-name').innerText = project.nome;
    document.getElementById('project-selection-view').style.display = 'none';
    document.getElementById('project-details-view').style.display = 'block';

    // Reset tabs to Dashboard (Tasks Semanais)
    switchOperacaoTab('dashboard');

    // Carregar dados reais do banco
    loadProjectData();
}

function backToProjects() {
    currentProject = null;
    document.getElementById('project-selection-view').style.display = 'block';
    document.getElementById('project-details-view').style.display = 'none';
}

function switchOperacaoTab(tabId) {
    const allSections = document.querySelectorAll('.op-content-section');
    const allButtons = document.querySelectorAll('.op-pill-btn');

    allSections.forEach(s => s.classList.remove('active'));
    allButtons.forEach(b => b.classList.remove('active'));

    const targetSection = document.getElementById(`section-${tabId}`);
    if (targetSection) targetSection.classList.add('active');

    // Encontrar o botão que chama esse tabId
    allButtons.forEach(btn => {
        if (btn.getAttribute('onclick').includes(`'${tabId}'`)) {
            btn.classList.add('active');
        }
    });
}

// --- CARREGAMENTO DE DADOS (API) ---

async function loadProjectData() {
    if (!currentProject) return;

    const pipefyId = currentProject.pipefy_id;

    // 1. Carregar Tarefas Semanais
    loadTarefas(pipefyId, 'semanal', 'main-task-list');

    // 2. Carregar Tasks do Quarter
    const currentQuarter = `Q${Math.floor((currentMonth - 1) / 3) + 1}`;
    loadTarefas(pipefyId, 'quarter', 'quarter-task-list', `${currentYear}-${currentQuarter}`);

    // 3. Carregar Entregas do Mês
    loadEntregas(pipefyId, currentMonth, currentYear);

    // 4. Carregar Plano de Mídia
    loadPlanoMidia(pipefyId, currentMonth, currentYear);
}

async function loadTarefas(pipefyId, tipo, listId, referencia = "") {
    const url = `/api/operacao/tarefas/${pipefyId}?tipo=${tipo}${referencia ? '&referencia=' + referencia : ''}`;
    try {
        const res = await fetch(url);
        const tarefas = await res.json();
        const list = document.getElementById(listId);
        list.innerHTML = '';

        tarefas.forEach(t => {
            const item = document.createElement('div');
            item.className = `task-item ${t.concluida ? 'completed' : ''}`;
            item.innerHTML = `
                <div class="task-checkbox" onclick="toggleTask(${t.id}, this)"><i class="fas fa-check"></i></div>
                <div class="task-text">${t.descricao}</div>
                <button class="btn-delete-task" style="opacity: 0.3; pointer-events: none;"><i class="fas fa-lock"></i></button>
            `;
            list.appendChild(item);
        });
    } catch (e) { console.error("Erro ao carregar tasks:", e); }
}

async function loadEntregas(pipefyId, mes, ano) {
    try {
        const res = await fetch(`/api/operacao/entregas/${pipefyId}/${mes}/${ano}`);
        const data = await res.json();

        for (let i = 1; i <= 4; i++) {
            const card = document.getElementById(`entrega-${i}`);
            if (card) {
                if (data[`entrega_${i}`]) card.classList.add('concluido');
                else card.classList.remove('concluido');
            }
        }

        updateMRRDisplay(data.percentual);
    } catch (e) { console.error("Erro ao carregar entregas:", e); }
}

async function loadPlanoMidia(pipefyId, mes, ano) {
    const meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
    const displayDate = document.getElementById('display-main-plan-date');
    if (displayDate) displayDate.innerText = `[${meses[mes - 1]} ${ano}]`;

    const body = document.getElementById('plano-midia-body');
    if (!body) return;

    try {
        const res = await fetch(`/api/operacao/plano-midia/${pipefyId}/${mes}/${ano}`);
        const data = await res.json();

        if (!data || !data.dados_plano || !data.dados_plano.canais || data.dados_plano.canais.length === 0) {
            body.innerHTML = `
                <tr>
                    <td colspan="5" style="padding: 3rem; color: var(--text-muted); text-align: center;">
                        <i class="fas fa-file-invoice-dollar" style="font-size: 2rem; margin-bottom: 1rem; display: block; opacity: 0.3;"></i>
                        Nenhum plano de mídia lançado para este mês.<br>
                        <button class="btn-add-task" style="margin-top: 1rem; background: var(--accent-red);" onclick="openGTModal('modal-novo-plano')">
                            <i class="fas fa-plus"></i> Lançar Plano de Mídia
                        </button>
                    </td>
                </tr>
            `;
            return;
        }

        // Renderizar canais se existirem
        body.innerHTML = '';
        let totalBudget = 0;
        let totalDaily = 0;

        data.dados_plano.canais.forEach(c => {
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
            <td>TOTAL</td>
            <td></td>
            <td>100%</td>
            <td>R$ ${totalBudget.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</td>
            <td>R$ ${totalDaily.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</td>
        `;
        body.appendChild(footer);

    } catch (e) {
        console.error("Erro ao carregar plano de mídia:", e);
    }
}

// --- PERSISTÊNCIA ---

async function addNewTask(tipo = 'semanal') {
    const inputId = tipo === 'semanal' ? 'task-desc-input' : 'task-quarter-input';
    const modalId = tipo === 'semanal' ? 'modal-nova-tarefa' : 'modal-nova-tarefa-quarter';
    const descInput = document.getElementById(inputId);

    if (!descInput || !descInput.value.trim()) return;

    let referencia = "";
    if (tipo === 'semanal') {
        const now = new Date();
        const start = new Date(now.getFullYear(), 0, 1);
        const diff = now - start;
        const oneDay = 1000 * 60 * 60 * 24;
        const day = Math.floor(diff / oneDay);
        const week = Math.ceil(day / 7);
        referencia = `${currentYear}-W${String(week).padStart(2, '0')}`;
    } else {
        const quarter = Math.floor((currentMonth - 1) / 3) + 1;
        referencia = `${currentYear}-Q${quarter}`;
    }

    const payload = {
        pipefy_id: currentProject.pipefy_id,
        tipo: tipo,
        descricao: descInput.value,
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
            showToast('Tarefa salva!');
            descInput.value = '';
            closeGTModal(modalId);
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
    } catch (e) { console.error(e); }
}

async function toggleEntrega(n) {
    const card = document.getElementById(`entrega-${n}`);
    const isConcluido = !card.classList.contains('concluido');

    const payload = {
        pipefy_id: currentProject.pipefy_id,
        mes: currentMonth,
        ano: currentYear
    };
    payload[`entrega_${n}`] = isConcluido;

    try {
        const res = await fetch('/api/operacao/entregas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok) {
            card.classList.toggle('concluido');
            updateMRRDisplay(data.percentual);
            showToast(`Entrega ${n} atualizada! MRR do projeto: R$ ${data.valor_mrr_projeto.toLocaleString('pt-BR')}`);
        }
    } catch (e) { console.error(e); }
}

function updateMRRDisplay(percentual) {
    const fee = currentProject ? parseFloat(currentProject.fee || 0) : 0;
    const impact = fee * percentual;
    const display = document.getElementById('mrr-impact-display');
    if (display) {
        display.innerText = `R$ ${impact.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
    }
}

// --- CHECKIN (ACCOUNT) ---

async function loadCheckins(pipefyId) {
    try {
        const res = await fetch(`/api/operacao/checkins/${pipefyId}`);
        const data = await res.json();
        const list = document.getElementById('checkin-list');
        if (!list) return;

        list.innerHTML = '';
        if (data.length === 0) {
            list.innerHTML = '<p style="color: var(--text-muted); text-align: center; padding: 2rem;">Nenhum checkin realizado ainda.</p>';
            return;
        }

        // Calcular média CSAT
        let totalCsat = 0;
        let countCsat = 0;

        data.forEach(c => {
            const item = document.createElement('div');
            item.className = 'op-card-premium';
            item.style.padding = '1.2rem';
            item.style.marginBottom = '12px';
            item.style.borderLeft = `4px solid ${c.compareceu ? '#28a745' : '#ffc107'}`;

            const campanhasIcon = c.campanhas_ativas ? '<i class="fas fa-bolt" style="color: #28a745;" title="Campanhas Ativas"></i>' : '<i class="fas fa-exclamation-triangle" style="color: #D61616;" title="Campanhas Paradas"></i>';
            const gapIcon = c.gap_comunicacao ? '<i class="fas fa-comment-slash" style="color: #D61616;" title="Houve Gap de Com."></i>' : '<i class="fas fa-comments" style="color: #28a745;" title="Comunicação OK"></i>';
            const reclamacaoIcon = c.cliente_reclamou ? '<i class="fas fa-thumbs-down" style="color: #D61616;" title="Cliente Reclamou"></i>' : '<i class="fas fa-thumbs-up" style="color: #28a745;" title="Sem Reclamações"></i>';

            item.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div style="flex: 1;">
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 5px;">
                            <strong style="color: #D61616; font-size: 0.9rem;">Semana ${c.semana.split('-W')[1]}</strong>
                            <span style="font-size: 0.75rem; color: #888;">${c.data}</span>
                        </div>
                        <p style="font-size: 0.8rem; color: var(--text-muted); margin: 5px 0 0; line-height: 1.4;">
                            ${c.obs || '<em>Sem observações registradas.</em>'}
                        </p>
                    </div>
                    <div style="display: flex; gap: 12px; margin-left: 15px; background: rgba(255,255,255,0.03); padding: 8px 12px; border-radius: 8px;">
                        <span title="Stakeholder Presente">${c.compareceu ? '<i class="fas fa-user-check" style="color: #28a745;"></i>' : '<i class="fas fa-user-times" style="color: #ffc107;"></i>'}</span>
                        ${campanhasIcon}
                        ${gapIcon}
                        ${reclamacaoIcon}
                    </div>
                </div>
            `;
            list.appendChild(item);
        });

        if (countCsat > 0) {
            document.getElementById('checkin-avg-csat').innerText = (totalCsat / countCsat).toFixed(1);
        }

        // Checar se houve checkin na semana atual
        const now = new Date();
        const start = new Date(now.getFullYear(), 0, 1);
        const diff = now - start;
        const oneDay = 1000 * 60 * 60 * 24;
        const day = Math.floor(diff / oneDay);
        const week = Math.ceil(day / 7);
        const currentWeekRef = `${currentYear}-W${String(week).padStart(2, '0')}`;

        const checkinEssaSemana = data.some(c => c.semana === currentWeekRef);
        const badge = document.getElementById('checkin-status-badge');
        if (checkinEssaSemana) {
            badge.innerHTML = 'Realizado <i class="fas fa-check-circle"></i>';
            badge.style.color = '#28a745';
        } else {
            badge.innerHTML = 'Pendente <i class="fas fa-clock"></i>';
            badge.style.color = '#ffc107';
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
    const start = new Date(now.getFullYear(), 0, 1);
    const diff = now - start;
    const oneDay = 1000 * 60 * 60 * 24;
    const day = Math.floor(diff / oneDay);
    const week = Math.ceil(day / 7);
    const semana_ano = `${currentYear}-W${String(week).padStart(2, '0')}`;

    const payload = {
        pipefy_id: currentProject.pipefy_id,
        semana_ano: semana_ano,
        compareceu: compareceu,
        campanhas_ativas: campanhasAtivas,
        gap_comunicacao: gapComunicacao,
        cliente_reclamou: clienteReclamou,
        satisfeito: true, // Padronizado para histórico
        obs: obs
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
        }
    } catch (e) { console.error(e); }
}

// --- OTIMIZAÇÃO (TRIGGER ENTREGA 2) ---

async function saveOtimizacao() {
    const type = document.getElementById('opt-type').value;
    const channel = document.getElementById('opt-channel').value;
    const date = document.getElementById('opt-date').value;
    const details = document.getElementById('opt-details').value;

    if (!date) {
        showToast('Por favor, selecione a data.', 'error');
        return;
    }

    const payload = {
        pipefy_id: currentProject.pipefy_id,
        tipo: type,
        canal: channel,
        data: date,
        detalhes: details
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
            loadProjectData(); // Recarrega tudo (inclusive entregas marcadas automaticamente)
        }
    } catch (e) { console.error(e); }
}

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
    console.log('Operação JS Ativo 🚀');
});

// --- FILTRO DE BUSCA DE PROJETOS ---
function filterProjects() {
    const searchValue = document.getElementById('opSearchInput').value.toLowerCase();
    const cards = document.querySelectorAll('.op-card-premium');

    cards.forEach(card => {
        const projectName = (card.querySelector('h3')?.textContent || '').toLowerCase();
        const product = (card.querySelector('p')?.textContent || '').toLowerCase();
        const squad = (card.querySelector('.op-card-meta')?.textContent || '').toLowerCase();

        const match = projectName.includes(searchValue) ||
            product.includes(searchValue) ||
            squad.includes(searchValue);

        card.style.display = match ? 'block' : 'none';
    });
}

// Adicionar listener para carregar checkins ao abrir o projeto ou trocar tab
const originalSwitchTab = switchOperacaoTab;
switchOperacaoTab = function (tabId) {
    originalSwitchTab(tabId);
    if (tabId === 'checkin' && currentProject) {
        loadCheckins(currentProject.pipefy_id);
    }
};

// Implementar funções placeholder para evitar erros (Wizard do Plano de Mídia)
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
}

async function saveFinalPlan() {
    // Coleta dados simplificados para teste da automação
    const m = document.getElementById('wizard-month').value;
    const y = document.getElementById('wizard-year').value;

    // Mapeamento de mês nome para número
    const mesesMap = { "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4, "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8, "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12 };

    const payload = {
        pipefy_id: currentProject.pipefy_id,
        mes: mesesMap[m],
        ano: parseInt(y),
        dados_plano: { budget_total: document.getElementById('wizard-total-budget')?.value || 0 }
    };

    try {
        const res = await fetch('/api/operacao/plano-midia', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            showToast('Plano de Mídia salvo! Entrega 1 validada.');
            closeGTModal('modal-novo-plano');
            loadProjectData();
        }
    } catch (e) { console.error(e); }
}
