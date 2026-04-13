SKILL NAME: AutoArchitect.Scan

DESCRIPTION:
Responsável por analisar profundamente todo o sistema e construir um modelo mental completo da arquitetura, regras de negócio e funcionamento interno, sem gerar documentação final.

---

## OBJETIVO

Criar uma representação interna COMPLETA do sistema que será usada posteriormente pela AutoArchitect.Doc.

---

## MODO DE OPERAÇÃO

Quando esta skill for ativada:

1. Assuma acesso total ao código-fonte
2. NÃO gere documentação final
3. NÃO gere Markdown estruturado
4. Foque exclusivamente em entender o sistema
5. Construa um modelo mental completo e consistente

---

## PROCESSO DE ANÁLISE (OBRIGATÓRIO)

### 1. Estrutura do Projeto
- Mapear diretórios
- Identificar organização (monolito, microserviços, etc.)

---

### 2. Tecnologias
- Linguagens
- Frameworks
- Bibliotecas principais
- Ferramentas externas

---

### 3. Identificação de Camadas
- Frontend
- Backend
- Banco de dados
- Integrações externas

---

### 4. Backend
- Estrutura de camadas
- Controllers, services, repositories
- Endpoints
- Autenticação e autorização

---

### 5. Frontend
- Componentes
- Páginas
- Rotas
- Gerenciamento de estado
- Integração com API

---

### 6. Banco de Dados
- Tabelas
- Relacionamentos
- Índices

---

### 7. Regras de Negócio
- Identificar regras explícitas e implícitas
- Validar dependências entre regras

---

### 8. Cálculos e Lógica Crítica (PRIORIDADE ALTA)
- Localizar fórmulas
- Entender dependências
- Mapear execução
- Identificar impactos

---

### 9. Fluxos do Sistema
- Mapear fluxos principais
- Sequência completa (frontend → backend → banco)

---

### 10. Pontos Críticos
- Gargalos
- Partes sensíveis
- Possíveis falhas

---

## RESULTADO ESPERADO

- Um modelo mental completo do sistema
- Todas as relações entre componentes compreendidas
- Nenhuma saída estruturada final ainda

---

## REGRAS

- NÃO gerar documentação final
- NÃO simplificar análise
- NÃO pular etapas
- Priorizar profundidade máxima