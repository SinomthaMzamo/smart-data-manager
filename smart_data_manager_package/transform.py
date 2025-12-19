import pandas as pd
from datetime import datetime
from .clean import clean_customers, clean_order_items, clean_orders, clean_products, logger

def clean_all(customers_df, products_df, orders_df, order_items_df):
    logger.info("Starting full transformation pipeline")
    
    cleaned_customers = clean_customers(customers_df)
    cleaned_products = clean_products(products_df)
    cleaned_orders = clean_orders(orders_df)
    cleaned_order_items = clean_order_items(order_items_df, cleaned_orders, cleaned_products)

    return cleaned_customers, cleaned_products, cleaned_orders, cleaned_order_items

def build_dim_customers(customers_df: pd.DataFrame) -> pd.DataFrame:
    return customers_df[[
        "customer_id", "full_name", "first_name", "last_name", "email", "phone", "created_at"
    ]].copy()

def build_dim_products(products_df: pd.DataFrame) -> pd.DataFrame:
    return products_df[[
        "product_id", "product_name", "full_description", "category", "price", "stock_quantity", "created_at"
    ]].copy()

def build_dim_date(orders_df: pd.DataFrame) -> pd.DataFrame:
    unique_dates = pd.to_datetime(orders_df["order_date"]).dt.date.dropna().unique()
    unique_dates = pd.Series(unique_dates).sort_values()

    df = pd.DataFrame({"date": pd.to_datetime(unique_dates)})
    df["date_key"] = df["date"].dt.strftime("%Y%m%d").astype(int)
    df["year"] = df["date"].dt.year
    df["quarter"] = df["date"].dt.quarter
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day
    df["day_name"] = df["date"].dt.day_name()
    df["month_name"] = df["date"].dt.month_name()
    df["is_weekend"] = df["date"].dt.dayofweek >= 5

    return df.drop_duplicates(subset=["date_key"]).reset_index(drop=True)

def build_fact_orders(orders_df: pd.DataFrame) -> pd.DataFrame:
    fact = orders_df.copy()
    fact["date_key"] = fact["order_date"].dt.strftime("%Y%m%d").astype(int)
    return fact[["order_id", "customer_id", "date_key", "total_amount", "status"]]

def build_fact_order_items(order_items_df: pd.DataFrame) -> pd.DataFrame:
    return order_items_df[[
        "order_id", "product_id", "quantity", "price", "line_total"
    ]].copy()

def transform_all(customers_df, products_df, orders_df, order_items_df):
    logger.info("Running cleaning phase...")
    cleaned_customers, cleaned_products, cleaned_orders, cleaned_order_items = clean_all(
        customers_df, products_df, orders_df, order_items_df
    )
    
    logger.info("Building analytics tables...")
    return {
        "dim_customers": build_dim_customers(cleaned_customers),
        "dim_products": build_dim_products(cleaned_products),
        "dim_date": build_dim_date(cleaned_orders),
        "fact_orders": build_fact_orders(cleaned_orders),
        "fact_order_items": build_fact_order_items(cleaned_order_items)
    }