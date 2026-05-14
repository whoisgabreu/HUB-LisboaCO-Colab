from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import kanban, cards
from backend.services.kanban_service import KanbanService
from backend.models.kanban import KanbanPhase, KanbanField

app = FastAPI(title="Kanban MVP API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(kanban.router)
app.include_router(cards.router)

@app.on_event("startup")
def startup_event():
    # Initialize with sample data if empty
    service = KanbanService()
    kanbans = service.list_kanbans()
    if not kanbans:
        service.create_kanban(
            nome="Desenvolvimento de Produto",
            fases=[
                KanbanPhase(id="backlog", nome="Backlog", ordem=1, campos=[
                    KanbanField(id="titulo", label="Título do Projeto", tipo="string", obrigatorio=True),
                    KanbanField(id="desc", label="Descrição", tipo="text"),
                    KanbanField(id="prioridade", label="Prioridade", tipo="select", opcoes=["Baixa", "Média", "Alta"])
                ]),
                KanbanPhase(id="analise", nome="Análise", ordem=2, campos=[
                    KanbanField(id="requisitos", label="URL Requisitos", tipo="string"),
                    KanbanField(id="estimativa", label="Estimativa (Horas)", tipo="number")
                ]),
                KanbanPhase(id="dev", nome="Desenvolvimento", ordem=3, campos=[
                    KanbanField(id="branch", label="Git Branch", tipo="string"),
                    KanbanField(id="completo", label="Desenvolvimento Concluído?", tipo="boolean")
                ]),
                KanbanPhase(id="qa", nome="QA / Testes", ordem=4, campos=[
                    KanbanField(id="bugs", label="Bugs Encontrados", tipo="number", readonly=False),
                    KanbanField(id="aprovado", label="Aprovado pelo QA?", tipo="boolean")
                ]),
                KanbanPhase(id="done", nome="Concluído", ordem=5, campos=[
                    KanbanField(id="data_entrega", label="Data de Entrega", tipo="datetime", readonly=True)
                ])
            ]
        )

@app.get("/")
def read_root():
    return {"message": "Welcome to Kanban MVP API"}

if __name__ == "__main__":
    import uvicorn
    # Habilitando reload para desenvolvimento
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
