let currentSlide = 'ativos';
let currentClientData = null;
let currentProjectData = null;
let currentHistorico = null;
let isEditMode = false;

/* ==============================
UTILITÁRIOS DE MOEDA
================================ */

function formatCurrency(value, currency) {
    if (value === null || value === undefined || value === '') return '';

    const number = Number(value);
    if (isNaN(number)) return '';

    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: currency || 'BRL'
    }).format(number); // centavos → reais
}

function parseCurrencyToCents(value) {
    if (!value) return 0;

    let clean = value.replace(/[^\d.,]/g, '');

    const lastComma = clean.lastIndexOf(',');
    const lastDot = clean.lastIndexOf('.');

    if (lastComma > lastDot) {
        clean = clean.replace(/\./g, '').replace(',', '.');
    } else {
        clean = clean.replace(/,/g, '');
    }

    const number = parseFloat(clean);
    return isNaN(number) ? 0 : Math.round(number * 100);
}

/* ==============================
TABS / FILTRO
================================ */

function switchTab(ev, tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    ev.currentTarget.classList.add('active');

    document.querySelectorAll('.slide-content').forEach(slide => slide.classList.remove('active'));
    document.getElementById(`slide-${tab}`).classList.add('active');

    currentSlide = tab;
    filterClients();
}

// function filterClients() {
//     const searchValue = document.getElementById('searchInput').value.toLowerCase();
//     const activeSlide = document.querySelector('.slide-content.active');
//     const cards = activeSlide.querySelectorAll('.project-card');

//     cards.forEach(card => {
//         const clientName = (card.getAttribute('data-cliente') || '').toLowerCase();
//         card.style.display = clientName.includes(searchValue) ? 'block' : 'none';
//     });
// }

function filterClients() {
    const searchValue = document
        .getElementById('searchInput')
        .value
        .toLowerCase();

    const activeSlide = document.querySelector('.slide-content.active');
    const cards = activeSlide.querySelectorAll('.project-card');

    cards.forEach(card => {
        const clientName = (card.getAttribute('data-cliente') || '').toLowerCase();
        const squadName  = (card.getAttribute('data-squad') || '').toLowerCase();

        const match =
            clientName.includes(searchValue) ||
            squadName.includes(searchValue);

        card.style.display = match ? 'block' : 'none';
    });
}


/* ==============================
MODAL CLIENTE
================================ */

