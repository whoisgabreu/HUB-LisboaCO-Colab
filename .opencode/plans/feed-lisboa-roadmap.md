# Plano — Feed Lisboa (HUB): Fases 1 a 4

Branch: `feature/feed` · Sem push/PR sem ordem explícita · Edição/DB de escopo próprio do feed (módulo isolado `feed/`).

## 0. Cabeçalho do composer (pedido direto)
- `templates/components/feed.html`: reestruturar `.feed-composer` para coluna:
  - `<div class="feed-composer-title">No que está pensando hoje?</div>` no topo.
  - Envolver avatar + corpo em `.feed-composer-main` (linha).
- `static/style/feed.css`: `.feed-composer { flex-direction: column }`, `.feed-composer-main { display:flex; gap:.85rem }`, estilo de `.feed-composer-title` (destaque + borda inferior leve).
- Placeholder do textarea → `"Escreva algo para o time..."`.
- Nenhuma mudança de JS.

---

## Fase 1 — Rápidas (UX)

### Funcionalidades
1. **Emoji picker** no composer (insere no textarea).
2. **@menções** com autocomplete de usuários ativos; token `@email`, render como `@PrimeiroNome`.
3. **Busca/filtro** no feed: texto/autor e tipo (post/evento/aniversário/enquete).
4. **Editar post** (autor), com registro de auditoria e badge "editado".
5. **Contador de caracteres** + limite.
6. **Auto-link** de URLs.
7. **Skeleton/empty-state** melhores; tooltip com data completa no timestamp.

### Backend
- `feed/service.py`
  - `listar_posts(...)` aceita `q`, `tipo`, `autor` (ilike em `conteudo`/`titulo`).
  - `editar_post(post_id, autor_email, novo_conteudo)`: só autor; grava `feed_posts_edicoes`; seta `editado`, `total_edicoes`, `editado_em`.
  - `listar_usuarios_para_mencao()` → ativos (email, nome, profile_picture).
- `feed/routes.py`: `GET /api/feed/usuarios`, `POST /api/feed/posts/<id>/editar`.

### Frontend
- `templates/components/feed.html`, `static/js/feed.js`, `static/style/feed.css`.

---

## Fase 2 — Engajamento/social

### Funcionalidades
1. **Notificações (sino)** com badge de não lidas: reações, comentários, @menções.
2. **Enquetes** (2–6 opções), votar/desvotar, resultado com barras e total.
3. **Salvar/favoritar** posts + filtro "salvos".
4. **Repost** (`tipo='repost'`, `original_post_id`).
5. **Reações em comentários**.
6. **Perfil rápido** ao clicar no avatar.

### Backend
- Novas estruturas: `feed_notificacoes`, `feed_enquete_votos`, `feed_salvos`, `feed_comentario_reacoes`.
- `feed/service.py`
  - `_notificar(usuario_email, tipo, ator, post_id, comentario_id, texto)` (não notifica a si mesmo) — chamado em `reagir`, `comentar` (autor do post + autor do comentário pai) e por @menções.
  - `listar_notificacoes(email)`, `contar_nao_lidas(email)`, `marcar_lida(id)`, `marcar_todas_lidas(email)`.
  - `criar_enquete(...)`, `votar_enquete(post_id, email, opcao_index)`; serialização com votos/minha opção.
  - `salvar_post`, `remover_salvo`; flag `salvo` na serialização.
  - `repostar(post_id, autor, comentario)` + embed do post original.
  - `reagir_comentario(...)`; incluir contagem/minha reação em `listar_comentarios`.
  - `perfil_usuario(email)` → nome, cargo, squad, senioridade, foto, aniversário, tempo de casa (`InvestidorProjeto.created_at`), clientes ativos.
- `feed/routes.py`: `/notificacoes`, `/notificacoes/contagem`, `/notificacoes/<id>/lida`, `/notificacoes/marcar-lidas`, `/posts/<id>/votar`, `/posts/<id>/salvar`, `/posts/<id>/repostar`, `/comentarios/<id>/reagir`, `/perfil/<email>`.
- `templates/components/header.html`: sino + dropdown; `static/js/notificacoes.js` global (polling leve da contagem).

---

## Fase 3 — Moderação/segmentação

### Funcionalidades
1. **Visibilidade por post**: Todos / Squad / Gerência.
2. **Denunciar** post; **ocultar** (gestão).

### Backend
- Colunas em `feed_posts`: `visibilidade`, `oculto`; tabela `feed_denuncias`.
- `listar_posts` filtra por visibilidade:
  - `todos`: visível a todos.
  - `squad`: visível a quem é da mesma squad do autor (gestão/admin veem sempre).
  - `gestao`: só gestão (Gerência/Sócio/Admin) ou o autor.
  - Posts `oculto`: só gestão.
- `denunciar_post`, `ocultar_post`/`desocultar_post`.
- Rotas: `/posts/<id>/denunciar`, `/posts/<id>/ocultar`, `/posts/<id>/desocultar`.

---

## Fase 4 — Retaguarda técnica

### Funcionalidades
1. **Paginação por cursor** (`criado_em`+`id`); fixados só na 1ª página.
2. **Polling de novos posts** ("N novas publicações").
3. **Auditoria** de edição (tabela `feed_posts_edicoes`), com badge "editado".

### Backend
- `listar_posts(usuario_email, cursor=None, por_pagina=10, ...)` → `{posts, proximo_cursor, tem_mais}`.
- `novos_posts(desde_iso, viewer)` → `{total, posts}`.
- Rotas: `/novos?desde=`.

---

## Banco (script `scripts/migrate_feed_social.py`, idempotente)
- `ALTER TABLE feed_posts ADD`: `visibilidade VARCHAR(20) DEFAULT 'todos'`, `original_post_id INTEGER`, `enquete JSONB`, `editado BOOLEAN DEFAULT FALSE`, `total_edicoes INTEGER DEFAULT 0`, `editado_em TIMESTAMP`, `oculto BOOLEAN DEFAULT FALSE`.
- `CREATE TABLE`: `feed_notificacoes`, `feed_enquete_votos`, `feed_salvos`, `feed_comentario_reacoes`, `feed_denuncias`, `feed_posts_edicoes` (com índices e UNIQUEs).

## Models (`feed/models.py`)
- Colunas novas em `FeedPost`; classes `FeedNotificacao`, `FeedEnqueteVoto`, `FeedSalvo`, `FeedComentarioReacao`, `FeedDenuncia`, `FeedPostEdicao`.

## Arquivos
- Backend: `scripts/migrate_feed_social.py`, `feed/models.py`, `feed/service.py`, `feed/routes.py`.
- Frontend: `templates/components/feed.html`, `templates/feed.html`, `templates/components/header.html`, `static/js/feed.js`, `static/js/notificacoes.js`, `static/style/feed.css`.

## Verificação
- `python scripts/migrate_feed_social.py`; smoke test de cada API com sessões de perfis diferentes; `py_compile` + `node --check`.
- Testar visibilidade (Todos/Squad/Gerência), cursor, votos, salvar, repost, notificações, edição/auditoria e perfis de permissão (autor vs Gerência/Sócio/Admin).
- Limpar dados de teste ao final.

## Git
- Commits por fase na `feature/feed`:
  1. cabeçalho + Fase 1
  2. Fase 2
  3. Fase 3
  4. Fase 4
- Sem push/PR.
