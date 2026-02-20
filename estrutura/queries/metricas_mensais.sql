CREATE TABLE plataforma_geral.investidores_metricas_mensais_novo (
    -- Campos fixos que serão inseridos
        -- Novas colunas
    mes INT,
    ANO INT,
    email_investidor TEXT,
    detalhes JSONB,

    cargo TEXT,
    senioridade TEXT,
    level TEXT,
    
    fixo_mrr_atual NUMERIC(15,2),
    fixo_churn_atual NUMERIC(15,2),
    fixo_remuneracao_fixa NUMERIC(15,2),
    fixo_csp_esperado NUMERIC(8,7),
    fixo_churn_maximo_percentual NUMERIC(8,7),
    fixo_mrr_minimo NUMERIC(15,2), -- novo
    fixo_mrr_esperado NUMERIC(15,2), -- novo
    fixo_mrr_teto NUMERIC(15,2), -- novo
    fixo_churn_maximo_valor NUMERIC(15,2), -- novo

    -- Colunas calculadas

    -- 1. Churn Real %
    calc_churn_real_percentual NUMERIC(8,7)
        GENERATED ALWAYS AS (fixo_churn_atual / NULLIF(fixo_mrr_atual,0)) STORED,

    -- 2. Delta Churn %
    calc_delta_churn_percentual NUMERIC(8,7)
        GENERATED ALWAYS AS (fixo_churn_maximo_percentual - (fixo_churn_atual / NULLIF(fixo_mrr_atual,0))) STORED,

    -- 3. Delta Churn $ 
    calc_delta_churn_valor NUMERIC(15,2)
        GENERATED ALWAYS AS ((fixo_churn_maximo_percentual - (fixo_churn_atual / NULLIF(fixo_mrr_atual,0))) * fixo_mrr_atual) STORED,

    -- 4. Variável Churn
    calc_variavel_churn NUMERIC(15,2)
        GENERATED ALWAYS AS (((fixo_churn_maximo_percentual - (fixo_churn_atual / NULLIF(fixo_mrr_atual,0))) * fixo_mrr_atual) * fixo_csp_esperado) STORED,

    -- 5. Delta CSP
    calc_delta_csp NUMERIC(8,7)
        GENERATED ALWAYS AS (fixo_csp_esperado - (fixo_remuneracao_fixa / NULLIF(fixo_mrr_atual,0))) STORED,

    -- 6. Variável CSP
    calc_variavel_csp NUMERIC(15,2)
        GENERATED ALWAYS AS ((fixo_csp_esperado - (fixo_remuneracao_fixa / NULLIF(fixo_mrr_atual,0))) * fixo_mrr_atual) STORED,

    -- 7. Variável Total
    calc_variavel_total NUMERIC(15,2)
        GENERATED ALWAYS AS (
            ((fixo_csp_esperado - (fixo_remuneracao_fixa / NULLIF(fixo_mrr_atual,0))) * fixo_mrr_atual) +
            (((fixo_churn_maximo_percentual - (fixo_churn_atual / NULLIF(fixo_mrr_atual,0))) * fixo_mrr_atual) * fixo_csp_esperado)
        ) STORED,

    -- 8. Remuneração Total
    calc_remuneracao_total NUMERIC(15,2)
        GENERATED ALWAYS AS (
            fixo_remuneracao_fixa +
            ((fixo_csp_esperado - (fixo_remuneracao_fixa / NULLIF(fixo_mrr_atual,0))) * fixo_mrr_atual) +
            (((fixo_churn_maximo_percentual - (fixo_churn_atual / NULLIF(fixo_mrr_atual,0))) * fixo_mrr_atual) * fixo_csp_esperado)
        ) STORED



);
