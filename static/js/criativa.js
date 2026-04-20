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
    // Roteia cargos operacionais para a view própria
    const funcao = card.getAttribute('data-designer-funcao') || '';
    if (funcao === 'Account' || funcao === 'Gestor de Tráfego') {
        openOperacionalDetalhe(card);
        return;
    }

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


// ═══════════════════════════════════════════════════════════════════════════════
// MÓDULO OPERACIONAL — Account / Gestor de Tráfego
// ═══════════════════════════════════════════════════════════════════════════════

const OP_ENTREGAS_CONFIG = {
    'Account': [
        { tipo: 'relatorio_mensal', label: 'Relatório Mensal', icone: 'fa-file-alt',       padrao: 1, link: true  },
        { tipo: 'planner_monday',   label: 'Planner Monday',   icone: 'fa-calendar-check', padrao: 4, link: false },
        { tipo: 'csat_checkin',     label: 'CSAT Check-in',    icone: 'fa-comments',        padrao: 4, link: false },
        { tipo: 'forecast',         label: 'Forecasting',       icone: 'fa-chart-line',      padrao: 1, link: true  },
    ],
    'Gestor de Tráfego': [
        { tipo: 'relatorio_mensal', label: 'Relatório Mensal',       icone: 'fa-file-alt',       padrao: 1, link: true  },
        { tipo: 'kpi',              label: 'KPI',                     icone: 'fa-tachometer-alt', padrao: 1, link: true  },
        { tipo: 'plano_midia',      label: 'Plano de Mídia',          icone: 'fa-bullhorn',       padrao: 1, link: false },
        { tipo: 'doc_otimizacao',   label: 'Documento de Otimização', icone: 'fa-sliders-h',      padrao: 4, link: false },
    ],
};

// ── Estado em memória ─────────────────────────────────────────────────────────
let _opFuncao   = '';
let _opNome     = '';
let _opCargo    = '';
let _opPhoto    = '';
let _opEmail    = '';
let _opClientes = [];
let _opProjIdEditando  = null;
let _opLinkEditando    = { projId: null, tipo: null };

const _opMetas  = {};  // { pipefyId: { tipo: count } }
const _opFeitos = {};  // { pipefyId: { tipo: count } }
const _opLinks  = {};  // { pipefyId: { tipo: url   } }

let _chartOpBarras    = null;
let _chartOpConclusao = null;

// ── Helpers ───────────────────────────────────────────────────────────────────
function _getOpMeta(pipefyId, tipo) {
    const custom = (_opMetas[String(pipefyId)] || {})[tipo];
    if (custom !== undefined) return custom;
    const cfg  = OP_ENTREGAS_CONFIG[_opFuncao] || [];
    const item = cfg.find(d => d.tipo === tipo);
    return item ? item.padrao : 1;
}

function _getOpFeito(pipefyId, tipo) {
    return ((_opFeitos[String(pipefyId)] || {})[tipo]) || 0;
}

function _opCor(pct) {
    return pct >= 80 ? '#22c55e' : pct >= 50 ? '#f59e0b' : '#ef4444';
}

