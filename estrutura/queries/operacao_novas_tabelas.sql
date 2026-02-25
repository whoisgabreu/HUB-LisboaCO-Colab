-- Tabelas para o Hub de Operação e Lógica de MRR
-- Execute este script no seu banco de dados (PostgreSQL)

-- 1. Tabela para Snapshots de Entregas Mensais (Impacta MRR)
CREATE TABLE IF NOT EXISTS plataforma_geral.operacao_entregas_mensais (
    id SERIAL PRIMARY KEY,
    investidor_email TEXT NOT NULL,
    projeto_pipefy_id INTEGER NOT NULL,
    mes INTEGER NOT NULL CHECK (mes >= 1 AND mes <= 12),
    ano INTEGER NOT NULL,
    entrega_1 BOOLEAN DEFAULT FALSE,
    entrega_2 BOOLEAN DEFAULT FALSE,
    entrega_3 BOOLEAN DEFAULT FALSE,
    entrega_4 BOOLEAN DEFAULT FALSE,
    percentual_calculado NUMERIC(3, 2) DEFAULT 0, -- 0.00 a 1.00
    valor_fee_original NUMERIC(15, 2) DEFAULT 0,
    valor_contribuicao_mrr NUMERIC(15, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(investidor_email, projeto_pipefy_id, mes, ano)
);

-- 2. Tabela para Tarefas (Semanais e Quarter)
CREATE TABLE IF NOT EXISTS plataforma_geral.operacao_tarefas (
    id SERIAL PRIMARY KEY,
    projeto_pipefy_id INTEGER NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('semanal', 'quarter')),
    descricao TEXT NOT NULL,
    concluida BOOLEAN DEFAULT FALSE,
    referencia VARCHAR(20) NOT NULL, -- ex: '2026-W08' para semana ou '2026-Q1' para quarter
    ano INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Comentários para documentação
COMMENT ON COLUMN plataforma_geral.operacao_entregas_mensais.percentual_calculado IS 'Percentual de entrega concluído (0, 0.25, 0.50, 0.75, 1.0)';
COMMENT ON COLUMN plataforma_geral.operacao_entregas_mensais.valor_contribuicao_mrr IS 'Valor do Fee * Percentual da entrega';
