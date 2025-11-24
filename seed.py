import random
import datetime
import pandas as pd
from sqlalchemy import text
from db import get_engine


# -----------------------------
# CONFIG
# -----------------------------
NUM_CUSTOMERS = 50
NUM_PRODUCTS = 30
NUM_ORDERS = 200
CORRUPTION_RATE = 0.15  # 15% corrupted rows

start_date = datetime.datetime.today() - datetime.timedelta(days=30)
end_date = datetime.datetime.today()

fake_first_names = ["John", "Jane", "Mary", "Neo", "Sizwe", "Lerato", "Amara", "Thabo", "Kyla", "Musa"]
fake_last_names = ["Smith", "Dlamini", "Zulu", "Nkosi", "Peters", "Naidoo", "Khumalo", "Jacobs", "Ngwenya"]

# -----------------------------
# PRODUCT CATALOG (with categories)
# -----------------------------
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

# -----------------------------
# UTILS
# -----------------------------
def random_date():
    delta = end_date - start_date
    return start_date + datetime.timedelta(seconds=random.randint(0, int(delta.total_seconds())))

def generate_email(first, last):
    # 80% good, 20% corrupted
    if random.random() < 0.2:  
        bad_values = ["not-an-email", "bad-email", "invalid", "fake"]
        base = random.choice(bad_values)
        suffix = random.randint(1000, 999999)
        return f"{base}-{suffix}"   # ensures uniqueness
    
    # good email
    unique = random.randint(1, 999999)
    return f"{first.lower()}.{last.lower()}{unique}@example.com"

# -------------------------
# Helper: Corrupt price safely
# -------------------------
def corrupt_price(price):
    """
    Returns a corrupted but SQL-safe price.
    Corruption outcomes:
    - 10%: negative price
    - 10%: extreme price
    - 10%: zero price
    - Otherwise: original price
    """
    r = random.random()

    if r < 0.10:
        return -abs(price)  # negative value corruption

    elif r < 0.20:
        return price * random.randint(50, 200)  # extreme outlier corruption

    elif r < 0.30:
        return 0  # zero price corruption

    else:
        return price  # valid price

def get_existing_customer_ids(engine):
    query = "SELECT customer_id FROM Customers"
    return pd.read_sql(query, engine)["customer_id"].tolist()


# -----------------------------
# CLEAR TABLES (dev only)
# -----------------------------
def clear_tables(engine):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM OrderItems"))
        conn.execute(text("DELETE FROM Orders"))
        conn.execute(text("DELETE FROM Products"))
        conn.execute(text("DELETE FROM Customers"))
    print("🧹 Tables cleared")

# -----------------------------
# SEED CUSTOMERS
# -----------------------------
def seed_customers(engine):
    customers = []
    emails_seen = set()

    for _ in range(NUM_CUSTOMERS):
        fname = random.choice(fake_first_names)
        lname = random.choice(fake_last_names)

        # Generate unique email (handles clean + corrupted automatically)
        email = generate_email(fname, lname)

        # Guarantee uniqueness no matter what
        while email in emails_seen:
            email = generate_email(fname, lname)

        emails_seen.add(email)

        customers.append({
            "first_name": fname,
            "last_name": lname,
            "email": email
        })

    df = pd.DataFrame(customers)

    # Final safety net (should not do anything, but protects DB insert)
    df = df.drop_duplicates(subset=["email"])

    df.to_sql("Customers", engine, if_exists="append", index=False)
    print("👥 Customers seeded:", len(df))
    return df

# -----------------------------
# SEED PRODUCTS
# -----------------------------
def seed_products(engine):
    products = []

    for name, desc, base_price, category in PRODUCT_CATALOG:

        price = base_price

        # Corrupt ~20% of the time
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

    # Convert to DataFrame
    df = pd.DataFrame(products)

    # Ensure all prices are numeric so SQL Server doesn't explode
    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0)

    # Print preview of corrupted rows (for debugging)
    corrupted_preview = df[df["price"] <= 0].head()
    if not corrupted_preview.empty:
        print("⚠️ Corrupted price examples:")
        print(corrupted_preview)

    # Insert safely
    df.to_sql("Products", engine, if_exists="append", index=False)

    print("📦 Products seeded:", len(df))
    return df

# -----------------------------
# SEED ORDERS + ORDER ITEMS
# -----------------------------
def seed_orders_and_items(engine, NUM_ORDERS=300):
    customers_df = pd.read_sql("SELECT customer_id FROM Customers;", engine)
    products_df = pd.read_sql("SELECT product_id, price FROM Products;", engine)

    customer_ids = customers_df["customer_id"].tolist()
    products = products_df.to_dict(orient="records")

    if not customer_ids:
        raise Exception("❌ No customers found. Seed customers first.")
    if not products:
        raise Exception("❌ No products found. Seed products first.")

    # -------------------------
    # Generate Orders
    # -------------------------
    orders = []
    for _ in range(NUM_ORDERS):
        customer_id = random.choice(customer_ids)
        order_date = datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 30))
        if random.random() < CORRUPTION_RATE:
            order_date = random.choice([datetime.datetime.now() + datetime.timedelta(days=365), None])

        orders.append({
            "customer_id": customer_id,
            "order_date": order_date,
            "total_amount": 0,  # placeholder
            "status": random.choice(["Pending", "Paid", "Shipped", "Cancelled"])
        })

    orders_df = pd.DataFrame(orders)
    orders_df.to_sql("Orders", engine, if_exists="append", index=False)
    print("🧾 Orders inserted:", len(orders_df))

    inserted_orders = pd.read_sql(
        f"SELECT TOP ({NUM_ORDERS}) order_id, customer_id, order_date FROM Orders ORDER BY order_id DESC",
        engine
    ).sort_values("order_id")

    # -------------------------
    # Generate OrderItems in memory
    # -------------------------
    order_items = []
    order_totals = {}  # key=order_id, value=total_amount

    for _, order_row in inserted_orders.iterrows():
        order_id = order_row["order_id"]
        num_items = random.randint(1, 5)
        chosen_products = random.sample(products, num_items)

        total_amount = 0
        for p in chosen_products:
            price = p["price"]
            quantity = random.randint(1, 3)

            # corruption but always valid (>0)
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

    # -------------------------
    # Insert all OrderItems at once
    # -------------------------
    items_df = pd.DataFrame(order_items)
    items_df.to_sql("OrderItems", engine, if_exists="append", index=False)
    print("🧺 OrderItems inserted:", len(items_df))

    # -------------------------
    # Bulk update total_amounts in one query
    # -------------------------
    if order_totals:
        case_sql = " ".join(
            f"WHEN {oid} THEN {amt}" for oid, amt in order_totals.items()
        )
        update_sql = f"""
        UPDATE Orders
        SET total_amount = CASE order_id
            {case_sql}
            ELSE total_amount
        END
        WHERE order_id IN ({','.join(str(oid) for oid in order_totals.keys())})
        """
        with engine.begin() as conn:
            conn.execute(text(update_sql))

    return orders_df, items_df

# -----------------------------
# MAIN
# -----------------------------
def seed_database():
    engine = get_engine()
    print("🔌 Connected to DB")

    clear_tables(engine)

    cust_df = seed_customers(engine)
    prod_df = seed_products(engine)
    orders_df, items_df = seed_orders_and_items(engine)

    print("\n🎉 Seeding complete!")
    print("Customers:", len(cust_df))
    print("Products:", len(prod_df))
    print("Orders:", len(orders_df))
    print("OrderItems:", len(items_df))

if __name__ == "__main__":
    seed_database()
