-- Seed data for demonstration / testing

-- Shop: PChome 24h (single shop)
INSERT INTO shops (platform, shop_id, name) VALUES
    ('pchome', 1, 'PChome 24h')
ON CONFLICT (platform, shop_id) DO NOTHING;

-- 10 real PChome products
INSERT INTO products (platform, item_id, shop_id, name, url, category, brand) VALUES
    ('pchome', 'DRACB8-A900G5P4K', 1, 'Kingston FURY Beast DDR5 5600 32GB(16GBx2) RGB 桌上型超頻記憶體', 'https://24h.pchome.com.tw/prod/DRACB8-A900G5P4K', 'DRAM', 'Kingston'),
    ('pchome', 'DRAC47-A900HB8VJ', 1, 'UMAX DDR5 5600 32GB(16Gx2) 桌上型記憶體', 'https://24h.pchome.com.tw/prod/DRAC47-A900HB8VJ', 'DRAM', 'UMAX'),
    ('pchome', 'DRAC4S-A900G14KE', 1, 'ADATA XPG Lancer DDR5 6000 64GB(32Gx2) RGB 桌上型記憶體', 'https://24h.pchome.com.tw/prod/DRAC4S-A900G14KE', 'DRAM', 'ADATA'),
    ('pchome', 'DRAC00-A900GGICG', 1, 'Micron Crucial DDR5 5600 16GB 筆記型記憶體', 'https://24h.pchome.com.tw/prod/DRAC00-A900GGICG', 'DRAM', 'Crucial'),
    ('pchome', 'DRAC5Z-A900HBGFM', 1, 'Samsung DDR5 5600 64GB ECC R-DIMM 伺服器記憶體', 'https://24h.pchome.com.tw/prod/DRAC5Z-A900HBGFM', 'DRAM', 'Samsung'),
    ('pchome', 'DRAC10-A900BJEIW', 1, 'PChome DDR5 記憶體商品', 'https://24h.pchome.com.tw/prod/DRAC10-A900BJEIW', 'DRAM', 'PChome'),
    ('pchome', 'DSAJHJ-A900J0F5H', 1, 'GIGABYTE B860M GAMING WIFI6 主機板 + DDR5 記憶體組合', 'https://24h.pchome.com.tw/prod/DSAJHJ-A900J0F5H', 'COMBO', 'GIGABYTE'),
    ('pchome', 'DHAI6O-A900HDPKP', 1, 'DELL Latitude 3550 商用筆電', 'https://24h.pchome.com.tw/prod/DHAI6O-A900HDPKP', 'LAPTOP', 'DELL'),
    ('pchome', 'DRAC5Z-A900B15AU', 1, 'V-Color DDR4 3200 128GB ECC R-DIMM 伺服器記憶體', 'https://24h.pchome.com.tw/prod/DRAC5Z-A900B15AU', 'DRAM', 'V-Color'),
    ('pchome', 'DSAM9M-A900IE4BA', 1, 'ASUS PN53 AMD Ryzen 5 迷你電腦', 'https://24h.pchome.com.tw/prod/DSAM9M-A900IE4BA', 'MINI-PC', 'ASUS')
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
