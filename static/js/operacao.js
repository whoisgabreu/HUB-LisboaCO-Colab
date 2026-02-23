/**
 * LÓGICA DE OPERAÇÃO - HUB LISBOA&CO V8.0
 * Gerenciamento de tarefas, modais e NOVO FLUXO DE PLANO (WIZARD).
 */

// --- GERENCIAMENTO DE MODAIS ---

/**
 * Exibe uma notificação temporária
 */
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

    // Animar entrada
    setTimeout(() => toast.classList.add('active'), 10);

    // Remover após 3 segundos
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
        
        // Reset do Wizard se for o modal de plano
        if (modalId === 'modal-novo-plano') {
            resetPlanWizard();
        }
    }
}

function closeGTModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

window.addEventListener('click', (e) => {
    if (e.target.classList.contains('gt-modal')) {
        e.target.classList.remove('active');
        document.body.style.overflow = '';
    }
});

// --- GERENCIAMENTO DE TAREFAS ---

function addNewTask() {
    const descInput = document.getElementById('task-desc-input');
    const tagSelect = document.getElementById('task-tag-input');
    const taskList = document.getElementById('main-task-list');

    if (!descInput.value.trim()) {
        alert('Por favor, descreva a tarefa.');
        return;
    }

    const taskItem = document.createElement('div');
    taskItem.className = 'task-item';
    taskItem.innerHTML = `
        <div class="task-checkbox" onclick="toggleTask(this)"><i class="fas fa-check"></i></div>
        <div class="task-text">${descInput.value}</div>
        <span class="task-tag">${tagSelect.value}</span>
        <button class="btn-delete-task" onclick="deleteTask(this)"><i class="fas fa-trash-alt"></i></button>
    `;

    if (taskList.firstChild) {
        taskList.insertBefore(taskItem, taskList.firstChild);
    } else {
        taskList.appendChild(taskItem);
    }

    descInput.value = '';
    closeGTModal('modal-nova-tarefa');
}

function toggleTask(checkbox) {
    const taskItem = checkbox.closest('.task-item');
    taskItem.classList.toggle('completed');
}

function deleteTask(btn) {
    const taskItem = btn.closest('.task-item');
    taskItem.style.opacity = '0';
    taskItem.style.transform = 'translateX(20px)';
    setTimeout(() => {
        taskItem.remove();
    }, 300);
}

// --- NOVO FLUXO PLANO DE MÍDIA (WIZARD V8.0) ---

