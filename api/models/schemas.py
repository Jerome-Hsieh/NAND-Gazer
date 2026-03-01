from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ProductListItem(BaseModel):
    id: int
    platform: str
    item_id: str
    name: str
    url: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    discount_percent: Optional[float] = None
    last_price_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductDetail(ProductListItem):
    shop_name: Optional[str] = None
    shop_platform_id: Optional[int] = None


class PaginatedProducts(BaseModel):
    items: list[ProductListItem]
    total: int
    page: int
    page_size: int
    pages: int


class PricePoint(BaseModel):
    id: int
    price: float
    original_price: Optional[float] = None
    discount_percent: Optional[float] = None
    currency: str = "TWD"
    scraped_at: datetime

    model_config = {"from_attributes": True}


class StatsResponse(BaseModel):
    total_products: int = 0
    total_shops: int = 0
    total_price_records: int = 0
    active_keywords: int = 0
    prices_last_24h: int = 0
    last_scrape_at: Optional[datetime] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
