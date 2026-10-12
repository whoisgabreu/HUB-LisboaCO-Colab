/**
 * ranking.js — Painel de Ranking (pessoas): clientes ativos, MRR sob gestão e dias sem churn.
 */
let RK_DATA = [];

document.addEventListener("DOMContentLoaded", () => {
    carregarRanking();
    ["rkBusca", "rkRole", "rkSort"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.addEventListener("input", render);
    });
});

function esc(s) {
    return String(s == null ? "" : s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

async function carregarRanking() {
    const load = document.getElementById("rkLoading");
    try {
        const r = await fetch("/api/ranking");
        const data = await r.json();
        if (!r.ok) throw new Error(data.error || "Erro ao carregar");
        RK_DATA = Array.isArray(data) ? data : [];
        preencherCargos();
        if (load) load.style.display = "none";
        render();
    } catch (e) {
        if (load) load.innerHTML = `<span class="rk-erro">Erro ao carregar: ${esc(e.message)}</span>`;
    }
}

function preencherCargos() {
    const sel = document.getElementById("rkRole");
    if (!sel) return;
    const cargos = [...new Set(RK_DATA.map((x) => x.role).filter(Boolean))].sort();
    sel.innerHTML = '<option value="">Todos os cargos</option>' +
        cargos.map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
}

function filtrado() {
    const busca = (document.getElementById("rkBusca")?.value || "").toLowerCase();
    const role = document.getElementById("rkRole")?.value || "";
    const sort = document.getElementById("rkSort")?.value || "clients";
    const arr = RK_DATA.filter((x) =>
        (!role || x.role === role) && (!busca || (x.name || "").toLowerCase().includes(busca))
    );
    arr.sort((a, b) => {
        if (sort === "mrr") return (b.mrr || 0) - (a.mrr || 0);
        if (sort === "days") return (b.daysWithoutChurn || 0) - (a.daysWithoutChurn || 0);
        if ((b.clientsCount || 0) !== (a.clientsCount || 0)) return (b.clientsCount || 0) - (a.clientsCount || 0);
        return (b.mrr || 0) - (a.mrr || 0);
    });
    return arr;
}

function avatar(x) {
    if (x.photo) {
        return `<img class="rk-avatar" src="${esc(x.photo)}" alt="${esc(x.name)}" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"><span class="rk-avatar-ic" style="display:none"><i class="fa-solid fa-user-tie"></i></span>`;
    }
    return `<span class="rk-avatar-ic"><i class="fa-solid fa-user-tie"></i></span>`;
}

function render() {
    const arr = filtrado();
    const top = arr.slice(0, 3);
    const rest = arr.slice(3);

    const top3 = document.getElementById("rkTop3");
    if (top3) {
        top3.innerHTML = top.map((x, i) => `
            <div class="rk-top-card rk-pos-${i + 1}" title="${esc(x.mrr_formatted)} (MRR)">
                <div class="rk-top-rank">${i + 1}º ${i === 0 ? '<i class="fa-solid fa-crown"></i>' : ""}</div>
                ${avatar(x)}
                <div class="rk-top-name">${esc(x.name)}</div>
                <div class="rk-top-role">${esc(x.role)}</div>
                <div class="rk-top-stats">
                    <span><strong>${x.clientsCount}</strong> clientes</span>
                    <span><strong>${esc(x.mrr_formatted)}</strong></span>
                    <span><strong>${x.daysWithoutChurn}</strong> dias s/ churn</span>
                </div>
            </div>`).join("");
    }

    const body = document.getElementById("rkBody");
    if (!body) return;
    if (!arr.length) {
        body.innerHTML = '<tr><td colspan="5" class="rk-empty">Nenhum resultado encontrado.</td></tr>';
        return;
    }
    body.innerHTML = rest.map((x, i) => `
        <tr>
            <td class="rk-pos">#${i + 4}</td>
            <td>
                <div class="rk-pessoa">
                    ${avatar(x)}
                    <div><div class="rk-nome">${esc(x.name)}</div><div class="rk-cargo">${esc(x.role)}</div></div>
                </div>
            </td>
            <td>${x.clientsCount}</td>
            <td>${esc(x.mrr_formatted)}</td>
            <td>${x.daysWithoutChurn}</td>
        </tr>`).join("");
}
