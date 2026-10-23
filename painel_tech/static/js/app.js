let techAvatarCacheVersion = Date.now();

document.addEventListener("DOMContentLoaded", function () {
  if (window.htmx) {
    htmx.config.defaultSwapStyle = "outerHTML";
  }

  const body = document.body;
  const sidebar = document.querySelector(".tech-sidebar");
  const botaoMenu = document.querySelector("[data-tech-menu-toggle]");
  const botoesFechar = document.querySelectorAll(
    "[data-tech-menu-close], [data-tech-sidebar-overlay]"
  );

  function definirMenuAberto(aberto, persistir) {
    body.classList.toggle("tech-menu-open", aberto);
    if (sidebar) sidebar.classList.toggle("open", aberto);
    if (botaoMenu) {
      botaoMenu.setAttribute("aria-expanded", aberto ? "true" : "false");
      botaoMenu.setAttribute("aria-label", aberto ? "Fechar menu" : "Abrir menu");
    }
    if (persistir !== false && window.innerWidth > 768) {
      try {
        localStorage.setItem("tech_sidebar_open", aberto ? "1" : "0");
      } catch (e) {
        // O menu continua funcional mesmo sem acesso ao armazenamento local.
      }
    }
    window.setTimeout(function () {
      window.dispatchEvent(new Event("resize"));
    }, 320);
  }

  if (window.innerWidth > 768) {
    try {
      definirMenuAberto(localStorage.getItem("tech_sidebar_open") === "1", false);
    } catch (e) {
      definirMenuAberto(false, false);
    }
  }

  if (botaoMenu) {
    botaoMenu.addEventListener("click", function () {
      definirMenuAberto(!body.classList.contains("tech-menu-open"));
    });
  }

  botoesFechar.forEach(function (botao) {
    botao.addEventListener("click", function () {
      definirMenuAberto(false);
    });
  });

  document.querySelectorAll(".tech-nav a").forEach(function (link) {
    link.addEventListener("click", function () {
      if (window.innerWidth <= 768) definirMenuAberto(false, false);
    });
  });

  const escolhasTema = document.querySelectorAll("[data-tech-theme-choice]");
  const statusTema = document.querySelector("[data-tech-theme-status]");

  function obterTemaTechAtual() {
    if (typeof window.obterTemaAtual === "function") return window.obterTemaAtual();
    return body.classList.contains("tema-claro") ? "claro" : "escuro";
  }

  function sincronizarControlesTema() {
    const temaAtual = obterTemaTechAtual();
    document.documentElement.classList.toggle("tema-claro", temaAtual === "claro");
    escolhasTema.forEach(function (botao) {
      const selecionado = botao.dataset.techThemeChoice === temaAtual;
      botao.classList.toggle("is-active", selecionado);
      botao.setAttribute("aria-pressed", selecionado ? "true" : "false");
    });
    if (statusTema) {
      statusTema.textContent =
        "Tema " + (temaAtual === "claro" ? "claro" : "escuro") + " ativo neste navegador.";
    }
  }

  function definirTemaTech(tema) {
    if (tema !== "claro" && tema !== "escuro") return;
    if (typeof window.definirTema === "function") {
      window.definirTema(tema);
    } else {
      body.classList.toggle("tema-claro", tema === "claro");
      try {
        localStorage.setItem("tema", tema);
      } catch (e) {
        // A troca visual continua funcional mesmo sem armazenamento local.
      }
    }
    sincronizarControlesTema();
    window.dispatchEvent(new CustomEvent("tech:themechange", { detail: { tema: tema } }));
  }

  escolhasTema.forEach(function (botao) {
    botao.addEventListener("click", function () {
      definirTemaTech(botao.dataset.techThemeChoice);
    });
  });
  sincronizarControlesTema();

  document.addEventListener("keydown", function (evento) {
    if (evento.key !== "Escape") return;
    if (document.querySelector(".notif-painel.aberto")) {
      fecharNotificacoesTech(true);
      evento.preventDefault();
      return;
    }
    if (body.classList.contains("tech-menu-open")) {
      definirMenuAberto(false);
      if (botaoMenu) botaoMenu.focus();
    }
  });

  window.addEventListener("resize", function () {
    if (window.innerWidth <= 768 && body.classList.contains("tech-menu-open")) {
      definirMenuAberto(false, false);
    }
  });

  inicializarSelectsTech(document);
  carregarAvataresTech(document);
});

