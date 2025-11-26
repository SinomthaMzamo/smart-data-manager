import os
from sqlalchemy import create_engine
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_engine():
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_NAME")
    username = os.getenv("DB_USERNAME")
    password = os.getenv("DB_PASSWORD")
    driver = os.getenv("DB_DRIVER")

    if not all([server, database, username, password, driver]):
        raise ValueError("Database environment variables are missing.")

    # Build connection string
    connection_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
    )

    params = quote_plus(connection_str)
    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

    return engine
