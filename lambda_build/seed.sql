-- =========================

-- Seed Customers

-- =========================

INSERT INTO Customers (first_name, last_name, email, phone)

VALUES

('Alice', 'Smith', 'alice.smith@example.com', '123-456-7890'),

('Bob', 'Johnson', 'bob.johnson@example.com', '234-567-8901'),

('Charlie', 'Brown', 'charlie.brown@example.com', '345-678-9012');



-- =========================

-- Seed Products

-- =========================

INSERT INTO Products (product_name, description, price, stock_quantity)

VALUES

('Laptop', '15-inch Laptop with 16GB RAM', 1200.00, 10),

('Smartphone', 'Latest model smartphone', 800.00, 20),

('Headphones', 'Noise-cancelling headphones', 150.00, 50),

('Mouse', 'Wireless mouse', 25.00, 100),

('Keyboard', 'Mechanical keyboard', 70.00, 40);



-- =========================

-- Seed Orders

-- =========================

INSERT INTO Orders (customer_id, order_date, total_amount, status)

VALUES

(1, '2025-11-01', 1375.00, 'Completed'),

(2, '2025-11-05', 820.00, 'Pending'),

(3, '2025-11-10', 1195.00, 'Shipped');



-- =========================

-- Seed OrderItems

-- =========================

INSERT INTO OrderItems (order_id, product_id, quantity, price)

VALUES

-- Alice's Order

(1, 1, 1, 1200.00),   -- Laptop

(1, 3, 1, 150.00),    -- Headphones



-- Bob's Order

(2, 2, 1, 800.00),    -- Smartphone

(2, 4, 1, 20.00),     -- Mouse (discounted)



-- Charlie's Order

(3, 1, 1, 1200.00),   -- Laptop

(3, 5, 1, 70.00);     -- Keyboard

 
