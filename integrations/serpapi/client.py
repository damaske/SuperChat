import os
from typing import Any

import httpx
from dotenv import load_dotenv


class SerpApiError(RuntimeError):
    """Raised when SerpApi cannot serve an eBay search."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class SerpApiClient:
    BASE_URL = "https://serpapi.com/search"
    API_KEY_VARIABLE = "SERPAPI_API_KEY"

    def __init__(self, timeout: float = 30.0):
        load_dotenv()
        self.api_key = os.getenv(self.API_KEY_VARIABLE)
        if not self.api_key:
            raise SerpApiError(
                f"{self.API_KEY_VARIABLE} is not configured."
            )
        self.timeout = timeout

    def search_ebay(
        self,
        query: str,
        ebay_domain: str = "ebay.com",
        min_price: float | None = None,
        max_price: float | None = None,
        sort: str | None = None,
    ) -> dict[str, Any]:
        if not query or not query.strip():
            raise SerpApiError("A product search query is required.")
        if min_price is not None and min_price < 0:
            raise SerpApiError("Minimum price cannot be negative.")
        if max_price is not None and max_price < 0:
            raise SerpApiError("Maximum price cannot be negative.")
        if (
            min_price is not None
            and max_price is not None
            and min_price > max_price
        ):
            raise SerpApiError("Minimum price cannot exceed maximum price.")
        if sort not in {None, "best_match", "price_low_to_high", "price_high_to_low"}:
            raise SerpApiError("Unsupported eBay sort value.")

        params: dict[str, Any] = {
            "engine": "ebay",
            "_nkw": query.strip(),
            "ebay_domain": ebay_domain,
            "api_key": self.api_key,
        }
        if min_price is not None:
            params["_udlo"] = min_price
        if max_price is not None:
            params["_udhi"] = max_price
        if sort:
            params["_sop"] = {
                "best_match": "12",
                "price_low_to_high": "15",
                "price_high_to_low": "16",
            }[sort]

        try:
            response = httpx.get(
                self.BASE_URL,
                params=params,
                timeout=self.timeout,
            )
        except httpx.TimeoutException as error:
            raise SerpApiError("SerpApi request timed out.") from error
        except httpx.RequestError as error:
            raise SerpApiError("SerpApi is unavailable.") from error

        if response.status_code in {401, 403}:
            raise SerpApiError(
                "SerpApi authentication was rejected.",
                response.status_code,
            )
        if response.status_code == 429:
            raise SerpApiError(
                "SerpApi rate limit reached. Please retry later.",
                response.status_code,
            )
        if response.is_error:
            raise SerpApiError(
                f"SerpApi returned HTTP {response.status_code}.",
                response.status_code,
            )

        try:
            payload = response.json()
        except ValueError as error:
            raise SerpApiError("SerpApi returned invalid JSON.") from error

        if not isinstance(payload, dict):
            raise SerpApiError("SerpApi returned an invalid response.")
        if payload.get("error"):
            raise SerpApiError("SerpApi returned an API error.")
        return payload
