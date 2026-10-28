/* Global clipboard helper (used by kanban_config.js and kanban.js) */
function copyToClipboard(text, successMsg) {
    successMsg = successMsg || "Link copiado!";
    const fallback = () => {
        const input = document.createElement('textarea');
        input.value = text;
        input.style.position = 'fixed';
        input.style.opacity = '0';
        document.body.appendChild(input);
        input.select();
        try {
            document.execCommand('copy');
            toast.success(successMsg);
        } catch (e) {
            toast.error("Não foi possível copiar. Selecione o link manualmente.");
        }
        document.body.removeChild(input);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            toast.success(successMsg);
        }).catch(() => fallback());
    } else {
        fallback();
    }
}

function generateUUID() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = Math.random() * 16 | 0;
        return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
}

/* ---- Postar no feed: variáveis como chips arrastáveis ---- */
const FEED_VARS = ['titulo', 'fase', 'fase_anterior', 'fee', 'moeda', 'cliente', 'squad', 'responsavel', 'documento', 'produto', 'data_inicio', 'usuario'];

function feedEscHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function feedRenderTemplate(tpl) {
    if (!tpl) return '';
    return feedEscHtml(tpl).split(/(\{[a-z_]+\})/).map(part => {
        if (/^\{[a-z_]+\}$/.test(part)) {
            return `<span class="var-chip" contenteditable="false" data-token="${part}">${part}</span>`;
        }
        return part.replace(/\n/g, '<br>');
    }).join('');
}

function feedSerializeEditor(el) {
    let out = '';
    const BLOCK = /^(DIV|P|LI|H[1-6]|BLOCKQUOTE|PRE|UL|OL|TR|TABLE|SECTION|ARTICLE|FIGURE)$/;
    const walk = (node) => {
        node.childNodes.forEach(n => {
            if (n.nodeType === 3) {
                out += n.textContent;
            } else if (n.nodeType === 1) {
                const tag = n.tagName;
                if (n.dataset && n.dataset.token) {
                    out += n.dataset.token;
                } else if (tag === 'BR') {
                    out += '\n';
                } else if (BLOCK.test(tag)) {
                    if (out.length > 0 && !out.endsWith('\n')) out += '\n';
                    walk(n);
                    out += '\n';
                } else {
                    walk(n);
                }
            }
        });
    };
    walk(el);
    return out
        .replace(/\u200B/g, '')
        .replace(/\u00A0/g, ' ')
        .replace(/\n{3,}/g, '\n\n')
        .replace(/\n+$/g, '');
}

function feedEnsureSentinel(editor) {
    const last = editor.lastChild;
    if (last && last.nodeType === 1 && last.dataset && last.dataset.token) {
        editor.appendChild(document.createTextNode('\u200B'));
    }
}

function feedPlaceCaret(container, offset) {
    const range = document.createRange();
    range.setStart(container, offset);
    range.collapse(true);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    return range;
}

function feedMakeChip(token) {
    const span = document.createElement('span');
    span.className = 'var-chip';
    span.setAttribute('contenteditable', 'false');
    span.dataset.token = token;
    span.textContent = token;
    return span;
}

