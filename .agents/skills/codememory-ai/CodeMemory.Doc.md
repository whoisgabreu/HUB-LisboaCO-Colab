🧠 Skill: Documentação Contínua do Projeto (project_memory.md)

Você é responsável por registrar TODAS as alterações feitas no projeto em um arquivo de documentação contínua chamado:

project_memory.md
🎯 Objetivo

Garantir que qualquer outro agente ou desenvolvedor consiga:

Entender rapidamente o estado atual do projeto
Saber o que já foi feito
Continuar o desenvolvimento sem retrabalho
Evitar perda de contexto
📌 Regras obrigatórias
Toda alteração deve ser documentada imediatamente após ser feita
O arquivo project_memory.md deve ser sempre atualizado, nunca sobrescrito completamente
As informações devem ser claras, objetivas e organizadas
Escrever sempre pensando que outra IA continuará o projeto
Não omitir decisões técnicas importantes

🧱 Estrutura do arquivo

O arquivo deve seguir este padrão:

# 📘 Project Memory

## 🧾 Visão Geral
Resumo curto do projeto e seu objetivo

---

## ⚙️ Stack Atual
- Framework: Django
- Origem: Flask (em migração)
- Banco: (manter o atual, sem alterações)

---

## 📅 Histórico de Alterações

### [DATA] - Título da alteração

**Descrição:**
Explicação clara do que foi feito

**Arquivos afetados:**
- caminho/arquivo.py
- outro/arquivo.py

**Motivo:**
Por que essa alteração foi necessária

**Impacto:**
O que mudou no sistema

---

## 📌 Estado Atual

Descreva como o sistema está funcionando neste momento:
- O que já foi migrado
- O que ainda falta
- Pontos de atenção

---

## 🚧 Próximos Passos

Lista clara do que deve ser feito a seguir

---

## ⚠️ Observações Importantes

- Decisões técnicas relevantes
- Limitações
- Coisas que NÃO devem ser alteradas
🔁 Comportamento esperado da IA

Sempre que realizar qualquer ação:

Executar a alteração no código
Atualizar o project_memory.md
Garantir que a informação seja suficiente para continuidade futura
🧠 Regras de qualidade
Evitar textos vagos como: “ajustes feitos”
Sempre explicar o porquê
Ser técnico, mas direto
Não escrever demais — foco em clareza
💡 Extra (muito importante)

Se houver decisões críticas, adicionar:

**Decisão Técnica:**
Descrição da decisão tomada

**Alternativas consideradas:**
Outras opções avaliadas

**Motivo da escolha:**
Por que essa foi escolhida
🔥 Resultado esperado

Um único arquivo .md que funciona como:

Memória do projeto
Log técnico
Guia de continuidade para humanos e IA