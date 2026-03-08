"""
migrate_entregas_v2.py
======================
Cria as novas tabelas estruturais do sistema de entregas v2:
  - plataforma_geral.monthly_deliveries
  - plataforma_geral.operacao_links_uteis

Não remove nem altera a tabela legada operacao_entregas_mensais
(mantida em standby por 30 dias para rollback).

Executar com:
    python migrate_entregas_v2.py
"""

from database import engine, Base
from models import MonthlyDelivery, OperacaoLinkUtil
from sqlalchemy import text

print("=== Migração Entregas v2 ===")
print("Criando tabelas novas...")

# Cria apenas as novas tabelas sem tocar nas existentes
MonthlyDelivery.__table__.create(bind=engine, checkfirst=True)
print("  ✅ plataforma_geral.monthly_deliveries criada (ou já existia).")

OperacaoLinkUtil.__table__.create(bind=engine, checkfirst=True)
print("  ✅ plataforma_geral.operacao_links_uteis criada (ou já existia).")

print("\nMigração concluída com sucesso!")
print("A tabela legada 'operacao_entregas_mensais' foi preservada para rollback.")
