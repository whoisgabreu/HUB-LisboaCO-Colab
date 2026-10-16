(function () {
  function urlComAba() {
    var params = new URLSearchParams(window.location.search);
    params.set("aba", "kanban");
    return "?" + params.toString();
  }

  function enviarStatus(evento) {
    var coluna = evento.to.closest(".kanban-coluna");
    var card = evento.item;
    if (!coluna || !card || !window.htmx) return;
    var novoStatus = coluna.dataset.status;
    var projetoId = card.dataset.projetoId;
    if (!novoStatus || !projetoId) return;
    htmx.ajax("POST", "/projetos/" + projetoId + "/mover" + urlComAba(), {
      target: "#kanban",
      swap: "outerHTML",
      values: { status: novoStatus },
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
    htmx.ajax("POST", "/projetos/fila/ordem" + urlComAba(), {
      target: "#kanban",
      swap: "outerHTML",
      values: { ids: ids.join(",") },
    });
  }

  function iniciarSortable() {
    if (!window.Sortable) return;
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

  document.addEventListener("htmx:afterSwap", function () {
    if (document.getElementById("kanban")) iniciarSortable();
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciarSortable);
  } else {
    iniciarSortable();
  }
})();
