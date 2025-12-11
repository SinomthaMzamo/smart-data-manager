import pandas as pd
from sqlalchemy import text
from rds_db import get_engine

# whitelist to avoid accidental / malicious arbitrary SQL
VALID_TABLES = {"Customers", "Products", "Orders", "OrderItems",
                "DimCustomers", "DimProducts", "DimDate", "FactOrders", "FactOrderItems"}

def extract_table(table_name, preview_rows=5):
    """
    Extracts data from a PostgreSQL table into a pandas DataFrame.
    """
    if table_name not in VALID_TABLES:
        raise ValueError(f"Invalid or unsupported table name: {table_name}")

    engine = get_engine()

    try:
        # Quote the identifier so PascalCase tables are found correctly
        query = text(f'SELECT * FROM "{table_name}"')
        df = pd.read_sql(query, engine)

        if df.empty:
            print(f"⚠️ Table '{table_name}' is empty.")
        else:
            print(f"✅ Table '{table_name}' extracted. Preview:")
            print(df.head(preview_rows))

        return df

    except Exception as e:
        print(f"❌ Failed to extract table '{table_name}': {e}")
        return pd.DataFrame()


if __name__ == "__main__":
    customers_df    = extract_table("Customers")
    products_df     = extract_table("Products")
    orders_df       = extract_table("Orders")
    order_items_df  = extract_table("OrderItems")

    print("\nExtraction complete.")