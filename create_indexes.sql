CREATE INDEX IF NOT EXISTS idx_email_customers ON customers (email);
CREATE INDEX IF NOT EXISTS idx_order_date_orders ON orders (order_date);