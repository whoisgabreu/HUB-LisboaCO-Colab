/**
 * dashboard_mrr.js — Dashboard histórico de MRR, churn, clientes e LTV.
 * Consome window.MRR_DATA (resumo, serie, ranking) injetado pelo template.
 */
(function () {
    "use strict";

    const DATA = window.MRR_DATA || { resumo: {}, serie: [], ranking: [] };
    const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
    const brlCompact = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", notation: "compact", compactDisplay: "short", maximumFractionDigits: 1 });
    const num = new Intl.NumberFormat("pt-BR");
    const pct = (v) => `${((v || 0) * 100).toFixed(2)}%`;
    const trunc = (s, n) => {
        const t = String(s == null ? "" : s);
        return t.length > n ? t.slice(0, n) + "…" : t;
    };

    let charts = {};

    function el(id) { return document.getElementById(id); }

    function periodoMeses() {
        const sel = el("mrrPeriodo");
        return sel ? parseInt(sel.value, 10) : 24;
    }

    function serieFiltrada() {
        const n = periodoMeses();
        return n > 0 ? DATA.serie.slice(-n) : DATA.serie.slice();
    }

    function renderKpis() {
        const r = DATA.resumo || {};
        if (el("kpiMrr")) el("kpiMrr").textContent = brl.format(r.mrr_atual || 0);
        if (el("kpiMrrRef")) el("kpiMrrRef").textContent = r.ultimo ? `Referência: ${r.ultimo}` : "";

        const delta = el("kpiDelta");
        const deltaPct = el("kpiDeltaPct");
        if (delta) {
            if (r.delta_mrr === null || r.delta_mrr === undefined) {
                delta.textContent = "—";
            } else {
                const up = r.delta_mrr >= 0;
                delta.textContent = `${up ? "+" : ""}${brl.format(r.delta_mrr)}`;
                delta.className = "kpi-value";
                if (deltaPct) {
                    deltaPct.textContent = up ? "▲" : "▼";
                    deltaPct.className = "kpi-variation " + (up ? "variation-up" : "variation-down");
                }
            }
        }

        if (el("kpiChurn")) el("kpiChurn").textContent = brl.format(r.churn_valor || 0);
        if (el("kpiChurnSub")) el("kpiChurnSub").textContent = `${num.format(r.churn_qtd || 0)} cliente(s)`;
        if (el("kpiChurnPct")) el("kpiChurnPct").textContent = pct(r.churn_pct || 0);
        if (el("kpiClientes")) el("kpiClientes").textContent = num.format(r.clientes || 0);
        if (el("kpiLtvMedio")) el("kpiLtvMedio").textContent = brl.format(r.ltv_medio || 0);
    }

    function baseOpts(extra) {
        return Object.assign({
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            plugins: { legend: { display: false } },
        }, extra || {});
    }

    function destroy(name) {
        if (charts[name]) { charts[name].destroy(); charts[name] = null; }
    }

    function renderCharts() {
        if (typeof Chart === "undefined") return;
        Chart.defaults.font.family = "Poppins";
        Chart.defaults.color = getComputedStyle(document.body).getPropertyValue("--text-muted") || "#a1a1aa";

        const serie = serieFiltrada();
        const labels = serie.map((s) => s.label);

        // MRR
        destroy("mrr");
        charts.mrr = new Chart(el("mrrChart"), {
            type: "line",
            data: {
                labels,
                datasets: [{
                    label: "MRR",
                    data: serie.map((s) => s.mrr),
                    borderColor: "#378ADD",
                    backgroundColor: "rgba(55,138,221,0.08)",
                    fill: true,
                    tension: 0.3,
                    pointRadius: 2,
                }],
            },
            options: baseOpts({
                scales: {
                    y: { ticks: { callback: (v) => brlCompact.format(v) } },
                    x: { ticks: { autoSkip: true, maxRotation: 0 } },
                },
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: { label: (c) => " MRR: " + brl.format(c.parsed.y) } },
                },
            }),
        });

        // Churn R$ (bar) + % (line)
        destroy("churn");
        charts.churn = new Chart(el("churnChart"), {
            data: {
                labels,
                datasets: [
                    {
                        type: "bar",
                        label: "Churn (R$)",
                        data: serie.map((s) => s.churn),
                        backgroundColor: "rgba(226,75,74,0.55)",
                        yAxisID: "y",
                        borderRadius: 4,
                    },
                    {
                        type: "line",
                        label: "Churn %",
                        data: serie.map((s) => (s.churn_pct || 0) * 100),
                        borderColor: "#EF9F27",
                        backgroundColor: "#EF9F27",
                        yAxisID: "y1",
                        tension: 0.3,
                        pointRadius: 2,
                    },
                ],
            },
            options: baseOpts({
                scales: {
                    y: { position: "left", ticks: { callback: (v) => brlCompact.format(v) } },
                    y1: { position: "right", grid: { drawOnChartArea: false }, ticks: { callback: (v) => v + "%" } },
                    x: { ticks: { autoSkip: true, maxRotation: 0 } },
                },
                plugins: {
                    legend: { display: true, position: "bottom", labels: { boxWidth: 10, font: { size: 10 } } },
                },
            }),
        });

        // Clientes
        destroy("clientes");
        charts.clientes = new Chart(el("clientesChart"), {
            type: "line",
            data: {
                labels,
                datasets: [{
                    label: "Clientes",
                    data: serie.map((s) => s.clientes),
                    borderColor: "#1D9E75",
                    backgroundColor: "rgba(29,158,117,0.08)",
                    fill: true,
                    tension: 0.3,
                    pointRadius: 2,
                }],
            },
            options: baseOpts({
                scales: {
                    y: { ticks: { precision: 0 } },
                    x: { ticks: { autoSkip: true, maxRotation: 0 } },
                },
                plugins: { legend: { display: false } },
            }),
        });

        // Top LTV
        const top = (DATA.ranking || []).slice(0, 10);
        destroy("ltv");
        charts.ltv = new Chart(el("ltvChart"), {
            type: "bar",
            data: {
                labels: top.map((c) => c.nome || `Projeto ${c.projeto_pipefy_id}`),
                datasets: [{
                    label: "LTV",
                    data: top.map((c) => c.ltv),
                    backgroundColor: "rgba(239,159,39,0.6)",
                    borderRadius: 4,
                }],
            },
            options: baseOpts({
                indexAxis: "y",
                scales: {
                    x: { ticks: { callback: (v) => brlCompact.format(v) } },
                    y: { ticks: { callback: (val) => trunc(val, 16) } },
                },
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: { label: (c) => " LTV: " + brl.format(c.parsed.x) } },
                },
            }),
        });
    }

    function statusClasse(s) {
        if (s === "Ativo") return "ativo";
        if (s === "Inativo") return "inativo";
        return "neutro";
    }

    let filtroAtual = "";
    const pag = { page: 1, size: 10 };

    function linhasFiltradas(filtro) {
        const termo = (filtro || "").toLowerCase();
        return (DATA.ranking_ativos || DATA.ranking || []).filter((c) =>
            !termo || (c.nome || "").toLowerCase().includes(termo)
        );
    }

    function renderPaginacao(total) {
        const box = el("mrrPaginacao");
        if (!box) return;
        const numPag = Math.max(1, Math.ceil(total / pag.size));
        if (pag.page > numPag) pag.page = numPag;
        const ini = total === 0 ? 0 : (pag.page - 1) * pag.size + 1;
        const fim = Math.min(total, pag.page * pag.size);
        let paginas = "";
        for (let p = 1; p <= Math.min(numPag, 30); p++) {
            paginas += `<button class="mrr-pag-btn ${p === pag.page ? "atual" : ""}" onclick="MRR.paginar(${p})">${p}</button>`;
        }
        box.innerHTML = `
            <span class="mrr-pag-info">${num.format(ini)}–${num.format(fim)} de ${num.format(total)}</span>
            <select class="mrr-pag-size" onchange="MRR.mudarTamanho(this.value)">
                ${[10, 15, 25].map((s) => `<option value="${s}" ${s === pag.size ? "selected" : ""}>${s}/pág</option>`).join("")}
            </select>
            <button class="mrr-pag-btn" onclick="MRR.paginar(${pag.page - 1})" ${pag.page <= 1 ? "disabled" : ""}>‹</button>
            ${paginas}
            <button class="mrr-pag-btn" onclick="MRR.paginar(${pag.page + 1})" ${pag.page >= numPag ? "disabled" : ""}>›</button>
        `;
    }

    function renderTabela(filtro) {
        filtroAtual = filtro || "";
        const tbody = el("mrrTabela");
        if (!tbody) return;
        const rows = linhasFiltradas(filtroAtual);
        renderPaginacao(rows.length);
        const start = (pag.page - 1) * pag.size;
        const slice = rows.slice(start, start + pag.size);
        if (!slice.length) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:1.5rem;">Nenhum cliente ativo encontrado.</td></tr>';
            return;
        }
        tbody.innerHTML = slice.map((c) => `
            <tr class="mrr-linha-cliente" title="Ver extrato mensal"
                onclick="MRR.extrato(${c.projeto_pipefy_id}, '${(c.nome || "").replace(/'/g, "\\'")}')">
                <td>${c.nome || ("Projeto " + c.projeto_pipefy_id)}</td>
                <td>${brl.format(c.ltv || 0)}</td>
                <td>${num.format(c.meses_ativo || 0)}</td>
                <td>${brl.format(c.mrr_atual || 0)}</td>
                <td><span class="mrr-status ${statusClasse(c.status_atual)}">${c.status_atual || "—"}</span></td>
                <td>${c.data_inicio || "—"}</td>
            </tr>
        `).join("");
    }

    async function extrato(pid, nome) {
        let linhas = [];
        try {
            linhas = await apiExtrato(pid);
        } catch (e) {
            HubModal.alert(e.message);
            return;
        }
        if (!linhas.length) { HubModal.alert("Sem histórico cadastrado para este cliente."); return; }
        let prev = null;
        const html = `<div class="mrr-extrato">
            ${linhas.map((l) => {
                const fee = l.fee != null ? l.fee : "—";
                const variou = prev !== null && l.fee !== null && parseFloat(l.fee) !== prev;
                const sinal = variou && l.fee > prev ? "▲" : (variou ? "▼" : "");
                if (l.fee !== null && l.fee !== "") prev = parseFloat(l.fee);
                return `<div class="mrr-extrato-linha ${variou ? "variou" : ""}">
                    <span class="mrr-extrato-mes">${String(l.mes).padStart(2, "0")}/${l.ano}</span>
                    <span class="mrr-extrato-fee">${fee} ${l.moeda || ""} ${sinal ? `<em class="mrr-extrato-var">${sinal}</em>` : ""}</span>
                    <span class="mrr-extrato-brl">${l.fee_brl != null ? brl.format(l.fee_brl) : "—"}</span>
                    <span class="mrr-extrato-status ${statusClasse(l.status)}">${l.status || "—"}${l.manual ? " · manual" : ""}</span>
                </div>`;
            }).join("")}
        </div>`;
        HubModal.alert(html, { html: true, title: nome || ("Projeto " + pid), okLabel: "Fechar", wide: true });
    }

    async function apiExtrato(pid) {
        const r = await fetch(`/api/mrr/cliente/extrato?projeto=${pid}`);
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || "Erro ao carregar extrato");
        return d;
    }

    function paginar(p) { pag.page = Number(p); renderTabela(filtroAtual); }
    function mudarTamanho(s) { pag.size = Number(s); pag.page = 1; renderTabela(filtroAtual); }

    document.addEventListener("DOMContentLoaded", () => {
        if (!DATA.serie || !DATA.serie.length) return;
        renderKpis();
        renderCharts();
        renderTabela("");

        const sel = el("mrrPeriodo");
        if (sel) sel.addEventListener("change", renderCharts);

        const busca = el("mrrBusca");
        if (busca) busca.addEventListener("input", (e) => { pag.page = 1; renderTabela(e.target.value); });
    });

    window.MRR = { paginar, mudarTamanho, extrato };
})();