// ── Abrir detalhe operacional ─────────────────────────────────────────────────
function openOperacionalDetalhe(card) {
    const name   = card.getAttribute('data-designer-name');
    const role   = card.getAttribute('data-designer-role');
    const funcao = card.getAttribute('data-designer-funcao');
    const photo  = card.getAttribute('data-designer-photo');
    const squad  = card.getAttribute('data-designer-squad') || '';
    const email  = card.getAttribute('data-designer-email') || '';
    let clientes = [];

    try {
        clientes = JSON.parse(card.getAttribute('data-designer-clientes-json') || '[]');
    } catch (e) { console.error(e); }

    _opFuncao   = funcao;
    _opNome     = name;
    _opEmail    = email;
    _opCargo    = squad ? `${role} · ${squad}` : role;
    _opPhoto    = photo;
    _opClientes = clientes;

    // Limpa feitos anteriores deste usuário
    const tipos = OP_ENTREGAS_CONFIG[funcao] || [];
    clientes.forEach(c => {
        const pid = String(c.projeto_id);
        if (_opFeitos[pid]) {
            tipos.forEach(d => { delete _opFeitos[pid][d.tipo]; });
        }
    });

    document.getElementById('op-detalhe-nome').textContent  = name;
    document.getElementById('op-detalhe-cargo').textContent = _opCargo;

    const avatarEl = document.getElementById('op-detalhe-avatar');
    avatarEl.innerHTML = photo
        ? `<img src="static/images/profile_pictures/${photo}" alt="${name}" style="width:100%;height:100%;object-fit:cover;border-radius:inherit;">`
        : `<i class="fa-solid fa-user-tie"></i>`;

    document.querySelectorAll('.criativa-view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.criativa-nav-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('criativa-view-operacional-detalhe').classList.add('active');

    _renderOpView();

    // Carrega estado real das entregas do backend
    if (email) {
        const mes = _mesSelecionado;
        const ano = _anoSelecionado;
        fetch(`/api/criativa/op-deliveries/${encodeURIComponent(email)}/${mes}/${ano}`)
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (!data) return;
                // data: { "proj_id": { "delivery_type": "completed"|"pending" } }
                Object.entries(data).forEach(([pid, tipos_status]) => {
                    Object.entries(tipos_status).forEach(([tipo, status]) => {
                        const meta = _getOpMeta(pid, tipo);
                        if (!_opFeitos[pid]) _opFeitos[pid] = {};
                        _opFeitos[pid][tipo] = status === 'completed' ? meta : 0;
                    });
                });
                _renderOpView();
            })
            .catch(() => {}); // falha silenciosa — mantém estado vazio
    }
}

// ── Render completo ───────────────────────────────────────────────────────────
function _renderOpView() {
    const tipos    = OP_ENTREGAS_CONFIG[_opFuncao] || [];
    const clientes = _opClientes;

    let totalMeta = 0, totalFeito = 0, totalFeeFeito = 0;
    let hasFee = false;

    const usdRate = (window.APP_CONFIG && window.APP_CONFIG.usdRate) || 5.7;

    clientes.forEach(c => {
        const pid    = String(c.projeto_id);
        const fee    = parseFloat(c.fee || 0);
        const moeda  = (c.moeda || 'BRL').toUpperCase();
        const feeBRL = moeda === 'USD' ? fee * usdRate : fee;
        if (fee > 0) hasFee = true;

        let projMeta = 0, projFeito = 0;
        tipos.forEach(d => {
            const m = _getOpMeta(pid, d.tipo);
            const f = Math.min(_getOpFeito(pid, d.tipo), m);
            projMeta   += m;
            projFeito  += f;
            totalMeta  += m;
            totalFeito += f;
        });

        // Fee proporcional: cada projeto contribui com sua própria % de conclusão (em BRL)
        const projPct = projMeta > 0 ? projFeito / projMeta : 0;
        totalFeeFeito += feeBRL * projPct;
    });

    const pct      = totalMeta > 0 ? Math.round((totalFeito / totalMeta) * 100) : 0;
    const feeFeito = hasFee ? totalFeeFeito : null;

    _renderOpKpis(totalMeta, totalFeito, pct, feeFeito);
    _renderOpCharts(tipos, clientes, pct);
    _renderOpProjetos(tipos, clientes);
}

// ── KPIs ──────────────────────────────────────────────────────────────────────
function _renderOpKpis(totalMeta, totalFeito, pct, feeFeito) {
    const cor    = _opCor(pct);
    const feeStr = feeFeito !== null
        ? `R$ ${feeFeito.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`
        : '—';

    document.getElementById('op-kpi-total').textContent = totalMeta;
    document.getElementById('op-kpi-feito').textContent = `${totalFeito} / ${totalMeta}`;

    const pctEl = document.getElementById('op-kpi-pct');
    pctEl.textContent = `${pct}%`;
    pctEl.style.color = cor;

    const feeEl = document.getElementById('op-kpi-fee');
    feeEl.textContent = feeStr;
    feeEl.style.color = feeFeito !== null ? cor : '';
}

