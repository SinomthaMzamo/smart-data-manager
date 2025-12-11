-- =========================
-- Azure SQL Server Schema
-- SQL Server 2019+ Compatible
-- =========================

-- =========================
-- Customers Table
-- =========================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Customers')
BEGIN
    CREATE TABLE Customers (
        customer_id INT IDENTITY(1,1) PRIMARY KEY,
        first_name NVARCHAR(50) NOT NULL,
        last_name NVARCHAR(50) NOT NULL,
        email NVARCHAR(100) NOT NULL,
        phone NVARCHAR(20),
        created_at DATETIME2 DEFAULT GETDATE(),
        deleted_at DATETIME2 NULL,
        CONSTRAINT UQ_Customer_Email UNIQUE (email)
    );
END
GO

-- =========================
-- Products Table
-- =========================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Products')
BEGIN
    CREATE TABLE Products (
        product_id INT IDENTITY(1,1) PRIMARY KEY,
        product_name NVARCHAR(100) NOT NULL,
        description NVARCHAR(255),
        price DECIMAL(10,2) NOT NULL,
        stock_quantity INT DEFAULT 0,
        category NVARCHAR(50),
        created_at DATETIME2 DEFAULT GETDATE(),
        deleted_at DATETIME2 NULL
    );
END
GO

-- =========================
-- Orders Table
-- =========================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Orders')
BEGIN
    CREATE TABLE Orders (
        order_id INT IDENTITY(1,1) PRIMARY KEY,
        customer_id INT NOT NULL,
        order_date DATETIME2 DEFAULT GETDATE(),
        total_amount DECIMAL(10,2) DEFAULT 0,
        status NVARCHAR(20) DEFAULT 'Pending',
        deleted_at DATETIME2 NULL,
        CONSTRAINT FK_Orders_Customer FOREIGN KEY (customer_id) 
            REFERENCES Customers(customer_id)
    );
END
GO

-- =========================
-- OrderItems Table
-- =========================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'OrderItems')
BEGIN
    CREATE TABLE OrderItems (
        order_item_id INT IDENTITY(1,1) PRIMARY KEY,
        order_id INT NOT NULL,
        product_id INT NOT NULL,
        quantity INT NOT NULL DEFAULT 1,
        price DECIMAL(10,2) NOT NULL,
        deleted_at DATETIME2 NULL,
        CONSTRAINT FK_OrderItems_Order FOREIGN KEY (order_id) 
            REFERENCES Orders(order_id),
        CONSTRAINT FK_OrderItems_Product FOREIGN KEY (product_id) 
            REFERENCES Products(product_id),
        CONSTRAINT UQ_OrderItem UNIQUE (order_id, product_id)
    );
END
GO

-- =========================
-- DailySalesSummary Table (for Power BI)
-- =========================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'DailySalesSummary')
BEGIN
    CREATE TABLE DailySalesSummary (
        summary_date DATE PRIMARY KEY,
        total_revenue DECIMAL(10, 2),
        order_count INT,
        avg_order_value DECIMAL(10, 2),
        total_items_sold INT,
        top_selling_product NVARCHAR(255),
        created_at DATETIME2 DEFAULT GETDATE(),
        updated_at DATETIME2 DEFAULT GETDATE()
    );
END
GO

-- =========================
-- Indexes for Performance
-- =========================

-- Soft delete indexes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Customers_DeletedAt')
    CREATE INDEX IX_Customers_DeletedAt ON Customers(deleted_at);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Products_DeletedAt')
    CREATE INDEX IX_Products_DeletedAt ON Products(deleted_at);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Orders_DeletedAt')
    CREATE INDEX IX_Orders_DeletedAt ON Orders(deleted_at);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_OrderItems_DeletedAt')
    CREATE INDEX IX_OrderItems_DeletedAt ON OrderItems(deleted_at);
GO

-- Business query indexes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Orders_CustomerId')
    CREATE INDEX IX_Orders_CustomerId ON Orders(customer_id);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Orders_Status')
    CREATE INDEX IX_Orders_Status ON Orders(status);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Orders_OrderDate')
    CREATE INDEX IX_Orders_OrderDate ON Orders(order_date);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_OrderItems_OrderId')
    CREATE INDEX IX_OrderItems_OrderId ON OrderItems(order_id);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_OrderItems_ProductId')
    CREATE INDEX IX_OrderItems_ProductId ON OrderItems(product_id);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Products_Category')
    CREATE INDEX IX_Products_Category ON Products(category);
GO

-- Daily sales summary index
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_DailySales_SummaryDate')
    CREATE INDEX IX_DailySales_SummaryDate ON DailySalesSummary(summary_date DESC);
GO

-- =========================
-- Analytics Tables (Star Schema)
-- =========================

-- DimCustomers
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'DimCustomers')
BEGIN
    CREATE TABLE DimCustomers (
        customer_id INT PRIMARY KEY,
        full_name NVARCHAR(101),
        first_name NVARCHAR(50),
        last_name NVARCHAR(50),
        email NVARCHAR(100),
        phone NVARCHAR(20),
        created_at DATETIME2
    );
END
GO

-- DimProducts
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'DimProducts')
BEGIN
    CREATE TABLE DimProducts (
        product_id INT PRIMARY KEY,
        product_name NVARCHAR(100),
        full_description NVARCHAR(356),
        category NVARCHAR(50),
        price DECIMAL(10,2),
        stock_quantity INT,
        created_at DATETIME2
    );
END
GO

-- DimDate
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'DimDate')
BEGIN
    CREATE TABLE DimDate (
        date_key INT PRIMARY KEY,
        date DATE,
        year INT,
        quarter INT,
        month INT,
        day INT,
        day_name NVARCHAR(20),
        month_name NVARCHAR(20),
        is_weekend BIT
    );
END
GO

-- FactOrders
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'FactOrders')
BEGIN
    CREATE TABLE FactOrders (
        order_id INT PRIMARY KEY,
        customer_id INT,
        date_key INT,
        total_amount DECIMAL(10,2),
        status NVARCHAR(20),
        FOREIGN KEY (customer_id) REFERENCES DimCustomers(customer_id),
        FOREIGN KEY (date_key) REFERENCES DimDate(date_key)
    );
END
GO

-- FactOrderItems
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'FactOrderItems')
BEGIN
    CREATE TABLE FactOrderItems (
        order_id INT,
        product_id INT,
        quantity INT,
        price DECIMAL(10,2),
        line_total DECIMAL(10,2),
        PRIMARY KEY (order_id, product_id),
        FOREIGN KEY (order_id) REFERENCES FactOrders(order_id),
        FOREIGN KEY (product_id) REFERENCES DimProducts(product_id)
    );
END
GO

PRINT 'Schema created successfully';
GO