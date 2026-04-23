
import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    res = conn.execute(text("SELECT email, nome FROM plataforma_geral.investidores"))
    for row in res:
        print(f"{row[0]} | {row[1]}")
