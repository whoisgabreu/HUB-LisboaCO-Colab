import sys
import os
from decimal import Decimal
from datetime import date
from sqlalchemy.orm.attributes import flag_modified

# Adiciona o diretório atual ao path para importar os módulos locais
sys.path.append(os.getcwd())

from database import Session
from models import ProjetoAtivo, MetricaMensal, InvestidorProjeto
from services.projeto_participacao_service import ProjetoParticipacaoService

def run_test_case(name, entry, exit_dt, expected_val):
    with Session() as db:
        print(f"\n--- Teste: {name} ---")
        
        pipefy_id = 999999999
        email = 'teste2@v4company.com'
        mes = 5
        ano = 2026
        
        projeto = db.query(ProjetoAtivo).filter(ProjetoAtivo.pipefy_id == pipefy_id).first()
        extra = dict(projeto.extra or {})
        if "investidores_metadata" not in extra: extra["investidores_metadata"] = {}
            
        extra["investidores_metadata"][email] = {
            "cientista_entrada": entry,
            "cientista_saida": exit_dt
        }
        projeto.extra = extra
        flag_modified(projeto, "extra")
        
        vinculo = db.query(InvestidorProjeto).filter(
            InvestidorProjeto.pipefy_id_projeto == pipefy_id,
            InvestidorProjeto.email_investidor == email
        ).first()
        vinculo.cientista = True
        vinculo.active = True
        vinculo.inactivated_at = None
        
        db.commit()
        
        ProjetoParticipacaoService.sincronizar_remuneracao(mes, ano)
        
        metrica = db.query(MetricaMensal).filter(
            MetricaMensal.email_investidor == email,
            MetricaMensal.mes == mes,
            MetricaMensal.ano == ano
        ).first()
        
        item = next((i for i in metrica.historico_projetos if str(i.get("projeto_id")) == str(pipefy_id)), None)
        valor_calculado = Decimal(str(item.get("valor_proporcional")))
        
        print(f"Calculado: {valor_calculado} | Esperado: {expected_val}")
        if abs(valor_calculado - expected_val) <= Decimal("0.01"):
            print("OK!")
            return True
        else:
            print("FALHA!")
            return False

if __name__ == "__main__":
    # Caso 1: 10 dias cientista (1 a 10)
    # (10 * 1500 + 21 * 1000) / 31 = 1161.29
    res1 = run_test_case("Parcial com saída", "2026-05-01", "2026-05-10", Decimal("1161.29"))
    
    # Caso 2: 21 dias cientista (11 a 31) - Saída NULL
    # (10 * 1000 + 21 * 1500) / 31 = 1338.71
    res2 = run_test_case("Parcial com saída NULL", "2026-05-11", None, Decimal("1338.71"))
    
    # Caso 3: 31 dias cientista (1 a 31)
    # (31 * 1500) / 31 = 1500.00
    res3 = run_test_case("Mês inteiro como cientista", "2026-05-01", None, Decimal("1500.00"))
    
    if res1 and res2 and res3:
        print("\nTODOS OS TESTES PASSARAM!")
        sys.exit(0)
    else:
        print("\nALGO FALHOU.")
        sys.exit(1)
