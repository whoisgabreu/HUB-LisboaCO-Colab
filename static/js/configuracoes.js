/**
 * configuracoes.js — Lógica para o Modal de Configurações
 * 
 * Responsabilidades:
 * - Navegação entre abas (Perfil, Segurança, Preferências)
 * - Gestão de foto de perfil (Upload, Preview, LocalStorage)
 * - Persistência de preferências (Moeda, Fuso Horário, Confirmações, Densidade)
 * - Aplicação imediata da densidade da interface
 */

(function () {
    'use strict';

    // =============================================
    // 1. CARREGAR CONFIGURAÇÕES AO INICIAR
    // =============================================
    document.addEventListener('DOMContentLoaded', function () {
        carregarConfiguracoes();
        configurarUploadFoto();
    });

    /**
     * Carrega as configurações do localStorage e aplica ao modal e interface
     */
    function carregarConfiguracoes() {
        // Foto de Perfil
        const fotoSalva = localStorage.getItem('fotoPerfil');
        if (fotoSalva) {
            const preview = document.getElementById('previewAvatar');
            const headerAvatar = document.getElementById('headerUserAvatar');
            if (preview) preview.src = fotoSalva;
            if (headerAvatar) headerAvatar.src = fotoSalva;
        }

        // Moeda e Timezone
        const moeda = localStorage.getItem('moeda') || 'BRL';
        const timezone = localStorage.getItem('timezone') || 'America/Sao_Paulo';
        
        const selectMoeda = document.getElementById('selectMoeda');
        const selectTimezone = document.getElementById('selectTimezone');
        
        if (selectMoeda) selectMoeda.value = moeda;
        if (selectTimezone) selectTimezone.value = timezone;

        // Confirmações
        const confirmacoesRaw = localStorage.getItem('confirmacoes');
        const confirmacoes = confirmacoesRaw ? JSON.parse(confirmacoesRaw) : { excluir: true, arquivar: true };
        
        const toggleExcluir = document.getElementById('confirmExcluir');
        const toggleArquivar = document.getElementById('confirmArquivar');
        
        if (toggleExcluir) toggleExcluir.checked = confirmacoes.excluir;
        if (toggleArquivar) toggleArquivar.checked = confirmacoes.arquivar;

        // Informações de Sessão (MOCK)
        const currentDevice = document.getElementById('currentDevice');
        const lastAccess = document.getElementById('lastAccess');
        
        if (currentDevice) {
            currentDevice.innerText = window.navigator.userAgent.match(/\(([^)]+)\)/)?.[1] || "Dispositivo desconhecido";
        }
        if (lastAccess) {
            lastAccess.innerText = new Date().toLocaleDateString('pt-BR') + ", às " + new Date().toLocaleTimeString('pt-BR', {hour: '2-digit', minute:'2-digit'});
        }
    }

    // =============================================
    // 2. NAVEGAÇÃO ENTRE ABAS
    // =============================================
    window.switchConfigTab = function (event, tabName) {
        if (event) event.preventDefault();
        
        // Atualizar botões
        document.querySelectorAll('.config-tab-btn').forEach(btn => btn.classList.remove('active'));
        event.currentTarget.classList.add('active');

        // Atualizar seções
        document.querySelectorAll('.config-section').forEach(sec => sec.classList.remove('active'));
        const targetSection = document.getElementById('config-' + tabName);
        if (targetSection) targetSection.classList.add('active');
    };

    // =============================================
    // 3. FOTO DE PERFIL
    // =============================================
    function configurarUploadFoto() {
        const input = document.getElementById('uploadFoto');
        const preview = document.getElementById('previewAvatar');

        if (input && preview) {
            input.addEventListener('change', function () {
                const file = this.files[0];
                if (file) {
                    // Validação de tamanho (2MB)
                    if (file.size > 2 * 1024 * 1024) {
                        alert('Erro: A imagem deve ter no máximo 2MB.');
                        this.value = '';
                        return;
                    }

                    const reader = new FileReader();
                    reader.onload = function (e) {
                        preview.src = e.target.result;
                    };
                    reader.readAsDataURL(file);
                }
            });
        }
    }

    window.salvarFotoPerfil = function () {
        const preview = document.getElementById('previewAvatar');
        if (preview && preview.src.startsWith('data:image')) {
            try {
                localStorage.setItem('fotoPerfil', preview.src);
                
                // Atualizar no header imediatamente
                const headerAvatar = document.getElementById('headerUserAvatar');
                if (headerAvatar) headerAvatar.src = preview.src;
                
                alert('Foto de perfil salva com sucesso!');
            } catch (e) {
                alert('Erro ao salvar foto: a imagem pode ser muito grande para o armazenamento local.');
            }
        }
    };

    window.salvarFoto = function() {
        const preview = document.getElementById('previewAvatar');
        const headerAvatar = document.getElementById('headerUserAvatar');
        
        if (preview && preview.src && !preview.src.includes('default-avatar.png')) {
            try {
                localStorage.setItem('fotoPerfil', preview.src);
                if (headerAvatar) headerAvatar.src = preview.src;
                showToast('Foto de perfil atualizada com sucesso!');
            } catch (e) {
                showToast('Erro ao salvar: imagem muito grande.', 'erro');
            }
        } else {
            showToast('Selecione uma foto válida primeiro.', 'erro');
        }
    };

    // Sistema de Notificação (Toast)
    window.showToast = function(mensagem, tipo = 'sucesso') {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `toast ${tipo}`;
        const icone = tipo === 'sucesso' ? 'fa-check-circle' : 'fa-exclamation-circle';
        
        toast.innerHTML = `
            <i class="fas ${icone}"></i>
            <span>${mensagem}</span>
        `;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateY(0)';
        }, 10);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-20px)';
            setTimeout(() => toast.remove(), 500);
        }, 3000);
    };

    // =============================================
    // 5. SEGURANÇA (VISUAL APENAS)
    // =============================================
    window.abrirModalTrocarSenha = function () {
        const modal = document.getElementById('modalTrocarSenha');
        if (modal) modal.classList.add('active');
    };

    window.fecharModalTrocarSenha = function () {
        const modal = document.getElementById('modalTrocarSenha');
        if (modal) modal.classList.remove('active');
    };

    window.confirmarTrocaSenha = function () {
        const nova = document.getElementById('novaSenha').value;
        const confirm = document.getElementById('confirmarNovaSenha').value;

        if (nova.length < 8) {
            showToast('A nova senha deve ter pelo menos 8 caracteres.', 'erro');
            return;
        }

        if (nova !== confirm) {
            showToast('As senhas não coincidem. Tente novamente.', 'erro');
            return;
        }

        showToast('Mudança de senha disponível em breve (backend).');
        fecharModalTrocarSenha();
    };

})();
