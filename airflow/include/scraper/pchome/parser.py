import logging

from .models import PChomeProduct

logger = logging.getLogger(__name__)

PRODUCT_BASE = "https://24h.pchome.com.tw/prod"


def _parse_product(raw: dict) -> PChomeProduct:
    # v4.3 API: Price is a plain number, OriginPrice is the original price
    price = raw.get("Price", 0)
    origin_price = raw.get("OriginPrice", 0)

    # If OriginPrice differs from Price, it's the original and Price is the sale price
    if origin_price and origin_price != price:
        sale_price = float(price)
        display_price = float(origin_price)
    else:
        sale_price = None
        display_price = float(price)

    product_id = raw.get("Id", "")

    # PCateId is a list in v4.3
    cate_ids = raw.get("PCateId") or []
    category = cate_ids[0] if cate_ids else None

    return PChomeProduct(
        product_id=product_id,
        name=raw.get("Name", ""),
        price=display_price,
        sale_price=sale_price,
        brand=raw.get("Brand") or None,
        nick=raw.get("Nick") or None,
        description=raw.get("Describe") or None,
        url=f"{PRODUCT_BASE}/{product_id}" if product_id else "",
        category=category,
        spec=None,
    )


def parse_search_response(data: dict) -> list[PChomeProduct]:
    """Parse a PChome search API response and return a list of products.

    Supports both v4.3 (Prods) and v3.3 (prods) response formats.
    """
    prods = data.get("Prods") or data.get("prods") or []
    if not prods:
        logger.warning("No products found in response")
        return []

    products = []
    for raw in prods:
        try:
            products.append(_parse_product(raw))
        except Exception:
            logger.exception("Failed to parse product: %s", raw.get("Id", "unknown"))

    logger.info("Parsed %d products from response", len(products))
    return products
