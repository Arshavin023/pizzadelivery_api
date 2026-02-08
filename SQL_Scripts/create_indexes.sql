CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS idx_email_users ON users USING gin (email gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_id_users ON users (id);
CREATE INDEX IF NOT EXISTS idx_createdat_orders ON orders (created_at);
CREATE INDEX IF NOT EXISTS idx_id_orders ON orders (id);
CREATE INDEX IF NOT EXISTS idx_name_products ON products USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_name_categories ON categories USING gin (name gin_trgm_ops);