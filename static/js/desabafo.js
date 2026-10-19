/* Desabafo — mural 100% anônimo. Nenhum dado de autor é enviado/exibido. */
(function () {
    let cursor = null;
    let podeModerar = false;
    let carregando = false;

    function esc(s) {
        return String(s == null ? "" : s)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    function rotuloDia(iso) {
        if (!iso) return "";
        const [y, m, d] = iso.split("-").map(Number);
        const alvo = new Date(y, m - 1, d);
        const hoje = new Date(); hoje.setHours(0, 0, 0, 0);
        const diff = Math.round((alvo - hoje) / 86400000);
        if (diff === 0) return "Hoje";
        if (diff === 1) return "Ontem";
        if (diff < 0) return `Há ${-diff} dias`;
        return `${d}/${m}`;
    }

    function itemHtml(p) {
        const cat = p.categoria
            ? `<span class="desabafo-cat">${esc(p.categoria)}</span>`
            : "";
        const mod = podeModerar
            ? `<div class="desabafo-mod">
                   <button type="button" onclick="Desabafo.ocultar(${p.id}, ${!p.oculto})" title="${p.oculto ? 'Reexibir' : 'Ocultar'}">
                       <i class="fa-solid ${p.oculto ? 'fa-eye' : 'fa-eye-slash'}"></i>
                   </button>
                   <button type="button" class="perigo" onclick="Desabafo.excluir(${p.id})" title="Excluir">
                       <i class="fa-solid fa-trash"></i>
                   </button>
               </div>`
            : "";
        return `<article class="desabafo-post ${p.oculto ? 'oculto' : ''}" data-id="${p.id}">
            <div class="desabafo-meta">
                <span class="desabafo-autor"><i class="fa-solid fa-user-secret"></i> Anônimo</span>
                ${cat}
                <span class="desabafo-dia">${esc(rotuloDia(p.criado_dia))}</span>
                ${p.oculto ? '<span class="desabafo-oculto-tag">oculto</span>' : ""}
                ${mod}
            </div>
            <div class="desabafo-texto">${esc(p.conteudo)}</div>
        </article>`;
    }

    function render(itens, append) {
        const lista = document.getElementById("desabafoLista");
        if (!append) lista.innerHTML = "";
        if (!itens.length && !append) {
            lista.innerHTML = '<div class="desabafo-vazio">Nada por aqui ainda. Seja o primeiro a desabafar.</div>';
            document.getElementById("desabafoMais").style.display = "none";
            return;
        }
        lista.insertAdjacentHTML("beforeend", itens.map(itemHtml).join(""));
    }

    async function carregar(reset) {
        if (carregando) return;
        carregando = true;
        try {
            const url = "/api/desabafo" + (reset || !cursor ? "" : "?cursor=" + cursor);
            const r = await fetch(url, { credentials: "same-origin" });
            const data = await r.json();
            if (data.erro) { mostrarStatus(data.erro, true); return; }
            podeModerar = !!data.pode_moderar;
            const itens = data.itens || [];
            render(itens, !(reset || !cursor));
            if (itens.length) cursor = itens[itens.length - 1].id;
            document.getElementById("desabafoMais").style.display = itens.length >= 20 ? "inline-flex" : "none";
        } catch (e) {
            mostrarStatus("Erro ao carregar.", true);
        } finally {
            carregando = false;
        }
    }

    function mostrarStatus(msg, erro) {
        const el = document.getElementById("desabafoStatus");
        el.textContent = msg;
        el.className = "desabafo-status" + (erro ? " erro" : "");
        if (msg) setTimeout(() => { el.textContent = ""; el.className = "desabafo-status"; }, 4000);
    }

    async function publicar() {
        const ta = document.getElementById("desabafoTexto");
        const conteudo = (ta.value || "").trim();
        if (!conteudo) { mostrarStatus("Escreva algo antes de publicar.", true); return; }
        const categoria = document.getElementById("desabafoCategoria").value;
        try {
            const r = await fetch("/api/desabafo", {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ conteudo, categoria }),
            });
            const data = await r.json();
            if (!r.ok) { mostrarStatus(data.error || "Erro ao publicar.", true); return; }
            ta.value = "";
            atualizarCount();
            mostrarStatus("Publicado anonimamente.");
            cursor = null;
            await carregar(true);
        } catch (e) {
            mostrarStatus("Erro ao publicar.", true);
        }
    }

    async function ocultar(id, oculto) {
        const r = await fetch(`/api/desabafo/${id}/ocultar`, {
            method: "POST", credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ oculto }),
        });
        if (r.ok) { cursor = null; carregar(true); }
    }

    async function excluir(id) {
        if (!window.confirm("Excluir definitivamente este desabafo?")) return;
        const r = await fetch(`/api/desabafo/${id}/excluir`, { method: "POST", credentials: "same-origin" });
        if (r.ok) { cursor = null; carregar(true); }
    }

    function atualizarCount() {
        const ta = document.getElementById("desabafoTexto");
        document.getElementById("desabafoCount").textContent = `${ta.value.length}/1000`;
    }

    document.addEventListener("DOMContentLoaded", function () {
        const ta = document.getElementById("desabafoTexto");
        if (!ta) return;
        ta.addEventListener("input", atualizarCount);
        carregar(true);
    });

    window.Desabafo = { publicar, ocultar, excluir, mais: () => carregar(false) };
})();