const board = {
    container: document.getElementById('kanbanBoard'),
    config: null,
    cards: [],
    draggedCardId: null,

    async init(config) {
        this.config = config;
        await this.refresh();
    },

    async refresh() {
        this.cards = await api.getCards(this.config.kanban_id);
        this.render();
    },

    render() {
        this.container.innerHTML = '';
        const sortedFases = [...this.config.fases].sort((a,b) => a.ordem - b.ordem);
        
        sortedFases.forEach((fase, index) => {
            const col = document.createElement('div');
            col.className = 'kanban-column';
            col.dataset.faseId = fase.id;
            
            // Filter cards for this phase
            const phaseCards = this.cards.filter(c => c.fase_atual === fase.nome);
            
            // Só exibe o botão de adicionar na primeira coluna/fase
            const addButton = index === 0 ? `<button class="btn-add" data-fase-id="${fase.id}">+</button>` : '';

            col.innerHTML = `
                <div class="column-header">
                    <div class="header-title">
                        <h3>${fase.nome}</h3>
                        <span class="column-count">${phaseCards.length}</span>
                    </div>
                    ${addButton}
                </div>
                <div class="card-list" data-fase-id="${fase.id}"></div>
            `;
            
            const list = col.querySelector('.card-list');
            
            // Drag & Drop events for column
            list.ondragover = (e) => {
                e.preventDefault();
                list.classList.add('column-over');
            };
            list.ondragleave = () => list.classList.remove('column-over');
            list.ondrop = (e) => {
                e.preventDefault();
                list.classList.remove('column-over');
                this.handleDrop(this.draggedCardId, fase.id);
            };

            // Add card button (only allowed on first phase)
            const addBtnEl = col.querySelector('.btn-add');
            if (addBtnEl) {
                addBtnEl.onclick = () => this.addNewCard(fase.id);
            }

            // Filter and render cards for this phase
            phaseCards.forEach(card => {
                const cardEl = this.createCardElement(card);
                list.appendChild(cardEl);
            });

            this.container.appendChild(col);
        });
    },

    formatDuration(ms) {
        if (ms < 0) ms = 0;
        const seconds = Math.floor(ms / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 0) return `${days}d`;
        if (hours > 0) return `${hours}h`;
        if (minutes > 0) return `${minutes}m`;
        return 'now';
    },

    getTimeInCurrentPhase(card) {
        if (!card.historico || card.historico.length === 0) return 0;
        const currentEntry = card.historico.find(h => h.saida === null);
        if (!currentEntry) return 0;
        
        const entrada = new Date(currentEntry.entrada.replace(' ', 'T'));
        return new Date() - entrada;
    },

    getTimeSince(dateStr) {
        if (!dateStr) return 0;
        const date = new Date(dateStr.replace(' ', 'T'));
        return new Date() - date;
    },

    createCardElement(card) {
        const el = document.createElement('div');
        el.className = 'kanban-card';
        el.draggable = true;
        el.dataset.cardId = card.card_id;
        
        const ageMs = this.getTimeSince(card.criado_em);
        const phaseMs = this.getTimeInCurrentPhase(card);
        const updateMs = this.getTimeSince(card.atualizado_em);

        const ageText = this.formatDuration(ageMs);
        const phaseText = this.formatDuration(phaseMs);
        const updateText = this.formatDuration(updateMs);

        el.innerHTML = `
            <h4>${card.titulo}</h4>
            <div class="card-info">ID: ${card.card_id.slice(0,8)}</div>
            <div class="card-badges">
                <div class="badge age" title="${ageText} desde que o card foi criado">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                    <span>${ageText}</span>
                </div>
                <div class="badge phase" title="${phaseText} nesta fase (${card.fase_atual})">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/><path d="M12 2v2"/></svg>
                    <span>${phaseText}</span>
                </div>
                <div class="badge update" title="${updateText} desde a última atualização">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>
                    <span>${updateText}</span>
                </div>
            </div>
        `;

        el.ondragstart = () => {
            this.draggedCardId = card.card_id;
            el.classList.add('card-dragging');
        };
        el.ondragend = () => el.classList.remove('card-dragging');
        
        el.onclick = () => this.editCard(card);
        
        return el;
    },

    async addNewCard(faseId) {
        // Find the phase config
        const fase = this.config.fases.find(f => f.id === faseId);
        
        modal.show(`Novo Card em ${fase.nome}`, fase, {}, async (dados) => {
            await api.createCard(this.config.kanban_id, dados);
            // If the start phase is NOT the one where we clicked '+', we might need to move it immediately
            // But usually '+' on a column implies creating it THERE. 
            // In our system, createCard default to primeira_fase.
            // Let's keep it simple: createCard, then move if needed.
            this.refresh();
        });
    },

    async editCard(card) {
        modal.showView(card, this.config);
    },

    async handleDrop(cardId, targetFaseId) {
        const card = this.cards.find(c => c.card_id === cardId);
        const targetFase = this.config.fases.find(f => f.id === targetFaseId);

        // Se já está na fase, não faz nada
        if (card.fase_atual === targetFase.nome) return;

        // ── Validação determinística de transição ──
        const currentFase = this.config.fases.find(f => f.nome === card.fase_atual);
        const { allowed, reason } = canTransition(currentFase, targetFase, card);

        if (!allowed) {
            const nextFase = [...this.config.fases]
                .sort((a, b) => a.ordem - b.ordem)
                .find(f => f.ordem === (currentFase ? currentFase.ordem + 1 : -1));
            const nextName = nextFase ? `"${nextFase.nome}"` : 'a próxima fase';
            toast.error(
                `🔒 Movimento bloqueado: "${targetFase.nome}" não é a próxima fase da sequência. ` +
                `O próximo passo é ${nextName}.`
            );
            return;
        }

        // Busca se já existe um snapshot anterior desta fase
        const previousSnapshot = card.fases.find(f => f.fase_id === targetFase.nome);

        if (previousSnapshot) {
            // Se já passou pela fase, move direto reaproveitando os dados antigos
            try {
                await api.moveCard(cardId, targetFaseId, previousSnapshot.dados);
                this.refresh();
            } catch (err) {
                toast.error(`Erro ao mover card: ${err.message}`);
            }
        } else {
            // Se é uma fase nova, abre o modal
            modal.show(`Mover para ${targetFase.nome}`, targetFase, {}, async (dados) => {
                try {
                    await api.moveCard(cardId, targetFaseId, dados);
                    this.refresh();
                } catch (err) {
                    toast.error(`Erro ao mover card: ${err.message}`);
                }
            });
        }
    }
};