function carregarAvataresTech(raiz) {
  const elementos = (raiz || document).querySelectorAll(
    "[data-tech-avatar-email]:not([data-avatar-loaded])"
  );
  const porEmail = new Map();

  elementos.forEach(function (elemento) {
    const email = (elemento.dataset.techAvatarEmail || "").trim();
    elemento.dataset.avatarLoaded = "true";
    if (!email) return;
    const chave = email.toLowerCase();
    if (!porEmail.has(chave)) porEmail.set(chave, { email: email, destinos: [] });
    porEmail.get(chave).destinos.push(elemento);
  });

  porEmail.forEach(function (grupo) {
    const email = grupo.email;
    const destinos = grupo.destinos;

    function aplicarImagem(url) {
      destinos.forEach(function (destino) {
        const imagem = document.createElement("img");
        imagem.src = url;
        imagem.alt = "";
        imagem.loading = "lazy";
        destino.replaceChildren(imagem);
        destino.classList.add("tech-avatar-has-photo");
      });
    }

    function buscarFotoDoPerfil() {
      fetch("/api/usuarios/" + encodeURIComponent(email) + "/foto", {
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      })
        .then(function (resposta) {
          if (!resposta.ok) throw new Error("Foto indisponível");
          return resposta.json();
        })
        .then(function (dados) {
          if (!dados || !dados.foto) throw new Error("Foto não cadastrada");
          aplicarImagem(dados.foto);
        })
        .catch(function () {
          // Mantém as iniciais ou o marcador neutro quando não há imagem.
        });
    }

    // A foto escolhida no Painel TECH usa a convenção por e-mail e tem prioridade.
    const candidato = "/static/images/profile_pictures/" + encodeURIComponent(email.toLowerCase() + ".png") + "?v=" + techAvatarCacheVersion;
    const teste = new Image();
    teste.onload = function () { aplicarImagem(candidato); };
    teste.onerror = buscarFotoDoPerfil;
    teste.src = candidato;
  });
}

document.addEventListener("htmx:afterSwap", function (evento) {
  inicializarSelectsTech(evento.target || document);
  if (evento.target && evento.target.id === "membros-conteudo") {
    techAvatarCacheVersion = Date.now();
    document.querySelectorAll("[data-tech-avatar-email]").forEach(function (avatar) {
      avatar.removeAttribute("data-avatar-loaded");
    });
    carregarAvataresTech(document);
    return;
  }
  carregarAvataresTech(evento.target || document);
});

let techRichSelectId = 0;
let techRichPositionFrame = 0;

function menuDoSelectTech(raiz) {
  return raiz && (raiz._techRichMenu || raiz.querySelector(".tech-rich-menu"));
}

function limparPosicaoMenuTech(menu) {
  if (!menu) return;
  menu.classList.remove("tech-rich-menu-portal");
  ["top", "right", "bottom", "left", "width", "maxHeight", "visibility"].forEach(function (propriedade) {
    menu.style.removeProperty(propriedade);
  });
}

function devolverMenuTech(raiz, menu) {
  if (!raiz || !menu) return;
  if (menu.parentNode !== raiz) raiz.appendChild(menu);
  limparPosicaoMenuTech(menu);
}

function portarMenuTech(raiz, menu) {
  if (!raiz || !menu) return;
  const dialogo = raiz.closest("dialog[open]");
  const destino = dialogo || document.body;
  if (menu.parentNode !== destino) destino.appendChild(menu);
  menu.classList.add("tech-rich-menu-portal");
}

