Jimport json
from app import _update_entrega_op_links

lista = [
    {
        "cliente": "Agra Astro",
        "entregas": [
            {"meta": 1, "nome": "relatorio_mensal", "tipo": "account", "entregues": 1}
        ],
        "projeto_id": "123",
        "responsavel": "account",
        "link_forecast": "",
        "link_relatorio": ""
    }
]

nova = _update_entrega_op_links(lista, "123", "Agra Astro", "account", link_relatorio="https://test.com")
print(json.dumps(nova, indent=2))
