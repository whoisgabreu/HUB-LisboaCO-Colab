/**
 * chat.js - Widget de chat interno (1:1), flutuante e global.
 */
(function () {
    "use strict";

    const LS_ABERTO = "hub_chat_aberto";
    const LS_CONV = "hub_chat_conversa";

    const state = {
        aberto: false,
        email: "",
        nome: "",
        conversa: null, // {id, outro_email, outro, online}
        mensagens: [],
        usuarios: [],
        pollMsg: null,
        pollLista: null,
        buscaTimer: null,
    };

    function esc(s) {
        return String(s === null || s === undefined ? "" : s)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function hora(iso) {
        if (!iso) return "";
        const d = new Date(iso);
        return isNaN(d) ? "" : d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    }

    function dia(iso) {
        if (!iso) return "";
        const d = new Date(iso);
        if (isNaN(d)) return "";
        const hoje = new Date();
        const ontem = new Date();
        ontem.setDate(hoje.getDate() - 1);
        const mesmaData = (a, b) => a.toDateString() === b.toDateString();
        if (mesmaData(d, hoje)) return "Hoje";
        if (mesmaData(d, ontem)) return "Ontem";
        return d.toLocaleDateString("pt-BR");
    }

    function avatar(foto, nome) {
        const inner = foto
            ? `<img src="/static/images/profile_pictures/${esc(foto)}" alt="${esc(nome)}">`
            : `<i class="fa-solid fa-user-tie"></i>`;
        return `<div class="chat-avatar">${inner}</div>`;
    }

    async function api(url, options) {
        const resp = await fetch(url, Object.assign({ headers: { "Content-Type": "application/json" } }, options));
        let data = null;
        try {
            data = await resp.json();
        } catch (e) {
            data = null;
        }
        if (!resp.ok) throw new Error((data && data.erro) || "Falha na requisição.");
        return data;
    }

    // ── Visibilidade do painel ────────────────────────────────────────────────
    function abrir() {
        state.aberto = true;
        localStorage.setItem(LS_ABERTO, "1");
        document.getElementById("chatPanel").classList.add("aberto");
        mostrarLista(true);
        iniciarPollLista();
        atualizarBadge();
    }

    function minimizar() {
        state.aberto = false;
        localStorage.setItem(LS_ABERTO, "0");
        document.getElementById("chatPanel").classList.remove("aberto");
        pararPollLista();
    }

    function toggle() {
        if (state.aberto) minimizar();
        else abrir();
    }

    function mostrarLista(refresh) {
        document.getElementById("chatViewLista").classList.add("ativo");
        document.getElementById("chatViewConversa").classList.remove("ativo");
        document.getElementById("chatBack").style.display = "none";
        document.getElementById("chatPanelTitle").textContent = "Mensagens";
        document.getElementById("chatPanelSub").textContent = "";
        pararPollMsg();
        if (refresh) carregarLista();
    }

    // ── Lista ─────────────────────────────────────────────────────────────────
    async function carregarLista() {
        try {
            const [convs, usuarios] = await Promise.all([
                api("/api/chat/conversas"),
                api("/api/chat/usuarios"),
            ]);
            state.usuarios = usuarios.usuarios || [];
            renderConvs(convs.conversas || []);
            renderPessoas(state.usuarios);
        } catch (e) {
            document.getElementById("chatPessoas").innerHTML = `<div class="chat-empty">${esc(e.message)}</div>`;
        }
    }

    function renderConvs(convs) {
        const title = document.getElementById("chatConvsTitle");
        const box = document.getElementById("chatConvs");
        const ativas = convs.filter((c) => c.ultima_mensagem);
        title.style.display = ativas.length ? "block" : "none";
        box.innerHTML = ativas
            .map((c) => {
                const prev = c.ultima_mensagem.deletado ? "Mensagem removida" : (c.ultima_mensagem.conteudo || "");
                const dot = c.online ? '<span class="chat-online"></span>' : "";
                return `<button class="chat-item" onclick="Chat.abrirConversaPorId(${c.id}, '${esc(c.outro_email)}', '${esc(c.outro.nome)}', ${c.online})">
                    <div class="chat-avatar">${c.outro.profile_picture ? `<img src="/static/images/profile_pictures/${esc(c.outro.profile_picture)}" alt="${esc(c.outro.nome)}">` : '<i class="fa-solid fa-user-tie"></i>'}${dot}</div>
                    <div class="chat-item-info">
                        <div class="chat-item-nome">${esc(c.outro.nome)}</div>
                        <div class="chat-item-sub">${esc(prev).slice(0, 45)}</div>
                    </div>
                    ${c.nao_lidas ? `<span class="chat-unread">${c.nao_lidas}</span>` : ""}
                </button>`;
            })
            .join("");
    }

    function renderPessoas(usuarios) {
        const box = document.getElementById("chatPessoas");
        if (!usuarios.length) {
            box.innerHTML = `<div class="chat-empty">Nenhum usuário ativo.</div>`;
            return;
        }
        box.innerHTML = usuarios
            .map(
                (u) => `<button class="chat-item" onclick="Chat.abrirConversaPorEmail('${esc(u.email)}', '${esc(u.nome)}', ${u.online})">
                    <div class="chat-avatar">${u.profile_picture ? `<img src="/static/images/profile_pictures/${esc(u.profile_picture)}" alt="${esc(u.nome)}">` : '<i class="fa-solid fa-user-tie"></i>'}${u.online ? '<span class="chat-online"></span>' : ""}</div>
                    <div class="chat-item-info">
                        <div class="chat-item-nome">${esc(u.nome)}</div>
                        <div class="chat-item-sub">${esc(u.funcao || "")}${u.squad ? " · " + esc(u.squad) : ""}</div>
                    </div>
                </button>`
            )
            .join("");
    }

    // ── Conversa ──────────────────────────────────────────────────────────────
    async function abrirConversaPorEmail(email, nome, online) {
        try {
            const conv = await api("/api/chat/conversas", { method: "POST", body: JSON.stringify({ email }) });
            await abrirConversaPorId(conv.id, email, nome || conv.outro.nome, conv.online);
        } catch (e) {
            alert(e.message);
        }
    }

    async function abrirConversaPorId(id, outroEmail, outroNome, online) {
        state.conversa = { id, outro_email: outroEmail, outro: { nome: outroNome }, online: !!online };
        localStorage.setItem(LS_CONV, JSON.stringify(state.conversa));

        document.getElementById("chatViewLista").classList.remove("ativo");
        document.getElementById("chatViewConversa").classList.add("ativo");
        document.getElementById("chatBack").style.display = "inline-flex";
        document.getElementById("chatPanelTitle").textContent = outroNome || "Conversa";
        document.getElementById("chatPanelSub").textContent = online ? "online" : "offline";

        state.mensagens = [];
        await carregarMensagens(false);
        await marcarLida();
        iniciarPollMsg();
        const ta = document.getElementById("chatTexto");
        if (ta) ta.focus();
    }

    async function carregarMensagens(antigas) {
        if (!state.conversa) return;
        const box = document.getElementById("chatMensagens");
        const antes = box.scrollHeight - box.scrollTop;
        try {
            const url = antigas && state.cursorAntigo
                ? `/api/chat/conversas/${state.conversa.id}/mensagens?cursor=${state.cursorAntigo}`
                : `/api/chat/conversas/${state.conversa.id}/mensagens`;
            const data = await api(url);
            if (antigas) {
                state.mensagens = [...data.mensagens, ...state.mensagens];
            } else {
                state.mensagens = data.mensagens;
            }
            state.cursorAntigo = data.cursor;
            state.temMais = data.tem_mais;
            state.conversa.online = data.online;
            renderMensagens();
            if (antigas) {
                box.scrollTop = box.scrollHeight - antes;
            } else {
                box.scrollTop = box.scrollHeight;
            }
            atualizarSub();
        } catch (e) {
            box.innerHTML = `<div class="chat-empty">${esc(e.message)}</div>`;
        }
    }

    function atualizarSub() {
        if (!state.conversa) return;
        document.getElementById("chatPanelSub").textContent = state.conversa.online ? "online" : "offline";
    }

    function renderMensagens() {
        const box = document.getElementById("chatMensagens");
        if (!state.mensagens.length) {
            box.innerHTML = `<div class="chat-empty">Diga olá 👋</div>`;
            return;
        }
        let html = "";
        let diaAtual = "";
        state.mensagens.forEach((m) => {
            const d = dia(m.criado_em);
            if (d && d !== diaAtual) {
                diaAtual = d;
                html += `<div class="chat-dia">${esc(d)}</div>`;
            }
            html += bolhaHtml(m);
        });
        box.innerHTML = html;
    }

    function bolhaHtml(m) {
        const corpo = m.deletado
            ? `<span class="chat-bubble deletada">Mensagem removida</span>`
            : `<span class="chat-bubble">${m.conteudo_html || esc(m.conteudo)}</span>`;
        const tick = m.meu
            ? `<span class="chat-tick ${m.lida ? "lida" : ""}"><i class="fa-solid ${m.lida ? "fa-check-double" : "fa-check"}"></i></span>`
            : "";
        const acoes = m.meu && !m.deletado
            ? `<span class="chat-msg-acoes">
                    <button onclick="Chat.editar(${m.id})">Editar</button>
                    <button onclick="Chat.excluir(${m.id})">Excluir</button>
               </span>`
            : "";
        const editado = m.editado ? ` · editado` : "";
        return `<div class="chat-msg ${m.meu ? "meu" : ""}" data-msg="${m.id}">
            ${corpo}
            <span class="chat-msg-meta">${acoes} <span>${esc(hora(m.criado_em))}${editado}</span> ${tick}</span>
        </div>`;
    }

    async function enviar() {
        const ta = document.getElementById("chatTexto");
        const conteudo = (ta.value || "").trim();
        if (!conteudo || !state.conversa) return;
        try {
            await api(`/api/chat/conversas/${state.conversa.id}/mensagens`, {
                method: "POST",
                body: JSON.stringify({ conteudo }),
            });
            ta.value = "";
            ta.style.height = "auto";
            document.getElementById("chatMencaoBox").classList.remove("aberto");
            await carregarMensagens(false);
            await marcarLida();
        } catch (e) {
            alert(e.message);
        }
    }

    async function editar(id) {
        const m = state.mensagens.find((x) => x.id === id);
        if (!m) return;
        const novo = await HubModal.prompt("Editar mensagem:", { defaultValue: m.conteudo || "" });
        if (novo === null) return;
        try {
            await api(`/api/chat/mensagens/${id}/editar`, { method: "POST", body: JSON.stringify({ conteudo: novo }) });
            await carregarMensagens(false);
        } catch (e) {
            alert(e.message);
        }
    }

    async function excluir(id) {
        if (!(await HubModal.confirm("Excluir esta mensagem?", { okLabel: "Excluir", danger: true }))) return;
        try {
            await api(`/api/chat/mensagens/${id}`, { method: "DELETE" });
            await carregarMensagens(false);
        } catch (e) {
            alert(e.message);
        }
    }

    async function marcarLida() {
        if (!state.conversa) return;
        try {
            await api(`/api/chat/conversas/${state.conversa.id}/ler`, { method: "POST" });
            atualizarBadge();
        } catch (e) {
            /* silencioso */
        }
    }

    // ── Polling ───────────────────────────────────────────────────────────────
    function iniciarPollMsg() {
        pararPollMsg();
        state.pollMsg = setInterval(async () => {
            if (!state.aberto || !state.conversa) return;
            const ultimoAtual = state.mensagens.length ? state.mensagens[state.mensagens.length - 1].id : 0;
            try {
                const data = await api(`/api/chat/conversas/${state.conversa.id}/mensagens`);
                const ultimoNovo = data.mensagens.length ? data.mensagens[data.mensagens.length - 1].id : 0;
                state.conversa.online = data.online;
                if (ultimoNovo !== ultimoAtual) {
                    state.mensagens = data.mensagens;
                    renderMensagens();
                    const box = document.getElementById("chatMensagens");
                    box.scrollTop = box.scrollHeight;
                    await marcarLida();
                } else {
                    atualizarSub();
                }
            } catch (e) {
                /* silencioso */
            }
        }, 3000);
    }

    function pararPollMsg() {
        if (state.pollMsg) clearInterval(state.pollMsg);
        state.pollMsg = null;
    }

    function iniciarPollLista() {
        pararPollLista();
        state.pollLista = setInterval(() => {
            if (state.aberto && document.getElementById("chatViewLista").classList.contains("ativo")) {
                carregarLista();
            }
        }, 5000);
    }

    function pararPollLista() {
        if (state.pollLista) clearInterval(state.pollLista);
        state.pollLista = null;
    }

    // ── Badge global ──────────────────────────────────────────────────────────
    async function atualizarBadge() {
        const el = document.getElementById("chatBadge");
        if (!el) return;
        try {
            const r = await fetch("/api/chat/nao-lidas");
            if (!r.ok) return;
            const d = await r.json();
            const total = d.total || 0;
            if (total > 0) {
                el.textContent = total > 99 ? "99+" : total;
                el.style.display = "flex";
            } else {
                el.style.display = "none";
            }
        } catch (e) {
            /* silencioso */
        }
    }

    // ── Busca ─────────────────────────────────────────────────────────────────
    function aoBuscar(e) {
        clearTimeout(state.buscaTimer);
        const q = e.target.value.trim();
        const box = document.getElementById("chatBuscaResultados");
        if (!q) {
            box.style.display = "none";
            box.innerHTML = "";
            return;
        }
        state.buscaTimer = setTimeout(async () => {
            try {
                const data = await api(`/api/chat/busca?q=${encodeURIComponent(q)}`);
                const pessoas = data.pessoas || [];
                const mensagens = data.mensagens || [];
                if (!pessoas.length && !mensagens.length) {
                    box.style.display = "block";
                    box.innerHTML = `<div class="chat-empty">Nada encontrado.</div>`;
                    return;
                }
                let html = "";
                if (pessoas.length) {
                    html += `<div class="chat-section-title">Pessoas</div>`;
                    html += pessoas
                        .map((p) => {
                            const inner = p.profile_picture
                                ? `<img src="/static/images/profile_pictures/${esc(p.profile_picture)}" alt="${esc(p.nome)}">`
                                : `<i class="fa-solid fa-user-tie"></i>`;
                            const dot = p.online ? '<span class="chat-online"></span>' : "";
                            const acao = p.conversa_id
                                ? `Chat.abrirConversaPorId(${p.conversa_id}, '${esc(p.email)}', '${esc(p.nome)}', ${p.online})`
                                : `Chat.abrirConversaPorEmail('${esc(p.email)}', '${esc(p.nome)}', ${p.online})`;
                            return `<button class="chat-item" onclick="Chat.limparBusca(); ${acao}">
                                <div class="chat-avatar">${inner}${dot}</div>
                                <div class="chat-item-info">
                                    <div class="chat-item-nome">${esc(p.nome)}</div>
                                    <div class="chat-item-sub">${esc(p.funcao || "")}${p.squad ? " · " + esc(p.squad) : ""}</div>
                                </div>
                            </button>`;
                        })
                        .join("");
                }
                if (mensagens.length) {
                    html += `<div class="chat-section-title">Mensagens</div>`;
                    html += mensagens
                        .map(
                            (r) => `<button class="chat-item" onclick="Chat.limparBusca(); Chat.abrirConversaPorId(${r.conversa_id}, '${esc(r.outro_email)}', '${esc(r.outro ? r.outro.nome : "")}', false)">
                            <div class="chat-item-info">
                                <div class="chat-item-nome">${esc(r.outro ? r.outro.nome : "Conversa")}</div>
                                <div class="chat-item-sub">${esc(r.conteudo).slice(0, 50)}</div>
                            </div>
                        </button>`
                        )
                        .join("");
                }
                box.style.display = "block";
                box.innerHTML = html;
            } catch (e2) {
                /* silencioso */
            }
        }, 300);
    }

    // ── Menções ───────────────────────────────────────────────────────────────
    function aoDigitar(e) {
        const ta = e.target;
        ta.style.height = "auto";
        ta.style.height = Math.min(ta.scrollHeight, 90) + "px";
        const box = document.getElementById("chatMencaoBox");
        const pos = ta.selectionStart;
        const antes = ta.value.slice(0, pos);
        const m = antes.match(/@([A-Za-z0-9._%+\-]*)$/);
        if (!m) {
            box.classList.remove("aberto");
            box.innerHTML = "";
            return;
        }
        const termo = m[1].toLowerCase();
        const sug = state.usuarios
            .filter((u) => (u.nome || "").toLowerCase().includes(termo) || (u.email || "").toLowerCase().includes(termo))
            .slice(0, 5);
        if (!sug.length) {
            box.classList.remove("aberto");
            box.innerHTML = "";
            return;
        }
        box.innerHTML = sug
            .map(
                (u) => `<button class="chat-mencao-item" onclick="Chat.inserirMencao('${esc(u.email)}')">
                    <span>${esc(u.nome)}</span><small>${esc(u.email)}</small>
                </button>`
            )
            .join("");
        box.classList.add("aberto");
    }

    function inserirMencao(email) {
        const ta = document.getElementById("chatTexto");
        const pos = ta.selectionStart;
        const antes = ta.value.slice(0, pos).replace(/@([A-Za-z0-9._%+\-]*)$/, "");
        ta.value = `${antes}@${email} ` + ta.value.slice(pos);
        ta.selectionStart = ta.selectionEnd = antes.length + email.length + 2;
        document.getElementById("chatMencaoBox").classList.remove("aberto");
        ta.focus();
    }

    function aoTeclar(e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            enviar();
        }
    }

    // ── Init ──────────────────────────────────────────────────────────────────
    document.addEventListener("DOMContentLoaded", () => {
        const root = document.getElementById("chatWidget");
        if (!root) return;
        state.email = root.dataset.userEmail || "";
        state.nome = root.dataset.userNome || "";

        const busca = document.getElementById("chatBusca");
        if (busca) busca.addEventListener("input", aoBuscar);
        const ta = document.getElementById("chatTexto");
        if (ta) {
            ta.addEventListener("input", aoDigitar);
            ta.addEventListener("keydown", aoTeclar);
        }

        // rolagem: carregar antigas ao chegar no topo
        const boxMsg = document.getElementById("chatMensagens");
        if (boxMsg) {
            boxMsg.addEventListener("scroll", () => {
                if (boxMsg.scrollTop <= 5 && state.temMais && state.conversa) {
                    carregarMensagens(true);
                }
            });
        }

        atualizarBadge();
        setInterval(atualizarBadge, 20000);

        // restaura estado
        const aberto = localStorage.getItem(LS_ABERTO) === "1";
        const convSalva = localStorage.getItem(LS_CONV);
        if (aberto) {
            abrir();
            if (convSalva) {
                try {
                    const c = JSON.parse(convSalva);
                    abrirConversaPorId(c.id, c.outro_email, c.outro && c.outro.nome, c.online);
                } catch (e) {
                    /* ignora */
                }
            }
        }
    });

    function limparBusca() {
        const b = document.getElementById("chatBusca");
        if (b) b.value = "";
        const box = document.getElementById("chatBuscaResultados");
        if (box) {
            box.style.display = "none";
            box.innerHTML = "";
        }
    }

    window.Chat = {
        toggle,
        minimizar,
        abrir,
        limparBusca,
        voltarLista: () => mostrarLista(true),
        abrirConversaPorEmail,
        abrirConversaPorId,
        enviar,
        editar,
        excluir,
        inserirMencao,
        atualizarBadge,
    };
})();
