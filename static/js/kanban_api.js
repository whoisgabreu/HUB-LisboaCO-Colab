const API_BASE = ""; // Relative to same host

// ── Toast utility ────────────────────────────────────────────────────────────
const toast = {
    show(message, type = 'info', duration = 4000) {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        const el = document.createElement('div');
        el.className = `toast toast-${type}`;
        el.textContent = message;
        container.appendChild(el);
        setTimeout(() => {
            el.style.opacity = '0';
            el.style.transform = 'translateX(100%)';
            el.style.transition = 'all 0.3s ease';
            setTimeout(() => el.remove(), 300);
        }, duration);
    },
    error(msg)   { this.show(msg, 'error'); },
    success(msg) { this.show(msg, 'success'); },
    info(msg)    { this.show(msg, 'info'); }
};

// ── API client ───────────────────────────────────────────────────────────────
const api = {
    async _handleResponse(resp) {
        const body = await resp.json();
        if (!resp.ok) {
            throw new Error(body.error || `Erro: ${resp.status}`);
        }
        return body;
    },

    async get(path) {
        const resp = await fetch(`${API_BASE}${path}`);
        return this._handleResponse(resp);
    },

    async post(path, body) {
        const resp = await fetch(`${API_BASE}${path}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        return this._handleResponse(resp);
    },

    // Specific methods
    getBoardConfig: () => api.get("/api/kanban/config"),
    getCards:       () => api.get("/api/kanban/cards"),
    getCard:        (cardId) => api.get(`/api/kanban/cards/${cardId}`),
    moveCard:       (cardId, novaFaseId, dados) => api.post("/api/kanban/move", { card_id: cardId, nova_fase_id: novaFaseId, dados }),
    createCard:     (payload) => api.post("/api/kanban/cards", payload),
    saveConfig:     (config) => api.post("/api/kanban/config", config) // Not implemented in backend yet, but for future
};
