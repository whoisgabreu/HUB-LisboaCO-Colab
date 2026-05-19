
import os
import json
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Configuração de logging básico
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_DATABASE = os.getenv("DB_DATABASE")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DATABASE_URL = f"postgresql+psycopg2://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

SCHEMA = "plataforma_geral"
TARGET_TABLE = "projetos"
SOURCE_TABLES = ["projetos_ativos", "projetos_inativos", "projetos_onetime"]

def is_empty(value):
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    # For JSONB, empty list or empty dict might be considered empty depending on intent,
    # but let's stick to None and "" for now as per instructions.
    return False

def sanitize_data():
    session = Session()
    report = {
        "updated": [],
        "missing_in_target": [],
        "conflicts": [],
        "inconsistencies": [],
        "summary": {
            "total_legacy_records": 0,
            "total_target_records": 0,
            "total_updates": 0,
            "fields_filled": 0
        }
    }

    try:
        # Load target records (projetos)
        log(f"Loading records from {TARGET_TABLE}...")
        target_records = session.execute(text(f'SELECT * FROM "{SCHEMA}"."{TARGET_TABLE}"')).fetchall()
        # Convert to dict for easier access, keyed by pipefy_id
        target_map = {r._mapping["pipefy_id"]: dict(r._mapping) for r in target_records if r._mapping["pipefy_id"] is not None}
        report["summary"]["total_target_records"] = len(target_map)

        # Load legacy records from all sources
        legacy_data = []
        for table in SOURCE_TABLES:
            log(f"Loading records from {table}...")
            records = session.execute(text(f'SELECT * FROM "{SCHEMA}"."{table}"')).fetchall()
            for r in records:
                d = dict(r._mapping)
                d["_source_table"] = table
                legacy_data.append(d)
        
        report["summary"]["total_legacy_records"] = len(legacy_data)

        updates_to_perform = {} # pipefy_id -> {field: value}

        for legacy_rec in legacy_data:
            pid = legacy_rec.get("pipefy_id")
            if pid not in target_map:
                report["missing_in_target"].append({
                    "pipefy_id": pid,
                    "nome": legacy_rec.get("nome"),
                    "source": legacy_rec["_source_table"]
                })
                continue

            target_rec = target_map[pid]
            updates = {}
            
            # Compare columns
            for col, val in legacy_rec.items():
                if col.startswith("_"): continue # Skip internal metadata
                
                if col in target_rec:
                    target_val = target_rec[col]
                    
                    if is_empty(target_val) and not is_empty(val):
                        # Candidate for update
                        if col in updates and updates[col] != val:
                            # Conflict: different legacy sources have different data for the same empty target field
                            report["conflicts"].append({
                                "pipefy_id": pid,
                                "field": col,
                                "val1": updates[col],
                                "val2": val,
                                "source": legacy_rec["_source_table"]
                            })
                        else:
                            updates[col] = val
            
            if updates:
                if pid not in updates_to_perform:
                    updates_to_perform[pid] = {}
                updates_to_perform[pid].update(updates)

        # Apply updates (DRY RUN by default)
        DRY_RUN = False # Safety first
        
        log(f"Found {len(updates_to_perform)} projects that need complementation.")
        
        for pid, fields in updates_to_perform.items():
            report["updated"].append({
                "pipefy_id": pid,
                "nome": target_map[pid].get("nome"),
                "fields": list(fields.keys())
            })
            report["summary"]["total_updates"] += 1
            report["summary"]["fields_filled"] += len(fields)
            
            if not DRY_RUN:
                # Build update statement
                set_clause = ", ".join([f'"{k}" = :{k}' for k in fields.keys()])
                # Pre-process params: convert dicts/lists to JSON strings for JSONB columns
                params = {"pid": pid}
                for k, v in fields.items():
                    if isinstance(v, (dict, list)):
                        params[k] = json.dumps(v)
                    else:
                        params[k] = v
                
                session.execute(
                    text(f'UPDATE "{SCHEMA}"."{TARGET_TABLE}" SET {set_clause} WHERE "pipefy_id" = :pid'),
                    params
                )

        if not DRY_RUN:
            session.commit()
            log("Updates committed successfully.")
        else:
            log("DRY RUN: No changes made to the database.")

        # Save report to a file
        report_path = "scratch/sanitation_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            # Handle decimals and dates for JSON serialization
            def default_serializer(obj):
                if isinstance(obj, (Decimal, date, datetime)):
                    return str(obj)
                raise TypeError(f"Type {type(obj)} not serializable")
            
            json.dump(report, f, indent=4, ensure_ascii=False, default=default_serializer)
        
        log(f"Report saved to {report_path}")
        return report

    except Exception as e:
        session.rollback()
        log(f"Error during sanitation: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    sanitize_data()
