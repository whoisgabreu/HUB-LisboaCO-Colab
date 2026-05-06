import urllib.request
import json

url = "http://127.0.0.1:5000/api/criativa/entregas/entregues"
data = {
    "email_investidor": "carlos@example.com",
    "mes": 4,
    "ano": 2026,
    "projeto_id": "893675661",
    "cliente": "Cliente Teste",
    "categoria": "criativos",
    "valor": 1
}

req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='PUT')
try:
    with urllib.request.urlopen(req) as response:
        print("Success:", response.read().decode())
except urllib.error.HTTPError as e:
    print(f"HTTPError {e.code}:")
    print(e.read().decode())
except Exception as e:
    print("Exception:", str(e))
