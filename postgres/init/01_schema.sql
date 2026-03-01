-- Price Tracker Database Schema

-- Shops table
CREATE TABLE IF NOT EXISTS shops (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(20) NOT NULL DEFAULT 'pchome',
    shop_id BIGINT NOT NULL,
    name VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(platform, shop_id)
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(20) NOT NULL DEFAULT 'pchome',
    item_id VARCHAR(50) NOT NULL,
    shop_id INTEGER REFERENCES shops(id),
    name VARCHAR(1000) NOT NULL,
    url VARCHAR(2000),
    category VARCHAR(500),
    brand VARCHAR(500),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(platform, item_id)
);

-- Price history (time-series)
CREATE TABLE IF NOT EXISTS price_history (
    id BIGSERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    price NUMERIC(12,2) NOT NULL,
    original_price NUMERIC(12,2),
    discount_percent NUMERIC(5,2),
    currency VARCHAR(10) NOT NULL DEFAULT 'TWD',
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tracked keywords
CREATE TABLE IF NOT EXISTS tracked_keywords (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(500) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    max_pages INTEGER NOT NULL DEFAULT 3,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Scrape jobs log
CREATE TABLE IF NOT EXISTS scrape_jobs (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(500),
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    products_found INTEGER DEFAULT 0,
    prices_recorded INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_price_history_product_scraped
    ON price_history (product_id, scraped_at DESC);

CREATE INDEX IF NOT EXISTS idx_products_platform_item
    ON products (platform, item_id);

CREATE INDEX IF NOT EXISTS idx_price_history_scraped_at
    ON price_history (scraped_at DESC);

CREATE INDEX IF NOT EXISTS idx_products_active
    ON products (is_active) WHERE is_active = TRUE;

-- Materialized View: latest prices per product
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_latest_prices AS
SELECT DISTINCT ON (ph.product_id)
    ph.product_id,
    p.name AS product_name,
    p.platform,
    p.item_id,
    p.url,
    ph.price,
    ph.original_price,
    ph.discount_percent,
    ph.currency,
    ph.scraped_at
FROM price_history ph
JOIN products p ON p.id = ph.product_id
WHERE p.is_active = TRUE
ORDER BY ph.product_id, ph.scraped_at DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_latest_prices_product_id
    ON mv_latest_prices (product_id);

-- Insert some default keywords
INSERT INTO tracked_keywords (keyword, max_pages) VALUES
    ('DDR5 記憶體', 2),
    ('DDR4 記憶體', 2)
ON CONFLICT (keyword) DO NOTHING;
