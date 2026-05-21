const board = {
    config: null,
    cards: [],
    pageSize: 30,
    searchQuery: "",
    columnsPagination: {},
    searchTimeout: null,
    viewArchived: false,
    
    async init() {
        modal.init();
        await this.refresh();
        
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

        const searchInput = document.getElementById('kanbanSearch');
        if (searchInput) {
            searchInput.oninput = (e) => this.handleSearch(e.target.value);
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
    },

    async refresh() {
        try {
            this.config = await api.getBoardConfig();
            this.cards = await api.getCards();
            
            const searchVal = document.getElementById('kanbanSearch')?.value || "";
            this.searchQuery = searchVal;
            
            this.render();
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

                if (!query) return true;
                return c.titulo.toLowerCase().includes(query) || String(c.card_id).includes(query);
            });

            col.innerHTML = `
                <div class="column-header">
                    <h3>${phase.nome}</h3>
                    <span class="column-count">${phaseCards.length}</span>
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
            cardEl.innerHTML = `
                <h4>${card.titulo}</h4>
                <div class="card-meta">
                    <span><i class="fas fa-hashtag"></i> ${card.card_id}</span>
                    <span><i class="fas fa-money-bill-wave"></i> ${card.fee.toLocaleString('pt-BR', {style:'currency', currency: card.moeda || 'BRL'})}</span>
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
    }
};

document.addEventListener('DOMContentLoaded', () => board.init());
