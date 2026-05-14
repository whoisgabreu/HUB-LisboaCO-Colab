# Kanban MVP

Sistema Kanban personalizado com fases configuráveis, formulários dinâmicos e histórico imutável.

## 🚀 Como Executar

### Backend (Python + FastAPI)

1. Certifique-se de ter o Python 3.11+ instalado.
2. Instale as dependências:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Inicie o servidor:
   ```bash
   python -m backend.main
   ```
   O backend estará disponível em `http://localhost:8000`.

### Frontend

Basta abrir o arquivo `frontend/index.html` em qualquer navegador moderno.

---

## 🛠️ Funcionalidades

- **Configuração Dinâmica**: As colunas e campos são definidos via JSON (API).
- **Imutabilidade**: Cada mudança de fase gera um snapshot completo dos dados.
- **Histórico**: Rastreamento completo de quando o card entrou e saiu de cada fase.
- **Design Premium**: Interface dark mode com visual moderno e responsivo.
- **Drag and Drop**: Mova cards entre colunas de forma intuitiva.

---

## 📂 Dados

Os dados são persistidos localmente na pasta `backend/data` em formato JSON, simulando uma estrutura de banco NoSQL para fácil migração futura para MongoDB.

---

## 🔌 API Endpoints (Exemplos)

### Criar Novo Kanban
`POST /kanban`
```json
{
  "nome": "Meu Fluxo",
  "fases": [
    {
      "id": "todo",
      "nome": "A Fazer",
      "ordem": 1,
      "campos": [
        { "id": "titulo", "label": "Título", "tipo": "string", "obrigatorio": true }
      ]
    }
  ]
}
```

### Mover Card
`POST /cards/{id}/mover`
```json
{
  "nova_fase_id": "em_progresso",
  "dados": {
    "responsavel": "João",
    "data_inicio": "2024-04-28"
  }
}
```
