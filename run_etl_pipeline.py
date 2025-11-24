import logging
from extract import extract_table
from transform import transform_all
from load import load_transformed_schema

# ----------------------------
# Logging Setup
# ----------------------------
logger = logging.getLogger("run_etl")
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

fh = logging.FileHandler("run_etl.log", mode="w")
fh.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
fh.setFormatter(formatter)

logger.addHandler(ch)
logger.addHandler(fh)

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
    logger.info("Extraction Phase Completed")

    # ---------- Transformation ----------
    logger.info("Starting Transformation Phase")
    transformed_data = transform_all(customers_df, products_df, orders_df, order_items_df)
    logger.info("Transformation Phase Completed")

    # ---------- Loading ----------
    logger.info("Starting Load Phase")
    load_transformed_schema(
        dim_customers=transformed_data["dim_customers"],
        dim_products=transformed_data["dim_products"],
        fact_orders=transformed_data["fact_orders"],
        fact_order_items=transformed_data["fact_order_items"],
        mode="replace"  # can switch to "append" if incremental load
    )
    logger.info("Load Phase Completed")
    logger.info("=== ETL Pipeline Finished Successfully ===")

# ----------------------------
# Optional: Run directly
# ----------------------------
if __name__ == "__main__":
    run_etl()