function editCurrentPlan() {
    const mainTitleDate = document.getElementById('display-main-plan-date');
    let currentMonth = "Fevereiro";
    let currentYear = "2026";
    
    if (mainTitleDate) {
        let match = mainTitleDate.innerText.match(/\[(.*?) (\d+)\]/);
        if (match) {
            currentMonth = match[1];
            currentYear = match[2];
        }
    }
    
    document.getElementById('wizard-month').value = currentMonth;
    document.getElementById('wizard-year').value = currentYear;
    
    const tbody = document.getElementById('plano-midia-body');
    const rows = Array.from(tbody.querySelectorAll('tr:not(.total-row)'));
    const totalRow = tbody.querySelector('.total-row');
    
    let totalBudgetVal = 0;
    if (totalRow && totalRow.cells.length >= 4) {
        const totalText = totalRow.cells[3].innerText; // "R$ 3.000,00"
        totalBudgetVal = parseFloat(totalText.replace(/[^\d\,]/g, '').replace(',', '.')) || 0;
    }
    document.getElementById('wizard-total-budget').value = totalBudgetVal;
    
    const editorBody = document.getElementById('wizard-editor-body');
    editorBody.innerHTML = '';
    
    rows.forEach(row => {
        if (row.cells.length < 5) return;
        const canal = row.cells[0].innerText;
        const campaign = row.cells[1].innerText;
        const percentText = row.cells[2].innerText;
        const percent = parseFloat(percentText.replace('%', '')) || 0;
        const budgetStr = row.cells[3].innerText;
        const dayStr = row.cells[4].innerText;
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>
                <select class="cell-input edit-canal">
                    <option value="Meta Ads" ${canal.includes("Meta Ads") ? "selected" : ""}>Meta Ads</option>
                    <option value="Google Ads" ${canal.includes("Google Ads") ? "selected" : ""}>Google Ads</option>
                    <option value="LinkedIn Ads" ${canal.includes("LinkedIn Ads") ? "selected" : ""}>LinkedIn Ads</option>
                    <option value="TikTok Ads" ${canal.includes("TikTok Ads") ? "selected" : ""}>TikTok Ads</option>
                    <option value="YouTube Ads" ${canal.includes("YouTube Ads") ? "selected" : ""}>YouTube Ads</option>
                </select>
            </td>
            <td><input type="text" class="cell-input edit-campaign" value="${campaign}"></td>
            <td><input type="number" class="cell-input edit-percent" value="${percent}" oninput="calculateEditorValues()"></td>
            <td><span class="edit-cash">${budgetStr}</span></td>
            <td><span class="edit-day">${dayStr}</span></td>
            <td><button class="btn-remove-row" onclick="removeEditorRow(this)"><i class="fas fa-trash"></i></button></td>
        `;
        editorBody.appendChild(tr);
    });
    
    if(editorBody.children.length === 0) {
       addEditorRow();
    }
    
    updateWizardTotals();
    
    document.getElementById('display-wizard-date').innerText = `${currentMonth} ${currentYear}`;
    document.getElementById('plan-step-1').classList.remove('active');
    document.getElementById('plan-step-2').classList.add('active');
    
    const modal = document.getElementById('modal-novo-plano');
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function resetPlanWizard() {
    // Volta para etapa 1
    document.getElementById('plan-step-1').classList.add('active');
    document.getElementById('plan-step-2').classList.remove('active');
    
    // Limpa campos
    document.getElementById('wizard-total-budget').value = "0";
    document.getElementById('wizard-editor-body').innerHTML = "";
    updateWizardTotals();
}

function goToPlanStep2() {
    const month = document.getElementById('wizard-month').value;
    const year = document.getElementById('wizard-year').value;
    
    document.getElementById('display-wizard-date').innerText = `${month} ${year}`;
    
    document.getElementById('plan-step-1').classList.remove('active');
    document.getElementById('plan-step-2').classList.add('active');
    
    // Adiciona uma linha inicial
    addEditorRow();
}

function addEditorRow() {
    const tbody = document.getElementById('wizard-editor-body');
    const row = document.createElement('tr');
    
    row.innerHTML = `
        <td>
            <select class="cell-input edit-canal">
                <option value="Meta Ads">Meta Ads</option>
                <option value="Google Ads">Google Ads</option>
                <option value="LinkedIn Ads">LinkedIn Ads</option>
                <option value="TikTok Ads">TikTok Ads</option>
                <option value="YouTube Ads">YouTube Ads</option>
            </select>
        </td>
        <td><input type="text" class="cell-input edit-campaign" placeholder="Nome da campanha"></td>
        <td><input type="number" class="cell-input edit-percent" value="0" oninput="calculateEditorValues()"></td>
        <td><span class="edit-cash">R$ 0,00</span></td>
        <td><span class="edit-day">R$ 0,00</span></td>
        <td><button class="btn-remove-row" onclick="removeEditorRow(this)"><i class="fas fa-trash"></i></button></td>
    `;
    
    tbody.appendChild(row);
    calculateEditorValues();
}

function removeEditorRow(btn) {
    btn.closest('tr').remove();
    calculateEditorValues();
}

function calculateEditorValues() {
    const totalBudget = parseFloat(document.getElementById('wizard-total-budget').value) || 0;
    const rows = document.querySelectorAll('#wizard-editor-body tr');
    
    let totalPercent = 0;
    let totalCash = 0;
    let totalDay = 0;

    rows.forEach(row => {
        const percent = parseFloat(row.querySelector('.edit-percent').value) || 0;
        const cash = (totalBudget * (percent / 100));
        const day = cash / 30;

        row.querySelector('.edit-cash').innerText = `R$ ${cash.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`;
        row.querySelector('.edit-day').innerText = `R$ ${day.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`;

        totalPercent += percent;
        totalCash += cash;
        totalDay += day;
    });

    updateWizardTotals(totalPercent, totalCash, totalDay);
}

function updateWizardTotals(p = 0, c = 0, d = 0) {
    document.getElementById('wizard-total-percent').innerText = `${p}%`;
    document.getElementById('wizard-total-cash').innerText = `R$ ${c.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`;
    document.getElementById('wizard-total-day').innerText = `R$ ${d.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`;
    
    // Alerta visual se passar de 100%
    const percentEl = document.getElementById('wizard-total-percent');
    if (p > 100) percentEl.style.color = '#D61616';
    else if (p === 100) percentEl.style.color = '#28a745';
    else percentEl.style.color = '#222';
}

function saveFinalPlan() {
    const rows = document.querySelectorAll('#wizard-editor-body tr');
    if (rows.length === 0) {
        alert('Adicione pelo menos uma campanha.');
        return;
    }

    const tbody = document.getElementById('plano-midia-body');
    const totalRow = tbody.querySelector('.total-row');
    
    // Limpar linhas atuais (exceto a total)
    const existingRows = tbody.querySelectorAll('tr:not(.total-row)');
    existingRows.forEach(r => r.remove());

    let finalTotalPercent = 0;
    let finalTotalCash = 0;
    let finalTotalDay = 0;

    rows.forEach(row => {
        const canal = row.querySelector('.edit-canal').value;
        const campaign = row.querySelector('.edit-campaign').value || "Campanha sem nome";
        const percent = parseFloat(row.querySelector('.edit-percent').value) || 0;
        const totalBudget = parseFloat(document.getElementById('wizard-total-budget').value) || 0;
        const cash = (totalBudget * (percent / 100));
        const day = cash / 30;

        const newRow = document.createElement('tr');
        newRow.innerHTML = `
            <td><strong>${canal}</strong></td>
            <td>${campaign}</td>
            <td>${percent}%</td>
            <td>R$ ${cash.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
            <td>R$ ${day.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
        `;
        tbody.insertBefore(newRow, totalRow);

        finalTotalPercent += percent;
        finalTotalCash += cash;
        finalTotalDay += day;
    });

    // Atualiza linha de TOTAL na dashboard
    totalRow.cells[2].innerText = `${finalTotalPercent}%`;
    totalRow.cells[3].innerText = `R$ ${finalTotalCash.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`;
    // Atualiza o título na tela principal com a data do plano
    const wizardMonth = document.getElementById('wizard-month').value;
    const wizardYear = document.getElementById('wizard-year').value;
    const mainTitleDate = document.getElementById('display-main-plan-date');
    if (mainTitleDate) {
        mainTitleDate.innerText = `[${wizardMonth} ${wizardYear}]`;
        mainTitleDate.style.color = '#D61616';
        mainTitleDate.style.fontWeight = '600';
    }

    closeGTModal('modal-novo-plano');
    showToast('Plano de Mídia salvo com sucesso! 🚀');
    updateEntregasChecklist();
}

// --- HISTÓRICO (V7.0 ACCORDION) ---

function toggleHistoryMonth(monthId) {
    const item = document.getElementById(monthId);
    if (!item) return;

    const allItems = document.querySelectorAll('.history-month-item');
    allItems.forEach(otherItem => {
        if (otherItem.id !== monthId) {
            otherItem.classList.remove('active');
        }
    });

    item.classList.toggle('active');
}

// --- ENTREGAS DO MÊS ---

function updateEntregasChecklist() {
    // Definir data da label usando as infos do plano mais recente que consta na home operation
    const mainTitleDate = document.getElementById('display-main-plan-date');
    const titleDateSpan = document.getElementById('display-entregas-date');
    
    // Atualiza a data com base no que está na interface
    if (mainTitleDate && titleDateSpan) {
        if (!mainTitleDate.innerText.includes('Nenhum')) {
           titleDateSpan.innerText = mainTitleDate.innerText;
        } else {
           titleDateSpan.innerText = "[Mês Atual]";
        }
    }

    // 1. Docs de Otimização (Auto) -> Ex: Simula contar as otimizações
    const optimCard = document.getElementById('entrega-optims');
    if (optimCard) {
        document.getElementById('optims-count').innerText = `${currentOptimizations}/4`;
        if (currentOptimizations >= 4) optimCard.classList.add('concluido');
        else optimCard.classList.remove('concluido');
    }

    // 2. Plano de Mídia Atualizado (Auto)
    const mediaCard = document.getElementById('entrega-media');
    if (mediaCard && mainTitleDate) {
        if (!mainTitleDate.innerText.includes('Nenhum')) {
            mediaCard.classList.add('concluido');
        } else {
            mediaCard.classList.remove('concluido');
        }
    }
}

function toggleManualEntrega(card) {
    card.classList.toggle('concluido');
}

function generateMonthlyReport() {
    showToast('Processando dados e compilando o relatório mensal...', 'success');
    setTimeout(() => {
        showToast('Relatório Mensal gerado com sucesso!', 'success');
        const reportCard = document.getElementById('entrega-report');
        if (reportCard) reportCard.classList.add('concluido');
    }, 2500);
}

let currentOptimizations = 0;

function saveOtimizacao() {
    const dataOtimizacao = document.getElementById('opt-date').value;
    const detalhes = document.getElementById('opt-details').value;
    const tipo = document.getElementById('opt-type').value;
    const canal = document.getElementById('opt-channel').value;
    
    if (!dataOtimizacao) {
        alert("Por favor, selecione a data da otimização.");
        return;
    }
    
    if (!detalhes) {
        alert("Por favor, preencha os detalhes.");
        return;
    }

    const [ano, mes, dia] = dataOtimizacao.split('-');
    
    // Validação da Data (Mês/Ano atuais)
    const dataSelecionada = new Date(ano, mes - 1, dia);
    const dataAtual = new Date();
    
    const mesSelecionado = dataSelecionada.getMonth();
    const anoSelecionado = dataSelecionada.getFullYear();
    const mesAtual = dataAtual.getMonth();
    const anoAtual = dataAtual.getFullYear();

    if (anoSelecionado > anoAtual || (anoSelecionado === anoAtual && mesSelecionado > mesAtual)) {
        alert("Não é possível registrar documentações de otimização em meses futuros.");
        return;
    }

    if (anoSelecionado < anoAtual || mesSelecionado < mesAtual) {
        alert("Você está tentando registrar um documento passado. Este registro irá diretamente para o Histórico de dados arquivados.");
        closeGTModal('modal-nova-otimizacao');
        showToast('Otimização enviada para o arquivo histórico.', 'success');
        document.getElementById('opt-date').value = '';
        document.getElementById('opt-details').value = '';
        return;
    }

    // Passou pela validação, então é um documento válido do MÊS VIGENTE.
    // Incrementa a contagem de otimizações da sessão atual
    currentOptimizations += 1;
    
    // Ocultar empty state e criar card
    const emptyState = document.getElementById('otimizacao-empty-state');
    if (emptyState) emptyState.style.display = 'none';

    const list = document.getElementById('otimizacao-list');
    
    // Formatar data de YYYY-MM-DD para DD/MM/YYYY
    // Formatar data de YYYY-MM-DD para DD/MM/YYYY
    const dataFormatada = `${dia}/${mes}/${ano}`;

    const card = document.createElement('div');
    card.className = 'op-card-premium';
    card.style.background = 'var(--card-bg)';
    card.style.border = '1px solid var(--border-color)';
    card.style.padding = '1.5rem';
    card.style.display = 'flex';
    card.style.flexDirection = 'column';
    card.style.gap = '10px';
    
    card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span class="badge-gt badge-estavel">${tipo}</span>
                <span style="color: var(--text-muted); font-size: 0.85rem; font-weight: 600;"><i class="fas fa-bullseye" style="margin-right: 5px;"></i> ${canal}</span>
            </div>
            <span style="font-size: 0.8rem; color: var(--text-muted);"><i class="far fa-calendar-alt" style="margin-right: 5px;"></i> ${dataFormatada}</span>
        </div>
        <p style="color: var(--text-main); font-size: 0.95rem; margin-top: 10px; margin-bottom: 0;">${detalhes}</p>
    `;
    
    if(list) {
        if(list.firstChild) {
            list.insertBefore(card, list.firstChild);
        } else {
            list.appendChild(card);
        }
    }
    
    // Atualiza a interface
    closeGTModal('modal-nova-otimizacao');
    showToast('Otimização registrada com sucesso!', 'success');
    
    // Limpa campos para a próxima
    document.getElementById('opt-date').value = '';
    document.getElementById('opt-details').value = '';
    
    // Atualiza os checks das Entregas do Mês 
    updateEntregasChecklist();
}

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
    console.log('Operação JS Ativo 🚀');
    updateEntregasChecklist();
});
