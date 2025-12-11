import pandas as pd
import logging
import re
from datetime import datetime, timedelta

# ----------------------------
# Logging setup
# ----------------------------

logger = logging.getLogger("transform")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # File handler – use /tmp for AWS Lambda (code dir is read-only)
    fh = logging.FileHandler("/tmp/transform.log", mode="w")
    fh.setLevel(logging.DEBUG)

    # Formatter
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)

    logger.addHandler(ch)
    logger.addHandler(fh)

# ----------------------------
# Cleaning Functions
# ----------------------------

def clean_customers(df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"Cleaning Customers: {len(df)} rows before cleaning")

    # Remove duplicates
    df = df.drop_duplicates(subset=["email"], keep="first")

    # Fill nulls in optional fields
    df["phone"] = df["phone"].fillna("Unknown")

    # Normalize email
    df["email"] = df["email"].str.strip().str.lower()

    # Remove invalid emails
    valid_email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    invalid_emails = df[~df["email"].str.match(valid_email_pattern, na=False)]
    if not invalid_emails.empty:
        logger.warning(f"Dropping {len(invalid_emails)} customers with invalid emails")
        df = df[df["email"].str.match(valid_email_pattern, na=False)]

    # Derived field
    df["full_name"] = df["first_name"].str.strip() + " " + df["last_name"].str.strip()

    logger.info(f"{len(df)} rows after cleaning Customers")
    logger.info(f"Customers preview:\n{df.head()}")
    return df

def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"Cleaning Products: {len(df)} rows before cleaning")

    df = df.drop_duplicates(subset=["product_name"], keep="first")

    # Handle negative or null prices
    negative_prices = df[df["price"] <= 0]
    if not negative_prices.empty:
        logger.warning(f"Correcting {len(negative_prices)} products with invalid prices")
        df.loc[df["price"] <= 0, "price"] = 0.01

    df["stock_quantity"] = df["stock_quantity"].fillna(0).clip(lower=0)

    # Derived field
    df["full_description"] = (
        df["product_name"].str.strip() + " — " +
        df["description"].fillna("").str.strip()
    )

    logger.info(f"{len(df)} rows after cleaning Products")
    logger.info(f"Products preview:\n{df.head()}")
    return df

def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"Cleaning Orders: {len(df)} rows before cleaning")

    # Remove duplicates
    df = df.drop_duplicates(subset=["order_id"], keep="first")
    
    # Convert order_date to datetime if it's not already
    df["order_date"] = pd.to_datetime(df["order_date"], errors='coerce')
    
    # Get current datetime (with a small buffer for timezone differences)
    # Adding 1 day buffer to account for timezone differences
    max_valid_date = pd.Timestamp(datetime.now() + timedelta(days=1))
    
    # Count problematic dates for logging
    null_dates = df["order_date"].isna().sum()
    future_dates = (df["order_date"] > max_valid_date).sum()
    
    if null_dates > 0:
        logger.warning(f"Found {null_dates} orders with null dates - will be set to today")
    
    if future_dates > 0:
        logger.warning(f"Found {future_dates} orders with future dates - will be dropped")
        # Log some examples of future dates
        future_examples = df[df["order_date"] > max_valid_date]["order_date"].head(5)
        logger.debug(f"Example future dates being dropped: {future_examples.tolist()}")
    
    # Fill null dates with today's date
    today = pd.Timestamp(datetime.now())
    df["order_date"] = df["order_date"].fillna(today)
    
    # Drop orders with future dates
    before_drop = len(df)
    df = df[df["order_date"] <= max_valid_date]
    after_drop = len(df)
    
    if before_drop != after_drop:
        logger.info(f"Dropped {before_drop - after_drop} orders with future dates")
    
    # Also drop orders that are too old (optional - e.g., more than 5 years old)
    # min_valid_date = pd.Timestamp(datetime.now() - timedelta(days=5*365))
    # very_old_orders = (df["order_date"] < min_valid_date).sum()
    
    # if very_old_orders > 0:
    #     logger.warning(f"Found {very_old_orders} orders older than 5 years - will be dropped")
    #     df = df[df["order_date"] >= min_valid_date]
    
    # Ensure total_amount >= 0
    df["total_amount"] = df["total_amount"].clip(lower=0)
    
    # Validate status values
    valid_statuses = ["Pending", "Paid", "Shipped", "Delivered", "Cancelled"]
    invalid_status = ~df["status"].isin(valid_statuses)
    if invalid_status.any():
        logger.warning(f"Found {invalid_status.sum()} orders with invalid status - setting to 'Pending'")
        df.loc[invalid_status, "status"] = "Pending"

    logger.info(f"{len(df)} rows after cleaning Orders")
    logger.info(f"Orders date range: {df['order_date'].min()} to {df['order_date'].max()}")
    logger.info(f"Orders preview:\n{df.head()}")
    return df

def clean_order_items(df: pd.DataFrame, orders_df: pd.DataFrame, products_df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"Cleaning OrderItems: {len(df)} rows before cleaning")

    # Remove duplicates (unique constraint already exists in DB)
    df = df.drop_duplicates(subset=["order_id", "product_id"], keep="first")

    # Remove items with invalid order_id or product_id
    before_filter = len(df)
    df = df[df["order_id"].isin(orders_df["order_id"])]
    after_order_filter = len(df)
    
    if before_filter != after_order_filter:
        logger.warning(f"Dropped {before_filter - after_order_filter} items with invalid order_id")
    
    df = df[df["product_id"].isin(products_df["product_id"])]
    after_product_filter = len(df)
    
    if after_order_filter != after_product_filter:
        logger.warning(f"Dropped {after_order_filter - after_product_filter} items with invalid product_id")

    # Correct negative quantities or prices
    negative_qty = (df["quantity"] <= 0).sum()
    negative_price = (df["price"] <= 0).sum()
    
    if negative_qty > 0:
        logger.warning(f"Correcting {negative_qty} items with invalid quantities")
    if negative_price > 0:
        logger.warning(f"Correcting {negative_price} items with invalid prices")
    
    df["quantity"] = df["quantity"].clip(lower=1)
    df["price"] = df["price"].clip(lower=0.01)

    # Derived field
    df["line_total"] = df["quantity"] * df["price"]

    logger.info(f"{len(df)} rows after cleaning OrderItems")
    logger.info(f"OrderItems preview:\n{df.head()}")
    return df