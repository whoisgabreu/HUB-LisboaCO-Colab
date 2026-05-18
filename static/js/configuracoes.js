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
            lastAccess.innerText = new Date().toLocaleDateString('pt-BR') + ", às " + new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
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
        let preview = document.getElementById('previewAvatar');

        if (!input || !preview) return;

        input.addEventListener('change', function () {
            const file = this.files[0];
            if (!file) return;

            // Validação de tamanho (2MB)
            if (file.size > 2 * 1024 * 1024) {
                showToast('A imagem deve ter no máximo 2MB.', 'erro');
                this.value = '';
                return;
            }

            const reader = new FileReader();
            reader.onload = function (e) {
                // Se o elemento de preview for um ícone <i>, substituir por <img>
                if (preview.tagName !== 'IMG') {
                    const img = document.createElement('img');
                    img.id = 'previewAvatar';
                    img.alt = 'Avatar';
                    img.style.cssText = preview.style.cssText;
                    preview.parentNode.replaceChild(img, preview);
                    preview = img;
                }
                preview.src = e.target.result;
            };
            reader.readAsDataURL(file);
        });
    }


    // Envia a foto de perfil para o backend /upload-profile-picture
    window.salvarFotoPerfil = function () {
        // Verifica se um arquivo foi selecionado no input (fonte de verdade mais confiável)
        const inputFoto = document.getElementById('uploadFoto');
        const file = inputFoto && inputFoto.files[0];

        if (!file) {
            showToast('Selecione uma foto antes de salvar.', 'erro');
            return;
        }

        // Validação extra de tamanho (2MB)
        if (file.size > 2 * 1024 * 1024) {
            showToast('A imagem deve ter no máximo 2MB.', 'erro');
            return;
        }

        const formData = new FormData();
        formData.append('foto', file);

        fetch('/upload-profile-picture', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) return response.json().then(e => Promise.reject(e.erro || 'Erro no servidor'));
            return response.json();
        })
        .then(data => {
            if (data.mensagem === 'Foto salva com sucesso') {
                // Atualiza avatar no header com a URL pública correta
                const headerAvatar = document.getElementById('headerUserAvatar');
                if (headerAvatar) {
                    // Se o header ainda usa ícone <i>, substituir por <img>
                    if (headerAvatar.tagName !== 'IMG') {
                        const img = document.createElement('img');
                        img.id = 'headerUserAvatar';
                        img.alt = 'Avatar';
                        img.className = 'user-avatar-header';
                        headerAvatar.parentNode.replaceChild(img, headerAvatar);
                        img.src = data.url;
                    } else {
                        headerAvatar.src = data.url;
                    }
                }
                // Limpa o input para evitar re-envio acidental
                inputFoto.value = '';
                showToast('Foto de perfil salva com sucesso!', 'sucesso');
            } else {
                showToast(data.erro || data.mensagem || 'Erro desconhecido.', 'erro');
            }
        })
        .catch(error => {
            const msg = typeof error === 'string' ? error : (error.message || 'Erro ao salvar foto.');
            showToast(msg, 'erro');
        });
    };

    window.salvarFoto = function () {
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

    // enviar dados de senha para o backend rota /alterar-senha
    window.confirmarTrocaSenha = function () {
        const senhaAtual = document.getElementById('senhaAtual').value;
        const nova = document.getElementById('novaSenha').value;
        const confirm = document.getElementById('confirmarNovaSenha').value;

        if (!senhaAtual || !nova || !confirm) {
            showToast('Preencha todos os campos.', 'erro');
            return;
        }

        if (nova.length < 8) {
            showToast('A nova senha deve ter pelo menos 8 caracteres.', 'erro');
            return;
        }

        if (nova !== confirm) {
            showToast('As senhas não coincidem. Tente novamente.', 'erro');
            return;
        }

        fetch('/alterar-senha', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                senha_atual: senhaAtual,
                nova_senha: nova,
                confirmar_senha: confirm,
            }),
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Erro ao alterar senha');
                }
                return response.text();
            })
            .then(message => {
                showToast(message, 'sucesso');
                fecharModalTrocarSenha();
            })
            .catch(error => {
                showToast(error.message, 'erro');
            });



        // showToast('Mudança de senha disponível em breve (backend).');
        // fecharModalTrocarSenha();
    };

})();
