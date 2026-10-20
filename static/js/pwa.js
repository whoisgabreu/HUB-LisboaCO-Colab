/**
 * pwa.js — Instalação, service worker, tema e estado de conexão.
 * Carregado em todas as páginas via components/pwa_head.html.
 */
(function () {
    "use strict";

    const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent) ||
        (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

    function estaInstalado() {
        return window.matchMedia("(display-mode: standalone)").matches ||
            window.navigator.standalone === true;
    }

    // ── Tema (theme-color) ───────────────────────────────────────────────
    function aplicarThemeColor() {
        const meta = document.getElementById("pwaThemeColor");
        if (!meta) return;
        const raiz = document.documentElement;
        const claro = document.body.classList.contains("tema-claro") ||
            raiz.dataset.tema === "claro" ||
            raiz.dataset.bsTheme === "light";
        meta.setAttribute("content", claro ? "#ffffff" : "#000000");
    }

    function observarTema() {
        aplicarThemeColor();
        if (!document.body) return;
        const observer = new MutationObserver(aplicarThemeColor);
        observer.observe(document.body, {
            attributes: true,
            attributeFilter: ["class"],
        });
        observer.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ["data-tema", "data-bs-theme"],
        });
    }

    // ── Banner de atualização ────────────────────────────────────────────
    let recarregarAoSolicitar = false;

    function mostrarBannerAtualizacao(worker) {
        if (document.getElementById("pwaUpdateBanner")) return;
        const banner = document.createElement("div");
        banner.id = "pwaUpdateBanner";
        banner.className = "pwa-update-banner";
        banner.innerHTML = `
            <span>Nova versão do HUB disponível.</span>
            <button type="button" id="pwaUpdateBtn">Atualizar</button>`;
        document.body.appendChild(banner);

        banner.querySelector("#pwaUpdateBtn").addEventListener("click", () => {
            recarregarAoSolicitar = true;
            banner.remove();
            if (worker) worker.postMessage({ type: "SKIP_WAITING" });
        });
    }

    function registrarServiceWorker() {
        if (!("serviceWorker" in navigator)) return;

        navigator.serviceWorker.addEventListener("controllerchange", () => {
            if (recarregarAoSolicitar) window.location.reload();
        });

        window.addEventListener("load", () => {
            navigator.serviceWorker
                .register("/sw.js", { scope: "/" })
                .then((registro) => {
                    if (registro.waiting && navigator.serviceWorker.controller) {
                        mostrarBannerAtualizacao(registro.waiting);
                    }
                    registro.addEventListener("updatefound", () => {
                        const novo = registro.installing;
                        if (!novo) return;
                        novo.addEventListener("statechange", () => {
                            if (novo.state === "installed" && navigator.serviceWorker.controller && registro.waiting) {
                                mostrarBannerAtualizacao(registro.waiting);
                            }
                        });
                    });
                })
                .catch((erro) => console.warn("[PWA] Falha ao registrar o service worker:", erro));
        });
    }

    // ── Instalação ───────────────────────────────────────────────────────
    let promptInstalacao = null;

    window.addEventListener("beforeinstallprompt", (event) => {
        event.preventDefault();
        promptInstalacao = event;
        if (document.readyState !== "loading") criarBotaoInstalar();
    });

    window.addEventListener("appinstalled", () => {
        const botao = document.getElementById("pwaInstallBtn");
        if (botao) botao.remove();
        promptInstalacao = null;
    });

    function criarBotaoInstalar() {
        if (estaInstalado()) return null;
        if (document.getElementById("pwaInstallBtn")) return document.getElementById("pwaInstallBtn");

        const botao = document.createElement("button");
        botao.id = "pwaInstallBtn";
        botao.type = "button";
        botao.className = "pwa-install-btn";
        botao.title = "Instalar o HUB";
        botao.innerHTML = '<i class="fa-solid fa-download"></i><span>Instalar</span>';

        const headerRight = document.querySelector(".header-right");
        if (headerRight) {
            headerRight.insertBefore(botao, headerRight.firstChild);
        } else {
            botao.classList.add("pwa-install-flutuante");
            document.body.appendChild(botao);
        }

        botao.addEventListener("click", async () => {
            if (isIOS) {
                mostrarInstrucoesIOS();
                return;
            }
            if (!promptInstalacao) return;
            promptInstalacao.prompt();
            const escolha = await promptInstalacao.userChoice;
            if (escolha && escolha.outcome === "accepted") botao.remove();
            promptInstalacao = null;
        });
        return botao;
    }

    function mostrarInstrucoesIOS() {
        const html = `
            <p>No <strong>Safari</strong>, toque em <strong>Compartilhar</strong>
            <i class="fa-solid fa-arrow-up-from-bracket"></i> e depois em
            <strong>Adicionar à Tela de Início</strong>.</p>`;
        if (window.HubModal && window.HubModal.alert) {
            window.HubModal.alert(html, { html: true, title: "Instalar o HUB", okLabel: "Entendi" });
        } else {
            alert("No Safari, toque em Compartilhar e depois em Adicionar à Tela de Início.");
        }
    }

    function configurarInstalacao() {
        if (estaInstalado()) return;
        if (isIOS || promptInstalacao) {
            criarBotaoInstalar();
        }
    }

    // ── Conexão ──────────────────────────────────────────────────────────
    function configurarConexao() {
        const toast = document.createElement("div");
        toast.id = "pwaOfflineToast";
        toast.className = "pwa-offline-toast";
        toast.textContent = "Você está sem conexão.";
        document.body.appendChild(toast);

        const atualizar = () => {
            toast.classList.toggle("aberto", !navigator.onLine);
        };
        window.addEventListener("online", atualizar);
        window.addEventListener("offline", atualizar);
        atualizar();
    }

    document.addEventListener("DOMContentLoaded", () => {
        observarTema();
        registrarServiceWorker();
        configurarInstalacao();
        configurarConexao();
    });
})();