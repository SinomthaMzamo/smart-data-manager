import random
import datetime
import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from rds_db import get_engine

# -----------------------------
# CONFIG
# -----------------------------
NUM_CUSTOMERS = 50
NUM_PRODUCTS = 30
NUM_ORDERS = 200
CORRUPTION_RATE = 0.15  # 15% corrupted rows

start_date = datetime.datetime.today() - datetime.timedelta(days=365)
end_date = datetime.datetime.today()

fake_first_names = ["John", "Jane", "Mary", "Neo", "Sizwe", "Lerato", "Amara", "Thabo", "Kyla", "Musa"]
fake_last_names = ["Smith", "Dlamini", "Zulu", "Nkosi", "Peters", "Naidoo", "Khumalo", "Jacobs", "Ngwenya"]

PRODUCT_CATALOG = [
    ("Samsung Galaxy A54", "Mid-range Android smartphone with AMOLED display", 4999.00, "Mobile"),
    ("iPhone 13 Mini", "Compact smartphone with A15 chip", 10999.00, "Mobile"),
    ("Xiaomi Redmi Note 12", "Budget smartphone with 50MP camera", 3299.00, "Mobile"),
    ("Sony WH-CH520", "Wireless Bluetooth headphones", 899.00, "Audio"),
    ("JBL Go 3", "Portable Bluetooth speaker", 699.00, "Audio"),
    ("Anker PowerCore 20k", "High-capacity power bank", 599.00, "Accessories"),
    ("Type-C Fast Charger", "25W USB-C fast-charging adapter", 249.00, "Accessories"),
    ("HP 24-inch Monitor", "1080p LED monitor with thin bezel", 1899.00, "Computing"),
    ("Logitech K380 Keyboard", "Compact Bluetooth multi-device keyboard", 749.00, "Computing"),
    ("Logitech M720 Mouse", "Ergonomic multi-device wireless mouse", 799.00, "Computing"),
    ("Seagate 1TB External HDD", "Portable USB 3.0 hard drive", 899.00, "Computing"),
    ("TP-Link WiFi Router", "Dual-band router for home use", 699.00, "Networking"),
    ("Google Chromecast", "Streaming device for TVs", 799.00, "Networking"),
    ("Philips Airfryer XL", "Digital air fryer with rapid hot air tech", 2499.00, "Appliances"),
    ("Russell Hobbs Kettle", "Stainless steel electric kettle", 399.00, "Appliances"),
    ("Defy Toaster", "2-slice electric toaster", 299.00, "Appliances"),
    ("SNUG Iron 2000W", "Steam iron with ceramic plate", 499.00, "Appliances"),
    ("NutriBullet Blender", "High-speed blender for smoothies", 1899.00, "Appliances"),
]

# ============================================================
# UTILS
# ============================================================
def random_date():
    delta = end_date - start_date
    return start_date + datetime.timedelta(seconds=random.randint(0, int(delta.total_seconds())))

def generate_email(first, last):
    if random.random() < 0.2:
        bad_values = ["not-an-email", "bad-email", "invalid", "fake"]
        base = random.choice(bad_values)
        suffix = random.randint(1000, 999999)
        return f"{base}-{suffix}"
    unique = random.randint(1, 999999)
    return f"{first.lower()}.{last.lower()}{unique}@example.com"

def corrupt_price(price):
    r = random.random()
    if r < 0.10:
        return -abs(price)
    elif r < 0.20:
        return price * random.randint(50, 200)
    elif r < 0.30:
        return 0
    else:
        return price

def current_db_and_schema(engine):
    with engine.connect() as conn:
        db = conn.execute(text("SELECT current_database()")).scalar()
        search_path = conn.execute(text("SHOW search_path")).scalar()
    print(f"📌 Connected to database: {db}, search_path: {search_path}")

def log_tables(engine, label, schema="public"):
    sql = text("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema = :schema
        ORDER BY table_name;
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"schema": schema}).fetchall()
    print(f"\n📊 [{label}] Tables in schema '{schema}' ({len(rows)} total):")
    for r in rows:
        print(f"  - {r.table_name}")
    print("📊 End table list\n")

