-- Seed data for demonstration / testing

-- Shop: PChome 24h (single shop)
INSERT INTO shops (platform, shop_id, name) VALUES
    ('pchome', 1, 'PChome 24h')
ON CONFLICT (platform, shop_id) DO NOTHING;

-- 10 real PChome memory products
INSERT INTO products (platform, item_id, shop_id, name, url, category, brand) VALUES
    ('pchome', 'DYAZ53-A900HUJSE', 1, 'Kingston FURY Beast DDR5 5600 32GB(16GBx2) 桌上型超頻記憶體', 'https://24h.pchome.com.tw/prod/DYAZ53-A900HUJSE', 'DRAM', 'Kingston'),
    ('pchome', 'DYAZ55-A900JM3PK', 1, 'Corsair Vengeance DDR5 6000 32GB(16GBx2) AMD EXPO 桌上型記憶體', 'https://24h.pchome.com.tw/prod/DYAZ55-A900JM3PK', 'DRAM', 'Corsair'),
    ('pchome', 'DYAZ4W-A900G5RJ8', 1, 'G.SKILL Trident Z5 RGB DDR5 6400 32GB(16GBx2) 桌上型記憶體', 'https://24h.pchome.com.tw/prod/DYAZ4W-A900G5RJ8', 'DRAM', 'G.SKILL'),
    ('pchome', 'DYAZ52-A900AVKQ3', 1, 'Kingston FURY Beast DDR5 5200 16GB 桌上型超頻記憶體', 'https://24h.pchome.com.tw/prod/DYAZ52-A900AVKQ3', 'DRAM', 'Kingston'),
    ('pchome', 'DYAZ2D-A900BR6TC', 1, 'Crucial DDR5 4800 16GB 桌上型記憶體', 'https://24h.pchome.com.tw/prod/DYAZ2D-A900BR6TC', 'DRAM', 'Crucial'),
    ('pchome', 'DYAZ50-A900FD7AU', 1, 'ADATA XPG Lancer DDR5 5600 32GB(16GBx2) 桌上型記憶體', 'https://24h.pchome.com.tw/prod/DYAZ50-A900FD7AU', 'DRAM', 'ADATA'),
    ('pchome', 'DYAZ3J-A900E4TYN', 1, 'Kingston DDR4 3200 16GB 桌上型記憶體', 'https://24h.pchome.com.tw/prod/DYAZ3J-A900E4TYN', 'DRAM', 'Kingston'),
    ('pchome', 'DYAZ3L-A900F8PQ2', 1, 'Corsair Vengeance LPX DDR4 3200 32GB(16GBx2) 桌上型記憶體', 'https://24h.pchome.com.tw/prod/DYAZ3L-A900F8PQ2', 'DRAM', 'Corsair'),
    ('pchome', 'DYAZ2K-A900CRK9H', 1, 'G.SKILL Ripjaws V DDR4 3200 32GB(16GBx2) 桌上型記憶體', 'https://24h.pchome.com.tw/prod/DYAZ2K-A900CRK9H', 'DRAM', 'G.SKILL'),
    ('pchome', 'DYAZ4S-A900GQZW5', 1, 'Team T-Force Delta RGB DDR5 6000 32GB(16GBx2) 桌上型記憶體', 'https://24h.pchome.com.tw/prod/DYAZ4S-A900GQZW5', 'DRAM', 'Team')
ON CONFLICT (platform, item_id) DO NOTHING;

-- Price history: simulate 30 days of price data for each product
-- Generate multiple price points per product with realistic fluctuations

DO $$
DECLARE
    prod RECORD;
    base_prices NUMERIC[] := ARRAY[3290, 3490, 4590, 1890, 1490, 2990, 1290, 2490, 2290, 3190];
    orig_prices NUMERIC[] := ARRAY[3690, 3990, 5290, 2190, 1690, 3490, 1490, 2890, 2690, 3590];
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
