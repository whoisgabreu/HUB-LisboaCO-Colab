"""Contexto de projeto: snapshots e aplicação de mapeamentos do Kanban.

O contexto é versionado: cada save cria uma nova linha, copiando os campos da
versão anterior. O helper é compartilhado entre o hub e o Kanban.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from models import Projeto, ProjetoContexto

# Campos de contexto que podem ser preenchidos por telas/mapeamentos.
# Ficam de fora:
# - cliente: identidade do snapshot (preenchido automaticamente)
# - contexto_geral: documento .md (aba própria)
# - act_meta/id_google: legado de contas (use projetos_contas)
CAMPOS_MAPEAVEIS: List[str] = [
    c for c in ProjetoContexto.CAMPOS if c not in ("cliente", "contexto_geral")
]

LABELS: Dict[str, str] = {
    "segmento_nicho": "Segmento / Nicho",
    "localizacao_regiao_atuacao": "Localização / Região de Atuação",
    "contato_principal_decisor": "Contato Principal / Decisor",
    "outros_contatos_chave": "Outros Contatos-Chave",
    "equipe_responsavel": "Equipe Responsável",
    "canais_midia_ativos": "Canais de Mídia Ativos",
    "ids_rastreamento": "IDs de Rastreamento",
    "orcamento_midia_mensal": "Orçamento Mensal de Mídia",
    "objetivo_meta_principal": "Objetivo / Meta Principal",
    "ticket_medio_financeiro": "Ticket Médio",
    "publico_alvo": "Público-Alvo",
    "estrategia_campanha_atual": "Estratégia / Campanha Atual",
    "tom_voz_posicionamento": "Tom de Voz / Posicionamento",
    "must_donts_restricoes": "Must-dos / Don'ts e Restrições",
    "benchmark_cpl_referencia": "Benchmark / CPL de Referência",
    "tracking_crm": "Tracking / CRM",
    "o_que_funciona": "O que Funciona",
    "o_que_nao_funciona": "O que Não Funciona",
    "forma_pagamento": "Forma de Pagamento",
    "relacionamento_alertas": "Relacionamento / Alertas",
    "pendencias_proximos_passos": "Pendências / Próximos Passos",
    "link_drive_documentos": "Link do Drive",
}


def ultimo(db: Session, projeto_pipefy_id: int) -> Optional[ProjetoContexto]:
    return (
        db.query(ProjetoContexto)
        .filter_by(projeto_pipefy_id=projeto_pipefy_id)
        .order_by(ProjetoContexto.id.desc())
        .first()
    )


def novo_snapshot_contexto(projeto: Projeto, anterior: Optional[ProjetoContexto],
                           origem: str, motivo: Optional[str] = None) -> ProjetoContexto:
    """Cria um snapshot copiando os campos da versão anterior."""
    cliente = None
    if anterior is not None:
        cliente = getattr(anterior, "cliente", None)
    cliente = (cliente or projeto.nome or "").strip() or "—"

    ctx = ProjetoContexto(
        projeto_pipefy_id=projeto.pipefy_id,
        cliente=cliente,
        origem_contexto=origem,
        motivo_atualizacao=(motivo or None),
        contexto_anterior_id=(anterior.id if anterior else None),
    )
    if anterior is not None:
        for campo in ProjetoContexto.CAMPOS:
            if campo == "cliente":
                continue
            setattr(ctx, campo, getattr(anterior, campo, None))
    return ctx


def aplicar_mapeamentos_kanban(db: Session, projeto: Projeto,
                               valores: Dict[str, Any]) -> Optional[ProjetoContexto]:
    """Cria uma nova versão do contexto com os campos mapeados pelo Kanban.

    ``valores`` usa os nomes das colunas de ``projetos_contexto``.
    """
    valores = {k: v for k, v in (valores or {}).items() if k in CAMPOS_MAPEAVEIS}
    if not valores:
        return None

    anterior = ultimo(db, projeto.pipefy_id)
    ctx = novo_snapshot_contexto(
        projeto, anterior, "kanban", "Atualização via Kanban"
    )
    for campo, valor in valores.items():
        if isinstance(valor, (list, tuple)):
            texto = ", ".join(str(v) for v in valor if v not in (None, ""))
        else:
            texto = "" if valor is None else str(valor)
        texto = texto.strip()
        setattr(ctx, campo, texto or None)

    db.add(ctx)
    db.flush()
    return ctx
