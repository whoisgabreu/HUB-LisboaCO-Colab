/**
 * feed.js - Feed social da Home
 * Consome as APIs /api/feed/* e renderiza posts, reações e comentários.
 */
(function () {
    "use strict";

    const REACOES = {
        like: { emoji: "👍", label: "Curtir" },
        love: { emoji: "❤️", label: "Amei" },
        haha: { emoji: "😂", label: "Haha" },
        wow: { emoji: "😮", label: "Uau" },
        sad: { emoji: "😢", label: "Triste" },
        angry: { emoji: "😡", label: "Grr" },
    };

    const state = {
        root: null,
        email: "",
        nome: "",
        foto: "",
        privilegiado: false,
        pagina: 1,
        carregando: false,
        temMais: false,
        posts: {},
    };

    // ── Utils ────────────────────────────────────────────────────────────────
    function esc(str) {
        if (str === null || str === undefined) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function tempoRelativo(iso) {
        if (!iso) return "";
        const data = new Date(iso);
        if (isNaN(data)) return "";
        const diff = Math.floor((Date.now() - data.getTime()) / 1000);
        if (diff < 60) return "agora";
        if (diff < 3600) return `há ${Math.floor(diff / 60)} min`;
        if (diff < 86400) return `há ${Math.floor(diff / 3600)} h`;
        if (diff < 604800) return `há ${Math.floor(diff / 86400)} d`;
        return data.toLocaleDateString("pt-BR");
    }

    function formatarData(iso) {
        if (!iso) return "";
        const d = new Date(iso);
        if (isNaN(d)) return "";
        return d.toLocaleString("pt-BR", {
            day: "2-digit",
            month: "long",
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    function avatarHtml(foto, nome) {
        if (foto) {
            return `<img src="/static/images/profile_pictures/${esc(foto)}" alt="${esc(nome)}">`;
        }
        return `<i class="fa-solid fa-user-tie"></i>`;
    }

    async function api(url, options) {
        const resp = await fetch(url, Object.assign({ headers: { "Content-Type": "application/json" } }, options));
        let data = null;
        try {
            data = await resp.json();
        } catch (e) {
            data = null;
        }
        if (!resp.ok) {
            throw new Error((data && data.erro) || "Falha na requisição.");
        }
        return data;
    }

    function pingar(post) {
        if (!post.fixado) return false;
        if (!post.fixado_ate) return true;
        return new Date(post.fixado_ate) > new Date();
    }

    function badgeTipo(post) {
        if (post.tipo === "evento") return `<span class="feed-badge evento"><i class="fa-regular fa-calendar"></i> Evento</span>`;
        if (post.tipo === "aniversario") return `<span class="feed-badge aniversario"><i class="fa-solid fa-cake-candles"></i> Aniversário</span>`;
        return "";
    }

    // ── Render ───────────────────────────────────────────────────────────────
    function reacoesResumoHtml(post) {
        const ativas = Object.entries(post.reacoes || {}).filter(([, q]) => q > 0);
        if (!ativas.length) return "";
        const emojis = ativas.map(([t]) => (REACOES[t] ? REACOES[t].emoji : t)).join(" ");
        return `<span class="feed-r-summary"><span class="feed-r-emojis">${emojis}</span> ${post.total_reacoes}</span>`;
    }

    function cardHtml(post) {
        const pinAtivo = pingar(post);
        const minha = post.minha_reacao;
        const meuBotao = minha && REACOES[minha] ? REACOES[minha] : REACOES.like;

        let evento = "";
        if (post.tipo === "evento") {
            evento = `
                <div class="feed-evento-box">
                    <div class="feed-evento-titulo"><i class="fa-regular fa-calendar"></i> ${esc(post.titulo || "Evento")}</div>
                    ${post.evento_data ? `<div class="feed-evento-meta"><i class="fa-regular fa-clock"></i> ${esc(formatarData(post.evento_data))}</div>` : ""}
                    ${post.evento_local ? `<div class="feed-evento-meta"><i class="fa-solid fa-location-dot"></i> ${esc(post.evento_local)}</div>` : ""}
                </div>`;
        }

        const menuPriv = state.privilegiado
            ? `${pinAtivo
                ? `<button class="feed-mini-btn" onclick="Feed.desfixar(${post.id})"><i class="fa-solid fa-thumbtack"></i> Desfixar</button>`
                : `<button class="feed-mini-btn" onclick="Feed.fixar(${post.id})"><i class="fa-solid fa-thumbtack"></i> Fixar</button>`
            }`
            : "";

        const podeExcluir = state.privilegiado || post.autor_email === state.email;
        const botaoExcluir = podeExcluir
            ? `<button class="feed-mini-btn danger" onclick="Feed.deletarPost(${post.id})"><i class="fa-solid fa-trash"></i></button>`
            : "";

        return `
        <article class="feed-post ${pinAtivo ? "is-pinned" : ""}" data-post-id="${post.id}">
            ${pinAtivo ? `<div class="feed-pin-flag"><i class="fa-solid fa-thumbtack"></i> Fixado</div>` : ""}
            <header class="feed-post-head">
                <div class="feed-avatar small">${avatarHtml(post.autor.profile_picture, post.autor.nome)}</div>
                <div class="feed-post-head-info">
                    <div class="feed-post-autor">
                        ${esc(post.autor.nome)}
                        ${badgeTipo(post)}
                    </div>
                    <div class="feed-post-meta">${esc(post.autor.funcao || "")} · ${esc(tempoRelativo(post.criado_em))}</div>
                </div>
                <div class="feed-post-tools">${menuPriv}${botaoExcluir}</div>
            </header>
            ${evento}
            ${post.conteudo ? `<div class="feed-post-conteudo">${esc(post.conteudo).replace(/\n/g, "<br>")}</div>` : ""}
            <div class="feed-post-stats">
                ${reacoesResumoHtml(post)}
                <button class="feed-r-link" onclick="Feed.toggleComentarios(${post.id})">
                    ${post.total_comentarios} comentário(s)
                </button>
            </div>
            <div class="feed-post-actions">
                <div class="feed-reaction-wrap">
                    <button class="feed-action-btn ${minha ? "ativa" : ""}" onclick="Feed.abrirPicker(${post.id}, event)">
                        <span class="feed-action-emoji">${meuBotao.emoji}</span> ${esc(meuBotao.label)}
                    </button>
                    <div class="feed-picker" data-picker="${post.id}"></div>
                </div>
                <button class="feed-action-btn" onclick="Feed.toggleComentarios(${post.id})">
                    <i class="fa-regular fa-comment"></i> Comentar
                </button>
            </div>
            <div class="feed-comentarios" data-comentarios="${post.id}" style="display:none;">
                <div class="feed-comentarios-lista"></div>
                <div class="feed-comentario-form">
                    <textarea rows="1" placeholder="Escreva um comentário..." data-input="${post.id}"></textarea>
                    <button class="feed-btn primary small" onclick="Feed.comentar(${post.id})">Enviar</button>
                </div>
            </div>
        </article>`;
    }

    function renderizarPosts(posts, append) {
        const lista = document.getElementById("feedList");
        const html = posts.map(cardHtml).join("");
        if (append) {
            lista.insertAdjacentHTML("beforeend", html);
        } else {
            lista.innerHTML = html || `<div class="feed-vazio"><i class="fa-regular fa-face-smile"></i> Nenhuma publicação ainda. Seja o primeiro!</div>`;
        }
        posts.forEach((p) => {
            state.posts[p.id] = p;
            montarPicker(p.id);
        });
    }

    function montarPicker(postId) {
        const picker = document.querySelector(`[data-picker="${postId}"]`);
        if (!picker) return;
        picker.innerHTML = Object.entries(REACOES)
            .map(([t, r]) => `<button type="button" title="${r.label}" onclick="Feed.reagir(${postId}, '${t}')">${r.emoji}</button>`)
            .join("");
    }

    // ── Ações ────────────────────────────────────────────────────────────────
    async function carregar(append) {
        if (state.carregando) return;
        state.carregando = true;
        if (!append) state.pagina = 1;

        const btn = document.getElementById("feedCarregarMais");
        try {
            const data = await api(`/api/feed/posts?pagina=${state.pagina}`);
            renderizarPosts(data.posts, append);
            state.temMais = data.tem_mais;
            if (btn) btn.style.display = data.tem_mais ? "inline-flex" : "none";
        } catch (e) {
            const lista = document.getElementById("feedList");
            if (lista && !append) lista.innerHTML = `<div class="feed-erro">${esc(e.message)}</div>`;
        } finally {
            state.carregando = false;
        }
    }

    async function carregarMais() {
        if (!state.temMais) return;
        state.pagina += 1;
        await carregar(true);
    }

    async function publicar() {
        const input = document.getElementById("feedTexto");
        const conteudo = (input.value || "").trim();
        if (!conteudo) return;
        try {
            await api("/api/feed/posts", { method: "POST", body: JSON.stringify({ conteudo }) });
            input.value = "";
            await carregar(false);
        } catch (e) {
            alert(e.message);
        }
    }

    function toggleEvento() {
        const form = document.getElementById("feedEventoForm");
        if (!form) return;
        form.classList.toggle("aberto");
    }

    async function publicarEvento() {
        const titulo = document.getElementById("eventoTitulo").value.trim();
        if (!titulo) {
            alert("Informe o título do evento.");
            return;
        }
        const body = {
            titulo,
            conteudo: document.getElementById("eventoConteudo").value,
            evento_data: document.getElementById("eventoData").value || null,
            evento_local: document.getElementById("eventoLocal").value,
            dias_fixado: parseInt(document.getElementById("eventoDias").value || "1", 10),
        };
        try {
            await api("/api/feed/eventos", { method: "POST", body: JSON.stringify(body) });
            document.getElementById("eventoTitulo").value = "";
            document.getElementById("eventoConteudo").value = "";
            document.getElementById("eventoData").value = "";
            document.getElementById("eventoLocal").value = "";
            document.getElementById("eventoDias").value = "1";
            toggleEvento();
            await carregar(false);
        } catch (e) {
            alert(e.message);
        }
    }

    function abrirPicker(postId, ev) {
        ev.stopPropagation();
        document.querySelectorAll(".feed-picker.aberto").forEach((el) => el.classList.remove("aberto"));
        const picker = document.querySelector(`[data-picker="${postId}"]`);
        if (picker) picker.classList.toggle("aberto");
    }

    async function reagir(postId, tipo) {
        try {
            const data = await api(`/api/feed/posts/${postId}/reagir`, {
                method: "POST",
                body: JSON.stringify({ tipo }),
            });
            const post = state.posts[postId];
            if (post) {
                post.reacoes = data.reacoes;
                post.total_reacoes = data.total_reacoes;
                post.minha_reacao = data.minha_reacao;
            }
            const card = document.querySelector(`.feed-post[data-post-id="${postId}"]`);
            if (card && post) {
                const stats = card.querySelector(".feed-post-stats");
                const minha = post.minha_reacao;
                const botao = minha && REACOES[minha] ? REACOES[minha] : REACOES.like;
                if (stats) {
                    stats.querySelector(".feed-r-summary")?.remove();
                    stats.insertAdjacentHTML("afterbegin", reacoesResumoHtml(post));
                }
                const actionBtn = card.querySelector(".feed-action-btn");
                if (actionBtn) {
                    actionBtn.classList.toggle("ativa", !!minha);
                    actionBtn.innerHTML = `<span class="feed-action-emoji">${botao.emoji}</span> ${botao.label}`;
                }
            }
            document.querySelectorAll(".feed-picker.aberto").forEach((el) => el.classList.remove("aberto"));
        } catch (e) {
            alert(e.message);
        }
    }

    async function toggleComentarios(postId) {
        const box = document.querySelector(`[data-comentarios="${postId}"]`);
        if (!box) return;
        if (box.style.display !== "none") {
            box.style.display = "none";
            return;
        }
        box.style.display = "block";
        await carregarComentarios(postId);
    }

    function comentarioHtml(c, depth) {
        const podeExcluir = state.privilegiado || c.autor_email === state.email;
        const respostas = (c.respostas || []).map((r) => comentarioHtml(r, depth + 1)).join("");
        return `
            <div class="feed-comentario" style="margin-left:${depth * 28}px">
                <div class="feed-avatar tiny">${avatarHtml(c.autor.profile_picture, c.autor.nome)}</div>
                <div class="feed-comentario-corpo">
                    <div class="feed-comentario-bolha">
                        <span class="feed-comentario-autor">${esc(c.autor.nome)}</span>
                        <span class="feed-comentario-texto">${c.deletado ? "<em>Comentário removido</em>" : esc(c.conteudo).replace(/\n/g, "<br>")}</span>
                    </div>
                    <div class="feed-comentario-acoes">
                        <span>${esc(tempoRelativo(c.criado_em))}</span>
                        ${depth === 0 ? `<button onclick="Feed.responder(${c.post_id}, ${c.id})">Responder</button>` : ""}
                        ${podeExcluir && !c.deletado ? `<button onclick="Feed.deletarComentario(${c.post_id}, ${c.id})">Excluir</button>` : ""}
                    </div>
                    ${respostas}
                </div>
            </div>`;
    }

    async function carregarComentarios(postId) {
        const box = document.querySelector(`[data-comentarios="${postId}"]`);
        const lista = box.querySelector(".feed-comentarios-lista");
        try {
            const data = await api(`/api/feed/posts/${postId}/comentarios`);
            const itens = data.comentarios || [];
            lista.innerHTML = itens.length
                ? itens.map((c) => comentarioHtml(c, 0)).join("")
                : `<div class="feed-comentario-vazio">Nenhum comentário ainda.</div>`;
        } catch (e) {
            lista.innerHTML = `<div class="feed-erro">${esc(e.message)}</div>`;
        }
    }

    let responderPara = { postId: null, parentId: null };

    function responder(postId, parentId) {
        const input = document.querySelector(`[data-input="${postId}"]`);
        if (!input) return;
        responderPara = { postId, parentId };
        input.placeholder = "Escrevendo resposta...";
        input.focus();
    }

    async function comentar(postId) {
        const input = document.querySelector(`[data-input="${postId}"]`);
        const conteudo = (input.value || "").trim();
        if (!conteudo) return;
        const parentId = responderPara.postId === postId ? responderPara.parentId : null;
        try {
            await api(`/api/feed/posts/${postId}/comentarios`, {
                method: "POST",
                body: JSON.stringify({ conteudo, parent_id: parentId }),
            });
            input.value = "";
            input.placeholder = "Escreva um comentário...";
            responderPara = { postId: null, parentId: null };
            const post = state.posts[postId];
            if (post) {
                post.total_comentarios = (post.total_comentarios || 0) + 1;
                const link = document.querySelector(`.feed-post[data-post-id="${postId}"] .feed-r-link`);
                if (link) link.textContent = `${post.total_comentarios} comentário(s)`;
            }
            await carregarComentarios(postId);
        } catch (e) {
            alert(e.message);
        }
    }

    async function deletarComentario(postId, comentarioId) {
        if (!confirm("Remover este comentário?")) return;
        try {
            await api(`/api/feed/comentarios/${comentarioId}`, { method: "DELETE" });
            await carregarComentarios(postId);
        } catch (e) {
            alert(e.message);
        }
    }

    async function deletarPost(postId) {
        if (!confirm("Remover esta publicação?")) return;
        try {
            await api(`/api/feed/posts/${postId}`, { method: "DELETE" });
            await carregar(false);
        } catch (e) {
            alert(e.message);
        }
    }

    async function fixar(postId) {
        const dias = parseInt(prompt("Fixar por quantos dias?", "7") || "0", 10);
        if (!dias || dias < 1) return;
        try {
            await api(`/api/feed/posts/${postId}/fixar`, { method: "POST", body: JSON.stringify({ dias }) });
            await carregar(false);
        } catch (e) {
            alert(e.message);
        }
    }

    async function desfixar(postId) {
        try {
            await api(`/api/feed/posts/${postId}/desfixar`, { method: "POST" });
            await carregar(false);
        } catch (e) {
            alert(e.message);
        }
    }

    document.addEventListener("click", () => {
        document.querySelectorAll(".feed-picker.aberto").forEach((el) => el.classList.remove("aberto"));
    });

    window.Feed = {
        publicar,
        publicarEvento,
        toggleEvento,
        carregarMais,
        reagir,
        abrirPicker,
        toggleComentarios,
        comentar,
        responder,
        deletarComentario,
        deletarPost,
        fixar,
        desfixar,
        reload: () => carregar(false),
    };

    document.addEventListener("DOMContentLoaded", () => {
        const root = document.getElementById("feedApp");
        if (!root) return;
        state.root = root;
        state.email = root.dataset.userEmail || "";
        state.nome = root.dataset.userNome || "";
        state.foto = root.dataset.userFoto || "";
        state.privilegiado = root.dataset.privilegiado === "true";
        carregar(false);
    });
})();
