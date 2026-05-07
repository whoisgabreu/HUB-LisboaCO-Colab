"""Simula a chamada de _update_entrega_op_entregues exatamente como o frontend envia."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import _update_entrega_op_entregues

# Estado real do JSON do pedro.rezende para KUNTZ
entregas_list = [
    {
        "cliente": "KUNTZ SOCIEDADE DE ADVOGADOS",
        "projeto_id": "1291732048",
        "responsavel": "gt",
        "link_relatorio": "",
        "link_kpi": "",
        "entregas": [
            {"nome": "kpis",                    "tipo": "gt", "meta": 1, "entregues": 1},
            {"nome": "plano_de_midia",          "tipo": "gt", "meta": 1, "entregues": 0},
            {"nome": "documento_de_otimizacao", "tipo": "gt", "meta": 4, "entregues": 4},
            {"nome": "relatorio_gt",            "tipo": "gt", "meta": 1, "entregues": 0},
        ],
    }
]

# Simula clique + em Relatorio Mensal (frontend GT manda 'relatorio_mensal','gt')
result = _update_entrega_op_entregues(
    entregas_list,
    projeto_id="1291732048",
    cliente_nome="KUNTZ SOCIEDADE DE ADVOGADOS",
    responsavel="gt",
    nome_entrega="relatorio_mensal",
    tipo_entrega="gt",
    valor=1,
)

print("\n=== Após simular clique + Relatório Mensal ===")
for it in result[0]["entregas"]:
    flag = " <-- ALTERADO" if it["nome"] in ("relatorio_gt", "relatorio_mensal") else ""
    print(f"  nome={it['nome']!r:<32} tipo={it['tipo']!r:<8} entregues={it['entregues']}/{it['meta']}{flag}")

rel = next((i for i in result[0]["entregas"] if i["nome"] in ("relatorio_gt", "relatorio_mensal")), None)
if rel and rel["entregues"] == 1:
    print("\n[OK] Fix funciona — Relatório Mensal subiu para 1.")
else:
    print(f"\n[FALHA] Relatório Mensal NÃO foi atualizado: {rel}")
