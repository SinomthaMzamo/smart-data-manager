import logging
import sys
from .extract import extract_table
from .transform import transform_all
from .load import load_transformed_schema

# ----------------------------
# Logging Setup
# ----------------------------
# We use a standard logger that outputs to the console (stdout).
# Azure Functions captures this stream and redirects it to Application Insights.
logger = logging.getLogger("run_etl")
logger.setLevel(logging.DEBUG)

# Console handler
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)

# NOTE: We removed fh = logging.FileHandler(...) to avoid OSError on Azure.
logger.addHandler(ch)

# ----------------------------
# ETL Pipeline
# ----------------------------
def run_etl():
    logger.info("=== ETL Pipeline Started ===")

    # ---------- Extraction ----------
    logger.info("Starting Extraction Phase")
    customers_df = extract_table("Customers")
    products_df = extract_table("Products")
    orders_df = extract_table("Orders")
    order_items_df = extract_table("OrderItems")
    
    if customers_df.empty or products_df.empty:
        logger.error("Critical tables are empty. Aborting ETL.")
        return
        
    logger.info("Extraction Phase Completed")

    # ---------- Transformation ----------
    logger.info("Starting Transformation Phase")
    transformed_data = transform_all(customers_df, products_df, orders_df, order_items_df)
    logger.info("Transformation Phase Completed")

    # ---------- Loading ----------
    logger.info("Starting Load Phase")
    try:
        load_transformed_schema(
            dim_customers=transformed_data["dim_customers"],
            dim_products=transformed_data["dim_products"],
            dim_date=transformed_data["dim_date"],
            fact_orders=transformed_data["fact_orders"],
            fact_order_items=transformed_data["fact_order_items"],
            mode="replace"
        )
        logger.info("Load Phase Completed")
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        raise

    logger.info("=== ETL Pipeline Finished Successfully ===")

# ----------------------------
# Optional: Run directly
# ----------------------------
if __name__ == "__main__":
    run_etl()