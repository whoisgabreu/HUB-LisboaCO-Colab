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
        try {
            const r = await fetch("/api/feed/notificacoes/contagem");
            if (!r.ok) return;
            const d = await r.json();
            badge(d.nao_lidas || 0);
        } catch (e) {
            /* silencioso */
        }
    }

    async function carregarLista() {
        const el = document.getElementById("notifList");
        if (!el) return;
        try {
            const r = await fetch("/api/feed/notificacoes");
            if (!r.ok) throw new Error();
            const d = await r.json();
            const itens = d.notificacoes || [];
            if (!itens.length) {
                el.innerHTML = '<div class="notif-empty">Sem notificações.</div>';
                return;
            }
            el.innerHTML = itens
                .map(
                    (n) => `
                <div class="notif-item ${n.lida ? "" : "nao-lida"}" onclick="Notificacoes.abrir(${n.id})">
                    <div class="notif-item-icon"><i class="fa-solid ${ICONES[n.tipo] || "fa-bell"}"></i></div>
                    <div class="notif-item-body">
                        <div class="notif-item-texto"><strong>${esc(n.autor.nome)}</strong> ${esc(n.texto)}</div>
                        <div class="notif-item-meta">${esc(tempo(n.criado_em))}</div>
                    </div>
                    ${n.lida ? "" : '<span class="notif-dot"></span>'}
                </div>`
                )
                .join("");
        } catch (e) {
            el.innerHTML = '<div class="notif-empty">Não foi possível carregar.</div>';
        }
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
        badge(0);
        carregarLista();
    }

    async function abrir(id) {
        try {
            await fetch(`/api/feed/notificacoes/${id}/lida`, { method: "POST" });
        } catch (e) {
            /* silencioso */
        }
        aberto = false;
        const dd = document.getElementById("notifDropdown");
        if (dd) dd.classList.remove("aberto");
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
        setInterval(atualizarContagem, 60000);
    });

    window.Notificacoes = { toggle, marcarTodas, abrir, atualizarContagem };
})();
