CREATE TABLE IF NOT EXISTS painel_tech.tempos_sessao (
    id SERIAL PRIMARY KEY,
    projeto_id INTEGER NOT NULL REFERENCES painel_tech.projetos(id) ON DELETE CASCADE,
    membro_id INTEGER REFERENCES painel_tech.membros(id) ON DELETE SET NULL,
    inicio TIMESTAMPTZ NOT NULL,
    fim TIMESTAMPTZ,
    segundos INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_tempos_ativo_projeto ON painel_tech.tempos_sessao (projeto_id) WHERE fim IS NULL;
CREATE INDEX IF NOT EXISTS idx_tempos_projeto ON painel_tech.tempos_sessao (projeto_id, fim);