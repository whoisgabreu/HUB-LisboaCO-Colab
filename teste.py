import requests as req
import json

url = "https://n8n.v4lisboatech.com.br/webhook/disgraça"

response = req.get(url, headers={"x-api-key": "4815162342"}, timeout=10)

print(json.dumps(response.json(), ensure_ascii = False, indent = 4))