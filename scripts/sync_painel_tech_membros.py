"""Sincroniza os membros do Painel Gerencial TECH com os usuários TECH do HUB.

- Remove TODOS os membros atuais do painel (dados de teste; FKs são ON DELETE SET NULL).
- Insere como membros os usuários do HUB com capacidade 'tech'
  (posição 'Tech' ou cargo que concede a capacidade 'tech').

Usage:
    python scripts/sync_painel_tech_membros.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def sync():
    from painel_tech import db as pdb

    tech = pdb.listar_usuarios_tech()
    removidos = len(pdb.listar_membros())

    pdb.limpar_membros()
    for u in tech:
        pdb.criar_membro(u["nome"], u.get("email"), u.get("id"))

    print(f"Membros removidos: {removidos}")
    print(f"Membros TECH inseridos: {len(tech)}")
    for u in tech:
        print(f"  - {u['nome']} <{u.get('email')}> (hub_user_id={u.get('id')})")


if __name__ == "__main__":
    sync()