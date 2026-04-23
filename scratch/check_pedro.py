import sys
import os
sys.path.append(os.getcwd())
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    sql = "SELECT funcao, senioridade, nivel FROM plataforma_geral.investidores WHERE email = 'pedro.vitorino@v4company.com'"
    res = conn.execute(text(sql)).fetchone()
    print("Pedro:", res)
    if res:
        sql2 = "SELECT fixo_mrr_teto FROM plataforma_geral.remuneracao_cargos WHERE fixo_cargo = :c AND fixo_senioridade = :s AND fixo_level = :l"
        teto = conn.execute(text(sql2), {"c": res[0], "s": res[1], "l": res[2]}).scalar()
        print("Teto do cargo:", teto)

        sql3 = "SELECT motivo_flag, fixo_mrr_projeto_total FROM plataforma_geral.investidores_metricas_mensais_novo WHERE email_investidor = 'pedro.vitorino@v4company.com' AND mes = 4 AND ano = 2026"
        metrica = conn.execute(text(sql3)).fetchone()
        print("Metrica atual:", metrica)
