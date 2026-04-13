# 📘 Project Memory

## 🧾 Visão Geral
O **HUB Lisboa&CO** é uma plataforma de gestão operacional e financeira para a franquia Lisboa&CO da V4 Company. Atualmente em fase final de migração de Flask para Django com paridade total de banco de dados legado.

---

## ⚙️ Stack Atual
- **Framework:** Django (Migração de Flask concluída)
- **Banco de Dados:** PostgreSQL (Schema: `plataforma_geral`) - **IMUTÁVEL**
- **ORM:** Django ORM (Configurado para `managed = False`)

---

## 📅 Histórico de Alterações

### 2026-04-13 - Sincronização Total de Schema (Paridade)

**Descrição:**
Inspeção técnica via `information_schema` e ajuste de todos os modelos Django para refletir o schema real.

---

### 2026-04-13 - Limpeza de Campos Django e Mapeamento de Cálculos

**Descrição:**
Desativação de campos padrão do Django que não existem no banco legado para evitar erros de SQL e mapeamento de colunas de cálculo adicionais.

**Arquivos afetados:**
- `users/models.py` (Desativados `last_login`, `is_superuser`, `groups`, `user_permissions`, `is_staff`, `is_active`)
- `remuneracao/models.py` (Adicionados campos `calc_media_clientes`, `calc_variavel_csp_teto_percentual`, `calc_variavel_csp_teto_valor`, etc.)

**Motivo:**
Eliminar erros `ProgrammingError` causados pela tentativa do Django de selecionar colunas inexistentes e garantir que todos os dados computados pelo banco estejam disponíveis.

**Impacto:**
O sistema agora realiza queries limpas, buscando apenas o que existe fisicamente no banco de dados legado.

---

### 2026-04-13 - Correção de Sintaxe em Templates (Compatibilidade Django)

**Descrição:**
Substituição massiva de padrões do Flask/Jinja2 por sintaxe nativa do Django Templates para eliminar erros de renderização.

**Arquivos afetados:**
- `templates/components/modal-configuracoes.html` (e outros)

**Alterações principais:**
- Substituído `session.campo` por `user.campo` (referenciando o objeto `Investidor` logado).
- Convertido `{{ var or 'default' }}` para `{{ var|default:'default' }}`.
- Corrigidas condicionais de exibição de fotos de perfil e permissões de menu.

**Motivo:**
O Django Templates não suporta o operador `or` dentro de tags de exibição e utiliza um processador de contexto específico para usuários autenticados (`request.user`), tornando as referências diretas à sessão obsoletas para dados de perfil.

### 2026-04-13 - Restauração de Templates de Modais

**Descrição:**
Reconstrução do arquivo `templates/components/hub-remuneracao-modals.html` que estava ausente, impedindo o acesso à página de remuneração.

**Alterações principais:**
- Criado `hub-remuneracao-modals.html` com suporte a `remunerationModal` (detalhes financeiros) e `clientsListModal` (lista de projetos).
- Garantida a integração com o JavaScript `remuneracao.js` através dos IDs de DOM corretos.

---

## 📌 Estado Atual

- **Migração Base:** 100% concluída.
- **Sincronização de Banco:** Finalizada.
- **Frontend:** Templates corrigidos e modais restaurados.
- **Autenticação:** Baseada na tabela `investidores` sem metadados do Django (Done).

---

## 🚧 Próximos Passos

1. Validar a exibição dos novos campos calculados no Hub de Remuneração.
2. Testar o fluxo de tarefas e entregas mensais.

---

## ⚠️ Observações Importantes

- **REGRA DE OURO:** Não alterar nenhuma tabela ou campo no banco de dados.
- **AUTH:** O modelo `Investidor` tem os campos `last_login`, `is_staff` e `is_active` setados como `None` para evitar erros de SQL em SELECTs.
