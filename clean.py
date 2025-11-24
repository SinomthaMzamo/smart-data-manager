import pandas as pd
import logging
import re
from datetime import datetime

# ----------------------------

# Logging setup

# ----------------------------

logger = logging.getLogger("transform")
logger.setLevel(logging.DEBUG)

# Console handler

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# File handler

fh = logging.FileHandler("transform.log", mode="w")
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
    df["full_description"] = df["product_name"].str.strip() + " — " + df["description"].fillna("").str.strip()

    logger.info(f"{len(df)} rows after cleaning Products")
    logger.info(f"Products preview:\n{df.head()}")
    return df


def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"Cleaning Orders: {len(df)} rows before cleaning")

    # Remove duplicates
    df = df.drop_duplicates(subset=["order_id"], keep="first")

    # Fill null dates with today
    df["order_date"] = df["order_date"].fillna(pd.Timestamp(datetime.now()))

    # Ensure total_amount >= 0
    df["total_amount"] = df["total_amount"].clip(lower=0)

    logger.info(f"{len(df)} rows after cleaning Orders")
    logger.info(f"Orders preview:\n{df.head()}")
    return df


def clean_order_items(df: pd.DataFrame, orders_df: pd.DataFrame, products_df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"Cleaning OrderItems: {len(df)} rows before cleaning")

    # Remove duplicates (unique constraint already exists in DB)
    df = df.drop_duplicates(subset=["order_id", "product_id"], keep="first")

    # Remove items with invalid order_id or product_id
    df = df[df["order_id"].isin(orders_df["order_id"])]
    df = df[df["product_id"].isin(products_df["product_id"])]

    # Correct negative quantities or prices
    df["quantity"] = df["quantity"].clip(lower=1)
    df["price"] = df["price"].clip(lower=0.01)

    # Derived field
    df["line_total"] = df["quantity"] * df["price"]

    logger.info(f"{len(df)} rows after cleaning OrderItems")
    logger.info(f"OrderItems preview:\n{df.head()}")
    return df




