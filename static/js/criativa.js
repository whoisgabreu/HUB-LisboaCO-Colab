/**
 * criativa.js
 * Lógica front-end da página de Gestão Criativa.
 */

// ── Estado global ─────────────────────────────────────────────────────────────
let _clientesDetalheAtual  = [];   // clientes do designer em exibição
let _clientesBaseAtual     = [];   // cópia dos clientes sem entregas (para remerge ao trocar período)
let _designerEmailAtual    = '';   // email do designer em exibição
let _mesSelecionado        = (window.APP_CONFIG || {}).mes  || new Date().getMonth() + 1;
let _anoSelecionado        = (window.APP_CONFIG || {}).ano  || new Date().getFullYear();

// Instâncias de gráficos (destruídas ao recriar)
let chartContratadoEntregue = null;
let chartConclusao          = null;

// ── Helpers de permissão ──────────────────────────────────────────────────────
function _isCoordinador() {
    const cfg = window.APP_CONFIG || {};
    return cfg.userPosicao === 'Gerência' || cfg.userPosicao === 'Sócio' || cfg.userAccessLevel === 'Admin';
}

// ── Seletor de período (mês/ano) ─────────────────────────────────────────────
/**
 * Chamado ao mudar o select de mês ou ano.
 * - Se o designer detalhe estiver aberto: faz AJAX e permanece na tela.
 * - Se estiver na view de equipe: recarrega a página normalmente.
 */
function handlePeriodoChange() {
    const novoMes = parseInt(document.getElementById('sel-mes').value);
    const novoAno = parseInt(document.getElementById('sel-ano').value);

    const isDetalhe = document.getElementById('criativa-view-designer-detalhe')
                            ?.classList.contains('active');

    if (isDetalhe && _designerEmailAtual) {
        _mesSelecionado = novoMes;
        _anoSelecionado = novoAno;

        // Atualiza URL sem recarregar
        const url = new URL(window.location);
        url.searchParams.set('mes', novoMes);
        url.searchParams.set('ano', novoAno);
        history.replaceState({}, '', url);

        _fetchAndRefreshDetalhe();
    } else {
        document.getElementById('form-periodo').submit();
    }
}

/**
 * Busca as entregas do designer atual para o período selecionado
 * e atualiza a view de detalhe sem recarregar a página.
 */
async function _fetchAndRefreshDetalhe() {
    try {
        const resp = await fetch(
            `/api/criativa/entregas/${encodeURIComponent(_designerEmailAtual)}/${_mesSelecionado}/${_anoSelecionado}`
        );
        if (!resp.ok) throw new Error('Falha ao buscar dados do período.');
        const entregas = await resp.json();

        // Remergeia os dados do período nos clientes base (preserva nome e projeto_id)
        _clientesDetalheAtual = _clientesBaseAtual.map(c => {
            const entry = (entregas || []).find(e => String(e.projeto_id) === String(c.projeto_id));
            return {
                ...c,
                link_criativos: entry ? (entry.link_criativos ?? '') : '',
                criativos_c: entry ? (entry.criativos?.contratados ?? 0) : 0,
                criativos_e: entry ? (entry.criativos?.entregues   ?? 0) : 0,
                videos_c:    entry ? (entry.videos?.contratados    ?? 0) : 0,
                videos_e:    entry ? (entry.videos?.entregues      ?? 0) : 0,
                lps_c:       entry ? (entry.lp?.contratados        ?? 0) : 0,
                lps_e:       entry ? (entry.lp?.entregues          ?? 0) : 0,
            };
        });

        renderChartPorCliente(_clientesDetalheAtual);
        atualizarKpisDetalhe(_clientesDetalheAtual);
    } catch (e) {
        console.error(e);
        showToast('Erro ao atualizar dados do período.', 'error');
    }
}

// ── Inicialização ─────────────────────────────────────────────────────────────
// Desativa animações do Chart.js globalmente para evitar travamentos
if (typeof Chart !== 'undefined') {
    Chart.defaults.animation = false;
}

