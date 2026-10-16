from datetime import date

from ..domain import nivel_indicador
from .health import calcular_saude
from .priority import calcular_prioridade
from .rules import avaliar_regras, calcular_intervencao


def analisar_projeto(projeto, etapas, cfg, hoje=None):
    hoje = hoje or date.today()
    saude = calcular_saude(projeto, etapas, cfg, hoje)
    prioridade = calcular_prioridade(projeto, cfg)

    ctx = {
        "status": projeto.get("status"),
        "impacto": nivel_indicador("impacto", projeto.get("impacto")),
        "urgencia": nivel_indicador("urgencia", projeto.get("urgencia")),
        "risco": nivel_indicador("risco", projeto.get("risco")),
        "esforco": nivel_indicador("esforco", projeto.get("esforco")),
        "ritmo": saude["ritmo"],
        "ritmo_nivel": saude["ritmo_nivel"],
        "prioridade": prioridade["nivel"],
        "prioridade_score": prioridade["score"],
        "bloqueio_dias": saude["dias_bloqueio"],
        "dias_sem_movimento": saude["dias_sem_movimento"],
        "etapas_vencidas": saude["etapas_vencidas"],
        "dependencias_bloqueadas": saude["dependencias_bloqueadas"],
        "progresso": saude["progresso"],
    }
    alertas = avaliar_regras(ctx, cfg)
    intervencao = calcular_intervencao(alertas)
    return {
        "prioridade": prioridade,
        "saude": saude,
        "alertas": alertas,
        "intervencao": intervencao,
        "ctx": ctx,
    }
