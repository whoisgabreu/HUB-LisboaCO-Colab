import sys
import os
sys.path.append(os.getcwd())
from database import Session
from models import Investidor
from werkzeug.security import generate_password_hash

def set_password():
    with Session() as db:
        u = db.query(Investidor).filter_by(email='ronaldo.teixeira@v4company.com').first()
        if u:
            u.senha = generate_password_hash('admin123')
            db.commit()
            print("Password updated successfully for ronaldo.teixeira@v4company.com to 'admin123'")
        else:
            print("User not found.")

if __name__ == "__main__":
    set_password()
