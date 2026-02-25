from services.remuneracao import calcular_metricas_mensais
from database import Session
from models import MetricaMensal, InvestidorProjeto
from datetime import datetime
from decimal import Decimal

def verify():
    print("--- Verificação Final: Escala e Centralização ---")
    mes = datetime.now().month
    ano = datetime.now().year
    
    try:
        # 1. Verificar se investidores_projetos tem os dados centralizados
        with Session() as db:
            vinc = db.query(InvestidorProjeto).first()
            if vinc:
                print(f"InvestidorProjeto Check: Nome={vinc.nome_projeto}, Fee={vinc.fee_projeto}, Contrib={vinc.fee_contribuicao}")
            else:
                print("ERRO: Nenhum vínculo encontrado em investidores_projetos.")

        # 2. Rodar processamento
        print(f"Processando métricas para {mes}/{ano}...")
        calcular_metricas_mensais(mes, ano)
        
        # 3. Validar resultados na tabela de métricas
        with Session() as db:
            metricas = db.query(MetricaMensal).filter_by(mes=mes, ano=ano).all()
            if not metricas:
                print("ERRO: Nenhuma métrica gerada.")
                return

            print(f"Total de métricas geradas: {len(metricas)}")
            for m in metricas[:3]:  # Mostrar os 3 primeiros
                print(f"\nInvestidor: {m.email_investidor}")
                print(f"  MRR Atual: {m.fixo_mrr_atual}")
                print(f"  Churn Atual: {m.fixo_churn_atual}")
                print(f"  Flag: {m.flag}")
                if m.fixo_mrr_atual > 1000000:
                    print("  !!! ALERTA: MRR parece estar em centavos (valor muito alto).")
                else:
                    print("  Escala: OK (R unidades)")
                
    except Exception as e:
        print(f"ERRO NO TESTE: {e}")

if __name__ == "__main__":
    verify()
