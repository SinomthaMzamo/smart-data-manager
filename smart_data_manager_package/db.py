import os
from sqlalchemy import create_engine
from urllib.parse import quote_plus

def get_engine():
    """
    Create SQLAlchemy engine for Azure SQL Server.
    Works both locally (with .env) and in Azure Functions (with Key Vault references).
    """
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_NAME")
    username = os.getenv("DB_USERNAME")
    password = os.getenv("DB_PASSWORD")
    driver = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")

    if not all([server, database, username, password]):
        raise ValueError(
            "Database environment variables are missing. Required: "
            "DB_SERVER, DB_NAME, DB_USERNAME, DB_PASSWORD"
        )

    # Build connection string for Azure SQL
    connection_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER=tcp:{server},1433;"  # Explicit TCP and port
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )

    params = quote_plus(connection_str)
    connection_url = f"mssql+pyodbc:///?odbc_connect={params}"
    
    # Create engine with appropriate settings for Azure
    engine = create_engine(
        connection_url,
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,   # Recycle connections every hour
        echo=False           # Set to True for debugging
    )

    return engine


def test_connection():
    """Test database connection - useful for debugging"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute("SELECT @@VERSION as version")
            version = result.fetchone()
            print(f"✅ Successfully connected to SQL Server")
            print(f"   Version: {version[0][:50]}...")
            return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


if __name__ == "__main__":
    test_connection()