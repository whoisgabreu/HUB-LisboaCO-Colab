from app import app
from services.projeto_participacao_service import ProjetoParticipacaoService
from services.remuneracao import calcular_metricas_mensais

with app.app_context():
    print("Iniciando sincronização de remuneração para 05/2026...")
    ProjetoParticipacaoService.sincronizar_remuneracao(5, 2026)
    print("Sincronização concluída.")
    
    print("Iniciando cálculo de métricas mensais para 05/2026...")
    calcular_metricas_mensais(5, 2026)
    print("Cálculo concluído.")
