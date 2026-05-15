const board = {
    config: null,
    cards: [],
    
    async init() {
        modal.init();
        await this.refresh();
        
        document.getElementById('btnRefresh').onclick = () => this.refresh();
        document.getElementById('btnNewCard').onclick = () => this.handleNewCard();

        const searchInput = document.getElementById('kanbanSearch');
        if (searchInput) {
            searchInput.oninput = (e) => this.handleSearch(e.target.value);
        }
    },

    async refresh() {
        try {
            this.config = await api.getBoardConfig();
            this.cards = await api.getCards();
            this.render();

            // Re-apply filter if search is active
            const searchVal = document.getElementById('kanbanSearch')?.value;
            if (searchVal) this.handleSearch(searchVal);
        } catch (err) {
            toast.error("Erro ao carregar Kanban: " + err.message);
        }
    },

    render() {
        const container = document.getElementById('kanbanBoard');
        container.innerHTML = '';

        const phases = [...this.config.fases].sort((a, b) => a.ordem - b.ordem);

        phases.forEach(phase => {
            const col = document.createElement('div');
            col.className = 'kanban-column';
            col.dataset.phaseId = phase.id;
            col.dataset.phaseNome = phase.nome;

            const phaseCards = this.cards.filter(c => c.fase_atual === phase.nome);

            col.innerHTML = `
                <div class="column-header">
                    <h3>${phase.nome}</h3>
                    <span class="column-count">${phaseCards.length}</span>
                </div>
                <div class="card-list" id="list-${phase.id}"></div>
            `;

            container.appendChild(col);
            const list = col.querySelector('.card-list');

            phaseCards.forEach(card => {
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

                list.appendChild(cardEl);
            });

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
        const term = query.toLowerCase().trim();
        const columns = document.querySelectorAll('.kanban-column');

        columns.forEach(col => {
            const cards = col.querySelectorAll('.kanban-card');
            let visibleInColumn = 0;

            cards.forEach(card => {
                const title = card.querySelector('h4').innerText.toLowerCase();
                const matches = title.includes(term);
                card.style.display = matches ? 'block' : 'none';
                if (matches) visibleInColumn++;
            });

            // Update column count UI
            const countEl = col.querySelector('.column-count');
            
            if (term === '') {
                col.style.display = 'flex';
                // Restore original count
                const phaseNome = col.dataset.phaseNome;
                const totalInPhase = this.cards.filter(c => c.fase_atual === phaseNome).length;
                if (countEl) countEl.innerText = totalInPhase;
            } else {
                col.style.display = visibleInColumn > 0 ? 'flex' : 'none';
                if (countEl) countEl.innerText = visibleInColumn;
            }
        });
    }
};

document.addEventListener('DOMContentLoaded', () => board.init());