function openClientModal(cardElement) {
    const projetos = JSON.parse(cardElement.getAttribute('data-projetos'));
    const clienteNome = cardElement.querySelector('.project-title').textContent;
    const tipo = cardElement.getAttribute('data-tipo');

    const formatarData = (dataISO) => {
        if (!dataISO) return '—';
        const [ano, mes, dia] = dataISO.split('T')[0].split('-');
        return `${dia}/${mes}/${ano}`;
    };

    currentClientData = { nome: clienteNome, projetos, tipo };

    document.getElementById('clientModalTitle').textContent = `Projetos de: ${clienteNome}`;

    const projectsList = document.getElementById('projectsList');
    projectsList.innerHTML = '';

    // 🔹 TOTAL DO FEE (em centavos)
    let totalFee = 0;
    let moeda = null;

    projetos.forEach(projeto => {
        if (projeto.fee) {
            totalFee += Number(projeto.fee);
            moeda = projeto.moeda;
        }
    });

    const totalFeeFormatado = formatCurrency(totalFee, moeda);

    // 🔹 Exibe o total
    const totalItem = document.createElement('div');
    totalItem.className = 'project-total-fee';
    totalItem.innerHTML = `
        <strong>Fee Total:</strong> ${totalFeeFormatado || '—'}
    `;
    projectsList.appendChild(totalItem);

    // 🔹 Lista projetos
    projetos.forEach(projeto => {
        const feeFormatado = formatCurrency(projeto.fee, projeto.moeda);

        const projectItem = document.createElement('div');
        projectItem.className = 'project-list-item';
        projectItem.innerHTML = `
            <div class="project-item-info">
                <h4>${projeto.produto_contratado || 'Sem nome'}</h4>
                <p>
                    Squad: ${projeto.squad_atribuida || 'N/A'} |
                    Fee: ${feeFormatado || '—'} |
                    Data Inicio: ${formatarData(projeto.data_de_inicio)}
                </p>
            </div>
            <button class="btn-view">
                <i class="fa-solid fa-eye"></i> Ver Detalhes
            </button>
        `;

        projectItem.querySelector('.btn-view').addEventListener('click', (e) => {
            e.stopPropagation();
            openProjectModal(projeto, tipo);
        });

        projectsList.appendChild(projectItem);
    });

    document.getElementById('clientModal').classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeClientModal() {
    document.getElementById('clientModal').classList.remove('active');
    document.body.style.overflow = 'auto';
    currentClientData = null;
}

/* ==============================
MODAL PROJETO
================================ */

function openProjectModal(projectData, tipoProjeto) {
    currentProjectData = projectData;
    currentHistorico = projectData.extra?.historico || [];

    currentNotas = projectData.notas || {};
    renderNotes();

    isEditMode = false;
    setEditMode(false);

    document.getElementById('projectModalTitle').textContent =
        projectData.nome || 'Detalhes do Projeto';

    document.getElementById('modal_projeto_id').value = projectData.id || '';
    document.getElementById('modal_tipo_projeto').value = tipoProjeto || '';
    document.getElementById('modal_nome').value = projectData.nome || '';
    document.getElementById('modal_pipefy_id').value = projectData.pipefy_id || '';
    document.getElementById('modal_documento').value = projectData.documento || '';
    document.getElementById('modal_fee').value = formatCurrency(projectData.fee, projectData.moeda);
    document.getElementById('modal_moeda').value = projectData.moeda || 'BRL';
    document.getElementById('modal_squad').value = projectData.squad_atribuida || '';
    document.getElementById('modal_produto').value = projectData.produto_contratado || '';
    document.getElementById('modal_step').value = projectData.step || '';
    document.getElementById('modal_informacoes').value = projectData.informacoes_gerais || '';
    document.getElementById('modal_cohort').value = projectData.cohort || '';
    document.getElementById('modal_meta_account').value = projectData.meta_account_id || '';
    document.getElementById('modal_google_account').value = projectData.google_account_id || '';
    document.getElementById('modal_orcamento_midia_meta').value = projectData.orcamento_midia_meta || '';
    document.getElementById('modal_orcamento_midia_google').value = projectData.orcamento_midia_google || '';
    document.getElementById('modal_fase_pipefy').value = projectData.fase_do_pipefy || '';
    document.getElementById('modal_webhook_url').value = projectData.url_webhook_gchat || '';
    document.getElementById('modal_ekyte_workspace').value = projectData.ekyte_workspace || '';

    let pipefyButton = document.getElementById("pipefyButton");

    pipefyButton.onclick = (e) => {
        if (e.button === 0) {
            window.open(
                `https://app.pipefy.com/open-cards/${projectData.pipefy_id}`,
                '_blank',
                'noopener,noreferrer'
            );
        }
    };

    // if (projectData.data_de_inicio) {
    //     document.getElementById('modal_data_inicio').value =
    //         String(projectData.data_de_inicio).split('T')[0];
    // } else {
    //     document.getElementById('modal_data_inicio').value = '';
    // }

    // if (projectData.data_fim) {
    //     document.getElementById('modal_data_fim').value =
    //         String(projectData.data_fim).split('T')[0];
    // } else {
    //     document.getElementById('modal_data_fim').value = '';
    // }

    const dataInicio = projectData.data_de_inicio;

    if (dataInicio && !String(dataInicio).includes('2900')) {
        document.getElementById('modal_data_inicio').value =
            String(dataInicio).split('T')[0];
    } else {
        document.getElementById('modal_data_inicio').value = '';
    }

    const dataFim = projectData.data_fim;

    if (dataFim && !String(dataFim).includes('2900')) {
        document.getElementById('modal_data_fim').value =
            String(dataFim).split('T')[0];
    } else {
        document.getElementById('modal_data_fim').value = '';
    }

    // Mostrar/esconder botão de histórico
    const historyBtn = document.getElementById('historyBtn');
    if (historyBtn) {
        if (currentHistorico && currentHistorico.length > 0) {
            historyBtn.style.display = 'flex';
        } else {
            historyBtn.style.display = 'none';
        }
    }

    document.getElementById('clientModal').classList.remove('active');
    document.getElementById('projectModal').classList.add('active');
}

function closeProjectModal() {
    document.getElementById('projectModal').classList.remove('active');
    document.body.style.overflow = 'auto';
    currentProjectData = null;
    currentHistorico = null;
    isEditMode = false;
    setEditMode(false);
}

function backToClientModal() {
    document.getElementById('projectModal').classList.remove('active');
    if (currentClientData) {
        document.getElementById('clientModal').classList.add('active');
    }
    isEditMode = false;
    setEditMode(false);
}

function toggleEditMode() {
    isEditMode = !isEditMode;
    setEditMode(isEditMode);
    renderNotes(); // 🔥 ESSENCIAL
}

function setEditMode(enable) {
    const inputs = document.querySelectorAll('#projectForm input, #projectForm select, #projectForm textarea');
    inputs.forEach(input => {
        if (input.id !== 'modal_projeto_id' && input.id !== 'modal_tipo_projeto') {
            input.disabled = !enable;
        }
    });

    const editBtn = document.getElementById('editBtn');
    const saveBtn = document.getElementById('saveBtn');

    if (!editBtn || !saveBtn) return;

    saveBtn.style.display = enable ? 'inline-flex' : 'none';
    editBtn.innerHTML = enable
        ? '<i class="fa-solid fa-xmark"></i> Cancelar'
        : '<i class="fa-solid fa-pen-to-square"></i> Editar';
}

/* ==============================
MODAL HISTÓRICO
================================ */

function openHistoryModal() {
    const historyContent = document.getElementById('historyContent');
    
    if (!currentHistorico || currentHistorico.length === 0) {
        historyContent.innerHTML = `
            <div class="empty-history">
                <i class="fa-solid fa-clock-rotate-left"></i>
                <h3>Sem histórico</h3>
                <p>Nenhuma alteração foi registrada para este projeto</p>
            </div>
        `;
    } else {
        // Ordenar por data (mais recente primeiro)
        const sortedHistory = [...currentHistorico].sort((a, b) => 
            new Date(b.data) - new Date(a.data)
        );
        
        historyContent.innerHTML = sortedHistory.map(item => {
            const date = new Date(item.data);
            const formattedDate = date.toLocaleString('pt-BR', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
            
            const changes = Object.entries(item.alteracoes || {}).map(([field, values]) => {
                // Formatar o nome do campo
                const fieldName = field.replace(/_/g, ' ');
                
                return `
                    <div class="change-item">
                        <div class="change-field">${fieldName}</div>
                        <div class="change-values">
                            <div class="change-before">
                                <!-- <strong>Antes:</strong><br> -->
                                ${values.antes || '<em>vazio</em>'}
                            </div>
                            <div class="change-arrow">
                                <i class="fa-solid fa-arrow-right"></i>
                            </div>
                            <div class="change-after">
                                <!-- <strong>Depois:</strong><br> -->
                                ${values.depois || '<em>vazio</em>'}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
            
            return `
                <div class="history-card">
                    <div class="history-header">
                        <div class="history-date">
                            <i class="fa-solid fa-calendar-days"></i>
                            ${formattedDate}
                        </div>
                        <div class="history-user">
                            <i class="fa-solid fa-user"></i>
                            ${item.usuario}
                        </div>
                    </div>
                    <div class="history-changes">
                        ${changes}
                    </div>
                </div>
            `;
        }).join('');
    }
    
    document.getElementById('historyModal').classList.add('active');
}

function closeHistoryModal() {
    document.getElementById('historyModal').classList.remove('active');
}

/* ==============================
RECARREGAR DADOS
================================ */
async function recarregarDados(email) {
    try {
        const [ativosRes, onetimeRes, inativosRes] = await Promise.all([
            fetch(`https://n8n.v4lisboatech.com.br/webhook/list_projetos?email=${email}`, {
                headers: { 'x-api-key': '4815162342' }
            }),
            fetch(`https://n8n.v4lisboatech.com.br/webhook/list_projetos_onetime?email=${email}`, {
                headers: { 'x-api-key': '4815162342' }
            }),
            fetch(`https://n8n.v4lisboatech.com.br/webhook/list_projetos_inativos?email=${email}`, {
                headers: { 'x-api-key': '4815162342' }
            })
        ]);

        const dados = {
            ativos: await ativosRes.json(),
            onetime: await onetimeRes.json(),
            inativos: await inativosRes.json()
        };

        atualizarCards(dados);
    } catch (error) {
        console.error('Erro ao recarregar:', error);
    }
}

/* ==============================
RECRIAR CARDS
============================== */
function atualizarCards(dados) {
    const tiposMap = {
        'ativos': 'ativo',
        'onetime': 'onetime', 
        'inativos': 'inativo'
    };

    ['ativos', 'onetime', 'inativos'].forEach(tipoSlide => {
        const slide = document.getElementById(`slide-${tipoSlide}`);
        if (!slide) return;

        const grid = slide.querySelector('.projects-grid');
        if (!grid) return;

        const projetosPorCliente = {};
        const tipoProjeto = tiposMap[tipoSlide];
        
        // Agrupar projetos por cliente
        if (dados[tipoSlide] && Array.isArray(dados[tipoSlide])) {
            dados[tipoSlide].forEach(item => {
                const projeto = item.projetos; // Acessar o objeto interno
                const nomeCliente = projeto.nome || 'Sem nome'; // nome = cliente
                
                if (!projetosPorCliente[nomeCliente]) {
                    projetosPorCliente[nomeCliente] = [];
                }
                projetosPorCliente[nomeCliente].push(projeto);
            });
        }

        // Verificar se há projetos
        if (Object.keys(projetosPorCliente).length === 0) {
            grid.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-inbox"></i>
                    <h3>Nenhum cliente ${tipoSlide === 'onetime' ? 'one-time' : tipoSlide}</h3>
                </div>
            `;
            return;
        }

        // Criar um card para cada CLIENTE (com todos seus projetos)
        grid.innerHTML = Object.entries(projetosPorCliente).map(([cliente, projetos]) => {
            const primeiroProj = projetos[0];
            const dataInicio = primeiroProj.data_de_inicio 
                ? new Date(primeiroProj.data_de_inicio).toLocaleDateString('pt-BR')
                : 'N/A';
            
            return `
                <div class="project-card" 
                    data-cliente="${cliente.toLowerCase()}"
                    data-projetos='${JSON.stringify(projetos)}'
                    data-tipo="${tipoProjeto}"
                    data-squad="${primeiroProj.squad_atribuida}"
                    onclick="openClientModal(this)">
                    <div class="project-header">
                        <div class="project-icon ${tipoSlide === 'inativos' ? 'inactive' : ''}">
                            <i class="fa-solid fa-building"></i>
                        </div>
                        <span class="project-status status-${tipoProjeto}">${projetos.length} projeto(s)</span>
                    </div>
                    <h3 class="project-title">${cliente}</h3>
                    <p class="project-description">
                        Squad: ${primeiroProj.squad_atribuida || 'N/A'}
                    </p>
                    <div class="project-meta">
                        <span>
                            <i class="fa-solid fa-calendar"></i>
                            ${dataInicio}
                        </span>
                        <span>
                            <i class="fa-solid fa-layer-group"></i>
                            ${projetos.length} projeto${projetos.length > 1 ? 's' : ''}
                        </span>
                    </div>
                </div>
            `;
        }).join('');
    });

    const searchInput = document.getElementById('searchInput');
    if (searchInput && searchInput.value) {
        filterClients();
    }
}

/* ==============================
UPDATE PROJETO (ATUALIZADO)
================================ */
async function updateProject(event) {
    event.preventDefault();

    const formData = new FormData(event.target);
    const data = Object.fromEntries(formData);

    data.fee = parseCurrencyToCents(data.fee);
    data.usuario = window.APP_CONFIG.userEmail;
    data.userToken = window.APP_CONFIG.userToken
    // Coletar notas do formulário
    data.notas = collectNotesFromForm();
    
    try {
        const response = await fetch('https://n8n.v4lisboatech.com.br/webhook/update_projeto', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': data.userToken
            },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            // alert(`Os dados do projeto ${data.produto_contratado} foram atualizados.`)
            // backToClientModal();
            await recarregarDados(data.usuario);
            closeProjectModal();
            // location.reload();
        }
    } catch (error) {
        console.error('Erro:', error);
    }
}

/* ==============================
MENU USUÁRIO / SENHA
================================ */

function toggleUserMenu(event) {
    event.stopPropagation();
    document.getElementById('userDropdown').classList.toggle('active');
}

document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('userDropdown');
    const menuBtn = document.getElementById('userMenuBtn');

    if (dropdown.classList.contains('active') &&
        !dropdown.contains(event.target) &&
        !menuBtn.contains(event.target)) {
        dropdown.classList.remove('active');
    }
});

function openManageUsers() {
    window.location.href = '/manage_users';
}

function openMyProfile() {
    alert('Meu Perfil - Em desenvolvimento');
}

function changePassword() {
    document.getElementById('passwordModal').classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closePasswordModal() {
    document.getElementById('passwordModal').classList.remove('active');
    document.body.style.overflow = 'auto';
    document.getElementById('passwordForm').reset();
}

async function updatePassword(event) {
    event.preventDefault();


    const novaSenha = document.getElementById('nova_senha').value;
    const confirmarSenha = document.getElementById('confirmar_senha').value;

    if (novaSenha !== confirmarSenha) {
        alert('As senhas não coincidem!');
        return;
    }

    if (novaSenha.length < 6) {
        alert('A senha deve ter no mínimo 6 caracteres!');
        return;
    }

    try {
        const response = await fetch('https://n8n.v4lisboatech.com.br/webhook/update_user_info', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': window.APP_CONFIG.userToken
            },
            body: JSON.stringify({
                email: window.APP_CONFIG.userEmail,
                senha: novaSenha,
                switch: 'user_password'
            })
        });

        if (response.ok) {
            alert('Senha atualizada com sucesso!');
            closePasswordModal();
        }
    } catch (error) {
        console.error('Erro:', error);
    }
}

let currentNotas = {};

/* ==============================
MODAL ADICIONAR NOTA
================================ */

function openAddNoteModal() {
    if (!isEditMode) {
        alert('Ative o modo de edição primeiro para adicionar notas');
        return;
    }
    document.getElementById('addNoteModal').classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeAddNoteModal() {
    document.getElementById('addNoteModal').classList.remove('active');
    document.getElementById('addNoteForm').reset();
}

function addNote(event) {
    event.preventDefault();
    
    const noteName = document.getElementById('note_name').value.trim();
    
    if (!noteName) {
        alert('Digite um nome para a nota');
        return;
    }
    
    // Verificar se já existe uma nota com esse nome
    if (currentNotas.hasOwnProperty(noteName)) {
        alert('Já existe uma nota com este nome');
        return;
    }
    
    // Adicionar a nota
    currentNotas[noteName] = '';
    
    // Renderizar notas
    renderNotes();

    closeAddNoteModal();
}

function renderNotes() {
    const container = document.getElementById('notesContainer');
    
    if (Object.keys(currentNotas).length === 0) {
        container.innerHTML = `
            <div class="notes-empty">
                <i class="fa-solid fa-note-sticky"></i>
                <p>Nenhuma nota adicionada</p>
                <small>Clique no botão "+" no header para adicionar notas</small>
            </div>
        `;
        return;
    }
    
    container.innerHTML = Object.entries(currentNotas).map(([name, value]) => `
        <div class="note-item" data-note-name="${name}">
            <div class="note-item-header">
                <div class="note-item-title">
                    <i class="fa-solid fa-note-sticky"></i> ${name}
                </div>
                <div class="note-item-actions">
                    <button type="button" class="btn-note-action" onclick="removeNote('${name}')" title="Remover nota" ${!isEditMode ? 'disabled' : ''}>
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>
            </div>
            <textarea 
                data-note-field="${name}"
                placeholder="Digite suas anotações aqui..."
                ${!isEditMode ? 'disabled' : ''}
            >${value || ''}</textarea>
        </div>
    `).join('');
}

function removeNote(noteName) {
    if (!confirm(`Deseja remover a nota "${noteName}"?`)) {
        return;
    }
    
    delete currentNotas[noteName];
    renderNotes();
}

function collectNotesFromForm() {
    const textareas = document.querySelectorAll('[data-note-field]');
    const notes = {};
    
    textareas.forEach(textarea => {
        const fieldName = textarea.getAttribute('data-note-field');
        notes[fieldName] = textarea.value || '';
    });
    
    return notes;
}


/* ==============================
EVENT LISTENERS GLOBAIS (ATUALIZADO)
================================ */

// window.addEventListener('click', function(event) {
//     const passwordModal = document.getElementById('passwordModal');
//     const historyModal = document.getElementById('historyModal');
//     const clientModal = document.getElementById('clientModal');
//     const projectModal = document.getElementById('projectModal');
//     const addNoteModal = document.getElementById('addNoteModal');
    
//     if (event.target === passwordModal) {
//         closePasswordModal();
//     } else if (event.target === historyModal) {
//         closeHistoryModal();
//     } else if (event.target === clientModal) {
//         closeClientModal();
//     } else if (event.target === projectModal) {
//         closeProjectModal();
//     } else if (event.target === addNoteModal) {
//         closeAddNoteModal();
//     }
// });