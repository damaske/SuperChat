import re
from typing import Any

from .client import SerpApiClient, SerpApiError


class SerpApiProductRepository:
    """Adapter from SerpApi eBay results to SuperChat product dictionaries."""

    def __init__(self, client: SerpApiClient):
        self.client = client
        self._products: dict[str, dict[str, Any]] = {}

    def search(
        self,
        query: str = None,
        category: str = None,
        brand: str = None,
        max_price: float = None,
        min_price: float = None,
        min_rating: float = None,
        in_stock: bool = None,
        sort: str = None,
        condition: str = None,
    ) -> list[dict[str, Any]]:
        if not query:
            raise SerpApiError("A product search query is required.")

        payload = self.client.search_ebay(
            query=query,
            min_price=min_price,
            max_price=max_price,
            sort=sort,
        )
        products = []
        for index, item in enumerate(payload.get("organic_results") or [], 1):
            product = self._normalize(item, index)
            if product is None:
                continue
            if condition and product.get("condition"):
                if condition.lower() not in product["condition"].lower():
                    continue
            if min_rating is not None and (
                product.get("rating") is None
                or product["rating"] < min_rating
            ):
                continue
            products.append(product)

        self._products = {product["id"]: product for product in products}
        return products

    def get_by_id(self, product_id: str):
        return self._products.get(product_id)

    @staticmethod
    def _normalize(item: dict[str, Any], index: int):
        title = item.get("title")
        if not title:
            return None

        price, currency = SerpApiProductRepository._price_info(item)

        return {
            "id": str(item.get("product_id") or f"ebay-{index}"),
            "name": {"en": title},
            "description": item.get("snippet") or "",
            "category": item.get("category"),
            "brand": item.get("brand"),
            "price": price,
            "price_azn": price,
            "currency": currency,
            "image_url": item.get("thumbnail") or item.get("image"),
            "product_url": item.get("link") or item.get("product_link"),
            "condition": item.get("condition"),
            "seller": item.get("seller"),
            "shipping": item.get("shipping"),
            "rating": item.get("rating"),
            "reviews": item.get("reviews"),
            "stock": item.get("stock"),
        }

    @staticmethod
    def _parse_price(value):
        if not isinstance(value, str):
            return None
        match = re.search(r"\d[\d,]*(?:\.\d+)?", value)
        if not match:
            return None
        return float(match.group().replace(",", ""))

    @staticmethod
    def _parse_currency(value):
        match = re.search(r"\b([A-Z]{3})\b", value)
        if match:
            return match.group(1)
        if "$" in value:
            return "USD"
        if "€" in value:
            return "EUR"
        if "£" in value:
            return "GBP"
        return None

    @staticmethod
    def _price_info(item):
        if item.get("extracted_price") is not None:
            return item["extracted_price"], item.get("currency")

        value = item.get("price")
        if isinstance(value, dict):
            low = value.get("from", value).get("extracted")
            high = value.get("to", {}).get("extracted")
            raw = value.get("raw") or value.get("from", {}).get("raw")
            currency = (
                item.get("currency")
                or SerpApiProductRepository._parse_currency(raw or "")
            )
            if low is not None and high is not None and low != high:
                return raw or f"{low} - {high}", currency
            if low is not None:
                return low, currency
            return raw, currency

        if isinstance(value, str):
            return (
                SerpApiProductRepository._parse_price(value) or value,
                item.get("currency")
                or SerpApiProductRepository._parse_currency(value),
            )
        return value, item.get("currency")
