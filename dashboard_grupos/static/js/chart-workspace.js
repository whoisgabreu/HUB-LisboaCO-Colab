(function () {
  "use strict";

  const SPEC_KEY = "dashboardGrupos.graficos.v1";
  const LAYOUT_KEY = "dashboardGrupos.graficos.layout.v1";
  const GRID_COLUMNS = 20;
  const MIN_SPAN = 5;
  const MAX_SPAN = 20;
  const MIN_HEIGHT = 220;
  const MAX_HEIGHT = 720;
  const MAX_CUSTOM = 12;
  const chartInstances = [];
  let specs = readStorage(SPEC_KEY, []);
  let layouts = readStorage(LAYOUT_KEY, {});

  const dimensions = {
    grupo: { label: "grupo", field: "grupo" },
    remetente: { label: "remetente", field: "remetente" },
    tipo: { label: "tipo de participante", field: "tipo", order: ["Equipe", "Cliente"] },
    papel: { label: "papel", field: "papel" },
    dia: { label: "dia", field: "dia", sortField: "dia_ordem" },
    dia_semana: { label: "dia da semana", field: "dia_semana", order: ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"] },
    hora: { label: "hora", field: "hora", order: Array.from({ length: 24 }, (_, index) => String(index).padStart(2, "0") + "h") }
  };

  const measures = {
    count: { label: "Quantidade de mensagens", mode: "count", decimals: 0 },
    withText: { label: "Mensagens com texto", mode: "sum", field: "com_texto", decimals: 0 },
    totalCharacters: { label: "Total de caracteres", mode: "sum", field: "caracteres", decimals: 0 },
    averageCharacters: { label: "Média de caracteres", mode: "average", field: "caracteres", decimals: 1 }
  };

  function readStorage(key, fallback) {
    try {
      const parsed = JSON.parse(localStorage.getItem(key) || "null");
      return parsed === null ? fallback : parsed;
    } catch (_) {
      return fallback;
    }
  }

  function saveStorage(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (_) {
      announce("O navegador não permitiu salvar essa configuração.");
      return false;
    }
  }

  function clamp(value, minimum, maximum, fallback) {
    const parsed = Number(value);
    return Math.min(maximum, Math.max(minimum, Number.isFinite(parsed) ? parsed : fallback));
  }

  function cleanLayout(raw, fallback) {
    const base = fallback || { span: 10, height: 310 };
    return {
      span: Math.round(clamp(raw && raw.span, MIN_SPAN, MAX_SPAN, base.span)),
      height: Math.round(clamp(raw && raw.height, MIN_HEIGHT, MAX_HEIGHT, base.height) / 10) * 10
    };
  }

  function cardKey(card) {
    return String(card.dataset.chartKey || "");
  }

  function defaultLayout(card) {
    return cleanLayout({
      span: card.dataset.defaultSpan,
      height: card.dataset.defaultHeight
    }, { span: 10, height: 310 });
  }

  function layoutFor(card) {
    return cleanLayout(layouts[cardKey(card)], defaultLayout(card));
  }

  function resizeChart(card) {
    const canvas = card.querySelector("canvas");
    if (!canvas || !window.Chart || typeof Chart.getChart !== "function") return;
    window.requestAnimationFrame(function () {
      const chart = Chart.getChart(canvas);
      if (chart) chart.resize();
    });
  }

  function applyLayout(card, raw, shouldResize) {
    const layout = cleanLayout(raw, defaultLayout(card));
    layouts[cardKey(card)] = layout;
    card.style.setProperty("--dg-chart-span", String(layout.span));
    card.style.setProperty("--dg-chart-height", layout.height + "px");
    card.dataset.layoutSpan = String(layout.span);
    card.dataset.layoutHeight = String(layout.height);
    const feedback = card.querySelector("[data-dg-size-feedback]");
    if (feedback) feedback.textContent = Math.round(layout.span / GRID_COLUMNS * 100) + "% · " + layout.height + "px";
    if (shouldResize !== false) resizeChart(card);
    return layout;
  }

  function gridStep(card) {
    const grid = card.parentElement;
    if (!grid) return 40;
    const styles = getComputedStyle(grid);
    const gap = Number.parseFloat(styles.columnGap) || 0;
    return Math.max(1, (grid.clientWidth - gap * (GRID_COLUMNS - 1)) / GRID_COLUMNS + gap);
  }

  function addResize(card) {
    if (!card || card.dataset.dgResizeReady === "true") return;
    card.dataset.dgResizeReady = "true";
    const surface = card.matches(".dg-custom-chart-card") ? card : card.querySelector(".card");
    if (!surface) return;

    const feedback = document.createElement("span");
    feedback.className = "dg-chart-size-feedback";
    feedback.dataset.dgSizeFeedback = "";
    feedback.setAttribute("aria-hidden", "true");

    const handle = document.createElement("button");
    handle.type = "button";
    handle.className = "dg-chart-resize-handle";
    handle.title = "Arraste para ajustar largura e altura";
    handle.setAttribute("aria-label", "Redimensionar gráfico. Use as setas para ajustes precisos e Home para restaurar.");
    handle.innerHTML = '<span class="dg-chart-resize-grip" aria-hidden="true"></span>';
    surface.append(feedback, handle);

    let drag = null;

    function finish(event) {
      if (!drag || (event.pointerId !== undefined && event.pointerId !== drag.pointerId)) return;
      const pointerId = drag.pointerId;
      drag = null;
      card.classList.remove("is-resizing");
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
      if (handle.hasPointerCapture && handle.hasPointerCapture(pointerId)) handle.releasePointerCapture(pointerId);
      saveStorage(LAYOUT_KEY, layouts);
    }

    handle.addEventListener("pointerdown", function (event) {
      if (event.button !== undefined && event.button !== 0) return;
      event.preventDefault();
      const layout = layoutFor(card);
      drag = {
        pointerId: event.pointerId,
        x: event.clientX,
        y: event.clientY,
        span: layout.span,
        height: layout.height,
        step: gridStep(card)
      };
      card.classList.add("is-resizing");
      document.body.style.userSelect = "none";
      document.body.style.cursor = "nwse-resize";
      if (handle.setPointerCapture) handle.setPointerCapture(event.pointerId);
    });

    handle.addEventListener("pointermove", function (event) {
      if (!drag || event.pointerId !== drag.pointerId) return;
      applyLayout(card, {
        span: drag.span + Math.round((event.clientX - drag.x) / drag.step),
        height: drag.height + event.clientY - drag.y
      });
    });
    handle.addEventListener("pointerup", finish);
    handle.addEventListener("pointercancel", finish);
    handle.addEventListener("lostpointercapture", finish);
    handle.addEventListener("keydown", function (event) {
      let layout = layoutFor(card);
      if (event.key === "ArrowLeft") layout.span -= event.shiftKey ? 2 : 1;
      else if (event.key === "ArrowRight") layout.span += event.shiftKey ? 2 : 1;
      else if (event.key === "ArrowUp") layout.height -= event.shiftKey ? 40 : 20;
      else if (event.key === "ArrowDown") layout.height += event.shiftKey ? 40 : 20;
      else if (event.key === "Home") layout = defaultLayout(card);
      else return;
      event.preventDefault();
      applyLayout(card, layout);
      saveStorage(LAYOUT_KEY, layouts);
    });

    applyLayout(card, layoutFor(card), false);
    if (typeof ResizeObserver === "function") {
      const observer = new ResizeObserver(function () { resizeChart(card); });
      observer.observe(card);
    }
    resizeChart(card);
  }

  function chartRows() {
    const node = document.getElementById("dgChartData");
    if (!node) return [];
    try {
      const rows = JSON.parse(node.textContent || "[]");
      return Array.isArray(rows) ? rows : [];
    } catch (_) {
      return [];
    }
  }

  function cleanSpec(raw) {
    if (!raw || !dimensions[raw.dimension] || !measures[raw.measure]) return null;
    const types = ["bar", "horizontalBar", "line", "area", "doughnut", "pie", "polarArea", "radar"];
    if (!types.includes(raw.type)) return null;
    const title = String(raw.title || "").trim().slice(0, 80);
    if (!title) return null;
    return {
      id: String(raw.id || ("chart-" + Date.now() + "-" + Math.random().toString(16).slice(2))).replace(/[^a-zA-Z0-9_-]/g, ""),
      title: title,
      type: raw.type,
      dimension: raw.dimension,
      measure: raw.measure,
      color: /^#[0-9a-f]{6}$/i.test(raw.color) ? raw.color : "#d61616",
      sort: ["natural", "valueDesc", "valueAsc", "labelAsc"].includes(raw.sort) ? raw.sort : "valueDesc",
      topN: Math.round(clamp(raw.topN, 0, 40, 10))
    };
  }

  function aggregate(rows, spec) {
    const dimension = dimensions[spec.dimension];
    const measure = measures[spec.measure];
    const groups = new Map();
    rows.forEach(function (row) {
      const label = String(row[dimension.field] || "Não informado");
      const current = groups.get(label) || { label: label, total: 0, count: 0, sort: row[dimension.sortField] || label };
      current.total += measure.mode === "count" ? 1 : Number(row[measure.field] || 0);
      current.count += 1;
      groups.set(label, current);
    });
    let values = Array.from(groups.values()).map(function (item) {
      const raw = measure.mode === "average" && item.count ? item.total / item.count : item.total;
      const factor = Math.pow(10, measure.decimals || 0);
      return { label: item.label, value: Math.round(raw * factor) / factor, sort: item.sort };
    });
    if (spec.sort === "valueDesc") values.sort((a, b) => b.value - a.value || a.label.localeCompare(b.label, "pt-BR"));
    else if (spec.sort === "valueAsc") values.sort((a, b) => a.value - b.value || a.label.localeCompare(b.label, "pt-BR"));
    else if (spec.sort === "labelAsc") values.sort((a, b) => a.label.localeCompare(b.label, "pt-BR"));
    else if (dimension.order) values.sort((a, b) => dimension.order.indexOf(a.label) - dimension.order.indexOf(b.label));
    else if (dimension.sortField) values.sort((a, b) => String(a.sort).localeCompare(String(b.sort)));
    return spec.topN ? values.slice(0, spec.topN) : values;
  }

  function rgba(hex, alpha) {
    const value = parseInt(hex.slice(1), 16);
    return "rgba(" + ((value >> 16) & 255) + "," + ((value >> 8) & 255) + "," + (value & 255) + "," + alpha + ")";
  }

  function seriesColors(amount) {
    const palette = ["#d61616", "#2563eb", "#159766", "#d68a00", "#7c3aed", "#0891b2", "#db2777", "#64748b"];
    return Array.from({ length: amount }, (_, index) => palette[index % palette.length]);
  }

  function chartOptions(spec) {
    const circular = ["doughnut", "pie", "polarArea"].includes(spec.type);
    const radial = spec.type === "radar";
    const color = getComputedStyle(document.documentElement).getPropertyValue("--dg-muted").trim() || "#667894";
    const grid = getComputedStyle(document.documentElement).getPropertyValue("--dg-border").trim() || "#dbe4ee";
    const options = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: circular || radial, position: "bottom", labels: { color: color, usePointStyle: true, boxWidth: 8 } },
        tooltip: { backgroundColor: "#10213a", padding: 10, cornerRadius: 8 }
      }
    };
    if (!circular && !radial) {
      options.scales = {
        x: { grid: { display: spec.type === "horizontalBar" }, ticks: { color: color } },
        y: { beginAtZero: true, grid: { color: grid }, ticks: { color: color } }
      };
    }
    if (spec.type === "horizontalBar") options.indexAxis = "y";
    if (radial) options.scales = { r: { beginAtZero: true, grid: { color: grid }, angleLines: { color: grid }, ticks: { color: color, backdropColor: "transparent" }, pointLabels: { color: color } } };
    if (spec.type === "doughnut") options.cutout = "62%";
    return options;
  }

  function createCustomCard(spec, rows) {
    const values = aggregate(rows, spec);
    const card = document.createElement("article");
    card.className = "dg-custom-chart-card dg-chart-item";
    card.dataset.dgChartCard = "";
    card.dataset.chartKey = "custom:" + spec.id;
    card.dataset.defaultSpan = "10";
    card.dataset.defaultHeight = "310";
    card.innerHTML =
      '<header class="dg-custom-chart-head"><div><h3></h3><p></p></div></header>' +
      '<button class="dg-custom-remove" type="button" title="Remover gráfico" aria-label="Remover gráfico"><i class="fa-solid fa-trash-can" aria-hidden="true"></i></button>';
    card.querySelector("h3").textContent = spec.title;
    card.querySelector("p").textContent = measures[spec.measure].label + " por " + dimensions[spec.dimension].label + ".";
    card.querySelector(".dg-custom-remove").addEventListener("click", function () { removeCustom(spec.id); });

    if (!values.length) {
      const empty = document.createElement("div");
      empty.className = "dg-custom-empty";
      empty.textContent = "Nenhum dado disponível no filtro atual.";
      card.appendChild(empty);
      return card;
    }

    const box = document.createElement("div");
    box.className = "chart-box";
    const canvas = document.createElement("canvas");
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-label", spec.title);
    box.appendChild(canvas);
    card.appendChild(box);

    const details = document.createElement("details");
    details.className = "dg-chart-data";
    details.innerHTML = "<summary>Ver dados</summary><ul></ul>";
    values.forEach(function (item) {
      const li = document.createElement("li");
      const label = document.createElement("span");
      const value = document.createElement("strong");
      label.textContent = item.label;
      value.textContent = String(item.value);
      li.append(label, value);
      details.querySelector("ul").appendChild(li);
    });
    card.appendChild(details);

    window.requestAnimationFrame(function () {
      const circular = ["doughnut", "pie", "polarArea"].includes(spec.type);
      const line = ["line", "area"].includes(spec.type);
      const type = spec.type === "horizontalBar" ? "bar" : spec.type === "area" ? "line" : spec.type;
      const chart = new Chart(canvas, {
        type: type,
        data: {
          labels: values.map(item => item.label),
          datasets: [{
            label: measures[spec.measure].label,
            data: values.map(item => item.value),
            backgroundColor: circular ? seriesColors(values.length) : rgba(spec.color, line || spec.type === "radar" ? 0.14 : 0.78),
            borderColor: circular ? "#ffffff" : spec.color,
            borderWidth: circular ? 2 : 1.5,
            borderRadius: type === "bar" ? 6 : 0,
            maxBarThickness: type === "bar" ? 42 : undefined,
            tension: line ? 0.32 : undefined,
            fill: spec.type === "area" || spec.type === "radar",
            pointBackgroundColor: spec.color
          }]
        },
        options: chartOptions(spec)
      });
      chartInstances.push(chart);
      resizeChart(card);
    });
    return card;
  }

  function renderCustom() {
    chartInstances.splice(0).forEach(function (chart) { chart.destroy(); });
    const section = document.getElementById("dgCustomSection");
    const container = document.getElementById("dgCustomCharts");
    const count = document.getElementById("dgCustomCount");
    if (!section || !container || !count) return;
    specs = Array.isArray(specs) ? specs.map(cleanSpec).filter(Boolean).slice(0, MAX_CUSTOM) : [];
    container.replaceChildren();
    section.hidden = specs.length === 0;
    count.textContent = String(specs.length);
    const rows = chartRows();
    specs.forEach(function (spec) {
      const card = createCustomCard(spec, rows);
      container.appendChild(card);
      addResize(card);
    });
  }

  function removeCustom(id) {
    specs = specs.filter(spec => spec.id !== id);
    delete layouts["custom:" + id];
    saveStorage(SPEC_KEY, specs);
    saveStorage(LAYOUT_KEY, layouts);
    renderCustom();
    announce("Gráfico removido.");
  }

  function announce(message) {
    const node = document.getElementById("dgChartAnnouncer");
    if (node) node.textContent = message;
  }

  function initBuilder() {
    const form = document.getElementById("dgChartBuilderForm");
    if (!form) return;
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      if (specs.length >= MAX_CUSTOM) {
        announce("Limite de " + MAX_CUSTOM + " gráficos atingido.");
        return;
      }
      const values = new FormData(form);
      const spec = cleanSpec({
        title: values.get("title"),
        type: values.get("type"),
        dimension: values.get("dimension"),
        measure: values.get("measure"),
        color: values.get("color"),
        sort: values.get("sort"),
        topN: values.get("topN")
      });
      if (!spec) {
        announce("Preencha os campos para criar o gráfico.");
        return;
      }
      specs.push(spec);
      saveStorage(SPEC_KEY, specs);
      renderCustom();
      form.elements.title.value = "";
      announce("Gráfico " + spec.title + " criado.");
      document.getElementById("dgCustomSection")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  function init() {
    document.querySelectorAll("[data-dg-chart-card]").forEach(addResize);
    initBuilder();
    renderCustom();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
