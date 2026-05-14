// ── Phase transition validator ──────────
function canTransition(currentFase, targetFase, card = null) {
    if (!currentFase || !targetFase) return { allowed: true, reason: '' };
    if (currentFase.id === targetFase.id) return { allowed: false, reason: 'same' };
    if (targetFase.permite_acesso_direto) return { allowed: true, reason: 'direct' };
    if (targetFase.ordem === currentFase.ordem + 1) return { allowed: true, reason: 'next' };
    
    // Retorno se o card já tiver histórico dessa fase
    if (card && card.historico && card.historico.some(h => (h.fase_entrada === targetFase.nome || h.fase === targetFase.nome))) {
        return { allowed: true, reason: 'return' };
    }

    return { allowed: false, reason: 'blocked' };
}

const modal = {
    overlay: document.getElementById('modalOverlay'),
    content: document.getElementById('modalBody'),
    title: document.getElementById('modalTitle'),
    saveBtn: document.getElementById('btnSave'),
    cancelBtn: document.getElementById('btnCancel'),
    footer: document.getElementById('modalFooter'),
    closeBtn: document.getElementById('btnCloseModal'),
    
    currentCard: null,
    currentPhaseConfig: null,

    init() {
        if (this.cancelBtn) this.cancelBtn.onclick = () => this.hide();
        if (this.closeBtn) this.closeBtn.onclick = () => this.hide();
        if (this.overlay) {
            this.overlay.onclick = (e) => { if (e.target === this.overlay) this.hide(); };
        }
    },

    showView(card, config) {
        this.currentCard = card;
        this.title.innerText = `Projeto: ${card.titulo}`;
        this.footer.style.display = 'flex';
        this.saveBtn.style.display = 'block';
        
        const currentPhase = config.fases.find(f => f.nome === card.fase_atual) || config.fases[0];
        this.currentPhaseConfig = currentPhase;

        this.content.innerHTML = `
            <div class="modal-grid">
                <div class="modal-col col-history" id="modalColHistory"></div>
                <div class="modal-col col-form" id="modalColForm"></div>
                <div class="modal-col col-transitions" id="modalColTransitions"></div>
            </div>
        `;

        const historyCol = document.getElementById('modalColHistory');
        const formCol = document.getElementById('modalColForm');
        const transCol = document.getElementById('modalColTransitions');

        // 1. History
        historyCol.innerHTML = '<div class="col-title"><i class="fas fa-history"></i> Histórico</div>';
        if (!card.historico || card.historico.length === 0) {
            historyCol.innerHTML += '<p style="color:var(--text-muted); font-size:0.8rem;">Sem histórico registrado.</p>';
        } else {
            card.historico.forEach(h => {
                const item = document.createElement('div');
                item.className = 'history-item';
                item.innerHTML = `
                    <div class="history-phase-name">${h.fase_entrada || h.fase || 'Movimentação'}</div>
                    <div style="font-size:0.7rem; color:var(--text-muted); margin-bottom:8px;">
                        ${new Date(h.timestamp).toLocaleString()} - ${h.usuario || 'Sistema'}
                    </div>
                `;
                historyCol.appendChild(item);
            });
        }

        // 2. Form
        formCol.innerHTML = `<div class="col-title"><i class="fas fa-edit"></i> Dados do Projeto</div>`;
        const formContainer = document.createElement('div');
        formContainer.className = 'modal-form-standard';
        formCol.appendChild(formContainer);

        // NOME DO PROJETO (FIXO)
        const nameGroup = document.createElement('div');
        nameGroup.className = 'form-group full-width';
        nameGroup.innerHTML = `<label>Nome do Projeto / Cliente *</label>`;
        const nameInput = document.createElement('input');
        nameInput.id = 'field_projeto_nome';
        nameInput.className = 'modern-input';
        nameInput.value = card.titulo || '';
        nameGroup.appendChild(nameInput);
        formContainer.appendChild(nameGroup);

        // Campos da fase
        currentPhase.campos.forEach(campo => {
            const group = document.createElement('div');
            group.className = 'form-group';
            if (campo.tipo === 'text') group.classList.add('full-width');
            
            group.innerHTML = `<label>${campo.label}${campo.obrigatorio ? ' *' : ''}</label>`;
            const val = card.dados[campo.id];
            group.appendChild(this.createFieldInput(campo, val));
            formContainer.appendChild(group);
        });

        // 3. Transitions
        transCol.innerHTML = '<div class="col-title"><i class="fas fa-exchange-alt"></i> Mover para...</div>';
        config.fases.forEach(fase => {
            if (fase.nome === card.fase_atual) return;
            const { allowed, reason } = canTransition(currentPhase, fase, card);

            const btn = document.createElement('button');
            btn.className = 'transition-btn';
            if (!allowed) btn.classList.add('blocked');
            
            let statusIcon = allowed ? '<i class="fas fa-arrow-right"></i>' : '<i class="fas fa-lock"></i>';
            if (reason === 'direct') statusIcon = '<i class="fas fa-bolt" style="color:#fbbf24;"></i>';
            if (reason === 'return') statusIcon = '<i class="fas fa-undo"></i>';

            btn.innerHTML = `<span>${fase.nome}</span><span>${statusIcon}</span>`;
            if (allowed) {
                btn.onclick = () => this.handleTransition(card, fase);
            }
            transCol.appendChild(btn);
        });

        this.saveBtn.onclick = () => this.handleSave(card.card_id);
        this.overlay.style.display = 'flex';
    },

    createFieldInput(campo, val) {
        if (campo.tipo === 'select') {
            const input = document.createElement('select');
            input.id = `field_${campo.id}`;
            input.className = 'modern-select';
            const emptyOpt = document.createElement('option');
            emptyOpt.value = ''; emptyOpt.text = '-- Selecione --';
            input.appendChild(emptyOpt);
            (campo.opcoes || []).forEach(opt => {
                const o = document.createElement('option');
                o.value = opt; o.text = opt;
                if (opt === val) o.selected = true;
                input.appendChild(o);
            });
            return input;
        } 
        
        if (campo.tipo === 'radio') {
            const container = document.createElement('div');
            container.className = 'selection-chips-group';
            container.id = `field_${campo.id}`;
            (campo.opcoes || []).forEach(opt => {
                const label = document.createElement('label');
                label.className = 'chip-item';
                const input = document.createElement('input');
                input.type = 'radio';
                input.name = `radio_${campo.id}`;
                input.value = opt;
                input.style.display = 'none';
                if (opt === val) input.checked = true;
                const chipContent = document.createElement('span');
                chipContent.className = 'chip-content';
                chipContent.innerText = opt;
                label.appendChild(input); label.appendChild(chipContent);
                container.appendChild(label);
            });
            return container;
        }

        if (campo.tipo === 'checkbox') {
            const container = document.createElement('div');
            container.className = 'selection-chips-group';
            container.id = `field_${campo.id}`;
            const selectedVals = Array.isArray(val) ? val : (val ? [val] : []);
            (campo.opcoes || []).forEach(opt => {
                const label = document.createElement('label');
                label.className = 'chip-item';
                const input = document.createElement('input');
                input.type = 'checkbox';
                input.value = opt;
                input.style.display = 'none';
                if (selectedVals.includes(opt)) input.checked = true;
                const chipContent = document.createElement('span');
                chipContent.className = 'chip-content';
                chipContent.innerText = opt;
                label.appendChild(input); label.appendChild(chipContent);
                container.appendChild(label);
            });
            return container;
        }

        if (campo.tipo === 'text') {
            const input = document.createElement('textarea');
            input.id = `field_${campo.id}`;
            input.className = 'modern-input';
            input.value = val || '';
            input.rows = 4;
            return input;
        }

        if (campo.tipo === 'boolean') {
            const container = document.createElement('label');
            container.className = 'toggle-switch';
            container.id = `field_${campo.id}`;
            const input = document.createElement('input');
            input.type = 'checkbox';
            input.checked = !!val;
            const slider = document.createElement('span');
            slider.className = 'toggle-slider';
            const text = document.createElement('span');
            text.className = 'toggle-text';
            text.innerText = val ? 'Sim' : 'Não';
            input.onchange = (e) => { text.innerText = e.target.checked ? 'Sim' : 'Não'; };
            container.appendChild(input); container.appendChild(slider); container.appendChild(text);
            return container;
        }

        if (campo.tipo === 'link') {
            const container = document.createElement('div');
            container.style.display = 'flex'; container.style.gap = '8px';
            const input = document.createElement('input');
            input.id = `field_${campo.id}`;
            input.className = 'modern-input';
            input.type = 'url';
            input.value = val || '';
            input.style.flex = '1';
            const btn = document.createElement('button');
            btn.className = 'btn-secondary';
            btn.innerHTML = '<i class="fas fa-external-link-alt"></i>';
            btn.onclick = () => {
                const url = input.value.trim();
                if (url) window.open(url.startsWith('http') ? url : 'https://'+url, '_blank');
            };
            container.appendChild(input); container.appendChild(btn);
            return container;
        }

        const input = document.createElement('input');
        input.id = `field_${campo.id}`;
        input.className = 'modern-input';
        input.type = (campo.tipo === 'number') ? 'number' : 
                     (campo.tipo === 'datetime') ? 'datetime-local' : 'text';
        input.value = val || '';
        return input;
    },

    async handleSave(cardId) {
        const dados = {};
        const nome = document.getElementById('field_projeto_nome').value;
        let valid = true;

        if (!nome) {
            document.getElementById('field_projeto_nome').style.borderColor = 'red';
            valid = false;
        }

        this.currentPhaseConfig.campos.forEach(campo => {
            const el = document.getElementById(`field_${campo.id}`);
            let val;
            if (campo.tipo === 'radio') {
                val = (el.querySelector('input:checked') || {}).value || '';
            } else if (campo.tipo === 'checkbox') {
                val = Array.from(el.querySelectorAll('input:checked')).map(i => i.value);
            } else if (campo.tipo === 'boolean') {
                val = el.querySelector('input').checked;
            } else {
                val = el.value;
            }
            
            if (campo.obrigatorio && (!val || (Array.isArray(val) && val.length === 0)) && val !== 0 && val !== false) {
                el.style.borderColor = 'red';
                valid = false;
            } else {
                el.style.borderColor = '';
            }
            dados[campo.id] = val;
        });
        
        if (!valid) return toast.error("Preencha todos os campos obrigatórios.");

        try {
            await api.post(`/api/kanban/cards/${cardId}/update`, { nome, dados });
            toast.success("Dados salvos!");
            this.hide();
            board.refresh();
        } catch (err) {
            toast.error(err.message);
        }
    },

    async handleTransition(card, targetFase) {
        // Coleta dados atuais antes de mover
        const dados_fase = {};
        this.currentPhaseConfig.campos.forEach(campo => {
            const el = document.getElementById(`field_${campo.id}`);
            if (campo.tipo === 'radio') dados_fase[campo.id] = (el.querySelector('input:checked') || {}).value || '';
            else if (campo.tipo === 'checkbox') dados_fase[campo.id] = Array.from(el.querySelectorAll('input:checked')).map(i => i.value);
            else if (campo.tipo === 'boolean') dados_fase[campo.id] = el.querySelector('input').checked;
            else dados_fase[campo.id] = el.value;
        });

        try {
            await api.moveCard(card.card_id, targetFase.id, dados_fase);
            toast.success(`Movido para ${targetFase.nome}`);
            this.hide();
            board.refresh();
            
            setTimeout(async () => {
                const updated = await api.getCard(card.card_id);
                this.showView(updated, board.config);
            }, 500);
        } catch (err) {
            toast.error(err.message);
        }
    },

    show(title, phase, cardData, onSave) {
        this.title.innerText = title;
        this.currentPhaseConfig = phase;
        this.footer.style.display = 'flex';
        this.saveBtn.style.display = 'block';

        this.content.innerHTML = `
            <div style="padding: 24px;">
                <div class="col-title"><i class="fas fa-plus"></i> Cadastro de Novo Projeto</div>
                <div id="modalNewCardForm" class="modal-form-standard"></div>
            </div>
        `;

        const formContainer = document.getElementById('modalNewCardForm');

        // NOME DO PROJETO (OBRIGATÓRIO NO CADASTRO)
        const nameGroup = document.createElement('div');
        nameGroup.className = 'form-group full-width';
        nameGroup.innerHTML = `<label>Nome do Projeto / Cliente *</label>`;
        const nameInput = document.createElement('input');
        nameInput.id = 'field_projeto_nome_new';
        nameInput.className = 'modern-input';
        nameInput.placeholder = "Digite o nome da empresa ou projeto...";
        nameGroup.appendChild(nameInput);
        formContainer.appendChild(nameGroup);

        phase.campos.forEach(campo => {
            const group = document.createElement('div');
            group.className = 'form-group';
            if (campo.tipo === 'text') group.classList.add('full-width');
            group.innerHTML = `<label>${campo.label}${campo.obrigatorio ? ' *' : ''}</label>`;
            group.appendChild(this.createFieldInput(campo, cardData[campo.id]));
            formContainer.appendChild(group);
        });

        this.saveBtn.onclick = () => {
            const dados = {};
            const nome = document.getElementById('field_projeto_nome_new').value;
            let valid = true;

            if (!nome) {
                document.getElementById('field_projeto_nome_new').style.borderColor = 'red';
                valid = false;
            }

            phase.campos.forEach(c => {
                const el = document.getElementById(`field_${c.id}`);
                let val;
                if (c.tipo === 'radio') val = (el.querySelector('input:checked') || {}).value || '';
                else if (c.tipo === 'checkbox') val = Array.from(el.querySelectorAll('input:checked')).map(i => i.value);
                else if (c.tipo === 'boolean') val = el.querySelector('input').checked;
                else val = el.value;

                if (c.obrigatorio && !val && val !== 0 && val !== false) {
                    valid = false; el.style.borderColor = 'red';
                }
                dados[c.id] = val;
            });

            if (valid) {
                onSave({ nome, dados });
                this.hide();
            } else {
                toast.error("Preencha o nome do projeto e campos obrigatórios.");
            }
        };

        this.overlay.style.display = 'flex';
    },

    hide() {
        this.overlay.style.display = 'none';
    }
};
