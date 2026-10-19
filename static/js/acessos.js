/* Acessos & Cargos — CRUD de cargos/posições e acessos padrão por tela. */
(function () {
    const DADOS = window.ACESSOS_DATA || {};
    const TELAS = DADOS.telas || [];
    const NIVEIS = [
        ["nenhum", "Nenhum"],
        ["ver", "Ver"],
        ["editar", "Editar"],
    ];

    function toast(msg, erro) {
        if (typeof window.toast !== "undefined" && toast[erro ? "error" : "success"]) {
            toast[erro ? "error" : "success"](msg);
        }
    }

    function el(id) { return document.getElementById(id); }

    function listaChips(containerId, tipo, nomes) {
        const box = el(containerId);
        if (!box) return;
        box.innerHTML = (nomes || []).map(nome =>
            `<span class="adm-chip">${nome}
                <button title="Renomear" onclick="Acessos.renomear('${tipo}', '${nome.replace(/'/g, "\\'")}')"><i class="fas fa-pen"></i></button>
                <button title="Desativar" onclick="Acessos.desativar('${tipo}', '${nome.replace(/'/g, "\\'")}')"><i class="fas fa-trash"></i></button>
            </span>`
        ).join("") || '<span class="hint">Nenhum.</span>';
    }

    function preencherAlvos() {
        const tipo = el("alvoTipo").value;
        const nomes = tipo === "cargo" ? (DADOS.cargos || []) : (DADOS.posicoes || []);
        el("alvoNome").innerHTML = nomes.map(n => `<option value="${n}">${n}</option>`).join("");
    }

    function renderMatriz() {
        const tipo = el("alvoTipo").value;
        const alvo = el("alvoNome").value;
        const box = el("matriz");
        if (!alvo) { box.innerHTML = '<p class="hint">Nenhum alvo.</p>'; return; }
        const mapa = (tipo === "cargo" ? (DADOS.cargo_telas || {}) : (DADOS.posicao_telas || {}))[alvo] || {};

        let html = '<table class="matrix"><tbody>';
        let grupoAtual = null;
        TELAS.forEach(t => {
            if (t.grupo !== grupoAtual) {
                grupoAtual = t.grupo;
                html += `<tr class="grupo"><td colspan="2">${grupoAtual || ""}</td></tr>`;
            }
            const nivel = mapa[t.codigo] || "nenhum";
            const opts = NIVEIS.map(([v, l]) => `<option value="${v}" ${v === nivel ? "selected" : ""}>${l}</option>`).join("");
            html += `<tr><td>${t.nome}</td><td class="nivel">
                <select class="adm-select" data-tela="${t.codigo}">${opts}</select>
            </td></tr>`;
        });
        html += "</tbody></table>";
        box.innerHTML = html;
    }

    async function criar(tipo) {
        const input = el(tipo === "cargo" ? "novoCargo" : "novaPosicao");
        const nome = (input.value || "").trim();
        if (!nome) return;
        const url = tipo === "cargo" ? "/api/admin/cargos" : "/api/admin/posicoes";
        const r = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ acao: "criar", nome }),
        });
        if (r.ok) location.reload();
        else toast("Erro ao criar.", true);
    }

    async function renomear(tipo, nome) {
        const novo = window.prompt(`Novo nome para ${nome}:`, nome);
        if (!novo || novo.trim() === nome) return;
        const url = tipo === "cargo" ? "/api/admin/cargos" : "/api/admin/posicoes";
        const r = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ acao: "renomear", nome, novo: novo.trim() }),
        });
        if (r.ok) location.reload();
        else toast("Erro ao renomear.", true);
    }

    async function desativar(tipo, nome) {
        if (!window.confirm(`Desativar ${nome}?`)) return;
        const url = tipo === "cargo" ? "/api/admin/cargos" : "/api/admin/posicoes";
        const r = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ acao: "desativar", nome }),
        });
        if (r.ok) location.reload();
        else toast("Erro ao desativar.", true);
    }

    async function salvar() {
        const tipo = el("alvoTipo").value;
        const alvo = el("alvoNome").value;
        if (!alvo) return;
        const acessos = {};
        document.querySelectorAll("#matriz select[data-tela]").forEach(sel => {
            acessos[sel.dataset.tela] = sel.value;
        });
        const url = tipo === "cargo" ? "/api/admin/acessos-cargo" : "/api/admin/acessos-posicao";
        const payload = tipo === "cargo" ? { cargo: alvo, acessos } : { posicao: alvo, acessos };
        const r = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        if (r.ok) toast("Acessos salvos.");
        else toast("Erro ao salvar acessos.", true);
    }

    function trocarTipo() {
        preencherAlvos();
        renderMatriz();
    }

    document.addEventListener("DOMContentLoaded", function () {
        if (!el("alvoTipo")) return;
        listaChips("listaCargos", "cargo", DADOS.cargos || []);
        listaChips("listaPosicoes", "posicao", DADOS.posicoes || []);
        preencherAlvos();
        renderMatriz();
    });

    window.Acessos = { criar, renomear, desativar, salvar, trocarTipo, renderMatriz };
})();