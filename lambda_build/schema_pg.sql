-- =========================
-- Customers Table
-- =========================
CREATE TABLE IF NOT EXISTS "Customers" (
    customer_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);

-- =========================
-- Products Table
-- =========================
CREATE TABLE IF NOT EXISTS "Products" (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    price NUMERIC(10,2) NOT NULL,
    stock_quantity INT DEFAULT 0,
    category VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL
);

-- =========================
-- Orders Table
-- =========================
CREATE TABLE IF NOT EXISTS "Orders" (
    order_id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES "Customers"(customer_id),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount NUMERIC(10,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'Pending',
    deleted_at TIMESTAMP DEFAULT NULL
);

-- =========================
-- OrderItems Table
-- =========================
CREATE TABLE IF NOT EXISTS "OrderItems" (
    order_item_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES "Orders"(order_id),
    product_id INT NOT NULL REFERENCES "Products"(product_id),
    quantity INT NOT NULL DEFAULT 1,
    price NUMERIC(10,2) NOT NULL,
    deleted_at TIMESTAMP DEFAULT NULL,
    UNIQUE (order_id, product_id)
);

-- =========================
-- DailySalesSummary Table (for Power BI)
-- =========================
CREATE TABLE IF NOT EXISTS "DailySalesSummary" (
    summary_date DATE PRIMARY KEY,
    total_revenue DECIMAL(10, 2),
    order_count INTEGER,
    avg_order_value DECIMAL(10, 2),
    total_items_sold INTEGER,
    top_selling_product VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- Indexes for Performance
-- =========================

-- Soft delete indexes
CREATE INDEX IF NOT EXISTS idx_customers_deleted_at ON "Customers"(deleted_at);
CREATE INDEX IF NOT EXISTS idx_products_deleted_at ON "Products"(deleted_at);
CREATE INDEX IF NOT EXISTS idx_orders_deleted_at ON "Orders"(deleted_at);
CREATE INDEX IF NOT EXISTS idx_orderitems_deleted_at ON "OrderItems"(deleted_at);

-- Business query indexes
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON "Orders"(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON "Orders"(status);
CREATE INDEX IF NOT EXISTS idx_orderitems_order_id ON "OrderItems"(order_id);
CREATE INDEX IF NOT EXISTS idx_orderitems_product_id ON "OrderItems"(product_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON "Products"(category);

-- Daily sales summary index
CREATE INDEX IF NOT EXISTS idx_daily_sales_summary_date ON "DailySalesSummary"(summary_date DESC);