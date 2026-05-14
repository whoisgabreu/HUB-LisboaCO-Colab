const configEditor = {
    overlay: document.getElementById('configModalOverlay'),
    body: document.getElementById('configModalBody'),
    saveBtn: document.getElementById('btnConfigSave'),
    cancelBtn: document.getElementById('btnConfigCancel'),
    
    currentConfig: null,
    expandedPhaseIndex: 0, // Track which phase accordion is open

    init() {
        document.getElementById('btnConfig').onclick = () => this.show();
        this.cancelBtn.onclick = () => this.hide();
        this.saveBtn.onclick = () => this.save();
        this.overlay.onclick = (e) => { if (e.target === this.overlay) this.hide(); };
    },

    show() {
        this.currentConfig = JSON.parse(JSON.stringify(board.config)); // Deep copy
        this.expandedPhaseIndex = 0; // Reset to first phase
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
        this.body.innerHTML = `
            <div class="config-section-header">
                <div class="form-group">
                    <label>Nome do Kanban</label>
                    <input type="text" id="config_kanban_nome" value="${this.currentConfig.nome}" placeholder="Ex: Projeto Hub Lisboa">
                </div>
            </div>
            <div class="config-phases-title">Fases do Fluxo</div>
            <div id="phases_container"></div>
            <button id="btn_add_phase" class="btn-add-phase-main">+ Adicionar Nova Fase</button>
        `;

        const container = document.getElementById('phases_container');
        this.currentConfig.fases.sort((a,b) => a.ordem - b.ordem).forEach((fase, fIndex) => {
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
                        <button class="btn-icon-small btn-move-phase" data-findex="${fIndex}" data-dir="-1" title="Subir">↑</button>
                        <button class="btn-icon-small btn-move-phase" data-findex="${fIndex}" data-dir="1" title="Descer">↓</button>
                        <span class="accordion-arrow">${isExpanded ? '▾' : '▸'}</span>
                    </div>
                </div>
                
                <div class="phase-accordion-body" style="display: ${isExpanded ? 'block' : 'none'}">
                    <div class="phase-settings-row">
                        <div class="form-group-inline">
                            <label>Nome da Fase</label>
                            <input type="text" value="${fase.nome}" class="phase-name-input" data-findex="${fIndex}">
                        </div>
                        <label class="phase-direct-access-toggle">
                            <input type="checkbox" class="phase-direct-access-check" data-findex="${fIndex}" ${fase.permite_acesso_direto ? 'checked' : ''}>
                            ⚡ Acesso Direto
                        </label>
                        ${(() => {
                            const hasCards = board.cards.some(c => c.fase_atual === fase.nome);
                            return `<button class="btn-small btn-danger btn-remove-phase" data-findex="${fIndex}" 
                                      ${hasCards ? 'disabled style="opacity:0.3; cursor:not-allowed;" title="Não é possível remover: esta fase contém cards."' : ''}>
                                      Remover Fase
                                    </button>`;
                        })()}
                    </div>

                    <div class="fields-config-header">Campos desta Fase</div>
                    <div class="fields-list" data-findex="${fIndex}">
                        ${fase.campos.map((campo, cIndex) => `
                            <div class="field-item-card">
                                <div class="field-row-main">
                                    <div class="field-col-label">
                                        <input type="text" value="${campo.label}" placeholder="Label do Campo" class="field-label-input" data-findex="${fIndex}" data-cindex="${cIndex}">
                                    </div>
                                    <div class="field-col-type">
                                        <select class="field-type-select" data-findex="${fIndex}" data-cindex="${cIndex}">
                                            ${['string', 'text', 'number', 'boolean', 'datetime', 'select', 'checkbox', 'radio', 'link'].map(t => `<option value="${t}" ${t === campo.tipo ? 'selected' : ''}>${t}</option>`).join('')}
                                        </select>
                                    </div>
                                    <div class="field-col-req">
                                        <label class="checkbox-label">
                                            <input type="checkbox" ${campo.obrigatorio ? 'checked' : ''} class="field-req-check" data-findex="${fIndex}" data-cindex="${cIndex}"> Obrig.
                                        </label>
                                    </div>
                                    <button class="btn-remove-field-circle" data-findex="${fIndex}" data-cindex="${cIndex}" title="Remover Campo">×</button>
                                </div>
                                ${['select', 'checkbox', 'radio'].includes(campo.tipo) ? `
                                    <div class="field-options-area">
                                        <label>Opções (separadas por vírgula)</label>
                                        <input type="text" class="field-options-input" data-findex="${fIndex}" data-cindex="${cIndex}" 
                                               placeholder="Ex: Opção 1, Opção 2" value="${(campo.opcoes || []).join(', ')}">
                                    </div>
                                ` : ''}
                            </div>
                        `).join('')}
                    </div>
                    <button class="btn-add-field-sec btn-small" data-findex="${fIndex}">+ Adicionar Campo</button>
                </div>
            `;
            container.appendChild(phaseCard);
        });

        this.attachEvents();
    },

    attachEvents() {
        // Accordion Toggle
        this.body.querySelectorAll('.phase-accordion-header').forEach(header => {
            header.onclick = (e) => {
                if (e.target.closest('button')) return; // Don't toggle if clicking move buttons
                const fIndex = parseInt(header.dataset.findex);
                this.togglePhase(fIndex);
            };
        });

        // Phase Name
        this.body.querySelectorAll('.phase-name-input').forEach(input => {
            input.onchange = (e) => {
                this.currentConfig.fases[e.target.dataset.findex].nome = e.target.value;
            };
        });

        // Add Phase
        document.getElementById('btn_add_phase').onclick = () => {
            const newId = 'fase_' + Date.now();
            const newIndex = this.currentConfig.fases.length;
            this.currentConfig.fases.push({
                id: newId,
                nome: 'Nova Fase',
                ordem: newIndex + 1,
                permite_acesso_direto: false,
                campos: [{ id: 'titulo', label: 'Título', tipo: 'string', obrigatorio: true }]
            });
            this.expandedPhaseIndex = newIndex; // Open the new phase
            this.render();
        };

        // Direct Access toggle
        this.body.querySelectorAll('.phase-direct-access-check').forEach(chk => {
            chk.onchange = (e) => {
                this.currentConfig.fases[e.target.dataset.findex].permite_acesso_direto = e.target.checked;
            };
        });

        // Remove Phase
        this.body.querySelectorAll('.btn-remove-phase').forEach(btn => {
            btn.onclick = (e) => {
                e.stopPropagation();
                this.currentConfig.fases.splice(e.target.dataset.findex, 1);
                this.expandedPhaseIndex = 0;
                this.render();
            };
        });

        // Move Phase
        this.body.querySelectorAll('.btn-move-phase').forEach(btn => {
            btn.onclick = (e) => {
                e.stopPropagation();
                const idx = parseInt(e.target.dataset.findex);
                const dir = parseInt(e.target.dataset.dir);
                const target = idx + dir;
                if (target >= 0 && target < this.currentConfig.fases.length) {
                    const temp = this.currentConfig.fases[idx];
                    this.currentConfig.fases[idx] = this.currentConfig.fases[target];
                    this.currentConfig.fases[target] = temp;
                    // Reset order
                    this.currentConfig.fases.forEach((f, i) => f.ordem = i + 1);
                    this.expandedPhaseIndex = target; // Follow the phase
                    this.render();
                }
            };
        });

        // Add Field
        this.body.querySelectorAll('.btn-add-field-sec').forEach(btn => {
            btn.onclick = (e) => {
                const fIndex = e.target.dataset.findex;
                const fieldId = 'field_' + Date.now();
                this.currentConfig.fases[fIndex].campos.push({
                    id: fieldId,
                    label: 'Novo Campo',
                    tipo: 'string',
                    obrigatorio: false
                });
                this.render();
            };
        });

        // Remove Field
        this.body.querySelectorAll('.btn-remove-field-circle').forEach(btn => {
            btn.onclick = (e) => {
                const { findex, cindex } = e.target.dataset;
                this.currentConfig.fases[findex].campos.splice(cindex, 1);
                this.render();
            };
        });

        // Field Label
        this.body.querySelectorAll('.field-label-input').forEach(input => {
            input.onchange = (e) => {
                const { findex, cindex } = e.target.dataset;
                this.currentConfig.fases[findex].campos[cindex].label = e.target.value;
            };
        });

        // Field Type
        this.body.querySelectorAll('.field-type-select').forEach(sel => {
            sel.onchange = (e) => {
                const { findex, cindex } = e.target.dataset;
                this.currentConfig.fases[findex].campos[cindex].tipo = e.target.value;
                if (['select', 'checkbox', 'radio'].includes(e.target.value)) {
                    if (!this.currentConfig.fases[findex].campos[cindex].opcoes) {
                        this.currentConfig.fases[findex].campos[cindex].opcoes = ['Opção 1', 'Opção 2'];
                    }
                }
                this.render();
            };
        });

        // Field Options
        this.body.querySelectorAll('.field-options-input').forEach(input => {
            input.onchange = (e) => {
                const { findex, cindex } = e.target.dataset;
                const options = e.target.value.split(',').map(s => s.trim()).filter(s => s !== '');
                this.currentConfig.fases[findex].campos[cindex].opcoes = options;
            };
        });

        // Field Required
        this.body.querySelectorAll('.field-req-check').forEach(chk => {
            chk.onchange = (e) => {
                const { findex, cindex } = e.target.dataset;
                this.currentConfig.fases[findex].campos[cindex].obrigatorio = e.target.checked;
            };
        });
    },

    async save() {
        const nome = document.getElementById('config_kanban_nome').value;
        this.currentConfig.nome = nome;
        
        try {
            await api.put(`/kanban/${this.currentConfig.kanban_id}`, {
                nome: this.currentConfig.nome,
                fases: this.currentConfig.fases
            });
            this.hide();
            location.reload();
        } catch (err) {
            toast.error("Erro ao salvar: " + err.message);
        }
    }
};
