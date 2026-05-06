"""
Script de diagnóstico: por que o check-in aparece na aba operação mas não na aba /criativa.
Verifica:
1. O snapshot (tabela operacao) — o que a aba operação lê
2. A MetricaMensal.entregas_operacao — o que a aba criativa lê
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Session, engine
from models import MetricaMensal, Investidor, InvestidorProjeto
from sqlalchemy import text
from datetime import datetime
import json

MES = datetime.now().month
ANO = datetime.now().year

def main():
    # Buscar o Isaac
    with Session() as db:
        inv = db.query(Investidor).filter(Investidor.nome.ilike("%isaac%")).first()
        if not inv:
            print("Isaac não encontrado!")
            return
        
        email = inv.email
        funcao = inv.funcao
        print(f"=== INVESTIDOR: {inv.nome} ({email}) | Função: {funcao} ===\n")
        
        # Buscar vínculos
        vinculos = db.query(InvestidorProjeto).filter_by(email_investidor=email).all()
        print(f"--- {len(vinculos)} vínculo(s) ---")
        for v in vinculos:
            print(f"  Projeto: {v.nome_projeto} (ID: {v.pipefy_id_projeto}) | Cientista: {v.cientista} | Ativo: {v.active}")
        
        # Buscar Grunn
        grunn_vinc = next((v for v in vinculos if v.nome_projeto and "grunn" in v.nome_projeto.lower()), None)
        if not grunn_vinc:
            print("\nGrunn não encontrado nos vínculos. Listando todos:")
            for v in vinculos:
                print(f"  {v.nome_projeto} | PipefyID={v.pipefy_id_projeto}")
            return
        
        pipefy_id = grunn_vinc.pipefy_id_projeto
        print(f"\n=== PROJETO GRUNN: PipefyID={pipefy_id} ===\n")
        
        # 1. Ler snapshot da tabela operacao (o que a aba "Entregas do Mês" lê)
        row = db.execute(text(
            "SELECT entregas FROM plataforma_geral.operacao "
            "WHERE id_projeto = :id AND mes = :mes AND ano = :ano LIMIT 1"
        ), {"id": str(pipefy_id), "mes": MES, "ano": ANO}).first()
        
        if row and row.entregas:
            snap = row.entregas if isinstance(row.entregas, dict) else json.loads(row.entregas)
            checkins = snap.get("checkin_semanal") or []
            print(f"[SNAPSHOT] checkin_semanal: {len(checkins)} item(s)")
            for i, c in enumerate(checkins):
                print(f"  [{i}] {json.dumps(c, ensure_ascii=False)[:200]}")
        else:
            print("[SNAPSHOT] NENHUM snapshot encontrado para este mês/ano!")
        
        # 2. Ler MetricaMensal (o que a aba /criativa lê)
        metrica = db.query(MetricaMensal).filter_by(
            email_investidor=email, mes=MES, ano=ANO
        ).first()
        
        if not metrica:
            print(f"\n[METRICA] MetricaMensal NÃO ENCONTRADA para {email} {MES}/{ANO}!")
            return
        
        print(f"\n[METRICA] MetricaMensal encontrada para {metrica.email_investidor} {metrica.mes}/{metrica.ano}")
        entregas_op = metrica.entregas_operacao or []
        print(f"[METRICA] entregas_operacao tem {len(entregas_op)} entrada(s)")
        
        entry = next((e for e in entregas_op if str(e.get("projeto_id")) == str(pipefy_id)), None)
        if not entry:
            print(f"[METRICA] NENHUMA entrada para projeto_id={pipefy_id} em entregas_operacao!")
            print(f"[METRICA] Projetos presentes: {[e.get('projeto_id') for e in entregas_op]}")
        else:
            print(f"[METRICA] Entrada encontrada: responsavel={entry.get('responsavel')}")
            print(f"[METRICA] Entregas:")
            for e in entry.get("entregas", []):
                print(f"  nome={e.get('nome'):30s} tipo={e.get('tipo'):10s} meta={e.get('meta')} entregues={e.get('entregues')}")
            print(f"[METRICA] Links: kpi={entry.get('link_kpi', 'N/A')} forecast={entry.get('link_forecast', 'N/A')} relatorio={entry.get('link_relatorio', 'N/A')}")
        
        # 3. Verificar se OperacaoTarefa existe
        print("\n--- Verificando tabela operacao_tarefas ---")
        try:
            result = db.execute(text("SELECT COUNT(*) FROM plataforma_geral.operacao_tarefas")).scalar()
            print(f"[OK] Tabela operacao_tarefas existe, {result} registro(s)")
        except Exception as ex:
            print(f"[ERRO] Tabela operacao_tarefas NÃO EXISTE: {ex}")
            db.rollback()

if __name__ == "__main__":
    main()
