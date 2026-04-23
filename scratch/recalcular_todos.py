"""
Recálculo de métricas mensais para todos os investidores.
Usa o serviço oficial calcular_metricas_mensais.
"""
import sys
import os
sys.path.append(os.getcwd())
from services.remuneracao import calcular_metricas_mensais

mes = 4
ano = 2026

print(f"Iniciando recalculo para {mes:02d}/{ano}...")
calcular_metricas_mensais(mes, ano)
print(f"Recalculo concluido para {mes:02d}/{ano}!")