function feedInsertChip(editor, token, x, y) {
    if (!editor || !token) return;
    editor.focus();
    const inEditor = (r) => r && (r.startContainer === editor || editor.contains(r.startContainer));
    let range = null;
    if (typeof x === 'number') {
        if (document.caretRangeFromPoint) range = document.caretRangeFromPoint(x, y);
        else if (document.caretPositionFromPoint) {
            const p = document.caretPositionFromPoint(x, y);
            if (p) { range = document.createRange(); range.setStart(p.offsetNode, p.offset); range.collapse(true); }
        }
    }
    if (!inEditor(range)) {
        const sel = window.getSelection();
        if (sel && sel.rangeCount && inEditor(sel.getRangeAt(0))) range = sel.getRangeAt(0);
    }
    if (!inEditor(range) && inEditor(editor._lastRange)) range = editor._lastRange;
    if (!inEditor(range)) {
        range = document.createRange();
        range.selectNodeContents(editor);
        range.collapse(false);
    }
    const chip = feedMakeChip(token);
    const sentinel = document.createTextNode('\u200B');
    range.deleteContents();
    range.insertNode(sentinel);
    range.insertNode(chip);
    const caret = feedPlaceCaret(sentinel, 1);
    editor._lastRange = caret.cloneRange();
    editor.dispatchEvent(new Event('input', { bubbles: true }));
}

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
        this.currentConfig = JSON.parse(JSON.stringify(board.config));
        this.currentConfig._slug = board.currentSlug;
        this.expandedPhaseIndex = 0;
        const boardLabel = board.boardList.find(b => b.slug === board.currentSlug);
        const modalTitle = this.overlay.querySelector('.modal-header h2');
        if (modalTitle) {
            modalTitle.innerHTML = `<i class="fas fa-cog" style="color:#d61616; margin-right:10px;"></i>Configurar: ${boardLabel ? boardLabel.nome : board.currentSlug}`;
        }
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
                                ${['Ativo', 'Onetime', 'Inativo', 'Onboarding'].map(s => `
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

                    <div class="phase-feed-config" style="margin-top:18px; border-top:1px solid rgba(255,255,255,0.06); padding-top:16px;">
                        <label class="checkbox-label" style="cursor:pointer; font-weight:600;">
                            <input type="checkbox" class="phase-feed-auto" data-findex="${fIndex}" ${fase.feed_auto ? 'checked' : ''}>
                            <i class="fas fa-share" style="color:#d61616; margin-right:4px;"></i> Postar no feed
                        </label>
                        <div style="margin-top:12px;">
                            <label>Mensagem do feed</label>
                            <div class="phase-feed-palette" data-findex="${fIndex}">
                                ${FEED_VARS.map(v => `<span class="var-chip palette-chip" draggable="true" data-findex="${fIndex}" data-drag-token="{${v}}">{${v}}</span>`).join('')}
                            </div>
                            <div class="phase-feed-editor" contenteditable="true" spellcheck="false" data-findex="${fIndex}" data-placeholder="Ex.: Novo cliente na fase {fase}: {titulo} ({fee} {moeda}) 🚀">${feedRenderTemplate(fase.feed_template || '')}</div>
                            <div style="font-size:0.65rem; color:var(--text-muted); margin-top:6px; line-height:1.5;">
                                Arraste (ou clique) as variáveis acima para posicioná-las na mensagem.
                            </div>
                        </div>
                    </div>

                    <div class="transitions-config-section">
                        <div class="transitions-config-header-row">
                            <div class="transitions-config-header-title">
                                <i class="fas fa-route"></i> Transições Permitidas
                                <span class="transitions-count-badge" data-findex="${fIndex}">${this._countTransitions(fase)}</span>
                            </div>
                            <span class="transitions-config-hint">Para onde este card pode ser movido</span>
                        </div>
                        ${(() => {
                            const others = (this.currentConfig.fases || []).filter(f => f.id !== fase.id);
                            const optionalCount = others.filter(o => !(o.ordem === fase.ordem + 1 || o.permite_acesso_direto)).length;
                            return others.length > 5 ? `
                            <div class="transitions-toolbar">
                                <div class="transitions-search-wrap">
                                    <i class="fas fa-magnifying-glass"></i>
                                    <input type="text" class="transitions-search-input" data-findex="${fIndex}" placeholder="Filtrar fases...">
                                </div>
                                ${optionalCount > 0 ? `
                                <div class="transitions-quick-actions">
                                    <button type="button" class="transitions-quick-btn btn-transitions-all" data-findex="${fIndex}"><i class="fas fa-check-double"></i> Todas</button>
                                    <button type="button" class="transitions-quick-btn btn-transitions-none" data-findex="${fIndex}"><i class="fas fa-eraser"></i> Limpar</button>
                                </div>` : ''}
                            </div>` : '';
                        })()}
                        <div class="transitions-list" data-findex="${fIndex}">
                            ${(this.currentConfig.fases || []).filter(f => f.id !== fase.id).map(otherFase => {
                                const isNext = otherFase.ordem === fase.ordem + 1;
                                const isDirect = otherFase.permite_acesso_direto;
                                const isAlwaysAllowed = isNext || isDirect;
                                const isChecked = isAlwaysAllowed || (fase.fases_permitidas || []).includes(otherFase.id);
                                return `
                                    <label class="transition-checkbox-item ${isAlwaysAllowed ? 'always-allowed' : ''} ${isChecked ? 'is-checked' : ''}" data-fase-name="${(otherFase.nome || '').toLowerCase()}">
                                        <input type="checkbox"
                                            class="transition-fase-check"
                                            data-findex="${fIndex}"
                                            data-faseid="${otherFase.id}"
                                            ${isChecked ? 'checked' : ''}
                                            ${isAlwaysAllowed ? 'disabled' : ''}>
                                        <span class="transition-check-box"><i class="fas fa-check"></i></span>
                                        <span class="transition-fase-name">${otherFase.nome}</span>
                                        ${isNext ? '<span class="transition-badge-next">Próxima (sequência)</span>' : ''}
                                        ${isDirect ? '<span class="transition-badge-direct">Acesso Direto</span>' : ''}
                                    </label>
                                `;
                            }).join('')}
                        </div>
                        <div class="transitions-empty-filter" data-findex="${fIndex}" style="display:none;">
                            <i class="fas fa-filter-circle-xmark"></i> Nenhuma fase corresponde ao filtro.
                        </div>
                    </div>

                    <div class="public-link-config-section">
                        <div class="public-link-header-row">
                            <div class="public-link-header-title">
                                <i class="fas fa-share-alt"></i> Link Público do Formulário
                                ${fase.form_token
                                    ? '<span class="public-link-status-badge active"><span class="public-link-status-dot"></span> Ativo</span>'
                                    : '<span class="public-link-status-badge"><span class="public-link-status-dot"></span> Desativado</span>'}
                            </div>
                            <span class="public-link-hint">Criação de cards sem login</span>
                        </div>
                        <div class="public-link-body">
                            ${fase.form_token ? `
                                <div class="public-link-card">
                                    <div class="public-link-card-icon"><i class="fas fa-link"></i></div>
                                    <div class="public-link-card-main">
                                        <span class="public-link-card-label">Endereço do formulário</span>
                                        <span class="public-link-card-url" title="${window.location.origin}/form-card/${fase.form_token}">${window.location.origin}/form-card/${fase.form_token}</span>
                                    </div>
                                </div>
                                <div class="public-link-actions">
                                    <button class="btn-link-action btn-link-copy" data-link="${window.location.origin}/form-card/${fase.form_token}">
                                        <i class="fas fa-copy"></i> Copiar
                                    </button>
                                    <a class="btn-link-action btn-link-open" href="${window.location.origin}/form-card/${fase.form_token}" target="_blank" rel="noopener">
                                        <i class="fas fa-arrow-up-right-from-square"></i> Abrir
                                    </a>
                                    <button class="btn-link-action btn-link-regen btn-regenerate-token" data-findex="${fIndex}">
                                        <i class="fas fa-sync"></i> Regenerar
                                    </button>
                                </div>
                            ` : `
                                <div class="public-link-empty">
                                    <div class="public-link-empty-icon"><i class="fas fa-link-slash"></i></div>
                                    <div class="public-link-empty-text">
                                        <strong>Nenhum link público ativo</strong>
                                        <span>Gere um link para receber cards de qualquer pessoa, sem necessidade de login.</span>
                                    </div>
                                    <button class="btn-primary btn-generate-token" data-findex="${fIndex}">
                                        <i class="fas fa-link"></i> Gerar Link Público
                                    </button>
                                </div>
                            `}
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
                                    <div class="field-desc-row">
                                        <input type="text" class="modern-input field-desc-input" data-findex="${fIndex}" data-cindex="${cIndex}"
                                               placeholder="Descrição opcional (ex: Informe o valor mensal do contrato)"
                                               value="${campo.descricao || ''}">
                                    </div>
                                    ${campo.tipo === 'incremental' ? this._incrementalConfigHtml(campo, fIndex, cIndex) : `
                                    <div class="field-sync-row">
                                        <label class="field-sync-toggle-wrap" title="Sincronizar este campo com uma coluna do banco">
                                            <input type="checkbox" class="field-sync-toggle" data-findex="${fIndex}" data-cindex="${cIndex}" ${campo.mapeamento_coluna ? 'checked' : ''}>
                                            <span class="field-sync-toggle-label">
                                                <i class="fas fa-database"></i> Sincronizar com banco de dados
                                            </span>
                                        </label>
                                        <div class="field-sync-select-wrap" style="display:${campo.mapeamento_coluna ? 'flex' : 'none'};">
                                            <span class="field-sync-arrow"><i class="fas fa-arrow-right-long"></i></span>
                                            <select class="modern-select field-sync-table" data-findex="${fIndex}" data-cindex="${cIndex}">
                                                <option value="">Tabela...</option>
                                                ${this._tableOptions(campo.mapeamento_tabela || 'projetos')}
                                            </select>
                                            <select class="modern-select field-mapping-select field-mapping-compact" data-findex="${fIndex}" data-cindex="${cIndex}">
                                                <option value="">Coluna...</option>
                                                ${this._columnOptions(campo.mapeamento_tabela || 'projetos', campo.mapeamento_coluna)}
                                            </select>
                                            <div class="field-sync-slot" style="display:${(campo.mapeamento_tabela || 'projetos') === 'projetos_contas' ? 'flex' : 'none'};">
                                                <select class="modern-select field-sync-platform" data-findex="${fIndex}" data-cindex="${cIndex}">
                                                    <option value="">Plataforma...</option>
                                                    ${this._platformOptions(campo.mapeamento_plataforma)}
                                                </select>
                                                <input type="text" class="modern-input field-sync-frente" data-findex="${fIndex}" data-cindex="${cIndex}"
                                                    value="${campo.mapeamento_frente || ''}" placeholder="Frente (opcional)">
                                            </div>
                                        </div>
                                    </div>
                                    `}
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

        this.body.querySelectorAll('.phase-feed-auto').forEach(chk => {
            chk.onchange = (e) => { this.currentConfig.fases[e.target.dataset.findex].feed_auto = e.target.checked; };
        });
        this.body.querySelectorAll('.phase-feed-editor').forEach(editor => {
            const fi = editor.dataset.findex;
            const saveCaret = () => {
                const sel = window.getSelection();
                if (sel && sel.rangeCount && (sel.getRangeAt(0).startContainer === editor || editor.contains(sel.getRangeAt(0).startContainer))) {
                    editor._lastRange = sel.getRangeAt(0).cloneRange();
                }
            };
            editor.addEventListener('keyup', saveCaret);
            editor.addEventListener('mouseup', saveCaret);
            editor.addEventListener('focus', saveCaret);
            editor.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    document.execCommand('insertLineBreak');
                    editor.dispatchEvent(new Event('input', { bubbles: true }));
                }
            });
            editor.addEventListener('input', () => {
                saveCaret();
                if (editor.textContent.replace(/\u200B/g, '').length === 0 && !editor.querySelector('.var-chip')) {
                    editor.innerHTML = '';
                } else {
                    feedEnsureSentinel(editor);
                }
                this.currentConfig.fases[fi].feed_template = feedSerializeEditor(editor);
            });
            editor.addEventListener('dragover', (e) => { e.preventDefault(); editor.classList.add('drag-over'); });
            editor.addEventListener('dragleave', () => editor.classList.remove('drag-over'));
            editor.addEventListener('drop', (e) => {
                e.preventDefault();
                editor.classList.remove('drag-over');
                const token = e.dataTransfer.getData('text/plain');
                if (token) feedInsertChip(editor, token, e.clientX, e.clientY);
            });
        });
        this.body.querySelectorAll('.palette-chip').forEach(chip => {
            chip.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('text/plain', chip.dataset.dragToken);
                e.dataTransfer.effectAllowed = 'copy';
            });
            chip.addEventListener('mousedown', (e) => e.preventDefault());
            chip.addEventListener('click', () => {
                const editor = this.body.querySelector(`.phase-feed-editor[data-findex="${chip.dataset.findex}"]`);
                if (editor) feedInsertChip(editor, chip.dataset.dragToken, null, null);
            });
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
                fases_permitidas: [],
                campos: [{ id: 'f_' + Date.now(), label: 'Título', tipo: 'string', obrigatorio: true }]
            });
            this.expandedPhaseIndex = newIndex;
            this.render();
        };

        this.body.querySelectorAll('.phase-direct-access-check').forEach(chk => {
            chk.onchange = (e) => { this.currentConfig.fases[e.target.dataset.findex].permite_acesso_direto = e.target.checked; };
        });

        this.body.querySelectorAll('.transition-fase-check').forEach(chk => {
            chk.onchange = (e) => {
                const { findex, faseid } = e.target.dataset;
                const fase = this.currentConfig.fases[findex];
                if (!fase.fases_permitidas) fase.fases_permitidas = [];
                if (e.target.checked) {
                    if (!fase.fases_permitidas.includes(faseid)) {
                        fase.fases_permitidas.push(faseid);
                    }
                } else {
                    fase.fases_permitidas = fase.fases_permitidas.filter(id => id !== faseid);
                }
                const item = e.target.closest('.transition-checkbox-item');
                if (item) item.classList.toggle('is-checked', e.target.checked);
                this._refreshTransitionCount(findex);
            };
        });

        // Filtro de transições
        this.body.querySelectorAll('.transitions-search-input').forEach(input => {
            input.oninput = (e) => {
                const { findex } = e.target.dataset;
                const term = e.target.value.toLowerCase().trim();
                const list = this.body.querySelector(`.transitions-list[data-findex="${findex}"]`);
                const empty = this.body.querySelector(`.transitions-empty-filter[data-findex="${findex}"]`);
                let visible = 0;
                list.querySelectorAll('.transition-checkbox-item').forEach(item => {
                    const match = !term || (item.dataset.faseName || '').includes(term);
                    item.style.display = match ? 'flex' : 'none';
                    if (match) visible++;
                });
                if (empty) empty.style.display = visible === 0 ? 'block' : 'none';
            };
        });

        // Ações rápidas: Todas / Limpar
        this.body.querySelectorAll('.btn-transitions-all').forEach(btn => {
            btn.onclick = (e) => {
                const { findex } = e.currentTarget.dataset;
                const fase = this.currentConfig.fases[findex];
                fase.fases_permitidas = (this.currentConfig.fases || [])
                    .filter(f => f.id !== fase.id && !(f.ordem === fase.ordem + 1 || f.permite_acesso_direto))
                    .map(f => f.id);
                this.render();
            };
        });
        this.body.querySelectorAll('.btn-transitions-none').forEach(btn => {
            btn.onclick = (e) => {
                const { findex } = e.currentTarget.dataset;
                this.currentConfig.fases[findex].fases_permitidas = [];
                this.render();
            };
        });

        this.body.querySelectorAll('.btn-generate-token').forEach(btn => {
            btn.onclick = (e) => {
                const { findex } = e.target.dataset;
                const fase = this.currentConfig.fases[findex];
                fase.form_token = generateUUID();
                this.render();
            };
        });

        this.body.querySelectorAll('.btn-regenerate-token').forEach(btn => {
            btn.onclick = async (e) => {
                const { findex } = e.target.dataset;
                if (!(await HubModal.confirm("Regenerar o link invalidará o link anterior. Continuar?"))) return;
                const fase = this.currentConfig.fases[findex];
                fase.form_token = generateUUID();
                this.render();
            };
        });

        this.body.querySelectorAll('.btn-copy-link, .btn-link-copy').forEach(btn => {
            btn.onclick = (e) => {
                const link = e.currentTarget.dataset.link;
                copyToClipboard(link, "Link do formulário copiado!");
            };
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
                    obrigatorio: false,
                    descricao: ''
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
                const campo = this.currentConfig.fases[findex].campos[cindex];
                campo.tipo = e.target.value;
                if (campo.tipo === 'incremental') {
                    campo.subcampos = campo.subcampos || [];
                    campo.subtabela = campo.subtabela || '';
                }
                this.render();
            };
        });

        this.body.querySelectorAll('.field-options-input').forEach(input => {
            input.onchange = (e) => {
                const { findex, cindex } = e.target.dataset;
                this.currentConfig.fases[findex].campos[cindex].opcoes = e.target.value.split(',').map(s => s.trim()).filter(s => s !== '');
            };
        });

        this.body.querySelectorAll('.field-desc-input').forEach(input => {
            input.onchange = (e) => {
                const { findex, cindex } = e.target.dataset;
                this.currentConfig.fases[findex].campos[cindex].descricao = e.target.value;
            };
        });

        this.body.querySelectorAll('.field-req-check').forEach(chk => {
            chk.onchange = (e) => {
                const { findex, cindex } = e.target.dataset;
                this.currentConfig.fases[findex].campos[cindex].obrigatorio = e.target.checked;
            };
        });

        this.body.querySelectorAll('.field-incremental-target').forEach(sel => {
            sel.onchange = (e) => {
                const { findex, cindex } = e.target.dataset;
                const campo = this.currentConfig.fases[findex].campos[cindex];
                campo.subtabela = e.target.value || '';
                (campo.subcampos || []).forEach(sub => { sub.coluna = ''; });
                this.render();
            };
        });

        this.body.querySelectorAll('.field-sub-label').forEach(input => {
            input.onchange = (e) => {
                const { findex, cindex, sindex } = e.target.dataset;
                const campo = this.currentConfig.fases[findex].campos[cindex];
                const sub = (campo.subcampos || [])[sindex];
                if (sub) sub.label = e.target.value;
            };
        });

        this.body.querySelectorAll('.field-sub-type').forEach(sel => {
            sel.onchange = (e) => {
                const { findex, cindex, sindex } = e.target.dataset;
                const campo = this.currentConfig.fases[findex].campos[cindex];
                const sub = (campo.subcampos || [])[sindex];
                if (!sub) return;
                sub.tipo = e.target.value;
                if (!['select', 'checkbox', 'radio'].includes(sub.tipo)) {
                    sub.opcoes = [];
                }
                if (sub.tipo === 'plataformas' && campo.subtabela === 'projetos_contas') {
                    sub.coluna = 'plataforma';
                } else if (sub.coluna === 'plataforma' && sub.tipo !== 'plataformas') {
                    sub.coluna = '';
                }
                this.render();
            };
        });

        this.body.querySelectorAll('.field-sub-required').forEach(chk => {
            chk.onchange = (e) => {
                const { findex, cindex, sindex } = e.target.dataset;
                const campo = this.currentConfig.fases[findex].campos[cindex];
                const sub = (campo.subcampos || [])[sindex];
                if (sub) sub.obrigatorio = e.target.checked;
            };
        });

        this.body.querySelectorAll('.field-sub-options').forEach(input => {
            input.onchange = (e) => {
                const { findex, cindex, sindex } = e.target.dataset;
                const campo = this.currentConfig.fases[findex].campos[cindex];
                const sub = (campo.subcampos || [])[sindex];
                if (sub) {
                    sub.opcoes = e.target.value.split(',').map(v => v.trim()).filter(v => v !== '');
                }
            };
        });

        this.body.querySelectorAll('.field-sub-column').forEach(sel => {
            sel.onchange = (e) => {
                const { findex, cindex, sindex } = e.target.dataset;
                const campo = this.currentConfig.fases[findex].campos[cindex];
                const sub = (campo.subcampos || [])[sindex];
                if (sub) sub.coluna = e.target.value;
            };
        });

        this.body.querySelectorAll('.field-sub-remove').forEach(btn => {
            btn.onclick = (e) => {
                const el = e.target.closest('button');
                const { findex, cindex, sindex } = el.dataset;
                const campo = this.currentConfig.fases[findex].campos[cindex];
                (campo.subcampos || []).splice(Number(sindex), 1);
                this.render();
            };
        });

        this.body.querySelectorAll('.btn-add-subfield').forEach(btn => {
            btn.onclick = (e) => {
                const { findex, cindex } = e.target.closest('button').dataset;
                const campo = this.currentConfig.fases[findex].campos[cindex];
                campo.subcampos = campo.subcampos || [];
                campo.subcampos.push({
                    id: this._novoSubfieldId(),
                    label: '',
                    tipo: 'string',
                    obrigatorio: false,
                    opcoes: [],
                    coluna: ''
                });
                this.render();
            };
        });

        this.body.querySelectorAll('.field-mapping-select').forEach(sel => {
            sel.onchange = (e) => {
                const { findex, cindex } = e.target.dataset;
                this.currentConfig.fases[findex].campos[cindex].mapeamento_coluna = e.target.value;
            };
        });

        this.body.querySelectorAll('.field-sync-table').forEach(sel => {
            sel.onchange = (e) => {
                const { findex, cindex } = e.target.dataset;
                const campo = this.currentConfig.fases[findex].campos[cindex];
                campo.mapeamento_tabela = e.target.value || 'projetos';
                e.target.value = campo.mapeamento_tabela;
                campo.mapeamento_coluna = '';
                if (campo.mapeamento_tabela === 'projetos_contas') {
                    campo.mapeamento_plataforma = campo.mapeamento_plataforma || 'meta_ads';
                    campo.mapeamento_frente = campo.mapeamento_frente || '';
                } else {
                    campo.mapeamento_plataforma = '';
                    campo.mapeamento_frente = '';
                }

                const wrap = e.target.closest('.field-sync-select-wrap');
                const colSel = wrap.querySelector('.field-mapping-select');
                colSel.innerHTML = `<option value="">Coluna...</option>${this._columnOptions(campo.mapeamento_tabela, '')}`;

                const slot = wrap.querySelector('.field-sync-slot');
                slot.style.display = campo.mapeamento_tabela === 'projetos_contas' ? 'flex' : 'none';
                const platformSel = wrap.querySelector('.field-sync-platform');
                if (platformSel) platformSel.value = campo.mapeamento_plataforma || '';
                const frenteInp = wrap.querySelector('.field-sync-frente');
                if (frenteInp) frenteInp.value = campo.mapeamento_frente || '';

                wrap.style.display = 'flex';
            };
        });

        this.body.querySelectorAll('.field-sync-platform').forEach(sel => {
            sel.onchange = (e) => {
                const { findex, cindex } = e.target.dataset;
                this.currentConfig.fases[findex].campos[cindex].mapeamento_plataforma = e.target.value;
            };
        });

        this.body.querySelectorAll('.field-sync-frente').forEach(inp => {
            inp.onchange = (e) => {
                const { findex, cindex } = e.target.dataset;
                this.currentConfig.fases[findex].campos[cindex].mapeamento_frente = e.target.value;
            };
        });

        this.body.querySelectorAll('.field-sync-toggle').forEach(chk => {
            chk.onchange = (e) => {
                const { findex, cindex } = e.target.dataset;
                const wrap = e.target.closest('.field-sync-row').querySelector('.field-sync-select-wrap');
                const select = wrap.querySelector('.field-mapping-select');
                const campo = this.currentConfig.fases[findex].campos[cindex];
                if (e.target.checked) {
                    campo.mapeamento_tabela = campo.mapeamento_tabela || 'projetos';
                    wrap.style.display = 'flex';
                } else {
                    wrap.style.display = 'none';
                    select.value = '';
                    campo.mapeamento_coluna = '';
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

    _mappingTargets() {
        return window.KANBAN_MAPPING_TARGETS || {};
    },

    _columnLabel(target, code) {
        const col = (target.columns || {})[code];
        if (!col) return code;
        return typeof col === 'string' ? col : (col.label || code);
    },

    _tableOptions(selected) {
        return Object.entries(this._mappingTargets()).map(([code, target]) =>
            `<option value="${code}" ${code === selected ? 'selected' : ''}>${target.label || code}</option>`
        ).join('');
    },

    _columnOptions(tabela, selected) {
        const target = this._mappingTargets()[tabela] || {};
        return Object.keys(target.columns || {}).map(code => {
            const col = target.columns[code];
            const legacy = typeof col === 'object' && col && col.legacy;
            const label = this._columnLabel(target, code);
            return `<option value="${code}" ${code === selected ? 'selected' : ''}>${label}${legacy ? ' (legado)' : ''}</option>`;
        }).join('');
    },

    _platformEntries() {
        if (Array.isArray(window.KANBAN_PLATAFORMAS) && window.KANBAN_PLATAFORMAS.length) {
            return window.KANBAN_PLATAFORMAS.map(p => [p.codigo, p.nome]);
        }
        const target = this._mappingTargets()['projetos_contas'] || {};
        return Object.entries(target.platforms || {});
    },

    _platformOptions(selected) {
        return this._platformEntries().map(([code, label]) =>
            `<option value="${code}" ${code === selected ? 'selected' : ''}>${label}</option>`
        ).join('');
    },

    _collectionTargets() {
        return window.KANBAN_COLLECTION_TARGETS || {};
    },

    _incrementalTargetOptions(selected) {
        return Object.entries(this._collectionTargets()).map(([code, target]) =>
            `<option value="${code}" ${code === selected ? 'selected' : ''}>${target.label || code}</option>`
        ).join('');
    },

    _incrementalColumnOptions(target, selected) {
        const def = this._collectionTargets()[target] || {};
        return Object.entries(def.columns || {}).map(([code, col]) =>
            `<option value="${code}" ${code === selected ? 'selected' : ''}>${(col && col.label) || code}</option>`
        ).join('');
    },

    _subfieldTypes() {
        return [
            { v: 'string',      l: 'Linha única',        i: 'fa-i-cursor'      },
            { v: 'text',        l: 'Parágrafo',          i: 'fa-align-left'    },
            { v: 'number',      l: 'Número',             i: 'fa-hashtag'       },
            { v: 'boolean',     l: 'Sim/Não',            i: 'fa-toggle-on'     },
            { v: 'datetime',    l: 'Data',               i: 'fa-calendar-days' },
            { v: 'select',      l: 'Opções (escolha 1)', i: 'fa-caret-down'    },
            { v: 'checkbox',    l: 'Múltipla escolha',   i: 'fa-square-check'  },
            { v: 'radio',       l: 'Escolha única',      i: 'fa-circle-dot'    },
            { v: 'link',        l: 'Link / URL',         i: 'fa-link'          },
            { v: 'plataformas', l: 'Plataformas',        i: 'fa-rectangle-ad'  },
        ];
    },

    _subfieldLabel(type) {
        const t = this._subfieldTypes().find(x => x.v === type);
        return t ? t.l : type;
    },

    _novoSubfieldId() {
        return `sf_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
    },

    _incrementalConfigHtml(campo, fIndex, cIndex) {
        const subcampos = campo.subcampos || [];
        const target = campo.subtabela || '';
        const targetDef = this._collectionTargets()[target];
        return `
            <div class="field-incremental-config">
                <div class="incremental-config-head">
                    <span><i class="fas fa-layer-group"></i> Estrutura do incremental</span>
                    <span class="incremental-count">${subcampos.length} subcampo(s)</span>
                </div>
                <div class="incremental-target-row">
                    <label>Sincronizar com banco</label>
                    <select class="modern-select field-incremental-target" data-findex="${fIndex}" data-cindex="${cIndex}">
                        <option value="">Nenhum (somente card)</option>
                        ${this._incrementalTargetOptions(target)}
                    </select>
                </div>
                ${targetDef ? `<p class="incremental-target-hint">Cada linha será sincronizada com <strong>${targetDef.label}</strong>. Mapeie os subcampos para as colunas desejadas.</p>` : ''}
                <div class="incremental-subfields">
                    ${subcampos.map((sub, sIndex) => this._incrementalSubfieldHtml(campo, sub, fIndex, cIndex, sIndex)).join('')}
                </div>
                <button type="button" class="btn-add-subfield" data-findex="${fIndex}" data-cindex="${cIndex}">
                    <i class="fas fa-plus"></i> Adicionar subcampo
                </button>
            </div>
        `;
    },

    _incrementalSubfieldHtml(campo, sub, fIndex, cIndex, sIndex) {
        const target = campo.subtabela || '';
        const targetDef = this._collectionTargets()[target];
        const tipo = sub.tipo || 'string';
        const pedeOpcoes = ['select', 'checkbox', 'radio'].includes(tipo);
        return `
            <div class="incremental-subfield" data-findex="${fIndex}" data-cindex="${cIndex}" data-sindex="${sIndex}">
                <input type="text" class="modern-input field-sub-label" data-findex="${fIndex}" data-cindex="${cIndex}" data-sindex="${sIndex}"
                    value="${sub.label || ''}" placeholder="Nome do subcampo">
                <select class="modern-select field-sub-type" data-findex="${fIndex}" data-cindex="${cIndex}" data-sindex="${sIndex}">
                    ${this._subfieldTypes().map(t => `<option value="${t.v}" ${t.v === tipo ? 'selected' : ''}>${t.l}</option>`).join('')}
                </select>
                <label class="field-sub-required-wrap" title="Subcampo obrigatório?">
                    <input type="checkbox" class="field-sub-required" data-findex="${fIndex}" data-cindex="${cIndex}" data-sindex="${sIndex}" ${sub.obrigatorio ? 'checked' : ''}>
                    <span>Obrigatório</span>
                </label>
                ${pedeOpcoes ? `
                    <input type="text" class="modern-input field-sub-options" data-findex="${fIndex}" data-cindex="${cIndex}" data-sindex="${sIndex}"
                        value="${(sub.opcoes || []).join(', ')}" placeholder="Opções separadas por vírgula">
                ` : ''}
                ${tipo === 'plataformas' ? `<span class="incremental-sub-hint"><i class="fas fa-lock"></i> Opções fixas</span>` : ''}
                ${targetDef ? `
                    <select class="modern-select field-sub-column" data-findex="${fIndex}" data-cindex="${cIndex}" data-sindex="${sIndex}">
                        <option value="">Coluna...</option>
                        ${this._incrementalColumnOptions(target, sub.coluna)}
                    </select>
                ` : ''}
                <button type="button" class="field-sub-remove" data-findex="${fIndex}" data-cindex="${cIndex}" data-sindex="${sIndex}" title="Remover subcampo">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
    },

    _fieldTypes() {
        return [
            { v: 'string',      l: 'Linha única',          i: 'fa-i-cursor'      },
            { v: 'text',        l: 'Parágrafo',            i: 'fa-align-left'    },
            { v: 'number',      l: 'Número',               i: 'fa-hashtag'       },
            { v: 'boolean',     l: 'Sim/Não',              i: 'fa-toggle-on'     },
            { v: 'datetime',    l: 'Data',                 i: 'fa-calendar-days' },
            { v: 'select',      l: 'Opções (escolha 1)',   i: 'fa-caret-down'    },
            { v: 'checkbox',    l: 'Múltipla escolha',     i: 'fa-square-check'  },
            { v: 'radio',       l: 'Escolha única',        i: 'fa-circle-dot'    },
            { v: 'link',        l: 'Link / URL',           i: 'fa-link'          },
            { v: 'incremental', l: 'Incremental',          i: 'fa-layer-group'   },
        ];
    },

    _countTransitions(fase) {
        return (this.currentConfig.fases || [])
            .filter(f => f.id !== fase.id)
            .filter(other => {
                const isNext = other.ordem === fase.ordem + 1;
                const isDirect = other.permite_acesso_direto;
                return isNext || isDirect || (fase.fases_permitidas || []).includes(other.id);
            }).length;
    },

    _refreshTransitionCount(findex) {
        const fase = this.currentConfig.fases[findex];
        const badge = this.body.querySelector(`.transitions-count-badge[data-findex="${findex}"]`);
        if (badge) badge.textContent = this._countTransitions(fase);
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
