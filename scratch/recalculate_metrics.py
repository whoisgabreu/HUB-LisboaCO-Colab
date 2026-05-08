import os
import sys
sys.path.append(os.getcwd())
from app import app
from services.remuneracao import calcular_metricas_mensais

def run():
    with app.app_context():
        print("Recalculating April 2026...")
        calcular_metricas_mensais(4, 2026)
        print("Recalculating May 2026...")
        calcular_metricas_mensais(5, 2026)
        print("Done!")

if __name__ == "__main__":
    run()
