/**
 * feed.js - Feed Lisboa (página dedicada)
 * Posts, reações, comentários, enquetes, salvos, repost, perfil,
 * busca/filtro, paginação por cursor, @menções e emoji picker.
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
    const EMOJIS = ["😀", "😂", "🥳", "😍", "😎", "👍", "👏", "🙌", "🔥", "🎉", "❤️", "😢", "😮", "🤝", "🚀", "💡", "✅", "📌", "🎂", "☕"];

    const state = {
        root: null,
        email: "",
        nome: "",
        foto: "",
        privilegiado: false,
        gestao: false,
        podeFixar: false,
        mencaoTarget: null,
        autor: "",
        singlePostId: null,
        cursor: null,
        temMais: false,
        carregando: false,
        posts: {},
        salvos: false,
        interacoes: false,
        q: "",
        tipo: "",
        usuarios: [],
        enqueteAberta: false,
        pollTimer: null,
        ultimoPostISO: null,
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

    function semAcento(str) {
        return String(str || "")
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .toLowerCase();
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
        return d.toLocaleString("pt-BR", { day: "2-digit", month: "long", hour: "2-digit", minute: "2-digit" });
    }

    function dataCompleta(iso) {
        if (!iso) return "";
        const d = new Date(iso);
        return isNaN(d) ? "" : d.toLocaleString("pt-BR");
    }

    function avatarHtml(foto, nome, cls) {
        const extra = cls ? ` ${cls}` : "";
        if (foto) return `<img src="/static/images/profile_pictures/${esc(foto)}" alt="${esc(nome)}">`;
        return `<i class="fa-solid fa-user-tie${extra}"></i>`;
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

    function pingar(post) {
        if (!post.fixado) return false;
        if (!post.fixado_ate) return true;
        return new Date(post.fixado_ate) > new Date();
    }

    function badgeTipo(post) {
        const map = {
            evento: '<span class="feed-badge evento"><i class="fa-regular fa-calendar"></i> Evento</span>',
            aniversario: '<span class="feed-badge aniversario"><i class="fa-solid fa-cake-candles"></i> Aniversário</span>',
            enquete: '<span class="feed-badge enquete"><i class="fa-solid fa-square-poll-vertical"></i> Enquete</span>',
            repost: '<span class="feed-badge repost"><i class="fa-solid fa-retweet"></i> Repost</span>',
        };
        return map[post.tipo] || "";
    }

    function badgesExtras(post) {
        let out = "";
        if (post.editado) out += `<span class="feed-badge editado" title="${esc(dataCompleta(post.editado_em))}">editado</span>`;
        const nomes = (post.squads_destino || []).map((s) => s.nome).filter(Boolean);
        if (!post.dest_todos && nomes.length) {
            out += `<span class="feed-badge visib"><i class="fa-solid fa-lock"></i> ${esc(nomes.join(", "))}</span>`;
        }
        if (post.oculto) out += `<span class="feed-badge oculto"><i class="fa-solid fa-eye-slash"></i> Oculto</span>`;
        return out;
    }

    // ── Render de cards ──────────────────────────────────────────────────────
    function reacoesResumoHtml(post) {
        const ativas = Object.entries(post.reacoes || {}).filter(([, q]) => q > 0);
        if (!ativas.length) return "";
        const emojis = ativas.map(([t]) => (REACOES[t] ? REACOES[t].emoji : t)).join(" ");
        return `<span class="feed-r-summary"><span class="feed-r-emojis">${emojis}</span> ${post.total_reacoes}</span>`;
    }

    function enqueteHtml(post) {
        if (post.tipo !== "enquete" || !post.enquete) return "";
        const { opcoes = [], total = 0, minha_opcao } = post.enquete;
        const podeVer = post.autor_email === state.email || state.gestao;
        const linhas = opcoes
            .map((o, i) => {
                const pct = total ? Math.round((o.votos / total) * 100) : 0;
                const votada = minha_opcao === i;
                return `<button type="button" class="feed-enquete-opcao ${votada ? "votada" : ""}" onclick="Feed.votar(${post.id}, ${i})">
                    <span class="feed-enquete-barra" style="width:${pct}%"></span>
                    <span class="feed-enquete-texto">${esc(o.texto)}${votada ? ' <i class="fa-solid fa-circle-check"></i>' : ""}</span>
                    <span class="feed-enquete-pct">${pct}%</span>
                </button>`;
            })
            .join("");
        const verBtn = podeVer
            ? ` · <button type="button" class="feed-enquete-ver" onclick="Feed.verVotantes(${post.id})">Ver votantes</button>`
            : "";
        return `<div class="feed-enquete">${linhas}<div class="feed-enquete-total">${total} voto(s)${verBtn}</div></div>`;
    }

    function verVotantes(postId) {
        const post = state.posts[postId];
        if (!post || !post.enquete) return;
        const opcoes = post.enquete.opcoes || [];
        const corpo = opcoes.map((o) => {
            const votantes = o.votantes || [];
            const nomes = votantes.length
                ? votantes.slice(0, 50).map((v) =>
                    `<div class="feed-enquete-votante"><div class="feed-avatar tiny">${avatarHtml(v.profile_picture, v.nome)}</div><span>${esc(v.nome)}</span></div>`).join("")
                : `<div class="feed-enquete-vazio">Ninguém votou ainda</div>`;
            const resto = votantes.length > 50
                ? `<div class="feed-enquete-votante-mais">+${votantes.length - 50} mais</div>` : "";
            return `<div class="feed-enquete-grupo">
                <div class="feed-enquete-grupo-head">
                    <span class="feed-enquete-grupo-titulo">${esc(o.texto)}</span>
                    <span class="feed-enquete-grupo-qtd">${o.votos} voto(s)</span>
                </div>
                <div class="feed-enquete-votantes-modal">${nomes}${resto}</div>
            </div>`;
        }).join("");
        HubModal.alert(corpo, { html: true, title: "Quem votou", okLabel: "Fechar", wide: true });
    }

    function originalHtml(post) {
        if (post.tipo !== "repost" || !post.original) return "";
        const o = post.original;
        if (o.deletado) return `<div class="feed-repost-box feed-repost-deletado">Publicação original removida.</div>`;
        return `<div class="feed-repost-box">
            <div class="feed-repost-head">
                <div class="feed-avatar tiny">${avatarHtml(o.autor.profile_picture, o.autor.nome)}</div>
                <span class="feed-repost-autor">${esc(o.autor.nome)}</span>
                <span class="feed-repost-meta">${esc(tempoRelativo(o.criado_em))}</span>
            </div>
            ${o.titulo ? `<div class="feed-repost-titulo">${esc(o.titulo)}</div>` : ""}
            <div class="feed-repost-conteudo">${o.conteudo_html || esc(o.conteudo)}</div>
        </div>`;
    }

    function cardHtml(post) {
        const pinAtivo = pingar(post);
        const minha = post.minha_reacao;
        const meuBotao = minha && REACOES[minha] ? REACOES[minha] : REACOES.like;
        const gerenciaPost = state.gestao || post.autor_email === state.email;
        const podeFixarPost = state.podeFixar || post.autor_email === state.email;

        let evento = "";
        if (post.tipo === "evento") {
            evento = `<div class="feed-evento-box">
                <div class="feed-evento-titulo"><i class="fa-regular fa-calendar"></i> ${esc(post.titulo || "Evento")}</div>
                ${post.evento_data ? `<div class="feed-evento-meta"><i class="fa-regular fa-clock"></i> ${esc(formatarData(post.evento_data))}</div>` : ""}
                ${post.evento_local ? `<div class="feed-evento-meta"><i class="fa-solid fa-location-dot"></i> ${esc(post.evento_local)}</div>` : ""}
            </div>`;
        }

        const itensMenu = [];
        if (!state.singlePostId) {
            itensMenu.push(`<button onclick="window.location.href='/feed/post/${post.id}'"><i class="fa-solid fa-up-right-from-square"></i> Abrir publicação</button>`);
        }
        if (podeFixarPost) itensMenu.push(pinAtivo
            ? `<button onclick="Feed.desfixar(${post.id})"><i class="fa-solid fa-thumbtack"></i> Desfixar</button>`
            : `<button onclick="Feed.fixar(${post.id})"><i class="fa-solid fa-thumbtack"></i> Fixar</button>`);
        if (post.autor_email === state.email && ["post", "enquete", "repost"].includes(post.tipo)) {
            itensMenu.push(`<button onclick="Feed.editar(${post.id})"><i class="fa-solid fa-pen"></i> Editar</button>`);
        }
        if (gerenciaPost) {
            itensMenu.push(post.oculto
                ? `<button onclick="Feed.ocultar(${post.id}, false)"><i class="fa-solid fa-eye"></i> Reexibir</button>`
                : `<button onclick="Feed.ocultar(${post.id}, true)"><i class="fa-solid fa-eye-slash"></i> Ocultar</button>`);
        }
        if (post.autor_email !== state.email) {
            itensMenu.push(`<button onclick="Feed.denunciar(${post.id})"><i class="fa-solid fa-flag"></i> Denunciar</button>`);
        }
        if (gerenciaPost) {
            itensMenu.push(`<button class="danger" onclick="Feed.deletarPost(${post.id})"><i class="fa-solid fa-trash"></i> Excluir</button>`);
        }

        // Autor do sistema (posts automáticos): não clicável, ícone e selo próprios
        const sis = !!(post.autor && post.autor.sistema);
        const avatarCls = `feed-avatar small ${sis ? "sistema" : "clickable"}`;
        const avatarClick = sis ? "" : ` onclick="Feed.abrirPerfil('${esc(post.autor_email)}')"`;
        const avatarInner = sis
            ? (post.autor.profile_picture
                ? `<img src="/static/images/profile_pictures/${esc(post.autor.profile_picture)}" alt="${esc(post.autor.nome)}">`
                : `<i class="fa-solid ${esc(post.autor.icone || "fa-robot")}"></i>`)
            : avatarHtml(post.autor.profile_picture, post.autor.nome);
        const nomeHtml = sis
            ? `<span>${esc(post.autor.nome)}</span>`
            : `<span class="clickable" onclick="Feed.abrirPerfil('${esc(post.autor_email)}')">${esc(post.autor.nome)}</span>`;
        const seloSistema = sis ? `<span class="feed-badge sistema"><i class="fa-solid fa-robot"></i> Sistema</span>` : "";

        return `
        <article class="feed-post ${pinAtivo ? "is-pinned" : ""} ${post.oculto ? "is-oculto" : ""}" data-post-id="${post.id}">
            ${pinAtivo ? `<div class="feed-pin-flag"><i class="fa-solid fa-thumbtack"></i> Fixado</div>` : ""}
            <header class="feed-post-head">
                <div class="${avatarCls}"${avatarClick}>${avatarInner}</div>
                <div class="feed-post-head-info">
                    <div class="feed-post-autor">
                        ${nomeHtml}
                        ${seloSistema}${badgeTipo(post)} ${badgesExtras(post)}
                    </div>
                    <div class="feed-post-meta" title="${esc(dataCompleta(post.criado_em))}">${esc(post.autor.funcao || "")} · <a class="feed-post-permalink" href="/feed/post/${post.id}">${esc(tempoRelativo(post.criado_em))}</a></div>
                </div>
                <div class="feed-post-menu-wrap">
                    <button class="feed-ico-btn feed-save-btn ${post.salvo ? "ativa" : ""}" onclick="Feed.salvar(${post.id})" title="${post.salvo ? "Remover dos salvos" : "Salvar"}"><i class="fa-${post.salvo ? "solid" : "regular"} fa-bookmark"></i></button>
                    <button class="feed-ico-btn" onclick="Feed.toggleMenu(${post.id}, event)"><i class="fa-solid fa-ellipsis"></i></button>
                    <div class="feed-post-menu" data-menu="${post.id}">${itensMenu.join("")}</div>
                </div>
            </header>
            ${evento}
            ${post.conteudo_html ? `<div class="feed-post-conteudo">${post.conteudo_html}</div>` : ""}
            ${enqueteHtml(post)}
            ${originalHtml(post)}
            <div class="feed-post-stats">
                ${reacoesResumoHtml(post)}
                <button class="feed-r-link" onclick="Feed.toggleComentarios(${post.id})">${post.total_comentarios} comentário(s)</button>
            </div>
            <div class="feed-post-actions">
                <div class="feed-reaction-wrap">
                    <button class="feed-action-btn ${minha ? "ativa" : ""}" onclick="Feed.abrirPicker(${post.id}, event)">
                        ${minha && meuBotao.emoji ? `<span class="feed-action-emoji">${meuBotao.emoji}</span> ${meuBotao.label}` : meuBotao.label}
                    </button>
                    <div class="feed-picker" data-picker="${post.id}"></div>
                </div>
                <button class="feed-action-btn" onclick="Feed.toggleComentarios(${post.id})"><i class="fa-regular fa-comment"></i> Comentar</button>
                <button class="feed-action-btn" onclick="Feed.repostar(${post.id})" title="Repostar"><i class="fa-solid fa-retweet"></i></button>
            </div>
            <div class="feed-comentarios" data-comentarios="${post.id}" style="display:none;">
                <div class="feed-comentarios-lista"></div>
                <div class="feed-mencao-box"></div>
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
        if (append) lista.insertAdjacentHTML("beforeend", html);
        else lista.innerHTML = html || `<div class="feed-vazio"><i class="fa-regular fa-face-smile"></i> Nenhuma publicação por aqui.</div>`;
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

    // ── Carregamento ─────────────────────────────────────────────────────────
    async function carregar(append) {
        if (state.carregando) return;
        state.carregando = true;
        if (!append) state.cursor = null;

        const listaParam = new URLSearchParams({ por_pagina: "10" });
        if (state.cursor) listaParam.set("cursor", state.cursor);
        if (state.q) listaParam.set("q", state.q);
        if (state.tipo) listaParam.set("tipo", state.tipo);
        if (state.salvos) listaParam.set("salvos", "1");
        if (state.autor) listaParam.set("autor", state.autor);

        const endpoint = state.interacoes
            ? `/api/feed/minhas-interacoes?por_pagina=20`
            : `/api/feed/posts?${listaParam.toString()}`;

        try {
            const data = await api(endpoint);
            renderizarPosts(data.posts, append);
            state.temMais = data.tem_mais;
            state.cursor = data.proximo_cursor;
            const btn = document.getElementById("feedCarregarMais");
            if (btn) btn.style.display = data.tem_mais ? "inline-flex" : "none";
            if (!append) {
                const primeiros = data.posts.filter((p) => p.criado_em);
                if (primeiros.length) state.ultimoPostISO = primeiros[0].criado_em;
            }
            esconderNovos();
        } catch (e) {
            if (!append) document.getElementById("feedList").innerHTML = `<div class="feed-erro">${esc(e.message)}</div>`;
        } finally {
            state.carregando = false;
        }
    }

    async function carregarMais() {
        if (!state.temMais || state.carregando) return;
        await carregar(true);
    }

    async function carregarNovos() {
        await carregar(false);
    }

    function esconderNovos() {
        const el = document.getElementById("feedNovos");
        if (el) el.classList.remove("visivel");
    }

    // Modo página única (permalink) de uma publicação
    async function carregarPostUnico(id) {
        const lista = document.getElementById("feedList");
        try {
            const data = await api(`/api/feed/posts/${id}`);
            if (!data.post) throw new Error("Publicação não encontrada.");
            renderizarPosts([data.post], false);

            // Abre os comentários
            const box = document.querySelector(`[data-comentarios="${id}"]`);
            if (box) {
                box.style.display = "block";
                await carregarComentarios(id);
            }

            // Rola até o comentário alvo (?comentario=<id>)
            const cid = new URLSearchParams(window.location.search).get("comentario");
            if (cid) {
                setTimeout(() => {
                    const el = document.querySelector(`[data-comentario-id="${cid}"]`);
                    if (el) {
                        el.scrollIntoView({ behavior: "smooth", block: "center" });
                        el.classList.add("comentario-destaque");
                    }
                }, 250);
            }
        } catch (e) {
            if (lista) lista.innerHTML = `<div class="feed-erro">${esc(e.message)}</div>`;
        }
    }

    // ── Composer ─────────────────────────────────────────────────────────────
    function atualizarContador() {
        const t = document.getElementById("feedTexto");
        const el = document.getElementById("feedCharCount");
        if (t && el) el.textContent = `${t.value.length}/3000`;
    }

    // ── Canais de envio (destinos) ───────────────────────────────────────────
    function toggleCanais(ev) {
        if (ev) ev.stopPropagation();
        const p = document.getElementById("feedCanaisPanel");
        if (p) p.classList.toggle("aberto");
    }

    function atualizarCanais() {
        const todos = document.getElementById("feedDestTodos");
        const squads = [...document.querySelectorAll(".feed-canal-squad")];
        const todosMarcado = !!(todos && todos.checked);
        if (todosMarcado) squads.forEach((c) => { c.checked = false; });
        squads.forEach((c) => { c.disabled = todosMarcado; });

        const label = document.getElementById("feedCanaisLabel");
        if (!label) return;
        const ativas = squads.filter((c) => c.checked);
        if (todosMarcado || ativas.length === 0) {
            label.textContent = "Todos";
        } else if (ativas.length <= 2) {
            label.textContent = ativas
                .map((c) => (c.parentElement.querySelector("span") || {}).textContent || "")
                .join(", ");
        } else {
            label.textContent = `${ativas.length} squads`;
        }
    }

    function coletarCanais() {
        const todos = document.getElementById("feedDestTodos");
        const destTodos = todos ? todos.checked : true;
        const squads = [...document.querySelectorAll(".feed-canal-squad:checked")].map((c) => parseInt(c.value, 10));
        if (destTodos || squads.length === 0) return { dest_todos: true, squads: [] };
        return { dest_todos: false, squads };
    }

    async function publicar() {
        const input = document.getElementById("feedTexto");
        const conteudo = (input.value || "").trim();
        if (!conteudo) return;
        if (state.enqueteAberta) return publicarEnquete(conteudo);
        const canais = coletarCanais();
        try {
            await api("/api/feed/posts", { method: "POST", body: JSON.stringify({ conteudo, ...canais }) });
            input.value = "";
            atualizarContador();
            fecharEnquete();
            await carregar(false);
            await carregarWidgets();
        } catch (e) {
            alert(e.message);
        }
    }

    function toggleEnquete() {
        state.enqueteAberta = !state.enqueteAberta;
        const form = document.getElementById("feedEnqueteForm");
        if (!form) return;
        form.classList.toggle("aberto", state.enqueteAberta);
        if (state.enqueteAberta && !document.querySelector(".feed-enquete-opcao-input")) {
            addOpcaoEnquete();
            addOpcaoEnquete();
        }
    }

    function fecharEnquete() {
        state.enqueteAberta = false;
        const form = document.getElementById("feedEnqueteForm");
        if (form) form.classList.remove("aberto");
        const box = document.getElementById("feedEnqueteOpcoes");
        if (box) box.innerHTML = "";
    }

    function addOpcaoEnquete() {
        const box = document.getElementById("feedEnqueteOpcoes");
        if (!box) return;
        if (box.querySelectorAll(".feed-enquete-opcao-input").length >= 6) return;
        const div = document.createElement("div");
        div.className = "feed-enquete-opcao-linha";
        div.innerHTML = `<input type="text" class="feed-enquete-opcao-input" placeholder="Opção" maxlength="80">
            <button type="button" class="feed-ico-btn" onclick="this.parentElement.remove()"><i class="fa-solid fa-xmark"></i></button>`;
        box.appendChild(div);
    }

    async function publicarEnquete(pergunta) {
        const inputs = [...document.querySelectorAll(".feed-enquete-opcao-input")];
        const opcoes = inputs.map((i) => i.value.trim()).filter(Boolean);
        if (opcoes.length < 2) {
            alert("A enquete precisa de pelo menos 2 opções.");
            return;
        }
        const canais = coletarCanais();
        try {
            await api("/api/feed/enquetes", { method: "POST", body: JSON.stringify({ pergunta, opcoes, ...canais }) });
            document.getElementById("feedTexto").value = "";
            atualizarContador();
            fecharEnquete();
            await carregar(false);
        } catch (e) {
            alert(e.message);
        }
    }

    function toggleEvento() {
        const form = document.getElementById("feedEventoForm");
        if (form) form.classList.toggle("aberto");
    }

    async function publicarEvento() {
        const titulo = document.getElementById("eventoTitulo").value.trim();
        if (!titulo) return alert("Informe o título do evento.");
        const body = {
            titulo,
            conteudo: document.getElementById("eventoConteudo").value,
            evento_data: document.getElementById("eventoData").value || null,
            evento_local: document.getElementById("eventoLocal").value,
            dias_fixado: parseInt(document.getElementById("eventoDias").value || "1", 10),
            ...coletarCanais(),
        };
        try {
            await api("/api/feed/eventos", { method: "POST", body: JSON.stringify(body) });
            ["eventoTitulo", "eventoConteudo", "eventoData", "eventoLocal"].forEach((id) => (document.getElementById(id).value = ""));
            document.getElementById("eventoDias").value = "1";
            toggleEvento();
            await carregar(false);
            await carregarWidgets();
        } catch (e) {
            alert(e.message);
        }
    }

    // ── Emoji + menções ──────────────────────────────────────────────────────
    function toggleEmoji(ev) {
        if (ev) ev.stopPropagation();
        const p = document.getElementById("feedEmojiPicker");
        if (!p) return;
        if (!p.dataset.pronto) {
            p.innerHTML = EMOJIS.map((e) => `<button type="button" data-emoji="${e}">${e}</button>`).join("");
            // Delegação: clicar num emoji insere no textarea e mantém o picker aberto
            p.addEventListener("click", (evt) => {
                const btn = evt.target.closest("[data-emoji]");
                if (btn) inserirNoTextarea(btn.dataset.emoji);
            });
            p.dataset.pronto = "1";
        }
        p.classList.toggle("aberto");
    }

    function inserirNoTextarea(txt) {
        const t = document.getElementById("feedTexto");
        const start = t.selectionStart || t.value.length;
        const end = t.selectionEnd || t.value.length;
        t.value = t.value.slice(0, start) + txt + t.value.slice(end);
        t.selectionStart = t.selectionEnd = start + txt.length;
        t.focus();
        atualizarContador();
    }

    function boxMencaoDoCampo(inputEl) {
        if (!inputEl) return null;
        if (inputEl.id === "feedTexto") return document.getElementById("feedMencaoBox");
        const cont = inputEl.closest("[data-comentarios]");
        return cont ? cont.querySelector(".feed-mencao-box") : null;
    }

    function mostrarMencoes(inputEl) {
        const box = boxMencaoDoCampo(inputEl);
        if (!box) return;
        const val = inputEl.value || "";
        const pos = inputEl.selectionStart != null ? inputEl.selectionStart : val.length;
        const antes = val.slice(0, pos);
        const m = antes.match(/@([A-Za-z0-9._%+\-]*)$/);
        if (!m) {
            box.classList.remove("aberto");
            box.innerHTML = "";
            return;
        }
        const termo = semAcento(m[1]);
        const sugestoes = state.usuarios
            .filter((u) => semAcento(u.nome).includes(termo) || semAcento(u.email).includes(termo))
            .slice(0, 6);
        if (!sugestoes.length) {
            box.classList.remove("aberto");
            box.innerHTML = "";
            return;
        }
        state.mencaoTarget = inputEl;
        box.innerHTML = sugestoes
            .map(
                (u) => `<button type="button" class="feed-mencao-item" onclick="Feed.inserirMencao('${esc(u.email)}')">
                    <span class="feed-avatar tiny">${avatarHtml(u.profile_picture, u.nome)}</span>
                    <span>${esc(u.nome)}</span><small>${esc(u.email)}</small>
                </button>`
            )
            .join("");
        box.classList.add("aberto");
    }

    function aoDigitar(e) {
        atualizarContador();
        mostrarMencoes(e.target);
    }

    function fecharMencoes() {
        document.querySelectorAll(".feed-mencao-box.aberto").forEach((el) => el.classList.remove("aberto"));
    }

    function inserirMencao(email) {
        const t = state.mencaoTarget || document.getElementById("feedTexto");
        if (!t) return;
        const pos = t.selectionStart != null ? t.selectionStart : (t.value || "").length;
        const antes = (t.value || "").slice(0, pos).replace(/@([A-Za-z0-9._%+\-]*)$/, "");
        t.value = `${antes}@${email} ` + (t.value || "").slice(pos);
        t.selectionStart = t.selectionEnd = antes.length + email.length + 2;
        const box = boxMencaoDoCampo(t);
        if (box) box.classList.remove("aberto");
        t.focus();
        if (t.id === "feedTexto") atualizarContador();
    }

    // ── Reações / salvos / repost ────────────────────────────────────────────
    function abrirPicker(postId, ev) {
        ev.stopPropagation();
        document.querySelectorAll(".feed-picker.aberto").forEach((el) => el.classList.remove("aberto"));
        const picker = document.querySelector(`[data-picker="${postId}"]`);
        if (picker) picker.classList.toggle("aberto");
    }

    async function reagir(postId, tipo) {
        try {
            const data = await api(`/api/feed/posts/${postId}/reagir`, { method: "POST", body: JSON.stringify({ tipo }) });
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
                    const old = stats.querySelector(".feed-r-summary");
                    if (old) old.remove();
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

    async function salvar(postId) {
        try {
            const data = await api(`/api/feed/posts/${postId}/salvar`, { method: "POST" });
            if (state.posts[postId]) state.posts[postId].salvo = data.salvo;
            const card = document.querySelector(`.feed-post[data-post-id="${postId}"]`);
            const btn = card && card.querySelector(".feed-save-btn");
            if (btn) {
                btn.classList.toggle("ativa", data.salvo);
                btn.title = data.salvo ? "Remover dos salvos" : "Salvar";
                btn.innerHTML = `<i class="fa-${data.salvo ? "solid" : "regular"} fa-bookmark"></i>`;
            }
            if (state.salvos && !data.salvo) carregar(false);
        } catch (e) {
            alert(e.message);
        }
    }

    async function repostar(postId) {
        const comentario = (await HubModal.prompt("Comentário no repost (opcional):")) || "";
        try {
            await api(`/api/feed/posts/${postId}/repostar`, { method: "POST", body: JSON.stringify({ comentario, ...coletarCanais() }) });
            await carregar(false);
        } catch (e) {
            alert(e.message);
        }
    }

    async function votar(postId, opcaoIndex) {
        try {
            const data = await api(`/api/feed/posts/${postId}/votar`, { method: "POST", body: JSON.stringify({ opcao_index: opcaoIndex }) });
            const post = state.posts[postId];
            if (post) post.enquete = Object.assign(post.enquete, data);
            const card = document.querySelector(`.feed-post[data-post-id="${postId}"]`);
            if (card) {
                const box = card.querySelector(".feed-enquete");
                if (box) box.outerHTML = enqueteHtml(post);
            }
        } catch (e) {
            alert(e.message);
        }
    }

    // ── Menu de ações ────────────────────────────────────────────────────────
    function toggleMenu(postId, ev) {
        ev.stopPropagation();
        document.querySelectorAll(".feed-post-menu.aberto").forEach((el) => el.classList.remove("aberto"));
        const menu = document.querySelector(`[data-menu="${postId}"]`);
        if (menu) menu.classList.toggle("aberto");
    }

    async function editar(postId) {
        const post = state.posts[postId];
        if (!post) return;
        const novo = await HubModal.prompt("Editar publicação:", { defaultValue: post.conteudo || "" });
        if (novo === null) return;
        try {
            const data = await api(`/api/feed/posts/${postId}/editar`, { method: "POST", body: JSON.stringify({ conteudo: novo }) });
            Object.assign(post, data);
            const card = document.querySelector(`.feed-post[data-post-id="${postId}"]`);
            const conteudo = card && card.querySelector(".feed-post-conteudo");
            if (conteudo) conteudo.innerHTML = data.conteudo_html || esc(data.conteudo);
            await carregar(false);
        } catch (e) {
            alert(e.message);
        }
    }

    async function fixar(postId) {
        const dias = parseInt((await HubModal.prompt("Fixar por quantos dias?", { defaultValue: "7" })) || "0", 10);
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

    async function ocultar(postId, ocultarFlag) {
        try {
            await api(`/api/feed/posts/${postId}/${ocultarFlag ? "ocultar" : "desocultar"}`, { method: "POST" });
            await carregar(false);
        } catch (e) {
            alert(e.message);
        }
    }

    async function denunciar(postId) {
        const motivo = (await HubModal.prompt("Motivo da denúncia (opcional):")) || "";
        try {
            await api(`/api/feed/posts/${postId}/denunciar`, { method: "POST", body: JSON.stringify({ motivo }) });
            alert("Denúncia registrada. Obrigado!");
        } catch (e) {
            alert(e.message);
        }
    }

    async function deletarPost(postId) {
        if (!(await HubModal.confirm("Remover esta publicação?", { okLabel: "Remover", danger: true }))) return;
        try {
            await api(`/api/feed/posts/${postId}`, { method: "DELETE" });
            await carregar(false);
        } catch (e) {
            alert(e.message);
        }
    }

    // ── Comentários ──────────────────────────────────────────────────────────
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
        const podeExcluir = state.gestao || c.autor_email === state.email;
        const respostas = (c.respostas || []).map((r) => comentarioHtml(r, depth + 1)).join("");
        const reac = c.reacoes && c.reacoes.like ? c.reacoes.like : 0;
        return `
        <div class="feed-comentario" data-comentario-id="${c.id}" style="margin-left:${depth * 28}px">
            <div class="feed-avatar tiny clickable" onclick="Feed.abrirPerfil('${esc(c.autor_email)}')">${avatarHtml(c.autor.profile_picture, c.autor.nome)}</div>
            <div class="feed-comentario-corpo">
                <div class="feed-comentario-bolha">
                    <span class="feed-comentario-autor">${esc(c.autor.nome)}</span>
                    <span class="feed-comentario-texto">${c.deletado ? "<em>Comentário removido</em>" : (c.conteudo_html || esc(c.conteudo))}</span>
                </div>
                <div class="feed-comentario-acoes">
                    <span>${esc(tempoRelativo(c.criado_em))}</span>
                    ${!c.deletado ? `<button class="${c.minha_reacao === "like" ? "ativo" : ""}" onclick="Feed.reagirComentario(${c.post_id}, ${c.id})">Curtir${reac ? ` (${reac})` : ""}</button>` : ""}
                    ${depth === 0 && !c.deletado ? `<button onclick="Feed.responder(${c.post_id}, ${c.id})">Responder</button>` : ""}
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
            await api(`/api/feed/posts/${postId}/comentarios`, { method: "POST", body: JSON.stringify({ conteudo, parent_id: parentId }) });
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

    async function reagirComentario(postId, comentarioId) {
        try {
            await api(`/api/feed/comentarios/${comentarioId}/reagir`, { method: "POST", body: JSON.stringify({ tipo: "like" }) });
            await carregarComentarios(postId);
        } catch (e) {
            alert(e.message);
        }
    }

    async function deletarComentario(postId, comentarioId) {
        if (!(await HubModal.confirm("Remover este comentário?", { okLabel: "Remover", danger: true }))) return;
        try {
            await api(`/api/feed/comentarios/${comentarioId}`, { method: "DELETE" });
            await carregarComentarios(postId);
        } catch (e) {
            alert(e.message);
        }
    }

    // ── Perfil rápido ────────────────────────────────────────────────────────
    async function abrirPerfil(email) {
        if (!email || email === "sistema") return; // perfil do sistema não abre
        const modal = document.getElementById("feedPerfilModal");
        const body = document.getElementById("feedPerfilBody");
        if (!modal || !email) return;
        body.innerHTML = `<div class="feed-loading"><i class="fa-solid fa-spinner fa-spin"></i></div>`;
        modal.classList.add("aberto");
        try {
            const u = await api(`/api/feed/perfil/${encodeURIComponent(email)}`);
            body.innerHTML = `
                <div class="feed-perfil-top">
                    <div class="feed-avatar big">${avatarHtml(u.profile_picture, u.nome)}</div>
                    <h3>${esc(u.nome)}</h3>
                    <p>${esc(u.funcao || "")}${u.squad ? " · " + esc(u.squad) : ""}</p>
                </div>
                <div class="feed-perfil-grid">
                    <div><span>Senioridade</span><strong>${esc(u.senioridade || "N/A")}</strong></div>
                    <div><span>Tempo de casa</span><strong>${u.tempo_de_casa != null ? u.tempo_de_casa + " ano(s)" : "N/A"}</strong></div>
                    <div><span>Clientes ativos</span><strong>${u.clientes_ativos}</strong></div>
                    <div><span>Aniversário</span><strong>${u.data_nascimento ? esc(new Date(u.data_nascimento).toLocaleDateString("pt-BR")) : "N/A"}</strong></div>
                </div>`;
        } catch (e) {
            body.innerHTML = `<div class="feed-erro">${esc(e.message)}</div>`;
        }
    }

    function fecharPerfil() {
        const modal = document.getElementById("feedPerfilModal");
        if (modal) modal.classList.remove("aberto");
    }

    // ── Filtros / polling ────────────────────────────────────────────────────
    function toggleSalvos() {
        state.salvos = !state.salvos;
        document.getElementById("feedSalvosBtn").classList.toggle("ativo", state.salvos);
        carregar(false);
    }

    // Modo perfil: abas "Minhas postagens" / "Salvos"
    async function modoPerfil(tab) {
        const salvos = tab === "salvos";
        const interacoes = tab === "interacoes";
        state.salvos = salvos;
        state.interacoes = interacoes;
        state.autor = (salvos || interacoes) ? "" : state.email;
        const pa = document.getElementById("perfilAbaPosts");
        const sa = document.getElementById("perfilAbaSalvos");
        const ina = document.getElementById("perfilAbaInteracoes");
        if (pa) pa.classList.toggle("ativa", !salvos && !interacoes);
        if (sa) sa.classList.toggle("ativa", salvos);
        if (ina) ina.classList.toggle("ativa", interacoes);
        const btn = document.getElementById("feedSalvosBtn");
        if (btn) btn.classList.toggle("ativo", salvos);
        await carregar(false);
    }

    let buscaTimer = null;
    function aoBuscar(e) {
        clearTimeout(buscaTimer);
        buscaTimer = setTimeout(() => {
            state.q = e.target.value.trim();
            carregar(false);
        }, 350);
    }

    function aoFiltrarTipo(e) {
        state.tipo = e.target.value;
        carregar(false);
    }

    function iniciarPolling() {
        state.pollTimer = setInterval(async () => {
            if (!state.ultimoPostISO) return;
            try {
                const data = await api(`/api/feed/novos?desde=${encodeURIComponent(state.ultimoPostISO)}`);
                const el = document.getElementById("feedNovos");
                if (data.total > 0 && el) {
                    document.getElementById("feedNovosQtd").textContent = data.total;
                    el.classList.add("visivel");
                }
            } catch (e) {
                /* silencioso */
            }
        }, 30000);
    }

    // ── Widgets ──────────────────────────────────────────────────────────────
    function setWidget(id, html) {
        const el = document.getElementById(id);
        if (el) el.innerHTML = html;
    }

    function renderAniversariantes(itens) {
        if (!itens.length) return setWidget("widgetAniversariantes", `<div class="feed-widget-empty">Sem aniversários nos próximos dias.</div>`);
        setWidget("widgetAniversariantes", itens.map((i) => `
            <div class="feed-widget-item">
                <div class="feed-avatar">${avatarHtml(i.profile_picture, i.nome)}</div>
                <div class="feed-widget-item-info">
                    <div class="feed-widget-item-nome">${esc(i.nome)}${i.eh_hoje ? ' <span class="feed-aniv-hoje">🎉 hoje</span>' : ""}</div>
                    <div class="feed-widget-item-meta">${esc(i.funcao || "")} · ${esc(i.data_ddmm)} · ${i.idade} anos 🎂</div>
                </div>
            </div>`).join(""));
    }

    function renderEventosWidget(itens) {
        if (!itens.length) return setWidget("widgetEventos", `<div class="feed-widget-empty">Nenhum evento agendado.</div>`);
        setWidget("widgetEventos", itens.map((e) => `
            <div class="feed-widget-post">
                <div class="feed-widget-post-titulo">${esc(e.titulo || "Evento")}</div>
                <div class="feed-widget-post-meta"><i class="fa-regular fa-clock"></i> ${esc(formatarData(e.evento_data))}${e.evento_local ? " · " + esc(e.evento_local) : ""}</div>
            </div>`).join(""));
    }

    function renderEmAlta(itens) {
        if (!itens.length) return setWidget("widgetEmAlta", `<div class="feed-widget-empty">Sem publicações em alta.</div>`);
        setWidget("widgetEmAlta", itens.map((p) => {
            const base = p.titulo || (p.conteudo || "").slice(0, 70) || "Publicação";
            return `<div class="feed-widget-post">
                <div class="feed-widget-post-titulo">${esc(base)}</div>
                <div class="feed-widget-post-meta">${esc(p.autor.nome)} · ${p.total_reacoes} reação(ões)</div>
            </div>`;
        }).join(""));
    }

    function renderRanking(itens) {
        if (!itens.length) return setWidget("widgetRanking", `<div class="feed-widget-empty">Sem participação nesta semana.</div>`);
        setWidget("widgetRanking", itens.map((u, idx) => `
            <div class="feed-widget-item">
                <span class="feed-widget-rank">${idx + 1}º</span>
                <div class="feed-avatar">${avatarHtml(u.profile_picture, u.nome)}</div>
                <div class="feed-widget-item-info">
                    <div class="feed-widget-item-nome">${esc(u.nome)}</div>
                    <div class="feed-widget-item-meta">${u.posts} post(s) · ${u.reacoes} reação(ões) · ${u.comentarios} comentário(s)</div>
                </div>
            </div>`).join(""));
    }

    async function carregarWidgets() {
        if (!document.getElementById("widgetAniversariantes")) return;
        try {
            const data = await api("/api/feed/widgets");
            renderAniversariantes(data.aniversariantes_mes || []);
            renderEventosWidget(data.proximos_eventos || []);
            renderEmAlta(data.em_alta || []);
            renderRanking(data.ranking || []);
        } catch (e) {
            console.error("Erro ao carregar widgets:", e);
        }
    }

    async function carregarUsuarios() {
        try {
            const data = await api("/api/feed/usuarios");
            state.usuarios = data.usuarios || [];
        } catch (e) {
            state.usuarios = [];
        }
    }

    // ── Eventos globais ──────────────────────────────────────────────────────
    document.addEventListener("click", (event) => {
        // Emoji picker: fecha só em clique fora (clicar num emoji mantém aberto)
        if (!event.target.closest("#feedEmojiPicker")) {
            document.querySelectorAll(".feed-emoji-picker.aberto").forEach((el) => el.classList.remove("aberto"));
        }
        // Canais: fecha em clique fora
        if (!event.target.closest("#feedCanais")) {
            document.querySelectorAll(".feed-canais-panel.aberto").forEach((el) => el.classList.remove("aberto"));
        }
        // Menções: fecha em clique fora
        if (!event.target.closest(".feed-mencao-box")) {
            document.querySelectorAll(".feed-mencao-box.aberto").forEach((el) => el.classList.remove("aberto"));
        }
        document.querySelectorAll(".feed-picker.aberto").forEach((el) => el.classList.remove("aberto"));
        document.querySelectorAll(".feed-post-menu.aberto").forEach((el) => el.classList.remove("aberto"));
    });

    window.Feed = {
        publicar, publicarEvento, toggleEvento,
        toggleEnquete, addOpcaoEnquete,
        toggleEmoji, inserirMencao,
        toggleCanais, atualizarCanais,
        carregarMais, carregarNovos,
        reagir, abrirPicker, salvar, repostar, votar, verVotantes,
        toggleComentarios, comentar, responder, reagirComentario, deletarComentario,
        toggleMenu, editar, fixar, desfixar, ocultar, denunciar, deletarPost,
        abrirPerfil, fecharPerfil, toggleSalvos, carregarWidgets, modoPerfil,
    };

    document.addEventListener("DOMContentLoaded", () => {
        const root = document.getElementById("feedApp");
        if (!root) return;
        state.root = root;
        state.email = root.dataset.userEmail || "";
        state.nome = root.dataset.userNome || "";
        state.foto = root.dataset.userFoto || "";
        state.privilegiado = root.dataset.privilegiado === "true";
        state.gestao = root.dataset.gestao === "true";
        state.podeFixar = root.dataset.podeFixar === "true";
        state.autor = root.dataset.autor || "";
        state.singlePostId = root.dataset.postId || null;

        const texto = document.getElementById("feedTexto");
        if (texto) {
            texto.addEventListener("input", aoDigitar);
            texto.addEventListener("input", atualizarContador);
        }
        const listaEl = document.getElementById("feedList");
        if (listaEl) {
            // Menções nos comentários (textareas geradas dinamicamente)
            listaEl.addEventListener("input", (e) => {
                if (e.target && e.target.matches("[data-input]")) mostrarMencoes(e.target);
            });
        }
        const busca = document.getElementById("feedBusca");
        if (busca) busca.addEventListener("input", aoBuscar);
        const tipo = document.getElementById("feedTipo");
        if (tipo) tipo.addEventListener("change", aoFiltrarTipo);
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape") {
                fecharPerfil();
                fecharEnquete();
                fecharMencoes();
            }
        });

        atualizarContador();
        carregarUsuarios();
        if (state.singlePostId) {
            carregarPostUnico(state.singlePostId);
        } else {
            carregar(false);
            carregarWidgets();
            iniciarPolling();
        }
    });
})();
