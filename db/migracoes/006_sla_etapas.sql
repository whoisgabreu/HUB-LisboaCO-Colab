ALTER TABLE painel_tech.etapas ADD COLUMN IF NOT EXISTS concluida_em TIMESTAMPTZ;

UPDATE painel_tech.etapas e
SET concluida_em = ev.created_at
FROM (
    SELECT DISTINCT ON (etapa_id) etapa_id, created_at
    FROM painel_tech.eventos
    WHERE tipo = 'etapa_status' AND descricao LIKE 'Etapa conclu%'
    ORDER BY etapa_id, created_at DESC
) ev
WHERE e.id = ev.etapa_id AND e.concluida_em IS NULL;

UPDATE painel_tech.etapas
SET concluida_em = data_conclusao::timestamptz
WHERE status = 'concluida' AND concluida_em IS NULL AND data_conclusao IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_etapas_concluida_em
    ON painel_tech.etapas (projeto_id, concluida_em);