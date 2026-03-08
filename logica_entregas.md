# Documentação Técnica: Lógica de Entregas Mensais e MRR Trabalhado

Este documento descreve o funcionamento atual da lógica de remuneração variável baseada em entregas e MRR (Monthly Recurring Revenue) trabalhado na plataforma HUB Lisboa&CO.

---

## 1. Definição de MRR Trabalhado vs. MRR Total

*   **MRR Total (`fixo_mrr_projeto_total`):** Representa a soma total dos honorários (fees) brutos de todos os projetos ativos vinculados a um investidor (Gestor de Tráfego ou Account). É o potencial máximo de receita sob gestão do profissional.
*   **MRR Trabalhado (`fixo_mrr_atual`):** É o valor real que o investidor "ganhou" no mês, calculado proporcionalmente ao cumprimento das entregas operacionais de cada projeto. É sobre este valor que as metas de Flag (Green/Yellow) e as remunerações variáveis são calculadas.

---

## 2. A Lógica de Entregas Mensais ([OperacaoEntregaMensal](file:///c:/Users/glam-/OneDrive/Documentos/Projetos/ProjetosV4/0.%20HUB%20Lisboa&CO%20Colab%20-%20Antigravity/models.py#237-256))

Cada projeto vinculado a um investidor possui um registro de "Entrega Mensal". Este registro é dividido em **4 Milestones (Checkpoints)**, onde cada um representa **25% (0.25)** do valor total do projeto.

### Milestones de Entrega:
1.  **Entrega 1 - Plano de Mídia (Automatizada):** 
    *   **Gatilho:** Verificação da existência de um registro na tabela `operacao_planos_midia` para o projeto, mês e ano correspondentes.
    *   **Ação:** Se existir pelo menos um plano salvo, a Entrega 1 é marcada como concluída.
2.  **Entrega 2 - Otimizações (Automatizada):**
    *   **Gatilho:** Contagem de registros na tabela `operacao_otimizacoes` para o projeto no respectivo mês.
    *   **Ação:** Se o projeto possuir **4 ou mais otimizações** registradas, a Entrega 2 é marcada como concluída.
3.  **Entrega 3 - (Manual/Task):** Atualmente controlada manualmente ou via interface de tarefas (setup/relatórios), aguardando novas integrações automáticas.
4.  **Entrega 4 - (Manual/Task):** Similar à Entrega 3, representa o fechamento ou entregas finais do ciclo mensal.

---

## 3. Fluxo de Cálculo e Sincronização

A atualização do MRR Trabalhado ocorre através de gatilhos (triggers) nas APIs de operação:

1.  **Gatilho de Atualização:** Sempre que um Plano de Mídia é salvo ou uma Otimização é registrada, a função [atualizar_entregas_automaticas](file:///c:/Users/glam-/OneDrive/Documentos/Projetos/ProjetosV4/0.%20HUB%20Lisboa&CO%20Colab%20-%20Antigravity/app.py#514-565) no [app.py](file:///c:/Users/glam-/OneDrive/Documentos/Projetos/ProjetosV4/0.%20HUB%20Lisboa&CO%20Colab%20-%20Antigravity/app.py) é disparada.
2.  **Cálculo da Contribuição:**
    *   Soma-se os Milestones concluídos (ex: 3 de 4 = 75%).
    *   `percentual_calculado = Milestone_Count * 0.25`.
    *   `valor_contribuicao_mrr = percentual_calculado * fee_original_projeto`.
3.  **Sincronização de Vínculos:** O valor resultante (`valor_contribuicao_mrr`) é salvo no campo `fee_contribuicao` da tabela `investidores_projetos`.
4.  **Agregação do Investidor:** A função [recalculate_investor_mrr](file:///c:/Users/glam-/OneDrive/Documentos/Projetos/ProjetosV4/0.%20HUB%20Lisboa&CO%20Colab%20-%20Antigravity/app.py#70-86) percorre todas as entregas mensais do investidor para aquele mês, soma os valores e atualiza o campo `fixo_mrr_atual` na tabela `investidores_metricas_mensais_novo`.

---

## 4. Impacto nas Métricas e Flags

O **MRR Trabalhado** é o input central para o motor de métricas ([services/remuneracao.py](file:///c:/Users/glam-/OneDrive/Documentos/Projetos/ProjetosV4/0.%20HUB%20Lisboa&CO%20Colab%20-%20Antigravity/services/remuneracao.py)):

*   **Flag Green:** O investidor fica "Verde" se o `mrr_trabalhado` estiver entre o MRR Mínimo e o MRR Teto configurados para seu cargo/nível, e se o Churn estiver dentro do limite.
*   **Remuneração Total:** As fórmulas de remuneração variável no SQL (Generated Columns) utilizam o `fixo_mrr_atual` como base para calcular o CSP (Custo Sobre Projeto) e as variações de Churn.

---

## Resumo para Prompt (Linguagem Executiva):

> "O sistema HUB calcula a remuneração com base em **Entregas Mensais**. Cada projeto tem 4 check-ins mensais (2 de 4 são automatizados: existêcia de Plano de Mídia e execução de no mínimo 4 Otimizações). Cada check-in vale 25% do fee. A soma desses valores ponderados por projeto resulta no **MRR Trabalhado**. Este MRR Trabalhado é o valor que define a performance (Flags) e a remuneração final do profissional, diferenciando-se do MRR Total (potencial bruto)."
