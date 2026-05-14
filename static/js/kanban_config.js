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
        this.body.innerHTML = `
            <div class="config-section-header">
                <div class="form-group">
                    <label>Nome do Board</label>
                    <input type="text" id="config_kanban_nome" class="modern-input" value="${this.currentConfig.nome}" placeholder="Ex: Fluxo de Projetos">
                </div>
            </div>
            <div class="config-phases-title">Fases do Fluxo</div>
            <div id="phases_container"></div>
            <button id="btn_add_phase" class="btn-secondary btn-add-phase-main" style="width:100%; margin-top:20px; border: 1px dashed var(--border-color);">
                <i class="fas fa-plus"></i> Adicionar Nova Fase
            </button>
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
                        <div class="form-group-inline" style="flex:1;">
                            <label>Nome da Fase</label>
                            <input type="text" value="${fase.nome}" class="modern-input phase-name-input" data-findex="${fIndex}">
                        </div>
                        <div style="display:flex; align-items:center; gap:20px; padding-top:20px;">
                            <label class="checkbox-label" style="cursor:pointer;">
                                <input type="checkbox" class="phase-direct-access-check" data-findex="${fIndex}" ${fase.permite_acesso_direto ? 'checked' : ''}>
                                ⚡ Acesso Direto
                            </label>
                            <button class="btn-danger btn-remove-phase" data-findex="${fIndex}" style="padding: 8px 12px; border-radius: 8px; font-size: 0.8rem;">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>

                    <div class="fields-config-header">Campos desta Fase</div>
                    <div class="fields-list" data-findex="${fIndex}">
                        ${fase.campos.map((campo, cIndex) => `
                            <div class="field-item-card">
                                <div class="field-row-main" style="display:grid; grid-template-columns: 2fr 1fr 100px 40px; gap:10px;">
                                    <input type="text" value="${campo.label}" placeholder="Label" class="modern-input field-label-input" data-findex="${fIndex}" data-cindex="${cIndex}">
                                    <select class="modern-select field-type-select" data-findex="${fIndex}" data-cindex="${cIndex}">
                                        ${['string', 'text', 'number', 'boolean', 'datetime', 'select', 'checkbox', 'radio', 'link'].map(t => `<option value="${t}" ${t === campo.tipo ? 'selected' : ''}>${t}</option>`).join('')}
                                    </select>
                                    <label class="checkbox-label" style="font-size:0.75rem;">
                                        <input type="checkbox" ${campo.obrigatorio ? 'checked' : ''} class="field-req-check" data-findex="${fIndex}" data-cindex="${cIndex}"> Obrig.
                                    </label>
                                    <button class="btn-remove-field-circle" data-findex="${fIndex}" data-cindex="${cIndex}" style="color:var(--kanban-accent); border:none; background:transparent; font-size:1.2rem;">×</button>
                                </div>
                                ${['select', 'checkbox', 'radio'].includes(campo.tipo) ? `
                                    <div class="field-options-area" style="margin-top:10px;">
                                        <label style="font-size:0.7rem; color:var(--text-muted);">Opções (vírgula)</label>
                                        <input type="text" class="modern-input field-options-input" data-findex="${fIndex}" data-cindex="${cIndex}" 
                                               placeholder="Op1, Op2" value="${(campo.opcoes || []).join(', ')}">
                                    </div>
                                ` : ''}
                            </div>
                        `).join('')}
                    </div>
                    <button class="btn-secondary btn-add-field-sec" data-findex="${fIndex}" style="width:100%; margin-top:10px; font-size:0.8rem;">
                        <i class="fas fa-plus"></i> Adicionar Campo
                    </button>
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

        document.getElementById('btn_add_phase').onclick = () => {
            const newIndex = this.currentConfig.fases.length;
            this.currentConfig.fases.push({
                id: 'fase_' + Date.now(),
                nome: 'Nova Fase',
                ordem: newIndex + 1,
                permite_acesso_direto: false,
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

        this.body.querySelectorAll('.btn-add-field-sec').forEach(btn => {
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

        this.body.querySelectorAll('.btn-remove-field-circle').forEach(btn => {
            btn.onclick = (e) => {
                const { findex, cindex } = e.target.dataset;
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
    },

    async save() {
        const nome = document.getElementById('config_kanban_nome').value;
        this.currentConfig.nome = nome;
        
        try {
            await api.post("/api/kanban/config", this.currentConfig);
            toast.success("Configuração salva!");
            this.hide();
            board.refresh();
        } catch (err) {
            toast.error("Erro ao salvar: " + err.message);
        }
    }
};

document.addEventListener('DOMContentLoaded', () => kanbanConfig.init());
