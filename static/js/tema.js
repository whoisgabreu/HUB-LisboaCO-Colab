/**
 * tema.js — Gerenciador de Tema (Claro/Escuro)
 * 
 * Responsabilidades:
 * - Ler preferência de tema do localStorage
 * - Aplicar classe 'tema-claro' no body
 * - Persistir escolha no localStorage
 * - Controlar modal de configurações e toggle
 * 
 * Chave do localStorage: 'tema'
 * Valores possíveis: 'claro' ou 'escuro' (padrão)
 */

(function () {
    'use strict';

    // =============================================
    // 1. APLICAR TEMA AO CARREGAR (evitar flash)
    // =============================================
    var temaArmazenado = localStorage.getItem('tema');
    if (temaArmazenado === 'claro') {
        document.body.classList.add('tema-claro');
    }

    // =============================================
    // 2. FUNÇÕES DE TEMA
    // =============================================

    /**
     * Retorna o tema atual ('claro' ou 'escuro')
     */
    function obterTemaAtual() {
        return document.body.classList.contains('tema-claro') ? 'claro' : 'escuro';
    }

    /**
     * Define o tema e persiste no localStorage
     * @param {string} tema - 'claro' ou 'escuro'
     */
    function definirTema(tema) {
        if (tema === 'claro') {
            document.body.classList.add('tema-claro');
            localStorage.setItem('tema', 'claro');
        } else {
            document.body.classList.remove('tema-claro');
            localStorage.setItem('tema', 'escuro');
        }

        // Atualizar toggle se o modal estiver aberto
        atualizarToggle();
    }

    /**
     * Alterna entre tema claro e escuro
     */
    function alternarTema() {
        var temaAtual = obterTemaAtual();
        definirTema(temaAtual === 'claro' ? 'escuro' : 'claro');
    }

    // =============================================
    // 3. MODAL DE CONFIGURAÇÕES
    // =============================================

    /**
     * Abre o modal de configurações
     * @param {Event} evento - Evento do clique (para preventDefault)
     */
    function abrirModalConfiguracoes(evento, abaPadrao = 'perfil') {
        if (evento) evento.preventDefault();

        var modal = document.getElementById('modalConfiguracoes');
        if (modal) {
            modal.classList.add('active');
            atualizarToggle();

            // Trocar para a aba solicitada
            if (window.switchConfigTab) {
                // Simula o clique no botão da sidebar para a aba correta
                const botoes = document.querySelectorAll('.config-tab-btn');
                const btnAlvo = Array.from(botoes).find(btn => btn.getAttribute('onclick')?.includes(`'${abaPadrao}'`));
                if (btnAlvo) {
                    window.switchConfigTab({ currentTarget: btnAlvo, preventDefault: () => {} }, abaPadrao);
                }
            }

            // Fechar dropdown do usuario se estiver aberto
            var dropdown = document.querySelector('.user-dropdown');
            if (dropdown) dropdown.classList.remove('active');
        }
    }

    /**
     * Fecha o modal de configurações
     */
    function fecharModalConfiguracoes() {
        var modal = document.getElementById('modalConfiguracoes');
        if (modal) {
            modal.classList.remove('active');
        }
    }

    /**
     * Atualiza o estado do toggle conforme o tema atual
     */
    function atualizarToggle() {
        var toggle = document.getElementById('toggleTemaClaro');
        if (toggle) {
            toggle.checked = obterTemaAtual() === 'claro';
        }
    }

    // =============================================
    // 4. EVENT LISTENERS
    // =============================================

    document.addEventListener('DOMContentLoaded', function () {
        // Toggle de tema
        var toggle = document.getElementById('toggleTemaClaro');
        if (toggle) {
            // Sincronizar estado ao carregar
            toggle.checked = obterTemaAtual() === 'claro';

            toggle.addEventListener('change', function () {
                definirTema(this.checked ? 'claro' : 'escuro');
            });
        }

        // Fechar modal ao clicar no overlay (fora do conteúdo)
        var modalOverlay = document.getElementById('modalConfiguracoes');
        if (modalOverlay) {
            modalOverlay.addEventListener('click', function (e) {
                if (e.target === this) {
                    fecharModalConfiguracoes();
                }
            });
        }

        // Fechar modal com ESC
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                var modal = document.getElementById('modalConfiguracoes');
                if (modal && modal.classList.contains('active')) {
                    fecharModalConfiguracoes();
                }
            }
        });
    });

    // =============================================
    // 5. EXPORTAR PARA ESCOPO GLOBAL
    // =============================================
    window.obterTemaAtual = obterTemaAtual;
    window.definirTema = definirTema;
    window.alternarTema = alternarTema;
    window.abrirModalConfiguracoes = abrirModalConfiguracoes;
    window.fecharModalConfiguracoes = fecharModalConfiguracoes;

})();
