import pandas as pd
import sys
import logging
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text  
from .db import get_engine

# ----------------------------
# Logging Setup
# ----------------------------
logger = logging.getLogger("load")
logger.setLevel(logging.DEBUG)

# Console handler - Redirects to Azure Log Stream
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)

# NOTE: Removed fh = logging.FileHandler("load.log") to fix OSError: [Errno 30]
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)

logger.addHandler(ch)

# ----------------------------
# Load Function
# ----------------------------

def load_table(df: pd.DataFrame, table_name: str, if_exists="replace"):
    """
    Loads a DataFrame into SQL Server.

    Args:
        df (pd.DataFrame): Data to load
        table_name (str): Destination table
        if_exists (str): "replace", "append", or "fail"
    """
    engine = get_engine()

    try:
        if df is None or df.empty:
            logger.warning(f"Skipping load for '{table_name}': DataFrame is empty.")
            return

        logger.info(f"Loading '{table_name}' ({len(df)} rows) using mode: {if_exists}...")
        
        # to_sql handles the bulk insertion
        df.to_sql(
            name=table_name,
            con=engine,
            if_exists=if_exists,
            index=False,
            chunksize=1000 # Better memory management for larger loads
        )
        logger.info(f"Successfully loaded table: {table_name}")

    except SQLAlchemyError as e:
        logger.error(f"❌ Failed loading table '{table_name}': {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error loading '{table_name}': {e}")


# ----------------------------
# Full Load Pipeline (Star Schema)
# ----------------------------
def load_transformed_schema(
    dim_customers,
    dim_products,
    dim_date,
    fact_orders,
    fact_order_items,
    mode="replace"
):
    engine = get_engine()
    logger.info("=== Starting Load Phase ===")

    if mode == "replace":
        # We manually clear tables in reverse order of dependencies
        # Facts first, then Dimensions
        with engine.begin() as conn:
            logger.info("Clearing existing data (maintaining schema)...")
            conn.execute(text("DELETE FROM FactOrderItems"))
            conn.execute(text("DELETE FROM FactOrders"))
            conn.execute(text("DELETE FROM DimCustomers"))
            conn.execute(text("DELETE FROM DimProducts"))
            conn.execute(text("DELETE FROM DimDate"))
        
        # Now we use "append" because the tables are empty but the schema exists
        current_mode = "append"
    else:
        current_mode = mode

    # Load Dimensions
    load_table(dim_customers, "DimCustomers", if_exists=current_mode)
    load_table(dim_products, "DimProducts", if_exists=current_mode)
    load_table(dim_date, "DimDate", if_exists=current_mode)

    # Load Facts
    load_table(fact_orders, "FactOrders", if_exists=current_mode)
    load_table(fact_order_items, "FactOrderItems", if_exists=current_mode)

    logger.info("=== Load Phase Complete ===")


# ----------------------------
# Optional: run standalone
# ----------------------------
if __name__ == "__main__":
    logger.info("load.py should be called from the ETL pipeline, not directly.")