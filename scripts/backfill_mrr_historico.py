"""Backfill aproximado do histórico mensal de MRR por projeto.

Usa o fee ATUAL de cada projeto para reconstruir os meses entre
data_de_inicio e data_fim (ou hoje). Para projetos já Inativos, marca o mês
de churn aproximado pela data_fim (ou o mês atual, se não houver data).

Usage:
    python scripts/backfill_mrr_historico.py [ano_inicio]
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Session
from services.mrr_historico_service import MrrHistoricoService


def run(ano_inicio: int = 2020):
    print(f"Iniciando backfill a partir de {ano_inicio}...")
    with Session() as db:
        criados = MrrHistoricoService(db).backfill(ano_inicio=ano_inicio)
    print(f"Backfill concluído: {criados} linhas processadas.")


if __name__ == "__main__":
    ano = int(sys.argv[1]) if len(sys.argv) > 1 else 2020
    run(ano)
