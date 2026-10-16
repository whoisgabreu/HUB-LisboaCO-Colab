document.addEventListener("DOMContentLoaded", function () {
  if (window.htmx) {
    htmx.config.defaultSwapStyle = "outerHTML";
  }
  inicializarFiltros();
});

document.addEventListener("click", function (evento) {
  const alternarFiltros = evento.target.closest("[data-alternar-filtros]");
  if (alternarFiltros) {
    toggleFiltros(alternarFiltros);
    return;
  }

  const abaRelatorio = evento.target.closest("[data-rel-aba]");
  if (abaRelatorio) {
    const campo = document.querySelector("[data-rel-aba-campo]");
    if (campo) campo.value = abaRelatorio.dataset.relAba;
  }

  const aba = evento.target.closest("[data-alvo]");
  if (aba) {
    ativarAba(aba);
    return;
  }

  const abrirEdicao = evento.target.closest("[data-abrir-edicao]");
  if (abrirEdicao) {
    const modal = document.getElementById(abrirEdicao.dataset.abrirEdicao);
    if (modal) modal.showModal();
    return;
  }

  const fecharEdicao = evento.target.closest("[data-fechar-edicao]");
  if (fecharEdicao) {
    const modal = fecharEdicao.closest("dialog");
    if (modal) modal.close();
    return;
  }

  const tema = evento.target.closest("[data-tema-toggle]");
  if (tema) {
    const atual =
      document.documentElement.dataset.tema === "escuro" ? "claro" : "escuro";
    document.documentElement.dataset.tema = atual;
    try {
      localStorage.setItem("tema", atual);
    } catch (e) {}
    return;
  }

  const abrirNotif = evento.target.closest("[data-abrir-notif]");
  if (abrirNotif) {
    evento.stopPropagation();
    const painel = abrirNotif
      .closest(".notif")
      .querySelector(".notif-painel");
    if (painel) {
      painel.classList.toggle("aberto");
      abrirNotif.setAttribute(
        "aria-expanded",
        painel.classList.contains("aberto") ? "true" : "false"
      );
    }
    return;
  }

  const abrir = evento.target.closest("[data-abrir-historico]");
  if (abrir) {
    const modal = document.getElementById("modal-historico");
    if (modal) modal.showModal();
    return;
  }

  const fechar = evento.target.closest("[data-fechar-historico]");
  if (fechar) {
    const modal = fechar.closest("dialog");
    if (modal) modal.close();
    return;
  }

  if (evento.target.id === "modal-historico") {
    evento.target.close();
  }

  const dialogoEtapa = evento.target.closest("dialog.modal-etapa");
  if (dialogoEtapa && evento.target === dialogoEtapa) {
    dialogoEtapa.close();
  }

  document.querySelectorAll(".notif-painel.aberto").forEach(function (painel) {
    if (!painel.closest(".notif").contains(evento.target)) {
      painel.classList.remove("aberto");
      const botao = painel.parentNode.querySelector("[data-abrir-notif]");
      if (botao) botao.setAttribute("aria-expanded", "false");
    }
  });
});

function mostrarToast(dado) {
  const container = document.getElementById("toasts");
  if (!container) return;
  if (dado && dado.hasOwnProperty("value")) {
    dado = dado.value;
  }
  const itens = Array.isArray(dado) ? dado : [dado];
  itens.forEach(function (item) {
    const el = document.createElement("div");
    el.className = "toast toast-" + ((item && item.tipo) || "ok");
    el.textContent = (item && item.mensagem) || "";
    container.appendChild(el);
    setTimeout(function () {
      el.classList.add("toast-saindo");
      setTimeout(function () {
        el.remove();
      }, 220);
    }, 3200);
  });
}

document.addEventListener("toast", function (evento) {
  mostrarToast(evento.detail);
});

function toggleFiltros(botao) {
  const form = botao.closest(".filtros");
  if (!form) return;
  const colapsado = form.classList.toggle("collapsed");
  botao.setAttribute("aria-expanded", colapsado ? "false" : "true");
  try {
    sessionStorage.setItem("filtros-colapsado", colapsado ? "1" : "0");
  } catch (e) {}
}

function inicializarFiltros() {
  document.querySelectorAll(".filtros").forEach(function (form) {
    const botao = form.querySelector("[data-alternar-filtros]");
    const corpo = form.querySelector(".filtros-corpo");
    if (!botao || !corpo) return;
    let colapsado = null;
    try {
      colapsado = sessionStorage.getItem("filtros-colapsado");
    } catch (e) {}
    if (colapsado === null) {
      const ativos = parseInt(form.dataset.ativos || "0", 10) || 0;
      colapsado = ativos === 0 ? "1" : "0";
    }
    const colapsou = colapsado === "1";
    form.classList.toggle("collapsed", colapsou);
    botao.setAttribute("aria-expanded", colapsou ? "false" : "true");
  });
}

function ativarAba(botao) {
  const grupo = botao.closest(".painel-abas");
  if (!grupo) return;
  grupo.querySelectorAll("[data-alvo]").forEach(function (b) {
    const ativo = b === botao;
    b.classList.toggle("ativa", ativo);
    b.setAttribute("aria-selected", ativo ? "true" : "false");
  });
  grupo.querySelectorAll("[id^='aba-']").forEach(function (paine) {
    paine.hidden = paine.id !== botao.dataset.alvo;
  });
}

document.addEventListener("change", function (evento) {
  const check = evento.target.closest("[data-ocultar-concluidas]");
  if (!check) return;
  document.querySelectorAll(".etapas").forEach(function (lista) {
    lista.classList.toggle("ocultar-concluidas", check.checked);
  });
});

function formatoTempo(segundos) {
  segundos = Math.max(0, Math.floor(segundos));
  const horas = Math.floor(segundos / 3600);
  const minutos = Math.floor((segundos % 3600) / 60);
  if (horas > 0) {
    return horas + "h " + String(minutos).padStart(2, "0") + "min";
  }
  return minutos + "min";
}

function atualizarTempos() {
  const agora = Date.now();
  document.querySelectorAll("[data-tempo-total]").forEach(function (el) {
    const total = parseInt(el.dataset.tempoTotal || "0", 10) || 0;
    let extra = 0;
    String(el.dataset.tempoInicios || "")
      .split(",")
      .filter(Boolean)
      .forEach(function (ms) {
        const inicio = parseInt(ms, 10) || 0;
        if (inicio > 0) extra += Math.max(0, agora - inicio);
      });
    el.textContent = formatoTempo(total + extra / 1000);
  });
}

document.addEventListener("DOMContentLoaded", function () {
  atualizarTempos();
});
setInterval(atualizarTempos, 1000);

var csrfToken = "";
(function () {
  var meta = document.querySelector('meta[name="csrf-token"]');
  if (meta) csrfToken = meta.content;
})();

document.addEventListener(
  "submit",
  function (evento) {
    var form = evento.target;
    if (!csrfToken || !form || form.method.toLowerCase() !== "post") return;
    if (!form.querySelector('input[name="csrf_token"]')) {
      var campo = document.createElement("input");
      campo.type = "hidden";
      campo.name = "csrf_token";
      campo.value = csrfToken;
      form.appendChild(campo);
    }
  },
  true
);

document.addEventListener("htmx:configRequest", function (evento) {
  if (csrfToken) evento.detail.headers["X-CSRF-Token"] = csrfToken;
});
