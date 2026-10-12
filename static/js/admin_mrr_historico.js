/**
 * admin_mrr_historico.js — Edição do histórico mensal de MRR.
 * Funções globais (usadas por onclick no template).
 */
const MRR_H = {
    projeto: null,     // {projeto_pipefy_id, nome}
    linhas: [],
    modal: null,       // {ano, mes}
};

const brlFmt = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });

function api(url, opts) {
    return fetch(url, opts).then(async (r) => {
        const d = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(d.error || "Erro na requisição");
        return d;
    });
}

function preencherMeses() {
    const opts = Array.from({ length: 12 }, (_, i) => i + 1)
        .map((m) => `<option value="${m}">${String(m).padStart(2, "0")}</option>`).join("");
    ["bMesIni", "bMesFim"].forEach((id) => { const el = document.getElementById(id); if (el) el.innerHTML = opts; });
    const agora = new Date();
    const anoSel = document.getElementById("bAnoIni");
    const anoFim = document.getElementById("bAnoFim");
    const mesSel = document.getElementById("bMesIni");
    const mesFim = document.getElementById("bMesFim");
    if (anoSel) anoSel.value = agora.getFullYear();
    if (anoFim) anoFim.value = agora.getFullYear();
    if (mesSel) mesSel.value = agora.getMonth() + 1;
    if (mesFim) mesFim.value = agora.getMonth() + 1;
}

async function carregarProjetos() {
    const busca = document.getElementById("busca").value.trim();
    const lista = document.getElementById("projList");
    lista.innerHTML = '<div class="empty">Carregando...</div>';
    try {
        const data = await api(`/api/admin/mrr-historico/projetos?busca=${encodeURIComponent(busca)}`);
        if (!data.length) { lista.innerHTML = '<div class="empty">Nenhum projeto.</div>'; return; }
        lista.innerHTML = data.map((p) => `
            <div class="proj-item ${MRR_H.projeto && MRR_H.projeto.projeto_pipefy_id === p.projeto_pipefy_id ? "sel" : ""}"
                 onclick="selecionarProjeto(${p.projeto_pipefy_id}, '${(p.nome || "").replace(/'/g, "\\'")}')">
                <strong>${p.nome || ("Projeto " + p.projeto_pipefy_id)}</strong>
                <small>#${p.projeto_pipefy_id} · ${p.linhas} meses · ${p.manuais} manuais</small>
            </div>`).join("");
    } catch (e) { lista.innerHTML = `<div class="empty">${e.message}</div>`; }
}

async function selecionarProjeto(pid, nome) {
    MRR_H.projeto = { projeto_pipefy_id: pid, nome };
    document.querySelectorAll(".proj-item").forEach((el) => el.classList.remove("sel"));
    document.getElementById("editorEmpty").hidden = true;
    document.getElementById("editorContent").hidden = false;
    document.getElementById("projTitle").textContent = `${nome || "Projeto"} (#${pid})`;
    await carregarLinhas();
    carregarProjetos();
}

async function carregarLinhas() {
    if (!MRR_H.projeto) return;
    const pid = MRR_H.projeto.projeto_pipefy_id;
    MRR_H.linhas = await api(`/api/admin/mrr-historico/linhas?projeto=${pid}`);
    renderLinhas();
}

function renderLinhas() {
    const tb = document.getElementById("linhasBody");
    if (!MRR_H.linhas.length) {
        tb.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:1.5rem;">Sem linhas. Use "Preencher lacunas" ou "Reimportar".</td></tr>';
        return;
    }
    let prevFee = null;
    tb.innerHTML = MRR_H.linhas.map((l) => {
        const atual = l.fee != null ? parseFloat(l.fee) : null;
        const variou = prevFee !== null && atual !== null && atual !== prevFee && l.status === "Ativo";
        const sinal = variou ? (atual > prevFee ? "▲" : "▼") : "";
        const antes = prevFee;
        prevFee = atual;
        return `<tr class="${l.manual ? "manual" : ""}">
            <td>${String(l.mes).padStart(2, "0")}/${l.ano}</td>
            <td>${l.fee != null ? l.fee : "—"}${variou ? ` <span class="fee-var" title="Fee variou (era ${antes})">${sinal}</span>` : ""}</td>
            <td>${l.moeda || "—"}</td>
            <td>${l.fee_brl != null ? brlFmt.format(l.fee_brl) : "—"}</td>
            <td>${l.status || "—"}</td>
            <td>${l.manual ? '<span class="pill">manual</span>' : ""}</td>
            <td>${l.observacao || ""}</td>
            <td style="white-space:nowrap;">
                <button class="mini-btn" onclick="editarLinha(${l.ano}, ${l.mes})"><i class="fas fa-pen"></i></button>
                <button class="mini-btn" onclick="excluirLinha(${l.ano}, ${l.mes})"><i class="fas fa-trash"></i></button>
            </td>
        </tr>`;
    }).join("");
}

