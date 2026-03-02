/**
 * criativa.js
 * Lógica front-end da página de Gestão Criativa.
 * Gerencia a troca de views (Clientes ↔ Entregas), filtro de busca e checkboxes de entrega.
 */

/**
 * Alterna entre as views "Clientes" e "Entregas" na mesma página.
 * @param {string} view - 'clientes' ou 'entregas'
 */
function switchCriativaView(view) {
    // Esconde todas as views
    document.querySelectorAll('.criativa-view').forEach(v => {
        v.classList.remove('active');
    });

    // Remove estado ativo de todos os botões
    document.querySelectorAll('.criativa-nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Ativa a view selecionada
    const targetView = document.getElementById('criativa-view-' + view);
    if (targetView) {
        targetView.classList.add('active');
    }

    // Ativa o botão correspondente
    const targetBtn = document.getElementById('btn-view-' + view);
    if (targetBtn) {
        targetBtn.classList.add('active');
    }
}

/**
 * Filtra as linhas da tabela criativa com base no texto digitado.
 * Compara o valor do input com a primeira coluna (nome do cliente).
 */
function filterCriativoTable() {
    const input = document.getElementById('criativaSearchInput');
    const filter = input.value.toLowerCase().trim();
    const table = document.getElementById('criativa-table');
    if (!table) return;

    const rows = table.querySelectorAll('tbody tr');

    rows.forEach(row => {
        // Ignora a linha de total
        if (row.classList.contains('criativa-total-row')) {
            return;
        }

        const clienteCell = row.querySelector('td:first-child');
        if (clienteCell) {
            const clienteText = clienteCell.textContent.toLowerCase();
            row.style.display = clienteText.includes(filter) ? '' : 'none';
        }
    });
}

/**
 * Alterna o estado de uma entrega criativa (checked/unchecked).
 * Cada entrega vale 25% do total.
 * @param {number} num - Número da entrega (1 a 4)
 */
function toggleCriativaEntrega(num) {
    const card = document.getElementById('criativa-entrega-' + num);
    if (!card) return;

    card.classList.toggle('checked');

    // Atualiza o texto de instrução
    const infoP = card.querySelector('.entrega-info p');
    if (infoP) {
        if (card.classList.contains('checked')) {
            infoP.textContent = 'Entrega concluída ✓';
        } else {
            infoP.textContent = 'Clique para marcar conclusão';
        }
    }

    // Calcula o percentual total de entregas concluídas
    atualizarMRRCriativo();
}

/**
 * Abre o modal de nova entrega criativa.
 */
function openNovaEntregaModal() {
    const modal = document.getElementById('modal-nova-entrega');
    if (modal) modal.style.display = 'flex';
}

/**
 * Fecha o modal de nova entrega criativa.
 */
function closeNovaEntregaModal() {
    const modal = document.getElementById('modal-nova-entrega');
    if (modal) modal.style.display = 'none';
}

/**
 * Processa o salvamento de uma nova entrega (Mock).
 * @param {Event} event 
 */
function saveNovaEntrega(event) {
    event.preventDefault();

    const projeto = document.getElementById('entrega-projeto').value;
    const tipo = document.getElementById('entrega-tipo').value;
    const quantidade = parseInt(document.getElementById('entrega-quantidade').value);

    if (!projeto || !tipo || isNaN(quantidade)) return;

    // Lógica Mock: Localiza a linha do cliente na tabela e atualiza os valores
    const tableBody = document.getElementById('criativa-table-body');
    const rows = Array.from(tableBody.querySelectorAll('tr'));

    const row = rows.find(r => r.textContent.includes('Cliente ' + projeto));

    if (row) {
        let colIndex = -1;
        if (tipo === 'criativo') colIndex = 3; // Criativos Entreg.
        else if (tipo === 'lp') colIndex = 5;     // LPs Entreg.
        else if (tipo === 'video') colIndex = 7;  // Vídeos Entreg.
        else if (tipo === 'copy') colIndex = 8;   // Copys

        if (colIndex !== -1) {
            const cell = row.children[colIndex];
            const currentVal = parseInt(cell.textContent) || 0;
            cell.textContent = currentVal + quantidade;

            // Atualiza o total da linha
            const totalCell = row.querySelector('.cell-total');
            const currentTotal = parseInt(totalCell.textContent) || 0;
            totalCell.innerHTML = `<strong>${currentTotal + quantidade}</strong>`;

            // Atualiza a linha de Totais (Mock simples)
            updateTableTotals();

            // Atualiza KPIs
            updateKPIs(tipo, quantidade);
        }
    }

    // Feedback e fechamento
    console.log(`Entrega salva: ${quantidade} ${tipo} para ${projeto}`);
    closeNovaEntregaModal();
    document.getElementById('form-nova-entrega').reset();

    // Notificação Premium
    showToast(`Entrega de ${quantidade} ${tipo}(s) para ${projeto} registrada!`, 'success');
}

/**
 * Atualiza os totais da tabela após uma inserção.
 */
function updateTableTotals() {
    const tableBody = document.getElementById('criativa-table-body');
    const rows = Array.from(tableBody.querySelectorAll('tr:not(.criativa-total-row)'));
    const totalRow = tableBody.querySelector('.criativa-total-row');

    if (!totalRow) return;

    // Itera pelas colunas de 2 a 9 (índices 2 a 9)
    for (let i = 2; i <= 9; i++) {
        let colSum = 0;
        rows.forEach(row => {
            if (row.style.display !== 'none') {
                colSum += parseInt(row.children[i].textContent) || 0;
            }
        });
        totalRow.children[i].innerHTML = `<strong>${colSum}</strong>`;
    }
}

/**
 * Atualiza os KPIs globais no topo da página.
 */
function updateKPIs(tipo, quantidade) {
    if (tipo === 'criativo') {
        const kpi = document.getElementById('kpi-total-criativos');
        if (kpi) kpi.textContent = parseInt(kpi.textContent) + quantidade;
    } else if (tipo === 'video') {
        const kpi = document.getElementById('kpi-total-videos');
        if (kpi) kpi.textContent = parseInt(kpi.textContent) + quantidade;
    }
}

// Inicialização: Fecha modal ao clicar fora dele
window.onclick = function (event) {
    const modal = document.getElementById('modal-nova-entrega');
    if (event.target == modal) {
        closeNovaEntregaModal();
    }
    const modalHist = document.getElementById('modal-historico-criativa');
    if (event.target == modalHist) {
        closeHistoricoModal();
    }
};

/**
 * Atualiza o valor de impacto no MRR com base nas entregas marcadas.
 */
function atualizarMRRCriativo() {
    const totalEntregas = 4;
    let concluidas = 0;

    for (let i = 1; i <= totalEntregas; i++) {
        const card = document.getElementById('criativa-entrega-' + i);
        if (card && card.classList.contains('checked')) {
            concluidas++;
        }
    }

    const percentual = (concluidas / totalEntregas);
    const feeTotal = 22600;
    const impacto = feeTotal * percentual;

    const mrrEl = document.getElementById('criativa-mrr-impact');
    if (mrrEl) {
        mrrEl.textContent = 'R$ ' + impacto.toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }
}

/**
 * Dados Mockados de Histórico Mensal e Detalhado
 */
const HISTORICO_CRIATIVA = {
    "Março 2026": [
        {
            id: 'alpha-mar',
            cliente: "Cliente Alpha",
            data: "Hoje, 10:30",
            detalhes: [
                { item: "Criativos Estáticos", contratado: 10, entregue: 8 },
                { item: "Landing Pages", contratado: 3, entregue: 2 },
                { item: "Vídeos", contratado: 5, entregue: 4 },
                { item: "Copys", contratado: 12, entregue: 12 }
            ]
        },
        {
            id: 'beta-mar',
            cliente: "Cliente Beta",
            data: "Hoje, 09:15",
            detalhes: [
                { item: "Criativos Estáticos", contratado: 15, entregue: 12 },
                { item: "Landing Pages", contratado: 4, entregue: 3 },
                { item: "Vídeos", contratado: 8, entregue: 6 },
                { item: "Copys", contratado: 18, entregue: 18 }
            ]
        }
    ],
    "Fevereiro 2026": [
        {
            id: 'gamma-feb',
            cliente: "Cliente Gamma",
            data: "28 Fev, 14:20",
            detalhes: [
                { item: "Criativos Estáticos", contratado: 8, entregue: 8 },
                { item: "Landing Pages", contratado: 2, entregue: 2 },
                { item: "Vídeos", contratado: 3, entregue: 3 },
                { item: "Copys", contratado: 8, entregue: 8 }
            ]
        },
        {
            id: 'delta-feb',
            cliente: "Cliente Delta",
            data: "27 Fev, 16:45",
            detalhes: [
                { item: "Criativos Estáticos", contratado: 20, entregue: 15 },
                { item: "Landing Pages", contratado: 5, entregue: 4 },
                { item: "Vídeos", contratado: 10, entregue: 8 },
                { item: "Copys", contratado: 24, entregue: 20 }
            ]
        }
    ]
};

/**
 * Abre o modal de histórico de entregas e renderiza as abas de meses.
 */
function openHistoricoModal() {
    const modal = document.getElementById('modal-historico-criativa');
    if (!modal) return;

    modal.style.display = 'flex';

    const body = modal.querySelector('.modal-body');
    if (!body) return;

    // Cria a estrutura de navegação por meses
    const meses = Object.keys(HISTORICO_CRIATIVA);
    let navHtml = `<div class="historico-meses-nav">`;
    meses.forEach((mes, idx) => {
        navHtml += `<button class="mes-tab ${idx === 0 ? 'active' : ''}" onclick="renderHistoricoMes('${mes}', this)">${mes}</button>`;
    });
    navHtml += `</div><div id="historico-content-area"></div>`;

    body.innerHTML = navHtml;

    // Renderiza o primeiro mês por padrão
    if (meses.length > 0) {
        renderHistoricoMes(meses[0]);
    }
}

/**
 * Renderiza os itens de histórico para um mês específico.
 * @param {string} mes - Nome do mês selecionado
 * @param {HTMLElement} btn - Botão clicado (opcional)
 */
function renderHistoricoMes(mes, btn) {
    // Atualiza classes dos botões
    if (btn) {
        document.querySelectorAll('.mes-tab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    }

    const contentArea = document.getElementById('historico-content-area');
    if (!contentArea) return;

    const projetos = HISTORICO_CRIATIVA[mes] || [];
    let html = '';

    projetos.forEach((proj, idx) => {
        html += `
            <div class="historico-detalhe-card">
                <div class="historico-detalhe-header" onclick="toggleDetalheProjeto('${proj.id}')">
                    <div class="historico-cliente-info">
                        <strong>${proj.cliente}</strong>
                        <span>Atividade em ${proj.data}</span>
                    </div>
                    <i class="fas fa-chevron-down" id="icon-${proj.id}"></i>
                </div>
                <div class="historico-detalhe-body" id="body-${proj.id}">
                    <table class="tabela-detalhe">
                        <thead>
                            <tr>
                                <th>Item</th>
                                <th style="text-align:center">Contratado</th>
                                <th style="text-align:center">Entregue</th>
                                <th style="text-align:center">%</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${proj.detalhes.map(d => {
            const pct = Math.round((d.entregue / d.contratado) * 100);
            const statusClass = pct >= 100 ? 'bom' : (pct >= 70 ? 'medio' : 'ruim');
            return `
                                    <tr>
                                        <td>${d.item}</td>
                                        <td style="text-align:center" class="text-contratado">${d.contratado}</td>
                                        <td style="text-align:center" class="text-entregue">${d.entregue}</td>
                                        <td style="text-align:center"><span class="pct-badge ${statusClass}">${pct}%</span></td>
                                    </tr>
                                `;
        }).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    });

    contentArea.innerHTML = html || '<p style="text-align:center; color:#888; padding:2rem;">Nenhum registro encontrado.</p>';
}

/**
 * Expande ou recolhe o detalhamento de um projeto no histórico.
 * @param {string} id - ID do projeto
 */
function toggleDetalheProjeto(id) {
    const body = document.getElementById('body-' + id);
    const icon = document.getElementById('icon-' + id);

    if (body) {
        const isActive = body.classList.contains('active');
        // Fecha outros? (opcional: document.querySelectorAll('.historico-detalhe-body').forEach(b => b.classList.remove('active')))
        body.classList.toggle('active');

        if (icon) {
            icon.style.transform = isActive ? 'rotate(0deg)' : 'rotate(180deg)';
            icon.style.transition = 'transform 0.3s';
        }
    }
}

/**
 * Fecha o modal de histórico de entregas.
 */
function closeHistoricoModal() {
    const modal = document.getElementById('modal-historico-criativa');
    if (modal) modal.style.display = 'none';
}
