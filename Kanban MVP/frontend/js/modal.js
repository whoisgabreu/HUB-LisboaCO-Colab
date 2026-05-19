// ── Phase transition validator (mirrors backend deterministic rule) ──────────
function canTransition(currentFase, targetFase, card = null) {
    if (!currentFase || !targetFase) return { allowed: true, reason: '' };
    if (currentFase.id === targetFase.id) return { allowed: false, reason: 'same' };
    if (targetFase.permite_acesso_direto) return { allowed: true, reason: 'direct' };
    if (targetFase.ordem === currentFase.ordem + 1) return { allowed: true, reason: 'next' };
    
    // Novo: Permite retorno se o card já tiver snapshot dessa fase
    if (card && card.fases && card.fases.some(s => s.fase_id === targetFase.nome)) {
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
    onSaveCallback: null,

    init() {
        this.cancelBtn.onclick = () => this.hide();
        this.closeBtn.onclick = () => this.hide();
        this.overlay.onclick = (e) => { if (e.target === this.overlay) this.hide(); };
    },

    showView(card, config) {
        this.currentCard = card;
        this.title.innerText = `Detalhes do Card: ${card.card_id.slice(0,8)}`;
        this.footer.style.display = 'flex';
        this.saveBtn.style.display = 'block';
        
        // Find current phase config
        const currentPhase = config.fases.find(f => f.nome === card.fase_atual);
        this.currentPhaseConfig = currentPhase;

        // Create Grid Layout
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

        // 1. Render History (Previous Phases)
        historyCol.innerHTML = '<div class="col-title">📄 Histórico de Fases</div>';
        const pastSnapshots = card.fases.filter(f => f.fase_id !== card.fase_atual);
        
        if (pastSnapshots.length === 0) {
            historyCol.innerHTML += '<div style="color: var(--text-muted); font-size: 0.9rem; font-style: italic;">Nenhuma fase anterior.</div>';
        }

        pastSnapshots.forEach(snapshot => {
            const item = document.createElement('div');
            item.className = 'history-item';
            
            let fieldsHtml = '';
            const labels = snapshot.dados._labels || {};
            
            Object.entries(snapshot.dados).forEach(([key, val]) => {
                if (key === '_labels') return;
                const label = labels[key] || key;
                let displayVal = val;
                if (Array.isArray(val)) displayVal = val.join(', ');
                else if (val === true) displayVal = 'Sim';
                else if (val === false) displayVal = 'Não';
                else if (!val) displayVal = '-';
                else if (typeof val === 'string' && /^https?:\/\//i.test(val)) {
                    displayVal = `<a href="${val}" target="_blank" style="color: var(--accent-color); text-decoration: underline;">Abrir Link 🔗</a>`;
                }

                fieldsHtml += `
                    <div class="history-field">
                        <span class="history-label">${label}</span>
                        <span>${displayVal}</span>
                    </div>
                `;
            });

            item.innerHTML = `
                <div class="history-phase-name">${snapshot.fase_id}</div>
                ${fieldsHtml || '<div style="color: var(--text-muted); font-size: 0.8rem;">Sem dados.</div>'}
            `;
            historyCol.appendChild(item);
        });

        // 2. Render Current Phase Form
        formCol.innerHTML = `<div class="col-title">✏️ Fase Atual: ${card.fase_atual}</div>`;
        const currentSnapshot = card.fases.find(f => f.fase_id === card.fase_atual) || { dados: {} };
        
        const useGrid = currentPhase.campos.length > 4;
        const formContainer = document.createElement('div');
        formContainer.className = useGrid ? 'modal-form-grid' : 'modal-form-standard';
        formCol.appendChild(formContainer);

        currentPhase.campos.forEach(campo => {
            const group = document.createElement('div');
            group.className = 'form-group';
            if (campo.tipo === 'text') group.classList.add('full-width');
            
            const label = document.createElement('label');
            label.innerText = campo.label + (campo.obrigatorio ? ' *' : '');
            group.appendChild(label);
            
            const val = currentSnapshot.dados[campo.id];
            group.appendChild(this.createFieldInput(campo, val));
            
            formContainer.appendChild(group);
        });

        // 3. Render Transitions
        transCol.innerHTML = '<div class="col-title">🚀 Mover para fase</div>';

        const sortedFases = [...config.fases].sort((a, b) => a.ordem - b.ordem);
        const otherPhases = sortedFases.filter(f => f.nome !== card.fase_atual);

        otherPhases.forEach(fase => {
            const { allowed, reason } = canTransition(currentPhase, fase, card);

            const btn = document.createElement('button');
            btn.className = 'transition-btn';
            if (!allowed)           btn.classList.add('blocked');
            if (reason === 'direct') btn.classList.add('direct-access');
            if (reason === 'return') btn.classList.add('return-access');

            const rightSlot = !allowed
                ? '<span class="badge-locked">🔒</span>'
                : (reason === 'direct'
                    ? '<span class="badge-direct">⚡ acesso direto</span>'
                    : (reason === 'return'
                        ? '<span class="badge-return">↩️ retorno</span>'
                        : '<span class="arrow">→</span>'));

            btn.innerHTML = `<span>${fase.nome}</span>${rightSlot}`;

            if (allowed) {
                btn.onclick = () => this.handleTransition(card, fase);
            }
            transCol.appendChild(btn);
        });

        // Actions
        const dangerZone = document.createElement('div');
        dangerZone.style.marginTop = '40px';
        dangerZone.innerHTML = '<div class="col-title" style="color: #ef4444;">⚠️ Zona de Perigo</div>';
        
        const delBtn = document.createElement('button');
        delBtn.innerText = 'Excluir este card';
        delBtn.className = 'btn-danger';
        delBtn.style.width = '100%';
        delBtn.onclick = async () => {
            if (confirm("Tem certeza que deseja excluir este card permanentemente?")) {
                await api.deleteCard(card.card_id);
                this.hide();
                board.refresh();
            }
        };
        dangerZone.appendChild(delBtn);
        transCol.appendChild(dangerZone);

        this.saveBtn.onclick = () => this.handleSave(card.card_id);
        this.overlay.style.display = 'flex';
    },

    createFieldInput(campo, val) {
        if (campo.tipo === 'select') {
            const input = document.createElement('select');
            input.id = `field_${campo.id}`;
            input.className = 'modern-select';
            const emptyOpt = document.createElement('option');
            emptyOpt.value = '';
            emptyOpt.text = '-- Selecione --';
            input.appendChild(emptyOpt);
            (campo.opcoes || []).forEach(opt => {
                const o = document.createElement('option');
                o.value = opt;
                o.text = opt;
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
                input.style.display = 'none'; // Hide real radio
                if (opt === val) input.checked = true;
                
                const chipContent = document.createElement('span');
                chipContent.className = 'chip-content';
                chipContent.innerText = opt;
                
                label.appendChild(input);
                label.appendChild(chipContent);
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
                input.style.display = 'none'; // Hide real checkbox
                if (selectedVals.includes(opt)) input.checked = true;
                
                const chipContent = document.createElement('span');
                chipContent.className = 'chip-content';
                chipContent.innerText = opt;
                
                label.appendChild(input);
                label.appendChild(chipContent);
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
            input.placeholder = `Preencha o campo ${campo.label}...`;
            return input;
        }

        if (campo.tipo === 'boolean') {
            const container = document.createElement('div');
            container.style.marginTop = '4px';
            
            const label = document.createElement('label');
            label.className = 'toggle-switch';
            const input = document.createElement('input');
            input.id = `field_${campo.id}`;
            input.type = 'checkbox';
            input.checked = !!val;
            
            const slider = document.createElement('span');
            slider.className = 'toggle-slider';
            
            const text = document.createElement('span');
            text.className = 'toggle-text';
            text.innerText = val ? 'Ativo' : 'Inativo';
            
            label.appendChild(input);
            label.appendChild(slider);
            label.appendChild(text);
            
            input.onchange = (e) => {
                text.innerText = e.target.checked ? 'Ativo' : 'Inativo';
            };
            container.appendChild(label);
            return container;
        }

        if (campo.tipo === 'link') {
            const container = document.createElement('div');
            container.style.display = 'flex';
            container.style.gap = '8px';
            
            const input = document.createElement('input');
            input.id = `field_${campo.id}`;
            input.className = 'modern-input';
            input.type = 'url';
            input.value = val || '';
            input.placeholder = `https://...`;
            input.style.flex = '1';
            
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn-icon';
            btn.innerHTML = '🔗';
            btn.title = 'Abrir Link';
            btn.style.padding = '12px';
            btn.onclick = () => {
                const url = input.value.trim();
                if (url) {
                    let finalUrl = url;
                    if (!/^https?:\/\//i.test(finalUrl)) {
                        finalUrl = 'https://' + finalUrl;
                    }
                    window.open(finalUrl, '_blank');
                }
            };
            
            container.appendChild(input);
            container.appendChild(btn);
            return container;
        }

        const input = document.createElement('input');
        input.id = `field_${campo.id}`;
        input.className = 'modern-input';
        input.type = (campo.tipo === 'number') ? 'number' : 
                     (campo.tipo === 'datetime') ? 'datetime-local' : 'text';
        input.value = val || '';
        input.placeholder = `Digite o ${campo.label.toLowerCase()}...`;
        return input;
    },

    async handleSave(cardId) {
        const data = {};
        let valid = true;

        this.currentPhaseConfig.campos.forEach(campo => {
            const el = document.getElementById(`field_${campo.id}`);
            let val;

            if (campo.tipo === 'radio') {
                const checked = el.querySelector('input:checked');
                val = checked ? checked.value : '';
            } else if (campo.tipo === 'checkbox') {
                const checked = Array.from(el.querySelectorAll('input:checked')).map(i => i.value);
                val = checked;
            } else if (campo.tipo === 'boolean') {
                const input = el.tagName === 'INPUT' ? el : el.querySelector('input');
                val = input.checked;
            } else {
                val = el.value;
            }
            
            if (campo.obrigatorio && (!val || (Array.isArray(val) && val.length === 0)) && val !== 0 && val !== false) {
                if (el.classList.contains('options-group')) el.style.border = '1px solid red';
                else el.style.borderColor = 'red';
                valid = false;
            } else {
                if (el.classList.contains('options-group')) el.style.border = 'none';
                else el.style.borderColor = '';
            }
            
            data[campo.id] = val;
        });

        if (valid) {
            await api.updateCard(cardId, data);
            this.hide();
            board.refresh();
        }
    },

    async handleTransition(card, targetFase) {
        // Collect current data before moving
        const data = {};
        this.currentPhaseConfig.campos.forEach(campo => {
            const el = document.getElementById(`field_${campo.id}`);
            if (campo.tipo === 'radio') {
                const checked = el.querySelector('input:checked');
                data[campo.id] = checked ? checked.value : '';
            } else if (campo.tipo === 'checkbox') {
                data[campo.id] = Array.from(el.querySelectorAll('input:checked')).map(i => i.value);
            } else if (campo.tipo === 'boolean') {
                const input = el.tagName === 'INPUT' ? el : el.querySelector('input');
                data[campo.id] = input.checked;
            } else {
                data[campo.id] = el.value;
            }
        });

        // Busca se já existe um snapshot anterior desta fase
        const previousSnapshot = card.fases.find(f => f.fase_id === targetFase.nome);

        try {
            if (previousSnapshot) {
                await api.moveCard(card.card_id, targetFase.id, previousSnapshot.dados);
            } else {
                await api.moveCard(card.card_id, targetFase.id, {});
            }
            this.hide();
            board.refresh();
            // Re-open with new phase
            setTimeout(async () => {
                const updatedCard = await api.getCard(card.card_id);
                this.showView(updatedCard, board.config);
            }, 500);
        } catch (err) {
            if (err instanceof ApiError && err.status === 422) {
                toast.error(`🔒 Transição bloqueada: ${err.detail}`);
            } else {
                toast.error(`Erro ao mover card: ${err.message}`);
            }
        }
    },

    hide() {
        this.overlay.style.display = 'none';
    },

    // Legacy show method for compatibility if needed, but we'll use showView now
    show(title, phase, cardData, onSave) {
        // Create a fake card object to reuse showView or implement minimal logic
        // But since we refactored everything to showView, we might not need this.
        // For new cards, we still need a simplified form.
        this.title.innerText = title;
        this.currentPhaseConfig = phase;
        this.saveBtn.style.display = 'block';
        this.footer.style.display = 'flex';
        this.content.innerHTML = `<div id="modalColForm" class="modal-col" style="width:100%"></div>`;
        const formCol = document.getElementById('modalColForm');
        
        // Use grid if many fields
        const useGrid = phase.campos.length > 4;
        const formContainer = document.createElement('div');
        formContainer.className = useGrid ? 'modal-form-grid' : 'modal-form-standard';
        formCol.appendChild(formContainer);

        phase.campos.forEach(campo => {
            const group = document.createElement('div');
            group.className = 'form-group';
            if (campo.tipo === 'text') group.classList.add('full-width');
            
            const label = document.createElement('label');
            label.innerText = campo.label + (campo.obrigatorio ? ' *' : '');
            group.appendChild(label);
            group.appendChild(this.createFieldInput(campo, cardData[campo.id]));
            formContainer.appendChild(group);
        });

        this.saveBtn.onclick = () => {
            const data = {};
            let valid = true;
            phase.campos.forEach(campo => {
                const el = document.getElementById(`field_${campo.id}`);
                let val;
                if (campo.tipo === 'radio') val = (el.querySelector('input:checked') || {}).value || '';
                else if (campo.tipo === 'checkbox') val = Array.from(el.querySelectorAll('input:checked')).map(i => i.value);
                else if (campo.tipo === 'boolean') val = (el.tagName === 'INPUT' ? el : el.querySelector('input')).checked;
                else val = el.value;

                if (campo.obrigatorio && !val && val !== 0 && val !== false) { valid = false; el.style.borderColor = 'red'; }
                data[campo.id] = val;
            });
            if (valid) { onSave(data); this.hide(); }
        };
        this.overlay.style.display = 'flex';
    }
};
