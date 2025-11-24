import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
import logging
from db import get_engine

# ----------------------------
# Logging Setup
# ----------------------------
logger = logging.getLogger("load")
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

fh = logging.FileHandler("load.log", mode="w")
fh.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
fh.setFormatter(formatter)

logger.addHandler(ch)
logger.addHandler(fh)

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
        logger.info(f"Loading '{table_name}' ({len(df)} rows)...")
        df.to_sql(
            name=table_name,
            con=engine,
            if_exists=if_exists,
            index=False
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
    fact_orders,
    fact_order_items,
    mode="replace"
):
    """
    Loads all transformed tables into SQL Server in correct FK order.

    Args:
        mode (str): "replace" or "append"
    """

    logger.info("=== Starting Load Phase ===")

    # Load Dimensions first
    load_table(dim_customers, "DimCustomers", if_exists=mode)
    load_table(dim_products, "DimProducts", if_exists=mode)

    # Load Facts afterwards
    load_table(fact_orders, "FactOrders", if_exists=mode)
    load_table(fact_order_items, "FactOrderItems", if_exists=mode)

    logger.info("=== Load Phase Complete ===")


# ----------------------------
# Optional: run standalone
# ----------------------------
if __name__ == "__main__":
    logger.info("load.py should be called from the ETL pipeline, not directly.")
