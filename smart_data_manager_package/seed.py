import os
import random
import datetime
import logging
import pandas as pd
from sqlalchemy import text
from .db import get_engine

# Configure logging to ensure it shows up in CloudWatch/Azure logs
logging.basicConfig(level=logging.INFO)

# -----------------------------
# CONFIG
# -----------------------------
NUM_CUSTOMERS = 50
NUM_PRODUCTS = 30
NUM_ORDERS = 1000
CORRUPTION_RATE = 0.15

start_date = datetime.datetime.today() - datetime.timedelta(days=730)
end_date = datetime.datetime.today()

fake_first_names = ["John", "Jane", "Mary", "Neo", "Sizwe", "Lerato", "Amara", "Thabo", "Kyla", "Musa"]
fake_last_names = ["Smith", "Dlamini", "Zulu", "Nkosi", "Peters", "Naidoo", "Khumalo", "Jacobs", "Ngwenya"]

PRODUCT_CATALOG = [
    ("Samsung Galaxy A54", "Mid-range Android smartphone", 4999.00, "Mobile"),
    ("iPhone 13 Mini", "Compact smartphone with A15 chip", 10999.00, "Mobile"),
    ("Xiaomi Redmi Note 12", "Budget smartphone", 3299.00, "Mobile"),
    ("Sony WH-CH520", "Wireless Bluetooth headphones", 899.00, "Audio"),
    ("JBL Go 3", "Portable Bluetooth speaker", 699.00, "Audio"),
    ("Anker PowerCore 20k", "High-capacity power bank", 599.00, "Accessories"),
    ("Type-C Fast Charger", "25W adapter", 249.00, "Accessories"),
    ("HP 24-inch Monitor", "1080p LED monitor", 1899.00, "Computing"),
    ("Logitech K380 Keyboard", "Bluetooth keyboard", 749.00, "Computing"),
    ("Logitech M720 Mouse", "Wireless mouse", 799.00, "Computing"),
    ("Seagate 1TB External HDD", "USB 3.0 drive", 899.00, "Computing"),
    ("TP-Link WiFi Router", "Dual-band router", 699.00, "Networking"),
    ("Google Chromecast", "Streaming device", 799.00, "Networking"),
    ("Philips Airfryer XL", "Digital air fryer", 2499.00, "Appliances"),
    ("Russell Hobbs Kettle", "Electric kettle", 399.00, "Appliances"),
    ("Defy Toaster", "2-slice toaster", 299.00, "Appliances"),
    ("SNUG Iron 2000W", "Steam iron", 499.00, "Appliances"),
    ("NutriBullet Blender", "High-speed blender", 1899.00, "Appliances"),
]

# -----------------------------
# LOGGING UTILITIES
# -----------------------------
def log_db_state(engine, label="CURRENT DATABASE STATE"):
    """Queries SQL Server metadata to report all tables and their current row counts."""
    query = """
    SELECT 
        t.name AS TableName, 
        p.rows AS [RowCount] 
    FROM sys.tables t
    INNER JOIN sys.partitions p ON t.object_id = p.object_id
    WHERE p.index_id IN (0,1)
    ORDER BY t.name;
    """
    logging.info(f"--- {label} ---")
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
            if df.empty:
                logging.info("  (Database is currently empty)")
            else:
                for _, row in df.iterrows():
                    logging.info(f"  - {row['TableName']}: {row['RowCount']} rows")
    except Exception as e:
        logging.warning(f"Could not fetch DB state: {e}")
    logging.info("-" * (len(label) + 8))

# -----------------------------
# SCHEMA & CLEANUP
# -----------------------------
def drop_tables(engine):
    tables = [
        "FactOrderItems", "FactOrders", "OrderItems", "Orders", 
        "Products", "Customers", "DimProducts", "DimCustomers", 
        "DimDate", "DailySalesSummary"
    ]
    with engine.begin() as conn:
        for table in tables:
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
                logging.info(f"🗑️ Dropped {table}")
            except Exception as e:
                logging.warning(f"Could not drop {table}: {e}")

def execute_schema(engine):
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    if not os.path.exists(schema_path):
        logging.error(f"⚠️ schema.sql not found at {schema_path}!")
        return

    with open(schema_path, "r") as f:
        statements = f.read().split("GO")
        
    with engine.begin() as conn:
        for statement in statements:
            clean_stmt = statement.strip()
            if clean_stmt:
                conn.execute(text(clean_stmt))
    logging.info("🏗️ Schema created successfully")

