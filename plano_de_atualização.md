📌 PROMPT OFICIAL – ALTERAÇÕES ESTRUTURAIS NO SISTEMA
🚨 REGRA ABSOLUTA (PRÉ-IMPLEMENTAÇÃO)

Antes de realizar qualquer modificação no código:

O agente deve obrigatoriamente gerar um DOCUMENTO TÉCNICO DE ALTERAÇÕES, contendo:

📂 Arquivos que serão alterados

🧠 Regras atuais vs. novas regras

🔁 Fluxos impactados (frontend e backend)

🗄 Impacto em banco de dados (models, migrations, relacionamentos)

🔐 Alterações de permissões

📊 Nova lógica de cálculo do MRR

⚠️ Riscos e possíveis regressões

🧪 Estratégia de testes

🪜 Passo a passo técnico da implementação

🔄 Estratégia de rollback

🚫 Nenhuma alteração pode ser executada antes da validação explícita do documento.

🎯 OBJETIVOS DA IMPLEMENTAÇÃO

Ajustar regras de visibilidade do menu lateral.

Corrigir inconsistências da tela operacao.html.

Implementar entregas mensais automáticas e fixas.

Alterar completamente a lógica do MRR Trabalhado.

Separar responsabilidades entre Account e Gestor de Tráfego.

Garantir consistência entre frontend e backend.

🔐 CONTROLE DE VISIBILIDADE DO MENU LATERAL
✅ Menu "Operação"

Visível apenas para:

Gerência

Account

Gestor de Tráfego

✅ Menu "Criativa"

Visível apenas para:

Gerência

Designer

WebDesigner

✅ Menu "Remuneração"

Visível apenas para:

Gerência

⚠️ As permissões devem ser validadas no backend (middleware/guard) e refletidas no frontend.

🛠 CORREÇÕES NA TELA operacao.html
1️⃣ Plano de Mídia

Problemas:

Dados são salvos no banco mas não são renderizados.

Botão "Adicionar Campanha" não executa ação.

Corrigir:

Fluxo de requisição (POST)

Eventos JS não vinculados

Atualização de estado após persistência

Re-fetch automático após criação

Garantir renderização reativa

2️⃣ Registro de Otimizações

Problema:

Persistido no banco, mas não renderizado na interface.

Corrigir:

Sincronização frontend/backend

Atualização automática após criação

Correção de listagem via API

3️⃣ Links Úteis por Cliente

Implementar tabela ou coluna específica na operacao.html.

Permissões:

Gestor de Tráfego → Pode editar

Account → Pode editar

Gerência → Pode editar

Associar links por cliente e garantir persistência correta.

📊 REESTRUTURAÇÃO COMPLETA DAS ENTREGAS DO MÊS
🚨 NOVA REGRA ESTRUTURAL (OBRIGATÓRIA)

As Entregas do Mês:

❌ Não podem ser preenchidas manualmente

❌ Não podem ser editáveis

❌ Não podem ser excluídas manualmente

✅ Devem ser geradas automaticamente

✅ Devem ser fixas e padronizadas

✅ Devem impactar diretamente o cálculo do MRR Trabalhado

💰 REGRA FINANCEIRA (OBRIGATÓRIA)

Cada colaborador possui:

4 entregas mensais fixas

Cada entrega representa 25% do valor do fee

Totalizando 100% do fee mensal

Fórmula obrigatória:
MRR Trabalhado = (Quantidade de entregas concluídas / 4) * Fee

A lógica deve ser:

Isolada por cargo

Isolada por usuário

Isolada por cliente

Isolada por competência (mês)

Não pode haver impacto cruzado entre cargos.

👤 ENTREGAS FIXAS – ACCOUNT (4)

Devem ser automaticamente concluídas quando:

✅ Check-in
→ Quando houver registro de check-in no mês vigente.

✅ Relatório Mensal do Account
→ Quando o relatório mensal for gerado/publicado.

✅ Planner Monday Semanal
→ Quando houver registro válido das semanas do mês.

✅ Atualização do Forecasting com Metas
→ Quando houver atualização registrada no mês vigente.

⚠️ Não pode depender de ações do Gestor de Tráfego.

👤 ENTREGAS FIXAS – GESTOR DE TRÁFEGO (4)

Devem ser automaticamente concluídas quando:

✅ Plano de Mídia
→ Quando houver criação ou atualização no mês vigente.

✅ Documento de Otimização
→ Quando houver registro de otimização no mês vigente.

✅ Relatório Mensal do Gestor de Tráfego
→ Quando o relatório for gerado/publicado.

✅ Configurações de Conta
→ Quando houver atualização registrada no mês vigente.

⚠️ Não pode depender de ações do Account.

🔒 REGRAS TÉCNICAS OBRIGATÓRIAS

A verificação deve considerar:

Cliente

Mês/competência

Usuário responsável

Cargo do usuário

O sistema deve:

Recalcular automaticamente o MRR ao detectar entrega concluída

Impedir marcação manual

Impedir exclusão manual

Permitir apenas reprocessamento automático

Evitar duplicidade de entregas

Manter histórico imutável de meses fechados

🧠 O DOCUMENTO TÉCNICO DEVE DEFINIR

Se será criada a tabela monthly_deliveries

Estrutura sugerida:

user_id

client_id

role

delivery_type

month

status

completed_at

Estratégia de trigger (event-driven ou recalculo batch)

Estratégia para edição retroativa

Estratégia para evitar inconsistência histórica

Estratégia para recalcular MRR sem afetar meses fechados

Garantia de idempotência no processamento

⚠️ ALTERAÇÃO CRÍTICA

A lógica atual de MRR deve ser completamente revisada e desacoplada.

O MRR Trabalhado do:

Account → depende apenas das 4 entregas do Account

Gestor de Tráfego → depende apenas das 4 entregas do Gestor

Não pode existir dependência cruzada.