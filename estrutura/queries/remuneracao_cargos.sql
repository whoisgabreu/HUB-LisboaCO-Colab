CREATE TABLE plataforma_geral.remuneracao_cargos (

    -- Campos Fixos
    fixo_cargo TEXT,
    fixo_senioridade TEXT,
    fixo_level TEXT,

    fixo_ticket_medio NUMERIC(15,2),
    fixo_mrr_esperado NUMERIC(15,2),
    fixo_mrr_teto NUMERIC(15,2),
    fixo_remuneracao_fixa NUMERIC(15,2),
    fixo_churn_maximo_percentual NUMERIC(8,7),

    -- Campos Calculados

    calc_media_clientes NUMERIC(15,2)
        GENERATED ALWAYS AS (fixo_mrr_esperado / NULLIF(fixo_ticket_medio,0)) STORED,

    calc_csp_esperado NUMERIC(8,7)
        GENERATED ALWAYS AS (fixo_remuneracao_fixa / NULLIF(fixo_mrr_esperado,0)) STORED,

    calc_mrr_minima NUMERIC(15,2) GENERATED ALWAYS AS (
        (fixo_remuneracao_fixa - (
            fixo_mrr_teto::NUMERIC *
            (
                (fixo_remuneracao_fixa::NUMERIC / NULLIF(fixo_mrr_esperado::NUMERIC,0))
                - (fixo_remuneracao_fixa::NUMERIC / NULLIF(fixo_mrr_teto::NUMERIC,0))
            )
        )) 
        / NULLIF(fixo_remuneracao_fixa::NUMERIC / NULLIF(fixo_mrr_esperado::NUMERIC,0),0)
    ) STORED,

    calc_variavel_csp_teto_percentual NUMERIC(8,7)
        GENERATED ALWAYS AS (
            (fixo_remuneracao_fixa / NULLIF(fixo_mrr_esperado,0))
            - (fixo_remuneracao_fixa / NULLIF(fixo_mrr_teto,0))
        ) STORED,

    calc_variavel_csp_teto_valor NUMERIC(15,2)
        GENERATED ALWAYS AS (
            fixo_mrr_teto *
            (
                (fixo_remuneracao_fixa / NULLIF(fixo_mrr_esperado,0))
                - (fixo_remuneracao_fixa / NULLIF(fixo_mrr_teto,0))
            )
        ) STORED,

    calc_remuneracao_minima NUMERIC(15,2)
        GENERATED ALWAYS AS (
            fixo_remuneracao_fixa
            - (
                fixo_mrr_teto *
                (
                    (fixo_remuneracao_fixa / NULLIF(fixo_mrr_esperado,0))
                    - (fixo_remuneracao_fixa / NULLIF(fixo_mrr_teto,0))
                )
            )
        ) STORED,

    calc_remuneracao_maxima NUMERIC(15,2)
        GENERATED ALWAYS AS (
            fixo_remuneracao_fixa
            +
            (
                fixo_mrr_teto *
                (
                    (fixo_remuneracao_fixa / NULLIF(fixo_mrr_esperado,0))
                    - (fixo_remuneracao_fixa / NULLIF(fixo_mrr_teto,0))
                )
            )
        ) STORED,

    calc_range_total_remuneracao NUMERIC(15,2)
        GENERATED ALWAYS AS (
            (
                fixo_remuneracao_fixa
                +
                (
                    fixo_mrr_teto *
                    (
                        (fixo_remuneracao_fixa / NULLIF(fixo_mrr_esperado,0))
                        - (fixo_remuneracao_fixa / NULLIF(fixo_mrr_teto,0))
                    )
                )
            )
            -
            (
                fixo_remuneracao_fixa
                -
                (
                    fixo_mrr_teto *
                    (
                        (fixo_remuneracao_fixa / NULLIF(fixo_mrr_esperado,0))
                        - (fixo_remuneracao_fixa / NULLIF(fixo_mrr_teto,0))
                    )
                )
            )
        ) STORED,

    calc_percentual_range_remuneracao NUMERIC(8,7)
        GENERATED ALWAYS AS (
            (
                fixo_mrr_teto *
                (
                    (fixo_remuneracao_fixa / NULLIF(fixo_mrr_esperado,0))
                    - (fixo_remuneracao_fixa / NULLIF(fixo_mrr_teto,0))
                )
            )
            / NULLIF(fixo_remuneracao_fixa,0)
        ) STORED,

    calc_churn_maximo_valor NUMERIC(15,2)
        GENERATED ALWAYS AS (
            fixo_churn_maximo_percentual * fixo_mrr_esperado
        ) STORED
);
