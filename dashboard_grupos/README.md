# Dashboard — Análise de Grupo de Clientes

Dashboard de análise dos grupos de WhatsApp de clientes, integrado ao **HUB Lisboa&CO** como um
Blueprint Flask isolado. Acessível em **`/grupos`** (rótulo **"Análise de Grupos"** no menu, grupo *Gestão & CS*).

## Acesso
- Restrito a **Gerência / Sócio / Coordenador** (guard em `hub_integration.py`).
- Sem login → redireciona para `/login` do HUB.
- Registrado no `app.py` via `register_dashboard_grupos(app)`.

## Fonte de dados (somente leitura)
Schema `analise_grupos_cliente` no banco do HUB (`Lisboa_PG_DB`), tabelas:
- `mensagens_coletadas` (mensagens) e `group_id` (catálogo de grupos).

A conexão é derivada das variáveis `DB_*` do `.env` do HUB (sem duplicar credenciais).
**Nenhuma escrita é feita no banco.**

Os nomes de grupo passam por limpeza de marca (`nomes.py`): removem os conectores
`V4 Company &`, `& V4 Company`, `V4 Company +`, `+ V4 Company` (case-insensitive).

## Arquivos de estado (JSON, graváveis)
Na raiz do HUB:

| Arquivo | Uso | Editável pela UI |
|---|---|---|
| `equipe.json` | Nome → papel dos membros da equipe | Sim (Equipe & Clientes) |
| `clientes.json` | Nome → papel dos clientes | Sim (Equipe & Clientes) |
| `churn.json` | Grupos marcados como churn (ocultados das métricas) | Sim (Churn) |
| `config.json` | Janela de atendimento, metas de SLA e limiar de inatividade | Sim (Configurações) |

> **Persistência**: em ambientes com container **efêmero**, monte esses arquivos em um **volume
> persistente** ou use o **Exportar/Importar mapeamento** (aba *Equipe & Clientes*) para
> backup/restauração. Caso contrário, as edições se perdem em um redeploy.

## Telas
- **Visão Geral** – KPIs, mensagens/dia (com média móvel 7d), comparação de metades, heatmap.
- **SLA & Respostas** – SLA útil/bruto, dentro da meta, distribuições, por hora e por dia da semana; tabelas em abas.
- **Grupos & Remetentes** – concentração, gaps e SLA por grupo/remetente.
- **Engajamento** – por papel e por pessoa, clientes inativos e **clientes em risco**.
- **Monitoramento de Grupos** – status de inatividade; cards clicáveis abrem a lista de grupos.
- **Diagnóstico** – alertas (inatividade, concentração, sem resposta, mapeamento).
- **Equipe & Clientes** – mapeamento (Equipe / Clientes / Não mapeados), busca e export/import.
- **Churn** – marcar/reativar grupos; busca por cliente.
- **Configurações** – edita `config.json` sem reiniciar.

Filtros globais: Grupo, De/Até, Últimos N dias, Autor, Papel — com chips de remoção individual.
Exportação de mensagens filtradas em CSV (`/grupos/exportar.csv`).

## Desenvolvimento
```bash
# Testes das funções de análise
.venv/bin/python -m unittest dashboard_grupos.tests.test_analise

# Rodar o HUB (o dashboard é registrado junto)
.venv/bin/python app.py
```

## Estrutura
```
dashboard_grupos/
├── __init__.py          # Blueprint (/grupos)
├── hub_integration.py   # Registro no HUB + guard de acesso + envs de DB
├── routes.py            # Rotas/contexto das telas
├── analise.py           # Cálculos (SLA, gaps, engajamento, status, risco)
├── db.py                # Conexão e leitura (cache 30s)
├── autores.py           # Mapeamento equipe/clientes (+ export/import)
├── churn.py             # Churn (+ export/import)
├── config.py            # Configurações (+ salvar/atual)
├── nomes.py             # Limpeza de nome de grupo
├── templates/           # base + telas + macros
├── static/css|js        # Estilo e scripts (paginação, busca, modais)
└── tests/               # Testes unittest
```

## Observações de operação
- Caches em memória com **TTL 30s** (mensagens e resultado filtrado). Alterações de churn/config
  podem levar até 30s para refletir em telas já carregadas.
- A limpeza de nomes e a tabela de churn são normalizadas, portanto chaves antigas do `churn.json`
  continuam válidas.
