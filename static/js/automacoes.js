// ── Automações Module ──────────────────────────────────────────────────────────

const automacoes = {
    modalOpen: false,
    editingId: null,
    kanbanPhases: [],
    filters: {},

    // ── Init ──────────────────────────────────────────────────────────────────
    async init() {
        this.cacheElements();
        this.bindEvents();
        await this.loadKanbanPhases();
        await this.listAutomacoes();
    },

    cacheElements() {
        this.elements = {
            list: document.getElementById('automacoesList'),
            emptyState: document.getElementById('emptyState'),
            logsTab: document.getElementById('logsTabContent'),
            automacoesTab: document.getElementById('automacoesTabContent'),
            logsList: document.getElementById('logsList'),

            modal: document.getElementById('automacaoModalOverlay'),
            modalTitle: document.getElementById('automacaoModalTitle'),
            btnClose: document.getElementById('btnCloseAutomacaoModal'),
            btnCancel: document.getElementById('btnCancelAutomacao'),
            btnSave: document.getElementById('btnSaveAutomacao'),

            editId: document.getElementById('editAutomacaoId'),
            inputNome: document.getElementById('inputNome'),
            inputDescricao: document.getElementById('inputDescricao'),
            inputAtiva: document.getElementById('inputAtiva'),
            statusLabel: document.getElementById('statusLabel'),
            inputTriggerType: document.getElementById('inputTriggerType'),
            inputTriggerPhase: document.getElementById('inputTriggerPhase'),
            inputTriggerFromPhase: document.getElementById('inputTriggerFromPhase'),
            inputTriggerToPhase: document.getElementById('inputTriggerToPhase'),
            inputTriggerDays: document.getElementById('inputTriggerDays'),
            inputWebhookUrl: document.getElementById('inputWebhookUrl'),
            inputHttpMethod: document.getElementById('inputHttpMethod'),
            inputContentType: document.getElementById('inputContentType'),
            inputToken: document.getElementById('inputToken'),
            inputPayload: document.getElementById('inputPayload'),
            headersContainer: document.getElementById('headersContainer'),

            triggerPhaseConfig: document.getElementById('triggerPhaseConfig'),
            triggerFromToConfig: document.getElementById('triggerFromToConfig'),
            triggerDaysConfig: document.getElementById('triggerDaysConfig'),

            btnNewAutomacao: document.getElementById('btnNewAutomacao'),
            btnEmptyNew: document.getElementById('btnEmptyNew'),
            btnViewLogs: document.getElementById('btnViewLogs'),
            btnBackToAutomacoes: document.getElementById('btnBackToAutomacoes'),
            btnAddHeader: document.getElementById('btnAddHeader'),

            confirmModal: document.getElementById('confirmModalOverlay'),
            confirmMessage: document.getElementById('confirmMessage'),
            btnCloseConfirm: document.getElementById('btnCloseConfirm'),
            btnConfirmCancel: document.getElementById('btnConfirmCancel'),
            btnConfirmDelete: document.getElementById('btnConfirmDelete'),
        };
    },

    bindEvents() {
        const el = this.elements;

        el.btnNewAutomacao.addEventListener('click', () => this.openCreateModal());
        el.btnEmptyNew.addEventListener('click', () => this.openCreateModal());
        el.btnViewLogs.addEventListener('click', () => this.showLogs());
        el.btnBackToAutomacoes.addEventListener('click', () => this.showAutomacoes());

        el.btnClose.addEventListener('click', () => this.closeModal());
        el.btnCancel.addEventListener('click', () => this.closeModal());
        el.modal.addEventListener('click', (e) => {
            if (e.target === el.modal) this.closeModal();
        });

        el.btnSave.addEventListener('click', () => this.saveAutomacao());
        el.inputAtiva.addEventListener('change', () => {
            el.statusLabel.textContent = el.inputAtiva.checked ? 'Ativa' : 'Inativa';
        });

        el.inputTriggerType.addEventListener('change', () => this.onTriggerTypeChange());

        el.btnAddHeader.addEventListener('click', () => this.addHeaderRow());

        el.btnCloseConfirm.addEventListener('click', () => this._cancelDelete());
        el.btnConfirmCancel.addEventListener('click', () => this._cancelDelete());
        el.btnConfirmDelete.addEventListener('click', () => this._confirmDelete());
        el.confirmModal.addEventListener('click', (e) => {
            if (e.target === el.confirmModal) this._cancelDelete();
        });
    },

    // ── Load Kanban Phases ────────────────────────────────────────────────────
    async loadKanbanPhases() {
        try {
            const resp = await fetch('/api/automacoes/kanban-config');
            this.kanbanPhases = await resp.json();
            this.populatePhaseSelects();
        } catch (e) {
            console.error('Erro ao carregar fases do Kanban:', e);
        }
    },

    populatePhaseSelects() {
        const phases = this.kanbanPhases;
        const sel = (id, placeholder) => {
            const s = document.getElementById(id);
            s.innerHTML = `<option value="">${placeholder}</option>`;
            phases.forEach(p => {
                s.innerHTML += `<option value="${p.id}">${p.nome}</option>`;
            });
        };
        sel('inputTriggerPhase', 'Selecione uma fase...');
        sel('inputTriggerFromPhase', 'Selecione...');
        sel('inputTriggerToPhase', 'Selecione...');
    },

    // ── Trigger Type Change ────────────────────────────────────────────────────
    onTriggerTypeChange() {
        const type = this.elements.inputTriggerType.value;
        this.elements.triggerPhaseConfig.style.display = 'none';
        this.elements.triggerFromToConfig.style.display = 'none';
        this.elements.triggerDaysConfig.style.display = 'none';

        if (['card_entered_phase', 'card_left_phase', 'card_archived'].includes(type)) {
            this.elements.triggerPhaseConfig.style.display = 'block';
        } else if (type === 'card_moved') {
            this.elements.triggerFromToConfig.style.display = 'block';
        } else if (['project_days_before', 'project_days_after'].includes(type)) {
            this.elements.triggerDaysConfig.style.display = 'block';
        }
    },

    // ── CRUD: List ────────────────────────────────────────────────────────────
    async listAutomacoes() {
        try {
            const resp = await fetch('/api/automacoes');
            const list = await resp.json();
            this.renderList(list);
        } catch (e) {
            this.showToast('Erro ao carregar automações.', 'error');
        }
    },

    renderList(list) {
        const el = this.elements;
        if (!list || list.length === 0) {
            el.list.innerHTML = '';
            el.emptyState.style.display = 'block';
            return;
        }
        el.emptyState.style.display = 'none';

        const triggerLabels = {
            card_entered_phase: 'Card entrou em fase',
            card_left_phase: 'Card saiu de fase',
            card_moved: 'Card movido entre fases',
            card_created: 'Card criado',
            card_archived: 'Card arquivado',
            project_days_before: 'Dias antes do projeto',
            project_date_today: 'Data do projeto é hoje',
            project_days_after: 'Dias após o projeto',
        };

        el.list.innerHTML = list.map(a => {
            const isActive = a.ativa;
            const triggerLabel = triggerLabels[a.trigger_type] || a.trigger_type;
            return `
                <div class="automacao-card" data-id="${a.id}">
                    <div class="automacao-card-info">
                        <div class="automacao-card-name">
                            ${this.escapeHtml(a.nome)}
                            <span class="status-badge ${isActive ? 'active' : 'inactive'}">
                                ${isActive ? 'Ativa' : 'Inativa'}
                            </span>
                        </div>
                        ${a.descricao ? `<div class="automacao-card-desc">${this.escapeHtml(a.descricao)}</div>` : ''}
                        <div class="automacao-card-meta">
                            <span><i class="fas fa-bolt"></i> ${triggerLabel}</span>
                            <span><i class="fas fa-plug"></i> Webhook</span>
                        </div>
                    </div>
                    <div class="automacao-card-actions">
                        <button class="btn-automacao-toggle ${isActive ? 'active' : ''}" data-id="${a.id}" title="${isActive ? 'Desativar' : 'Ativar'}">
                            <i class="fas ${isActive ? 'fa-toggle-on' : 'fa-toggle-off'}"></i>
                        </button>
                        <button class="btn-icon btn-edit-automacao" data-id="${a.id}" title="Editar"><i class="fas fa-pen"></i></button>
                        <button class="btn-icon btn-delete-automacao" data-id="${a.id}" title="Excluir"><i class="fas fa-trash"></i></button>
                    </div>
                </div>
            `;
        }).join('');

        el.list.querySelectorAll('.btn-automacao-toggle').forEach(btn => {
            btn.addEventListener('click', () => this.toggleAutomacao(parseInt(btn.dataset.id)));
        });
        el.list.querySelectorAll('.btn-edit-automacao').forEach(btn => {
            btn.addEventListener('click', () => this.openEditModal(parseInt(btn.dataset.id)));
        });
        el.list.querySelectorAll('.btn-delete-automacao').forEach(btn => {
            btn.addEventListener('click', () => this.deleteAutomacao(parseInt(btn.dataset.id)));
        });
    },

    // ── CRUD: Toggle ──────────────────────────────────────────────────────────
    async toggleAutomacao(id) {
        try {
            const resp = await fetch(`/api/automacoes/${id}/toggle`, { method: 'POST' });
            const data = await resp.json();
            if (data.status === 'success') {
                this.showToast(data.ativa ? 'Automação ativada.' : 'Automação desativada.', 'success');
                await this.listAutomacoes();
            }
        } catch (e) {
            this.showToast('Erro ao alterar estado.', 'error');
        }
    },

    // ── CRUD: Create/Edit Modal ───────────────────────────────────────────────
    openCreateModal() {
        this.editingId = null;
        this.elements.modalTitle.innerHTML = '<i class="fas fa-plus-circle"></i> Nova Automação';
        this.elements.editId.value = '';
        this.resetForm();
        this.elements.modal.classList.add('active');
        this.modalOpen = true;
    },

    async openEditModal(id) {
        try {
            const resp = await fetch('/api/automacoes');
            const list = await resp.json();
            const a = list.find(item => item.id === id);
            if (!a) {
                this.showToast('Automação não encontrada.', 'error');
                return;
            }

            this.editingId = id;
            this.elements.modalTitle.innerHTML = '<i class="fas fa-pen"></i> Editar Automação';
            this.elements.editId.value = id;
            this.populateForm(a);
            this.elements.modal.classList.add('active');
            this.modalOpen = true;
        } catch (e) {
            this.showToast('Erro ao carregar automação.', 'error');
        }
    },

    closeModal() {
        this.elements.modal.classList.remove('active');
        this.modalOpen = false;
        this.editingId = null;
    },

    resetForm() {
        const el = this.elements;
        el.inputNome.value = '';
        el.inputDescricao.value = '';
        el.inputAtiva.checked = true;
        el.statusLabel.textContent = 'Ativa';
        el.inputTriggerType.value = '';
        el.inputTriggerPhase.value = '';
        el.inputTriggerFromPhase.value = '';
        el.inputTriggerToPhase.value = '';
        el.inputTriggerDays.value = '30';
        el.inputWebhookUrl.value = '';
        el.inputHttpMethod.value = 'POST';
        el.inputContentType.value = 'json';
        el.inputToken.value = '';
        el.inputPayload.value = '';
        el.headersContainer.innerHTML = `
            <div class="header-row">
                <input type="text" class="modern-input header-key" placeholder="Chave">
                <input type="text" class="modern-input header-value" placeholder="Valor">
                <button class="btn-icon btn-remove-header" title="Remover"><i class="fas fa-times"></i></button>
            </div>
        `;
        this.onTriggerTypeChange();
        this.bindHeaderRemoveButtons();
    },

    populateForm(a) {
        const el = this.elements;
        el.inputNome.value = a.nome || '';
        el.inputDescricao.value = a.descricao || '';
        el.inputAtiva.checked = a.ativa !== false;
        el.statusLabel.textContent = a.ativa !== false ? 'Ativa' : 'Inativa';
        el.inputTriggerType.value = a.trigger_type || '';
        this.onTriggerTypeChange();

        const tc = a.trigger_config || {};
        el.inputTriggerPhase.value = tc.phase_id || '';
        el.inputTriggerFromPhase.value = tc.from_phase_id || '';
        el.inputTriggerToPhase.value = tc.to_phase_id || '';
        el.inputTriggerDays.value = tc.days || '30';

        const ac = a.action_config || {};
        el.inputWebhookUrl.value = ac.url || '';
        el.inputHttpMethod.value = ac.method || 'POST';
        el.inputContentType.value = ac.content_type || 'json';
        el.inputToken.value = ac.token || '';
        el.inputPayload.value = ac.payload || '';

        el.headersContainer.innerHTML = '';
        const headers = ac.headers || [];
        if (headers.length === 0) {
            this.addHeaderRow();
        } else {
            headers.forEach(h => {
                const row = document.createElement('div');
                row.className = 'header-row';
                row.innerHTML = `
                    <input type="text" class="modern-input header-key" placeholder="Chave" value="${this.escapeHtml(h.key || h[0] || '')}">
                    <input type="text" class="modern-input header-value" placeholder="Valor" value="${this.escapeHtml(h.value || h[1] || '')}">
                    <button class="btn-icon btn-remove-header" title="Remover"><i class="fas fa-times"></i></button>
                `;
                el.headersContainer.appendChild(row);
            });
        }
        this.bindHeaderRemoveButtons();
    },

    // ── Save ──────────────────────────────────────────────────────────────────
    async saveAutomacao() {
        const el = this.elements;
        const nome = el.inputNome.value.trim();
        if (!nome) {
            this.showToast('O nome da automação é obrigatório.', 'error');
            return;
        }
        const triggerType = el.inputTriggerType.value;
        if (!triggerType) {
            this.showToast('Selecione um gatilho.', 'error');
            return;
        }
        const webhookUrl = el.inputWebhookUrl.value.trim();
        if (!webhookUrl) {
            this.showToast('A URL do webhook é obrigatória.', 'error');
            return;
        }

        const headers = [];
        el.headersContainer.querySelectorAll('.header-row').forEach(row => {
            const key = row.querySelector('.header-key').value.trim();
            const value = row.querySelector('.header-value').value.trim();
            if (key) {
                headers.push({ key, value });
            }
        });

        const triggerConfig = {};
        if (['card_entered_phase', 'card_left_phase', 'card_archived'].includes(triggerType)) {
            triggerConfig.phase_id = el.inputTriggerPhase.value;
        } else if (triggerType === 'card_moved') {
            triggerConfig.from_phase_id = el.inputTriggerFromPhase.value;
            triggerConfig.to_phase_id = el.inputTriggerToPhase.value;
        } else if (['project_days_before', 'project_days_after'].includes(triggerType)) {
            triggerConfig.days = parseInt(el.inputTriggerDays.value) || 0;
        }

        const actionConfig = {
            url: webhookUrl,
            method: el.inputHttpMethod.value,
            content_type: el.inputContentType.value,
            token: el.inputToken.value.trim(),
            headers: headers,
            payload: el.inputPayload.value,
        };

        const payload = {
            nome,
            descricao: el.inputDescricao.value.trim(),
            ativa: el.inputAtiva.checked,
            trigger_type: triggerType,
            trigger_config: triggerConfig,
            action_config: actionConfig,
        };

        try {
            let resp;
            if (this.editingId) {
                resp = await fetch(`/api/automacoes/${this.editingId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
            } else {
                resp = await fetch('/api/automacoes', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
            }
            const data = await resp.json();
            if (data.status === 'success') {
                this.showToast(this.editingId ? 'Automação atualizada.' : 'Automação criada.', 'success');
                this.closeModal();
                await this.listAutomacoes();
            } else {
                this.showToast(data.error || 'Erro ao salvar.', 'error');
            }
        } catch (e) {
            this.showToast('Erro de conexão.', 'error');
        }
    },

    // ── CRUD: Delete ───────────────────────────────────────────────────────────
    deleteAutomacao(id) {
        this._pendingDeleteId = id;
        this.elements.confirmMessage.textContent = 'Tem certeza que deseja excluir esta automação? Esta ação não pode ser desfeita.';
        this.elements.confirmModal.classList.add('active');
    },

    async _confirmDelete() {
        const id = this._pendingDeleteId;
        if (!id) return;
        this.elements.confirmModal.classList.remove('active');
        try {
            const resp = await fetch(`/api/automacoes/${id}`, { method: 'DELETE' });
            const data = await resp.json();
            if (data.status === 'success') {
                this.showToast('Automação excluída.', 'success');
                await this.listAutomacoes();
            } else {
                this.showToast(data.error || 'Erro ao excluir.', 'error');
            }
        } catch (e) {
            this.showToast('Erro de conexão.', 'error');
        }
        this._pendingDeleteId = null;
    },

    _cancelDelete() {
        this.elements.confirmModal.classList.remove('active');
        this._pendingDeleteId = null;
    },

    // ── Logs ──────────────────────────────────────────────────────────────────
    async showLogs() {
        this.elements.automacoesTab.style.display = 'none';
        this.elements.logsTab.style.display = 'block';
        await this.loadLogs();
    },

    showAutomacoes() {
        this.elements.logsTab.style.display = 'none';
        this.elements.automacoesTab.style.display = 'block';
    },

    async loadLogs() {
        try {
            const resp = await fetch('/api/automacoes/logs?limit=100');
            const logs = await resp.json();
            this.renderLogs(logs);
        } catch (e) {
            this.showToast('Erro ao carregar logs.', 'error');
        }
    },

    renderLogs(logs) {
        const el = this.elements.logsList;
        if (!logs || logs.length === 0) {
            el.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-history"></i>
                    <p>Nenhuma execução registrada ainda.</p>
                </div>
            `;
            return;
        }

        const eventLabels = {
            card_entered_phase: 'Card entrou em fase',
            card_left_phase: 'Card saiu de fase',
            card_moved: 'Card movido entre fases',
            card_created: 'Card criado',
            card_archived: 'Card arquivado',
            project_days_before: 'Dias antes do projeto',
            project_date_today: 'Data do projeto é hoje',
            project_days_after: 'Dias após o projeto',
        };

        el.innerHTML = logs.map(log => `
            <div class="log-entry">
                <div class="log-entry-header">
                    <span class="log-automacao-name">${this.escapeHtml(log.automacao_nome || '')}</span>
                    <span class="log-status ${log.status}">${log.status === 'success' ? 'Sucesso' : 'Falha'}</span>
                </div>
                <div class="log-details">
                    <span class="log-label">Evento:</span>
                    <span>${eventLabels[log.event_type] || log.event_type}</span>
                    <span class="log-label">URL:</span>
                    <span style="word-break:break-all;">${this.escapeHtml(log.url_chamada || '')}</span>
                    ${log.http_status ? `<span class="log-label">Status HTTP:</span><span>${log.http_status}</span>` : ''}
                    <span class="log-label">Data:</span>
                    <span>${log.executed_at ? new Date(log.executed_at).toLocaleString('pt-BR') : '-'}</span>
                </div>
                ${log.error_message ? `<div class="log-error"><i class="fas fa-exclamation-triangle"></i> ${this.escapeHtml(log.error_message)}</div>` : ''}
            </div>
        `).join('');
    },

    // ── Header rows ───────────────────────────────────────────────────────────
    addHeaderRow() {
        const row = document.createElement('div');
        row.className = 'header-row';
        row.innerHTML = `
            <input type="text" class="modern-input header-key" placeholder="Chave">
            <input type="text" class="modern-input header-value" placeholder="Valor">
            <button class="btn-icon btn-remove-header" title="Remover"><i class="fas fa-times"></i></button>
        `;
        this.elements.headersContainer.appendChild(row);
        this.bindHeaderRemoveButtons();
    },

    bindHeaderRemoveButtons() {
        this.elements.headersContainer.querySelectorAll('.btn-remove-header').forEach(btn => {
            btn.removeEventListener('click', this._onRemoveHeader);
            btn.addEventListener('click', this._onRemoveHeader = (e) => {
                const row = btn.closest('.header-row');
                if (this.elements.headersContainer.querySelectorAll('.header-row').length > 1) {
                    row.remove();
                } else {
                    row.querySelector('.header-key').value = '';
                    row.querySelector('.header-value').value = '';
                }
            });
        });
    },

    // ── Utilities ─────────────────────────────────────────────────────────────
    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },

    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        const el = document.createElement('div');
        el.className = `toast toast-${type}`;
        el.textContent = message;
        container.appendChild(el);
        setTimeout(() => {
            el.style.opacity = '0';
            el.style.transform = 'translateX(100%)';
            el.style.transition = 'all 0.3s ease';
            setTimeout(() => el.remove(), 300);
        }, 4000);
    },
};

// ── Init when DOM ready ───────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => automacoes.init());
