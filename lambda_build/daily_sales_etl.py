# daily_sales_etl.py
import logging
import pandas as pd
from datetime import datetime
from extract import extract_table
from load import load_table

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def run_daily_sales_etl():
    """
    Run daily sales ETL to prepare data for Power BI dashboard.
    This creates/updates the DailySalesSummary table.
    """
    logger.info("=== Daily Sales ETL Started ===")
    
    try:
        # 1. Extract all raw data WITHOUT quotes (extract.py handles the quoting)
        logger.info("Extracting data from raw tables...")
        orders = extract_table("Orders")  # No quotes - extract.py will handle it
        order_items = extract_table("OrderItems")
        products = extract_table("Products")
        
        if orders.empty:
            logger.warning("No orders found in database. Creating empty summary.")
            # Create empty summary table structure
            empty_summary = pd.DataFrame(columns=[
                'summary_date', 'total_revenue', 'order_count', 
                'avg_order_value', 'total_items_sold', 'top_selling_product'
            ])
            load_table(empty_summary, "DailySalesSummary", if_exists="replace")
            return {
                'status': 'success',
                'days_processed': 0,
                'last_date': None,
                'message': 'No orders to process'
            }
        
        logger.info(f"Processing {len(orders)} orders...")
        
        # 2. Filter out soft-deleted records (if columns exist)
        if 'deleted_at' in orders.columns:
            orders = orders[orders['deleted_at'].isna()]
            logger.info(f"After filtering soft-deleted: {len(orders)} orders")
        
        if 'deleted_at' in order_items.columns:
            order_items = order_items[order_items['deleted_at'].isna()]
        
        if 'deleted_at' in products.columns:
            products = products[products['deleted_at'].isna()]
        
        # Check if we still have data after filtering
        if orders.empty:
            logger.warning("No active orders after filtering soft-deleted records.")
            empty_summary = pd.DataFrame(columns=[
                'summary_date', 'total_revenue', 'order_count', 
                'avg_order_value', 'total_items_sold', 'top_selling_product'
            ])
            load_table(empty_summary, "DailySalesSummary", if_exists="replace")
            return {
                'status': 'success',
                'days_processed': 0,
                'last_date': None,
                'message': 'No active orders to process'
            }
        
        # 3. Standardize Dates
        orders["order_date"] = pd.to_datetime(orders["order_date"], errors='coerce').dt.normalize()
        
        # Remove any rows with invalid dates
        orders = orders.dropna(subset=['order_date'])
        
        if orders.empty:
            logger.warning("No orders with valid dates.")
            empty_summary = pd.DataFrame(columns=[
                'summary_date', 'total_revenue', 'order_count', 
                'avg_order_value', 'total_items_sold', 'top_selling_product'
            ])
            load_table(empty_summary, "DailySalesSummary", if_exists="replace")
            return {
                'status': 'success',
                'days_processed': 0,
                'last_date': None,
                'message': 'No orders with valid dates'
            }
        
        # 4. Aggregate Order-Level Metrics
        daily_stats = orders.groupby("order_date").agg(
            total_revenue=("total_amount", "sum"),
            order_count=("order_id", "count")
        ).reset_index()
        
        # Handle division by zero
        daily_stats["avg_order_value"] = daily_stats.apply(
            lambda row: row["total_revenue"] / row["order_count"] if row["order_count"] > 0 else 0,
            axis=1
        ).round(2)
        
        # 5. Aggregate Item-Level Metrics
        # Only merge orders that have items
        if not order_items.empty:
            orders_items_merged = orders.merge(
                order_items, 
                on="order_id", 
                how="inner"  # Use inner join to exclude orders without items
            )
            
            if not orders_items_merged.empty:
                daily_items = orders_items_merged.groupby("order_date")["quantity"].sum().reset_index(name="total_items_sold")
                
                # 6. Determine Top Selling Product per Day
                if not products.empty:
                    full_data = orders_items_merged.merge(
                        products, 
                        on="product_id", 
                        how="inner"
                    )
                    
                    if not full_data.empty:
                        # Sum quantity per Day + Product
                        daily_product_sales = full_data.groupby(
                            ["order_date", "product_name"]
                        )["quantity"].sum().reset_index()
                        
                        # Get top product for each date
                        top_products = (daily_product_sales
                            .sort_values(["order_date", "quantity"], ascending=[True, False])
                            .groupby("order_date")
                            .first()
                            .reset_index()[["order_date", "product_name"]]
                        )
                        top_products.rename(columns={"product_name": "top_selling_product"}, inplace=True)
                    else:
                        # No product data available
                        top_products = pd.DataFrame(columns=["order_date", "top_selling_product"])
                else:
                    # No products table data
                    top_products = pd.DataFrame(columns=["order_date", "top_selling_product"])
            else:
                # No order items
                daily_items = pd.DataFrame(columns=["order_date", "total_items_sold"])
                top_products = pd.DataFrame(columns=["order_date", "top_selling_product"])
        else:
            # No order items table data
            daily_items = pd.DataFrame(columns=["order_date", "total_items_sold"])
            top_products = pd.DataFrame(columns=["order_date", "top_selling_product"])
        
        # 7. Merge all metrics
        summary = daily_stats.merge(daily_items, on="order_date", how="left")
        summary = summary.merge(top_products, on="order_date", how="left")
        
        # Rename column to match DB schema
        summary.rename(columns={"order_date": "summary_date"}, inplace=True)
        
        # Fill NaNs
        summary["total_items_sold"] = summary["total_items_sold"].fillna(0).astype(int)
        summary["top_selling_product"] = summary["top_selling_product"].fillna("None")
        
        # Ensure proper data types for PostgreSQL
        summary["total_revenue"] = summary["total_revenue"].astype(float).round(2)
        summary["avg_order_value"] = summary["avg_order_value"].astype(float).round(2)
        summary["order_count"] = summary["order_count"].astype(int)
        
        logger.info(f"Generated summary for {len(summary)} days of history.")
        
        # 8. Load to PostgreSQL with quoted table name
        load_table(summary, "DailySalesSummary", if_exists="replace")
        
        logger.info("=== Daily Sales ETL Completed Successfully ===")
        
        # Get the last date for reporting
        last_date = summary['summary_date'].max() if not summary.empty else None
        
        return {
            'status': 'success',
            'days_processed': len(summary),
            'last_date': str(last_date) if last_date is not None else None,
            'total_revenue': float(summary['total_revenue'].sum()) if not summary.empty else 0,
            'total_orders': int(summary['order_count'].sum()) if not summary.empty else 0
        }
        
    except Exception as e:
        logger.error(f"Daily Sales ETL failed: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    result = run_daily_sales_etl()
    print(f"Daily Sales ETL Result: {result}")