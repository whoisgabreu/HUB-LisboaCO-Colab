"""Simula save em registro legado responsavel='cientista' / tipo='CIENTISTA'
quando o vínculo atual virou cientista=False (não-cientista)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import _update_entrega_op_entregues

# Estado real: MF SELECT mes=4 do pedro.rezende
entregas_list = [{
    "cliente": "MF SELECT",
    "projeto_id": "1313908918",
    "responsavel": "cientista",
    "link_relatorio": "",
    "link_kpi": "",
    "link_forecast": "",
    "entregas": [
        {"nome": "relatorio_mensal",        "tipo": "CIENTISTA", "meta": 1, "entregues": 0},
        {"nome": "planner_monday",          "tipo": "CIENTISTA", "meta": 4, "entregues": 4},
        {"nome": "csat_checkin",            "tipo": "CIENTISTA", "meta": 1, "entregues": 1},
        {"nome": "forecasting",             "tipo": "CIENTISTA", "meta": 1, "entregues": 1},
        {"nome": "kpis",                    "tipo": "CIENTISTA", "meta": 1, "entregues": 1},
        {"nome": "plano_de_midia",          "tipo": "CIENTISTA", "meta": 1, "entregues": 1},
        {"nome": "documento_de_otimizacao", "tipo": "CIENTISTA", "meta": 4, "entregues": 4},
    ],
}]

# Vínculo atual: cientista=False, então a rota normaliza responsavel='gt' e tipo='gt'
# Frontend envia nome='relatorio_mensal' tipo_entrega='gt'
result = _update_entrega_op_entregues(
    entregas_list,
    projeto_id="1313908918",
    cliente_nome="MF SELECT",
    responsavel="gt",
    nome_entrega="relatorio_mensal",
    tipo_entrega="gt",
    valor=1,
)

print("\n=== Após simular clique + Relatório Mensal (vínculo gt, JSON legado CIENTISTA) ===")
for it in result[0]["entregas"]:
    flag = " <-- ALTERADO" if it["nome"] == "relatorio_mensal" else ""
    print(f"  nome={it['nome']!r:<32} tipo={it['tipo']!r:<12} entregues={it['entregues']}/{it['meta']}{flag}")

rel = next((i for i in result[0]["entregas"] if i["nome"] == "relatorio_mensal"), None)
print()
print("[OK]" if rel and rel["entregues"] == 1 else "[FALHA]", f"Relatório Mensal entregues = {rel['entregues'] if rel else 'None'}")
