-- Seed data for demonstration / testing

-- Shop: PChome 24h (single shop)
INSERT INTO shops (platform, shop_id, name) VALUES
    ('pchome', 1, 'PChome 24h')
ON CONFLICT (platform, shop_id) DO NOTHING;

-- 10 real PChome products (prices fetched from PChome API 2026-03-03)
INSERT INTO products (platform, item_id, shop_id, name, url, category, brand) VALUES
    ('pchome', 'DRAC47-A900I6WWE', 1, 'UMAX DDR5 4800 32G 筆記型記憶體', 'https://24h.pchome.com.tw/prod/DRAC47-A900I6WWE', 'DRAM', 'UMAX'),
    ('pchome', 'DRAC47-A900I6WU6', 1, 'UMAX DDR5 4800 16G 筆記型記憶體', 'https://24h.pchome.com.tw/prod/DRAC47-A900I6WU6', 'DRAM', 'UMAX'),
    ('pchome', 'DSBC3V-A900G91GU', 1, 'ADATA 威剛 DDR5-5600 32G 筆記型記憶體', 'https://24h.pchome.com.tw/prod/DSBC3V-A900G91GU', 'DRAM', 'ADATA'),
    ('pchome', 'DRAC8Z-A900G73JT', 1, 'KLEVV 科賦 DDR5 5600 16G 桌上型記憶體', 'https://24h.pchome.com.tw/prod/DRAC8Z-A900G73JT', 'DRAM', 'KLEVV'),
    ('pchome', 'DRAC8Z-A900HIELY', 1, 'KLEVV 科賦 DDR5 5600 32G 桌上型記憶體', 'https://24h.pchome.com.tw/prod/DRAC8Z-A900HIELY', 'DRAM', 'KLEVV'),
    ('pchome', 'DSAJD1-A900J7IN7', 1, 'GIGABYTE 技嘉 B760M E DDR5 主機板+威剛 DDR5 5600 16G 記憶體', 'https://24h.pchome.com.tw/prod/DSAJD1-A900J7IN7', 'DRAM', 'GIGABYTE'),
    ('pchome', 'DSBC3V-A900G91FR', 1, 'ADATA 威剛 DDR5-5600 32G 桌上型記憶體', 'https://24h.pchome.com.tw/prod/DSBC3V-A900G91FR', 'DRAM', 'ADATA'),
    ('pchome', 'DRAC47-A900GIHJ6', 1, 'UMAX DDR5 4800 32GB 桌上型記憶體(2048X8)', 'https://24h.pchome.com.tw/prod/DRAC47-A900GIHJ6', 'DRAM', 'UMAX'),
    ('pchome', 'DRACDB-A900HRBI3', 1, 'ACER 宏碁 SD200 DDR5 5600 16GB 筆電記憶體', 'https://24h.pchome.com.tw/prod/DRACDB-A900HRBI3', 'DRAM', 'ACER'),
    ('pchome', 'DCBE27-A900HPB4R', 1, 'Micron 美光 Crucial DDR5 5600 16G 筆電記憶體', 'https://24h.pchome.com.tw/prod/DCBE27-A900HPB4R', 'DRAM', 'Micron')
ON CONFLICT (platform, item_id) DO NOTHING;

-- Price history: simulate 30 days of price data for each product
-- Base prices from real PChome API (2026-03-03)
-- Generate multiple price points per product with realistic fluctuations

DO $$
DECLARE
    prod RECORD;
    base_prices NUMERIC[] := ARRAY[10519, 5599, 10499, 5158, 10088, 7990, 10499, 10499, 5199, 5999];
    orig_prices NUMERIC[] := ARRAY[10819, 5899, 10499, 5458, 10388, 7990, 10499, 10799, 5499, 5999];
    i INTEGER;
    j INTEGER;
    day_offset INTEGER;
    price_var NUMERIC;
    cur_price NUMERIC;
    cur_orig NUMERIC;
    discount NUMERIC;
BEGIN
    i := 1;
    FOR prod IN SELECT id FROM products WHERE platform = 'pchome' ORDER BY id LOOP
        -- Generate price points for last 30 days (every 6 hours = 4 per day)
        FOR day_offset IN 0..29 LOOP
            FOR j IN 0..3 LOOP
                -- Add random variation (-3% to +2%) to base price
                price_var := (random() * 5 - 3) / 100.0;
                cur_price := base_prices[i] * (1 + price_var);
                cur_orig := orig_prices[i];

                -- Simulate a flash sale on day 10-12
                IF day_offset BETWEEN 10 AND 12 THEN
                    cur_price := cur_price * 0.88;  -- 12% extra discount
                END IF;

                -- Simulate price increase on day 20-22
                IF day_offset BETWEEN 20 AND 22 THEN
                    cur_price := cur_price * 1.05;
                END IF;

                cur_price := round(cur_price, 0);
                IF cur_orig > cur_price THEN
                    discount := round((1 - cur_price / cur_orig) * 100, 2);
                ELSE
                    discount := NULL;
                    cur_orig := NULL;
                END IF;

                INSERT INTO price_history (product_id, price, original_price, discount_percent, scraped_at)
                VALUES (
                    prod.id,
                    cur_price,
                    cur_orig,
                    discount,
                    NOW() - (day_offset || ' days')::INTERVAL - (j * 6 || ' hours')::INTERVAL + (random() * 30 || ' minutes')::INTERVAL
                );
            END LOOP;
        END LOOP;
        i := i + 1;
    END LOOP;
END $$;

-- Refresh materialized view
REFRESH MATERIALIZED VIEW mv_latest_prices;

-- Log a seed job
INSERT INTO scrape_jobs (keyword, status, products_found, prices_recorded, finished_at)
VALUES ('seed-data', 'success', 10, 1200, NOW());
