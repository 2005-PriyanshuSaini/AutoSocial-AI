from db import SessionLocal
from sqlalchemy import text

def test_connection():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    finally:
        db.close()
