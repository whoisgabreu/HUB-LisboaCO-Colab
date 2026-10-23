(function () {
  "use strict";

  var STORAGE_KEY = "painelTech.metricas.graficos.v1";
  var LAYOUT_STORAGE_KEY = "painelTech.metricas.layout.v1";
  var MAX_CUSTOM_CHARTS = 8;
  var DEFAULT_COLOR = "#d61616";
  var GRID_COLUMNS = 20;
  var MIN_CHART_SPAN = 4;
  var MAX_CHART_SPAN = 20;
  var MIN_CHART_HEIGHT = 220;
  var MAX_CHART_HEIGHT = 720;
  var HEIGHT_STEP = 10;
  var fixedCharts = [];
  var customCharts = [];
  var metricsData = null;
  var customSpecs = [];
  var chartLayouts = {};
  var chartResizeObserver = null;

  var DIMENSIONS = {
    status: { label: "Status", field: "status", order: ["Na fila", "Ativo", "Pausado", "Finalizado"] },
    owner: { label: "Responsável", field: "owner" },
    priority: { label: "Prioridade", field: "priority", order: ["Crítica", "Alta", "Média", "Baixa"] },
    health: { label: "Saúde", field: "health", order: ["Normal", "Atenção", "Intervenção necessária"] },
    intervention: { label: "Intervenção", field: "intervention", order: ["Normal", "Atenção", "Intervenção necessária"] },
    impact: { label: "Impacto", field: "impact", order: ["Baixo", "Médio", "Alto", "Crítico"] },
    urgency: { label: "Urgência", field: "urgency", order: ["Baixa", "Média", "Alta", "Crítica"] },
    risk: { label: "Risco", field: "risk", order: ["Baixo", "Médio", "Alto", "Crítico"] },
    effort: { label: "Esforço", field: "effort", order: ["Pequeno", "Médio", "Grande", "Muito grande"] },
    rhythm: { label: "Ritmo", field: "rhythm", order: ["Muito lento", "Lento", "Fluindo", "Rápido", "Muito rápido"] },
    deadlineState: { label: "Estado do prazo", field: "deadlineState", order: ["Atrasado", "Vence em até 7 dias", "No prazo", "Finalizado", "Sem prazo"] },
    progressBand: { label: "Faixa de progresso", field: "progressBand", order: ["0%", "1–25%", "26–50%", "51–75%", "76–99%", "100%"] },
    assignment: { label: "Atribuição", field: "assignment", order: ["Com responsável", "Sem responsável"] },
    overdueState: { label: "Vencimento", field: "overdueState", order: ["Com etapas vencidas", "Sem etapas vencidas"] },
    blockageState: { label: "Bloqueios", field: "blockageState", order: ["Com bloqueio", "Sem bloqueio"] },
    createdMonth: { label: "Mês de criação", field: "createdMonth", sortField: "createdMonthKey", emptyLabel: "Sem data" },
  };

  var MEASURES = {
    count: { label: "Quantidade de projetos", mode: "count", decimals: 0, unit: "projetos" },
    averageProgress: { label: "Progresso médio", mode: "average", field: "progress", decimals: 1, suffix: "%", unit: "percentual" },
    averagePriority: { label: "Índice médio de prioridade", mode: "average", field: "priorityIndex", decimals: 1, unit: "pontos" },
    totalSteps: { label: "Total de etapas", mode: "sum", field: "stepsTotal", decimals: 0, unit: "etapas" },
    completedSteps: { label: "Etapas concluídas", mode: "sum", field: "stepsCompleted", decimals: 0, unit: "etapas" },
    pendingSteps: { label: "Etapas pendentes", mode: "sum", field: "stepsPending", decimals: 0, unit: "etapas" },
    overdueSteps: { label: "Etapas vencidas", mode: "sum", field: "stepsOverdue", decimals: 0, unit: "etapas" },
    blockedSteps: { label: "Etapas bloqueadas", mode: "sum", field: "stepsBlocked", decimals: 0, unit: "etapas" },
    completionRate: { label: "Taxa de conclusão das etapas", mode: "ratio", numerator: "stepsCompleted", denominator: "stepsTotal", decimals: 1, suffix: "%", unit: "percentual" },
  };

  var CHART_TYPES = ["bar", "horizontalBar", "line", "area", "doughnut", "pie", "polarArea", "radar"];
  var SORT_MODES = ["domain", "valueDesc", "valueAsc", "labelAsc", "labelDesc"];
  var LEGACY_WIDTH_SPANS = {
    small: 7,
    medium: 10,
    large: 20,
  };
  var LEGACY_HEIGHT_PIXELS = {
    small: 240,
    medium: 320,
    large: 420,
  };

  function css(name, fallback) {
    var value = getComputedStyle(document.body).getPropertyValue(name).trim();
    return value || fallback;
  }

  function color(name, fallback) {
    return css(name, fallback);
  }

  function hexToRgba(hex, alpha) {
    var clean = String(hex || "").replace("#", "");
    if (/^[0-9a-f]{3}$/i.test(clean)) {
      clean = clean.split("").map(function (part) { return part + part; }).join("");
    }
    if (!/^[0-9a-f]{6}$/i.test(clean)) return hex;
    var number = parseInt(clean, 16);
    return "rgba(" + ((number >> 16) & 255) + ", " + ((number >> 8) & 255) + ", " + (number & 255) + ", " + alpha + ")";
  }

  function validColor(value) {
    return /^#[0-9a-f]{6}$/i.test(String(value || "")) ? value : DEFAULT_COLOR;
  }

  function seriesColors(base, amount) {
    var clean = validColor(base).slice(1);
    var number = parseInt(clean, 16);
    var red = (number >> 16) & 255;
    var green = (number >> 8) & 255;
    var blue = number & 255;
    var max = Math.max(red, green, blue) / 255;
    var min = Math.min(red, green, blue) / 255;
    var delta = max - min;
    var hue = 0;
    if (delta) {
      if (max === red / 255) hue = ((green - blue) / 255 / delta) % 6;
      else if (max === green / 255) hue = (blue - red) / 255 / delta + 2;
      else hue = (red - green) / 255 / delta + 4;
      hue = Math.round(hue * 60);
      if (hue < 0) hue += 360;
    }
    return Array.from({ length: amount }, function (_, index) {
      var offset = amount > 1 ? Math.round((index / amount) * 300) : 0;
      return "hsl(" + ((hue + offset) % 360) + " 68% " + (index % 2 ? 52 : 44) + "% / 0.84)";
    });
  }

  function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function palette() {
    return {
      red: color("--color-error", "#d61616"),
      blue: color("--color-info", "#2563eb"),
      green: color("--color-success", "#159766"),
      amber: color("--color-warning", "#c98300"),
      orange: color("--color-orange", "#e66f16"),
      gray: color("--dot-cinza", "#94a3b8"),
      surface: color("--card-bg", "#ffffff"),
      text: color("--text-muted", "#64748b"),
      strong: color("--text-main", "#1e293b"),
      grid: color("--border-color", "#e2e8f0"),
    };
  }

  function tooltipLines(value, maxLength, maxLines) {
    var text = String(value || "").replace(/\s+/g, " ").trim();
    var lineLength = maxLength || 34;
    var limit = maxLines || 2;
    if (!text) return [];
    var words = text.split(" ");
    var lines = [];
    var current = "";
    for (var index = 0; index < words.length; index += 1) {
      var candidate = current ? current + " " + words[index] : words[index];
      if (candidate.length <= lineLength) {
        current = candidate;
        continue;
      }
      if (lines.length === limit - 1) {
        lines.push(truncate((current ? current + " " : "") + words.slice(index).join(" "), lineLength));
        return lines;
      }
      if (current) lines.push(current);
      current = words[index].length > lineLength ? truncate(words[index], lineLength) : words[index];
    }
    if (current && lines.length < limit) lines.push(current);
    return lines;
  }

  function baseOptions(withScales) {
    var colors = palette();
    var options = {
      responsive: true,
      maintainAspectRatio: false,
      animation: prefersReducedMotion() ? false : { duration: 420 },
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          labels: {
            color: colors.text,
            usePointStyle: true,
            pointStyle: "circle",
            boxWidth: 8,
            boxHeight: 8,
            padding: 15,
            font: { size: 11 },
          },
        },
        tooltip: {
          displayColors: true,
          padding: 11,
          cornerRadius: 8,
          backgroundColor: colors.strong,
          titleColor: colors.surface,
          bodyColor: colors.surface,
          titleFont: { size: 11, weight: "600" },
          bodyFont: { size: 10 },
          callbacks: {
            title: function (contexts) {
              return contexts.length ? tooltipLines(contexts[0].label, 34, 2) : [];
            },
          },
        },
      },
      layout: { padding: 6 },
    };
    if (withScales) {
      options.scales = {
        x: { ticks: { color: colors.text, font: { size: 10 } }, grid: { color: colors.grid } },
        y: { ticks: { color: colors.text, font: { size: 10 } }, grid: { color: colors.grid } },
      };
    }
    return options;
  }

  function readData() {
    var node = document.getElementById("tech-metrics-data");
    if (!node) return null;
    try {
      return JSON.parse(node.textContent);
    } catch (error) {
      return null;
    }
  }

  function destroyCharts(collection) {
    while (collection.length) {
      var chart = collection.pop();
      if (chart && typeof chart.destroy === "function") chart.destroy();
    }
  }

  function pushFixed(canvas, config) {
    if (!canvas) return;
    fixedCharts.push(new Chart(canvas, config));
  }

  function renderDoughnut(canvasId, items, colors) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) return;
    var options = baseOptions(false);
    options.cutout = "67%";
    options.plugins.legend.position = "bottom";
    options.plugins.tooltip.callbacks.label = function (context) {
      var total = context.dataset.data.reduce(function (sum, value) { return sum + Number(value || 0); }, 0);
      var value = Number(context.raw || 0);
      var percentage = total ? Math.round(value / total * 100) : 0;
      return "Projetos: " + value + " (" + percentage + "%)";
    };
    pushFixed(canvas, {
      type: "doughnut",
      data: {
        labels: items.map(function (item) { return item.label; }),
        datasets: [{
          data: items.map(function (item) { return item.value; }),
          backgroundColor: colors,
          borderColor: palette().surface,
          borderWidth: 4,
          hoverOffset: 6,
        }],
      },
      options: options,
    });
  }

  function renderStatusAndHealth() {
    var colors = palette();
    renderDoughnut("tech-status-chart", metricsData.status, [colors.amber, colors.blue, colors.gray, colors.green]);
    renderDoughnut("tech-health-chart", metricsData.health, [colors.green, colors.amber, colors.red]);

    var canvas = document.getElementById("tech-priority-chart");
    if (!canvas) return;
    var options = baseOptions(true);
    options.indexAxis = "y";
    options.plugins.legend.display = false;
    options.scales.x.beginAtZero = true;
    options.scales.x.ticks.precision = 0;
    options.scales.y.grid.display = false;
    pushFixed(canvas, {
      type: "bar",
      data: {
        labels: metricsData.priority.map(function (item) { return item.label; }),
        datasets: [{
          label: "Projetos",
          data: metricsData.priority.map(function (item) { return item.value; }),
          backgroundColor: [hexToRgba(colors.red, 0.82), hexToRgba(colors.orange, 0.82), hexToRgba(colors.amber, 0.82), hexToRgba(colors.gray, 0.72)],
          borderColor: [colors.red, colors.orange, colors.amber, colors.gray],
          borderWidth: 1,
          borderRadius: 6,
          maxBarThickness: 24,
        }],
      },
      options: options,
    });
  }

  function renderProgress() {
    var canvas = document.getElementById("tech-progress-chart");
    if (!canvas || !metricsData.activeProjects.length) return;
    var options = baseOptions(true);
    options.indexAxis = "y";
    options.plugins.legend.display = false;
    options.scales.x.beginAtZero = true;
    options.scales.x.max = 100;
    options.scales.x.ticks.callback = function (value) { return value + "%"; };
    options.scales.y.grid.display = false;
    options.plugins.tooltip.callbacks.afterLabel = function (context) {
      return "Ritmo: " + metricsData.activeProjects[context.dataIndex].rhythm;
    };
    pushFixed(canvas, {
      type: "bar",
      data: {
        labels: metricsData.activeProjects.map(function (item) { return truncate(item.name, 34); }),
        datasets: [{
          label: "Progresso",
          data: metricsData.activeProjects.map(function (item) { return item.value; }),
          backgroundColor: hexToRgba(color("--accent-red", DEFAULT_COLOR), 0.78),
          borderColor: color("--accent-red", DEFAULT_COLOR),
          borderWidth: 1,
          borderRadius: 6,
          barThickness: 15,
        }],
      },
      options: options,
    });
  }

  function renderWorkload() {
    var canvas = document.getElementById("tech-workload-chart");
    if (!canvas || !metricsData.workload.length) return;
    var colors = palette();
    var options = baseOptions(true);
    options.indexAxis = "y";
    options.scales.x.beginAtZero = true;
    options.scales.x.ticks.precision = 0;
    options.scales.y.grid.display = false;
    options.plugins.legend.position = "bottom";
    pushFixed(canvas, {
      type: "bar",
      data: {
        labels: metricsData.workload.map(function (item) { return truncate(item.name, 30); }),
        datasets: [
          {
            label: "Projetos ativos",
            data: metricsData.workload.map(function (item) { return item.active; }),
            backgroundColor: metricsData.workload.map(function (item) {
              return hexToRgba(item.active > item.limit ? colors.red : colors.blue, 0.8);
            }),
            borderColor: metricsData.workload.map(function (item) { return item.active > item.limit ? colors.red : colors.blue; }),
            borderWidth: 1,
            borderRadius: 6,
            maxBarThickness: 18,
          },
          {
            label: "Limite",
            data: metricsData.workload.map(function (item) { return item.limit; }),
            backgroundColor: hexToRgba(colors.gray, 0.22),
            borderColor: colors.gray,
            borderWidth: 1,
            borderRadius: 6,
            maxBarThickness: 18,
          },
        ],
      },
      options: options,
    });
  }

  function renderTrend() {
    var canvas = document.getElementById("tech-trend-chart");
    if (!canvas) return;
    var colors = palette();
    var options = baseOptions(true);
    options.scales.x.grid.display = false;
    options.scales.y.beginAtZero = true;
    options.scales.y.ticks.precision = 0;
    options.plugins.legend.position = "bottom";
    pushFixed(canvas, {
      type: "line",
      data: {
        labels: metricsData.trend.map(function (item) { return item.label; }),
        datasets: [
          {
            label: "Criados",
            data: metricsData.trend.map(function (item) { return item.created; }),
            borderColor: colors.blue,
            backgroundColor: hexToRgba(colors.blue, 0.12),
            pointBackgroundColor: colors.blue,
            borderWidth: 2,
            pointRadius: 3,
            tension: 0.32,
            fill: true,
          },
          {
            label: "Finalizados",
            data: metricsData.trend.map(function (item) { return item.finished; }),
            borderColor: colors.green,
            backgroundColor: hexToRgba(colors.green, 0.1),
            pointBackgroundColor: colors.green,
            borderWidth: 2,
            pointRadius: 3,
            tension: 0.32,
            fill: true,
          },
        ],
      },
      options: options,
    });
  }

  function impactEffortGroups(rows) {
    var groups = new Map();
    rows.forEach(function (row) {
      var x = Number(row.effortLevel || 0);
      var y = Number(row.impactLevel || 0);
      if (!x || !y) return;
      var key = x + ":" + y;
      var group = groups.get(key) || { x: x, y: y, count: 0, names: [], priorityTotal: 0 };
      group.count += 1;
      group.names.push(row.name);
      group.priorityTotal += Number(row.priorityIndex || 0);
      groups.set(key, group);
    });
    return Array.from(groups.values()).map(function (group) {
      group.r = Math.min(24, 7 + Math.sqrt(group.count) * 5);
      group.averagePriority = group.count ? Math.round(group.priorityTotal / group.count) : 0;
      return group;
    });
  }

  function renderImpactEffort() {
    var canvas = document.getElementById("tech-impact-effort-chart");
    if (!canvas) return;
    var groups = impactEffortGroups(metricsData.rows);
    var colors = palette();
    var options = baseOptions(true);
    var effortLabels = { 1: "Pequeno", 2: "Médio", 3: "Grande", 4: "Muito grande" };
    var impactLabels = { 1: "Baixo", 2: "Médio", 3: "Alto", 4: "Crítico" };
    options.interaction = { mode: "nearest", intersect: true };
    options.plugins.legend.display = false;
    options.plugins.tooltip.displayColors = false;
    options.plugins.tooltip.position = "nearest";
    options.scales.x.min = 1;
    options.scales.x.max = 4;
    options.scales.x.title = { display: true, text: "Esforço", color: colors.text, font: { size: 11, weight: "600" } };
    options.scales.x.ticks = { stepSize: 1, color: colors.text, callback: function (value) { return effortLabels[value] || ""; }, font: { size: 10 } };
    options.scales.y.min = 1;
    options.scales.y.max = 4;
    options.scales.y.title = { display: true, text: "Impacto", color: colors.text, font: { size: 11, weight: "600" } };
    options.scales.y.ticks = { stepSize: 1, color: colors.text, callback: function (value) { return impactLabels[value] || ""; }, font: { size: 10 } };
    options.plugins.tooltip.callbacks.title = function (contexts) {
      if (!contexts.length) return "";
      var raw = contexts[0].raw;
      return impactLabels[raw.y] + " impacto · " + effortLabels[raw.x] + " esforço";
    };
    options.plugins.tooltip.callbacks.label = function (context) {
      var raw = context.raw;
      return raw.count + (raw.count === 1 ? " projeto" : " projetos") + " · prioridade média " + raw.averagePriority;
    };
    options.plugins.tooltip.callbacks.afterLabel = function (context) {
      var names = context.raw.names || [];
      var lines = names.slice(0, 3).map(function (name, index) {
        return (index + 1) + ". " + truncate(name, 30);
      });
      if (names.length > 3) lines.push("+ " + (names.length - 3) + " projeto(s)");
      return lines;
    };
    pushFixed(canvas, {
      type: "bubble",
      data: {
        datasets: [{
          label: "Projetos",
          data: groups,
          backgroundColor: hexToRgba(colors.red, 0.58),
          borderColor: colors.red,
          borderWidth: 1.5,
          hoverBackgroundColor: hexToRgba(colors.red, 0.76),
          clip: 18,
        }],
      },
      options: options,
    });
  }

  function renderFixedCharts() {
    destroyCharts(fixedCharts);
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    Chart.defaults.color = palette().text;
    renderStatusAndHealth();
    renderProgress();
    renderWorkload();
    renderTrend();
    renderImpactEffort();
  }

  function truncate(value, maxLength) {
    var text = String(value || "");
    return text.length > maxLength ? text.slice(0, maxLength - 1) + "…" : text;
  }

  function newId() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return "chart-" + window.crypto.randomUUID();
    }
    return "chart-" + Date.now() + "-" + Math.random().toString(16).slice(2);
  }

  function sanitizeSpec(raw) {
    if (!raw || typeof raw !== "object") return null;
    if (CHART_TYPES.indexOf(raw.type) === -1 || !DIMENSIONS[raw.dimension] || !MEASURES[raw.measure]) return null;
    var title = String(raw.title || "").trim().slice(0, 80);
    if (!title) return null;
    var id = String(raw.id || "").replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 80) || newId();
    var sort = SORT_MODES.indexOf(raw.sort) === -1 ? "domain" : raw.sort;
    var parsedTop = Number.parseInt(raw.topN, 10);
    var topN = Number.isFinite(parsedTop) ? Math.max(0, Math.min(30, parsedTop)) : 0;
    var showZeros = raw.showZeros !== false && raw.showZeros !== "false";
    var width = Object.prototype.hasOwnProperty.call(LEGACY_WIDTH_SPANS, raw.width) ? raw.width : "large";
    var height = Object.prototype.hasOwnProperty.call(LEGACY_HEIGHT_PIXELS, raw.height) ? raw.height : "medium";
    return {
      id: id,
      title: title,
      type: raw.type,
      dimension: raw.dimension,
      measure: raw.measure,
      color: validColor(raw.color),
      sort: sort,
      topN: topN,
      showZeros: showZeros,
      width: width,
      height: height,
    };
  }

  function loadSpecs() {
    try {
      var stored = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "[]");
      if (!Array.isArray(stored)) return [];
      return stored.map(sanitizeSpec).filter(Boolean).slice(0, MAX_CUSTOM_CHARTS);
    } catch (error) {
      return [];
    }
  }

  function saveSpecs() {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(customSpecs));
      return true;
    } catch (error) {
      announce("O navegador não permitiu salvar os gráficos personalizados.");
      return false;
    }
  }

  function aggregateRows(rows, spec) {
    var dimension = DIMENSIONS[spec.dimension];
    var measure = MEASURES[spec.measure];
    var groups = new Map();
    rows.forEach(function (row) {
      var rawLabel = row[dimension.field];
      var label = String(rawLabel === null || rawLabel === undefined || rawLabel === "" ? (dimension.emptyLabel || "Não informado") : rawLabel);
      var current = groups.get(label) || {
        label: label,
        sum: 0,
        count: 0,
        numerator: 0,
        denominator: 0,
        sortValue: dimension.sortField ? String(row[dimension.sortField] || "9999-99") : label,
      };
      if (measure.mode === "ratio") {
        var numerator = Number(row[measure.numerator]);
        var denominator = Number(row[measure.denominator]);
        if (!Number.isFinite(numerator) || !Number.isFinite(denominator)) return;
        current.numerator += numerator;
        current.denominator += denominator;
      } else {
        var numeric = measure.mode === "count" ? 1 : Number(row[measure.field]);
        if (!Number.isFinite(numeric)) return;
        current.sum += numeric;
      }
      current.count += 1;
      groups.set(label, current);
    });

    if (spec.showZeros && dimension.order) {
      dimension.order.forEach(function (label) {
        if (!groups.has(label)) {
          groups.set(label, { label: label, sum: 0, count: 0, numerator: 0, denominator: 0, sortValue: label });
        }
      });
    }

    var result = Array.from(groups.values()).map(function (group) {
      var value = group.sum;
      if (measure.mode === "average") value = group.count ? group.sum / group.count : 0;
      if (measure.mode === "ratio") value = group.denominator ? group.numerator / group.denominator * 100 : 0;
      var factor = Math.pow(10, measure.decimals || 0);
      return { label: group.label, value: Math.round(value * factor) / factor, sortValue: group.sortValue };
    });

    if (!spec.showZeros) {
      result = result.filter(function (item) { return item.value !== 0; });
    }

    if (spec.sort === "valueDesc") {
      result.sort(function (left, right) { return right.value - left.value || left.label.localeCompare(right.label, "pt-BR"); });
    } else if (spec.sort === "valueAsc") {
      result.sort(function (left, right) { return left.value - right.value || left.label.localeCompare(right.label, "pt-BR"); });
    } else if (spec.sort === "labelAsc") {
      result.sort(function (left, right) { return left.label.localeCompare(right.label, "pt-BR"); });
    } else if (spec.sort === "labelDesc") {
      result.sort(function (left, right) { return right.label.localeCompare(left.label, "pt-BR"); });
    } else if (dimension.order) {
      result.sort(function (left, right) {
        var leftIndex = dimension.order.indexOf(left.label);
        var rightIndex = dimension.order.indexOf(right.label);
        if (leftIndex === -1) leftIndex = dimension.order.length;
        if (rightIndex === -1) rightIndex = dimension.order.length;
        return leftIndex - rightIndex;
      });
    } else if (dimension.sortField) {
      result.sort(function (left, right) { return left.sortValue.localeCompare(right.sortValue, "pt-BR"); });
    } else {
      result.sort(function (left, right) { return right.value - left.value || left.label.localeCompare(right.label, "pt-BR"); });
    }

    return spec.topN ? result.slice(0, spec.topN) : result;
  }

  function customOptions(spec, measure) {
    var circular = spec.type === "doughnut" || spec.type === "pie" || spec.type === "polarArea";
    var radial = spec.type === "radar";
    var options = baseOptions(!circular && !radial);
    options.plugins.legend.position = circular || radial ? "bottom" : "top";
    if (!circular && !radial) {
      options.scales.y.beginAtZero = true;
      options.scales.y.ticks.precision = measure.decimals || 0;
      options.scales.x.grid.display = false;
    }
    if (spec.type === "horizontalBar") {
      options.indexAxis = "y";
      options.scales.x.beginAtZero = true;
      options.scales.x.ticks.precision = measure.decimals || 0;
      options.scales.y.grid.display = false;
    }
    if (radial) {
      var colors = palette();
      options.scales = {
        r: {
          beginAtZero: true,
          ticks: { color: colors.text, precision: measure.decimals || 0, backdropColor: "transparent", font: { size: 9 } },
          angleLines: { color: colors.grid },
          grid: { color: colors.grid },
          pointLabels: { color: colors.text, font: { size: 10 } },
        },
      };
    }
    if (spec.type === "doughnut") options.cutout = "64%";
    options.plugins.tooltip.callbacks.label = function (context) {
      var value = circular
        ? context.raw
        : radial
          ? context.parsed.r
          : context.parsed[spec.type === "horizontalBar" ? "x" : "y"];
      return measure.label + ": " + value + (measure.suffix || "");
    };
    return options;
  }

  function clampNumber(value, minimum, maximum, fallback) {
    var number = Number(value);
    if (!Number.isFinite(number)) number = fallback;
    return Math.min(maximum, Math.max(minimum, number));
  }

  function sanitizeLayout(raw, fallback) {
    var base = fallback || { span: 10, height: 320 };
    var source = raw && typeof raw === "object" ? raw : {};
    var span = Math.round(clampNumber(source.span, MIN_CHART_SPAN, MAX_CHART_SPAN, base.span));
    var height = clampNumber(source.height, MIN_CHART_HEIGHT, MAX_CHART_HEIGHT, base.height);
    height = Math.round(height / HEIGHT_STEP) * HEIGHT_STEP;
    return { span: span, height: height };
  }

  function loadLayouts() {
    try {
      var stored = JSON.parse(window.localStorage.getItem(LAYOUT_STORAGE_KEY) || "{}");
      if (!stored || Array.isArray(stored) || typeof stored !== "object") return {};
      var layouts = {};
      Object.keys(stored).slice(0, 100).forEach(function (key) {
        if (!/^(fixed|custom):[a-zA-Z0-9_-]+$/.test(key)) return;
        layouts[key] = sanitizeLayout(stored[key], { span: 10, height: 320 });
      });
      return layouts;
    } catch (error) {
      return {};
    }
  }

  function saveLayouts() {
    try {
      window.localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(chartLayouts));
      return true;
    } catch (error) {
      announce("O navegador não permitiu salvar o tamanho dos gráficos.");
      return false;
    }
  }

  function chartKeyForCard(card) {
    return card ? String(card.dataset.chartKey || "") : "";
  }

  function defaultLayoutForCard(card) {
    return sanitizeLayout({
      span: card && card.dataset.defaultSpan,
      height: card && card.dataset.defaultHeight,
    }, { span: 10, height: 320 });
  }

  function layoutForCard(card) {
    var key = chartKeyForCard(card);
    var fallback = defaultLayoutForCard(card);
    var layout = sanitizeLayout(key && chartLayouts[key], fallback);
    if (key) chartLayouts[key] = layout;
    return layout;
  }

  function chartLabelForCard(card) {
    var heading = card && card.querySelector("h2, h3");
    return heading ? heading.textContent.trim() : "gráfico";
  }

  function updateResizeFeedback(card, layout) {
    var feedback = card.querySelector("[data-chart-size-feedback]");
    var handle = card.querySelector("[data-chart-resize-handle]");
    var widthPercent = Math.round((layout.span / GRID_COLUMNS) * 100);
    var value = widthPercent + "% · " + layout.height + " px";
    card.dataset.layoutSpan = String(layout.span);
    card.dataset.layoutHeight = String(layout.height);
    if (feedback) feedback.textContent = value;
    if (handle) {
      handle.setAttribute("aria-label", "Redimensionar " + chartLabelForCard(card) + ". Tamanho atual: " + widthPercent + "% de largura e " + layout.height + " pixels de altura. Use esquerda e direita para a largura; cima e baixo para a altura; Home restaura o tamanho inicial.");
    }
  }

  function resizeChartForCard(card) {
    if (!card || card._techResizeFrame) return;
    var schedule = window.requestAnimationFrame || function (callback) { return window.setTimeout(callback, 0); };
    card._techResizeFrame = schedule(function () {
      card._techResizeFrame = null;
      var canvas = card.querySelector("canvas");
      if (!canvas) return;
      var chart = customCharts.find(function (item) { return item.canvas === canvas; });
      if (!chart && window.Chart && typeof Chart.getChart === "function") chart = Chart.getChart(canvas);
      if (!chart) return;
      if (chart.$techFullLabels) {
        var span = Number.parseInt(card.dataset.layoutSpan, 10) || 10;
        var labelLimit = span <= 5 ? 14 : span <= 7 ? 18 : span <= 10 ? 26 : 34;
        chart.data.labels = chart.$techFullLabels.map(function (label) { return truncate(label, labelLimit); });
      }
      chart.resize();
      if (chart.$techFullLabels) chart.update("none");
    });
  }

  function applyChartLayout(card, rawLayout, resizeChart) {
    var layout = sanitizeLayout(rawLayout, defaultLayoutForCard(card));
    var key = chartKeyForCard(card);
    if (key) chartLayouts[key] = layout;
    card.style.setProperty("--tech-chart-span", String(layout.span));
    card.style.setProperty("--tech-chart-height", layout.height + "px");
    updateResizeFeedback(card, layout);
    if (resizeChart !== false) resizeChartForCard(card);
    return layout;
  }

  function gridColumnStep(card) {
    var grid = card && card.parentElement;
    if (!grid) return 40;
    var styles = window.getComputedStyle(grid);
    var gap = Number.parseFloat(styles.columnGap) || 0;
    var cell = (grid.clientWidth - gap * (GRID_COLUMNS - 1)) / GRID_COLUMNS;
    return Math.max(1, cell + gap);
  }

  function bindResizeHandle(card, handle) {
    if (handle.dataset.resizeReady === "true") return;
    handle.dataset.resizeReady = "true";
    var drag = null;

    function stopDragging(event) {
      if (!drag || (event && event.pointerId !== undefined && event.pointerId !== drag.pointerId)) return;
      var finished = drag;
      drag = null;
      card.classList.remove("is-resizing");
      document.body.style.userSelect = finished.bodyUserSelect;
      document.body.style.cursor = finished.bodyCursor;
      if (handle.hasPointerCapture && handle.hasPointerCapture(finished.pointerId)) {
        handle.releasePointerCapture(finished.pointerId);
      }
      saveLayouts();
      var layout = layoutForCard(card);
      announce("Tamanho de " + chartLabelForCard(card) + " ajustado para " + Math.round((layout.span / GRID_COLUMNS) * 100) + "% de largura e " + layout.height + " pixels de altura.");
    }

    handle.addEventListener("pointerdown", function (event) {
      if (event.button !== undefined && event.button !== 0) return;
      event.preventDefault();
      var layout = layoutForCard(card);
      drag = {
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        startSpan: layout.span,
        startHeight: layout.height,
        columnStep: gridColumnStep(card),
        bodyUserSelect: document.body.style.userSelect,
        bodyCursor: document.body.style.cursor,
      };
      card.classList.add("is-resizing");
      document.body.style.userSelect = "none";
      document.body.style.cursor = "nwse-resize";
      if (handle.setPointerCapture) handle.setPointerCapture(event.pointerId);
    });

    handle.addEventListener("pointermove", function (event) {
      if (!drag || event.pointerId !== drag.pointerId) return;
      event.preventDefault();
      var spanDelta = Math.round((event.clientX - drag.startX) / drag.columnStep);
      var height = drag.startHeight + (event.clientY - drag.startY);
      applyChartLayout(card, {
        span: drag.startSpan + spanDelta,
        height: Math.round(height / HEIGHT_STEP) * HEIGHT_STEP,
      });
    });

    handle.addEventListener("pointerup", stopDragging);
    handle.addEventListener("pointercancel", stopDragging);
    handle.addEventListener("lostpointercapture", stopDragging);
    handle.addEventListener("keydown", function (event) {
      var layout = layoutForCard(card);
      var spanStep = event.shiftKey ? 2 : 1;
      var heightStep = event.shiftKey ? 40 : 20;
      var changed = true;
      if (event.key === "ArrowLeft") layout.span -= spanStep;
      else if (event.key === "ArrowRight") layout.span += spanStep;
      else if (event.key === "ArrowUp") layout.height -= heightStep;
      else if (event.key === "ArrowDown") layout.height += heightStep;
      else if (event.key === "Home") layout = defaultLayoutForCard(card);
      else changed = false;
      if (!changed) return;
      event.preventDefault();
      layout = applyChartLayout(card, layout);
      saveLayouts();
      announce("Tamanho de " + chartLabelForCard(card) + ": " + Math.round((layout.span / GRID_COLUMNS) * 100) + "% por " + layout.height + " pixels.");
    });
  }

  function ensureResizeHandle(card) {
    var feedback = card.querySelector("[data-chart-size-feedback]");
    if (!feedback) {
      feedback = document.createElement("span");
      feedback.className = "tech-chart-size-feedback";
      feedback.dataset.chartSizeFeedback = "";
      feedback.setAttribute("aria-hidden", "true");
      card.appendChild(feedback);
    }

    var handle = card.querySelector("[data-chart-resize-handle]");
    if (!handle) {
      handle = document.createElement("button");
      handle.type = "button";
      handle.className = "tech-chart-resize-handle";
      handle.dataset.chartResizeHandle = "";
      handle.title = "Arraste para redimensionar. Use as setas com o botão focado para ajustes precisos.";
      handle.setAttribute("aria-label", "Redimensionar " + chartLabelForCard(card) + ". Setas esquerda e direita ajustam a largura; cima e baixo ajustam a altura; Home restaura o tamanho inicial.");
      var grip = document.createElement("span");
      grip.className = "tech-chart-resize-grip";
      grip.setAttribute("aria-hidden", "true");
      handle.appendChild(grip);
      card.appendChild(handle);
    }
    bindResizeHandle(card, handle);
  }

  function setupResizableCards() {
    if (chartResizeObserver) chartResizeObserver.disconnect();
    chartResizeObserver = typeof window.ResizeObserver === "function"
      ? new window.ResizeObserver(function (entries) {
        entries.forEach(function (entry) { resizeChartForCard(entry.target); });
      })
      : null;

    document.querySelectorAll("[data-tech-chart-card]").forEach(function (card) {
      ensureResizeHandle(card);
      applyChartLayout(card, layoutForCard(card), false);
      if (chartResizeObserver) chartResizeObserver.observe(card);
      resizeChartForCard(card);
    });
  }

  function createCustomCard(spec, aggregated) {
    var dimension = DIMENSIONS[spec.dimension];
    var measure = MEASURES[spec.measure];
    var card = document.createElement("article");
    card.className = "tech-custom-chart-card";
    card.dataset.customId = spec.id;
    card.dataset.techChartCard = "";
    card.dataset.chartKey = "custom:" + spec.id;
    card.dataset.defaultSpan = String(LEGACY_WIDTH_SPANS[spec.width] || LEGACY_WIDTH_SPANS.large);
    card.dataset.defaultHeight = String(LEGACY_HEIGHT_PIXELS[spec.height] || LEGACY_HEIGHT_PIXELS.medium);

    var header = document.createElement("header");
    header.className = "tech-custom-chart-head";
    var copy = document.createElement("div");
    var heading = document.createElement("h3");
    heading.id = spec.id + "-title";
    heading.textContent = spec.title;
    var description = document.createElement("p");
    description.textContent = measure.label + " por " + dimension.label.toLowerCase() + " · unidade: " + measure.unit + ".";
    copy.appendChild(heading);
    copy.appendChild(description);
    header.appendChild(copy);
    card.appendChild(header);

    var remove = document.createElement("button");
    remove.type = "button";
    remove.className = "tech-custom-remove";
    remove.dataset.removeCustom = spec.id;
    remove.setAttribute("aria-label", "Remover gráfico " + spec.title);
    remove.title = "Remover gráfico";
    var icon = document.createElement("i");
    icon.className = "fa-solid fa-trash-can";
    icon.setAttribute("aria-hidden", "true");
    remove.appendChild(icon);
    card.appendChild(remove);

    if (!aggregated.length) {
      var empty = document.createElement("div");
      empty.className = "tech-chart-empty";
      empty.textContent = "Nenhum dado disponível no recorte atual.";
      card.appendChild(empty);
      return card;
    }

    var canvasWrap = document.createElement("div");
    canvasWrap.className = "tech-custom-canvas-wrap";
    var canvas = document.createElement("canvas");
    canvas.id = spec.id + "-canvas";
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-labelledby", heading.id);
    canvas.textContent = spec.title + ".";
    canvasWrap.appendChild(canvas);
    card.appendChild(canvasWrap);

    var details = document.createElement("details");
    details.className = "tech-chart-data";
    var summary = document.createElement("summary");
    summary.textContent = "Ver dados";
    var list = document.createElement("ul");
    aggregated.forEach(function (item) {
      var row = document.createElement("li");
      var label = document.createElement("span");
      label.textContent = item.label;
      var value = document.createElement("strong");
      value.textContent = item.value + (measure.suffix || "");
      row.appendChild(label);
      row.appendChild(value);
      list.appendChild(row);
    });
    details.appendChild(summary);
    details.appendChild(list);
    card.appendChild(details);
    return card;
  }

  function chartCustom(canvas, spec, aggregated) {
    var measure = MEASURES[spec.measure];
    var circular = spec.type === "doughnut" || spec.type === "pie" || spec.type === "polarArea";
    var radial = spec.type === "radar";
    var line = spec.type === "line" || spec.type === "area";
    var type = spec.type === "horizontalBar" ? "bar" : spec.type === "area" ? "line" : spec.type;
    var labelLimit = 34;
    var colors = circular ? seriesColors(spec.color, aggregated.length) : spec.color;
    var dataset = {
      label: measure.label,
      data: aggregated.map(function (item) { return item.value; }),
      backgroundColor: circular ? colors : hexToRgba(spec.color, line || radial ? 0.14 : 0.76),
      borderColor: circular ? palette().surface : spec.color,
      borderWidth: circular ? 3 : line || radial ? 2 : 1.5,
      borderRadius: type === "bar" ? 6 : 0,
      maxBarThickness: type === "bar" ? 38 : undefined,
      pointBackgroundColor: spec.color,
      pointRadius: line || radial ? 3 : undefined,
      tension: line ? 0.32 : undefined,
      fill: spec.type === "area" || radial,
      hoverOffset: circular ? 5 : undefined,
    };
    var fullLabels = aggregated.map(function (item) { return item.label; });
    var chart = new Chart(canvas, {
      type: type,
      data: {
        labels: fullLabels.map(function (label) { return truncate(label, labelLimit); }),
        datasets: [dataset],
      },
      options: customOptions(spec, measure),
    });
    chart.$techFullLabels = fullLabels;
    customCharts.push(chart);
  }

  function renderCustomCharts() {
    destroyCharts(customCharts);
    var section = document.getElementById("tech-custom-section");
    var container = document.getElementById("tech-custom-charts");
    var count = document.getElementById("tech-custom-count");
    if (!section || !container || !count) return;
    container.replaceChildren();
    section.hidden = customSpecs.length === 0;
    count.textContent = customSpecs.length ? String(customSpecs.length) : "";

    customSpecs.forEach(function (spec) {
      var aggregated = aggregateRows(metricsData.rows, spec);
      var card = createCustomCard(spec, aggregated);
      container.appendChild(card);
      var canvas = card.querySelector("canvas");
      if (canvas) chartCustom(canvas, spec, aggregated);
    });
    setupResizableCards();
  }

  function announce(message) {
    var node = document.getElementById("tech-chart-announcer");
    if (!node) return;
    node.textContent = "";
    window.setTimeout(function () { node.textContent = message; }, 20);
  }

  function updateBuilderPreview(form) {
    var preview = document.querySelector("#tech-chart-builder-preview span");
    if (!preview || !form || !form.elements.dimension || !form.elements.measure) return;
    var dimension = DIMENSIONS[form.elements.dimension.value];
    var measure = MEASURES[form.elements.measure.value];
    if (!dimension || !measure) return;
    preview.textContent = "Exemplo: " + measure.label + " para cada " + dimension.label.toLowerCase() + ". Unidade: " + measure.unit + ".";
  }

  function handleBuilderSubmit(event) {
    event.preventDefault();
    if (customSpecs.length >= MAX_CUSTOM_CHARTS) {
      announce("Limite de " + MAX_CUSTOM_CHARTS + " gráficos personalizados atingido.");
      return;
    }
    var form = event.currentTarget;
    var values = new FormData(form);
    var spec = sanitizeSpec({
      id: newId(),
      title: values.get("title"),
      type: values.get("type"),
      dimension: values.get("dimension"),
      measure: values.get("measure"),
      color: values.get("color"),
      sort: values.get("sort"),
      topN: values.get("topN"),
      showZeros: form.elements.showZeros.checked,
      width: "large",
      height: "medium",
    });
    if (!spec) {
      announce("Revise os campos antes de criar o gráfico.");
      return;
    }
    customSpecs.push(spec);
    saveSpecs();
    renderCustomCharts();
    form.elements.title.value = "";
    announce("Gráfico " + spec.title + " criado e salvo neste navegador.");
  }

  function handleCustomClick(event) {
    var button = event.target.closest("[data-remove-custom]");
    if (!button) return;
    var id = button.dataset.removeCustom;
    var removed = customSpecs.find(function (spec) { return spec.id === id; });
    customSpecs = customSpecs.filter(function (spec) { return spec.id !== id; });
    delete chartLayouts["custom:" + id];
    saveSpecs();
    saveLayouts();
    renderCustomCharts();
    announce(removed ? "Gráfico " + removed.title + " removido." : "Gráfico removido.");
    var titleInput = document.querySelector("#tech-chart-builder-form [name='title']");
    if (titleInput) titleInput.focus();
  }

  function renderAll() {
    if (!window.Chart || !metricsData) return;
    renderFixedCharts();
    renderCustomCharts();
  }

  function init() {
    metricsData = readData();
    var runtimeError = document.getElementById("tech-chart-runtime-error");
    if (!window.Chart || !metricsData) {
      if (runtimeError) runtimeError.hidden = false;
      var createButton = document.querySelector(".tech-chart-create-btn");
      if (createButton) createButton.disabled = true;
      return;
    }
    customSpecs = loadSpecs();
    chartLayouts = loadLayouts();
    var form = document.getElementById("tech-chart-builder-form");
    var customContainer = document.getElementById("tech-custom-charts");
    if (form) {
      form.addEventListener("submit", handleBuilderSubmit);
      form.addEventListener("change", function () { updateBuilderPreview(form); });
      updateBuilderPreview(form);
    }
    if (customContainer) customContainer.addEventListener("click", handleCustomClick);
    renderAll();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.addEventListener("tech:themechange", function () {
    window.setTimeout(renderAll, 40);
  });
})();