function posicionarMenuTech(raiz) {
  const menu = menuDoSelectTech(raiz);
  const gatilho = raiz && raiz.querySelector(".tech-rich-trigger");
  if (!raiz || !raiz.isConnected || !raiz.classList.contains("is-open") || !menu || !gatilho) {
    return;
  }

  portarMenuTech(raiz, menu);
  const retangulo = gatilho.getBoundingClientRect();
  const viewport = window.visualViewport;
  const viewportEsquerda = viewport ? viewport.offsetLeft : 0;
  const viewportTopo = viewport ? viewport.offsetTop : 0;
  const viewportLargura = viewport ? viewport.width : document.documentElement.clientWidth;
  const viewportAltura = viewport ? viewport.height : window.innerHeight;
  const viewportDireita = viewportEsquerda + viewportLargura;
  const viewportBase = viewportTopo + viewportAltura;
  const margem = 12;
  const espaco = 6;

  if (
    retangulo.bottom <= viewportTopo ||
    retangulo.top >= viewportBase ||
    retangulo.right <= viewportEsquerda ||
    retangulo.left >= viewportDireita
  ) {
    fecharSelectsTech();
    return;
  }

  const larguraDisponivel = Math.max(1, viewportLargura - margem * 2);
  const larguraMinima = raiz.closest(".tech-board-person") ? 240 : retangulo.width;
  const largura = Math.min(Math.max(retangulo.width, larguraMinima), larguraDisponivel);
  const esquerdaMaxima = Math.max(viewportEsquerda + margem, viewportDireita - margem - largura);
  const esquerda = Math.min(Math.max(retangulo.left, viewportEsquerda + margem), esquerdaMaxima);
  const abaixo = Math.max(0, viewportBase - retangulo.bottom - espaco - margem);
  const acima = Math.max(0, retangulo.top - viewportTopo - espaco - margem);
  const alturaDesejada = Math.min(menu.scrollHeight || 280, 280);
  const abrirAbaixo = abaixo >= Math.min(alturaDesejada, 180) || abaixo >= acima;
  const alturaDisponivel = abrirAbaixo ? abaixo : acima;
  const alturaMaxima = Math.max(72, Math.min(280, alturaDisponivel));

  menu.style.visibility = "hidden";
  menu.style.width = Math.round(largura) + "px";
  menu.style.maxHeight = Math.floor(alturaMaxima) + "px";
  menu.style.left = Math.round(esquerda) + "px";
  menu.style.right = "auto";
  menu.style.bottom = "auto";

  const alturaMenu = Math.min(menu.getBoundingClientRect().height, alturaMaxima);
  let topo = abrirAbaixo
    ? retangulo.bottom + espaco
    : retangulo.top - espaco - alturaMenu;
  topo = Math.max(viewportTopo + margem, Math.min(topo, viewportBase - margem - alturaMenu));
  menu.style.top = Math.round(topo) + "px";
  menu.style.visibility = "";
}

function agendarPosicaoSelectsTech() {
  if (techRichPositionFrame) return;
  techRichPositionFrame = window.requestAnimationFrame(function () {
    techRichPositionFrame = 0;
    document.querySelectorAll("[data-tech-rich-root].is-open").forEach(posicionarMenuTech);
  });
}

function fecharSelectsTech(excecao) {
  document.querySelectorAll("[data-tech-rich-root].is-open").forEach(function (raiz) {
    if (raiz === excecao) return;
    raiz.classList.remove("is-open");
    const gatilho = raiz.querySelector(".tech-rich-trigger");
    const menu = menuDoSelectTech(raiz);
    if (gatilho) gatilho.setAttribute("aria-expanded", "false");
    if (menu) {
      menu.hidden = true;
      devolverMenuTech(raiz, menu);
    }
  });
}

function conteudoOpcaoTech(opcao, selecionada) {
  const fragmento = document.createDocumentFragment();
  const visual = document.createElement("span");
  visual.className = "tech-rich-option-visual";

  if (opcao.hasAttribute("data-avatar-email")) {
    const avatar = document.createElement("span");
    avatar.className = "tech-avatar tech-rich-avatar";
    if (opcao.dataset.avatarEmail) {
      avatar.dataset.techAvatarEmail = opcao.dataset.avatarEmail;
    }
    const nomes = opcao.textContent.trim().split(/\s+/).filter(Boolean);
    avatar.textContent = ((nomes[0] || "").charAt(0) + (nomes.length > 1 ? nomes[nomes.length - 1].charAt(0) : "")).toUpperCase();
    visual.appendChild(avatar);
  } else if (opcao.dataset.color) {
    const ponto = document.createElement("span");
    ponto.className = "tech-rich-dot tech-rich-dot-" + opcao.dataset.color;
    visual.appendChild(ponto);
  } else if (opcao.dataset.icon) {
    const icone = document.createElement("i");
    icone.className = opcao.dataset.icon;
    icone.setAttribute("aria-hidden", "true");
    visual.appendChild(icone);
  }

  const texto = document.createElement("span");
  texto.className = "tech-rich-option-label";
  texto.textContent = opcao.textContent.trim();
  visual.appendChild(texto);
  fragmento.appendChild(visual);

  if (selecionada) {
    const check = document.createElement("i");
    check.className = "fa-solid fa-check tech-rich-option-check";
    check.setAttribute("aria-hidden", "true");
    fragmento.appendChild(check);
  }
  return fragmento;
}

