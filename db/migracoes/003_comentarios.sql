CREATE TABLE IF NOT EXISTS painel_tech.comentarios (
    id SERIAL PRIMARY KEY,
    projeto_id INTEGER REFERENCES painel_tech.projetos(id) ON DELETE CASCADE,
    etapa_id INTEGER REFERENCES painel_tech.etapas(id) ON DELETE CASCADE,
    autor_nome TEXT,
    texto TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_comentarios_projeto ON painel_tech.comentarios (projeto_id, created_at);
CREATE INDEX IF NOT EXISTS idx_comentarios_etapa ON painel_tech.comentarios (etapa_id, created_at);