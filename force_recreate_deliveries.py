
from database import engine, Base
from models import MonthlyDelivery
from sqlalchemy import text

with engine.connect() as conn:
    print("--- Forcing Recreate of MonthlyDelivery ---")
    
    # Drop the table with cascade for safety
    print("Dropping old table if exists...")
    conn.execute(text("DROP TABLE IF EXISTS plataforma_geral.monthly_deliveries CASCADE"))
    conn.commit()
    print("Table dropped.")

# Use SQLAlchemy to recreate it properly
print("Creating new table from model...")
MonthlyDelivery.__table__.create(bind=engine)
print("Table plataforma_geral.monthly_deliveries recreated successfully.")
