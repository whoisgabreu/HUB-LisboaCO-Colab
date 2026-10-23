(function () {
  function urlComAba() {
    var params = new URLSearchParams(window.location.search);
    params.set("aba", "kanban");
    return "?" + params.toString();
  }

  function kanbanEl() {
    return document.getElementById("kanban");
  }

  function baseUrl() {
    var el = kanbanEl();
    var base = el && el.dataset ? el.dataset.base : "";
    return (base || "/tech/projetos").replace(/\/$/, "");
  }

  function podeEditar() {
    var el = kanbanEl();
    return Boolean(el && el.dataset.editavel === "1");
  }

  function mensagem(texto, tipo) {
    if (typeof window.mostrarToast === "function") {
      window.mostrarToast({ mensagem: texto, tipo: tipo || "ok" });
      return;
    }
    if (tipo === "erro") window.alert(texto);
  }

  function enviarStatus(evento) {
    var coluna = evento.to.closest(".kanban-coluna");
    var card = evento.item;
    if (!coluna || !card || !window.htmx) return;
    var novoStatus = coluna.dataset.status;
    var colunaId = coluna.dataset.colunaId;
    var projetoId = card.dataset.projetoId;
    if (!novoStatus || !colunaId || !projetoId) return;
    htmx.ajax("POST", baseUrl() + "/" + projetoId + "/mover" + urlComAba(), {
      target: "#kanban",
      swap: "outerHTML",
      values: { status: novoStatus, coluna_id: colunaId },
    });
  }

  function enviarOrdemFila(evento) {
    var lista = evento.to;
    if (!window.htmx) return;
    var ids = Array.prototype.slice
      .call(lista.querySelectorAll(".kanban-card"))
      .map(function (card) {
        return card.dataset.projetoId;
      })
      .filter(Boolean);
    if (!ids.length) return;
    htmx.ajax("POST", baseUrl() + "/fila/ordem" + urlComAba(), {
      target: "#kanban",
      swap: "outerHTML",
      values: { ids: ids.join(",") },
    });
  }

  function iniciarSortable() {
    if (!window.Sortable || !podeEditar()) return;
    document.querySelectorAll(".kanban-cards").forEach(function (lista) {
      var coluna = lista.closest(".kanban-coluna");
      var ehFila = coluna && coluna.dataset.status === "fila";
      if (lista._sortable) lista._sortable.destroy();
      lista._sortable = new Sortable(lista, {
        group: "kanban",
        animation: 150,
        sort: ehFila,
        draggable: ".kanban-card",
        ghostClass: "sortable-ghost",
        chosenClass: "sortable-chosen",
        onEnd: function (evento) {
          if (evento.from !== evento.to) {
            enviarStatus(evento);
          } else if (ehFila) {
            enviarOrdemFila(evento);
          }
        },
      });
    });
  }

  function editor() {
    return document.getElementById("kanban-editor");
  }

  function listaEditor() {
    var modal = editor();
    return modal && modal.querySelector("[data-kanban-editor-lista]");
  }

  function novaColunaId() {
    var parte;
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      parte = window.crypto.randomUUID().replace(/-/g, "").slice(0, 12);
    } else {
      parte = Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
    }
    return "coluna-" + parte;
  }

  function ativarEditor(modal) {
    // O Hub possui uma regra global `.modal { display: none; height: 100% }`.
    // A classe e a altura abaixo tornam o <dialog> visível sem alterar o CSS
    // compartilhado e são sempre removidas ao fechar.
    modal.classList.add("active");
    modal.style.height = "auto";
  }

  function desativarEditor(modal) {
    modal.classList.remove("active");
    modal.style.removeProperty("height");
  }

  function abrirEditor(colunaId) {
    var modal = editor();
    var lista = listaEditor();
    if (!modal || !lista) return;
    if (!modal.open) {
      modal._kanbanSnapshot = lista.innerHTML;
      if (typeof modal.showModal === "function") {
        modal.showModal();
      } else {
        modal.setAttribute("open", "");
      }
    }
    ativarEditor(modal);

    var linha = Array.prototype.find.call(
      lista.querySelectorAll("[data-kanban-editor-linha]"),
      function (item) {
        return item.dataset.colunaId === colunaId;
      }
    );
    var foco = linha
      ? linha.querySelector("[data-kanban-coluna-nome]")
      : lista.querySelector("[data-kanban-coluna-nome]");
    if (foco) window.setTimeout(function () { foco.focus(); }, 0);
  }

  function restaurarEditor() {
    var modal = editor();
    var lista = listaEditor();
    if (!modal || !lista || typeof modal._kanbanSnapshot !== "string") return;
    lista.innerHTML = modal._kanbanSnapshot;
    delete modal._kanbanSnapshot;
  }

  function fecharEditor() {
    var modal = editor();
    if (!modal) return;
    restaurarEditor();
    desativarEditor(modal);
    if (modal.open && typeof modal.close === "function") {
      modal.close();
    } else {
      modal.removeAttribute("open");
    }
  }

  function adicionarColuna() {
    var lista = listaEditor();
    var modelo = document.getElementById("kanban-coluna-template");
    if (!lista || !modelo) return;
    var fragmento = modelo.content.cloneNode(true);
    var linha = fragmento.querySelector("[data-kanban-editor-linha]");
    linha.dataset.colunaId = novaColunaId();
    lista.appendChild(fragmento);
    var nome = linha.querySelector("[data-kanban-coluna-nome]");
    if (nome) nome.focus();
  }

  function removerColuna(botao) {
    var linha = botao.closest("[data-kanban-editor-linha]");
    var lista = listaEditor();
    if (!linha || !lista) return;
    var status = linha.querySelector("[data-kanban-coluna-status]").value;
    if (!status) {
      linha.remove();
      return;
    }
    var quantidade = Array.prototype.filter.call(
      lista.querySelectorAll("[data-kanban-coluna-status]"),
      function (campo) {
        return campo.value === status;
      }
    ).length;
    if (quantidade <= 1) {
      mensagem("Mantenha ao menos uma coluna para esse comportamento.", "erro");
      return;
    }
    linha.remove();
  }

  function coletarColunas() {
    var lista = listaEditor();
    if (!lista) return [];
    return Array.prototype.map.call(
      lista.querySelectorAll("[data-kanban-editor-linha]"),
      function (linha) {
        return {
          id: linha.dataset.colunaId,
          nome: linha.querySelector("[data-kanban-coluna-nome]").value.trim(),
          cor: linha.querySelector("[data-kanban-coluna-cor]").value,
          status_base: linha.querySelector("[data-kanban-coluna-status]").value,
        };
      }
    );
  }

  function validarCobertura(colunas) {
    var modal = editor();
    var obrigatorios = String(modal.dataset.statusObrigatorios || "")
      .split(",")
      .filter(Boolean);
    var ausentes = obrigatorios.filter(function (status) {
      return !colunas.some(function (coluna) {
        return coluna.status_base === status;
      });
    });
    if (ausentes.length) {
      mensagem("Mantenha ao menos uma coluna para cada comportamento.", "erro");
      return false;
    }
    return true;
  }

  async function salvarEditor(form) {
    var modal = editor();
    if (!modal || !form.reportValidity()) return;
    var colunas = coletarColunas();
    if (!validarCobertura(colunas)) return;

    var botao = form.querySelector("[data-kanban-editor-salvar]");
    var tokenMeta = document.querySelector('meta[name="csrf-token"]');
    var headers = { "Content-Type": "application/json", Accept: "application/json" };
    if (tokenMeta && tokenMeta.content) headers["X-CSRF-Token"] = tokenMeta.content;

    if (botao) {
      botao.disabled = true;
      botao.setAttribute("aria-busy", "true");
    }
    try {
      var resposta = await fetch(modal.dataset.saveUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: headers,
        body: JSON.stringify({ colunas: colunas }),
      });
      var dados = await resposta.json().catch(function () { return {}; });
      if (!resposta.ok || !dados.ok) {
        throw new Error(dados.erro || "Não foi possível salvar as colunas.");
      }
      delete modal._kanbanSnapshot;
      desativarEditor(modal);
      if (modal.open && typeof modal.close === "function") modal.close();
      window.location.reload();
    } catch (erro) {
      mensagem(erro.message || "Não foi possível salvar as colunas.", "erro");
    } finally {
      if (botao) {
        botao.disabled = false;
        botao.removeAttribute("aria-busy");
      }
    }
  }

  function iniciarEditor() {
    var modal = editor();
    var lista = listaEditor();
    if (!modal || !lista) return;
    if (window.Sortable && !lista._sortable) {
      lista._sortable = new Sortable(lista, {
        animation: 150,
        handle: "[data-kanban-editor-handle]",
        draggable: "[data-kanban-editor-linha]",
        ghostClass: "sortable-ghost",
        chosenClass: "sortable-chosen",
      });
    }
    modal.addEventListener("cancel", function () {
      restaurarEditor();
      desativarEditor(modal);
    });
    modal.addEventListener("close", function () {
      desativarEditor(modal);
    });
    modal.addEventListener("click", function (evento) {
      if (evento.target === modal) fecharEditor();
    });
    var form = modal.querySelector("[data-kanban-editor-form]");
    if (form) {
      form.addEventListener("submit", function (evento) {
        evento.preventDefault();
        salvarEditor(form);
      });
    }
  }

  document.addEventListener("click", function (evento) {
    var abrir = evento.target.closest("[data-kanban-editor-open]");
    if (abrir) {
      abrirEditor(abrir.dataset.colunaFoco || "");
      return;
    }
    if (evento.target.closest("[data-kanban-editor-close]")) {
      fecharEditor();
      return;
    }
    if (evento.target.closest("[data-kanban-coluna-adicionar]")) {
      adicionarColuna();
      return;
    }
    var remover = evento.target.closest("[data-kanban-coluna-remover]");
    if (remover) removerColuna(remover);
  });

  document.addEventListener("htmx:afterSwap", function () {
    if (kanbanEl()) iniciarSortable();
  });

  function iniciar() {
    iniciarSortable();
    iniciarEditor();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
