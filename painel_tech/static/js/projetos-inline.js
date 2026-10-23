(function () {
  "use strict";

  function toast(mensagem, tipo) {
    if (typeof window.mostrarToast === "function") {
      window.mostrarToast({ mensagem: mensagem, tipo: tipo || "ok" });
    }
  }

  function definirDesabilitado(campo, desabilitado) {
    campo.disabled = desabilitado;
    const raiz = campo.closest("[data-tech-rich-root]");
    const gatilho = raiz && raiz.querySelector(".tech-rich-trigger");
    if (gatilho) gatilho.disabled = desabilitado;
  }

  function restaurarValor(campo, valor) {
    campo.value = valor || "";
    campo.dispatchEvent(new Event("change", { bubbles: false }));
  }

  async function salvar(campo) {
    if (!campo || campo.dataset.saving === "1") return;
    const valorAnterior = campo.dataset.previousValue != null
      ? campo.dataset.previousValue
      : (campo.dataset.techInlineOriginalValue != null ? campo.dataset.techInlineOriginalValue : campo.defaultValue);
    const token = document.querySelector('meta[name="csrf-token"]');
    const corpo = new URLSearchParams({ campo: campo.dataset.techInlineField, valor: campo.value });

    campo.dataset.saving = "1";
    definirDesabilitado(campo, true);
    const linha = campo.closest("[data-tech-project-row]");
    if (linha) linha.classList.add("tech-row-saving");

    try {
      const resposta = await fetch(campo.dataset.techInlineUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
          "X-CSRF-Token": token ? token.content : "",
          Accept: "application/json",
        },
        body: corpo.toString(),
      });
      const dados = await resposta.json().catch(function () { return {}; });
      if (!resposta.ok || !dados.ok) throw new Error(dados.erro || "Não foi possível atualizar o projeto.");
      toast(dados.mensagem || "Projeto atualizado.");
      window.location.reload();
    } catch (erro) {
      restaurarValor(campo, valorAnterior);
      definirDesabilitado(campo, false);
      delete campo.dataset.saving;
      if (linha) linha.classList.remove("tech-row-saving");
      toast(erro.message || "Não foi possível atualizar o projeto.", "erro");
    }
  }

  document.addEventListener("focusin", function (evento) {
    const campo = evento.target.closest("[data-tech-inline-field]");
    if (campo) campo.dataset.previousValue = campo.value;
  });

  document.addEventListener("change", function (evento) {
    const campo = evento.target.closest("[data-tech-inline-field]");
    if (campo) salvar(campo);
  });
})();
