ALTER TABLE painel_tech.eventos ADD COLUMN IF NOT EXISTS autor_id INTEGER REFERENCES painel_tech.membros(id) ON DELETE SET NULL;
ALTER TABLE painel_tech.eventos ADD COLUMN IF NOT EXISTS autor_nome TEXT;
ALTER TABLE painel_tech.eventos ADD COLUMN IF NOT EXISTS payload JSONB;
