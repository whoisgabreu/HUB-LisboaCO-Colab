const kanbanConfig = {
    overlay: null,
    body: null,
    saveBtn: null,
    cancelBtn: null,
    
    currentConfig: null,
    expandedPhaseIndex: 0, 

    init() {
        this.overlay = document.getElementById('configModalOverlay');
        this.body = document.getElementById('configModalBody');
        this.saveBtn = document.getElementById('btnConfigSave');
        this.cancelBtn = document.getElementById('btnConfigCancel');

        const btn = document.getElementById('btnConfig');
        if (btn) btn.onclick = () => this.show();
        
        if (this.cancelBtn) this.cancelBtn.onclick = () => this.hide();
        if (this.saveBtn) this.saveBtn.onclick = () => this.save();
        
        const closeBtn = document.getElementById('btnCloseConfigModal');
        if (closeBtn) closeBtn.onclick = () => this.hide();

        if (this.overlay) {
            this.overlay.onclick = (e) => { if (e.target === this.overlay) this.hide(); };
        }
    },

    show() {
        if (!board.config) return toast.error("Configuração não carregada.");
        this.currentConfig = JSON.parse(JSON.stringify(board.config)); // Deep copy
        this.expandedPhaseIndex = 0; 
        this.render();
        this.overlay.style.display = 'flex';
    },

    hide() {
        this.overlay.style.display = 'none';
    },

    togglePhase(index) {
        this.expandedPhaseIndex = this.expandedPhaseIndex === index ? -1 : index;
        this.render();
    },

    render() {
        if (!this.body) return;
        const totalFases = (this.currentConfig.fases || []).length;
        this.body.innerHTML = `
            <div class="config-section-header">
                <div class="config-section-title">
                    <i class="fas fa-sliders-h"></i> Configurações Gerais
                </div>
                <div class="form-group">
                    <label><i class="fas fa-clipboard-list"></i> Nome do Board</label>
                    <input type="text" id="config_kanban_nome" class="modern-input" value="${this.currentConfig.nome}" placeholder="Ex: Fluxo de Projetos">
                </div>
            </div>
            <div class="config-phases-section">
                <div class="config-phases-header">
                    <div class="config-phases-title">
                        <i class="fas fa-layer-group"></i> Fases do Fluxo
                        <span class="phases-count-badge">${totalFases}</span>
                    </div>
                    <span class="config-phases-hint">Clique em uma fase para editá-la</span>
                </div>
                <div id="phases_container"></div>
                <button id="btn_add_phase" class="btn-add-phase-main">
                    <i class="fas fa-plus-circle"></i> Adicionar Nova Fase
                </button>
            </div>
        `;

        const container = document.getElementById('phases_container');
        const sortedFases = this.currentConfig.fases.sort((a,b) => a.ordem - b.ordem);

        sortedFases.forEach((fase, fIndex) => {
            const isExpanded = this.expandedPhaseIndex === fIndex;
            const phaseCard = document.createElement('div');
            phaseCard.className = `phase-accordion-item ${isExpanded ? 'active' : ''}`;

            phaseCard.innerHTML = `
                <div class="phase-accordion-header" data-findex="${fIndex}">
                    <div class="phase-header-left">
                        <span class="phase-order-badge">${fase.ordem}</span>
                        <span class="phase-title-text">${fase.nome}</span>
                    </div>
                    <div class="phase-header-actions">
                        <button class="btn-icon-small btn-move-phase" data-findex="${fIndex}" data-dir="-1" title="Subir"><i class="fas fa-arrow-up"></i></button>
                        <button class="btn-icon-small btn-move-phase" data-findex="${fIndex}" data-dir="1" title="Descer"><i class="fas fa-arrow-down"></i></button>
                        <span class="accordion-arrow">${isExpanded ? '<i class="fas fa-chevron-down"></i>' : '<i class="fas fa-chevron-right"></i>'}</span>
                    </div>
                </div>
                
                <div class="phase-accordion-body" style="display: ${isExpanded ? 'block' : 'none'}">
                    <div class="phase-settings-row">
                        <div class="form-group-inline" style="flex:1.5;">
                            <label>Nome da Fase</label>
                            <input type="text" value="${fase.nome}" class="modern-input phase-name-input" data-findex="${fIndex}">
                        </div>
                        <div class="form-group-inline" style="flex:1.2;">
                            <label>Status do Projeto *</label>
                            <div class="status-pills" data-findex="${fIndex}">
                                ${['Ativo', 'Onetime', 'Inativo'].map(s => `
                                    <button type="button" class="status-pill status-pill-${s.toLowerCase()} ${fase.status_do_projeto === s ? 'active' : ''}" data-findex="${fIndex}" data-status="${s}">
                                        <span class="status-pill-dot"></span>${s}
                                    </button>
                                `).join('')}
                            </div>
                        </div>
                        <div style="display:flex; align-items:center; gap:20px; padding-top:20px;">
                            <label class="checkbox-label" style="cursor:pointer;">
                                <input type="checkbox" class="phase-direct-access-check" data-findex="${fIndex}" ${fase.permite_acesso_direto ? 'checked' : ''}>
                                <i class="fas fa-bolt" style="color:#d61616; margin-right:4px;"></i> Acesso Direto
                            </label>
                            <button class="btn-danger btn-remove-phase" data-findex="${fIndex}" title="Excluir fase" style="padding: 8px 12px; border-radius: 8px; font-size: 0.8rem;">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>

                    <div class="fields-config-section">
                        <div class="fields-config-header-row">
                            <div class="fields-config-header-title">
                                <i class="fas fa-list-check"></i> Campos desta Fase
                                <span class="fields-count-badge">${fase.campos.length}</span>
                            </div>
                            <span class="fields-config-hint">Informações que aparecem no card do projeto</span>
                        </div>
                        <div class="fields-list" data-findex="${fIndex}">
                            ${fase.campos.map((campo, cIndex) => `
                                <div class="field-item-card field-card-v2">
                                    <div class="field-main-row">
                                        <div class="field-type-icon" data-type="${campo.tipo}" title="${this._fieldLabel(campo.tipo)}">
                                            <i class="fas ${this._fieldIcon(campo.tipo)}"></i>
                                        </div>
                                        <input type="text" value="${campo.label}" placeholder="Nome do campo (ex: Cliente, Valor)" class="modern-input field-label-input" data-findex="${fIndex}" data-cindex="${cIndex}">
                                        <select class="modern-select field-type-select" data-findex="${fIndex}" data-cindex="${cIndex}">
                                            ${this._fieldTypes().map(t => `<option value="${t.v}" ${t.v === campo.tipo ? 'selected' : ''}>${t.l}</option>`).join('')}
                                        </select>
                                        <label class="field-req-toggle" title="Campo obrigatório?">
                                            <input type="checkbox" ${campo.obrigatorio ? 'checked' : ''} class="field-req-check" data-findex="${fIndex}" data-cindex="${cIndex}">
                                            <span class="field-req-pill">Obrigatório</span>
                                        </label>
                                        <button class="field-remove-btn" data-findex="${fIndex}" data-cindex="${cIndex}" title="Remover campo">
                                            <i class="fas fa-trash"></i>
                                        </button>
                                    </div>
                                    <div class="field-sync-row">
                                        <label class="field-sync-toggle-wrap" title="Sincronizar este campo com uma coluna do banco">
                                            <input type="checkbox" class="field-sync-toggle" data-findex="${fIndex}" data-cindex="${cIndex}" ${campo.mapeamento_coluna ? 'checked' : ''}>
                                            <span class="field-sync-toggle-label">
                                                <i class="fas fa-database"></i> Sincronizar com banco de dados
                                            </span>
                                        </label>
                                        <div class="field-sync-select-wrap" style="display:${campo.mapeamento_coluna ? 'flex' : 'none'};">
                                            <span class="field-sync-arrow"><i class="fas fa-arrow-right-long"></i></span>
                                            <select class="modern-select field-mapping-select field-mapping-compact" data-findex="${fIndex}" data-cindex="${cIndex}">
                                                <option value="">Selecione a coluna...</option>
                                                ${["nome", "documento", "fee", "moeda", "squad_atribuida", "produto_contratado", "data_de_inicio", "cohort", "meta_account_id", "google_account_id", "url_webhook_gchat", "step", "informacoes_gerais", "orcamento_midia_meta", "orcamento_midia_google", "data_fim", "ekyte_workspace"].map(col => `
                                                    <option value="${col}" ${col === campo.mapeamento_coluna ? 'selected' : ''}>${col}</option>
                                                `).join('')}
                                            </select>
                                        </div>
                                    </div>
                                    ${['select', 'checkbox', 'radio'].includes(campo.tipo) ? `
                                        <div class="field-options-area">
                                            <label><i class="fas fa-list"></i> Opções disponíveis</label>
                                            <input type="text" class="modern-input field-options-input" data-findex="${fIndex}" data-cindex="${cIndex}"
                                                   placeholder="Ex: Aprovado, Pendente, Recusado" value="${(campo.opcoes || []).join(', ')}">
                                            <span class="field-options-hint">Separe cada opção por vírgula</span>
                                        </div>
                                    ` : ''}
                                </div>
                            `).join('')}
                            ${fase.campos.length === 0 ? `
                                <div class="fields-empty-state">
                                    <i class="fas fa-folder-open"></i>
                                    <p>Nenhum campo configurado nesta fase.</p>
                                    <small>Adicione campos para registrar informações sobre o projeto.</small>
                                </div>
                            ` : ''}
                        </div>
                        <button class="btn-add-field-sec-v2" data-findex="${fIndex}">
                            <i class="fas fa-plus-circle"></i> Adicionar Campo
                        </button>
                    </div>
                </div>
            `;
            container.appendChild(phaseCard);
        });

        this.attachEvents();
    },

    attachEvents() {
        this.body.querySelectorAll('.phase-accordion-header').forEach(header => {
            header.onclick = (e) => {
                if (e.target.closest('button')) return; 
                const fIndex = parseInt(header.dataset.findex);
                this.togglePhase(fIndex);
            };
        });

        this.body.querySelectorAll('.phase-name-input').forEach(input => {
            input.onchange = (e) => { this.currentConfig.fases[e.target.dataset.findex].nome = e.target.value; };
        });

        this.body.querySelectorAll('.status-pill').forEach(pill => {
            pill.onclick = (e) => {
                const btn = e.currentTarget;
                const { findex, status } = btn.dataset;
                this.currentConfig.fases[findex].status_do_projeto = status;
                const group = btn.closest('.status-pills');
                group.querySelectorAll('.status-pill').forEach(p => p.classList.remove('active'));
                btn.classList.add('active');
            };
        });

        document.getElementById('btn_add_phase').onclick = () => {
            const newIndex = this.currentConfig.fases.length;
            this.currentConfig.fases.push({
                id: 'fase_' + Date.now(),
                nome: 'Nova Fase',
                ordem: newIndex + 1,
                permite_acesso_direto: false,
                status_do_projeto: '',
                campos: [{ id: 'f_' + Date.now(), label: 'Título', tipo: 'string', obrigatorio: true }]
            });
            this.expandedPhaseIndex = newIndex;
            this.render();
        };

        this.body.querySelectorAll('.phase-direct-access-check').forEach(chk => {
            chk.onchange = (e) => { this.currentConfig.fases[e.target.dataset.findex].permite_acesso_direto = e.target.checked; };
        });

        this.body.querySelectorAll('.btn-remove-phase').forEach(btn => {
            btn.onclick = (e) => {
                const b = e.target.closest('button');
                const idx = b.dataset.findex;
                this.currentConfig.fases.splice(idx, 1);
                this.expandedPhaseIndex = 0;
                this.render();
            };
        });

        this.body.querySelectorAll('.btn-move-phase').forEach(btn => {
            btn.onclick = (e) => {
                const b = e.target.closest('button');
                const idx = parseInt(b.dataset.findex);
                const dir = parseInt(b.dataset.dir);
                const target = idx + dir;
                if (target >= 0 && target < this.currentConfig.fases.length) {
                    const temp = this.currentConfig.fases[idx];
                    this.currentConfig.fases[idx] = this.currentConfig.fases[target];
                    this.currentConfig.fases[target] = temp;
                    this.currentConfig.fases.forEach((f, i) => f.ordem = i + 1);
                    this.expandedPhaseIndex = target;
                    this.render();
                }
            };
        });

        this.body.querySelectorAll('.btn-add-field-sec, .btn-add-field-sec-v2').forEach(btn => {
            btn.onclick = (e) => {
                const fIndex = e.target.closest('button').dataset.findex;
                this.currentConfig.fases[fIndex].campos.push({
                    id: 'f_' + Date.now(),
                    label: 'Novo Campo',
                    tipo: 'string',
                    obrigatorio: false
                });
                this.render();
            };
        });

        this.body.querySelectorAll('.btn-remove-field-circle, .field-remove-btn').forEach(btn => {
            btn.onclick = (e) => {
                const btnEl = e.target.closest('button');
                const { findex, cindex } = btnEl.dataset;
                this.currentConfig.fases[findex].campos.splice(cindex, 1);
                this.render();
            };
        });

        this.body.querySelectorAll('.field-label-input').forEach(input => {
            input.onchange = (e) => {
                const { findex, cindex } = e.target.dataset;
                this.currentConfig.fases[findex].campos[cindex].label = e.target.value;
            };
        });

        this.body.querySelectorAll('.field-type-select').forEach(sel => {
            sel.onchange = (e) => {
                const { findex, cindex } = e.target.dataset;
                this.currentConfig.fases[findex].campos[cindex].tipo = e.target.value;
                this.render();
            };
        });

        this.body.querySelectorAll('.field-options-input').forEach(input => {
            input.onchange = (e) => {
                const { findex, cindex } = e.target.dataset;
                this.currentConfig.fases[findex].campos[cindex].opcoes = e.target.value.split(',').map(s => s.trim()).filter(s => s !== '');
            };
        });

        this.body.querySelectorAll('.field-req-check').forEach(chk => {
            chk.onchange = (e) => {
                const { findex, cindex } = e.target.dataset;
                this.currentConfig.fases[findex].campos[cindex].obrigatorio = e.target.checked;
            };
        });

        this.body.querySelectorAll('.field-mapping-select').forEach(sel => {
            sel.onchange = (e) => {
                const { findex, cindex } = e.target.dataset;
                this.currentConfig.fases[findex].campos[cindex].mapeamento_coluna = e.target.value;
            };
        });

        this.body.querySelectorAll('.field-sync-toggle').forEach(chk => {
            chk.onchange = (e) => {
                const { findex, cindex } = e.target.dataset;
                const wrap = e.target.closest('.field-sync-row').querySelector('.field-sync-select-wrap');
                const select = wrap.querySelector('.field-mapping-select');
                if (e.target.checked) {
                    wrap.style.display = 'flex';
                } else {
                    wrap.style.display = 'none';
                    select.value = '';
                    this.currentConfig.fases[findex].campos[cindex].mapeamento_coluna = '';
                }
            };
        });
    },

    async save() {
        const nome = document.getElementById('config_kanban_nome').value;
        this.currentConfig.nome = nome;
        
        // Validação obrigatória de status do projeto por fase
        const fases = this.currentConfig.fases || [];
        for (let i = 0; i < fases.length; i++) {
            const fase = fases[i];
            if (!fase.status_do_projeto) {
                toast.error(`A fase "${fase.nome || ('Fase ' + (i + 1))}" precisa ter um Status do Projeto definido.`);
                this.expandedPhaseIndex = i;
                this.render();
                return;
            }
        }
        
        try {
            await api.post("/api/kanban/config", this.currentConfig);
            toast.success("Configuração salva!");
            this.hide();
            board.refresh();
        } catch (err) {
            toast.error("Erro ao salvar: " + err.message);
        }
    },

    _fieldTypes() {
        return [
            { v: 'string',   l: 'Linha única',          i: 'fa-i-cursor'      },
            { v: 'text',     l: 'Parágrafo',            i: 'fa-align-left'    },
            { v: 'number',   l: 'Número',               i: 'fa-hashtag'       },
            { v: 'boolean',  l: 'Sim/Não',              i: 'fa-toggle-on'     },
            { v: 'datetime', l: 'Data',                 i: 'fa-calendar-days' },
            { v: 'select',   l: 'Opções (escolha 1)',   i: 'fa-caret-down'    },
            { v: 'checkbox', l: 'Múltipla escolha',     i: 'fa-square-check'  },
            { v: 'radio',    l: 'Escolha única',        i: 'fa-circle-dot'    },
            { v: 'link',     l: 'Link / URL',           i: 'fa-link'          }
        ];
    },

    _fieldLabel(type) {
        const t = this._fieldTypes().find(x => x.v === type);
        return t ? t.l : type;
    },

    _fieldIcon(type) {
        const t = this._fieldTypes().find(x => x.v === type);
        return t ? t.i : 'fa-circle';
    }
};

document.addEventListener('DOMContentLoaded', () => kanbanConfig.init());
