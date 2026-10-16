CREATE SCHEMA IF NOT EXISTS painel_tech;

CREATE TABLE IF NOT EXISTS painel_tech.membros (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    email TEXT,
    hub_user_id TEXT,
    capacidade INTEGER,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS painel_tech.projetos (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    descricao TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'fila'
        CHECK (status IN ('fila', 'ativo', 'pausado', 'finalizado')),
    responsavel_id INTEGER REFERENCES painel_tech.membros(id) ON DELETE SET NULL,
    impacto TEXT NOT NULL DEFAULT 'medio'
        CHECK (impacto IN ('baixo', 'medio', 'alto', 'critico')),
    urgencia TEXT NOT NULL DEFAULT 'media'
        CHECK (urgencia IN ('baixa', 'media', 'alta', 'critica')),
    risco TEXT NOT NULL DEFAULT 'medio'
        CHECK (risco IN ('baixo', 'medio', 'alto', 'critico')),
    esforco TEXT NOT NULL DEFAULT 'medio'
        CHECK (esforco IN ('pequeno', 'medio', 'grande', 'muito_grande')),
    ritmo_manual TEXT
        CHECK (ritmo_manual IN ('muito_lento', 'lento', 'fluindo', 'rapido', 'muito_rapido')),
    ritmo_justificativa TEXT,
    data_inicio DATE,
    data_prevista_fim DATE,
    data_fim DATE,
    ordem INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS painel_tech.etapas (
    id SERIAL PRIMARY KEY,
    projeto_id INTEGER NOT NULL REFERENCES painel_tech.projetos(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    ordem INTEGER NOT NULL DEFAULT 0,
    responsavel_id INTEGER REFERENCES painel_tech.membros(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'pendente'
        CHECK (status IN ('pendente', 'em_andamento', 'concluida')),
    data_prevista DATE,
    data_conclusao DATE,
    concluida_em TIMESTAMPTZ,
    observacao TEXT,
    bloqueada BOOLEAN NOT NULL DEFAULT FALSE,
    bloqueio_motivo TEXT,
    bloqueio_descricao TEXT,
    bloqueio_desde DATE,
    bloqueio_responsavel_id INTEGER REFERENCES painel_tech.membros(id) ON DELETE SET NULL,
    dependencia_id INTEGER REFERENCES painel_tech.etapas(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS painel_tech.eventos (
    id SERIAL PRIMARY KEY,
    projeto_id INTEGER NOT NULL REFERENCES painel_tech.projetos(id) ON DELETE CASCADE,
    etapa_id INTEGER REFERENCES painel_tech.etapas(id) ON DELETE SET NULL,
    tipo TEXT NOT NULL,
    descricao TEXT,
    autor_id INTEGER REFERENCES painel_tech.membros(id) ON DELETE SET NULL,
    autor_nome TEXT,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

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

CREATE INDEX IF NOT EXISTS idx_projetos_status ON painel_tech.projetos (status);
CREATE INDEX IF NOT EXISTS idx_etapas_projeto ON painel_tech.etapas (projeto_id, ordem);
CREATE INDEX IF NOT EXISTS idx_eventos_projeto ON painel_tech.eventos (projeto_id, created_at DESC);
