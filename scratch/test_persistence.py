import requests

BASE_URL = "http://localhost:5000" # Ajuste se necessário

def test_save_link():
    payload = {
        "email_investidor": "gabriel@test.com", # Substituir por um email real se necessário
        "mes": 4,
        "ano": 2026,
        "projeto_id": "1291767668",
        "cliente": "Agra Astro",
        "responsavel": "account",
        "link_relatorio": "https://google.com/relatorio"
    }
    
    # Nota: Precisamos de uma sessão autenticada. 
    # Como este é um teste local, podemos tentar rodar o código de dentro do app.py se for mais fácil,
    # ou usar um e-mail que já existe no banco.
    
    print(f"Testando salvamento de link para {payload['email_investidor']}...")
    # Aqui eu precisaria de um cookie de sessão, o que dificulta o teste via requests externo.
    # Vou fazer o teste via SQLAlchemy direto no banco para validar o helper.

if __name__ == "__main__":
    # test_save_link()
    pass
