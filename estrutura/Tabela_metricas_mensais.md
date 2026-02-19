Churn Máximo % = NUMERIC(5,4)
CSP Esperado = NUMERIC(5,4)
Remuneração Fixa = NUMERIC(15,2)


Churn Real % = MRR Atual/Churn Atual
Delta Churn % = Churn Máximo %(ja existe na table de Remuneração) - Churn Real %
Delta Churn $ = Delta Churn % * MRR Atual
Variavel Churn = Delta Churn $ * CSP Esperado(ja existe na table de Remuneração)
Delta CSP = CSP Esperado(ja existe na table de Remuneração) - (Remuneração Fixa(ja existe na table de Remuneração)/MRR Atual)
Variavel CSP = Delta CSP * MRR Atual
Variavel Total = Variavel CSP + Variavel Churn
Remuneração Total = Remuneração Fixa(ja existe na table de Remuneração) + Variavel Total