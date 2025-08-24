# tasks.py
import os
import io
import pandas as pd
from celery import Celery
from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv

load_dotenv()

BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BACKEND = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MONGO_URI = os.getenv("MONGO_URI")

celery = Celery("cutm_tasks", broker=BROKER_URL, backend=CELERY_BACKEND)

client = MongoClient(MONGO_URI)
db = client.get_database("cutm")
cutm_collection = db.get_collection("CUTM")

def normalize_row(row):
    reg_no = str(row.get('Reg_No') or row.get('Registration No.') or "").strip().upper()
    subject_code = str(row.get('Subject_Code') or row.get('Subject Code') or "").strip().upper()
    subject_name = str(row.get('Subject_Name') or row.get('Subject Name') or "").strip()
    name = str(row.get('Name') or "").strip()
    sem = str(row.get('Sem') or "").strip()
    credits = str(row.get('Credits') or row.get('Credit') or "").strip()
    grade = str(row.get('Grade') or row.get('Grade Point') or "").strip().upper()
    subject_type = str(row.get('Subject_Type') or row.get('Subject Type') or "").strip()
    sem_value = f"Sem {sem}" if sem.isdigit() else sem
    return reg_no, subject_code, subject_name, name, sem_value, credits, grade, subject_type

@celery.task(name="tasks.process_upload")
def process_upload(file_bytes, filename):
    updated_count = 0
    inserted_count = 0

    # Read to DataFrame (chunking for CSV)
    if filename.lower().endswith('.csv'):
        bio = io.BytesIO(file_bytes)
        # You can iterate chunks if files are huge:
        df_iter = pd.read_csv(bio, chunksize=5000)
        for df in df_iter:
            u, i = _bulk_upsert(df)
            updated_count += u
            inserted_count += i
    else:
        df = pd.read_excel(io.BytesIO(file_bytes))
        u, i = _bulk_upsert(df)
        updated_count += u
        inserted_count += i

    # Invalidate cached reads after data changes
    try:
        from cache import cache_delete_prefix
        cache_delete_prefix("sem:")
        cache_delete_prefix("res:")
        cache_delete_prefix("cgpa:")
    except Exception:
        pass

    return {"updated": updated_count, "inserted": inserted_count}

def _bulk_upsert(df: pd.DataFrame):
    ops = []
    updated_count = 0
    inserted_count = 0

    for _, row in df.iterrows():
        reg_no, subject_code, subject_name, name, sem_value, credits, grade, subject_type = normalize_row(row)
        if not reg_no or not subject_code:
            continue

        filter_q = {"Reg_No": reg_no, "Subject_Code": subject_code}

        # Two-step logic via bulk ops:
        # 1) Update grade if existing grade is F/S/M
        ops.append(UpdateOne(
            {**filter_q, "Grade": {"$in": ["F", "S", "M"]}},
            {"$set": {"Grade": grade}},
            upsert=False
        ))

        # 2) Upsert if not existing
        ops.append(UpdateOne(
            filter_q,
            {"$setOnInsert": {
                "Reg_No": reg_no, "Subject_Code": subject_code, "Grade": grade,
                "Name": name, "Sem": sem_value, "Subject_Name": subject_name,
                "Subject_Type": subject_type, "Credits": credits
            }},
            upsert=True
        ))

    if ops:
        res = cutm_collection.bulk_write(ops, ordered=False)
        # The counts below are estimates; precise split is tricky with UpdateOne combos.
        updated_count = res.modified_count
        inserted_count = res.upserted_count

    return updated_count, inserted_count
