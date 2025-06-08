from db import SessionLocal
from sqlalchemy import text

def test_connection():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1")) 
        db.close()
        print("✅ Database connection successful!")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

test_connection()