function editarLinha(ano, mes) {
    const l = MRR_H.linhas.find((x) => x.ano === ano && x.mes === mes);
    if (!l) return;
    MRR_H.modal = { ano, mes };
    document.getElementById("modalTitle").textContent = `Editar ${String(mes).padStart(2, "0")}/${ano}`;
    document.getElementById("mFee").value = l.fee != null ? l.fee : "";
    document.getElementById("mMoeda").value = l.moeda || "BRL";
    document.getElementById("mCotacao").value = l.cotacao_usd != null ? l.cotacao_usd : "";
    document.getElementById("mFeeBrl").value = l.fee_brl != null ? l.fee_brl : "";
    document.getElementById("mStatus").value = l.status || "Ativo";
    document.getElementById("mNome").value = l.nome_projeto || "";
    document.getElementById("mObs").value = l.observacao || "";
    document.getElementById("editModal").classList.add("open");
}

function fecharModal() {
    document.getElementById("editModal").classList.remove("open");
    MRR_H.modal = null;
}

async function salvarLinha() {
    if (!MRR_H.modal) return;
    const body = {
        projeto_pipefy_id: MRR_H.projeto.projeto_pipefy_id,
        ano: MRR_H.modal.ano,
        mes: MRR_H.modal.mes,
        fee: document.getElementById("mFee").value,
        moeda: document.getElementById("mMoeda").value,
        cotacao_usd: document.getElementById("mCotacao").value,
        fee_brl: document.getElementById("mFeeBrl").value,
        status: document.getElementById("mStatus").value,
        nome_projeto: document.getElementById("mNome").value,
        observacao: document.getElementById("mObs").value,
    };
    try {
        await api("/api/admin/mrr-historico/linha", {
            method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
        });
        fecharModal();
        await carregarLinhas();
    } catch (e) { alert(e.message); }
}

async function excluirLinha(ano, mes) {
    if (!(await HubModal.confirm(`Excluir ${String(mes).padStart(2, "0")}/${ano}?`, { okLabel: "Excluir", danger: true }))) return;
    try {
        await api(`/api/admin/mrr-historico/linha?projeto=${MRR_H.projeto.projeto_pipefy_id}&ano=${ano}&mes=${mes}`, { method: "DELETE" });
        await carregarLinhas();
    } catch (e) { alert(e.message); }
}

function ajustarBulk() {
    const acao = document.getElementById("bulkAcao").value;
    const show = (id, on) => { document.getElementById(id).style.display = on ? "flex" : "none"; };
    show("fldFee", ["fee", "preencher"].includes(acao));
    show("fldMoeda", ["fee", "preencher"].includes(acao));
    show("fldStatus", ["status", "preencher"].includes(acao));
}

function _periodo() {
    return {
        ano_ini: document.getElementById("bAnoIni").value,
        mes_ini: document.getElementById("bMesIni").value,
        ano_fim: document.getElementById("bAnoFim").value,
        mes_fim: document.getElementById("bMesFim").value,
    };
}

async function aplicarLote() {
    if (!MRR_H.projeto) return;
    const acao = document.getElementById("bulkAcao").value;
    const pid = MRR_H.projeto.projeto_pipefy_id;
    const p = Object.assign({ projeto_pipefy_id: pid }, _periodo());
    if (acao === "fee" || acao === "preencher") {
        p.fee = document.getElementById("bFee").value;
        p.moeda = document.getElementById("bMoeda").value;
    }
    if (acao === "status" || acao === "preencher") p.status = document.getElementById("bStatus").value;
    if (acao === "churn") {
        p.ano = document.getElementById("bAnoIni").value;
        p.mes = document.getElementById("bMesIni").value;
        if (!(await HubModal.confirm(`Marcar churn em ${p.mes}/${p.ano}? Os meses posteriores serão removidos.`))) return;
    }
    if (acao === "excluir" && !(await HubModal.confirm("Excluir o período selecionado?", { okLabel: "Excluir", danger: true }))) return;
    try {
        const r = await api("/api/admin/mrr-historico/aplicar", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ tipo: acao, params: p }),
        });
        await carregarLinhas();
        carregarProjetos();
        alert("Ação aplicada. " + JSON.stringify(r));
    } catch (e) { alert(e.message); }
}

