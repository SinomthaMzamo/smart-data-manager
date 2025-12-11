from .db import get_engine
from sqlalchemy import text

def test_connection():
    engine = get_engine()

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT TOP 1 * FROM Products;"))
            print("✅ Connection successful!")
            for row in result:
                print(row)
    except Exception as e:
        print("❌ Connection failed:", e)

if __name__ == "__main__":
    test_connection()
