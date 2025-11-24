import pandas as pd
from datetime import datetime
from clean import clean_customers, clean_order_items, clean_orders, clean_products, logger


# ----------------------------

# Wrapper Cleaning Function

# ----------------------------
def clean_all(customers_df, products_df, orders_df, order_items_df):
    logger.info("Starting full transformation pipeline")


    cleaned_customers = clean_customers(customers_df)
    cleaned_products = clean_products(products_df)
    cleaned_orders = clean_orders(orders_df)
    cleaned_order_items = clean_order_items(order_items_df, cleaned_orders, cleaned_products)

    logger.info("Transformation pipeline completed")
    return cleaned_customers, cleaned_products, cleaned_orders, cleaned_order_items


# ============================================================
# BUILD ANALYTICS TABLES (DIMENSIONS + FACTS)
# ============================================================
def build_dim_customers(customers_df: pd.DataFrame) -> pd.DataFrame:
    dim = customers_df.copy()
    dim = dim[[
        "customer_id",
        "full_name",
        "first_name",
        "last_name",
        "email",
        "phone",
        "created_at"
    ]]

    return dim

def build_dim_products(products_df: pd.DataFrame) -> pd.DataFrame:
    dim = products_df.copy()
    dim = dim[[
        "product_id",
        "product_name",
        "full_description",
        "category",
        "price",
        "stock_quantity",
        "created_at"
    ]]

    return dim

def build_dim_date(orders_df: pd.DataFrame) -> pd.DataFrame:
    """Creates a date dimension using all order dates."""
    df = pd.DataFrame()
    unique_dates = pd.Series(pd.to_datetime(orders_df["order_date"].unique())).sort_values()
    df["date"] = unique_dates
    df["date_key"] = df["date"].dt.strftime("%Y%m%d").astype(int)
    df["year"] = df["date"].dt.year
    df["quarter"] = df["date"].dt.quarter
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day
    df["day_name"] = df["date"].dt.day_name()
    df["month_name"] = df["date"].dt.month_name()
    df["is_weekend"] = df["date"].dt.dayofweek >= 5

    return df


def build_fact_orders(orders_df: pd.DataFrame) -> pd.DataFrame:
    fact = orders_df.copy()
    fact["date_key"] = fact["order_date"].dt.strftime("%Y%m%d").astype(int)
    fact = fact[[
        "order_id",
        "customer_id",
        "date_key",
        "total_amount",
        "status"
    ]]

    return fact


def build_fact_order_items(order_items_df: pd.DataFrame) -> pd.DataFrame:
    fact = order_items_df.copy()
    fact = fact[[
    "order_id",
        "product_id",
        "quantity",
        "price",
        "line_total"
    ]]

    return fact


# ============================================================
# FULL TRANSFORMATION PIPELINE
# ============================================================

def transform_all(customers_df, products_df, orders_df, order_items_df):
    print("Running cleaning phase...")
    cleaned_customers, cleaned_products, cleaned_orders, cleaned_order_items = clean_all(customers_df, products_df, orders_df, order_items_df)
    
    print("Cleaning done. Building analytics tables...")
    dim_customers = build_dim_customers(cleaned_customers)
    dim_products = build_dim_products(cleaned_products)
    dim_date = build_dim_date(cleaned_orders)
    fact_orders = build_fact_orders(cleaned_orders)
    fact_order_items = build_fact_order_items(cleaned_order_items)

    print("Transformation pipeline completed.")

    return {
        "dim_customers": dim_customers,
        "dim_products": dim_products,
        "dim_date": dim_date,
        "fact_orders": fact_orders,
        "fact_order_items": fact_order_items
    }



