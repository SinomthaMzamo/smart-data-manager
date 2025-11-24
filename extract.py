import pandas as pd
from sqlalchemy import text
from db import get_engine

def extract_table(table_name, preview_rows=5):
    """
    Extracts data from a SQL Server table into a pandas DataFrame.
    
    Args:
        table_name (str): Name of the table to extract.
        preview_rows (int): Number of rows to print as preview.
    
    Returns:
        pd.DataFrame: Data from the table.
    """
    engine = get_engine()
    
    try:
        query = text(f"SELECT * FROM {table_name}")
        df = pd.read_sql(query, engine)

        if df.empty:
            print(f"⚠️ Table '{table_name}' is empty.")
        else:
            print(f"✅ Table '{table_name}' extracted. Preview:")
            print(df.head(preview_rows))
        
        return df

    except Exception as e:
        print(f"❌ Failed to extract table '{table_name}': {e}")
        return pd.DataFrame()  # return empty DataFrame on error


if __name__ == "__main__":
    # Extract all tables
    customers_df = extract_table("Customers")
    products_df = extract_table("Products")
    orders_df = extract_table("Orders")
    order_items_df = extract_table("OrderItems")
    
    print("\nExtraction complete.")
