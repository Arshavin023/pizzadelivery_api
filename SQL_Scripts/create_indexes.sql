CREATE INDEX IF NOT EXISTS idx_email_users ON users (email);
CREATE INDEX IF NOT EXISTS idx_id_users ON users (id);
CREATE INDEX IF NOT EXISTS idx_orderdate_orders ON orders (time_created);
CREATE INDEX IF NOT EXISTS idx_id_orders ON orders (id);