function inicializarSelectTech(select) {
  if (!select || select.dataset.richReady === "true") return;
  select.dataset.richReady = "true";
  select.classList.add("tech-rich-native");
  if (select.parentElement && select.parentElement.classList.contains("filter-item")) {
    select.parentElement.classList.add("has-tech-rich-select");
  }

  const raiz = document.createElement("div");
  raiz.className = "tech-rich-select";
  if (select.hasAttribute("data-tech-avatar-only")) {
    raiz.classList.add("tech-rich-select-avatar-only");
  }
  raiz.dataset.techRichRoot = "";
  select.parentNode.insertBefore(raiz, select);
  raiz.appendChild(select);

  const menuId = "tech-rich-menu-" + (++techRichSelectId);
  const gatilho = document.createElement("button");
  gatilho.type = "button";
  gatilho.className = "tech-rich-trigger";
  gatilho.setAttribute("aria-haspopup", "listbox");
  gatilho.setAttribute("aria-expanded", "false");
  gatilho.setAttribute("aria-controls", menuId);
  gatilho.setAttribute("aria-label", select.getAttribute("aria-label") || "Selecionar opção");
  gatilho.disabled = select.disabled;

  const valor = document.createElement("span");
  valor.className = "tech-rich-value";
  const seta = document.createElement("i");
  seta.className = "fa-solid fa-chevron-down tech-rich-chevron";
  seta.setAttribute("aria-hidden", "true");
  gatilho.append(valor, seta);

  const menu = document.createElement("div");
  menu.id = menuId;
  menu.className = "tech-rich-menu";
  menu.setAttribute("role", "listbox");
  menu.setAttribute("aria-label", select.getAttribute("aria-label") || "Opções");
  menu.hidden = true;
  raiz.append(gatilho, menu);
  raiz._techRichMenu = menu;

  function botoesMenu() {
    return Array.from(menu.querySelectorAll(".tech-rich-option:not([disabled])"));
  }

  function focarOpcao(delta) {
    const botoes = botoesMenu();
    if (!botoes.length) return;
    const atual = document.activeElement;
    let indice = botoes.indexOf(atual);
    if (indice < 0) indice = botoes.findIndex(function (botao) { return botao.getAttribute("aria-selected") === "true"; });
    indice = Math.max(0, indice);
    botoes[(indice + delta + botoes.length) % botoes.length].focus();
  }

  function abrir(focarSelecionada) {
    fecharSelectsTech(raiz);
    raiz.classList.add("is-open");
    gatilho.setAttribute("aria-expanded", "true");
    menu.hidden = false;
    posicionarMenuTech(raiz);
    if (focarSelecionada) {
      const selecionado = menu.querySelector('[aria-selected="true"]') || menu.querySelector(".tech-rich-option");
      if (selecionado) selecionado.focus();
    }
  }

  function fechar(devolverFoco) {
    raiz.classList.remove("is-open");
    gatilho.setAttribute("aria-expanded", "false");
    menu.hidden = true;
    devolverMenuTech(raiz, menu);
    if (devolverFoco) gatilho.focus();
  }

  function sincronizar() {
    const opcoes = Array.from(select.options);
    const selecionada = select.selectedOptions[0] || opcoes[0];
    raiz.dataset.tone = selecionada && selecionada.dataset.color ? selecionada.dataset.color : "";
    if (select.hasAttribute("data-tech-avatar-only")) {
      gatilho.title = selecionada ? selecionada.textContent.trim() : "";
    }
    valor.replaceChildren();
    if (selecionada) valor.appendChild(conteudoOpcaoTech(selecionada, false));
    menu.replaceChildren();

    opcoes.forEach(function (opcao) {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "tech-rich-option";
      item.setAttribute("role", "option");
      item.setAttribute("aria-selected", opcao.selected ? "true" : "false");
      item.disabled = opcao.disabled;
      item.dataset.value = opcao.value;
      item.appendChild(conteudoOpcaoTech(opcao, opcao.selected));
      item.addEventListener("click", function () {
        if (opcao.disabled) return;
        select.value = opcao.value;
        select.dispatchEvent(new Event("change", { bubbles: true }));
        fechar(true);
      });
      menu.appendChild(item);
    });
    carregarAvataresTech(raiz);
    carregarAvataresTech(menu);
    if (raiz.classList.contains("is-open")) posicionarMenuTech(raiz);
  }

  gatilho.addEventListener("click", function (evento) {
    evento.stopPropagation();
    if (raiz.classList.contains("is-open")) fechar(false);
    else abrir(false);
  });

  gatilho.addEventListener("keydown", function (evento) {
    if (["ArrowDown", "ArrowUp", "Enter", " "].includes(evento.key)) {
      evento.preventDefault();
      abrir(true);
    }
  });

  menu.addEventListener("keydown", function (evento) {
    if (evento.key === "ArrowDown" || evento.key === "ArrowUp") {
      evento.preventDefault();
      focarOpcao(evento.key === "ArrowDown" ? 1 : -1);
    } else if (evento.key === "Home" || evento.key === "End") {
      evento.preventDefault();
      const botoes = botoesMenu();
      const alvo = evento.key === "Home" ? botoes[0] : botoes[botoes.length - 1];
      if (alvo) alvo.focus();
    } else if (evento.key === "Escape" || evento.key === "Tab") {
      fechar(evento.key === "Escape");
    }
  });

  select.addEventListener("change", sincronizar);
  select.addEventListener("invalid", function (evento) {
    evento.preventDefault();
    raiz.classList.add("is-invalid");
    gatilho.focus();
  });
  select.addEventListener("change", function () {
    raiz.classList.remove("is-invalid");
  });
  if (select.form) {
    select.form.addEventListener("reset", function () {
      window.setTimeout(sincronizar, 0);
    });
  }
  sincronizar();
}

