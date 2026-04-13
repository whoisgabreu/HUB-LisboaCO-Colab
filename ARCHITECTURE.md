# HUB Lisboa&CO — Documentação Técnica Completa

> Documento gerado automaticamente pela skill **AutoArchitect.Doc** em 13/04/2026.
> Fonte de verdade: análise completa do código-fonte (AutoArchitect.Scan).

---

## Sumário

1. [Visão Geral do Sistema](#1-visão-geral-do-sistema)
2. [Arquitetura do Sistema](#2-arquitetura-do-sistema)
3. [Tecnologias Utilizadas](#3-tecnologias-utilizadas)
4. [Setup do Ambiente](#4-setup-do-ambiente)
5. [Frontend](#5-frontend)
6. [Backend](#6-backend)
7. [Banco de Dados](#7-banco-de-dados)
8. [Fluxos do Sistema](#8-fluxos-do-sistema)
9. [Regras de Negócio](#9-regras-de-negócio)
10. [Pontos Críticos](#10-pontos-críticos)
11. [Guia de Recriação](#11-guia-de-recriação)

---

## 1. Visão Geral do Sistema

### 1.1 Descrição

O **HUB Lisboa&CO** é uma plataforma web interna de gestão operacional e financeira para a franquia **Lisboa&CO** da rede **V4 Company**. O sistema centraliza a gestão de projetos (clientes), investidores (colaboradores), operações diárias, e o cálculo de remuneração variável baseada em performance.

### 1.2 Objetivo de Negócio

- Substituir fluxos manuais e automações legadas (N8N + planilhas) por uma plataforma unificada.
- Calcular automaticamente a **remuneração variável** dos investidores com base em MRR (Monthly Recurring Revenue), churn e entregas operacionais.
- Oferecer visibilidade em tempo real da performance individual e coletiva.
- Implementar controle de acesso por cargo e posição hierárquica.

### 1.3 Funcionalidades Principais

| Módulo | Descrição |
|--------|-----------|
| **Autenticação** | Login com hash de senha (Werkzeug), gestão de sessão Flask, tokens de auth |
| **Home / Dashboard** | KPIs operacionais (MRR total, clientes, squads), métricas pessoais de remuneração |
| **Hub de Projetos** | CRUD de projetos (Ativos, One-time, Inativos), vinculação de investidores, edição com histórico |
| **Operação** | Gestão de tarefas semanais/trimestrais, plano de mídia, otimizações, check-ins, links úteis |
| **Remuneração** | Dashboard gerencial com flags (Green/Yellow/Red/Black), histórico mensal, detalhamento por investidor |
| **Ranking** | Painel público de performance: dias sem churn, MRR, clientes ativos |
| **Gerenciar Usuários** | CRUD de investidores (Admin only), reset de senha |
| **Hub CS/CX** | Dashboard de Customer Success: MRR total, NPS, LTV por cliente, health score |
| **Criativa** | Módulo de design (em desenvolvimento, acesso restrito) |
| **Cockpit** | Página placeholder para ferramentas futuras de gestão |

### 1.4 Arquitetura Geral

O sistema é um **monolito server-side rendered** usando Flask + Jinja2 no backend e Vanilla JS no frontend. Não há framework SPA. Toda navegação é baseada em rotas Flask que renderizam templates HTML completos, com chamadas AJAX (fetch API) para operações CRUD assíncronas.

---

## 2. Arquitetura do Sistema

### 2.1 Estrutura Geral

```
┌─────────────────────────────────────────────────────────────┐
│                       BROWSER (Cliente)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐ │
│  │ HTML/CSS │  │ Vanilla  │  │ Font     │  │ Google      │ │
│  │ (Jinja2) │  │ JS       │  │ Awesome  │  │ Fonts       │ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────────┘ │
└─────────────────────────────┬───────────────────────────────┘
                              │ HTTP (GET/POST/PUT/DELETE)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FLASK APPLICATION (app.py)                │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │ Rotas /     │  │ Decorators   │  │ Helpers            │ │
│  │ Páginas     │  │ check_session│  │ _projeto_to_dict   │ │
│  │ APIs REST   │  │ check_access │  │ _agrupar_por_cli   │ │
│  └──────┬──────┘  └──────────────┘  └────────────────────┘ │
│         │                                                   │
│  ┌──────▼─────────────────────────────────────────────────┐ │
│  │                   SERVICES LAYER                       │ │
│  │  ┌─────────────────┐  ┌──────────────────────────────┐ │ │
│  │  │ remuneracao.py   │  │ projeto_participacao_service │ │ │
│  │  │ (cálculo mensal) │  │ (proporcional + histórico)   │ │ │
│  │  └─────────────────┘  └──────────────────────────────┘ │ │
│  │  ┌─────────────────┐  ┌──────────────────────────────┐ │ │
│  │  │ delivery_engine  │  │ delivery_service             │ │ │
│  │  │ (motor entregas) │  │ (helper entregas E4/E5)      │ │ │
│  │  └─────────────────┘  └──────────────────────────────┘ │ │
│  │  ┌─────────────────┐  ┌──────────────────────────────┐ │ │
│  │  │ operacao_service │  │ currency.py                  │ │ │
│  │  │ (projetos op.)   │  │ (USD→BRL AwesomeAPI)         │ │ │
│  │  └─────────────────┘  └──────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│         │                                                   │
│  ┌──────▼──────┐  ┌───────────────┐                        │
│  │ SQLAlchemy  │  │ APScheduler   │                        │
│  │ ORM 2.0    │  │ (cron diário  │                        │
│  │            │  │  00:00)        │                        │
│  └──────┬──────┘  └───────────────┘                        │
└─────────┼───────────────────────────────────────────────────┘
          │ psycopg2 (TCP 5432)
          ▼
┌─────────────────────────────────────────────────────────────┐
│              POSTGRESQL (Schema: plataforma_geral)           │
│  ┌────────────────┐  ┌──────────────────────────────────┐   │
│  │ investidores   │  │ investidores_metricas_mensais_novo│   │
│  │ auth           │  │ remuneracao_cargos               │   │
│  │ projetos_*     │  │ investidores_projetos            │   │
│  │ operacao_*     │  │ monthly_deliveries               │   │
│  └────────────────┘  └──────────────────────────────────┘   │
│                                                             │
│  Colunas GENERATED ALWAYS AS STORED:                        │
│  calc_churn_real_percentual, calc_delta_churn_percentual,   │
│  calc_delta_churn_valor, calc_variavel_churn,               │
│  calc_delta_csp, calc_variavel_csp, calc_variavel_total,    │
│  calc_remuneracao_total                                     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Comunicação entre Camadas

| Camada Origem | Camada Destino | Mecanismo |
|---------------|---------------|-----------|
| Browser → Flask | HTTP GET/POST/PUT/DELETE | `fetch()` API + Forms |
| Flask → Templates | Jinja2 render_template | Variáveis de contexto |
| Flask → Services | Chamada direta (Python import) | Funções e métodos estáticos |
| Services → Database | SQLAlchemy ORM 2.0 | Session context manager |
| Flask → API Externa | HTTP GET | `requests` (AwesomeAPI USD→BRL) |
| APScheduler → Services | Chamada direta (cron) | `calcular_metricas_mensais()` diário |

### 2.3 Fluxo de Dados

```
REQUISIÇÃO HTTP
     │
     ▼
 check_session (decorator) → redireciona para /login se não autenticado
     │
     ▼
 check_access (decorator) → verifica funcao/posicao do usuário
     │
     ▼
 Route Handler (app.py) → monta dados via Session() do SQLAlchemy
     │
     ▼
 render_template() → Jinja2 processa HTML com dados do backend
     │
     ▼
 Browser renderiza → JavaScript (Vanilla) gerencia interatividade
     │
     ▼
 AJAX (fetch) → APIs REST em /api/* para operações CRUD
```

---

## 3. Tecnologias Utilizadas

### 3.1 Linguagens

| Linguagem | Uso |
|-----------|-----|
| **Python 3.x** | Backend (Flask, SQLAlchemy, services) |
| **JavaScript (ES6+)** | Frontend interatividade (Vanilla, sem framework) |
| **HTML5** | Estrutura das páginas (Jinja2 templates) |
| **CSS3** | Estilização (Vanilla CSS, sem preprocessor) |
| **SQL** | Queries diretas e colunas GENERATED no PostgreSQL |

### 3.2 Frameworks

| Framework | Versão | Uso |
|-----------|--------|-----|
| **Flask** | 3.1.3 | Web framework principal |
| **SQLAlchemy** | 2.0.46 | ORM para PostgreSQL |
| **Jinja2** | 3.1.6 | Template engine (server-side) |
| **Flask-APScheduler** | 1.13.1 | Agendamento de tarefas (cron) |

### 3.3 Bibliotecas Principais

| Biblioteca | Uso |
|------------|-----|
| **Werkzeug** 3.1.6 | Hash de senhas (`generate_password_hash`, `check_password_hash`) |
| **psycopg2-binary** 2.9.11 | Driver PostgreSQL |
| **python-dotenv** 1.2.1 | Carregamento de variáveis de ambiente (.env) |
| **requests** 2.32.5 | Chamadas HTTP para API de câmbio |
| **gunicorn** 25.1.0 | Servidor WSGI para produção |

### 3.4 Banco de Dados

- **PostgreSQL** (versão não especificada no projeto, compatível com JSONB e GENERATED columns)
- Schema: `plataforma_geral`
- Conexão: `postgresql+psycopg2://` via variáveis de ambiente
- Pool: `pool_pre_ping=True`, `pool_recycle=300`

### 3.5 Ferramentas Externas

| Ferramenta | Uso |
|------------|-----|
| **AwesomeAPI** (`economia.awesomeapi.com.br`) | Cotação USD→BRL em tempo real (cache 1h) |
| **Font Awesome** 6.4/6.5 | Ícones na interface |
| **Google Fonts (Poppins)** | Tipografia |
| **N8N** (legado) | Fluxos de automação anteriores (Autenticação, CRUD, Remuneração) — migrados para Python |

---

## 4. Setup do Ambiente

### 4.1 Pré-requisitos

- Python 3.10+
- PostgreSQL (com schema `plataforma_geral` já provisionado)
- Git
- Virtualenv (recomendado)

### 4.2 Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/whoisgabreu/HUB-LisboaCO-Colab.git
cd HUB-LisboaCO-Colab

# 2. Crie e ative o virtualenv
python -m venv .venv

# Windows:
.\.venv\Scripts\activate

# Linux/Mac:
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt
```

### 4.3 Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```env
DB_HOST=<endereço do servidor PostgreSQL>
DB_PORT=<porta, geralmente 5432>
DB_DATABASE=<nome do banco de dados>
DB_USERNAME=<usuário do banco>
DB_PASSWORD=<senha do banco>
```

Existe também um arquivo `externo.env` para configuração de ambiente externo (produção/staging).

### 4.4 Execução Local

```bash
# Ativa o virtualenv (se ainda não ativo)
.\.venv\Scripts\activate

# Executa a aplicação
python app.py
```

A aplicação inicia em `http://0.0.0.0:5000` com `debug=True`.

O sistema automaticamente:
1. Cria tabelas inexistentes via `Base.metadata.create_all(engine)`
2. Inicia o APScheduler (job de remuneração diário à 00:00)

### 4.5 Deploy (Produção)

```bash
gunicorn app:app --bind 0.0.0.0:5000 --workers 4
```

> **Nota**: O `gunicorn` está listado no `requirements.txt` mas não há Dockerfile ou configuração de container no repositório.

---

## 5. Frontend

### 5.1 Estrutura de Pastas

```
templates/
├── components/
│   ├── header.html            # Header global (logo, user info, dropdown)
│   ├── sidebar.html           # Navegação lateral (RBAC via Jinja2)
│   ├── icon_title.html        # Favicon
│   ├── loader.html            # Spinner de carregamento
│   ├── modal-configuracoes.html  # Modal de perfil/aparência/senha
│   └── up-button.html         # Botão "voltar ao topo"
├── login.html                 # Página de login
├── index.html                 # Home / Dashboard pessoal
├── hub-projetos.html          # Gestão de projetos
├── hub-remuneracao.html       # Dashboard de remuneração (Gerência)
├── operacao.html              # Operações (tarefas, plano, otimizações, checkin, links)
├── criativa.html              # Módulo de design
├── gerenciar-usuarios.html    # Admin: CRUD de usuários
├── painel-ranking.html        # Ranking de investidores
├── painel-atribuicao.html     # Painel de atribuição (placeholder)
├── vendas.html                # Vendas (placeholder)
├── cockpit.html               # Cockpit (placeholder)
├── cs_dashboard.html          # Dashboard CS/CX
└── cs_client_detail.html      # Detalhe do cliente (CS/CX)

static/
├── js/
│   ├── app.js                 # Sidebar, dropdown, utilities globais (Utils.formatBRL, showToast)
│   ├── home.js                # Lógica da Home (KPIs, atalhos)
│   ├── hub-projetos.js        # CRUD de projetos, modal de edição, vinculação
│   ├── operacao.js            # Tabs, tarefas, plano de mídia, otimizações, checkin, links
│   ├── remuneracao.js         # Filtros, cards de investidores, modal de detalhes
│   ├── ranking.js             # Cards de ranking, animações
│   ├── gerenciar-usuarios.js  # Tabela de usuários, modal CRUD
│   ├── criativa.js            # Lógica do módulo criativa
│   ├── configuracoes.js       # Modal de configurações (perfil, tema, senha)
│   ├── login.js               # Toggle de senha visível
│   ├── tema.js                # Alternância de tema claro/escuro
│   └── placeholders.js        # Textos placeholder para páginas em construção
├── style/
│   ├── styles.css             # CSS principal (97KB, ~3000+ linhas)
│   ├── tema-claro.css         # Override de variáveis para tema claro
│   ├── hub-projetos.css       # Estilos específicos do hub de projetos
│   ├── login.css              # Estilos da página de login
│   ├── ranking.css            # Estilos do painel de ranking
│   ├── criativa.css           # Estilos do módulo criativa
│   └── gerenciar-usuarios.css # Estilos do gerenciar usuários
└── images/
    ├── profile_pictures/      # Fotos de perfil dos investidores
    ├── v4-logo.png            # Logo V4
    └── V4.png                 # Banner V4
```

### 5.2 Componentes Reutilizáveis

| Componente | Arquivo | Descrição |
|------------|---------|-----------|
| **Header** | `components/header.html` | Logo, nome/cargo do usuário via sessão, dropdown (Perfil, Aparência, Configurações, Sair) |
| **Sidebar** | `components/sidebar.html` | Navegação lateral com RBAC via Jinja2 (`session.posicao`, `session.funcao`, `session.nivel_acesso`) |
| **Loader** | `components/loader.html` | Animação de carregamento fullscreen |
| **Modal Configurações** | `components/modal-configuracoes.html` | 3 abas: Perfil (foto, info), Aparência (tema), Senha |
| **Up Button** | `components/up-button.html` | Botão flutuante "voltar ao topo" |

### 5.3 Rotas (páginas)

| Rota | Template | Acesso |
|------|----------|--------|
| `/login` | `login.html` | Público |
| `/` | `index.html` | Autenticado |
| `/hub-projetos` | `hub-projetos.html` | Autenticado |
| `/operacao` | `operacao.html` | Account, Gestor de Tráfego, Gerência, Sócio |
| `/hub-remuneracao` | `hub-remuneracao.html` | Gerência, Sócio |
| `/gerenciar-usuarios` | `gerenciar-usuarios.html` | Admin (`nivel_acesso`) |
| `/painel-ranking` | `painel-ranking.html` | Autenticado |
| `/criativa` | `criativa.html` | Designer, WebDesigner (atualmente restrito a 2 e-mails) |
| `/hub-cs-cx` | `cs_dashboard.html` / `cs_client_detail.html` | Gerência, Sócio, Account, CS (restrito a 2 e-mails) |
| `/painel-atribuicao` | `painel-atribuicao.html` | Autenticado (placeholder) |
| `/vendas` | `vendas.html` | Autenticado (placeholder) |
| `/cockpit` | `cockpit.html` | Autenticado (placeholder, restrito a 2 e-mails) |

### 5.4 Gerenciamento de Estado

O frontend **não utiliza gerenciamento de estado centralizado** (sem Redux, Vuex, etc.). O estado é gerido por:

1. **Sessão Flask (server-side)**: `session["nome"]`, `session["email"]`, `session["funcao"]`, `session["posicao"]`, `session["squad"]`, `session["nivel_acesso"]`, `session["profile_picture"]`.
2. **`window.APP_CONFIG`**: Objeto JS injetado no template com `userEmail`, `userAccessLevel`, `userToken`.
3. **`localStorage`**: Tema (claro/escuro), estado da sidebar (colapsada/expandida).
4. **Variáveis globais JS**: Dados injetados via `<script>` inline no template (ex: `operationalData`, `my_remuneracao`).

### 5.5 Integração com API

Todas as chamadas do frontend para o backend usam `fetch()` nativo:

```javascript
// Padrão de chamada
fetch('/api/operacao/tarefas', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
})
.then(res => res.json())
.then(data => { /* atualiza DOM */ })
.catch(err => showToast('Erro', 'error'));
```

Utilitários globais disponíveis em todas as páginas:
- `Utils.formatBRL(value)` → Formata valor em Reais (pt-BR)
- `Utils.formatNumber(value)` → Formata número com separadores
- `showToast(message, type)` → Notificação toast (success/error/info)

### 5.6 Regras de Negócio no Frontend

- **RBAC na Sidebar**: Menus são condicionalmente renderizados via Jinja2 com base em `session.posicao`, `session.funcao` e `session.nivel_acesso`.
- **Flag de Remuneração**: A tabela de histórico exibe cores (Green/Yellow/Red/Black) baseadas em `yellow_streak` e `green_streak`.
- **Remuneração Total com clamp**: Valor final é limitado entre `rem_min` e `rem_max` tanto no backend quanto exibido no template.
- **Entregas automáticas são read-only**: O frontend não permite marcação manual de entregas (endpoint retorna 403).

---

## 6. Backend

### 6.1 Estrutura

```
app.py                  # 1737 linhas — Ponto de entrada, todas as rotas e APIs
database.py             # Configuração do engine e Session SQLAlchemy
models.py               # 14 modelos ORM (tabelas do banco)
services/
├── remuneracao.py      # Cálculo mensal de métricas (MRR, churn, flags)
├── projeto_participacao_service.py  # Proporcional de MRR + histórico JSONB
├── delivery_engine.py  # Motor de automação de entregas E4/E5
├── delivery_service.py # Helper de entregas com recálculo MRR
├── operacao_service.py # Busca de projetos para tela de operação
└── currency.py         # Serviço de cotação USD→BRL (AwesomeAPI)
```

### 6.2 Camadas

| Camada | Responsabilidade |
|--------|-----------------|
| **Rotas (app.py)** | Receber requisições HTTP, validar sessão/acesso, chamar services, retornar HTML ou JSON |
| **Services** | Lógica de negócio isolada (cálculos, automações, integrações externas) |
| **Models (models.py)** | Mapeamento ORM das tabelas PostgreSQL |
| **Database (database.py)** | Configuração de conexão, engine e session factory |

### 6.3 Endpoints Detalhados

#### 6.3.1 Autenticação

| Método | Rota | Descrição |
|--------|------|-----------|
| GET/POST | `/login` | Login com e-mail + senha (hash Werkzeug). Gera token, popula sessão. |
| GET/POST | `/logout` | Limpa sessão e redireciona para login. |
| POST | `/alterar-senha` | Altera senha do usuário logado (verifica senha atual). |
| POST | `/upload-profile-picture` | Upload de foto de perfil (.png). |

#### 6.3.2 Páginas (HTML)

| Método | Rota | Acesso | Descrição |
|--------|------|--------|-----------|
| GET | `/` | Autenticado | Home: KPIs operacionais + métricas pessoais de remuneração |
| GET | `/hub-projetos` | Autenticado | Lista projetos ativos, one-time e inativos (filtro por squad) |
| GET | `/hub-remuneracao` | Gerência | Dashboard de remuneração de todos os investidores |
| GET | `/operacao` | Account, GT | Lista projetos operados pelo usuário |
| GET | `/gerenciar-usuarios` | Admin | CRUD de investidores |
| GET | `/painel-ranking` | Autenticado | Ranking de investidores |
| GET | `/hub-cs-cx` | Gerência, Account, CS | Dashboard CS/CX ou detalhe do cliente |
| GET | `/criativa` | Designer, WebDesigner | Módulo de design |
| GET | `/cockpit` | Autenticado | Placeholder |

#### 6.3.3 APIs REST (/api)

**Operação — Tarefas**

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/operacao/tarefas/<pipefy_id>` | Lista tarefas (filtro: tipo, referência) |
| POST | `/api/operacao/tarefas` | Cria/atualiza tarefa. Dispara `DeliveryService.checkAndComplete()` |

**Operação — Entregas**

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/operacao/entregas/<pipefy_id>/<mes>/<ano>` | Entregas manuais (legado) |
| POST | `/api/operacao/entregas` | **BLOQUEADO** (retorna 403). Entregas são 100% automáticas. |
| GET | `/api/operacao/monthly-deliveries/<pipefy_id>/<mes>/<ano>` | Entregas automáticas do mês (read-only) |

**Operação — Plano de Mídia**

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/operacao/plano-midia/<pipefy_id>/<mes>/<ano>` | Busca plano de mídia (tenta próprio usuário, depois qualquer) |
| POST | `/api/operacao/plano-midia` | Cria/atualiza plano. Dispara delivery engine. |

**Operação — Otimizações**

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/operacao/otimizacoes/<pipefy_id>` | Lista otimizações (Gerência vê todas, outros veem as suas) |
| POST | `/api/operacao/otimizacao` | Registra nova otimização. Dispara delivery engine. |

**Operação — Check-ins**

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/operacao/checkins/<pipefy_id>` | Lista check-ins do projeto |
| POST | `/api/operacao/checkin` | Registra check-in semanal. Dispara delivery engine. |

**Operação — Links Úteis**

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/operacao/links/<pipefy_id>` | Lista links úteis do projeto |
| POST | `/api/operacao/links` | Cria novo link |
| DELETE | `/api/operacao/links/<link_id>` | Remove link |

**Projetos**

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/projetos/listar` | Lista projetos (ativos + onetime + inativos) filtrados por squad |
| PUT | `/api/projetos/<pipefy_id>` | Atualiza projeto + sincroniza vínculos + registra histórico. (Gerência) |
| GET | `/api/projetos/<pipefy_id>/vinculos` | Lista investidores vinculados ao projeto |
| POST | `/api/projetos/vincular` | Vincula investidor a projeto (Gerência) |

**Admin**

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/admin/usuarios` | Lista todos os usuários (Admin) |
| POST | `/api/admin/usuarios` | Cria novo usuário (Admin) |
| PUT | `/api/admin/usuarios/<email>` | Atualiza usuário (Admin) |
| POST | `/api/admin/usuarios/reset-password` | Reset de senha (Admin) |
| GET | `/api/admin/investidores-ativos` | Lista investidores ativos para vinculação (Gerência) |

**Remuneração**

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/remuneracao/processar` | Dispara cálculo de métricas do mês atual |

**Ranking**

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/ranking` | Dados de ranking: dias sem churn, MRR, flag, clientes |

### 6.4 Validações

- **Sessão**: Decorator `check_session` verifica se `nome` está na sessão Flask.
- **Acesso por Cargo**: Decorator `check_access(roles)` verifica `funcao` e `posicao` do usuário. Gerência e Sócio têm acesso a quase tudo via `is_high_level`.
- **Admin**: Verificação direta de `session.nivel_acesso == "Admin"` para rotas de gestão de usuários.
- **Meses Fechados**: `delivery_engine.py` e `delivery_service.py` bloqueiam recálculo para meses anteriores ao corrente.

### 6.5 Autenticação

1. Usuário submete e-mail + senha via form POST em `/login`.
2. Backend busca `Investidor` por e-mail.
3. Verifica se `ativo == True`.
4. Compara hash de senha com `check_password_hash`.
5. Gera token aleatório (`os.urandom(10).hex()`).
6. Faz UPSERT na tabela `auth` com o novo token.
7. Popula sessão Flask com `nome`, `email`, `token`, `funcao`, `posicao`, `senioridade`, `squad`, `nivel_acesso`, `profile_picture`.
8. Redireciona para `/` (Home).

> **Nota**: Não há JWT, OAuth, ou renovação de token. A sessão é gerida inteiramente pelo Flask (`app.secret_key` é gerado aleatoriamente a cada reinício da aplicação).

### 6.6 Scheduler (APScheduler)

- **Job**: `do_remuneracao_daily`
- **Trigger**: Cron diário às 00:00
- **Ação**: Executa `calcular_metricas_mensais()` + `ProjetoParticipacaoService.sincronizar_remuneracao()` para o mês/ano corrente.

---

## 7. Banco de Dados

Schema: **`plataforma_geral`** (PostgreSQL)

### 7.1 Tabela: `investidores`

> Representa os colaboradores (investidores) da franquia.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | INTEGER | **PK**. ID sequencial. |
| `nome` | VARCHAR(100) | Nome completo |
| `email` | VARCHAR(50) | E-mail corporativo (usado como identificador lógico) |
| `funcao` | VARCHAR(50) | Cargo: Account, Gestor de Tráfego, Designer, WebDesigner, Desenvolvedor |
| `senioridade` | VARCHAR(50) | Nível de experiência (ex: Junior, Pleno, Senior) |
| `squad` | VARCHAR(100) | Squad atribuído (Shark, Tigers, Strike Force, Gerência) |
| `senha` | VARCHAR(250) | Hash Werkzeug da senha |
| `nivel_acesso` | VARCHAR(10) | "Admin" ou "Usuário" |
| `ativo` | BOOLEAN | Se o investidor pode fazer login |
| `cpf` | VARCHAR(11) | CPF (não utilizado na lógica atual) |
| `telefone` | VARCHAR(15) | Telefone (não utilizado na lógica atual) |
| `nivel` | TEXT | Level (L1, L2, L3...) |
| `profile_picture` | VARCHAR(250) | Filename da foto de perfil |
| `posicao` | VARCHAR(250) | Posição hierárquica: Operação, Gerência, Meio, Sócio |

**Relacionamentos**: Referenciado por `investidores_projetos`, `auth`, `investidores_metricas_mensais_novo`, `monthly_deliveries`.

---

### 7.2 Tabela: `auth`

> Tokens de autenticação (modelo UPSERT).

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | INTEGER | Autoincrement |
| `email` | VARCHAR(50) | **PK**. FK → investidores.email (lógico) |
| `token` | VARCHAR(30) | Token gerado no login |

---

### 7.3 Tabela: `projetos_ativos`

> Projetos recorrentes ativos.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `pipefy_id` | INTEGER | **PK**. ID vindo do Pipefy (sistema legado) |
| `id` | INTEGER | ID secundário |
| `nome` | VARCHAR(250) | Nome do cliente |
| `documento` | VARCHAR(250) | CNPJ/CPF |
| `fee` | INTEGER | Honorário mensal (em inteiro, unidade da moeda) |
| `moeda` | VARCHAR(6) | "BRL" ou "USD" |
| `squad_atribuida` | VARCHAR(20) | Squad responsável |
| `produto_contratado` | VARCHAR(250) | Produto V4 contratado |
| `data_de_inicio` | DATE | Data de início do projeto |
| `cohort` | VARCHAR(100) | Cohort de entrada |
| `meta_account_id` | VARCHAR(100) | ID da conta Meta Ads |
| `google_account_id` | VARCHAR(100) | ID da conta Google Ads |
| `fase_do_pipefy` | VARCHAR(100) | Fase atual no Pipefy |
| `url_webhook_gchat` | VARCHAR(250) | Webhook Google Chat |
| `step` | VARCHAR(15) | Fase atual (Pipeline) |
| `informacoes_gerais` | VARCHAR(1500) | Info livres |
| `orcamento_midia_meta` | INTEGER | Orçamento Meta Ads |
| `orcamento_midia_google` | INTEGER | Orçamento Google Ads |
| `data_fim` | DATE | Data de encerramento (se aplicável) |
| `extra` | JSONB | Dados extra (inclui `historico` de alterações) |
| `notas` | JSONB | Notas livres por projeto |
| `ekyte_workspace` | VARCHAR(2500) | URL do workspace Ekyte |

**Tabelas espelho**: `projetos_onetime` (mesma estrutura, projetos pontuais) e `projetos_inativos` (mesma estrutura, projetos cancelados).

---

### 7.4 Tabela: `remuneracao_cargos`

> Tabela de configuração de limites por cargo/senioridade/level.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `fixo_cargo` | VARCHAR(50) | **PK composta**. Cargo |
| `fixo_senioridade` | VARCHAR(50) | **PK composta**. Senioridade |
| `fixo_level` | VARCHAR(50) | **PK composta**. Level |
| `fixo_ticket_medio` | DECIMAL(15,2) | Ticket médio esperado |
| `fixo_mrr_esperado` | DECIMAL(15,2) | MRR esperado para o cargo |
| `fixo_mrr_teto` | DECIMAL(15,2) | MRR teto (máximo) |
| `fixo_remuneracao_fixa` | DECIMAL(15,2) | Remuneração fixa mensal |
| `fixo_churn_maximo_percentual` | DECIMAL(8,7) | Churn máximo permitido (%) |
| `calc_mrr_minima` | DECIMAL(15,2) | MRR mínimo = Rem.Min / CSP Esperado |
| `calc_remuneracao_minima` | DECIMAL(15,2) | Rem.Min = Fixa - Variável CSP Teto$ |
| `calc_remuneracao_maxima` | DECIMAL(15,2) | Rem.Max = Fixa + Variável CSP Teto$ |
| `calc_csp_esperado` | DECIMAL(8,7) | CSP Esp. = Fixa / MRR Esperado |
| `calc_churn_maximo_valor` | DECIMAL(15,2) | Churn Max$ = Churn Max% × MRR Esperado |

---

### 7.5 Tabela: `investidores_projetos`

> Tabela de vínculo entre investidores e projetos (many-to-many denormalizada).

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | INTEGER | **PK composta** |
| `email_investidor` | VARCHAR(250) | **PK composta**. FK → investidores.email |
| `pipefy_id_projeto` | INTEGER | FK → projetos_*.pipefy_id |
| `active` | BOOLEAN | Se o vínculo está ativo |
| `inactivated_at` | DATE | Data de desativação (para cálculo de churn) |
| `created_at` | DATE | Data de criação do vínculo |
| `cientista` | BOOLEAN | Se é "cientista" (multiplicador 1.5x no fee) |
| `nome_projeto` | VARCHAR(250) | Denormalizado do projeto |
| `fee_projeto` | DECIMAL(15,2) | Fee denormalizado do projeto |
| `fee_contribuicao` | DECIMAL(15,2) | Fee de contribuição (calculado pelas entregas) |

---

### 7.6 Tabela: `investidores_metricas_mensais_novo` ⚠️ TABELA CRÍTICA

> Armazena as métricas mensais por investidor. Contém **8 colunas GENERATED ALWAYS AS STORED** calculadas automaticamente pelo PostgreSQL.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `email_investidor` | TEXT | **PK composta** |
| `mes` | INTEGER | **PK composta** |
| `ano` | INTEGER | **PK composta** |
| `ativo` | BOOLEAN | Status ativo do investidor |
| `cargo` | TEXT | Cargo snapshot |
| `senioridade` | TEXT | Senioridade snapshot |
| `level` | TEXT | Level snapshot |
| `flag` | TEXT | "GREEN" ou "YELLOW" |
| `motivo_flag` | TEXT | Explicação da flag |
| `green_streak` | INTEGER | Meses consecutivos GREEN |
| `yellow_streak` | INTEGER | Meses consecutivos YELLOW |
| `detalhes` | JSONB | Snapshot dos projetos e fees |
| `historico_projetos` | JSONB | Histórico proporcional detalhado dos projetos |

**Campos fixos (gravados pelo serviço `remuneracao.py`)**:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `fixo_mrr_atual` | DECIMAL(15,2) | MRR base para cálculos GENERATED (soma fees ativos) |
| `fixo_mrr_entrega` | DECIMAL(15,2) | MRR proporcional para exibição (dashboard) |
| `fixo_mrr_projeto_total` | DECIMAL(15,2) | MRR total comparativo do portfólio |
| `fixo_churn_atual` | DECIMAL(15,2) | Churn (R$) no mês |
| `fixo_remuneracao_fixa` | DECIMAL(15,2) | Cópia da remuneração fixa do cargo |
| `fixo_csp_esperado` | DECIMAL(8,7) | CSP esperado do cargo |
| `fixo_churn_maximo_percentual` | DECIMAL(8,7) | Churn máximo % do cargo |
| `fixo_mrr_minimo` | DECIMAL(15,2) | MRR mínimo do cargo |
| `fixo_mrr_esperado` | DECIMAL(15,2) | MRR esperado do cargo |
| `fixo_mrr_teto` | DECIMAL(15,2) | MRR teto do cargo |
| `fixo_churn_maximo_valor` | DECIMAL(15,2) | Churn máximo R$ do cargo |
| `fixo_remuneracao_minima` | DECIMAL(15,2) | Remuneração mínima do cargo |
| `fixo_remuneracao_maxima` | DECIMAL(15,2) | Remuneração máxima do cargo |

**Colunas GENERATED (calculadas pelo PostgreSQL)** ⚠️:

| Campo | Fórmula | Tipo |
|-------|---------|------|
| `calc_churn_real_percentual` | `fixo_churn_atual / fixo_mrr_atual` | DECIMAL(8,7) |
| `calc_delta_churn_percentual` | `fixo_churn_maximo_percentual - calc_churn_real_percentual` | DECIMAL(8,7) |
| `calc_delta_churn_valor` | `calc_delta_churn_percentual × fixo_mrr_atual` | DECIMAL(15,2) |
| `calc_variavel_churn` | `calc_delta_churn_valor × fixo_csp_esperado` | DECIMAL(15,2) |
| `calc_delta_csp` | `fixo_csp_esperado - (fixo_remuneracao_fixa / fixo_mrr_atual)` | DECIMAL(8,7) |
| `calc_variavel_csp` | `calc_delta_csp × fixo_mrr_atual` | DECIMAL(15,2) |
| `calc_variavel_total` | `calc_variavel_csp + calc_variavel_churn` | DECIMAL(15,2) |
| `calc_remuneracao_total` | `fixo_remuneracao_fixa + calc_variavel_total` | DECIMAL(15,2) |

> **IMPORTANTE**: Todas as colunas `calc_*` dependem de `fixo_mrr_atual` como denominador. Alterar `fixo_mrr_atual` para um valor muito baixo (ex: proporcional de poucos dias) quando `fixo_churn_atual` é alto causa **overflow NUMERIC(8,7)** (ex: 6000/167 = 35.8 > 9.9999999). Por isso, `fixo_mrr_atual` NÃO é atualizado pelo serviço de propagação proporcional (`projeto_participacao_service.py`).

---

### 7.7 Tabelas de Operação

#### `operacao_tarefas`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | INTEGER | **PK** |
| `projeto_pipefy_id` | INTEGER | FK projeto |
| `tipo` | VARCHAR(20) | "semanal" ou "quarter" |
| `descricao` | TEXT | Descrição da tarefa |
| `concluida` | BOOLEAN | Status |
| `referencia` | VARCHAR(20) | "2026-W08" ou "2026-Q1" |
| `ano` | INTEGER | Ano |
| `created_at` | DATE | Data de criação |

#### `operacao_entregas_mensais` (legado)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | INTEGER | **PK** |
| `investidor_email` | TEXT | E-mail do investidor |
| `projeto_pipefy_id` | INTEGER | FK projeto |
| `mes` / `ano` | INTEGER | Competência |
| `entrega_1` a `entrega_4` | BOOLEAN | 4 milestones |
| `percentual_calculado` | DECIMAL(3,2) | Soma das entregas × 0.25 |
| `valor_fee_original` | DECIMAL(15,2) | Fee do projeto |
| `valor_contribuicao_mrr` | DECIMAL(15,2) | percentual × fee |

#### `operacao_planos_midia`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | INTEGER | **PK** |
| `projeto_pipefy_id` | INTEGER | FK projeto |
| `mes` / `ano` | INTEGER | Competência |
| `investidor_email` | TEXT | Criador |
| `dados_plano` | JSONB | Canais, campanhas, orçamentos |
| `created_at` / `updated_at` | DATE | Timestamps |

#### `operacao_otimizacoes`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | INTEGER | **PK** |
| `projeto_pipefy_id` | INTEGER | FK projeto |
| `investidor_email` | TEXT | Quem registrou |
| `tipo` | VARCHAR(50) | Tipo (Campanha, Criativo, GTM) |
| `canal` | VARCHAR(50) | Canal (Meta, Google) |
| `data_otimizacao` | DATE | Data da otimização |
| `detalhes` | TEXT | Descrição |
| `created_at` | DATE | Data de registro |

#### `operacao_checkins`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | INTEGER | **PK** |
| `projeto_pipefy_id` | INTEGER | FK projeto |
| `investidor_email` | TEXT | Quem registrou |
| `semana_ano` | VARCHAR(20) | "2026-W09" |
| `compareceu` | BOOLEAN | Cliente compareceu? |
| `campanhas_ativas` | BOOLEAN | Campanhas ativas? |
| `gap_comunicacao` | BOOLEAN | Gap de comunicação? |
| `cliente_reclamou` | BOOLEAN | Cliente reclamou? |
| `satisfeito` | BOOLEAN | Cliente satisfeito? |
| `csat_pontuacao` | INTEGER | Score CSAT |
| `observacoes` | TEXT | Notas |
| `created_at` | DATE | Data |

#### `operacao_links_uteis`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | INTEGER | **PK** |
| `projeto_pipefy_id` | INTEGER | FK projeto |
| `titulo` | VARCHAR(200) | Título |
| `url` | TEXT | URL |
| `descricao` | TEXT | Descrição opcional |
| `icone` | VARCHAR(50) | Classe Font Awesome |
| `criado_por` | TEXT | E-mail do criador |
| `created_at` | DATETIME | Data de criação |

---

### 7.8 Tabela: `monthly_deliveries`

> Entregas mensais automáticas, geradas por cargo (E4/E5).

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | INTEGER | **PK** |
| `user_id` | INTEGER | FK → investidores.id |
| `client_id` | INTEGER | FK → projetos_ativos.pipefy_id |
| `email` | TEXT | E-mail do investidor |
| `role` | VARCHAR(50) | "Account" ou "Gestor de Tráfego" |
| `delivery_type` | VARCHAR(100) | Tipo de entrega (checkin, plano_midia, etc.) |
| `month` / `year` | INTEGER | Competência |
| `status` | VARCHAR(20) | "pending" ou "completed" |
| `completed_at` | DATETIME | Data de conclusão |
| `fee_snapshot` | DECIMAL(15,2) | Fee no momento do cálculo |
| `mrr_contribution` | DECIMAL(15,2) | fee_snapshot × 0.25 (se completed) |
| `created_at` | DATETIME | Data de criação |

**UNIQUE constraint**: `(email, client_id, role, delivery_type, month, year)` — garante idempotência.

---

## 8. Fluxos do Sistema

### 8.1 Fluxo de Login

```
Usuário → POST /login (email, senha)
  │
  ├─ Consulta Investidor por email
  ├─ Verifica ativo == True
  ├─ Compara hash de senha
  ├─ Gera token aleatório
  ├─ UPSERT na tabela auth
  ├─ Popula sessão Flask (nome, email, funcao, posicao, etc.)
  └─ Redirect → /
```

### 8.2 Fluxo de Cálculo de Remuneração

```
Trigger: APScheduler diário (00:00) OU GET /api/remuneracao/processar
  │
  ├─ 1. calcular_metricas_mensais(mes, ano) [remuneracao.py]
  │     ├─ Sincroniza status ativo (bulk UPDATE)
  │     ├─ Para cada investidor ativo com funcao:
  │     │   ├─ Soma fees de todos os vínculos ativos → mrr_portfolio_total
  │     │   │   ├─ Converte USD→BRL se necessário
  │     │   │   └─ Aplica multiplicador 1.5x se cientista
  │     │   ├─ Calcula churn (vínculos inativados no mês)
  │     │   ├─ Busca limites do cargo em remuneracao_cargos
  │     │   ├─ Determina FLAG (GREEN se MRR entre min/teto E churn ≤ max)
  │     │   ├─ Calcula streaks (green_streak, yellow_streak)
  │     │   ├─ UPSERT em investidores_metricas_mensais_novo
  │     │   └─ db.flush() (evita bulk com GENERATED columns)
  │     └─ db.commit()
  │
  └─ 2. ProjetoParticipacaoService.sincronizar_remuneracao(mes, ano)
        ├─ Busca vínculos (ativos + inativados no mês)
        ├─ Mapeia moedas dos projetos
        ├─ Para cada investidor:
        │   ├─ Calcula valor proporcional por vínculo
        │   │   (dias trabalhados × fee / total dias no mês)
        │   ├─ Reconcilia com histórico existente (JSONB)
        │   ├─ Marca projetos removidos como inativos
        │   └─ Grava historico_projetos (JSONB)
        ├─ db.commit()
        ├─ Para cada métrica do mês:
        │   ├─ Soma valores proporcionais (com conversão USD→BRL)
        │   ├─ Grava fixo_mrr_entrega e fixo_mrr_projeto_total
        │   └─ db.flush()
        └─ db.commit()
```

### 8.3 Fluxo de Entrega Automática (E4/E5)

```
Usuário salva Plano de Mídia / Otimização / Check-in / Tarefa
  │
  ├─ API persiste o registro no banco
  │
  ├─ Chama DeliveryService.checkAndComplete(email, pipefy_id, tipo, mes, ano)
  │   ├─ Verifica mês corrente (não recalcula meses fechados)
  │   ├─ Busca cargo do investidor
  │   ├─ Verifica se delivery_type pertence ao cargo
  │   ├─ Verifica gatilho (_check_trigger)
  │   │   ├─ checkin: ≥1 checkin no mês
  │   │   ├─ relatorio_account/gt: ≥1 tarefa quarter concluída
  │   │   ├─ planner_monday/config_conta: ≥4 tarefas semanais no mês
  │   │   ├─ forecasting: ≥1 tarefa quarter registrada
  │   │   ├─ plano_midia: ≥1 plano salvo no mês
  │   │   └─ otimizacao: ≥1 otimização no mês
  │   ├─ UPSERT idempotente em monthly_deliveries
  │   ├─ Atualiza status (pending → completed ou vice-versa)
  │   ├─ Recalcula mrr_contribution: (completed/4) × fee
  │   └─ Sincroniza fixo_mrr_entrega na MetricaMensal
  │
  └─ Chama process_deliveries(email, pipefy_id, mes, ano) [delivery_engine.py]
      └─ Mesma lógica, processando TODOS os delivery_types do cargo
```

### 8.4 Fluxo de Edição de Projeto (Gerência)

```
Gerência → PUT /api/projetos/<pipefy_id>
  │
  ├─ Busca projeto (ProjetoAtivo ou ProjetoOnetime)
  ├─ Detecta alterações (nome, fee, squad, produto, step, etc.)
  ├─ Registra no campo extra.historico (JSONB)
  ├─ Sincroniza vínculos:
  │   ├─ Remove vínculos que não estão na lista recebida
  │   └─ Cria/atualiza vínculos restantes (fee_projeto denormalizado)
  ├─ db.commit()
  └─ Dispara ProjetoParticipacaoService.sincronizar_remuneracao()
```

---

## 9. Regras de Negócio

### 9.1 Remuneração

| # | Regra | Detalhes |
|---|-------|---------|
| R1 | **MRR = soma dos fees dos projetos ativos vinculados** | Calculado em `remuneracao.py`. Moeda USD convertida para BRL via AwesomeAPI. |
| R2 | **Multiplicador Cientista = 1.5×** | Se `cientista == True` no vínculo, o fee é multiplicado por 1.5 em todos os cálculos. |
| R3 | **Churn = soma dos fees de vínculos inativados no mês** | Apenas vínculos com `inactivated_at` no mês corrente. |
| R4 | **FLAG GREEN** | MRR entre min e teto do cargo **E** churn ≤ máximo R$. |
| R5 | **FLAG YELLOW** | Qualquer condição R4 não satisfeita. |
| R6 | **Streaks consecutivas** | `green_streak` incrementa se mês anterior era GREEN. `yellow_streak` idem para YELLOW. Streams resetam na troca. |
| R7 | **Remuneração Total = Fixa + Variável** | Variável = Variável Churn + Variável CSP. |
| R8 | **Clamp de remuneração** | Total final = max(rem_min, min(rem_max, calc_remuneracao_total)). |
| R9 | **Entregas NÃO influenciam o cálculo de remuneração** | Na branch atual, `fixo_mrr_atual` é baseado exclusivamente no fee_projeto. `recalculate_investor_mrr` é NO-OP. |

### 9.2 Valor Proporcional

| # | Regra | Detalhes |
|---|-------|---------|
| R10 | **Proporcional = (Dias Trabalhados × Fee) / Total Dias Mês** | Calculado em `projeto_participacao_service.py`. |
| R11 | **Data início baseline = 01/03/2026** | Para o mês de março de 2026, todos os vínculos existentes usam essa data como mínimo. |
| R12 | **fixo_mrr_atual NÃO recebe valor proporcional** | Para evitar overflow NUMERIC(8,7) nas colunas GENERATED. Apenas `fixo_mrr_entrega` e `fixo_mrr_projeto_total` recebem o proporcional. |

### 9.3 Entregas Automáticas

| # | Regra | Detalhes |
|---|-------|---------|
| R13 | **4 tipos por cargo** | Account: checkin, relatorio_account, planner_monday, forecasting. GT: plano_midia, otimizacao, relatorio_gt, config_conta. |
| R14 | **Cada entrega vale 1/4 do fee** | `mrr_contribution = fee_snapshot × 0.25` |
| R15 | **Idempotência via UNIQUE constraint** | `(email, client_id, role, delivery_type, month, year)` impede duplicatas. |
| R16 | **Meses fechados são imutáveis** | Não se recalcula entregas/MRR de meses anteriores ao corrente. |
| R17 | **Marcação manual bloqueada** | POST `/api/operacao/entregas` retorna 403 fixo. |

### 9.4 Acesso (RBAC)

| # | Regra | Detalhes |
|---|-------|---------|
| R18 | **Gerência e Sócio veem tudo** | Verificação via `posicao` ("Gerência", "Sócio") → `is_high_level = True`. |
| R19 | **Operação é filtrada por vínculo** | Outros cargos veem apenas projetos no seu squad ou vinculados ao seu e-mail. |
| R20 | **Admin é distinto de Gerência** | `nivel_acesso == "Admin"` controla acesso ao CRUD de usuários. Um Gerente não é necessariamente Admin. |
| R21 | **Criativa/CS/Cockpit restritos a 2 e-mails** | Hardcoded na sidebar para `martins.gabriel@...` e `gabriel.lasaro@...`. |

### 9.5 Câmbio

| # | Regra | Detalhes |
|---|-------|---------|
| R22 | **Conversão USD→BRL via AwesomeAPI** | Chamada com cache de 1h. Fallback: último valor cacheado ou R$ 5.00 fixo. |

### 9.6 Exceções e Casos Especiais

- **Sócio sem cargo operacional**: Recebe flag GREEN automática e motivo "Sócio sem cargo operacional".
- **Cargo/Nível não configurado**: Recebe flag YELLOW com motivo "Cargo/Nível não configurado".
- **Desenvolvedor como fallback**: Para testes, o cargo "Desenvolvedor" é mapeado para "Gestor de Tráfego" no motor de entregas.
- **Projetos que saem da UI**: Se um projeto é removido da lista de vínculos (PUT /api/projetos), o `projeto_participacao_service` marca-o como inativo no histórico JSONB e recalcula o proporcional.

---

## 10. Pontos Críticos

### 10.1 Riscos

| # | Risco | Severidade | Detalhes |
|---|-------|-----------|---------|
| 1 | **Overflow NUMERIC(8,7) nas colunas GENERATED** | 🔴 Alta | Se `fixo_mrr_atual` for muito baixo e `fixo_churn_atual` for alto, a divisão pode exceder 9.9999999. Mitigação atual: `fixo_mrr_atual` é mantido com fees brutos, não proporcionais. |
| 2 | **Secret key efêmera** | 🟡 Média | `app.secret_key = os.urandom(10).hex()` — sessões são invalidadas a cada reinício da aplicação. Em produção, isso desloga todos os usuários. |
| 3 | **SQLAlchemy bulk vs. FetchedValue** | 🟡 Média | Colunas GENERATED causam erro 9h9h em bulk INSERT/UPDATE. Mitigação: `db.flush()` individual após cada registro. |
| 4 | **Hardcoded access control** | 🟡 Média | Sidebar contém e-mails hardcoded para acesso a Criativa, CS/CX e Cockpit. Deveria ser RBAC via banco. |
| 5 | **Sem rate limiting** | 🟡 Média | APIs REST não têm rate limiting ou throttling. |

### 10.2 Gargalos

| # | Gargalo | Impacto | Detalhes |
|---|---------|---------|---------|
| 1 | **`app.py` monolítico (1737 linhas)** | Manutenção difícil | Todas as rotas, helpers e configs em um único arquivo. |
| 2 | **CSS principal (97KB)** | Performance de parsing | `styles.css` é muito grande e poderia ser modularizado. |
| 3 | **`operacao.html` (66KB)** | Renderização pesada | Template muito extenso com muita lógica inline. |
| 4 | **N+1 queries em remuneracao.py** | Performance de BD | Para cada investidor, faz queries individuais de vínculos e projetos. |
| 5 | **Sessão sem persistência** | Reinício perde sessões | Sessão Flask em memória, sem armazenamento em Redis ou banco. |

### 10.3 Cuidados (Manutenção)

| # | Cuidado | Detalhes |
|---|---------|---------|
| 1 | **Não alterar `fixo_mrr_atual` com valores proporcionais** | Causa overflow nas 8 colunas GENERATED. Documentado em `projeto_participacao_service.py`. |
| 2 | **Usar `db.flush()` após cada UPSERT em MetricaMensal** | Necessário por causa de FetchedValue(). Bug documentado na conversa `de6b6958`. |
| 3 | **Models, Services e Database são protegidos** | Skill `change-restrictions` proíbe alteração direta desses artefatos. |
| 4 | **Manter denormalização sincronizada** | `nome_projeto` e `fee_projeto` em `investidores_projetos` devem ser atualizados quando o projeto muda. |
| 5 | **JSONB mutation tracking** | Ao alterar campos JSONB, usar `flag_modified()` ou reatribuir o dicionário inteiro para que o SQLAlchemy detecte a mudança. |

---

## 11. Guia de Recriação

### Passo 1: Estrutura Inicial

```
projeto/
├── app.py
├── database.py
├── models.py
├── requirements.txt
├── .env
├── services/
│   ├── remuneracao.py
│   ├── projeto_participacao_service.py
│   ├── delivery_engine.py
│   ├── delivery_service.py
│   ├── operacao_service.py
│   └── currency.py
├── templates/
│   ├── components/
│   │   ├── header.html
│   │   ├── sidebar.html
│   │   ├── loader.html
│   │   ├── modal-configuracoes.html
│   │   ├── icon_title.html
│   │   └── up-button.html
│   ├── login.html
│   ├── index.html
│   └── ... (demais templates)
├── static/
│   ├── js/
│   ├── style/
│   └── images/
└── .agents/
    └── skills/
```

### Passo 2: Banco de Dados

1. Provisionar PostgreSQL com schema `plataforma_geral`.
2. Criar a tabela `remuneracao_cargos` primeiro (é referenciada por todas as métricas).
3. Criar `investidores`, `auth`.
4. Criar `projetos_ativos`, `projetos_onetime`, `projetos_inativos`.
5. Criar `investidores_projetos`.
6. Criar `investidores_metricas_mensais_novo` com as **8 colunas GENERATED ALWAYS AS STORED**.
7. Criar as tabelas de operação (`operacao_tarefas`, `operacao_entregas_mensais`, etc.).
8. Criar `monthly_deliveries` com a UNIQUE constraint.
9. Popular `remuneracao_cargos` com os limites de cada cargo/senioridade/level.

> **Atenção**: As colunas GENERATED devem ser criadas diretamente via DDL SQL, não via SQLAlchemy `create_all`. No ORM, elas são mapeadas com `server_default=FetchedValue()`.

### Passo 3: Backend

1. Configurar `database.py` (engine, Session, Base).
2. Definir todos os modelos em `models.py`.
3. Implementar services na ordem:
   - `currency.py` (sem dependência)
   - `operacao_service.py` (depende apenas de models)
   - `remuneracao.py` (depende de models + currency)
   - `projeto_participacao_service.py` (depende de models + currency)
   - `delivery_engine.py` (depende de models)
   - `delivery_service.py` (depende de models + currency)
4. Implementar `app.py`:
   - Autenticação (login/logout/alterar-senha)
   - Páginas (rotas GET que renderizam templates)
   - APIs REST (/api/*)
   - Scheduler (APScheduler)

### Passo 4: Frontend

1. Criar `styles.css` com o design system (variáveis CSS, layout, componentes).
2. Criar `tema-claro.css` para override do tema.
3. Criar componentes reutilizáveis (`header.html`, `sidebar.html`, `loader.html`, `modal-configuracoes.html`).
4. Criar `app.js` com utilitários globais (sidebar, dropdown, `Utils.formatBRL`, `showToast`).
5. Criar templates na ordem de complexidade:
   - `login.html`
   - `index.html` (Home)
   - `hub-projetos.html` + `hub-projetos.js`
   - `operacao.html` + `operacao.js`
   - `hub-remuneracao.html` + `remuneracao.js`
   - `gerenciar-usuarios.html` + `gerenciar-usuarios.js`
   - `painel-ranking.html` + `ranking.js`
   - Templates secundários (CS/CX, Criativa, placeholders)

### Passo 5: Integração

1. Conectar frontend → APIs via `fetch()`.
2. Implementar RBAC na sidebar (Jinja2 conditions).
3. Configurar scheduler para cálculo diário.
4. Testar fluxo completo: Login → Home → Operação → Entregas → Remuneração.

### Passo 6: Validação

1. Criar investidor de teste com cargo, senioridade e level configurados em `remuneracao_cargos`.
2. Vincular investidor a projetos.
3. Executar `GET /api/remuneracao/processar`.
4. Verificar se as métricas foram calculadas corretamente (flag, MRR, churn, variável, total).
5. Testar entregas automáticas: salvar plano de mídia, registrar otimização, fazer check-in.
6. Verificar que `monthly_deliveries` foi populada e `fixo_mrr_entrega` atualizada.
7. Verificar RBAC: Account vê sua operação, Gerência vê remuneração, Admin gerencia usuários.

---

> **Fim do documento**. Gerado por AutoArchitect.Doc com base na análise completa do código-fonte do HUB Lisboa&CO.
