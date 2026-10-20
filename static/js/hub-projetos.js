let currentSlide = 'ativos';
let currentClientData = null;
let currentProjectData = null;
let currentHistorico = null;
let isEditMode = false;
let projectVinculosLocal = []; // ESTADO LOCAL DE VÍNCULOS
let ctxDocPodeEditar = false;
let ctxDocEditando = false;
let ctxDocOriginal = '';
let ctxDocCarregado = false;
const PROJETOS_CACHE = {}; // cache cliente→projetos (chave: `${tipo}::${nomeLower}`)
const TIPO_STATUS = { ativo: 'Ativo', onetime: 'Onetime', onboarding: 'Onboarding', inativo: 'Inativo' };

const FIELD_LABELS = {
    nome: 'Nome', documento: 'Documento', fee: 'Fee', moeda: 'Moeda',
    squad_atribuida: 'Squad', produto_contratado: 'Produto contratado',
    data_de_inicio: 'Data de início', data_fim: 'Data fim', cohort: 'Cohort', step: 'Step',
    meta_account_id: 'Meta account', google_account_id: 'Google account',
    orcamento_midia_meta: 'Orçamento Meta', orcamento_midia_google: 'Orçamento Google',
    fase_do_pipefy: 'Fase do Pipefy', informacoes_gerais: 'Informações gerais',
    url_webhook_gchat: 'Webhook', ekyte_workspace: 'Ekyte workspace',
    responsavel_projeto: 'Responsável', contrato_variavel: 'Contrato variável',
    status: 'Status', pipefy_id: 'Pipefy ID', id: 'ID',
    cliente: 'Cliente', localizacao_regiao_atuacao: 'Região de atuação',
    segmento_nicho: 'Segmento / nicho', publico_alvo: 'Público-alvo',
    objetivo_meta_principal: 'Objetivo / meta', contato_principal_decisor: 'Contato principal',
    equipe_responsavel: 'Equipe responsável', outros_contatos_chave: 'Outros contatos-chave',
    canais_midia_ativos: 'Canais de mídia', id_google: 'ID do Google', act_meta: 'ID da Meta (act)',
    ids_rastreamento: 'IDs de rastreamento', tracking_crm: 'Ferramenta de tracking / CRM',
    orcamento_midia_mensal: 'Orçamento mensal', benchmark_cpl_referencia: 'Benchmark / CPL',
    estrategia_campanha_atual: 'Estratégia / campanha', tom_voz_posicionamento: 'Tom de voz / posicionamento',
    must_donts_restricoes: "Must-dos / Don'ts e restrições",
    o_que_funciona: 'O que funciona', o_que_nao_funciona: 'O que não funciona',
    ticket_medio_financeiro: 'Ticket médio', forma_pagamento: 'Forma de pagamento',
    relacionamento_alertas: 'Relacionamento / alertas',
    pendencias_proximos_passos: 'Pendências / próximos passos',
    link_drive_documentos: 'Link do Drive', motivo_atualizacao: 'Motivo da atualização',
    contexto_geral: 'Documento do projeto',
};

function rotuloCampo(field) {
    return FIELD_LABELS[field] || String(field || '').replace(/_/g, ' ');
}

