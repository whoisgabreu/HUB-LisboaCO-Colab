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
            if (data[`entrega_${i}`]) card.classList.add('concluido');
            else card.classList.remove('concluido');
        }

        updateMRRDisplay(data.percentual);
    } catch (e) { console.error("Erro ao carregar entregas:", e); }
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

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
    console.log('Operação JS Ativo 🚀');
});
