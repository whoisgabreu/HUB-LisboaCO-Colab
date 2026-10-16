/* Minha Agenda — agrega Tarefas (Ekyte) e Eventos (Google Agenda futura).
   Modo widget (rail do perfil) e modo página completa (/minha-agenda). */
(function () {
    function esc(s) {
        return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function hojeISO() {
        const d = new Date();
        return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
    }

    function dataISO(t) {
        return String(t.data || '').replace(/\//g, '-').slice(0, 10);
    }

    function badgeFonte(t) {
        if (t.fonte === 'google') return '<span class="agenda-fonte-badge google"><i class="fa-regular fa-calendar"></i> Evento</span>';
        return '<span class="agenda-fonte-badge"><i class="fa-solid fa-list-check"></i> Tarefa</span>';
    }

    function montarItem(t) {
        const titulo = esc(t.titulo || 'Sem título');
        const meta = [];
        if (t.rotulo) meta.push('<span>' + esc(t.rotulo) + '</span>');
        if (t.data) {
            const iso = dataISO(t);
            const atrasada = t.fonte === 'ekyte' && iso && iso < hojeISO();
            meta.push('<span><i class="fa-regular fa-calendar"></i> ' + esc(t.data) + '</span>' + (atrasada ? ' <span class="ekyte-prazo atrasado">Atrasada</span>' : ''));
        }
        if (t.sub) meta.push('<span><i class="fa-solid fa-layer-group"></i> ' + esc(t.sub) + '</span>');
        const metaHtml = meta.length ? '<div class="ekyte-task-meta">' + meta.join(' · ') + '</div>' : '';
        const rotuloLink = t.fonte === 'google' ? 'Abrir no Google' : 'Abrir no Ekyte';
        const link = t.link
            ? '<a class="ekyte-open" href="' + esc(t.link) + '" target="_blank" rel="noopener">' + rotuloLink + ' <i class="fa-solid fa-arrow-up-right-from-square"></i></a>'
            : '';
        return '<div class="ekyte-task"><div class="ekyte-task-titulo">' + badgeFonte(t) + ' ' + titulo + '</div>' + metaHtml + link + '</div>';
    }

    /* ── 1. WIDGET compacto (rail do perfil): só contadores ───────────── */
    async function carregarWidget() {
        const body = document.getElementById('agendaWidgetBody');
        if (!body) return;
        body.innerHTML = '<div class="feed-widget-empty"><i class="fa-solid fa-spinner fa-spin"></i> Carregando agenda...</div>';
        try {
            const r = await fetch('/api/agenda/resumo', { credentials: 'same-origin' });
            const data = await r.json();
            if (data.erro) { body.innerHTML = '<div class="feed-widget-empty">Erro ao buscar a agenda.</div>'; return; }
            if (data.atualizando) {
                body.innerHTML = '<div class="feed-widget-empty"><i class="fa-solid fa-spinner fa-spin"></i> Buscando sua agenda...</div>';
                setTimeout(carregarWidget, 12000);
                return;
            }
            const tarefas = Number(data.tarefas_total) || 0;
            const agenda = Number(data.agenda_hoje) || 0;
            body.innerHTML = '<div class="agenda-resumo">' +
                '<div class="agenda-resumo-item"><i class="fa-solid fa-list-check"></i><span>Tasks</span><b>' + tarefas + '</b></div>' +
                '<div class="agenda-resumo-item"><i class="fa-regular fa-calendar"></i><span>Agenda hoje</span><b>' + agenda + '</b></div>' +
                '</div>';
        } catch (e) {
            body.innerHTML = '<div class="feed-widget-empty">Erro ao buscar a agenda.</div>';
        }
    }

    /* ── 2. PÁGINA completa (/minha-agenda) ─────────────────────────── */
    let paginaItens = [];
    let paginaAba = 'tarefas';

    function renderPagina() {
        const lista = document.getElementById('agendaLista');
        if (!lista) return;
        const fonte = paginaAba === 'agenda' ? 'google' : 'ekyte';
        const fonteInfo = paginaItens._fontes && paginaItens._fontes[fonte];
        const q = (document.getElementById('agendaBusca').value || '').trim().toLowerCase();
        const todos = (paginaItens || []).filter(t => t.fonte === fonte);
        const filtrados = todos.filter(t => {
            if (!q) return true;
            const alvo = ((t.titulo || '') + ' ' + (t.rotulo || '') + ' ' + (t.sub || '')).toLowerCase();
            return alvo.indexOf(q) !== -1;
        });

        document.getElementById('agendaCount').textContent = (paginaItens || []).length;
        document.getElementById('agendaQtdTarefas').textContent = (paginaItens || []).filter(t => t.fonte === 'ekyte').length;
        document.getElementById('agendaQtdAgenda').textContent = (paginaItens || []).filter(t => t.fonte === 'google').length;

        if (fonte === 'google' && (!fonteInfo || !fonteInfo.conectado)) {
            lista.innerHTML = '<div class="feed-widget-empty"><i class="fa-regular fa-calendar-plus"></i> Conecte sua Google Agenda para ver seus eventos (em breve).</div>';
            return;
        }
        if (!filtrados.length) {
            lista.innerHTML = q
                ? '<div class="feed-widget-empty">Nenhum item encontrado para "' + esc(document.getElementById('agendaBusca').value) + '".</div>'
                : '<div class="feed-widget-empty">' + (fonte === 'google' ? 'Nenhum evento em aberto.' : 'Nenhuma tarefa em aberto.') + '</div>';
            return;
        }
        lista.innerHTML = '<div class="ekyte-tasks">' + filtrados.map(montarItem).join('') + '</div>';
    }

    async function carregarPagina() {
        const lista = document.getElementById('agendaLista');
        if (!lista) return;
        lista.innerHTML = '<div class="feed-loading"><i class="fa-solid fa-spinner fa-spin"></i> Carregando agenda...</div>';
        try {
            const r = await fetch('/api/agenda/items?fontes=ekyte,google', { credentials: 'same-origin' });
            const data = await r.json();
            if (data.erro) { lista.innerHTML = '<div class="feed-widget-empty">Erro ao buscar a agenda.</div>'; return; }
            if (data.atualizando && !(data.itens || []).length) {
                lista.innerHTML = '<div class="feed-loading"><i class="fa-solid fa-spinner fa-spin"></i> Buscando sua agenda...</div>';
                setTimeout(carregarPagina, 12000);
                return;
            }
            const arr = data.itens || [];
            arr._fontes = data.fontes || {};
            paginaItens = arr;
            renderPagina();
        } catch (e) {
            lista.innerHTML = '<div class="feed-widget-empty">Erro ao buscar a agenda.</div>';
        }
    }

    function mudarAba(aba) {
        paginaAba = aba;
        document.getElementById('agendaAbaTarefas').classList.toggle('ativa', aba === 'tarefas');
        document.getElementById('agendaAbaAgenda').classList.toggle('ativa', aba === 'agenda');
        renderPagina();
    }

    window.Agenda = { mudarAba: mudarAba };

    document.addEventListener('DOMContentLoaded', function () {
        const busca = document.getElementById('agendaBusca');
        if (busca) {
            busca.addEventListener('input', renderPagina);
            carregarPagina();
        } else {
            carregarWidget();
        }
    });
})();