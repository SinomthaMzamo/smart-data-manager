import pandas as pd
import logging
import re
from datetime import datetime

# ----------------------------
# Logging setup
# ----------------------------
logger = logging.getLogger("transform")
logger.setLevel(logging.DEBUG)

# Console handler - Azure picks this up automatically
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)

# Only add the console handler to avoid Read-Only File System errors
logger.addHandler(ch)

# ----------------------------
# Cleaning Functions
# ----------------------------

def clean_customers(df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"Cleaning Customers: {len(df)} rows before cleaning")
    df = df.drop_duplicates(subset=["email"], keep="first")
    df["phone"] = df["phone"].fillna("Unknown")
    df["email"] = df["email"].str.strip().str.lower()

    valid_email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    invalid_emails = df[~df["email"].str.match(valid_email_pattern, na=False)]
    if not invalid_emails.empty:
        logger.warning(f"Dropping {len(invalid_emails)} customers with invalid emails")
        df = df[df["email"].str.match(valid_email_pattern, na=False)]

    df["full_name"] = df["first_name"].str.strip() + " " + df["last_name"].str.strip()
    logger.info(f"{len(df)} rows after cleaning Customers")
    return df

def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"Cleaning Products: {len(df)} rows before cleaning")
    df = df.drop_duplicates(subset=["product_name"], keep="first")
    
    # Handle negative or null prices
    if not df.empty and "price" in df.columns:
        df.loc[df["price"] <= 0, "price"] = 0.01
        df["stock_quantity"] = df["stock_quantity"].fillna(0).clip(lower=0)
        df["full_description"] = df["product_name"].str.strip() + " — " + df["description"].fillna("").str.strip()

    logger.info(f"{len(df)} rows after cleaning Products")
    return df

def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"Cleaning Orders: {len(df)} rows before cleaning")
    df = df.drop_duplicates(subset=["order_id"], keep="first")
    df["order_date"] = pd.to_datetime(df["order_date"]).fillna(pd.Timestamp(datetime.now()))
    df["total_amount"] = df["total_amount"].clip(lower=0)
    logger.info(f"{len(df)} rows after cleaning Orders")
    return df

def clean_order_items(df: pd.DataFrame, orders_df: pd.DataFrame, products_df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"Cleaning OrderItems: {len(df)} rows before cleaning")
    df = df.drop_duplicates(subset=["order_id", "product_id"], keep="first")
    
    # Referencial integrity check
    df = df[df["order_id"].isin(orders_df["order_id"])]
    df = df[df["product_id"].isin(products_df["product_id"])]

    df["quantity"] = df["quantity"].clip(lower=1)
    df["price"] = df["price"].clip(lower=0.01)
    df["line_total"] = df["quantity"] * df["price"]

    logger.info(f"{len(df)} rows after cleaning OrderItems")
    return df