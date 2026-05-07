
import traceback
from app import app

def test_flask_home():
    app.config['TESTING'] = True
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['nome'] = 'Gabriel Henrique'
            sess['email'] = 'gabriel.soares@v4company.com'
            sess['funcao'] = 'Gerência'
            sess['posicao'] = 'Gerência'
        
        response = client.get('/')
        print(f"Status Code: {response.status_code}")
        # print(response.text[:500])

if __name__ == '__main__':
    test_flask_home()
