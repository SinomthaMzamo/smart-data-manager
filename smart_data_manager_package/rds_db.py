import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

def get_engine():
    host = os.getenv("AWS_DB_HOST")        # e.g. mydb.abcd1234xyz.us-east-1.rds.amazonaws.com
    port = os.getenv("AWS_DB_PORT", "5432")
    database = os.getenv("AWS_DB_NAME")
    username = os.getenv("AWS_DB_USERNAME")
    password = os.getenv("AWS_DB_PASSWORD")

    if not all([host, port, database, username, password]):
        raise ValueError("One or more database environment variables are missing.")

    # PostgreSQL connection URL (psycopg2)
    url = f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}"

    return create_engine(url)