document.addEventListener('DOMContentLoaded', () => {
    // Fecha modais ao clicar no backdrop
    ['modal-designer', 'modal-contratados', 'modal-link-criativo'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('click', e => {
            if (e.target === e.currentTarget) el.style.display = 'none';
        });
    });

    // Delegação de eventos na tabela de clientes (persistente no DOM)
    const tbody = document.getElementById('detalhe-clientes-tbody');
    if (tbody) {
        tbody.addEventListener('click', e => {
            // Botões +/-
            const deltaBtn = e.target.closest('.btn-delta');
            if (deltaBtn) {
                deltaEntregue(
                    deltaBtn.dataset.projId,
                    deltaBtn.dataset.cliente,
                    deltaBtn.dataset.categoria,
                    parseInt(deltaBtn.dataset.delta)
                );
                return;
            }
            // Botão editar link
            const linkBtn = e.target.closest('.criativa-btn-link-edit');
            if (linkBtn) {
                const c = _clientesDetalheAtual.find(x => String(x.projeto_id) === String(linkBtn.dataset.projId));
                if (c) openLinkModal(c);
                return;
            }
            // Botão configurar contratados (coordenador)
            const contBtn = e.target.closest('.criativa-btn-contratados');
            if (contBtn) {
                const c = _clientesDetalheAtual.find(x => String(x.projeto_id) === String(contBtn.dataset.projId));
                if (c) openContratadosModal(c);
                return;
            }
        });
    }
});

// ── Navegação entre views ─────────────────────────────────────────────────────
function switchCriativaView(view) {
    document.querySelectorAll('.criativa-view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.criativa-nav-btn').forEach(btn => btn.classList.remove('active'));

    const targetView = document.getElementById('criativa-view-' + view);
    if (targetView) targetView.classList.add('active');

    const targetBtn = document.getElementById('btn-view-' + view);
    if (targetBtn) targetBtn.classList.add('active');
}

function voltarParaEquipe() {
    switchCriativaView('equipe');
}

