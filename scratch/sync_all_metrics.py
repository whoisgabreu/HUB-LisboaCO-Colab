import sys
import os
sys.path.append(os.getcwd())
from database import Session
from services.remuneracao import calcular_metricas_mensais

mes = 4
ano = 2026

print(f"Sincronizando metricas de TODOS para {mes}/{ano}...")
calcular_metricas_mensais(mes, ano)
print("Concluido!")
