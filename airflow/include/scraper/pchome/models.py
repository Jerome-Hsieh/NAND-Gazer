from dataclasses import dataclass


@dataclass
class PChomeProduct:
    product_id: str  # PChome 商品 ID (如 DYAZ53-A900HUJSE)
    name: str  # 商品名稱
    price: float  # 售價 (取 Price.P)
    sale_price: float | None  # 促銷價 (取 Price.M，若與 P 不同)
    brand: str | None  # 品牌/廠商
    nick: str | None  # 副標題（通常含型號/規格資訊）
    description: str | None  # 商品描述
    url: str  # PChome 商品頁面連結
    category: str | None  # 分類
    spec: dict | None  # 額外規格資訊（如有）
