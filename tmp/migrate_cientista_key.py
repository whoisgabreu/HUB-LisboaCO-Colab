import os
import sys
from decimal import Decimal
from datetime import datetime, date

# Setup paths
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.append(root_dir)

from sqlalchemy import text
from database import Session
from services.currency import CurrencyService
from sqlalchemy.orm.attributes import flag_modified

def migrate():
    with Session() as db:
        # 1. Fetch all scientist flags
        res = db.execute(text("SELECT email_investidor, pipefy_id_projeto, cientista FROM plataforma_geral.investidores_projetos"))
        scientists_map = {}
        for email, pid, cientista in res:
            scientists_map[(email, str(pid))] = bool(cientista)

        # 2. Fetch conversion rate
        rate_usd = CurrencyService.get_usd_to_brl_rate()
        print(f"Current USD conversion rate: {rate_usd}")

        # 3. Fetch metrics with historico_projetos
        res = db.execute(text("SELECT email_investidor, mes, ano, historico_projetos FROM plataforma_geral.investidores_metricas_mensais_novo WHERE historico_projetos IS NOT NULL"))
        rows = res.fetchall()
        
        updated_count = 0
        from models import MetricaMensal

        for email, mes, ano, historico in rows:
            if not historico:
                continue
                
            changed = False
            total_proporcional_brl = Decimal("0.00")
            
            new_historico = []
            for item in historico:
                p_id = str(item.get("projeto_id"))
                is_scientist = scientists_map.get((email, p_id), False)
                
                # Check if key is already there and correct
                if "cientista" not in item or item["cientista"] != is_scientist:
                    item["cientista"] = is_scientist
                    changed = True
                
                # Recalculate valor_proporcional if it's a scientist
                # We need data_inicio, data_fim, fee_projeto, and total_dias_mes from the item
                fee_projeto = Decimal(str(item.get("fee_projeto") or 0))
                fee_base = fee_projeto
                if is_scientist:
                    fee_base *= Decimal("1.5")
                
                # We can't easily call ProjectoParticipacaoService.calcular_valor_proporcional here without re-importing
                # but we can do the math: valor = (dias * fee_base) / total_dias
                # Actually, let's just use the ratio of (new_fee / old_fee) if possible, but that's risky if old_fee was 0.
                # Let's perform the same calculation as in the service.
                
                data_inicio = date.fromisoformat(item["data_inicio"])
                data_fim_str = item.get("data_fim")
                data_fim = date.fromisoformat(data_fim_str) if data_fim_str else None
                
                # Days worked in month
                import calendar
                total_dias_mes = calendar.monthrange(ano, mes)[1]
                inicio_mes = date(ano, mes, 1)
                fim_mes = date(ano, mes, total_dias_mes)
                
                d_fim_calc = data_fim if data_fim else fim_mes
                d_inicio_calc = max(data_inicio, inicio_mes)
                d_fim_calc = min(d_fim_calc, fim_mes)
                
                if d_inicio_calc <= d_fim_calc:
                    dias_trabalhados = (d_fim_calc - d_inicio_calc).days + 1
                    new_val_prop = (Decimal(dias_trabalhados) * fee_base) / Decimal(total_dias_mes)
                    new_val_prop = new_val_prop.quantize(Decimal("0.01"))
                else:
                    new_val_prop = Decimal("0.00")
                
                if float(new_val_prop) != item.get("valor_proporcional"):
                    item["valor_proporcional"] = float(new_val_prop)
                    changed = True
                
                new_historico.append(item)
                
                # Sum for BRL totals
                val_item_brl = new_val_prop
                if item.get("moeda") == "USD":
                    val_item_brl *= rate_usd
                total_proporcional_brl += val_item_brl

            if changed:
                total_proporcional_brl = total_proporcional_brl.quantize(Decimal("0.01"))
                
                db.execute(text("""
                    UPDATE plataforma_geral.investidores_metricas_mensais_novo 
                    SET historico_projetos = :h,
                        fixo_mrr_entrega = :mrr_e,
                        fixo_mrr_projeto_total = :mrr_t
                    WHERE email_investidor = :e AND mes = :m AND ano = :a
                """), {
                    "h": json_dumps(new_historico),
                    "mrr_e": total_proporcional_brl,
                    "mrr_t": total_proporcional_brl,
                    "e": email,
                    "m": mes,
                    "a": ano
                })
                updated_count += 1
                
        db.commit()
        print(f"Updated {updated_count} records.")

def json_dumps(obj):
    import json
    return json.dumps(obj)

if __name__ == "__main__":
    migrate()
