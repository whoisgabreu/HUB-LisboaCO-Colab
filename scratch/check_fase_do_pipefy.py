import sys
import os
sys.path.append(os.getcwd())
from database import Session
from models import Projeto
from sqlalchemy import func

def check_fase():
    with Session() as db:
        print("Count of projects with null/empty fase_do_pipefy:")
        null_count = db.query(Projeto).filter((Projeto.fase_do_pipefy == None) | (Projeto.fase_do_pipefy == '')).count()
        print(f"Null/Empty: {null_count}")
        
        print("\nDistinct values of fase_do_pipefy:")
        fases = db.query(Projeto.fase_do_pipefy, func.count(Projeto.fase_do_pipefy)).group_by(Projeto.fase_do_pipefy).all()
        for f, count in fases:
            print(f"- {f}: {count}")

        print("\nCount of projects with kanban_dados:")
        kd_count = db.query(Projeto).filter(Projeto.kanban_dados != None).count()
        print(f"With kanban_dados: {kd_count}")

if __name__ == "__main__":
    check_fase()