// ── Gráficos ──────────────────────────────────────────────────────────────────
function _renderOpCharts(tipos, clientes, pct) {
    const isTemaClaro = document.body.classList.contains('tema-claro');
    const textColor   = isTemaClaro ? '#374151' : '#e5e7eb';
    const gridColor   = isTemaClaro ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.08)';
    const cor         = _opCor(pct);

    // ── Barras: Meta vs Realizado por tipo ────────────────────────────────────
    if (_chartOpBarras) _chartOpBarras.destroy();
    const ctxBar = document.getElementById('chart-op-barras')?.getContext('2d');
    if (ctxBar) {
        const labels      = tipos.map(d => d.label);
        const metaTotais  = tipos.map(d =>
            clientes.reduce((s, c) => s + _getOpMeta(String(c.projeto_id), d.tipo), 0));
        const feitoTotais = tipos.map(d =>
            clientes.reduce((s, c) => s + Math.min(
                _getOpFeito(String(c.projeto_id), d.tipo),
                _getOpMeta(String(c.projeto_id), d.tipo)
            ), 0));
        const yMax = Math.ceil(Math.max(...metaTotais, 1) / 5) * 5;

        _chartOpBarras = new Chart(ctxBar, {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    { label: 'Meta',      data: metaTotais,  backgroundColor: 'rgba(239,68,68,0.7)',  borderColor: '#ef4444', borderWidth: 2, borderRadius: 6, borderSkipped: false },
                    { label: 'Realizado', data: feitoTotais, backgroundColor: 'rgba(34,197,94,0.7)',  borderColor: '#22c55e', borderWidth: 2, borderRadius: 6, borderSkipped: false },
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { color: textColor, font: { family: 'Poppins', size: 12, weight: '500' }, usePointStyle: true, pointStyle: 'rectRounded', padding: 20 } },
                    tooltip: { backgroundColor: isTemaClaro ? '#1f2937' : '#1a1a2e', titleFont: { family: 'Poppins', size: 13 }, bodyFont: { family: 'Poppins', size: 12 }, padding: 12, cornerRadius: 8 }
                },
                scales: {
                    x: { ticks: { color: textColor, font: { family: 'Poppins', size: 11 } }, grid: { display: false } },
                    y: { beginAtZero: true, max: yMax, ticks: { color: textColor, font: { family: 'Poppins', size: 11 }, stepSize: Math.max(1, Math.floor(yMax / 5)) }, grid: { color: gridColor } }
                }
            }
        });
    }

    // ── Doughnut: Taxa de Conclusão ───────────────────────────────────────────
    if (_chartOpConclusao) _chartOpConclusao.destroy();
    const ctxDo = document.getElementById('chart-op-conclusao')?.getContext('2d');
    if (ctxDo) {
        _chartOpConclusao = new Chart(ctxDo, {
            type: 'doughnut',
            data: {
                labels: ['Realizado', 'Pendente'],
                datasets: [{
                    data: [pct, 100 - pct],
                    backgroundColor: [cor, isTemaClaro ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.06)'],
                    borderColor: ['transparent', 'transparent'], borderWidth: 0, cutout: '78%', borderRadius: 8
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { backgroundColor: isTemaClaro ? '#1f2937' : '#1a1a2e', titleFont: { family: 'Poppins', size: 13 }, bodyFont: { family: 'Poppins', size: 12 }, padding: 12, cornerRadius: 8, callbacks: { label: ctx => ctx.label + ': ' + ctx.raw + '%' } }
                }
            },
            plugins: [{
                id: 'textoCentralOp',
                afterDraw(chart) {
                    const { ctx: c, chartArea } = chart;
                    const cx = (chartArea.left + chartArea.right)  / 2;
                    const cy = (chartArea.top  + chartArea.bottom) / 2;
                    c.save();
                    c.textAlign = 'center'; c.textBaseline = 'middle';
                    c.font = 'bold 2rem Poppins'; c.fillStyle = cor;
                    c.fillText(pct + '%', cx, cy - 8);
                    c.font = '500 0.75rem Poppins'; c.fillStyle = textColor;
                    c.fillText('Concluído', cx, cy + 22);
                    c.restore();
                }
            }]
        });
    }
}

