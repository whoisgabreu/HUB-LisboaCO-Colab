/* Minha Agenda — Tarefas (Ekyte) e Eventos (Google Agenda).
   Widget no rail do perfil + página completa (/minha-agenda) com visão de agenda. */
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

    function horaHM(iso) {
        const m = String(iso || '').match(/T(\d{2}:\d{2})/);
        return m ? m[1] : '';
    }

    function dataChave(iso) {
        const m = String(iso || '').match(/^(\d{4}-\d{2}-\d{2})/);
        return m ? m[1] : '';
    }

    function rotuloDia(dstr) {
        if (!dstr) return '';
        const [y, m, d] = dstr.split('-').map(Number);
        const dt = new Date(y, m - 1, d);
        const hoje = new Date(); hoje.setHours(0, 0, 0, 0);
        const diff = Math.round((dt - hoje) / 86400000);
        if (diff === 0) return 'Hoje';
        if (diff === 1) return 'Amanhã';
        if (diff === -1) return 'Ontem';
        const wd = dt.toLocaleDateString('pt-BR', { weekday: 'long' });
        return wd.charAt(0).toUpperCase() + wd.slice(1) + ', ' + String(d).padStart(2, '0') + '/' + String(m).padStart(2, '0');
    }

    function passaBusca(t, q) {
        if (!q) return true;
        const alvo = ((t.titulo || '') + ' ' + (t.rotulo || '') + ' ' + (t.sub || '')).toLowerCase();
        return alvo.indexOf(q) !== -1;
    }

    function byInicio(a, b) {
        return String(a.inicio || a.data || '').localeCompare(String(b.inicio || b.data || ''));
    }

    function badgeFonte(t) {
        if (t.fonte === 'google') return '<span class="agenda-fonte-badge google"><i class="fa-regular fa-calendar"></i> Evento</span>';
        return '<span class="agenda-fonte-badge"><i class="fa-solid fa-list-check"></i> Tarefa</span>';
    }

    /* ── Item de tarefa (cards, como antes) ───────────────────────────── */
    function montarTarefa(t) {
        const titulo = esc(t.titulo || 'Sem título');
        const meta = [];
        if (t.rotulo) meta.push('<span>' + esc(t.rotulo) + '</span>');
        if (t.data) {
            const iso = dataISO(t);
            const atrasada = iso && iso < hojeISO();
            meta.push('<span><i class="fa-regular fa-calendar"></i> ' + esc(t.data) + '</span>' + (atrasada ? ' <span class="ekyte-prazo atrasado">Atrasada</span>' : ''));
        }
        if (t.sub) meta.push('<span><i class="fa-solid fa-layer-group"></i> ' + esc(t.sub) + '</span>');
        const metaHtml = meta.length ? '<div class="ekyte-task-meta">' + meta.join(' · ') + '</div>' : '';
        const link = t.link
            ? '<a class="ekyte-open" href="' + esc(t.link) + '" target="_blank" rel="noopener">Abrir no Ekyte <i class="fa-solid fa-arrow-up-right-from-square"></i></a>'
            : '';
        return '<div class="ekyte-task"><div class="ekyte-task-titulo">' + badgeFonte(t) + ' ' + titulo + '</div>' + metaHtml + link + '</div>';
    }

    /* ── Evento (visão de agenda) ─────────────────────────────────────── */
    function montarEvento(e, proxima) {
        const hr = e.dia_todo
            ? '<span class="agenda-diatodo-tag">Dia todo</span>'
            : '<div class="agenda-evento-horas"><span class="ini">' + esc(horaHM(e.inicio)) + '</span>' + (e.fim && horaHM(e.fim) ? '<span class="fim">' + esc(horaHM(e.fim)) + '</span>' : '') + '</div>';
        const badge = proxima ? ' <span class="agenda-proxima-badge">Próxima</span>' : '';
        const local = e.sub ? '<div class="agenda-evento-meta"><i class="fa-solid fa-location-dot"></i> ' + esc(e.sub) + '</div>' : '';
        const link = e.link
            ? '<a class="ekyte-open" href="' + esc(e.link) + '" target="_blank" rel="noopener">Abrir no Google <i class="fa-solid fa-arrow-up-right-from-square"></i></a>'
            : '';
        return '<div class="agenda-evento' + (proxima ? ' proxima' : '') + (e.dia_todo ? ' dia-todo' : '') + '">' +
            '<div class="agenda-evento-hora">' + hr + '</div>' +
            '<div class="agenda-evento-body"><div class="agenda-evento-titulo">' + esc(e.titulo || 'Sem título') + badge + '</div>' + local + link + '</div>' +
            '</div>';
    }

    function montarSeguir(e) {
        const d = dataChave(e.inicio || e.data);
        return '<div class="agenda-seguir-item">' +
            '<div class="agenda-seguir-hora">' + esc(horaHM(e.inicio)) + '</div>' +
            '<div class="agenda-seguir-info"><div class="agenda-seguir-nome">' + esc(e.titulo || '') + '</div>' +
            '<div class="agenda-seguir-meta">' + esc(rotuloDia(d)) + (e.sub ? ' · ' + esc(e.sub) : '') + '</div></div>' +
            '</div>';
    }

    /* ── 1. WIDGET compacto (rail do perfil) ──────────────────────────── */
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
            let extra = '';
            if (data.google_conectado && data.proxima_reuniao) {
                extra = '<div class="agenda-proxima"><i class="fa-regular fa-clock"></i> Próxima: <b>' +
                    esc(horaHM(data.proxima_reuniao.inicio)) + '</b> ' + esc(data.proxima_reuniao.titulo) + '</div>';
            } else if (data.google_conectado) {
                extra = '<div class="agenda-proxima vazio">Sem reuniões hoje.</div>';
            }
            body.innerHTML = '<div class="agenda-resumo">' +
                '<div class="agenda-resumo-item"><i class="fa-solid fa-list-check"></i><span>Tasks</span><b>' + tarefas + '</b></div>' +
                '<div class="agenda-resumo-item"><i class="fa-regular fa-calendar"></i><span>Agenda hoje</span><b>' + agenda + '</b></div>' +
                extra +
                '</div>';
        } catch (e) {
            body.innerHTML = '<div class="feed-widget-empty">Erro ao buscar a agenda.</div>';
        }
    }

    /* ── 2. PÁGINA completa (/minha-agenda) ──────────────────────────── */
    let paginaItens = [];
    let paginaAba = 'tarefas';

    function renderAgenda(todos, q, fonteInfo, toolbar) {
        const lista = document.getElementById('agendaLista');
        if (!fonteInfo || !fonteInfo.conectado) {
            lista.innerHTML = '<div class="agenda-conectar">' +
                '<i class="fa-brands fa-google"></i>' +
                '<p>Conecte sua Google Agenda para ver seus eventos aqui.</p>' +
                '<a class="agenda-conectar-btn" href="/agenda/google/conectar">Conectar Google Agenda</a>' +
                '</div>';
            return;
        }
        const eventos = todos.filter(t => passaBusca(t, q)).sort(byInicio);
        if (!eventos.length) {
            lista.innerHTML = toolbar + '<div class="feed-widget-empty">' +
                (q ? 'Nenhum evento encontrado.' : 'Nenhum evento nos próximos dias.') + '</div>';
            return;
        }

        const agora = new Date();
        const seguir = eventos.filter(e => e.inicio && e.inicio.indexOf('T') !== -1 && new Date(e.inicio) >= agora).slice(0, 3);

        const grupos = {};
        eventos.forEach(e => {
            const k = dataChave(e.inicio || e.data) || 'sem-data';
            (grupos[k] = grupos[k] || []).push(e);
        });
        const dias = Object.keys(grupos).sort();

        let html = '';
        if (seguir.length) {
            html += '<div class="agenda-seguir"><div class="agenda-seguir-titulo"><i class="fa-solid fa-bolt"></i> A seguir</div>' +
                '<div class="agenda-seguir-lista">' + seguir.map(montarSeguir).join('') + '</div></div>';
        }
        html += '<div class="agenda-view">';
        let marcouProxima = false;
        dias.forEach(d => {
            html += '<div class="agenda-dia"><div class="agenda-dia-header">' + esc(rotuloDia(d)) + '</div>';
            const evs = grupos[d].slice().sort((a, b) => (a.dia_todo ? 0 : 1) - (b.dia_todo ? 0 : 1) || byInicio(a, b));
            evs.forEach(e => {
                const isProx = !marcouProxima && !e.dia_todo && e.inicio && e.inicio.indexOf('T') !== -1 && new Date(e.inicio) >= agora;
                if (isProx) marcouProxima = true;
                html += montarEvento(e, isProx);
            });
            html += '</div>';
        });
        html += '</div>';
        lista.innerHTML = toolbar + html;
    }

    function renderPagina() {
        const lista = document.getElementById('agendaLista');
        if (!lista) return;
        const fonte = paginaAba === 'agenda' ? 'google' : 'ekyte';
        const fonteInfo = paginaItens._fontes && paginaItens._fontes[fonte];
        const q = (document.getElementById('agendaBusca').value || '').trim().toLowerCase();
        const todos = (paginaItens || []).filter(t => t.fonte === fonte);

        document.getElementById('agendaCount').textContent = (paginaItens || []).length;
        document.getElementById('agendaQtdTarefas').textContent = (paginaItens || []).filter(t => t.fonte === 'ekyte').length;
        document.getElementById('agendaQtdAgenda').textContent = (paginaItens || []).filter(t => t.fonte === 'google').length;

        if (fonte === 'google') {
            const toolbar = (fonteInfo && fonteInfo.conectado)
                ? '<div class="agenda-lista-toolbar"><form method="post" action="/agenda/google/desconectar"><button type="submit" class="agenda-desconectar-btn"><i class="fa-solid fa-link-slash"></i> Desconectar Google Agenda</button></form></div>'
                : '';
            renderAgenda(todos, q, fonteInfo, toolbar);
            return;
        }

        const filtrados = todos.filter(t => passaBusca(t, q));
        if (!filtrados.length) {
            lista.innerHTML = q
                ? '<div class="feed-widget-empty">Nenhuma tarefa encontrada para "' + esc(q) + '".</div>'
                : '<div class="feed-widget-empty">Nenhuma tarefa em aberto.</div>';
            return;
        }
        lista.innerHTML = '<div class="ekyte-tasks">' + filtrados.map(montarTarefa).join('') + '</div>';
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
            const params = new URLSearchParams(location.search);
            if (params.get('agenda') === 'conectada') {
                paginaAba = 'agenda';
                document.getElementById('agendaAbaTarefas').classList.remove('ativa');
                document.getElementById('agendaAbaAgenda').classList.add('ativa');
                if (typeof toast !== 'undefined' && toast.success) toast.success('Google Agenda conectada!');
                history.replaceState(null, '', location.pathname);
            }
            carregarPagina();
        } else {
            carregarWidget();
        }
    });
})();