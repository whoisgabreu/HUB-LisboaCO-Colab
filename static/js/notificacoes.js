/**
 * notificacoes.js - Sino de notificações do Feed Lisboa (global).
 * Faz polling leve da contagem de não lidas e mostra o dropdown.
 */
(function () {
    "use strict";

    const ICONES = {
        reacao: "fa-heart",
        comentario: "fa-comment",
        resposta: "fa-reply",
        mencao: "fa-at",
    };

    let aberto = false;

    function esc(s) {
        return String(s === null || s === undefined ? "" : s)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function badge(n) {
        const el = document.getElementById("notifBadge");
        if (!el) return;
        if (n > 0) {
            el.textContent = n > 99 ? "99+" : n;
            el.style.display = "flex";
        } else {
            el.style.display = "none";
        }
    }

    async function atualizarContagem() {
        if (!document.getElementById("notifBell")) return;
        let total = 0;
        try {
            const r = await fetch("/api/feed/notificacoes/contagem");
            if (r.ok) {
                const d = await r.json();
                total += d.nao_lidas || 0;
            }
        } catch (e) {
            /* silencioso */
        }
        try {
            const r = await fetch("/api/chat/nao-lidas");
            if (r.ok) {
                const d = await r.json();
                total += d.total || 0;
            }
        } catch (e) {
            /* silencioso */
        }
        badge(total);
    }

    async function pingPresenca() {
        try {
            await fetch("/api/chat/presenca/ping", { method: "POST" });
        } catch (e) {
            /* silencioso */
        }
    }

    async function carregarLista() {
        const el = document.getElementById("notifList");
        if (!el) return;

        let feed = [];
        let convs = [];
        try {
            const r = await fetch("/api/feed/notificacoes");
            if (r.ok) feed = (await r.json()).notificacoes || [];
        } catch (e) {
            /* silencioso */
        }
        try {
            const r = await fetch("/api/chat/conversas");
            if (r.ok) convs = ((await r.json()).conversas || []).filter((c) => c.nao_lidas > 0);
        } catch (e) {
            /* silencioso */
        }

        if (!feed.length && !convs.length) {
            el.innerHTML = '<div class="notif-empty">Sem notificações.</div>';
            return;
        }

        let html = "";

        if (convs.length) {
            html += '<div class="notif-section-title">Mensagens</div>';
            html += convs
                .map((c) => {
                    const prev = c.ultima_mensagem && c.ultima_mensagem.conteudo ? c.ultima_mensagem.conteudo : "enviou uma mensagem";
                    return `
                    <div class="notif-item nao-lida" onclick="Notificacoes.abrirChat(${c.id}, '${esc(c.outro_email)}', '${esc(c.outro.nome)}', ${c.online})">
                        <div class="notif-item-icon"><i class="fa-solid fa-comment"></i></div>
                        <div class="notif-item-body">
                            <div class="notif-item-texto"><strong>${esc(c.outro.nome)}</strong> ${esc(prev)}</div>
                            <div class="notif-item-meta">${esc(tempo(c.ultima_mensagem_em))}</div>
                        </div>
                        <span class="notif-unread">${c.nao_lidas}</span>
                    </div>`;
                })
                .join("");
        }

        if (feed.length) {
            html += '<div class="notif-section-title">Publicações</div>';
            html += feed
                .map(
                    (n) => `
                <div class="notif-item ${n.lida ? "" : "nao-lida"}" onclick="Notificacoes.abrir(${n.id}, ${n.post_id || "null"}, ${n.comentario_id || "null"})">
                    <div class="notif-item-icon"><i class="fa-solid ${ICONES[n.tipo] || "fa-bell"}"></i></div>
                    <div class="notif-item-body">
                        <div class="notif-item-texto"><strong>${esc(n.autor.nome)}</strong> ${esc(n.texto)}</div>
                        <div class="notif-item-meta">${esc(tempo(n.criado_em))}</div>
                    </div>
                    ${n.lida ? "" : '<span class="notif-dot"></span>'}
                </div>`
                )
                .join("");
        }

        el.innerHTML = html;
    }

    function tempo(iso) {
        if (!iso) return "";
        const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
        if (diff < 60) return "agora";
        if (diff < 3600) return `há ${Math.floor(diff / 60)} min`;
        if (diff < 86400) return `há ${Math.floor(diff / 3600)} h`;
        return new Date(iso).toLocaleDateString("pt-BR");
    }

    function toggle(ev) {
        if (ev) ev.stopPropagation();
        aberto = !aberto;
        const dd = document.getElementById("notifDropdown");
        if (!dd) return;
        dd.classList.toggle("aberto", aberto);
        if (aberto) carregarLista();
    }

    async function marcarTodas() {
        try {
            await fetch("/api/feed/notificacoes/marcar-lidas", { method: "POST" });
        } catch (e) {
            /* silencioso */
        }
        try {
            await fetch("/api/chat/marcar-todas-lidas", { method: "POST" });
        } catch (e) {
            /* silencioso */
        }
        badge(0);
        carregarLista();
    }

    function abrirChat(id, email, nome, online) {
        aberto = false;
        const dd = document.getElementById("notifDropdown");
        if (dd) dd.classList.remove("aberto");
        if (window.Chat) {
            Chat.abrir();
            Chat.abrirConversaPorId(id, email, nome, online);
        }
        setTimeout(atualizarContagem, 500);
    }

    async function abrir(id, postId, comentarioId) {
        try {
            await fetch(`/api/feed/notificacoes/${id}/lida`, { method: "POST" });
        } catch (e) {
            /* silencioso */
        }
        aberto = false;
        const dd = document.getElementById("notifDropdown");
        if (dd) dd.classList.remove("aberto");

        if (postId) {
            const destino = `/feed/post/${postId}` + (comentarioId ? `?comentario=${comentarioId}` : "");
            if (window.location.pathname + window.location.search !== destino) {
                window.location.href = destino;
            }
            return;
        }
        if (!window.location.pathname.startsWith("/feed")) {
            window.location.href = "/feed";
        } else {
            atualizarContagem();
        }
    }

    document.addEventListener("click", () => {
        if (!aberto) return;
        aberto = false;
        const dd = document.getElementById("notifDropdown");
        if (dd) dd.classList.remove("aberto");
    });

    document.addEventListener("DOMContentLoaded", () => {
        atualizarContagem();
        pingPresenca();
        setInterval(atualizarContagem, 60000);
        setInterval(pingPresenca, 30000);
    });

    window.Notificacoes = { toggle, marcarTodas, abrir, abrirChat, atualizarContagem };
})();
