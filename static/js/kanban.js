const board = {
    config: null,
    cards: [],
    currentSlug: "fluxo-projetos",
    boardList: [],
    pageSize: 30,
    searchQuery: "",
    columnsPagination: {},
    searchTimeout: null,
    viewArchived: false,
    tagsAtivas: [],
    _fieldLabels: null,
    
    async init() {
        modal.init();
        await this.loadBoardList();
        await this.refresh();
        
        document.getElementById('kanbanBoard').addEventListener('click', (e) => {
            const linkIcon = e.target.closest('.column-form-link');
            if (!linkIcon) return;
            e.stopPropagation();
            const url = linkIcon.dataset.link;
            if (!url) return;
            copyToClipboard(url, "Link do formulário copiado!");
        });

        document.getElementById('btnRefresh').onclick = async (e) => {
            const btn = e.currentTarget;
            const icon = btn.querySelector('i');
            btn.classList.add('is-refreshing');
            if (icon) icon.classList.add('fa-spin');
            try {
                await this.refresh();
            } finally {
                setTimeout(() => {
                    btn.classList.remove('is-refreshing');
                    if (icon) icon.classList.remove('fa-spin');
                }, 400);
            }
        };
        document.getElementById('btnNewCard').onclick = () => this.handleNewCard();

        const searchWrapper = document.getElementById('searchWrapper');
        const searchInput = document.getElementById('kanbanSearch');
        if (searchWrapper && searchInput) {
            searchWrapper.onclick = (e) => {
                if (e.target !== searchInput) {
                    searchInput.focus();
                }
            };
        }

        if (searchInput) {
            searchInput.oninput = (e) => this.handleSearch(e.target.value);
            
            searchInput.addEventListener('keydown', (event) => {
                const valor = searchInput.value.trim();

                if (event.key === 'Enter') {
                    event.preventDefault();
                    if (valor !== '') {
                        if (!this.tagsAtivas.includes(valor)) {
                            this.tagsAtivas.push(valor);
                            this.renderTags();
                            this.handleSearch(""); // Clear current search text query
                        }
                        searchInput.value = '';
                    }
                }

                if (event.key === 'Backspace' && valor === '' && this.tagsAtivas.length > 0) {
                    this.tagsAtivas.pop();
                    this.renderTags();
                    this.handleSearch("");
                }
            });
        }

        const btnToggleArchived = document.getElementById('btnToggleArchived');
        if (btnToggleArchived) {
            btnToggleArchived.onclick = () => {
                this.viewArchived = !this.viewArchived;
                if (this.viewArchived) {
                    btnToggleArchived.innerHTML = '<i class="fas fa-folder-open"></i> Ver Normais';
                    btnToggleArchived.classList.add('active-filter');
                } else {
                    btnToggleArchived.innerHTML = '<i class="fas fa-archive"></i> Ver Arquivados';
                    btnToggleArchived.classList.remove('active-filter');
                }
                this.render();
            };
        }

        const boardSelector = document.getElementById('boardSelector');
        if (boardSelector) {
            boardSelector.onchange = () => {
                this.switchBoard(boardSelector.value);
            };
        }

        const btnCreateBoard = document.getElementById('btnCreateBoard');
        if (btnCreateBoard) {
            btnCreateBoard.onclick = () => this.handleCreateBoard();
        }
    },

    async loadBoardList() {
        try {
            this.boardList = await api.getBoardList();
            const selector = document.getElementById('boardSelector');
            if (!selector) return;
            const currentVal = selector.value;
            selector.innerHTML = this.boardList.map(b =>
                `<option value="${b.slug}" ${b.slug === this.currentSlug ? 'selected' : ''}>${b.nome}</option>`
            ).join('');
            if (currentVal && currentVal !== this.currentSlug) {
                selector.value = currentVal;
            }
        } catch (err) {
            console.warn("Erro ao carregar lista de boards:", err);
        }
    },

    async switchBoard(slug) {
        if (slug === this.currentSlug) return;
        this.currentSlug = slug;
        await this.refresh();
    },

    async handleCreateBoard() {
        const nome = prompt("Nome do novo board:");
        if (!nome || !nome.trim()) return;
        const slug = nome.trim().toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
        if (!slug) return toast.error("Nome inválido para criar board.");
        try {
            await api.createBoard(slug, nome.trim());
            toast.success(`Board "${nome.trim()}" criado!`);
            await this.loadBoardList();
            document.getElementById('boardSelector').value = slug;
            await this.switchBoard(slug);
        } catch (err) {
            toast.error("Erro ao criar board: " + err.message);
        }
    },

    async refresh() {
        try {
            this.config = await api.getBoardConfig(this.currentSlug);
            this.cards = await api.getCards(this.currentSlug);
            this._fieldLabels = null;
            
            const searchVal = document.getElementById('kanbanSearch')?.value || "";
            this.searchQuery = searchVal;
            
            document.querySelector('.kanban-header .header-board-selector select#boardSelector');
            this.render();
            this.renderTags();
        } catch (err) {
            toast.error("Erro ao carregar Kanban: " + err.message);
        }
    },

    render() {
        const container = document.getElementById('kanbanBoard');
        container.innerHTML = '';

        const phases = [...this.config.fases].sort((a, b) => a.ordem - b.ordem);
        const query = (this.searchQuery || '').toLowerCase().trim();

        phases.forEach(phase => {
            const col = document.createElement('div');
            col.className = 'kanban-column';
            col.dataset.phaseId = phase.id;
            col.dataset.phaseNome = phase.nome;

            const phaseCards = this.cards.filter(c => {
                const matchPhase = c.fase_atual === phase.nome;
                if (!matchPhase) return false;

                const isArchived = !!(c.dados && c.dados.arquivado);
                if (this.viewArchived !== isArchived) return false;

                const cardText = this.getCardSearchableText(c);

                // Matches all active tags
                const matchesTags = !this.tagsAtivas || this.tagsAtivas.every(tag => 
                    cardText.includes(tag.toLowerCase().trim())
                );

                // Matches current text query (unsubmitted)
                const matchesQuery = !query || cardText.includes(query);

                return matchesTags && matchesQuery;
            });

            col.innerHTML = `
                <div class="column-header">
                    <h3>${phase.nome}</h3>
                    <div class="column-header-right">
                        <span class="column-count">${phaseCards.length}</span>
                        ${phase.form_token ? `<i class="fas fa-link column-form-link" data-link="${window.location.origin}/form-card/${phase.form_token}" title="Copiar link do formulário público"></i>` : ''}
                    </div>
                </div>
                <div class="card-list" id="list-${phase.id}"></div>
            `;

            if (query && phaseCards.length === 0) {
                col.style.display = 'none';
            } else {
                col.style.display = 'flex';
            }

            container.appendChild(col);
            const list = col.querySelector('.card-list');

            // Initialize pagination state for this column
            this.columnsPagination[phase.id] = 1;

            // Render first batch (Page 1)
            this.renderBatch(phase.id, list, phaseCards, 1);

            // Progressive scroll loading
            list.onscroll = () => {
                if (list.scrollTop + list.clientHeight >= list.scrollHeight - 100) {
                    const currentPage = this.columnsPagination[phase.id];
                    const maxPages = Math.ceil(phaseCards.length / this.pageSize);
                    if (currentPage < maxPages) {
                        const nextPage = currentPage + 1;
                        this.columnsPagination[phase.id] = nextPage;
                        this.renderBatch(phase.id, list, phaseCards, nextPage);
                    }
                }
            };

            // Column Drop Events
            list.ondragover = (e) => {
                e.preventDefault();
                list.classList.add('column-over');
            };
            list.ondragleave = () => list.classList.remove('column-over');
            list.ondrop = async (e) => {
                e.preventDefault();
                list.classList.remove('column-over');
                const cardId = e.dataTransfer.getData('cardId');
                const targetPhaseId = phase.id;
                
                // Check if card is already in this phase
                const card = this.cards.find(c => c.card_id == cardId);
                if (card.fase_atual === phase.nome) return;

                try {
                    await api.moveCard(cardId, targetPhaseId, {});
                    toast.success("Card movido!");
                    this.refresh();
                } catch (err) {
                    toast.error(err.message);
                }
            };
        });
    },

    renderBatch(phaseId, listEl, cards, page) {
        const start = (page - 1) * this.pageSize;
        const end = page * this.pageSize;
        const batch = cards.slice(start, end);

        batch.forEach(card => {
            const cardEl = document.createElement('div');
            cardEl.className = 'kanban-card';
            cardEl.draggable = true;

            const ageMs = this.getCardAge(card);
            const phaseMs = this.getTimeInPhase(card);
            const updateMs = this.getTimeSinceUpdate(card);
            const ageText = this.formatDuration(ageMs);
            const phaseText = this.formatDuration(phaseMs);
            const updateText = this.formatDuration(updateMs);
            const phaseClass = this.phaseSeverityClass(phaseMs);

            const isClone = card.dados && card.dados._origem_clonagem === 'snapshot';

            cardEl.innerHTML = `
                <h4>${card.titulo}</h4>
                ${isClone ? '<div class="card-clone-badge"><i class="fas fa-copy"></i> Clonado de Snapshot</div>' : ''}
                <div class="card-meta">
                    <span><i class="fas fa-hashtag"></i> ${card.card_id}</span>
                    <span><i class="fas fa-money-bill-wave"></i> ${card.fee.toLocaleString('pt-BR', {style:'currency', currency: card.moeda || 'BRL'})}</span>
                </div>
                <div class="card-time-badges">
                    <span class="time-badge time-badge--age" title="Card criado há ${ageText}">
                        <i class="far fa-calendar-plus"></i> ${ageText}
                    </span>
                    <span class="time-badge time-badge--phase ${phaseClass}" title="${phaseText} nesta fase (${card.fase_atual || '-'})">
                        <i class="fas fa-hourglass-half"></i> ${phaseText}
                    </span>
                    <span class="time-badge time-badge--update" title="Última edição há ${updateText}">
                        <i class="fas fa-pen"></i> ${updateText}
                    </span>
                </div>
            `;
            
            cardEl.onclick = async () => {
                const fullCard = await api.getCard(card.card_id);
                modal.showView(fullCard, this.config);
            };

            // Drag Events
            cardEl.ondragstart = (e) => {
                e.dataTransfer.setData('cardId', card.card_id);
                cardEl.classList.add('card-dragging');
            };
            cardEl.ondragend = () => cardEl.classList.remove('card-dragging');

            listEl.appendChild(cardEl);
        });
    },

    async handleNewCard() {
        const firstPhase = this.config.fases.sort((a,b) => a.ordem - b.ordem)[0];
        modal.show(`Novo Projeto`, firstPhase, {}, async (payload) => {
            try {
                await api.createCard(payload);
                toast.success("Projeto criado com sucesso!");
                this.refresh();
            } catch (err) {
                toast.error(err.message);
            }
        });
    },

    handleSearch(query) {
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }
        this.searchTimeout = setTimeout(() => {
            this.searchQuery = query;
            this.render();
        }, 150);
    },

    formatDuration(ms) {
        if (!ms || ms < 0) return 'agora';
        const seconds = Math.floor(ms / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);
        if (days >= 30) {
            const months = Math.floor(days / 30);
            return `${months}m`;
        }
        if (days > 0) return `${days}d`;
        if (hours > 0) return `${hours}h`;
        if (minutes > 0) return `${minutes}min`;
        return 'agora';
    },

    _historicoTimestamps(card) {
        const hist = card && Array.isArray(card.historico) ? card.historico : [];
        return hist
            .map(h => h && h.timestamp ? new Date(h.timestamp).getTime() : NaN)
            .filter(n => !isNaN(n));
    },

    getCardAge(card) {
        const ts = this._historicoTimestamps(card);
        if (ts.length === 0) return 0;
        return Date.now() - Math.min(...ts);
    },

    getTimeSinceUpdate(card) {
        const ts = this._historicoTimestamps(card);
        if (ts.length === 0) return 0;
        return Date.now() - Math.max(...ts);
    },

    getTimeInPhase(card) {
        const hist = card && Array.isArray(card.historico) ? card.historico : [];
        if (hist.length === 0 || !card.fase_atual) return 0;
        const entries = hist
            .filter(h => h && h.timestamp && (h.fase_entrada === card.fase_atual || h.fase_nova === card.fase_atual))
            .map(h => new Date(h.timestamp).getTime())
            .filter(n => !isNaN(n));
        if (entries.length === 0) return 0;
        return Date.now() - Math.max(...entries);
    },

    phaseSeverityClass(ms) {
        const days = ms / (1000 * 60 * 60 * 24);
        if (days >= 30) return 'time-badge--danger';
        if (days >= 14) return 'time-badge--warning';
        return '';
    },

    getCardSearchableText(card) {
        // Collect labels map
        if (!this._fieldLabels) {
            this._fieldLabels = {};
            if (this.config && this.config.fases) {
                this.config.fases.forEach(f => {
                    if (f.campos) {
                        f.campos.forEach(c => {
                            this._fieldLabels[c.id] = c.label;
                        });
                    }
                });
            }
        }

        const labelsMap = { ...this._fieldLabels };
        if (card.historico) {
            card.historico.forEach(h => {
                if (h.labels) {
                    Object.entries(h.labels).forEach(([key, label]) => {
                        labelsMap[key] = label;
                    });
                }
            });
        }

        const searchable = [
            String(card.card_id),
            card.titulo || '',
            card.fase_atual || '',
            card.status || '',
            String(card.fee || ''),
            card.fee ? card.fee.toLocaleString('pt-BR', {style:'currency', currency: card.moeda || 'BRL'}) : '',
            card.moeda || ''
        ];

        const addVal = (key, val) => {
            const label = labelsMap[key] || key;
            searchable.push(label);
            
            if (Array.isArray(val)) {
                searchable.push(...val.map(String));
            } else if (val === true) {
                searchable.push('Sim');
            } else if (val === false) {
                searchable.push('Não');
            } else if (val !== null && val !== undefined) {
                const strVal = String(val);
                searchable.push(strVal);
                if (/^\d{4}-\d{2}-\d{2}/.test(strVal)) {
                    const parts = strVal.split('T')[0].split('-');
                    if (parts.length === 3) {
                        searchable.push(`${parts[2]}/${parts[1]}/${parts[0]}`);
                    }
                }
            }
        };

        if (card.dados) {
            Object.entries(card.dados).forEach(([key, val]) => {
                addVal(key, val);
            });
        }

        if (card.historico) {
            card.historico.forEach(h => {
                if (h.dados) {
                    Object.entries(h.dados).forEach(([key, val]) => {
                        addVal(key, val);
                    });
                }
                if (h.snapshot) {
                    const snapCompleto = h.snapshot.snapshot_completo || h.snapshot.dados;
                    if (snapCompleto && typeof snapCompleto === 'object') {
                        Object.entries(snapCompleto).forEach(([key, val]) => {
                            addVal(key, val);
                        });
                    }
                    if (h.snapshot.alteracoes && typeof h.snapshot.alteracoes === 'object') {
                        Object.entries(h.snapshot.alteracoes).forEach(([fieldName, diff]) => {
                            searchable.push(fieldName);
                            if (diff) {
                                addVal(fieldName, diff.de);
                                addVal(fieldName, diff.para);
                            }
                        });
                    }
                }
            });
        }

        const uniqueValues = Array.from(new Set(searchable.filter(Boolean)));
        return uniqueValues.map(v => v.toLowerCase().trim()).join(' ');
    },

    renderTags() {
        const wrapper = document.getElementById('tags-wrapper');
        const searchInput = document.getElementById('kanbanSearch');
        if (!wrapper || !searchInput) return;

        wrapper.innerHTML = '';
        this.tagsAtivas.forEach((tag, index) => {
            const divTag = document.createElement('div');
            divTag.className = 'search-tag';
            divTag.innerHTML = `<span>${tag}</span> <span class="btn-remover" onclick="board.removerTag(${index})">&times;</span>`;
            wrapper.appendChild(divTag);
        });

        if (searchInput) {
            searchInput.placeholder = this.tagsAtivas.length > 0 ? '' : 'Pesquisar projeto ou cliente...';
        }
    },

    removerTag(index) {
        this.tagsAtivas.splice(index, 1);
        this.renderTags();
        this.handleSearch(""); // Re-render filter list
        const searchInput = document.getElementById('kanbanSearch');
        if (searchInput) searchInput.focus();
    }
};

document.addEventListener('DOMContentLoaded', () => board.init());