// ── Cards por projeto ─────────────────────────────────────────────────────────
function _renderOpProjetos(tipos, clientes) {
    const container = document.getElementById('op-projetos-container');
    if (!container) return;

    const isCoordenador = _isCoordinador();
    container.innerHTML = '';

    if (!clientes.length) {
        container.innerHTML = `<p style="color:var(--text-muted);padding:1rem;">Nenhum cliente vinculado.</p>`;
        return;
    }

    clientes.forEach(c => {
        const pid    = String(c.projeto_id);
        const fee    = parseFloat(c.fee || 0);
        const moeda  = (c.moeda || 'BRL').toUpperCase();
        const isUSD  = moeda === 'USD';
        const simbol = isUSD ? 'US$' : 'R$';
        const feeStr = fee > 0
            ? `${simbol} ${fee.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`
            : '—';

        // Totais do projeto — cada tipo de entrega vale 25% fixo
        const PESO_POR_TIPO = 25;
        const projPct = tipos.length > 0 ? Math.round(tipos.reduce((s, d) => {
            const meta  = _getOpMeta(pid, d.tipo);
            const feito = Math.min(_getOpFeito(pid, d.tipo), meta);
            return s + (meta > 0 ? (feito / meta) * PESO_POR_TIPO : 0);
        }, 0)) : 0;
        const projCor      = _opCor(projPct);
        // Proporcional exibido na moeda original do projeto
        const projFeeFeito = fee > 0 ? fee * projPct / 100 : null;
        const projFeeStr   = projFeeFeito !== null
            ? ` &nbsp;·&nbsp; Proporcional: <strong style="color:${projCor};">${simbol} ${projFeeFeito.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</strong>`
            : '';

        // Rows de entrega
        const deliveryRows = tipos.map(d => {
            const meta   = _getOpMeta(pid, d.tipo);
            const feito  = _getOpFeito(pid, d.tipo);
            const clamp  = Math.min(feito, meta);
            const rowPct = meta > 0 ? Math.round((clamp / meta) * 100) : 0;
            const rowCor = _opCor(rowPct);
            // cada tipo vale 25% fixo, independente da meta individual
            const pesoPorEntrega  = meta > 0 ? PESO_POR_TIPO / meta : PESO_POR_TIPO;
            const contribuicao    = clamp * pesoPorEntrega;
            const contribuicaoFmt = Number.isInteger(contribuicao) ? contribuicao : contribuicao.toFixed(2);
            const maxed  = feito >= meta;
            const zeroed = feito <= 0;

            // Botão de link (apenas para entregas com link: true)
            const linkUrl   = ((_opLinks[pid] || {})[d.tipo]) || '';
            const linkBtns  = d.link ? `
                <span style="width:1px;height:20px;background:var(--border-color);margin:0 2px;"></span>
                ${linkUrl ? `<a href="${linkUrl.replace(/"/g, '&quot;')}" target="_blank" rel="noopener"
                    class="criativa-btn-icon" title="Abrir planilha" style="font-size:0.8rem;">
                    <i class="fas fa-external-link-alt"></i></a>` : ''}
                <button class="criativa-btn-icon" title="${linkUrl ? 'Editar link' : 'Adicionar link da planilha'}"
                    style="font-size:0.8rem;"
                    onclick="openOpLinkModal('${pid}','${d.tipo}','${d.label.replace(/'/g, "\\'")}')">
                    <i class="fas fa-${linkUrl ? 'pencil-alt' : 'link'}"></i>
                </button>` : '';

            return `
            <div class="op-entrega-row">
                <div class="op-entrega-info">
                    <i class="fas ${d.icone}" style="color:#D61616;width:16px;text-align:center;flex-shrink:0;margin-top:2px;"></i>
                    <div class="op-entrega-texts">
                        <span class="op-entrega-label">${d.label}</span>
                        <span class="op-entrega-peso">Peso: <strong style="color:var(--text-main)">25%</strong>${meta > 1 ? ` <span style="opacity:0.6;">(${pesoPorEntrega % 1 === 0 ? pesoPorEntrega : pesoPorEntrega.toFixed(2)}% × ${meta})</span>` : ''} &nbsp;·&nbsp; <strong style="color:${rowCor}">${contribuicaoFmt}%</strong> conquistado</span>
                    </div>
                </div>
                <div class="op-entrega-controls">
                    ${linkBtns}
                    <button class="btn-delta btn-minus${zeroed ? ' btn-disabled' : ''}"
                        onclick="opDelta('${pid}','${d.tipo}',-1)"
                        ${zeroed ? 'disabled' : ''}>−</button>
                    <span style="min-width:48px;text-align:center;font-weight:600;color:${rowCor};">${clamp}<span style="color:var(--text-muted);font-weight:400"> / ${meta}</span></span>
                    <button class="btn-delta btn-plus${maxed ? ' btn-disabled' : ''}"
                        onclick="opDelta('${pid}','${d.tipo}',1)"
                        ${maxed ? 'disabled' : ''}>+</button>
                </div>
                <div class="op-entrega-bar-wrap">
                    <div class="op-entrega-bar" style="width:${rowPct}%;background:${rowCor};box-shadow:0 0 6px ${rowCor}44;"></div>
                </div>
            </div>`;
        }).join('');

        const cardEl = document.createElement('div');
        cardEl.className = 'criativa-table-card';
        cardEl.style.cssText = 'padding:1.5rem;';
        cardEl.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.25rem;flex-wrap:wrap;gap:0.75rem;">
                <div>
                    <h4 style="margin:0;font-size:1rem;color:var(--text-main);">${c.nome}</h4>
                    <span style="font-size:0.8rem;color:var(--text-muted);">Fee: <strong style="color:var(--text-sub);">${feeStr}</strong>${projFeeStr}</span>
                </div>
                <div style="display:flex;align-items:center;gap:0.75rem;">
                    <div style="font-size:1.4rem;font-weight:700;color:${projCor};">${projPct}%</div>
                    ${isCoordenador ? `<button class="criativa-btn-icon" title="Configurar metas" onclick="openOpMetasModal('${pid}','${c.nome.replace(/'/g, "\\'")}')"><i class="fas fa-sliders-h"></i></button>` : ''}
                </div>
            </div>
            <div class="op-entregas-lista">${deliveryRows}</div>
        `;
        container.appendChild(cardEl);
    });
}

// ── Delta (+ / -) ─────────────────────────────────────────────────────────────
function opDelta(projId, tipo, delta) {
    const pid   = String(projId);
    const meta  = _getOpMeta(pid, tipo);
    const atual = _getOpFeito(pid, tipo);
    const novo  = Math.min(Math.max(0, atual + delta), meta);
    if (novo === atual) return;

    if (!_opFeitos[pid]) _opFeitos[pid] = {};
    _opFeitos[pid][tipo] = novo;
    _renderOpView();

    // Persiste no backend se coordenador
    if (_isCoordinador() && _opEmail) {
        const mes = _mesSelecionado;
        const ano = _anoSelecionado;
        fetch('/api/criativa/op-deliveries', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: _opEmail,
                client_id: parseInt(pid),
                delivery_type: tipo,
                mes, ano,
                status: novo >= meta ? 'completed' : 'pending',
            }),
        }).catch(() => {});
    }
}

// ── Modal: configurar metas por projeto ───────────────────────────────────────
function openOpMetasModal(projId, projNome) {
    _opProjIdEditando = String(projId);
    document.getElementById('modal-op-metas-projeto').textContent = `Cliente: ${projNome}`;

    const tipos = OP_ENTREGAS_CONFIG[_opFuncao] || [];
    document.getElementById('op-meta-fields').innerHTML = tipos.map(d => {
        const val = _getOpMeta(_opProjIdEditando, d.tipo);
        return `
        <div style="display:grid;grid-template-columns:1fr auto;align-items:center;gap:1rem;
                    padding:0.75rem 1rem;background:rgba(255,255,255,0.02);
                    border:1px solid var(--border-color);border-radius:8px;">
            <div style="display:flex;align-items:center;gap:0.5rem;">
                <i class="fas ${d.icone}" style="color:#D61616;width:16px;text-align:center;"></i>
                <span style="font-size:0.87rem;font-weight:600;">${d.label}</span>
                <span style="font-size:0.7rem;color:var(--text-muted);">(padrão: ${d.padrao})</span>
            </div>
            <input type="number" class="op-meta-input" data-tipo="${d.tipo}"
                   value="${val}" min="1" max="31"
                   style="width:64px;text-align:center;background:var(--card-bg);
                          border:1px solid var(--border-color);border-radius:6px;
                          color:var(--text-main);font-family:Poppins,sans-serif;
                          font-size:1rem;font-weight:600;padding:0.3rem 0.4rem;outline:none;">
        </div>`;
    }).join('');

    document.getElementById('modal-op-metas').style.display = 'flex';
}

function closeOpMetasModal() {
    document.getElementById('modal-op-metas').style.display = 'none';
    _opProjIdEditando = null;
}

function saveOpMetas() {
    if (!_opProjIdEditando) return;

    // Salva metas por tipo
    if (!_opMetas[_opProjIdEditando]) _opMetas[_opProjIdEditando] = {};
    document.querySelectorAll('#op-meta-fields .op-meta-input').forEach(inp => {
        const val = parseInt(inp.value, 10);
        if (!isNaN(val) && val >= 1) _opMetas[_opProjIdEditando][inp.dataset.tipo] = val;
    });

    // Garante que feitos não excedem novas metas
    if (_opFeitos[_opProjIdEditando]) {
        (OP_ENTREGAS_CONFIG[_opFuncao] || []).forEach(d => {
            const meta  = _getOpMeta(_opProjIdEditando, d.tipo);
            const feito = _opFeitos[_opProjIdEditando][d.tipo] || 0;
            if (feito > meta) _opFeitos[_opProjIdEditando][d.tipo] = meta;
        });
    }

    closeOpMetasModal();
    _renderOpView();
    if (typeof showToast === 'function') showToast('Metas atualizadas!', 'success');
}

// ── Modal: link de planilha ───────────────────────────────────────────────────
function openOpLinkModal(projId, tipo, tipoLabel) {
    _opLinkEditando = { projId: String(projId), tipo };
    document.getElementById('modal-op-link-descricao').textContent = `Planilha: ${tipoLabel}`;
    document.getElementById('op-link-url').value = ((_opLinks[String(projId)] || {})[tipo]) || '';
    document.getElementById('modal-op-link').style.display = 'flex';
}

function closeOpLinkModal() {
    document.getElementById('modal-op-link').style.display = 'none';
    _opLinkEditando = { projId: null, tipo: null };
}

function saveOpLink() {
    const { projId, tipo } = _opLinkEditando;
    if (!projId || !tipo) return;
    const url = document.getElementById('op-link-url').value.trim();
    if (!_opLinks[projId]) _opLinks[projId] = {};
    _opLinks[projId][tipo] = url;
    closeOpLinkModal();
    _renderOpView();
    if (typeof showToast === 'function') showToast('Link salvo!', 'success');
}

// ── Fecha modais ao clicar no backdrop ────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const modalOp = document.getElementById('modal-op-metas');
    if (modalOp) modalOp.addEventListener('click', e => {
        if (e.target === e.currentTarget) closeOpMetasModal();
    });
    const modalLink = document.getElementById('modal-op-link');
    if (modalLink) modalLink.addEventListener('click', e => {
        if (e.target === e.currentTarget) closeOpLinkModal();
    });
});
