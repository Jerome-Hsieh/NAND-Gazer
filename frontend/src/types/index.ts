export interface Product {
  id: number;
  platform: string;
  item_id: string;
  name: string;
  url: string | null;
  category: string | null;
  brand: string | null;
  price: number | null;
  original_price: number | null;
  discount_percent: number | null;
  last_price_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductDetail extends Product {
  shop_name: string | null;
  shop_platform_id: number | null;
}

export interface PaginatedProducts {
  items: Product[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface PricePoint {
  id: number;
  price: number;
  original_price: number | null;
  discount_percent: number | null;
  currency: string;
  scraped_at: string;
}

export interface Stats {
  total_products: number;
  total_shops: number;
  total_price_records: number;
  active_keywords: number;
  keyword_names: string[];
  prices_last_24h: number;
  last_scrape_at: string | null;
}
