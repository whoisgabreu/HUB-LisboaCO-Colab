// ── Phase transition validator ──────────
function canTransition(currentFase, targetFase, card = null) {
    if (!currentFase || !targetFase) return { allowed: true, reason: '' };
    if (currentFase.id === targetFase.id) return { allowed: false, reason: 'same' };
    if (targetFase.permite_acesso_direto) return { allowed: true, reason: 'direct' };
    if (targetFase.ordem === currentFase.ordem + 1) return { allowed: true, reason: 'next' };
    
    // Retorno se o card já tiver histórico dessa fase
    if (card && card.historico && card.historico.some(h => 
        h.fase_entrada === targetFase.nome || 
        h.fase_anterior === targetFase.nome || 
        h.fase_nova === targetFase.nome
    )) {
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
        this.footer.style.display = 'flex';
        this.saveBtn.style.display = 'block';

        const currentPhase = config.fases.find(f => f.nome === card.fase_atual) || config.fases[0];
        this.currentPhaseConfig = currentPhase;

        const status = (currentPhase.status_do_projeto || '').toLowerCase() || 'ativo';
        const lastTs = this._lastUpdateTimestamp(card);
        const updatedLabel = lastTs ? `atualizado ${this._timeAgo(lastTs)}` : '';
        this.title.innerHTML = `
            <div class="modal-title-wrap">
                <span class="modal-title-text">Projeto: <strong>${card.titulo || ''}</strong></span>
                <div class="modal-title-meta">
                    <span class="phase-badge phase-badge-${status}">
                        <span class="phase-badge-dot"></span>${currentPhase.nome || 'Sem fase'}
                    </span>
                    ${updatedLabel ? `<span class="modal-meta-sep">·</span><span class="modal-meta-time"><i class="far fa-clock"></i> ${updatedLabel}</span>` : ''}
                </div>
            </div>
        `;

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

        // 1. History (Snapshots of Data) - ORDEM CRONOLÓGICA (Cima para Baixo)
        historyCol.innerHTML = '<div class="col-title"><i class="fas fa-file-invoice"></i> Histórico de Dados</div>';
        
        const sortedHistory = (card.historico || [])
            .filter(h => h.fase_entrada && h.fase_entrada !== card.fase_atual)
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)); // Temporário: mais recentes primeiro para o filtro

        const seenPhases = new Set();
        const snapshots = sortedHistory.filter(h => {
            if (!seenPhases.has(h.fase_entrada)) {
                seenPhases.add(h.fase_entrada);
                return true;
            }
            return false;
        }).sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp)); // Volta para cronológico (Antigo -> Novo)

        if (snapshots.length === 0) {
            historyCol.innerHTML += '<p style="color:var(--text-muted); font-size:0.8rem; font-style:italic; padding: 10px;">Nenhum snapshot de dados anterior disponível.</p>';
        } else {
            const fallbackLabels = {};
            config.fases.forEach(f => f.campos.forEach(c => fallbackLabels[c.id] = c.label));

            snapshots.forEach(h => {
                const item = document.createElement('div');
                item.className = 'history-item';
                if (window.APP_CONFIG.podeEditarKanban) {
                    item.classList.add('clickable');
                    item.onclick = () => this.showHistoryEditModal(h, config, card);
                }
                
                let fieldsHtml = '';
                const labels = h.labels || {};
                const dados = h.dados || {};
                
                // Encontrar a configuração da fase para filtrar apenas os campos que pertencem a ela
                const phaseConfig = config.fases.find(f => f.nome === h.fase_entrada);
                const allowedFields = phaseConfig ? phaseConfig.campos.map(c => c.id) : [];

                Object.entries(dados).forEach(([key, val]) => {
                    if (key === '_labels' || key === 'titulo' || key === 'fase') return;
                    
                    // SE a fase for conhecida, filtramos para mostrar apenas os campos dela
                    if (allowedFields.length > 0 && !allowedFields.includes(key)) return;

                    const label = labels[key] || fallbackLabels[key] || key;
                    
                    let displayVal = val;
                    if (Array.isArray(val)) displayVal = val.join(', ');
                    else if (val === true) displayVal = 'Sim';
                    else if (val === false) displayVal = 'Não';
                    else if (!val && val !== 0) displayVal = '-';
                    else if (typeof val === 'string' && val.includes('T') && val.length > 10) {
                         try { displayVal = new Date(val).toLocaleString(); } catch(e) {}
                    }

                    fieldsHtml += `
                        <div class="history-field" style="margin-bottom: 6px; border-bottom: 1px solid rgba(255,255,255,0.03); padding-bottom: 4px;">
                            <span style="font-weight: 600; font-size: 0.7rem; color: var(--text-muted); display: block; text-transform: uppercase;">${label}</span>
                            <span style="font-size: 0.85rem; color: #eee;">${displayVal}</span>
                        </div>
                    `;
                });

                let edicaoHtml = '';
                if (h.snapshot && h.snapshot.edicoes && h.snapshot.edicoes.length > 0) {
                    const ultimaEdicao = h.snapshot.edicoes[h.snapshot.edicoes.length - 1];
                    const dataEdicao = new Date(ultimaEdicao.data).toLocaleDateString();
                    edicaoHtml = `
                        <div style="font-size: 0.65rem; color: var(--text-muted); margin-top: 8px; border-top: 1px dotted rgba(255,255,255,0.1); padding-top: 4px; font-style: italic; display: flex; align-items: center; gap: 4px;">
                            <i class="fas fa-edit"></i> Editado em ${dataEdicao} por ${ultimaEdicao.usuario}
                        </div>
                    `;
                }

                item.innerHTML = `
                    <div class="history-phase-header" style="background: rgba(255,255,255,0.05); padding: 8px 12px; border-radius: 6px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; color: var(--kanban-accent); font-size: 0.75rem; text-transform: uppercase;">${h.fase_entrada}</span>
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <span style="font-size: 0.65rem; color: var(--text-muted);">${new Date(h.timestamp).toLocaleDateString()}</span>
                            ${window.APP_CONFIG.podeEditarKanban ? '<i class="fas fa-pen" style="font-size: 0.65rem; color: var(--text-muted); opacity: 0.6;"></i>' : ''}
                        </div>
                    </div>
                    <div class="history-snapshot-content" style="padding: 0 4px;">
                        ${fieldsHtml || '<div style="color:var(--text-muted); font-size:0.75rem;">Sem dados registrados nesta fase.</div>'}
                        ${edicaoHtml}
                    </div>
                `;
                historyCol.appendChild(item);
            });
        }

        const techLogBtn = document.createElement('button');
        techLogBtn.className = 'btn-link';
        techLogBtn.style = 'font-size: 0.7rem; color: var(--text-muted); margin-top: 20px; background: none; border: none; cursor: pointer; text-decoration: underline;';
        techLogBtn.innerHTML = '<i class="fas fa-list-ul"></i> Ver log de movimentações técnico';
        techLogBtn.onclick = () => this.showTechnicalLog(card);
        historyCol.appendChild(techLogBtn);

        // 2. Form
        formCol.innerHTML = `<div class="col-title"><i class="fas fa-edit"></i> Dados da Fase: ${currentPhase.nome}</div>`;
        const formContainer = document.createElement('div');
        formContainer.className = 'modal-form-standard';
        formCol.appendChild(formContainer);

        const nameGroup = document.createElement('div');
        nameGroup.className = 'form-group full-width';
        nameGroup.innerHTML = `<label>Nome do Projeto / Cliente *</label>`;
        const nameInput = document.createElement('input');
        nameInput.id = 'field_projeto_nome';
        nameInput.className = 'modern-input';
        nameInput.value = card.titulo || '';
        nameGroup.appendChild(nameInput);
        formContainer.appendChild(nameGroup);

        currentPhase.campos.forEach(campo => {
            const group = document.createElement('div');
            group.className = 'form-group';
            if (campo.tipo === 'text') group.classList.add('full-width');
            group.innerHTML = `<label>${campo.label}${campo.obrigatorio ? ' *' : ''}</label>${campo.descricao ? `<p class="field-description">${campo.descricao}</p>` : ''}`;
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
            if (reason === 'direct') statusIcon = '<i class="fas fa-bolt direct-access-icon" title="Acesso direto"></i>';
            if (reason === 'return') statusIcon = '<i class="fas fa-undo"></i>';

            btn.innerHTML = `<span>${fase.nome}</span><span>${statusIcon}</span>`;
            if (allowed) {
                btn.onclick = () => this.handleTransition(card, fase);
            }
            transCol.appendChild(btn);
        });

        const btnArchive = document.getElementById('btnArchive');
        if (btnArchive) {
            if (window.APP_CONFIG.podeEditarKanban) {
                btnArchive.style.display = 'inline-flex';
                const isArchived = !!(card.dados && card.dados.arquivado);
                if (isArchived) {
                    btnArchive.innerHTML = '<i class="fas fa-folder-open"></i> Desarquivar';
                    btnArchive.className = 'btn-secondary';
                } else {
                    btnArchive.innerHTML = '<i class="fas fa-archive"></i> Arquivar';
                    btnArchive.className = 'btn-danger';
                }
                btnArchive.onclick = async () => {
                    try {
                        const targetState = !isArchived;
                        await api.post(`/api/kanban/cards/${card.card_id}/update`, {
                            nome: card.titulo,
                            dados: { arquivado: targetState }
                        });
                        toast.success(targetState ? "Card arquivado!" : "Card desarquivado!");
                        this.hide();
                        board.refresh();
                    } catch (err) {
                        toast.error(err.message);
                    }
                };
            } else {
                btnArchive.style.display = 'none';
            }
        }

        this.saveBtn.onclick = () => this.handleSave(card.card_id);

        // Controle de Permissão (Read-Only)
        if (!window.APP_CONFIG.podeEditarKanban) {
            document.getElementById('modalFooter').style.display = 'none';
            if (btnArchive) btnArchive.style.display = 'none';
            // Desabilitar botões de transição
            transCol.querySelectorAll('.transition-btn').forEach(btn => btn.classList.add('blocked'));
            // Desabilitar inputs
            modalBody.querySelectorAll('input, select, textarea').forEach(el => el.disabled = true);
        } else {
            document.getElementById('modalFooter').style.display = 'flex';
        }

        this.overlay.style.display = 'flex';
    },

    showTechnicalLog(card, page = 1) {
        const pageSize = 10;
        const allLogs = [...(card.historico || [])].sort((a,b) => new Date(b.timestamp) - new Date(a.timestamp));
        const totalPages = Math.ceil(allLogs.length / pageSize);
        const start = (page - 1) * pageSize;
        const end = start + pageSize;
        const logsToShow = allLogs.slice(start, end);

        const _getInitial = (str) => {
            if (!str) return '?';
            const s = String(str).trim();
            return (s[0] || '?').toUpperCase();
        };

        const logHtml = logsToShow.map(h => {
            const usuario = h.usuario || 'Sistema';
            const isSistema = !h.usuario || /sistema/i.test(usuario);
            const initial = _getInitial(usuario);
            const avatarHtml = isSistema
                ? `<span class="log-user-avatar log-user-avatar--sistema"><i class="fas fa-cog"></i></span>`
                : `<span class="log-user-avatar" data-email="${usuario}"><span class="log-user-initial">${initial}</span></span>`;
            return `
            <div class="log-item">
                <div class="log-item-header">
                    <span style="font-weight: 700; color: ${h.evento === 'atualizacao' ? '#3b82f6' : 'var(--kanban-accent)'};">
                        ${h.evento === 'criacao' ? 'CRIAÇÃO' : (h.evento === 'atualizacao' ? 'ALTERAÇÃO' : 'MOVIMENTAÇÃO')}
                    </span>
                    <span style="color: var(--text-muted);">${new Date(h.timestamp).toLocaleString()}</span>
                </div>
                <div class="log-item-content">
                    ${h.evento === 'criacao' ? `Projeto criado na fase <b>${h.fase_entrada}</b>` :
                      (h.evento === 'atualizacao' ? this._renderAlteracoes(h.snapshot?.alteracoes) :
                      `Movido de <b>${h.fase_anterior || '-'}</b> para <b>${h.fase_nova || h.fase_entrada}</b>`)}
                </div>
                <div class="log-item-user">
                    ${avatarHtml}<span class="log-user-name">${usuario}</span>
                </div>
            </div>
        `;
        }).join('');

        // Pagination controls
        let paginationHtml = '';
        if (totalPages > 1) {
            paginationHtml = `
                <div class="pagination-container">
                    <button class="btn-prev" ${page === 1 ? 'disabled' : ''}>
                        <i class="fas fa-chevron-left"></i> Anterior
                    </button>
                    <span style="font-size: 0.85rem; color: var(--text-muted); font-weight: 600;">${page} / ${totalPages}</span>
                    <button class="btn-next" ${page === totalPages ? 'disabled' : ''}>
                        Próxima <i class="fas fa-chevron-right"></i>
                    </button>
                </div>
            `;
        }

        let logModal = document.getElementById('techLogModal');
        if (!logModal) {
            logModal = document.createElement('div');
            logModal.id = 'techLogModal';
            logModal.className = 'modal-overlay';
            logModal.style.zIndex = '2000';
            logModal.style.display = 'flex';
            document.body.appendChild(logModal);
        }

        logModal.innerHTML = `
            <div class="tech-log-content">
                <div class="modal-header">
                    <h3 class="modal-title">Log Técnico de Movimentações</h3>
                    <button class="btn-close-log">&times;</button>
                </div>
                <div class="modal-body">
                    ${logHtml}
                </div>
                ${paginationHtml ? `
                <div class="modal-footer-tech">
                    ${paginationHtml}
                </div>
                ` : ''}
            </div>
        `;

        logModal.querySelector('.btn-close-log').onclick = () => {
            logModal.remove();
        };

        if (totalPages > 1) {
            const prev = logModal.querySelector('.btn-prev');
            const next = logModal.querySelector('.btn-next');
            if (page > 1) prev.onclick = () => this.showTechnicalLog(card, page - 1);
            if (page < totalPages) next.onclick = () => this.showTechnicalLog(card, page + 1);
        }

        logModal.onclick = (e) => { if(e.target === logModal) logModal.remove(); };

        this._carregarFotosLog(logModal);
    },

    _fotoCache: {},

    _lastUpdateTimestamp(card) {
        const hist = card.historico || [];
        if (hist.length === 0) return null;
        const ts = hist
            .map(h => h.timestamp)
            .filter(Boolean)
            .map(t => new Date(t).getTime())
            .filter(n => !isNaN(n));
        if (ts.length === 0) return null;
        return new Date(Math.max(...ts));
    },

    _timeAgo(date) {
        const now = new Date();
        const diffMs = now - date;
        const diffSec = Math.floor(diffMs / 1000);
        const diffMin = Math.floor(diffSec / 60);
        const diffHour = Math.floor(diffMin / 60);
        const diffDay = Math.floor(diffHour / 24);
        if (diffSec < 60) return 'agora há pouco';
        if (diffMin < 60) return `há ${diffMin} min`;
        if (diffHour < 24) return `há ${diffHour}h`;
        if (diffDay < 30) return `há ${diffDay}d`;
        const diffMonth = Math.floor(diffDay / 30);
        if (diffMonth < 12) return `há ${diffMonth} mês${diffMonth > 1 ? 'es' : ''}`;
        const diffYear = Math.floor(diffDay / 365);
        return `há ${diffYear} ano${diffYear > 1 ? 's' : ''}`;
    },

    async _carregarFotosLog(scopeEl) {
        const avatars = scopeEl.querySelectorAll('.log-user-avatar[data-email]');
        const emails = Array.from(new Set(Array.from(avatars).map(a => a.dataset.email).filter(Boolean)));
        for (const email of emails) {
            try {
                let info = this._fotoCache[email];
                if (info === undefined) {
                    const resp = await fetch(`/api/usuarios/${encodeURIComponent(email)}/foto`, { credentials: 'same-origin' });
                    info = resp.ok ? await resp.json() : { foto: null };
                    this._fotoCache[email] = info;
                }
                if (info && info.foto) {
                    scopeEl.querySelectorAll(`.log-user-avatar[data-email="${email}"]`).forEach(el => {
                        el.innerHTML = `<img src="${info.foto}" alt="${email}" class="log-user-photo">`;
                        el.classList.add('log-user-avatar--has-photo');
                    });
                }
            } catch (e) {
                this._fotoCache[email] = { foto: null };
            }
        }
    },

    _renderAlteracoes(alteracoes) {
        if (!alteracoes || Object.keys(alteracoes).length === 0) return "Campos atualizados.";
        let html = '<div class="diff-container">';
        Object.entries(alteracoes).forEach(([campo, diff]) => {
            const formatVal = (val) => {
                if (val === true) return '<span class="badge-success">Sim</span>';
                if (val === false) return '<span class="badge-danger">Não</span>';
                if (!val && val !== 0) return '<span style="opacity:0.5;">-</span>';
                return val;
            };

            html += `
                <div class="diff-item">
                    <b class="diff-field-name">${campo}:</b> 
                    <div class="diff-values-wrapper">
                        <span class="diff-val-old">${formatVal(diff.de)}</span> 
                        <i class="fas fa-long-arrow-alt-right diff-arrow"></i> 
                        <span class="diff-val-new">${formatVal(diff.para)}</span>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        return html;
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
        const btnArchive = document.getElementById('btnArchive');
        if (btnArchive) btnArchive.style.display = 'none';

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
            group.innerHTML = `<label>${campo.label}${campo.obrigatorio ? ' *' : ''}</label>${campo.descricao ? `<p class="field-description">${campo.descricao}</p>` : ''}`;
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

    showHistoryEditModal(historyItem, config, card) {
        const phaseConfig = config.fases.find(f => f.nome === historyItem.fase_entrada);
        if (!phaseConfig) {
            return toast.error("Configuração da fase não encontrada para edição.");
        }

        let editModal = document.getElementById('historyEditModal');
        if (!editModal) {
            editModal = document.createElement('div');
            editModal.id = 'historyEditModal';
            editModal.className = 'modal-overlay';
            editModal.style.zIndex = '2100';
            editModal.style.display = 'flex';
            document.body.appendChild(editModal);
        }

        // Render structure
        editModal.innerHTML = `
            <div class="modal-content" style="max-width: 600px; width: 90%;">
                <div class="modal-header">
                    <h2><i class="fas fa-edit" style="color: var(--kanban-accent); margin-right: 10px;"></i>Editar dados: ${phaseConfig.nome}</h2>
                    <button class="btn-close-modal btn-close-edit-history" title="Fechar"><i class="fas fa-xmark"></i></button>
                </div>
                <div class="modal-body-scroll" style="padding: 24px;">
                    <div id="historyEditForm" class="modal-form-standard"></div>
                    
                    ${historyItem.snapshot && historyItem.snapshot.edicoes && historyItem.snapshot.edicoes.length > 0 ? `
                        <div class="history-edits-log" style="margin-top: 24px; padding-top: 16px; border-top: 1px dashed rgba(255,255,255,0.1);">
                            <div style="font-weight: 700; font-size: 0.75rem; color: var(--text-muted); margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.05em;">
                                <i class="fas fa-history" style="margin-right: 4px;"></i> Histórico de alterações deste registro:
                            </div>
                            <div style="max-height: 120px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px;">
                                ${historyItem.snapshot.edicoes.map(ed => {
                                    const dataEd = new Date(ed.data).toLocaleString();
                                    const alteracoesHtml = Object.entries(ed.alteracoes).map(([c, d]) => {
                                        return `<span style="display: block; font-size: 0.7rem; color: var(--text-muted); margin-left: 8px;">• <b>${c}</b>: de "${d.antes || '-'}" para "${d.depois || '-'}"</span>`;
                                    }).join('');
                                    return `
                                        <div style="background: rgba(255,255,255,0.02); padding: 8px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.03);">
                                            <span style="font-size: 0.72rem; color: #eee; font-weight: 600;">${ed.usuario}</span>
                                            <span style="font-size: 0.65rem; color: var(--text-muted); margin-left: 6px;">(${dataEd})</span>
                                            ${alteracoesHtml}
                                        </div>
                                    `;
                                }).join('')}
                            </div>
                        </div>
                    ` : ''}
                </div>
                <div class="modal-footer">
                    <button class="btn-secondary btn-cancel-edit-history">Cancelar</button>
                    <button class="btn-primary btn-save-edit-history"><i class="fas fa-check" style="margin-right: 6px;"></i>Salvar Alterações</button>
                </div>
            </div>
        `;

        const formContainer = editModal.querySelector('#historyEditForm');
        const dados = historyItem.dados || {};

        phaseConfig.campos.forEach(campo => {
            const group = document.createElement('div');
            group.className = 'form-group';
            if (campo.tipo === 'text') group.classList.add('full-width');
            group.innerHTML = `<label>${campo.label}${campo.obrigatorio ? ' *' : ''}</label>${campo.descricao ? `<p class="field-description">${campo.descricao}</p>` : ''}`;
            
            const input = this.createFieldInput(campo, dados[campo.id]);
            input.id = `hist_field_${campo.id}`;
            group.appendChild(input);
            formContainer.appendChild(group);
        });

        const closeBtn = editModal.querySelector('.btn-close-edit-history');
        const cancelBtn = editModal.querySelector('.btn-cancel-edit-history');
        const saveBtn = editModal.querySelector('.btn-save-edit-history');

        const closeFn = () => editModal.remove();
        closeBtn.onclick = closeFn;
        cancelBtn.onclick = closeFn;
        editModal.onclick = (e) => { if (e.target === editModal) closeFn(); };

        saveBtn.onclick = async () => {
            const novosDados = {};
            let valid = true;

            phaseConfig.campos.forEach(campo => {
                const el = editModal.querySelector(`#hist_field_${campo.id}`);
                let val;
                if (campo.tipo === 'radio') {
                    val = (el.querySelector('input:checked') || {}).value || '';
                } else if (campo.tipo === 'checkbox') {
                    val = Array.from(el.querySelectorAll('input:checked')).map(i => i.value);
                } else if (campo.tipo === 'boolean') {
                    val = el.querySelector('input').checked;
                } else if (campo.tipo === 'link') {
                    val = el.querySelector('input').value;
                } else {
                    val = el.value;
                }
                
                if (campo.obrigatorio && (!val || (Array.isArray(val) && val.length === 0)) && val !== 0 && val !== false) {
                    el.style.borderColor = 'red';
                    valid = false;
                } else {
                    if (el) el.style.borderColor = '';
                }
                novosDados[campo.id] = val;
            });

            if (!valid) return toast.error("Preencha todos os campos obrigatórios.");

            try {
                if (!confirm("Tem certeza de que deseja atualizar as informações históricas desta fase?")) {
                    return;
                }

                saveBtn.disabled = true;
                saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';
                
                const result = await api.post(`/api/kanban/history/${historyItem.id}/update`, { dados: novosDados });
                if (result && result.status === 'success') {
                    toast.success("Dados históricos atualizados!");
                    closeFn();
                    
                    const updatedCard = await api.getCard(card.card_id);
                    this.showView(updatedCard, config);
                    
                    if (window.board && typeof window.board.refresh === 'function') {
                        window.board.refresh();
                    }
                } else {
                    throw new Error(result.error || "Erro ao salvar alterações no histórico.");
                }
            } catch (err) {
                toast.error(err.message);
                saveBtn.disabled = false;
                saveBtn.innerHTML = '<i class="fas fa-check" style="margin-right: 6px;"></i>Salvar Alterações';
            }
        };
    },

    hide() {
        this.overlay.style.display = 'none';
    }
};
