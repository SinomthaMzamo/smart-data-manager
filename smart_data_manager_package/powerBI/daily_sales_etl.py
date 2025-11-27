import logging
import pandas as pd
from ..extract import extract_table
from ..load import load_table
 
logger = logging.getLogger("daily_sales_etl")
logger.setLevel(logging.DEBUG)
 
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
 
fh = logging.FileHandler("daily_sales_etl.log", mode="w")
fh.setLevel(logging.DEBUG)
 
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
fh.setFormatter(formatter)
 
logger.addHandler(ch)
logger.addHandler(fh)
 
def run_daily_sales_etl(config_file="./week2/powerBI/config.json"):
    # We load the config only to keep the function signature compatible,
    # but we will ignore the date_range parameters inside it.
    logger.info("=== Full History Sales ETL Started ===")
 
    # 1. Extract all raw data
    orders = extract_table("Orders")
    order_items = extract_table("OrderItems")
    products = extract_table("Products")
 
    if orders.empty:
        logger.warning("No orders found in database. Nothing to process.")
        return
 
    # 2. Standardize Dates
    # Normalize removes the time component, leaving only YYYY-MM-DD
    orders["order_date"] = pd.to_datetime(orders["order_date"]).dt.normalize()
    
    # 3. Aggregate Order-Level Metrics (Revenue, Count, AOV)
    # Group by date immediately to process the entire history at once
    daily_stats = orders.groupby("order_date").agg(
        total_revenue=("total_amount", "sum"),
        order_count=("order_id", "count")
    ).reset_index()
 
    daily_stats["avg_order_value"] = daily_stats["total_revenue"] / daily_stats["order_count"]
 
    # 4. Aggregate Item-Level Metrics (Total Items Sold)
    # Merge Orders -> Items to associate items with dates
    orders_items_merged = orders.merge(order_items, on="order_id")
    
    daily_items = orders_items_merged.groupby("order_date")["quantity"].sum().reset_index(name="total_items_sold")
 
    # 5. Determine Top Selling Product per Day
    # Merge down to Product names
    full_data = orders_items_merged.merge(products, on="product_id")
    
    # Sum quantity per Day + Product
    daily_product_sales = full_data.groupby(["order_date", "product_name"])["quantity"].sum().reset_index()
    
    # Sort by Date (asc) and Quantity (desc)
    # Then take the top 1 for each date
    top_products = daily_product_sales.sort_values(["order_date", "quantity"], ascending=[True, False])
    top_products = top_products.groupby("order_date").first().reset_index()[["order_date", "product_name"]]
    top_products.rename(columns={"product_name": "top_selling_product"}, inplace=True)
 
    # 6. Merge all metrics into one final DataFrame
    summary = daily_stats.merge(daily_items, on="order_date", how="left")
    summary = summary.merge(top_products, on="order_date", how="left")
 
    # Rename column to match DB schema
    summary.rename(columns={"order_date": "summary_date"}, inplace=True)
 
    # Fill NaNs (safe handling if a day has orders but somehow no items)
    summary["total_items_sold"] = summary["total_items_sold"].fillna(0)
    summary["top_selling_product"] = summary["top_selling_product"].fillna("None")
 
    logger.info(f"Generated summary for {len(summary)} days of history.")
 
    # 7. Load
    # We use 'replace' here to ensure the summary table exactly matches
    # the calculated history, preventing any duplicate key issues.
    load_table(summary, "DailySalesSummary", if_exists="replace")
    
    logger.info("=== Full History Sales ETL Completed ===")
 
if __name__ == "__main__":
    run_daily_sales_etl()
