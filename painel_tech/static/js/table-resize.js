(function () {
  "use strict";

  const STORAGE_KEY = "painelTech.tabelas.colunas.v1";
  const MIN_WIDTH = 76;
  const MAX_WIDTH = 720;
  const originalLayouts = new WeakMap();
  let savedLayouts = readLayouts();

  function readLayouts() {
    try {
      const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
      return value && typeof value === "object" ? value : {};
    } catch (error) {
      return {};
    }
  }

  function writeLayouts() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(savedLayouts));
    } catch (error) {
      /* A tabela continua redimensionavel mesmo sem armazenamento local. */
    }
  }

  function headersFor(table) {
    const row = table.tHead && table.tHead.rows && table.tHead.rows[0];
    return row ? Array.from(row.cells) : [];
  }

  function normalizedText(value) {
    return String(value || "")
      .trim()
      .toLocaleLowerCase("pt-BR")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/\s+/g, "-")
      .replace(/[^a-z0-9-]/g, "");
  }

  function layoutKey(table, headers) {
    if (table.dataset.techTableKey) return table.dataset.techTableKey;
    const signature = headers.map(function (header) {
      return normalizedText(header.childNodes[0] ? header.childNodes[0].textContent : header.textContent);
    }).join("|");
    return window.location.pathname + "::" + signature;
  }

  function directColgroup(table) {
    return Array.from(table.children).find(function (child) {
      return child.tagName === "COLGROUP";
    }) || null;
  }

  function ensureColumns(table, count) {
    let group = directColgroup(table);
    if (!group) {
      group = document.createElement("colgroup");
      table.insertBefore(group, table.firstChild);
    }
    while (group.children.length < count) group.appendChild(document.createElement("col"));
    while (group.children.length > count) group.lastElementChild.remove();
    return Array.from(group.children);
  }

  function rememberOriginal(table, count) {
    if (originalLayouts.has(table)) return;
    const group = directColgroup(table);
    originalLayouts.set(table, {
      tableWidth: table.style.width,
      minWidth: table.style.minWidth,
      tableLayout: table.style.tableLayout,
      hadColgroup: Boolean(group),
      columnStyles: group
        ? Array.from(group.children).slice(0, count).map(function (col) { return col.getAttribute("style") || ""; })
        : [],
    });
  }

  function measuredWidths(table, headers) {
    const tableWidth = table.getBoundingClientRect().width || table.offsetWidth;
    return headers.map(function (header) {
      const width = header.getBoundingClientRect().width;
      return Math.round(Math.max(MIN_WIDTH, width || tableWidth / headers.length || MIN_WIDTH));
    });
  }

  function applyWidths(table, widths) {
    const headers = headersFor(table);
    if (!headers.length || widths.length !== headers.length) return;
    rememberOriginal(table, headers.length);
    const columns = ensureColumns(table, headers.length);
    widths.forEach(function (width, index) {
      columns[index].style.width = Math.round(width) + "px";
    });
    const wrapper = table.closest(".tech-board-table, .tabela-wrapper");
    const available = wrapper ? wrapper.clientWidth : 0;
    const total = widths.reduce(function (sum, width) { return sum + width; }, 0);
    table.style.width = Math.max(total, available) + "px";
    table.classList.add("tech-columns-sized");
  }

  function tablesWithKey(key) {
    return Array.from(document.querySelectorAll("table.tech-resizable-table")).filter(function (table) {
      return table.dataset.techTableLayoutKey === key;
    });
  }

  function applyToGroup(key, widths) {
    tablesWithKey(key).forEach(function (table) { applyWidths(table, widths); });
  }

  function restoreOriginal(table) {
    const original = originalLayouts.get(table);
    if (!original) return;
    table.style.width = original.tableWidth;
    table.style.minWidth = original.minWidth;
    table.style.tableLayout = original.tableLayout;
    table.classList.remove("tech-columns-sized");
    const group = directColgroup(table);
    if (!original.hadColgroup) {
      if (group) group.remove();
      return;
    }
    if (!group) return;
    Array.from(group.children).forEach(function (col, index) {
      const style = original.columnStyles[index] || "";
      if (style) col.setAttribute("style", style);
      else col.removeAttribute("style");
    });
  }

  function resetGroup(key) {
    delete savedLayouts[key];
    writeLayouts();
    tablesWithKey(key).forEach(restoreOriginal);
  }

  function resizedWidths(widths, index, targetWidth) {
    const next = widths.slice();
    const current = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, targetWidth));
    const delta = current - widths[index];
    next[index] = current;

    /* Ao mover uma divisoria, a coluna vizinha absorve o espaco quando pode.
       Assim a tabela continua preenchendo o quadro, como numa planilha. */
    if (index < widths.length - 1 && delta !== 0) {
      const neighbor = widths[index + 1] - delta;
      next[index + 1] = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, neighbor));
    }
    return next;
  }

  function startResize(event, table, header, index, handle) {
    if (event.button != null && event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();

    const headers = headersFor(table);
    const key = table.dataset.techTableLayoutKey;
    const widths = measuredWidths(table, headers);
    const startX = event.clientX;
    const startWidth = widths[index];
    let latest = widths.slice();

    handle.classList.add("is-active");
    document.body.classList.add("tech-is-resizing-column");
    if (handle.setPointerCapture && event.pointerId != null) handle.setPointerCapture(event.pointerId);

    function move(moveEvent) {
      const delta = moveEvent.clientX - startX;
      latest = resizedWidths(widths, index, startWidth + delta);
      applyToGroup(key, latest);
      handle.setAttribute("aria-valuenow", String(Math.round(latest[index])));
    }

    function finish() {
      handle.classList.remove("is-active");
      document.body.classList.remove("tech-is-resizing-column");
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", finish);
      document.removeEventListener("pointercancel", finish);
      savedLayouts[key] = { widths: latest.map(Math.round) };
      writeLayouts();
    }

    document.addEventListener("pointermove", move);
    document.addEventListener("pointerup", finish, { once: true });
    document.addEventListener("pointercancel", finish, { once: true });
  }

  function keyboardResize(event, table, index, handle) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const headers = headersFor(table);
    const key = table.dataset.techTableLayoutKey;
    const widths = measuredWidths(table, headers);
    const step = event.shiftKey ? 32 : 12;
    const resized = resizedWidths(
      widths,
      index,
      widths[index] + (event.key === "ArrowRight" ? step : -step)
    );
    applyToGroup(key, resized);
    savedLayouts[key] = { widths: resized.map(Math.round) };
    writeLayouts();
    handle.setAttribute("aria-valuenow", String(Math.round(resized[index])));
  }

  function initializeTable(table) {
    if (table.dataset.techResizableReady === "1") return;
    const wrapper = table.closest(".tech-board-table, .tabela-wrapper");
    const headers = headersFor(table);
    if (!wrapper || headers.length < 2) return;

    rememberOriginal(table, headers.length);
    const key = layoutKey(table, headers);
    table.dataset.techTableLayoutKey = key;
    table.dataset.techResizableReady = "1";
    table.classList.add("tech-resizable-table");

    headers.forEach(function (header, index) {
      const handle = document.createElement("button");
      const columnName = String(header.textContent || "coluna").trim();
      handle.type = "button";
      handle.className = "tech-column-resizer";
      handle.tabIndex = 0;
      handle.setAttribute("role", "separator");
      handle.setAttribute("aria-orientation", "vertical");
      handle.setAttribute("aria-label", "Ajustar largura da coluna " + columnName);
      handle.setAttribute("aria-valuemin", String(MIN_WIDTH));
      handle.setAttribute("aria-valuemax", String(MAX_WIDTH));
      handle.setAttribute("title", "Arraste para ajustar; clique duas vezes para restaurar");
      handle.addEventListener("pointerdown", function (event) { startResize(event, table, header, index, handle); });
      handle.addEventListener("keydown", function (event) { keyboardResize(event, table, index, handle); });
      handle.addEventListener("dblclick", function (event) {
        event.preventDefault();
        event.stopPropagation();
        resetGroup(key);
      });
      header.appendChild(handle);
    });

    const saved = savedLayouts[key];
    if (saved && Array.isArray(saved.widths) && saved.widths.length === headers.length) {
      applyWidths(table, saved.widths.map(function (width) {
        return Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, Number(width) || MIN_WIDTH));
      }));
    }
  }

  function initializeTables(root) {
    const scope = root && root.querySelectorAll ? root : document;
    if (scope.matches && scope.matches("table.tabela")) initializeTable(scope);
    scope.querySelectorAll("table.tabela").forEach(initializeTable);
  }

  document.addEventListener("DOMContentLoaded", function () { initializeTables(document); });
  document.addEventListener("htmx:afterSwap", function (event) { initializeTables(event.target); });
  window.addEventListener("storage", function (event) {
    if (event.key !== STORAGE_KEY) return;
    savedLayouts = readLayouts();
    document.querySelectorAll("table.tech-resizable-table").forEach(function (table) {
      const saved = savedLayouts[table.dataset.techTableLayoutKey];
      if (saved && Array.isArray(saved.widths)) applyWidths(table, saved.widths);
      else restoreOriginal(table);
    });
  });
})();
