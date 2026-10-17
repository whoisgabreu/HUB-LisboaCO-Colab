"""Seed: cria no Painel Gerencial TECH (schema painel_tech) os cards do board Trello 'v4'.

- Concluídos (lista DONE) -> status 'finalizado'
- Demais listas -> status 'fila'
- Idempotente: pula projetos cujo nome já exista.

Usage:
    python scripts/seed_painel_tech_trello.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CONCLUIDOS = [
    "[ INTERNO ] Bugs & QoL - HUB Lisboa",
    "[ INTERNO ] HUB Lisboa&CO",
    "Q2 - Ideiai do CRM para clientes",
    "[ Chat AI ] Hotel Uirapuru",
    "Unitrier Site",
    "Q2 - Projeto Kanbam (substituição Pipefy)",
    "Q2 - MPA: melhoria no fluxo",
    "Dashboard Somaxi",
    "Performance e SEO - Marble",
    "LP Somaxi",
    "[CORREÇÕES] HUB",
    "[CS/CX] Mais notificações Pipefy",
    "Q2 - Processo de criação visual com Skills OpenClaude/ Antigravity",
    "HUB - Implementar no sistema a possibilidade de registrar data de saída do projeto.",
    "Q1-[SEG][MPA Advogados] SDR AI",
    "Q1-[QUA][EPIC Rental] Dashboard",
    "[DATABASE] Adaptação DB operação + Sistema",
    "HUB - Sincronizar CHURN do Kanban no DB.",
    "Q2 - Ideia do Chat para Exemplo para cliente",
    "HUB - BUGS",
    "HUB - Corrigir Filtro na tela HUB Projetos",
    "[CS/CX] Automação de Notificações Aniversário V4 do Cliente",
    "[CS/CX]Automação de Notificações Quarter do Cliente na fase Ongoing",
    "[DATABASE] Popular DB com Clientes Reais",
    "Sistema de Tokenização de Login para poder realizar requisões N8N",
    "[INTERNACIONAL]Telegram - Gerenciamento de Membros e Envio de Mensagens",
    "[UIRAPURU]Manutenção ChatBot",
]

FILA = [
    ("Trello: PAUSADOS", [
        "[ SDR IA ] Unitrier",
        "[ Automação ] Grunn – Congelado Devido à Falta de Continuidade do Cliente",
        "[OPERAÇÃO][PERFORMANCE] Automações Account",
        "[OPERAÇÃO][PERFORMANCE] Automações Coordenador",
        "[OPERAÇÃO][REPORT] Relatório Mensal",
        "[OPERAÇÃO][PERFORMANCE] Tracking Offline e Serverside",
    ]),
    ("Trello: GOING - CLIENTES", [
        "[ Cão & CIA ] Sistema de Filas",
        "[ Beco Mágico ] Migrar LP da Agência anterior para V4",
        "[ Sueli Silveira ] IA Sueli Silveira",
        "[ SDR IA ] Franco - Pausado por Solicitação do Cliente",
    ]),
    ("Trello: TO DO - INTERNO", [
        "[ INTERNO ] Outbound Tech",
        "[GESTÃO][SEGURANÇA] Backup diário VPS / n8n",
        "[ INFRA ] Migrar projetos/serviços do EasyPanel 1 para o EasyPanel 2",
        "[ INFRA ] Migrar LPs do Easypanel para Cloudflare",
        "[ GT IA & SM IA ] Conectar projetos com DB de contexto",
    ]),
    ("Trello: GOING - INTERNO", [
        "[ INTERNO ] Social Media AI",
        "[OPERAÇÃO][PERFORMANCE] Automações GT",
        "[ INTERNO ] Análise de grupos de clientes",
        "[ INTERNO ] Dashboard da Análise de grupos de cliente",
        "[ INTERNO ] Creative IA",
    ]),
    ("Trello: REVIEW", [
        "[ Delivery Elite ] SDR IA + Kommo",
        "[ MPA Advogados ] Manutenção SDR IA",
        "[ INTERNO ] Formulário evento Cozinha Campeã",
        "[ Essenza ] Landing Page",
        "[ Copetro ] Site Institucional",
        "[ Marvin ] Landing Page",
        "[ Marietta ] Landing Page",
        "[ MAKRO ] Landing Page",
        "[ FLUA ] Landing Page",
        "[ N8N ] Transcrição Gemini > Ekyte",
    ]),
]


def _existe(nome):
    from painel_tech import db as pdb

    return pdb._fetch_one(
        f'SELECT id FROM "{pdb.SCHEMA}".projetos WHERE nome = %s', (nome,)
    ) is not None


def seed():
    from painel_tech import db as pdb

    inseridos, pulados = 0, 0

    ordem = 0
    for nome in CONCLUIDOS:
        if _existe(nome):
            pulados += 1
            continue
        pdb.criar_projeto({"nome": nome, "descricao": "Trello: DONE", "status": "finalizado", "ordem": ordem})
        ordem += 1
        inseridos += 1

    ordem = 0
    for descricao, nomes in FILA:
        for nome in nomes:
            if _existe(nome):
                pulados += 1
                continue
            pdb.criar_projeto({"nome": nome, "descricao": descricao, "status": "fila", "ordem": ordem})
            ordem += 1
            inseridos += 1

    print(f"Inseridos: {inseridos} | Pulados (já existiam): {pulados}")


if __name__ == "__main__":
    seed()