def table_exists(engine, table_name, schema="public"):
    sql = text("""
        SELECT EXISTS (
          SELECT 1
          FROM information_schema.tables
          WHERE table_schema = :schema
            AND table_name   = :table_name
        );
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"schema": schema, "table_name": table_name}).scalar()

def require_table(engine, table_name, schema="public"):
    if not table_exists(engine, table_name, schema):
        raise RuntimeError(f'Required table "{table_name}" does not exist in schema "{schema}"')

# ============================================================
# CREATE TABLES (Preserve Analytics Tables)
# ============================================================
def create_tables(engine, schema_file="schema_pg.sql", schema="public"):
    with open(schema_file, "r") as f:
        schema_sql = f.read()

    # Only manage OLTP tables, preserve analytics
    non_pascal_tables = ["customers", "products", "orders", "orderitems", "order_items"]
    pascal_tables = ["Customers", "Products", "Orders", "OrderItems"]
    
    # Analytics tables to preserve (don't drop these)
    analytics_tables = ["DimCustomers", "DimProducts", "DimDate", "FactOrders", "FactOrderItems"]

    print("\n🔧 [create_tables] BEFORE drops/creates")
    log_tables(engine, "before create_tables", schema)

    # Check which analytics tables exist
    existing_analytics = []
    for table in analytics_tables:
        if table_exists(engine, table, schema):
            existing_analytics.append(table)
    
    if existing_analytics:
        print(f"📊 Preserving existing analytics tables: {', '.join(existing_analytics)}")

    with engine.begin() as conn:
        # Drop lowercase / legacy OLTP tables only
        for t in non_pascal_tables:
            stmt = text(f'DROP TABLE IF EXISTS "{t}" CASCADE')
            print(f"🧹 Dropping non-Pascal OLTP table (if exists): {t}")
            conn.execute(stmt)

        # Drop PascalCase OLTP tables only
        for t in pascal_tables:
            stmt = text(f'DROP TABLE IF EXISTS "{t}" CASCADE')
            print(f"🧹 Dropping PascalCase OLTP table (if exists): {t}")
            conn.execute(stmt)

        # Parse and execute schema SQL statements individually
        print("🛠 Creating tables from schema_pg.sql ...")
        
        # Split by semicolon but handle statements properly
        statements = []
        current = []
        for line in schema_sql.split('\n'):
            if line.strip().startswith('--'):
                continue
            current.append(line)
            if ';' in line:
                statements.append('\n'.join(current))
                current = []
        
        for statement in statements:
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    conn.execute(text(statement))
                    # Extract table name for logging
                    if 'CREATE TABLE' in statement.upper():
                        import re
                        match = re.search(r'CREATE TABLE IF NOT EXISTS "?(\w+)"?', statement, re.IGNORECASE)
                        if match:
                            print(f"  ✓ Created/verified table: {match.group(1)}")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        # Extract table name from error
                        import re
                        match = re.search(r'relation "(\w+)" already exists', str(e), re.IGNORECASE)
                        if match:
                            print(f"  ℹ️ Table already exists, skipping: {match.group(1)}")
                    else:
                        print(f"  ⚠️ Error executing statement: {str(e)[:100]}")
                        # Don't raise, continue with other statements

    print("\n🔧 [create_tables] AFTER running schema_pg.sql")
    log_tables(engine, "after create_tables", schema)

    # Verify required OLTP tables exist
    missing = [t for t in pascal_tables if not table_exists(engine, t, schema)]
    if missing:
        raise RuntimeError(f"❌ After create_tables, required OLTP tables are missing: {missing}")

    print("✅ create_tables: all required OLTP tables exist:", ", ".join(pascal_tables))
    
    # Report on analytics tables
    still_existing_analytics = []
    for table in analytics_tables:
        if table_exists(engine, table, schema):
            still_existing_analytics.append(table)
    
    if still_existing_analytics:
        print(f"✅ Analytics tables preserved: {', '.join(still_existing_analytics)}")

# ============================================================
# ENSURE SOFT DELETE COLUMNS (Migration Support)
# ============================================================
def ensure_soft_delete_columns(engine):
    """Add soft delete columns if they don't exist (for migration)"""
    with engine.begin() as conn:
        tables_to_update = ["Customers", "Products", "Orders", "OrderItems"]
        
        for table in tables_to_update:
            # Check if deleted_at column exists
            check_query = text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{table}' 
                AND column_name = 'deleted_at'
            """)
            
            result = conn.execute(check_query).fetchone()
            
            if not result:
                print(f"  ➕ Adding deleted_at column to {table}")
                try:
                    alter_query = text(f"""
                        ALTER TABLE "{table}" 
                        ADD COLUMN deleted_at TIMESTAMP DEFAULT NULL
                    """)
                    conn.execute(alter_query)
                    
                    # Add index
                    index_query = text(f"""
                        CREATE INDEX IF NOT EXISTS idx_{table.lower()}_deleted_at 
                        ON "{table}"(deleted_at)
                    """)
                    conn.execute(index_query)
                except Exception as e:
                    if "already exists" in str(e).lower():
                        print(f"  ℹ️ Column already exists on {table}")
                    else:
                        print(f"  ⚠️ Error adding column to {table}: {str(e)[:100]}")
            else:
                print(f"  ✓ {table} already has deleted_at column")

# ============================================================
# CLEAR TABLES (Only OLTP)
# ============================================================
def clear_tables(engine):
    """Clear only OLTP tables, preserve analytics"""
    tables = ["OrderItems", "Orders", "Products", "Customers"]  # Order matters for FK constraints
    with engine.begin() as conn:
        for table in tables:
            if table_exists(engine, table):
                conn.execute(text(f'DELETE FROM "{table}"'))
                print(f"  🧼 Cleared table: {table}")
                
                # Reset sequences for clean IDs
                if table == "Customers":
                    conn.execute(text("ALTER SEQUENCE \"Customers_customer_id_seq\" RESTART WITH 1"))
                elif table == "Products":
                    conn.execute(text("ALTER SEQUENCE \"Products_product_id_seq\" RESTART WITH 1"))
                elif table == "Orders":
                    conn.execute(text("ALTER SEQUENCE \"Orders_order_id_seq\" RESTART WITH 1"))
                elif table == "OrderItems":
                    conn.execute(text("ALTER SEQUENCE \"OrderItems_order_item_id_seq\" RESTART WITH 1"))

# ============================================================
# SEED FUNCTIONS (unchanged)
# ============================================================
def seed_customers(engine):
    require_table(engine, "Customers")

    customers = []
    emails_seen = set()
    for _ in range(NUM_CUSTOMERS):
        fname = random.choice(fake_first_names)
        lname = random.choice(fake_last_names)
        email = generate_email(fname, lname)
        while email in emails_seen:
            email = generate_email(fname, lname)
        emails_seen.add(email)
        
        # Add phone numbers for some customers
        phone = None
        if random.random() > 0.3:  # 70% have phone numbers
            phone = f"+27{random.randint(600000000, 899999999)}"
            
        customers.append({
            "first_name": fname, 
            "last_name": lname, 
            "email": email,
            "phone": phone
        })

    df = pd.DataFrame(customers)
    df.drop_duplicates(subset=["email"], inplace=True)

    df.to_sql("Customers", engine, if_exists="append", index=False)
    print(f"  👥 Customers seeded: {len(df)}")
    return df

def seed_products(engine):
    require_table(engine, "Products")

    products = []
    for name, desc, base_price, category in PRODUCT_CATALOG:
        price = base_price
        if random.random() < CORRUPTION_RATE:
            price = corrupt_price(base_price)
        stock_quantity = random.randint(0, 200)
        products.append({
            "product_name": name,
            "description": desc,
            "price": price,
            "stock_quantity": stock_quantity,
            "category": category
        })

    df = pd.DataFrame(products)
    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0)

    corrupted_preview = df[df["price"] <= 0].head()
    if not corrupted_preview.empty:
        print("  ⚠️ Corrupted price examples:")
        print(corrupted_preview)

    df.to_sql("Products", engine, if_exists="append", index=False)
    print(f"  📦 Products seeded: {len(df)}")
    return df

def seed_orders_and_items(engine, num_orders=NUM_ORDERS):
    require_table(engine, "Customers")
    require_table(engine, "Products")
    require_table(engine, "Orders")
    require_table(engine, "OrderItems")

    customers_df = pd.read_sql('SELECT customer_id FROM "Customers";', engine)
    products_df = pd.read_sql('SELECT product_id, price FROM "Products";', engine)

    customer_ids = customers_df["customer_id"].tolist()
    products = products_df.to_dict(orient="records")

    if not customer_ids:
        raise RuntimeError("❌ No customers found.")
    if not products:
        raise RuntimeError("❌ No products found.")

    # Orders
    orders = []
    for _ in range(num_orders):
        customer_id = random.choice(customer_ids)
        order_date = datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 365))
        if random.random() < CORRUPTION_RATE:
            order_date = random.choice([datetime.datetime.now() + datetime.timedelta(days=365), None])
        orders.append({
            "customer_id": customer_id,
            "order_date": order_date,
            "total_amount": 0,
            "status": random.choice(["Pending", "Paid", "Shipped", "Cancelled", "Delivered"])
        })

    orders_df = pd.DataFrame(orders)
    orders_df.to_sql("Orders", engine, if_exists="append", index=False)
    print(f"  🧾 Orders inserted: {len(orders_df)}")

    inserted_orders = pd.read_sql(
        f'SELECT order_id FROM "Orders" ORDER BY order_id DESC LIMIT {num_orders}',
        engine
    )

    # OrderItems
    order_items = []
    order_totals = {}
    for _, order_row in inserted_orders.iterrows():
        order_id = order_row["order_id"]
        num_items = random.randint(1, 5)
        chosen_products = random.sample(products, min(num_items, len(products)))
        total_amount = 0
        for p in chosen_products:
            price = p["price"]
            quantity = random.randint(1, 3)
            if random.random() < CORRUPTION_RATE:
                quantity = max(1, quantity + random.choice([-1, 0, 1]))
                price = max(0.01, price * random.uniform(0.5, 2))
            total_amount += price * quantity
            order_items.append({
                "order_id": order_id,
                "product_id": p["product_id"],
                "quantity": quantity,
                "price": round(price, 2)
            })
        order_totals[order_id] = round(total_amount, 2)

    items_df = pd.DataFrame(order_items)
    items_df.to_sql("OrderItems", engine, if_exists="append", index=False)
    print(f"  🧺 OrderItems inserted: {len(items_df)}")

    # Update order totals
    if order_totals:
        case_sql = " ".join(f"WHEN {oid} THEN {amt}" for oid, amt in order_totals.items())
        update_sql = f"""
        UPDATE "Orders"
        SET total_amount = CASE order_id
            {case_sql}
            ELSE total_amount
        END
        WHERE order_id IN ({','.join(str(oid) for oid in order_totals.keys())})
        """
        with engine.begin() as conn:
            conn.execute(text(update_sql))

    return orders_df, items_df

# ============================================================
# MAIN
# ============================================================
def seed_database():
    """Main seeding function with analytics preservation"""
    engine = get_engine()
    
    print("\n" + "="*60)
    print("🌱 DATABASE SEEDING STARTED")
    print("="*60)
    
    current_db_and_schema(engine)
    log_tables(engine, "initial", "public")

    print("\n📦 Step 1: Creating/updating table schema...")
    create_tables(engine, schema_file="schema_pg.sql")
    
    print("\n🔄 Step 2: Ensuring soft delete columns...")
    ensure_soft_delete_columns(engine)
    
    print("\n🧹 Step 3: Clearing OLTP tables...")
    clear_tables(engine)

    print("\n🌱 Step 4: Seeding data...")
    cust_df = seed_customers(engine)
    prod_df = seed_products(engine)
    orders_df, items_df = seed_orders_and_items(engine)

    print("\n📊 Step 5: Final state...")
    log_tables(engine, "final after seeding", "public")

    print("\n" + "="*60)
    print("🎉 SEEDING COMPLETE!")
    print("="*60)
    print(f"✅ Customers: {len(cust_df)}")
    print(f"✅ Products: {len(prod_df)}")
    print(f"✅ Orders: {len(orders_df)}")
    print(f"✅ OrderItems: {len(items_df)}")
    
    # Check for analytics tables
    analytics_check = ["DimCustomers", "DimProducts", "DimDate", "FactOrders", "FactOrderItems", "DailySalesSummary"]
    existing_analytics = []
    for table in analytics_check:
        if table_exists(engine, table):
            existing_analytics.append(table)
    
    if existing_analytics:
        print(f"\n📊 Analytics tables present: {', '.join(existing_analytics)}")
        print("   (Run ETL pipeline to refresh these)")
    else:
        print("\n📊 No analytics tables found yet")
        print("   (Run ETL pipeline to create them)")
    
    print("="*60 + "\n")

def lambda_handler(event, context):
    """Lambda entry point"""
    try:
        seed_database()
        return {
            "statusCode": 200,
            "body": {"status": "success", "message": "Database seeded successfully"}
        }
    except Exception as e:
        print(f"❌ Error in lambda_handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": {"status": "error", "message": str(e)}
        }

if __name__ == "__main__":
    seed_database()