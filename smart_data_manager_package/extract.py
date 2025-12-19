import pandas as pd
import logging
from sqlalchemy import text
from .db import get_engine

logger = logging.getLogger("run_etl")

def extract_table(table_name, preview_rows=5):
    """Extracts data from a SQL Server table into a pandas DataFrame."""
    engine = get_engine()
    
    try:
        query = text(f"SELECT * FROM {table_name}")
        df = pd.read_sql(query, engine)

        if df.empty:
            logger.warning(f"⚠️ Table '{table_name}' is empty.")
        else:
            logger.info(f"✅ Table '{table_name}' extracted. Rows: {len(df)}")
        
        return df

    except Exception as e:
        logger.error(f"❌ Failed to extract table '{table_name}': {e}")
        return pd.DataFrame() 

if __name__ == "__main__":
    customers_df = extract_table("Customers")
    products_df = extract_table("Products")
    orders_df = extract_table("Orders")
    order_items_df = extract_table("OrderItems")