// ── Modal de Designer (leitura) ───────────────────────────────────────────────
function openDesignerModal(card) {
    const name  = card.getAttribute('data-designer-name');
    const role  = card.getAttribute('data-designer-role');
    const photo = card.getAttribute('data-designer-photo');
    let clientes = [];

    try {
        clientes = JSON.parse(card.getAttribute('data-designer-clientes-json') || '[]');
    } catch (e) {
        console.error('Erro ao parsear clientes do designer:', e);
    }

    document.getElementById('designer-modal-name').textContent = name;
    document.getElementById('designer-modal-role').textContent = role;

    const avatarEl = document.getElementById('designer-modal-avatar');
    avatarEl.innerHTML = photo
        ? `<img src="static/images/profile_pictures/${photo}" alt="${name}" style="width:100%;height:100%;object-fit:cover;">`
        : `<i class="fa-solid fa-user-tie"></i>`;

    const tbody = document.getElementById('designer-modal-tbody');
    tbody.innerHTML = '';
    clientes.forEach(c => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="cell-cliente" style="text-align:left; padding-left:1rem;"><strong>${c.nome}</strong></td>
            <td class="text-contratado">${c.criativos_c ?? '-'}</td>
            <td class="text-entregue">${c.criativos_e ?? '-'}</td>
            <td class="text-contratado">${c.videos_c ?? '-'}</td>
            <td class="text-entregue">${c.videos_e ?? '-'}</td>
            <td class="text-contratado">${c.lps_c ?? '-'}</td>
            <td class="text-entregue">${c.lps_e ?? '-'}</td>
        `;
        tbody.appendChild(row);
    });

    document.getElementById('modal-designer').style.display = 'flex';
}

function closeDesignerModal() {
    document.getElementById('modal-designer').style.display = 'none';
}

// ── View 4: Detalhe do Designer ───────────────────────────────────────────────
function openDesignerDetalhe(card) {
    const name  = card.getAttribute('data-designer-name');
    const role  = card.getAttribute('data-designer-role');
    const photo = card.getAttribute('data-designer-photo');
    const squad = card.getAttribute('data-designer-squad') || '';
    let clientes = [];

    try {
        clientes = JSON.parse(card.getAttribute('data-designer-clientes-json') || '[]');
    } catch (e) {
        console.error('Erro ao parsear clientes do designer:', e);
    }

    _clientesDetalheAtual = clientes;
    _clientesBaseAtual    = clientes.map(c => ({ nome: c.nome, projeto_id: c.projeto_id }));
    _designerEmailAtual   = card.getAttribute('data-designer-email') || '';

    document.getElementById('detalhe-nome').textContent  = name;
    document.getElementById('detalhe-cargo').textContent = squad ? `${role} · ${squad}` : role;

    const avatarEl = document.getElementById('detalhe-avatar');
    avatarEl.innerHTML = photo
        ? `<img src="static/images/profile_pictures/${photo}" alt="${name}" style="width:100%;height:100%;object-fit:cover;border-radius:inherit;">`
        : `<i class="fa-solid fa-user-tie"></i>`;

    // Totais por categoria
    let criC=0, criE=0, vidC=0, vidE=0, lpC=0, lpE=0;
    clientes.forEach(c => {
        criC += c.criativos_c || 0; criE += c.criativos_e || 0;
        vidC += c.videos_c    || 0; vidE += c.videos_e    || 0;
        lpC  += c.lps_c       || 0; lpE  += c.lps_e       || 0;
    });
    const totalC = criC + vidC + lpC;
    const totalE = criE + vidE + lpE;
    const pct    = totalC > 0 ? Math.round((totalE / totalC) * 100) : 0;

    document.getElementById('detalhe-kpi-criativos').textContent = `${criE}/${criC}`;
    document.getElementById('detalhe-kpi-videos').textContent    = `${vidE}/${vidC}`;
    document.getElementById('detalhe-kpi-lps').textContent       = `${lpE}/${lpC}`;

    const kpiPct = document.getElementById('detalhe-kpi-conclusao');
    kpiPct.textContent  = `${pct}%`;
    kpiPct.style.color  = pct >= 80 ? '#22c55e' : pct >= 50 ? '#f59e0b' : '#ef4444';

    document.querySelectorAll('.criativa-view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.criativa-nav-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('criativa-view-designer-detalhe').classList.add('active');

    renderChartPorCliente(clientes);
    requestAnimationFrame(() => {
        renderChartContratadoEntregue(criC, criE, vidC, vidE, lpC, lpE);
        renderChartConclusao(pct);
    });
}

// ── Renderização da tabela de clientes ────────────────────────────────────────
function renderChartPorCliente(clientes) {
    const tbody = document.getElementById('detalhe-clientes-tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!clientes.length) {
        tbody.innerHTML = `<tr><td colspan="10" style="text-align:center;color:var(--text-muted);padding:1.5rem;">Nenhum cliente vinculado.</td></tr>`;
        return;
    }

    const isCoordenador = _isCoordinador();

    // Mostra/esconde coluna de contratados para coordenadores
    const thContratados = document.getElementById('th-contratados');
    if (thContratados) thContratados.style.display = isCoordenador ? '' : 'none';

    clientes.forEach(c => {
        const val = v => (v != null && v !== undefined) ? v : '—';
        const row = document.createElement('tr');

        // Mapa categoria → campo contratado (para verificar limite)
        const limiteMap = { criativos: c.criativos_c, lp: c.lps_c, videos: c.videos_c };

        // Célula de entregue com +/- (o botão + fica desabilitado se atingiu o limite)
        const makeEntregueCell = (categoria, valor) => {
            const nomeSeguro  = (c.nome || '').replace(/"/g, '&quot;');
            const limite      = limiteMap[categoria] || 0;
            const atingiuMax  = limite > 0 && (valor || 0) >= limite;
            const atingiuMin  = (valor || 0) <= 0;
            return `<td class="text-entregue cell-entregue">
                <div class="entregue-controls">
                    <button class="btn-delta btn-minus${atingiuMin ? ' btn-disabled' : ''}"
                        data-proj-id="${c.projeto_id}"
                        data-cliente="${nomeSeguro}"
                        data-categoria="${categoria}"
                        data-delta="-1"
                        ${atingiuMin ? 'disabled' : ''}>−</button>
                    <span>${val(valor)}</span>
                    <button class="btn-delta btn-plus${atingiuMax ? ' btn-disabled' : ''}"
                        data-proj-id="${c.projeto_id}"
                        data-cliente="${nomeSeguro}"
                        data-categoria="${categoria}"
                        data-delta="1"
                        ${atingiuMax ? 'disabled' : ''}>+</button>
                </div>
            </td>`;
        };

        // Célula de link
        const linkUrl = c.link_criativos || '';
        const linkCell = `<td class="cell-link-criativos">
            ${linkUrl
                ? `<a href="${linkUrl.replace(/"/g, '&quot;')}" target="_blank" rel="noopener"
                       class="criativa-btn-icon" title="Abrir criativos" style="margin-right:4px;">
                       <i class="fas fa-external-link-alt"></i>
                   </a>`
                : ''}
            <button class="criativa-btn-icon criativa-btn-link-edit"
                data-proj-id="${c.projeto_id}"
                title="${linkUrl ? 'Editar link' : 'Adicionar link'}">
                <i class="fas fa-${linkUrl ? 'pencil-alt' : 'link'}"></i>
            </button>
        </td>`;

        // Coluna de contratados (última, só para coordenadores)
        const acaoCell = isCoordenador
            ? `<td style="text-align:center;">
                <button class="criativa-btn-icon criativa-btn-contratados"
                    data-proj-id="${c.projeto_id}"
                    title="Configurar contratados">
                    <i class="fas fa-sliders-h"></i>
                </button>
               </td>`
            : '<td style="display:none;"></td>';

        row.innerHTML = `
            <td class="cell-cliente"><strong>${c.nome}</strong></td>
            <td class="text-contratado">${val(c.criativos_c)}</td>
            ${makeEntregueCell('criativos', c.criativos_e)}
            <td class="text-contratado">${val(c.lps_c)}</td>
            ${makeEntregueCell('lp', c.lps_e)}
            <td class="text-contratado">${val(c.videos_c)}</td>
            ${makeEntregueCell('videos', c.videos_e)}
            ${linkCell}
            ${acaoCell}
        `;
        tbody.appendChild(row);
    });
}

// ── +/- Entregas direto na tabela ────────────────────────────────────────────
async function deltaEntregue(projId, clienteNome, categoria, delta) {
    const hoje = new Date();
    if (_anoSelecionado > hoje.getFullYear() ||
        (_anoSelecionado === hoje.getFullYear() && _mesSelecionado > hoje.getMonth() + 1)) {
        showToast('Não é possível registrar entregas em meses futuros.', 'error');
        return;
    }

    const cliente = _clientesDetalheAtual.find(c => String(c.projeto_id) === String(projId));
    if (!cliente) return;

    const campoLocal = categoria === 'lp' ? 'lps_e' : `${categoria}_e`;
    const campoContratado = { criativos: 'criativos_c', lp: 'lps_c', videos: 'videos_c' }[categoria];
    const categoriaLabel  = { criativos: 'Criativos', lp: 'LPs', videos: 'Vídeos' }[categoria] || categoria;
    const limite     = cliente[campoContratado] || 0;
    const valorAtual = cliente[campoLocal] || 0;
    const novoValor  = Math.max(0, valorAtual + delta);
    if (novoValor === valorAtual) return;

    // Bloqueia se ultrapassar o limite contratado
    if (delta > 0 && limite > 0 && novoValor > limite) {
        showToast(`Limite atingido! ${categoriaLabel} contratados: ${limite}.`, 'error');
        return;
    }

    // Atualização otimista
    cliente[campoLocal] = novoValor;
    renderChartPorCliente(_clientesDetalheAtual);
    atualizarKpisDetalhe(_clientesDetalheAtual);

    try {
        const resp = await fetch('/api/criativa/entregas/entregues', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email_investidor: _designerEmailAtual,
                mes: _mesSelecionado,
                ano: _anoSelecionado,
                projeto_id: projId,
                cliente: clienteNome,
                categoria,
                valor: novoValor,
            })
        });
        if (!resp.ok) {
            cliente[campoLocal] = valorAtual;
            renderChartPorCliente(_clientesDetalheAtual);
            atualizarKpisDetalhe(_clientesDetalheAtual);
            const err = await resp.json();
            showToast(err.error || 'Erro ao salvar.', 'error');
        }
    } catch {
        cliente[campoLocal] = valorAtual;
        renderChartPorCliente(_clientesDetalheAtual);
        atualizarKpisDetalhe(_clientesDetalheAtual);
        showToast('Erro de conexão.', 'error');
    }
}

// ── Modal: Link de Criativos ──────────────────────────────────────────────────
function openLinkModal(cliente) {
    document.getElementById('modal-link-cliente').textContent = `Cliente: ${cliente.nome}`;
    document.getElementById('lc-projeto-id').value   = cliente.projeto_id;
    document.getElementById('lc-cliente-nome').value = cliente.nome;
    document.getElementById('lc-link').value         = cliente.link_criativos || '';
    document.getElementById('modal-link-criativo').style.display = 'flex';
}

function closeLinkModal() {
    document.getElementById('modal-link-criativo').style.display = 'none';
    document.getElementById('form-link-criativo').reset();
}

async function saveLinkCriativo(event) {
    event.preventDefault();
    const projetoId   = document.getElementById('lc-projeto-id').value;
    const clienteNome = document.getElementById('lc-cliente-nome').value;
    const link        = document.getElementById('lc-link').value.trim();

    const btn = document.getElementById('btn-save-link');
    btn.disabled = true;
    btn.textContent = 'Salvando...';

    try {
        const resp = await fetch('/api/criativa/entregas/link', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email_investidor: _designerEmailAtual,
                mes: _mesSelecionado,
                ano: _anoSelecionado,
                projeto_id: projetoId,
                cliente: clienteNome,
                link,
            })
        });

        if (!resp.ok) {
            const err = await resp.json();
            showToast(err.error || 'Erro ao salvar link.', 'error');
            return;
        }

        const cliente = _clientesDetalheAtual.find(c => String(c.projeto_id) === String(projetoId));
        if (cliente) cliente.link_criativos = link;

        renderChartPorCliente(_clientesDetalheAtual);
        closeLinkModal();
        showToast('Link salvo com sucesso!', 'success');
    } catch {
        showToast('Erro de conexão.', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Salvar';
    }
}

// ── Modal: Configurar Contratados (Coordenador) ───────────────────────────────
function openContratadosModal(cliente) {
    document.getElementById('modal-contratados-cliente').textContent = `Cliente: ${cliente.nome}`;
    document.getElementById('mc-projeto-id').value   = cliente.projeto_id;
    document.getElementById('mc-cliente-nome').value = cliente.nome;
    document.getElementById('mc-criativos').value    = cliente.criativos_c || 0;
    document.getElementById('mc-videos').value       = cliente.videos_c    || 0;
    document.getElementById('mc-lp').value           = cliente.lps_c       || 0;
    document.getElementById('modal-contratados').style.display = 'flex';
}

function closeContratadosModal() {
    document.getElementById('modal-contratados').style.display = 'none';
    document.getElementById('form-contratados').reset();
}

async function saveContratados(event) {
    event.preventDefault();
    const projetoId   = document.getElementById('mc-projeto-id').value;
    const clienteNome = document.getElementById('mc-cliente-nome').value;
    const criativos   = parseInt(document.getElementById('mc-criativos').value);
    const videos      = parseInt(document.getElementById('mc-videos').value);
    const lp          = parseInt(document.getElementById('mc-lp').value);

    const btn = document.getElementById('btn-save-contratados');
    btn.disabled = true;
    btn.textContent = 'Salvando...';

    try {
        const resp = await fetch('/api/criativa/entregas/contratados', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email_investidor: _designerEmailAtual,
                mes: _mesSelecionado,
                ano: _anoSelecionado,
                projeto_id: projetoId,
                cliente: clienteNome,
                criativos, videos, lp,
            })
        });

        if (!resp.ok) {
            const err = await resp.json();
            showToast(err.error || 'Erro ao salvar contratados.', 'error');
            return;
        }

        // Atualiza estado local
        const cliente = _clientesDetalheAtual.find(c => String(c.projeto_id) === String(projetoId));
        if (cliente) {
            cliente.criativos_c = criativos;
            cliente.videos_c    = videos;
            cliente.lps_c       = lp;
        }

        renderChartPorCliente(_clientesDetalheAtual);
        atualizarKpisDetalhe(_clientesDetalheAtual);
        closeContratadosModal();
        showToast(`Contratados de ${clienteNome} atualizados.`, 'success');
    } catch (e) {
        console.error(e);
        showToast('Erro de conexão.', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Salvar';
    }
}

// ── Atualiza KPIs e gráficos ──────────────────────────────────────────────────
function atualizarKpisDetalhe(clientes) {
    let criC=0, criE=0, vidC=0, vidE=0, lpC=0, lpE=0;
    clientes.forEach(c => {
        criC += c.criativos_c || 0; criE += c.criativos_e || 0;
        vidC += c.videos_c    || 0; vidE += c.videos_e    || 0;
        lpC  += c.lps_c       || 0; lpE  += c.lps_e       || 0;
    });
    const total = criC + vidC + lpC;
    const pct   = total > 0 ? Math.round(((criE + vidE + lpE) / total) * 100) : 0;

    document.getElementById('detalhe-kpi-criativos').textContent = `${criE}/${criC}`;
    document.getElementById('detalhe-kpi-videos').textContent    = `${vidE}/${vidC}`;
    document.getElementById('detalhe-kpi-lps').textContent       = `${lpE}/${lpC}`;

    const kpiPct = document.getElementById('detalhe-kpi-conclusao');
    kpiPct.textContent = `${pct}%`;
    kpiPct.style.color = pct >= 80 ? '#22c55e' : pct >= 50 ? '#f59e0b' : '#ef4444';

    setTimeout(() => {
        renderChartContratadoEntregue(criC, criE, vidC, vidE, lpC, lpE);
        renderChartConclusao(pct);
    }, 50);
}

// ── Gráficos (Chart.js) ───────────────────────────────────────────────────────
function renderChartContratadoEntregue(criC, criE, vidC, vidE, lpC, lpE) {
    if (chartContratadoEntregue) chartContratadoEntregue.destroy();

    const ctx          = document.getElementById('chart-contratado-entregue').getContext('2d');
    const isTemaClaro  = document.body.classList.contains('tema-claro');
    const textColor    = isTemaClaro ? '#374151' : '#e5e7eb';
    const gridColor    = isTemaClaro ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.08)';

    // Escala Y dinâmica: máximo entre contratados, arredondado para cima em múltiplos de 10
    const maxContratado = Math.max(criC, vidC, lpC, 1);
    const yMax = Math.ceil(maxContratado / 10) * 10;

    chartContratadoEntregue = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Criativos', 'Vídeos', 'Landing Pages'],
            datasets: [
                {
                    label: 'Contratado',
                    data: [criC, vidC, lpC],
                    backgroundColor: 'rgba(239,68,68,0.7)',
                    borderColor: '#ef4444',
                    borderWidth: 2,
                    borderRadius: 6,
                    borderSkipped: false,
                },
                {
                    label: 'Entregue',
                    data: [criE, vidE, lpE],
                    backgroundColor: 'rgba(34,197,94,0.7)',
                    borderColor: '#22c55e',
                    borderWidth: 2,
                    borderRadius: 6,
                    borderSkipped: false,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: textColor,
                        font: { family: 'Poppins', size: 12, weight: '500' },
                        usePointStyle: true,
                        pointStyle: 'rectRounded',
                        padding: 20
                    }
                },
                tooltip: {
                    backgroundColor: isTemaClaro ? '#1f2937' : '#1a1a2e',
                    titleFont: { family: 'Poppins', size: 13 },
                    bodyFont: { family: 'Poppins', size: 12 },
                    padding: 12,
                    cornerRadius: 8,
                }
            },
            scales: {
                x: {
                    ticks: { color: textColor, font: { family: 'Poppins', size: 12 } },
                    grid: { display: false }
                },
                y: {
                    beginAtZero: true,
                    max: yMax,
                    ticks: { color: textColor, font: { family: 'Poppins', size: 11 }, stepSize: 10 },
                    grid: { color: gridColor }
                }
            }
        }
    });
}

function renderChartConclusao(pct) {
    if (chartConclusao) chartConclusao.destroy();

    const ctx         = document.getElementById('chart-conclusao').getContext('2d');
    const isTemaClaro = document.body.classList.contains('tema-claro');
    const textColor   = isTemaClaro ? '#374151' : '#e5e7eb';

    let corPrincipal = '#22c55e';
    if (pct < 50)      corPrincipal = '#ef4444';
    else if (pct < 80) corPrincipal = '#f59e0b';

    chartConclusao = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Entregue', 'Pendente'],
            datasets: [{
                data: [pct, 100 - pct],
                backgroundColor: [
                    corPrincipal,
                    isTemaClaro ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.06)'
                ],
                borderColor: ['transparent', 'transparent'],
                borderWidth: 0,
                cutout: '78%',
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: isTemaClaro ? '#1f2937' : '#1a1a2e',
                    titleFont: { family: 'Poppins', size: 13 },
                    bodyFont: { family: 'Poppins', size: 12 },
                    padding: 12,
                    cornerRadius: 8,
                    callbacks: { label: ctx => ctx.label + ': ' + ctx.raw + '%' }
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
                c.textAlign    = 'center';
                c.textBaseline = 'middle';
                c.font         = 'bold 2rem Poppins';
                c.fillStyle    = corPrincipal;
                c.fillText(pct + '%', cx, cy - 8);
                c.font      = '500 0.75rem Poppins';
                c.fillStyle = textColor;
                c.fillText('Concluído', cx, cy + 22);
                c.restore();
            }
        }]
    });
}
