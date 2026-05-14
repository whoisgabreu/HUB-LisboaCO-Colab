const app = {
    kanbanSelector: document.getElementById('kanbanSelector'),
    
    async init() {
        modal.init();
        configEditor.init();
        await this.loadKanbans();
        
        this.kanbanSelector.onchange = (e) => {
            this.loadBoard(e.target.value);
        };
    },

    async loadKanbans() {
        try {
            const kanbans = await api.getKanbans();
            this.kanbanSelector.innerHTML = '';
            
            kanbans.forEach(k => {
                const opt = document.createElement('option');
                opt.value = k.kanban_id;
                opt.text = k.nome;
                this.kanbanSelector.appendChild(opt);
            });

            if (kanbans.length > 0) {
                this.loadBoard(kanbans[0].kanban_id);
            }
        } catch (err) {
            console.error("Failed to load kanbans", err);
            alert("Erro ao conectar com o backend. Certifique-se que o servidor FastAPI está rodando em http://localhost:8000");
        }
    },

    async loadBoard(id) {
        const config = await api.getKanban(id);
        board.init(config);
    }
};

window.onload = () => app.init();
