from app import app
from services.projeto_participacao_service import ProjetoParticipacaoService
from services.remuneracao import calcular_metricas_mensais

with app.app_context():
    for m in [2, 3]:
        print(f"Iniciando sincronização de remuneração para {m:02d}/2026...")
        ProjetoParticipacaoService.sincronizar_remuneracao(m, 2026)
        print("Sincronização concluída.")
        
        print(f"Iniciando cálculo de métricas mensais para {m:02d}/2026...")
        calcular_metricas_mensais(m, 2026)
        print("Cálculo concluído.")
