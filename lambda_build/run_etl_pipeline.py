import json
import logging
from extract import extract_table
from daily_sales_etl import run_daily_sales_etl
from transform import transform_all
from load import load_transformed_schema

# ----------------------------
# Logging Setup
# ----------------------------

logger = logging.getLogger("run_etl")
logger.setLevel(logging.DEBUG)

# Avoid adding duplicate handlers if this module is imported multiple times
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # Use /tmp so it works inside AWS Lambda (only /tmp is writable)
    fh = logging.FileHandler("/tmp/run_etl.log", mode="w")
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
    customers_df   = extract_table("Customers")
    products_df    = extract_table("Products")
    orders_df      = extract_table("Orders")
    order_items_df = extract_table("OrderItems")
    logger.info("Extraction Phase Completed")

    # ---------- Transformation ----------
    logger.info("Starting Transformation Phase")
    transformed_data = transform_all(customers_df, products_df, orders_df, order_items_df)
    logger.info("Transformation Phase Completed")

    # ---------- Loading ----------
    logger.info("Starting Load Phase")
    load_transformed_schema(
        dim_customers   = transformed_data["dim_customers"],
        dim_products    = transformed_data["dim_products"],
        dim_date        = transformed_data["dim_date"],
        fact_orders     = transformed_data["fact_orders"],
        fact_order_items= transformed_data["fact_order_items"],
        mode="replace"  # or "append" for incremental loads
    )
    logger.info("Load Phase Completed")
    logger.info("=== ETL Pipeline Finished Successfully ===")

# ----------------------------
# Lambda handler
# ----------------------------
def lambda_handler(event, context):
    """
    AWS Lambda handler function for ETL pipeline
    """
    try:
        logger.info("Lambda ETL invocation started")
        
        # Run main ETL pipeline (creates Dim and Fact tables)
        run_etl()
        
        # Run daily sales ETL (creates summary for Power BI)
        logger.info("Starting Daily Sales ETL for Power BI...")
        daily_result = run_daily_sales_etl()
        logger.info(f"Daily Sales ETL Result: {daily_result}")
        
        logger.info("Lambda ETL invocation completed successfully")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'ETL pipeline completed successfully',
                'daily_sales': daily_result
            })
        }
    except Exception as e:
        logger.error(f"Lambda ETL invocation failed: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

# ----------------------------
# Optional: Run directly
# ----------------------------
if __name__ == "__main__":
    run_etl()