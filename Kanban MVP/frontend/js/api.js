const API_BASE = "http://localhost:8000";

// ── Toast utility ────────────────────────────────────────────────────────────
const toast = {
    show(message, type = 'info', duration = 4000) {
        const container = document.getElementById('toastContainer');
        const el = document.createElement('div');
        el.className = `toast toast-${type}`;
        el.textContent = message;
        container.appendChild(el);
        setTimeout(() => {
            el.classList.add('toast-out');
            el.addEventListener('animationend', () => el.remove(), { once: true });
        }, duration);
    },
    error(msg)   { this.show(msg, 'error'); },
    success(msg) { this.show(msg, 'success'); },
    info(msg)    { this.show(msg, 'info'); }
};

// ── Typed API error ──────────────────────────────────────────────────────────
class ApiError extends Error {
    constructor(status, detail) {
        super(detail || `API Error: ${status}`);
        this.status = status;
        this.detail = detail;
    }
}

// ── API client ───────────────────────────────────────────────────────────────
const api = {
    async _handleResponse(resp) {
        if (!resp.ok) {
            let detail = `API Error: ${resp.status}`;
            try {
                const body = await resp.json();
                if (body.detail) detail = body.detail;
            } catch (_) {}
            throw new ApiError(resp.status, detail);
        }
        return resp.json();
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

    async put(path, body) {
        const resp = await fetch(`${API_BASE}${path}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        return this._handleResponse(resp);
    },

    async delete(path) {
        const resp = await fetch(`${API_BASE}${path}`, { method: 'DELETE' });
        return this._handleResponse(resp);
    },

    // Specific methods
    getKanbans:  ()                      => api.get("/kanban"),
    getKanban:   (id)                    => api.get(`/kanban/${id}`),
    getCards:    (kanbanId)              => api.get(`/cards?kanban_id=${kanbanId}`),
    getCard:     (cardId)                => api.get(`/cards/${cardId}`),
    createCard:  (kanbanId, dados)       => api.post("/cards", { kanban_id: kanbanId, dados_iniciais: dados }),
    updateCard:  (cardId, dados)         => api.put(`/cards/${cardId}`, { dados }),
    moveCard:    (cardId, novaFaseId, dados) => api.post(`/cards/${cardId}/mover`, { nova_fase_id: novaFaseId, dados }),
    deleteCard:  (cardId)                => api.delete(`/cards/${cardId}`)
};
