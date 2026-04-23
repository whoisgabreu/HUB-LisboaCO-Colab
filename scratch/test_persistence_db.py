import sys
import os

# Adiciona o diretório atual ao sys.path para importar os módulos locais
sys.path.append(os.getcwd())

from database import Session
from models import MetricaMensal
from app import _update_entrega_op_links, _get_or_create_entrega_record
from sqlalchemy.orm.attributes import flag_modified

def test_persistence():
    email = "gabriel.colaborador@v4company.com" # Ajuste para um email existente no banco
    mes = 4
    ano = 2026
    projeto_id = "1291767668"
    cliente_nome = "Agra Astro"
    responsavel = "account"
    link = "https://google.com/test-link-" + str(os.urandom(4).hex())

    print(f"--- TESTE DE PERSISTÊNCIA ---")
    print(f"Email: {email}")
    print(f"Projeto: {projeto_id} ({cliente_nome})")
    print(f"Link a ser salvo: {link}")

    try:
        with Session() as db:
            # 1. Busca ou cria o registro
            record = _get_or_create_entrega_record(db, email, mes, ano)
            print(f"Registro encontrado/criado: {record.email_investidor} ({record.mes}/{record.ano})")
            
            # 2. Atualiza os links
            lista_original = list(record.entregas_operacao or [])
            print(f"Tamanho da lista original: {len(lista_original)}")
            
            nova_lista = _update_entrega_op_links(
                lista_original,
                projeto_id, cliente_nome, responsavel,
                link_relatorio=link
            )
            
            record.entregas_operacao = nova_lista
            flag_modified(record, "entregas_operacao")
            db.commit()
            print("Commit realizado com sucesso.")

        # 3. Verifica se persistiu
        with Session() as db:
            record_verif = db.query(MetricaMensal).filter_by(
                email_investidor=email, mes=mes, ano=ano
            ).first()
            
            entregas = record_verif.entregas_operacao or []
            entry = next((e for e in entregas if str(e.get("projeto_id")) == str(projeto_id)), None)
            
            if entry and entry.get("link_relatorio") == link:
                print("SUCESSO: O link foi persistido corretamente no banco de dados.")
            else:
                print("FALHA: O link NÃO foi persistido ou o valor está incorreto.")
                if entry:
                    print(f"Valor encontrado: {entry.get('link_relatorio')}")
                else:
                    print("Projeto não encontrado na lista de entregas.")

    except Exception as e:
        print(f"ERRO durante o teste: {e}")

if __name__ == "__main__":
    test_persistence()