function escHtml(s) {
    return String(s === null || s === undefined ? '' : s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

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

function filterClients(inputEl) {
    // Lê o valor do próprio campo que disparou o evento (evita pegar input errado/vazio)
    const searchEl = inputEl || document.getElementById('searchInput');
    const searchValue = (searchEl && searchEl.value ? searchEl.value : '').toLowerCase().trim();

    const squadFilterEl = document.getElementById('squadFilter');
    const squadValue = squadFilterEl ? squadFilterEl.value.toLowerCase().trim() : '';

    // Cards do slide ativo; com fallback se a classe .active não estiver presente
    const activeSlide = document.querySelector('.slide-content.active');
    const cards = (activeSlide || document).querySelectorAll('.project-card');

    cards.forEach(card => {
        const clientName = (card.getAttribute('data-cliente') || '').toLowerCase();
        const squadName  = (card.getAttribute('data-squad') || '').toLowerCase();

        const matchSearch = !searchValue
            || clientName.includes(searchValue)
            || squadName.includes(searchValue);

        const matchSquad = !squadValue || squadName === squadValue;

        // O CSS da página usa `.project-card { display: flex !important }`,
        // então é preciso usar !important para conseguir esconder o card.
        if (matchSearch && matchSquad) {
            card.style.removeProperty('display'); // volta ao display do CSS (flex)
        } else {
            card.style.setProperty('display', 'none', 'important');
        }
    });

    updateTabCounts();
}

function updateTabCounts() {
    const searchEl = document.getElementById('searchInput');
    const searchValue = (searchEl && searchEl.value ? searchEl.value : '').toLowerCase().trim();

    const squadFilterEl = document.getElementById('squadFilter');
    const squadValue = squadFilterEl ? squadFilterEl.value.toLowerCase().trim() : '';

    ['ativos', 'onetime', 'onboarding', 'inativos'].forEach(slideName => {
        const slide = document.getElementById(`slide-${slideName}`);
        if (!slide) return;

        const cards = slide.querySelectorAll('.project-card');
        let count = 0;

        if (!searchValue && !squadValue) {
            count = cards.length;
        } else {
            cards.forEach(card => {
                const clientName = (card.getAttribute('data-cliente') || '').toLowerCase();
                const squadName  = (card.getAttribute('data-squad') || '').toLowerCase();

                const matchSearch = !searchValue
                    || clientName.includes(searchValue)
                    || squadName.includes(searchValue);

                const matchSquad = !squadValue || squadName === squadValue;

                if (matchSearch && matchSquad) count++;
            });
        }

        const tabBtn = document.querySelector(`.tab-btn[onclick*="'${slideName}'"]`);
        if (tabBtn) {
            const countEl = tabBtn.querySelector('.tab-count');
            if (countEl) countEl.textContent = count;
        }
    });
}

function populateSquadFilter() {
    const select = document.getElementById('squadFilter');
    if (!select) return;

    while (select.options.length > 1) {
        select.remove(1);
    }

    const squads = new Set();
    document.querySelectorAll('.project-card').forEach(card => {
        const s = (card.getAttribute('data-squad') || '').trim();
        if (s) squads.add(s);
    });

    const sorted = Array.from(squads).sort();
    sorted.forEach(squad => {
        const opt = document.createElement('option');
        opt.value = squad;
        opt.textContent = squad.replace(/\b\w/g, c => c.toUpperCase());
        select.appendChild(opt);
    });
}

document.addEventListener('DOMContentLoaded', populateSquadFilter);


/* ==============================
MODAL CLIENTE
================================ */

async function openClientModal(cardElement) {
    const clienteNome = cardElement.querySelector('.project-title').textContent;
    const tipo = cardElement.getAttribute('data-tipo');
    const chave = `${tipo}::${clienteNome.toLowerCase()}`;

    let projetos = PROJETOS_CACHE[chave];
    const nomeExato = cardElement.getAttribute('data-cliente-nome') || clienteNome;
    if (!projetos) {
        try {
            const resp = await fetch(
                `/api/projetos/por-cliente?nome=${encodeURIComponent(nomeExato)}&status=${encodeURIComponent(TIPO_STATUS[tipo] || '')}`
            );
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.error || 'Erro ao carregar projetos');
            projetos = Array.isArray(data) ? data : [];
            PROJETOS_CACHE[chave] = projetos;
        } catch (e) {
            if (window.HubModal) HubModal.alert('Erro ao carregar projetos: ' + e.message);
            return;
        }
    }

    const formatarData = (dataISO) => {
        if (!dataISO) return '—';
        const [ano, mes, dia] = dataISO.split('T')[0].split('-');
        return `${dia}/${mes}/${ano}`;
    };

    currentClientData = { nome: clienteNome, projetos, tipo };

    document.getElementById('clientModalTitle').textContent = `Projetos de: ${clienteNome}`;

    const projectsList = document.getElementById('projectsList');
    projectsList.innerHTML = '';

    // Totais por moeda
    const totais = {};
    projetos.forEach(projeto => {
        const m = (projeto.moeda || 'BRL').toUpperCase();
        const fee = Number(projeto.fee || 0);
        if (fee) totais[m] = (totais[m] || 0) + fee;
    });
    const totaisHtml = Object.entries(totais)
        .map(([m, v]) => formatCurrency(v, m))
        .filter(Boolean)
        .map(f => `<span class="project-total-item">${f}</span>`)
        .join(' ');

    const totalItem = document.createElement('div');
    totalItem.className = 'project-total-fee';
    totalItem.innerHTML = `<strong>Fees:</strong> ${totaisHtml || '—'}`;
    projectsList.appendChild(totalItem);

    // Lista projetos
    const statusTxt = (t) => ({ ativo: 'Ativo', onetime: 'One-time', onboarding: 'Onboarding', inativo: 'Inativo' }[t] || '');
    projetos.forEach(projeto => {
        const feeFormatado = formatCurrency(projeto.fee, projeto.moeda);

        const projectItem = document.createElement('div');
        projectItem.className = 'project-list-item';
        projectItem.innerHTML = `
            <div class="project-item-info">
                <div class="project-item-head">
                    <h4>${projeto.produto_contratado || 'Sem nome'}</h4>
                    ${statusTxt(tipo) ? `<span class="project-badge badge-${tipo}">${statusTxt(tipo)}</span>` : ''}
                </div>
                <div class="project-meta-chips">
                    <span class="project-meta-chip"><i class="fa-solid fa-sitemap"></i> ${projeto.squad_atribuida || 'N/A'}</span>
                    <span class="project-meta-chip"><i class="fa-solid fa-money-bill-wave"></i> ${feeFormatado || '—'}</span>
                    <span class="project-meta-chip"><i class="fa-regular fa-calendar"></i> Desde ${formatarData(projeto.data_de_inicio)}</span>
                </div>
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

    switchProjectTab('dados');
    carregarContextoProjeto(projectData.pipefy_id);

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
    loadResponsavelOptions(projectData.responsavel_projeto || '');
    
    // Campo: Contrato Variável
    const checkboxContratoVar = document.getElementById('modal_contrato_variavel');
    const labelContratoVar = document.getElementById('contrato_variavel_label');
    if (checkboxContratoVar) {
        checkboxContratoVar.checked = !!projectData.contrato_variavel;
        if (labelContratoVar) {
            labelContratoVar.textContent = projectData.contrato_variavel
                ? 'Faturamento variável ativo'
                : 'Faturamento variável inativo';
        }
        // Atualiza label ao mudar o checkbox
        checkboxContratoVar.onchange = function() {
            if (labelContratoVar) {
                labelContratoVar.textContent = this.checked
                    ? 'Faturamento variável ativo'
                    : 'Faturamento variável inativo';
            }
        };
    }


    let pipefyButton = document.getElementById("pipefyButton");

    pipefyButton.onclick = (e) => {
        if (e.button === 0) {
            window.open(
                `/kanban?card_id=${projectData.pipefy_id}`,
                '_blank'
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

    // CARREGAR VÍNCULOS E INVESTIDORES ATIVOS
    loadProjectVinculos(projectData.pipefy_id);
    if (window.APP_CONFIG.nivelAcesso === 'Gerência' || window.APP_CONFIG.nivelAcesso === 'Admin') {
        loadActiveInvestors();
        // Define data de hoje como padrão no date picker de vincular
        const vincularDataInput = document.getElementById('vincularDataInicio');
        if (vincularDataInput) vincularDataInput.value = _todayISO();
    }
}

function closeProjectModal() {
    document.getElementById('projectModal').classList.remove('active');
    document.body.style.overflow = 'auto';
    currentProjectData = null;
    currentHistorico = null;
    isEditMode = false;
    ctxDocEditando = false;
    setEditMode(false);
}

function backToClientModal() {
    document.getElementById('projectModal').classList.remove('active');
    if (currentClientData) {
        const { nome, projetos, tipo } = currentClientData;

        document.getElementById('clientModalTitle').textContent = `Projetos de: ${nome}`;

        const projectsList = document.getElementById('projectsList');
        projectsList.innerHTML = '';

        const formatarData = (dataISO) => {
            if (!dataISO) return '—';
            const [ano, mes, dia] = dataISO.split('T')[0].split('-');
            return `${dia}/${mes}/${ano}`;
        };

        let totalFee = 0;
        let moeda = null;
        projetos.forEach(projeto => {
            if (projeto.fee) {
                totalFee += Number(projeto.fee);
                moeda = projeto.moeda;
            }
        });

        const totalFeeFormatado = formatCurrency(totalFee, moeda);

        const totalItem = document.createElement('div');
        totalItem.className = 'project-total-fee';
        totalItem.innerHTML = `
            <strong>Fee Total:</strong> ${totalFeeFormatado || '—'}
        `;
        projectsList.appendChild(totalItem);

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
    }
    isEditMode = false;
    setEditMode(false);
}

function toggleEditMode() {
    isEditMode = !isEditMode;
    setEditMode(isEditMode);
    renderVinculos(); // 🔥 ESSENCIAL (Atualiza botões de remover)
}

function setEditMode(enable) {
    const inputs = document.querySelectorAll('#projectForm input, #projectForm select, #projectForm textarea');
    inputs.forEach(input => {
        // O documento do projeto tem edição própria (aba .md), independente do Editar global.
        if (input.closest && input.closest('#ctxDocEditor')) return;
        // PERMITIR EDIÇÃO DE NOME E FEE NO HUB LOCAL
        if (input.id !== 'modal_projeto_id' && input.id !== 'modal_tipo_projeto' && input.id !== 'modal_pipefy_id' && input.id !== 'modal_fase_pipefy') {
            if (input.id === 'modal_contrato_variavel') {
                const nivelAcesso = window.APP_CONFIG && window.APP_CONFIG.nivelAcesso;
                const temPermissao = nivelAcesso && nivelAcesso !== 'Usuário';
                input.disabled = !enable || !temPermissao;
            } else {
                input.disabled = !enable;
            }
        }
    });

    // Mostrar/esconder ações de vinculação
    const vinculosActions = document.getElementById('vinculosActions');
    if (vinculosActions) vinculosActions.style.display = enable ? 'flex' : 'none';

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
                const antes = values.antes ?? '';
                const depois = values.depois ?? '';
                return `
                    <div class="change-item">
                        <div class="change-field">${escHtml(rotuloCampo(field))}</div>
                        <div class="change-values">
                            <div class="change-box before">
                                <span class="change-badge before">Antes</span>
                                <div class="change-value">${escHtml(antes) || '<em>vazio</em>'}</div>
                            </div>
                            <div class="change-arrow">
                                <i class="fa-solid fa-arrow-right"></i>
                            </div>
                            <div class="change-box after">
                                <span class="change-badge after">Depois</span>
                                <div class="change-value">${escHtml(depois) || '<em>vazio</em>'}</div>
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
                            ${escHtml(item.usuario || 'Sistema')}
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
async function recarregarDados() {
    try {
        const response = await fetch('/api/projetos/listar');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const dados = await response.json();
        atualizarCards(dados);
    } catch (error) {
        console.error('Erro ao recarregar dados locais:', error);
        if (window.showToast) {
            window.showToast(
                'Alterações salvas, mas ocorreu um erro ao atualizar a página. Recarregue (F5) para ver os dados atualizados.',
                'error'
            );
        }
    }
}

/* ==============================
RECRIAR CARDS
============================== */
function atualizarCards(dados) {
    const tiposMap = {
        'ativos': 'ativo',
        'onetime': 'onetime', 
        'onboarding': 'onboarding',
        'inativos': 'inativo'
    };

    ['ativos', 'onetime', 'onboarding', 'inativos'].forEach(tipoSlide => {
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
                    <h3>Nenhum cliente ${tipoSlide === 'onetime' ? 'one-time' : tipoSlide === 'onboarding' ? 'em onboarding' : tipoSlide}</h3>
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
            
            PROJETOS_CACHE[`${tipoProjeto}::${cliente.toLowerCase()}`] = projetos;
            return `
                <div class="project-card" 
                    data-cliente="${cliente.toLowerCase()}" data-cliente-nome="${cliente}"
                    data-tipo="${tipoProjeto}"
                    data-squad="${(primeiroProj.squad_atribuida || '').toLowerCase()}"
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

    populateSquadFilter();
    filterClients();
}

/* ==============================
UPDATE PROJETO (ATUALIZADO)
================================ */
async function updateProject(event) {
    event.preventDefault();

    const form = event.target;
    const data = {};
    
    // Coleta TODOS os campos, inclusive desabilitados
    const allInputs = form.querySelectorAll('input, select, textarea');
    allInputs.forEach(input => {
        if (input.name) {
            data[input.name] = input.value;
        }
    });

    // Converte fee para número puro (Decimal no backend)
    data.fee = parseCurrencyToCents(data.fee) / 100;
    data.usuario = window.APP_CONFIG.userEmail;
    data.userToken = window.APP_CONFIG.userToken;

    // Flag de contrato variável
    const checkboxContratoVar = document.getElementById('modal_contrato_variavel');
    if (checkboxContratoVar) {
        data.contrato_variavel = checkboxContratoVar.checked;
    }

    // Coleta dados dos investidores vinculados do estado local
    data.investidores = projectVinculosLocal;

    // Salva o contexto do projeto (histórico — v2_)
    await salvarContextoProjeto(data.pipefy_id);

    try {
        // 1. Atualiza no HUB LOCAL (Backend Flask)
        const response = await fetch(`/api/projetos/${data.pipefy_id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            if (window.showToast) window.showToast("Projeto salvo com sucesso!", "success");
            window.location.href = `/hub-projetos?card_id=${data.pipefy_id}`;
        } else {
            const err = await response.json().catch(() => ({}));
            alert(`Erro ao salvar: ${err.error || 'Erro desconhecido'}`);
        }
    } catch (error) {
        console.error('Erro ao atualizar projeto:', error);
        const pipefyId = data?.pipefy_id;
        if (pipefyId) {
            window.location.href = `/hub-projetos?card_id=${pipefyId}`;
        } else {
            alert('Ocorreu um erro ao salvar as alterações.');
        }
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
    if (!dropdown || !menuBtn) return;

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

/* ==============================
CONTEXTO DO PROJETO (abas do modal)
=============================== */

function switchProjectTab(tab) {
    document.querySelectorAll('#projectModal .project-tab').forEach(b =>
        b.classList.toggle('active', b.dataset.ptab === tab));
    document.querySelectorAll('#projectModal .project-panel').forEach(p =>
        p.classList.toggle('active', p.dataset.ppanel === tab));
}

async function carregarContextoProjeto(pipefyId) {
    if (!pipefyId) return;
    ctxDocPodeEditar = false;
    ctxDocEditando = false;
    ctxDocOriginal = '';
    ctxDocCarregado = false;
    const taReset = document.getElementById('ctxDocTexto');
    if (taReset) taReset.value = '';
    renderPreviewDocumento('');
    atualizarControlesDocumento();
    try {
        const resp = await fetch(`/api/projetos/${pipefyId}/contexto`);
        const data = await resp.json();
        const ctx = data.contexto || {};
        document.querySelectorAll('#projectForm [data-ctx-field]').forEach(el => {
            const valor = ctx[el.dataset.ctxField];
            el.value = (valor === null || valor === undefined) ? '' : valor;
        });
        // Cliente padrão: nome do projeto
        const cli = document.querySelector('#projectForm [data-ctx-field="cliente"]');
        if (cli && !cli.value && currentProjectData) cli.value = currentProjectData.nome || '';

        ctxDocPodeEditar = !!data.pode_editar_documento;
        ctxDocEditando = false;
        ctxDocOriginal = ctx.contexto_geral || '';
        ctxDocCarregado = true;
        const ta = document.getElementById('ctxDocTexto');
        if (ta) ta.value = ctxDocOriginal;
        renderPreviewDocumento(ctxDocOriginal);
        atualizarControlesDocumento();
    } catch (e) {
        console.error('Erro ao carregar contexto do projeto:', e);
    }
}

function coletarContexto() {
    const ctx = {};
    document.querySelectorAll('#projectForm [data-ctx-field]').forEach(el => {
        ctx[el.dataset.ctxField] = el.value;
    });
    // Se o documento ainda não carregou, não envia vazio (evita apagar sem querer).
    if (!ctxDocCarregado) delete ctx.contexto_geral;
    return ctx;
}

async function salvarContextoProjeto(pipefyId) {
    if (!pipefyId) return;
    const ctx = coletarContexto();
    try {
        const resp = await fetch(`/api/projetos/${pipefyId}/contexto`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(ctx)
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            alert(`Erro ao salvar contexto: ${err.error || 'erro desconhecido'}`);
        }
    } catch (e) {
        console.error('Erro ao salvar contexto:', e);
    }
}

/* ==============================
DOCUMENTO DO PROJETO (context.md)
=============================== */

function setStatusDocumento(msg, tipo) {
    const el = document.getElementById('ctxDocStatus');
    if (!el) return;
    el.textContent = msg || '';
    el.className = 'ctx-doc-status' + (tipo ? ` ${tipo}` : '');
    clearTimeout(el._timer);
    if (msg) {
        el._timer = setTimeout(() => {
            el.textContent = '';
            el.className = 'ctx-doc-status';
        }, 6000);
    }
}

function renderPreviewDocumento(texto) {
    const box = document.getElementById('ctxDocPreview');
    if (!box) return;

    const raw = (texto || '').trim();
    if (!raw) {
        box.innerHTML = '<p class="ctx-doc-vazio">Nenhum documento cadastrado.</p>';
        return;
    }

    const marked = window.marked;
    const purify = window.DOMPurify;
    const parse = marked && (marked.parse || marked);
    if (parse && purify) {
        try {
            const html = parse(raw, { gfm: true, breaks: true });
            box.innerHTML = purify.sanitize(html, {
                FORBID_TAGS: ['style', 'iframe', 'object', 'embed', 'form', 'input', 'button'],
                FORBID_ATTR: ['style'],
            });
            box.querySelectorAll('a').forEach((a) => {
                a.target = '_blank';
                a.rel = 'noopener noreferrer';
            });
            return;
        } catch (e) {
            console.error('Erro ao renderizar Markdown:', e);
        }
    }

    box.innerHTML = '';
    const pre = document.createElement('pre');
    pre.className = 'ctx-doc-raw';
    pre.textContent = raw;
    box.appendChild(pre);
}

function atualizarControlesDocumento() {
    const editBtn = document.getElementById('ctxDocEditBtn');
    const downloadBtn = document.getElementById('ctxDocDownloadBtn');
    const editor = document.getElementById('ctxDocEditor');
    const preview = document.getElementById('ctxDocPreview');
    const ta = document.getElementById('ctxDocTexto');

    const temTexto = !!(ctxDocOriginal || '').trim();
    if (editBtn) editBtn.style.display = (ctxDocPodeEditar && !ctxDocEditando) ? 'inline-flex' : 'none';
    if (downloadBtn) downloadBtn.style.display = (temTexto && !ctxDocEditando) ? 'inline-flex' : 'none';
    if (editor) editor.style.display = ctxDocEditando ? 'block' : 'none';
    if (preview) preview.style.display = ctxDocEditando ? 'none' : 'block';
    if (ta) ta.disabled = !ctxDocEditando;
}

function editarDocumentoProjeto() {
    if (!ctxDocPodeEditar) return;
    const ta = document.getElementById('ctxDocTexto');
    if (ta) ta.value = ctxDocOriginal;
    ctxDocEditando = true;
    atualizarControlesDocumento();
    setStatusDocumento('', '');
    if (ta) ta.focus();
}

function cancelarDocumentoProjeto() {
    ctxDocEditando = false;
    const ta = document.getElementById('ctxDocTexto');
    if (ta) ta.value = ctxDocOriginal;
    renderPreviewDocumento(ctxDocOriginal);
    atualizarControlesDocumento();
    setStatusDocumento('', '');
}

async function salvarDocumentoProjeto() {
    const pipefyId = currentProjectData && currentProjectData.pipefy_id;
    if (!pipefyId) return;

    const ta = document.getElementById('ctxDocTexto');
    const texto = (ta && ta.value) || '';
    const motivoEl = document.querySelector('[data-ctx-field="motivo_atualizacao"]');
    const btn = document.getElementById('ctxDocSalvarBtn');
    if (btn) btn.disabled = true;

    try {
        const resp = await fetch(`/api/projetos/${pipefyId}/contexto-geral`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                contexto_geral: texto,
                motivo_atualizacao: motivoEl ? motivoEl.value : '',
            }),
        });
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) throw new Error(data.error || 'Erro ao salvar o documento.');

        ctxDocOriginal = (data.contexto && data.contexto.contexto_geral) || texto;
        if (ta) ta.value = ctxDocOriginal;
        ctxDocEditando = false;
        renderPreviewDocumento(ctxDocOriginal);
        atualizarControlesDocumento();
        setStatusDocumento('', '');
        if (typeof window.showToast === 'function') {
            window.showToast('Documento do projeto salvo!', 'success');
        }
    } catch (e) {
        setStatusDocumento(e.message || 'Erro ao salvar o documento.', 'erro');
    } finally {
        if (btn) btn.disabled = false;
    }
}

function anexarDocumentoProjeto(input) {
    const file = input.files && input.files[0];
    input.value = '';
    if (!file) return;

    const nome = (file.name || '').toLowerCase();
    if (!/\.(md|markdown|txt)$/.test(nome)) {
        setStatusDocumento('Use um arquivo .md, .markdown ou .txt.', 'erro');
        return;
    }
    if (file.size > 512 * 1024) {
        setStatusDocumento('O arquivo deve ter no máximo 512 KB.', 'erro');
        return;
    }

    const reader = new FileReader();
    reader.onload = () => {
        const ta = document.getElementById('ctxDocTexto');
        if (!ta) return;
        ta.value = String(reader.result || '').replace(/^\uFEFF/, '');
        setStatusDocumento(`"${file.name}" carregado. Clique em Salvar documento.`, 'ok');
    };
    reader.onerror = () => setStatusDocumento('Não foi possível ler o arquivo.', 'erro');
    reader.readAsText(file, 'utf-8');
}

function baixarDocumentoProjeto() {
    const texto = ctxDocOriginal || '';
    if (!texto.trim()) return;

    const pipefyId = currentProjectData && currentProjectData.pipefy_id;
    const blob = new Blob([texto], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `context-${pipefyId || 'projeto'}.md`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}


/* ==============================
EVENT LISTENERS GLOBAIS
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

/* ==============================
VINCULAÇÃO DE INVESTIDORES
================================ */

async function loadActiveInvestors() {
    try {
        const response = await fetch('/api/admin/investidores-ativos');
        const investidores = await response.json();
        
        const select = document.getElementById('vinculoInvestidorSelect');
        if (!select) return;

        select.innerHTML = '<option value="">Vincular investidor...</option>';
        investidores.forEach(inv => {
            const option = document.createElement('option');
            option.value = inv.email;
            option.textContent = `${inv.nome} (${inv.email})`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Erro ao carregar investidores ativos:', error);
    }
}

async function loadResponsavelOptions(selectedEmail = '') {
    try {
        const response = await fetch('/api/admin/investidores-ativos');
        const investidores = await response.json();

        const select = document.getElementById('modal_responsavel_projeto');
        if (!select) return;

        select.innerHTML = '<option value="">Selecione o responsável...</option>';
        investidores.forEach(inv => {
            const option = document.createElement('option');
            option.value = inv.email;
            option.textContent = `${inv.nome} (${inv.email})`;
            select.appendChild(option);
        });

        select.value = selectedEmail;
    } catch (error) {
        console.error('Erro ao carregar responsáveis:', error);
    }
}

async function loadProjectVinculos(pipefy_id) {
    const container = document.getElementById('vinculosContainer');
    if (!container) return;

    container.innerHTML = '<div class="loading"><i class="fa-solid fa-spinner fa-spin"></i> Carregando vínculos...</div>';
    
    try {
        const response = await fetch(`/api/projetos/${pipefy_id}/vinculos`);
        const vinculos = await response.json();
        
        // Inicializa estado local
        projectVinculosLocal = vinculos;
        renderVinculos();

    } catch (error) {
        console.error('Erro ao carregar vínculos:', error);
        container.innerHTML = '<div class="error">Erro ao carregar vínculos.</div>';
    }
}

function renderVinculos() {
    const container = document.getElementById('vinculosContainer');
    if (!container) return;

    if (projectVinculosLocal.length === 0) {
        container.innerHTML = `
            <div class="notes-empty">
                <i class="fa-solid fa-user-slash"></i>
                <p>Nenhum investidor vinculado</p>
            </div>
        `;
        return;
    }

    container.innerHTML = projectVinculosLocal.map(v => {
        const dataInicioExibir = _formatDateBR(v.data_inicio);
        const isChurn = v.active === false || (v.data_fim && new Date(v.data_fim) <= new Date());
        const nome = v.nome || v.email;
        const cargo = v.funcao || v.posicao || '';
        const initials = _buildInitials(nome);
        const avatarHTML = v.profile_picture
            ? `<img class="vinculo-avatar" src="${v.profile_picture}" alt="${nome}" onerror="this.outerHTML='<div class=\\'vinculo-avatar vinculo-avatar-fallback\\'>${initials}</div>'">`
            : `<div class="vinculo-avatar vinculo-avatar-fallback">${initials}</div>`;

        return `
        <div class="vinculo-card-v2 ${isChurn ? 'churn' : ''}" onclick="isEditMode ? openInvestidorVinculoModal('${v.email}', 'edit') : null">
            <div class="vinculo-card-header">
                <div class="vinculo-identity">
                    ${avatarHTML}
                    <div class="vinculo-user-info">
                        <span class="vinculo-name" title="${nome}">${nome}</span>
                        ${cargo ? `<span class="vinculo-role">${cargo}</span>` : ''}
                        <span class="vinculo-email" title="${v.email}">${v.email}</span>
                    </div>
                </div>
                ${isEditMode ? `
                <button type="button" class="btn-card-edit" title="Editar vínculo">
                    <i class="fa-solid fa-pen"></i>
                </button>
                ` : ''}
            </div>
            <div class="vinculo-card-body">
                <div class="vinculo-tags-row">
                    <span class="vinculo-status-tag ${isChurn ? 'status-inactive' : 'status-active'}">
                        ${isChurn ? 'Churn' : 'Ativo'}
                    </span>
                    ${v.cientista ? `
                        <span class="badge-cientista-v2" title="Entrada: ${_formatDateBR(v.cientista_entrada) || '—'}">
                            <i class="fa-solid fa-flask"></i> Cientista
                        </span>
                    ` : ''}
                </div>
                <div class="vinculo-meta-row">
                    <div class="meta-item">
                        <i class="fa-solid fa-calendar-plus"></i>
                        <span>${dataInicioExibir}</span>
                    </div>
                    ${v.data_fim ? `
                    <div class="meta-item">
                        <i class="fa-solid fa-calendar-minus"></i>
                        <span>${_formatDateBR(v.data_fim)}</span>
                    </div>
                    ` : ''}
                </div>
            </div>
            ${isEditMode ? `
            <button type="button" class="btn-remove-vinculo-v2"
                    onclick="event.stopPropagation(); removerVinculoLocal('${v.email}')"
                    title="Remover investidor">
                <i class="fa-solid fa-trash-can"></i>
            </button>
            ` : ''}
        </div>`;
    }).join('');
}

function _buildInitials(nome) {
    if (!nome) return '?';
    const parts = String(nome).trim().split(/\s+/);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}
function _todayISO() {
    return new Date().toISOString().split('T')[0];
}

function _formatDateBR(iso) {
    if (!iso) return '—';
    const parts = iso.split('T')[0].split('-');
    if (parts.length !== 3) return iso;
    const [y, m, d] = parts;
    return `${d}/${m}/${y}`;
}

/* ==============================
MODAL DE VÍNCULO (V2)
================================ */

let _vinculoEditEmail = null;
let _vinculoMode = 'add'; // 'add' ou 'edit'

function openInvestidorVinculoModal(email = null, mode = 'add') {
    _vinculoMode = mode;
    _vinculoEditEmail = email;

    const modal = document.getElementById('investidorVinculoModal');
    const title = document.getElementById('vinculoModalTitle');
    const selectGroup = document.getElementById('vinculoSelectGroup');
    const nameGroup = document.getElementById('vinculoNameGroup');
    const nameInput = document.getElementById('vinculoInvestidorName');
    
    // Reset inputs
    document.getElementById('vinculoInvestidorSelect').value = '';
    document.getElementById('vinculoDataInicio').value = _todayISO();
    document.getElementById('vinculoDataFim').value = '';
    document.getElementById('vinculoIsCientista').checked = false;
    document.getElementById('vinculoCientistaInicio').value = '';
    document.getElementById('vinculoCientistaFim').value = '';
    
    if (mode === 'edit' && email) {
        title.innerHTML = '<i class="fa-solid fa-user-pen"></i> Editar Vínculo';
        if (selectGroup) selectGroup.style.display = 'none';
        if (nameGroup) nameGroup.style.display = 'block';
        if (nameInput) nameInput.value = email;

        const v = projectVinculosLocal.find(x => x.email === email);
        if (v) {
            document.getElementById('vinculoDataInicio').value = v.data_inicio ? v.data_inicio.split('T')[0] : '';
            document.getElementById('vinculoDataFim').value = v.data_fim ? v.data_fim.split('T')[0] : '';
            document.getElementById('vinculoIsCientista').checked = v.cientista || false;
            document.getElementById('vinculoCientistaInicio').value = v.cientista_entrada ? v.cientista_entrada.split('T')[0] : '';
            document.getElementById('vinculoCientistaFim').value = v.cientista_saida ? v.cientista_saida.split('T')[0] : '';
        }
    } else {
        title.innerHTML = '<i class="fa-solid fa-user-plus"></i> Vincular Investidor';
        if (selectGroup) selectGroup.style.display = 'block';
        if (nameGroup) nameGroup.style.display = 'none';
    }

    toggleScientistDates();
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeInvestidorVinculoModal() {
    document.getElementById('investidorVinculoModal').classList.remove('active');
    document.body.style.overflow = 'auto';
    _vinculoEditEmail = null;
}

function toggleScientistDates() {
    const isCientista = document.getElementById('vinculoIsCientista').checked;
    const group = document.getElementById('scientistDatesGroup');
    if (group) group.style.display = isCientista ? 'block' : 'none';
}

function confirmarVinculo() {
    const email = _vinculoMode === 'add' 
        ? document.getElementById('vinculoInvestidorSelect').value 
        : _vinculoEditEmail;
    
    if (!email) {
        if (window.showToast) showToast('Selecione um investidor.', 'error');
        return;
    }

    const dataInicio = document.getElementById('vinculoDataInicio').value;
    const dataFim = document.getElementById('vinculoDataFim').value;
    const isCientista = document.getElementById('vinculoIsCientista').checked;
    const cientistaInicio = document.getElementById('vinculoCientistaInicio').value;
    const cientistaFim = document.getElementById('vinculoCientistaFim').value;

    if (!dataInicio) {
        if (window.showToast) showToast('A data de início é obrigatória.', 'error');
        return;
    }

    const vinculoData = {
        email: email,
        data_inicio: dataInicio,
        data_fim: dataFim || null,
        active: !dataFim,
        cientista: isCientista,
        cientista_entrada: isCientista ? (cientistaInicio || null) : null,
        cientista_saida: isCientista ? (cientistaFim || null) : null
    };

    if (_vinculoMode === 'add') {
        if (projectVinculosLocal.find(v => v.email === email)) {
            if (window.showToast) showToast('Este investidor já está vinculado.', 'error');
            return;
        }
        projectVinculosLocal.push(vinculoData);
    } else {
        const idx = projectVinculosLocal.findIndex(v => v.email === email);
        if (idx !== -1) {
            projectVinculosLocal[idx] = vinculoData;
        }
    }

    renderVinculos();
    closeInvestidorVinculoModal();
    if (window.showToast) showToast('Vínculo atualizado localmente. Clique em "Salvar" para confirmar no banco.', 'info');
}

async function removerVinculoLocal(email) {
    if (!(await HubModal.confirm(`Deseja remover o vínculo de ${email}?`, { okLabel: "Remover", danger: true }))) return;
    projectVinculosLocal = projectVinculosLocal.filter(v => v.email !== email);
    renderVinculos();
}

// ── Abrir projeto diretamente via ?card_id= na URL ──
document.addEventListener('DOMContentLoaded', async function autoOpenCard() {
    const params = new URLSearchParams(window.location.search);
    const cardId = params.get('card_id');
    if (!cardId) return;

    history.replaceState({}, '', '/hub-projetos');

    const tipoDeStatus = (s) =>
        ({ Ativo: 'ativo', Onetime: 'onetime', Onboarding: 'onboarding', Inativo: 'inativo' }[s || ''] || 'ativo');

    try {
        const resp = await fetch(`/api/projetos/${encodeURIComponent(cardId)}`);
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || 'Erro ao carregar o projeto');
        openProjectModal(data, tipoDeStatus(data.status));
    } catch (e) {
        console.error('autoOpenCard:', e);
    }
});
