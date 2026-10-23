(function () {
  "use strict";

  var checklistKey = "tech-project-checklist:" + window.location.pathname;
  var detailsKey = checklistKey + ":comments";
  var dialogTriggers = new WeakMap();

  function tabsDoProjeto() {
    return Array.from(document.querySelectorAll(".project-tabs [role='tab']"));
  }

  function ativarAbaPeloHash() {
    if (window.location.hash !== "#comentarios") return;
    var commentsTab = document.getElementById("project-tab-comments");
    if (commentsTab) commentsTab.click();
  }

  function aplicarEstadoChecklist() {
    var checkbox = document.querySelector("[data-ocultar-concluidas]");
    var etapas = document.querySelector(".etapas");
    if (checkbox && etapas) {
      var ocultar = window.sessionStorage.getItem(checklistKey) === "1";
      checkbox.checked = ocultar;
      etapas.classList.toggle("ocultar-concluidas", ocultar);
    }

    var salvos;
    try {
      salvos = JSON.parse(window.sessionStorage.getItem(detailsKey) || "{}");
    } catch (error) {
      salvos = {};
    }
    document.querySelectorAll(".project-task-comments").forEach(function (details) {
      var dialog = details.closest(".project-task") && details.closest(".project-task").querySelector("dialog[id]");
      if (dialog && Object.prototype.hasOwnProperty.call(salvos, dialog.id)) {
        details.open = Boolean(salvos[dialog.id]);
      }
    });
  }

  function salvarEstadoDosComentarios() {
    var salvos = {};
    document.querySelectorAll(".project-task-comments").forEach(function (details) {
      var task = details.closest(".project-task");
      var dialog = task && task.querySelector("dialog[id]");
      if (dialog) salvos[dialog.id] = details.open;
    });
    window.sessionStorage.setItem(detailsKey, JSON.stringify(salvos));
  }

  function fecharMenusDeEtapa(exceto) {
    document.querySelectorAll(".project-row-menu[open]").forEach(function (menu) {
      if (menu !== exceto) menu.removeAttribute("open");
    });
  }

  function ajustarPosicaoDoMenu(menu) {
    menu.classList.remove("is-up");
    var popover = menu.querySelector(".project-row-menu-popover");
    if (!popover) return;
    var rect = popover.getBoundingClientRect();
    var summaryRect = menu.querySelector("summary").getBoundingClientRect();
    if (rect.bottom > window.innerHeight - 12 && summaryRect.top > rect.height + 12) {
      menu.classList.add("is-up");
    }
  }

  function configurarCriacaoDeTask(parentId, parentLabel) {
    var form = document.querySelector(".project-new-stage");
    if (!form) return;

    var parentInput = form.querySelector("input[name='parent_id']");
    var nameInput = form.querySelector("input[name='nome']");
    if (!parentInput || !nameInput) return;

    form.reset();
    var isSubtask = Boolean(parentId);
    parentInput.value = parentId || "";
    nameInput.placeholder = isSubtask
      ? "Ex.: Configurar domínio flua.com.br"
      : "Ex.: Configurar subdomínio";
    form.classList.toggle("is-adding-subtask", isSubtask);

    var title = document.querySelector("[data-task-create-title]");
    var context = document.querySelector("[data-task-create-context]");
    var heading = form.querySelector("[data-task-form-heading]");
    var submit = form.querySelector("[data-task-create-submit]");
    if (title) title.textContent = isSubtask ? "Criar subtask" : "Criar task";
    if (context) {
      context.textContent = isSubtask
        ? "Nova subtask de “" + (parentLabel || "task principal") + "”."
        : "Adicione uma entrega principal ao plano.";
    }
    if (heading) heading.textContent = isSubtask ? "Dados da subtask" : "Dados da task";
    if (submit) submit.textContent = isSubtask ? "Criar subtask" : "Criar task";

    window.setTimeout(function () { nameInput.focus(); }, 80);
  }

  function prepararNovaTask() {
    configurarCriacaoDeTask("", "");
  }

  function prepararNovaEtapaComoSubtarefa(trigger) {
    configurarCriacaoDeTask(
      trigger.dataset.addSubtaskParent || "",
      trigger.dataset.addSubtaskLabel || ""
    );
  }

  document.addEventListener("keydown", function (event) {
    var openSelect = event.key === "Escape"
      ? document.querySelector(".project-stage-modal[open] .tech-rich-select.is-open")
      : null;
    if (openSelect) {
      var trigger = openSelect && openSelect.querySelector(".tech-rich-trigger");
      if (trigger) {
        event.preventDefault();
        event.stopImmediatePropagation();
        trigger.click();
        trigger.focus();
      }
      return;
    }

    var tab = event.target.closest(".project-tabs [role='tab']");
    if (!tab || !["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;

    var tabs = tabsDoProjeto();
    if (!tabs.length) return;
    event.preventDefault();

    var current = tabs.indexOf(tab);
    var next = current;
    if (event.key === "ArrowRight") next = (current + 1) % tabs.length;
    if (event.key === "ArrowLeft") next = (current - 1 + tabs.length) % tabs.length;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = tabs.length - 1;

    tabs[next].click();
    tabs[next].focus();
  });

  document.addEventListener("click", function (event) {
    var menuSummary = event.target.closest(".project-row-menu > summary");
    if (menuSummary) {
      fecharMenusDeEtapa(menuSummary.closest(".project-row-menu"));
    } else if (!event.target.closest(".project-row-menu")) {
      fecharMenusDeEtapa();
    }

    var subtaskTrigger = event.target.closest("[data-add-subtask-parent]");
    if (subtaskTrigger) {
      prepararNovaEtapaComoSubtarefa(subtaskTrigger);
      fecharMenusDeEtapa();
    } else if (event.target.closest("[data-create-task]")) {
      prepararNovaTask();
    }

    var tab = event.target.closest(".project-tabs [role='tab']");
    if (tab) {
      tabsDoProjeto().forEach(function (item) {
        item.tabIndex = item === tab ? 0 : -1;
      });
      var hash = tab.id === "project-tab-comments" ? "#comentarios" : window.location.pathname + window.location.search;
      window.history.replaceState(null, "", hash);
    }

    var dialogTrigger = event.target.closest("[data-abrir-historico], [data-abrir-edicao]");
    if (dialogTrigger) {
      var dialogId = dialogTrigger.dataset.abrirEdicao || "modal-historico";
      var dialog = document.getElementById(dialogId);
      if (dialog) dialogTriggers.set(dialog, dialogTrigger);
      fecharMenusDeEtapa();
    }
  });

  document.addEventListener("change", function (event) {
    if (event.target.matches("[data-ocultar-concluidas]")) {
      window.sessionStorage.setItem(checklistKey, event.target.checked ? "1" : "0");
    }
  });

  document.addEventListener("toggle", function (event) {
    if (event.target.matches(".project-task-comments")) salvarEstadoDosComentarios();
    if (event.target.matches(".project-row-menu") && event.target.open) {
      fecharMenusDeEtapa(event.target);
      window.requestAnimationFrame(function () { ajustarPosicaoDoMenu(event.target); });
    }
  }, true);

  document.addEventListener("close", function (event) {
    if (!(event.target instanceof HTMLDialogElement)) return;
    if (typeof fecharSelectsTech === "function") fecharSelectsTech();
    var trigger = dialogTriggers.get(event.target);
    if (trigger && document.contains(trigger)) trigger.focus();
  }, true);

  document.addEventListener("htmx:afterSwap", aplicarEstadoChecklist);

  document.addEventListener("DOMContentLoaded", function () {
    aplicarEstadoChecklist();
    ativarAbaPeloHash();
  });
})();