function inicializarSelectsTech(raiz) {
  const escopo = raiz && raiz.querySelectorAll ? raiz : document;
  escopo.querySelectorAll("select[data-tech-rich-select]").forEach(inicializarSelectTech);
}

document.addEventListener("click", function (evento) {
  if (!evento.target.closest("[data-tech-rich-root], .tech-rich-menu-portal")) fecharSelectsTech();
});

window.addEventListener("resize", function () {
  agendarPosicaoSelectsTech();
});

window.addEventListener("scroll", agendarPosicaoSelectsTech, true);
if (window.visualViewport) {
  window.visualViewport.addEventListener("resize", agendarPosicaoSelectsTech);
  window.visualViewport.addEventListener("scroll", agendarPosicaoSelectsTech);
}

document.addEventListener("htmx:beforeSwap", function () {
  fecharSelectsTech();
});

function fecharNotificacoesTech(devolverFoco) {
  document.querySelectorAll(".notif-painel.aberto").forEach(function (painel) {
    painel.classList.remove("aberto");
    painel.setAttribute("aria-hidden", "true");
    const botao = painel.closest(".notif").querySelector("[data-abrir-notif]");
    if (botao) {
      botao.setAttribute("aria-expanded", "false");
      if (devolverFoco) botao.focus();
    }
  });
}

document.addEventListener("click", function (evento) {
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

  const abrirNotif = evento.target.closest("[data-abrir-notif]");
  if (abrirNotif) {
    evento.stopPropagation();
    const painel = abrirNotif
      .closest(".notif")
      .querySelector(".notif-painel");
    if (painel) {
      const abrir = !painel.classList.contains("aberto");
      fecharNotificacoesTech(false);
      painel.classList.toggle("aberto", abrir);
      painel.setAttribute("aria-hidden", abrir ? "false" : "true");
      abrirNotif.setAttribute("aria-expanded", abrir ? "true" : "false");
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

  if (!evento.target.closest(".notif")) fecharNotificacoesTech(false);
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

function ativarAba(botao) {
  const grupo = botao.closest(".painel-abas");
  if (!grupo) return;
  grupo.querySelectorAll("[data-alvo]").forEach(function (b) {
    const ativo = b === botao;
    b.classList.toggle("active", ativo);
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