async function aplicarFeePartir() {
    if (!MRR_H.projeto) return;
    const hoje = new Date();
    document.getElementById("bAnoFim").value = hoje.getFullYear();
    document.getElementById("bMesFim").value = hoje.getMonth() + 1;
    document.getElementById("bulkAcao").value = "fee";
    await aplicarLote();
}

async function reimportar() {
    if (!MRR_H.projeto) return;
    if (!(await HubModal.confirm("Isso apaga e regenera o histórico deste projeto a partir dos dados atuais. Continuar?"))) return;
    try {
        await api("/api/admin/mrr-historico/aplicar", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ tipo: "reimportar", params: { projeto_pipefy_id: MRR_H.projeto.projeto_pipefy_id } }),
        });
        await carregarLinhas();
        carregarProjetos();
    } catch (e) { alert(e.message); }
}

async function carregarInconsistencias() {
    const tb = document.getElementById("inconsBody");
    tb.innerHTML = '<tr><td colspan="5" class="empty">Carregando...</td></tr>';
    try {
        const data = await api("/api/admin/mrr-historico/inconsistencias");
        document.getElementById("inconsCount").textContent = data.length;
        if (!data.length) { tb.innerHTML = '<tr><td colspan="5" class="empty">Nenhuma inconsistência encontrada.</td></tr>'; return; }
        tb.innerHTML = data.map((p) => {
            const ref = p.ano ? `${String(p.mes).padStart(2, "0")}/${p.ano}` : "—";
            const extra = p.tipo === "sem_historico"
                ? `<button class="mini-btn" onclick="reimportarProjeto(${p.projeto_pipefy_id}, '${(p.nome || "").replace(/'/g, "\\'")}')"><i class="fas fa-rotate"></i> Reimportar</button>`
                : "";
            return `<tr>
                <td><span class="tipo-tag tipo-${p.tipo}">${p.tipo}</span></td>
                <td>${p.nome || ("#" + p.projeto_pipefy_id)}</td>
                <td>${ref}</td>
                <td>${p.detalhe || ""}</td>
                <td style="white-space:nowrap;">
                    <button class="mini-btn" onclick="abrirNoEditor(${p.projeto_pipefy_id}, '${(p.nome || "").replace(/'/g, "\\'")}')"><i class="fas fa-pen"></i> Abrir</button>
                    ${extra}
                </td>
            </tr>`;
        }).join("");
    } catch (e) { tb.innerHTML = `<tr><td colspan="5" class="empty">${e.message}</td></tr>`; }
}

function abrirNoEditor(pid, nome) {
    trocarAba("editor");
    selecionarProjeto(pid, nome);
}

async function reimportarProjeto(pid, nome) {
    abrirNoEditor(pid, nome);
    await reimportar();
}

function trocarAba(tab) {
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === tab));
    document.getElementById("tab-editor").classList.toggle("active", tab === "editor");
    document.getElementById("tab-incons").classList.toggle("active", tab === "incons");
    if (tab === "incons") carregarInconsistencias();
}

function exportarCSV() {
    window.location = "/api/admin/mrr-historico/exportar";
}

async function importarCSV(input) {
    const file = input.files && input.files[0];
    if (!file) return;
    if (!(await HubModal.confirm("Importar o CSV? Valores serão marcados como manual."))) { input.value = ""; return; }
    const fd = new FormData();
    fd.append("arquivo", file);
    try {
        const r = await api("/api/admin/mrr-historico/importar", { method: "POST", body: fd });
        alert(`${r.importados} linha(s) importada(s).`);
        if (MRR_H.projeto) carregarLinhas();
        carregarProjetos();
    } catch (e) { alert(e.message); }
    input.value = "";
}

document.addEventListener("DOMContentLoaded", () => {
    preencherMeses();
    ajustarBulk();
    carregarProjetos();
    carregarInconsistencias();
});