# -----------------------------
# SEEDING FUNCTIONS
# -----------------------------
def seed_customers(engine):
    customers = []
    emails_seen = set()
    for _ in range(NUM_CUSTOMERS):
        fname, lname = random.choice(fake_first_names), random.choice(fake_last_names)
        email = f"{fname.lower()}.{lname.lower()}{random.randint(1,9999)}@test.com"
        if email not in emails_seen:
            emails_seen.add(email)
            customers.append({"first_name": fname, "last_name": lname, "email": email})

    df = pd.DataFrame(customers)
    df.to_sql("Customers", engine, if_exists="append", index=False)
    logging.info(f"👥 Inserted {len(df)} customers")

def seed_products(engine):
    products = []
    for name, desc, price, cat in PRODUCT_CATALOG:
        products.append({
            "product_name": name, "description": desc,
            "price": price, "stock_quantity": random.randint(10, 100),
            "category": cat
        })
    df = pd.DataFrame(products)
    df.to_sql("Products", engine, if_exists="append", index=False)
    logging.info(f"📦 Inserted {len(df)} products")

def get_random_date(start, end):
    """Generates a random datetime between two datetime objects."""
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = random.randrange(int_delta)
    return start + datetime.timedelta(seconds=random_second)

def seed_orders_and_items(engine):
    cust_df = pd.read_sql("SELECT customer_id FROM Customers", engine)
    prod_df = pd.read_sql("SELECT product_id, price FROM Products", engine)
    
    cust_ids = cust_df["customer_id"].tolist()
    prods = prod_df.to_dict('records')

    # 1. Create Orders with randomized dates
    orders = []
    for _ in range(NUM_ORDERS):
        orders.append({
            "customer_id": random.choice(cust_ids),
            "order_date": get_random_date(start_date, end_date), # Added random date
            "total_amount": 0,
            "status": random.choice(["Paid", "Paid", "Paid", "Refunded"]) # Added status variety
        })
    
    pd.DataFrame(orders).to_sql("Orders", engine, if_exists="append", index=False)

    # 2. Get the generated IDs (Ordering by order_id to map correctly)
    order_ids = pd.read_sql(f"SELECT TOP {NUM_ORDERS} order_id FROM Orders ORDER BY order_id DESC", engine)["order_id"].tolist()
    
    items = []
    for oid in order_ids:
        # Determine number of unique items (1 to 5)
        num_items = random.randint(1, 5) 
        selected_prods = random.sample(prods, num_items)
        
        for p in selected_prods:
            items.append({
                "order_id": oid, 
                "product_id": p["product_id"], 
                "quantity": random.randint(1, 3), 
                "price": p["price"]
            })
    
    pd.DataFrame(items).to_sql("OrderItems", engine, if_exists="append", index=False)
    logging.info(f"🧾 Inserted {NUM_ORDERS} orders spread across 2 years.")

def update_order_totals(engine):
    """Calculates the sum of items and updates the Orders table."""
    update_query = """
    UPDATE O
    SET O.total_amount = Sub.CalculatedTotal
    FROM Orders O
    INNER JOIN (
        SELECT order_id, SUM(price * quantity) as CalculatedTotal
        FROM OrderItems
        GROUP BY order_id
    ) Sub ON O.order_id = Sub.order_id
    """
    with engine.begin() as conn:
        conn.execute(text(update_query))
    logging.info("💰 Synchronized Order total_amount with OrderItems.")

# -----------------------------
# MAIN
# -----------------------------
def seed_database():
    engine = get_engine()
    
    # 1. Report Initial State
    log_db_state(engine, "INITIAL DB STATE")

    # 2. Wipe and Rebuild
    logging.info("🧹 Wiping tables...")
    drop_tables(engine)
    log_db_state(engine, "STATE AFTER DROP")

    logging.info("🏗️ Building schema...")
    execute_schema(engine)
    log_db_state(engine, "STATE AFTER SCHEMA CREATION")

    # 3. Seed
    seed_customers(engine)
    seed_products(engine)
    seed_orders_and_items(engine)

    # NEW: Sync the totals
    update_order_totals(engine)

    # 4. Final State
    log_db_state(engine, "FINAL DB STATE")
    logging.info("🎉 Seeding complete!")

if __name__ == "__main__":
    seed_database()