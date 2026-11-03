import os
from unittest.mock import patch

import httpx

from integrations.serpapi import (
    SerpApiClient,
    SerpApiError,
    SerpApiProductRepository,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload

    @property
    def is_error(self):
        return self.status_code >= 400

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


PRODUCT = {
    "product_id": "123",
    "title": "Wireless headphones",
    "price": "$29.99",
    "extracted_price": 29.99,
    "currency": "USD",
    "thumbnail": "https://i.ebayimg.com/image.jpg",
    "link": "https://www.ebay.com/itm/123",
    "condition": "New",
    "seller": "Example seller",
    "shipping": "Free shipping",
    "rating": 4.8,
    "reviews": 21,
}


def client_with_response(response):
    with patch("integrations.serpapi.client.httpx.get", return_value=response):
        return response


def test_search_parameters_and_normalization():
    response = FakeResponse(payload={"organic_results": [PRODUCT]})
    with patch("integrations.serpapi.client.httpx.get", return_value=response) as get:
        with patch.dict(os.environ, {"SERPAPI_API_KEY": "test-key"}):
            repository = SerpApiProductRepository(SerpApiClient())
            results = repository.search(
                query="headphones",
                min_price=10,
                max_price=50,
                sort="price_low_to_high",
            )

    params = get.call_args.kwargs["params"]
    assert params["engine"] == "ebay"
    assert params["_nkw"] == "headphones"
    assert params["_udlo"] == 10
    assert params["_udhi"] == 50
    assert params["_sop"] == "15"
    assert results[0]["name"]["en"] == PRODUCT["title"]
    assert results[0]["price"] == 29.99
    assert results[0]["product_url"] == PRODUCT["link"]
    assert results[0]["image_url"] == PRODUCT["thumbnail"]


def test_empty_results():
    with patch("integrations.serpapi.client.httpx.get", return_value=FakeResponse(
        payload={"organic_results": []}
    )):
        with patch.dict(os.environ, {"SERPAPI_API_KEY": "test-key"}):
            repository = SerpApiProductRepository(SerpApiClient())
            assert repository.search(query="missing item") == []


def test_category_brand_and_stock_constraints_are_applied():
    product = {**PRODUCT, "stock": 3}
    response = FakeResponse(payload={"organic_results": [product]})
    with patch("integrations.serpapi.client.httpx.get", return_value=response) as get:
        with patch.dict(os.environ, {"SERPAPI_API_KEY": "test-key"}):
            repository = SerpApiProductRepository(SerpApiClient())
            results = repository.search(
                query="headphones",
                category="audio",
                brand="Example",
                in_stock=True,
            )

    assert results
    assert get.call_args.kwargs["params"]["_nkw"] == "headphones audio Example"

    product_without_stock = {**PRODUCT, "stock": None}
    response = FakeResponse(
        payload={"organic_results": [product_without_stock]}
    )
    with patch("integrations.serpapi.client.httpx.get", return_value=response):
        with patch.dict(os.environ, {"SERPAPI_API_KEY": "test-key"}):
            repository = SerpApiProductRepository(SerpApiClient())
            assert repository.search(query="headphones", in_stock=True) == []

    response = FakeResponse(payload={"organic_results": [product_without_stock]})
    with patch("integrations.serpapi.client.httpx.get", return_value=response):
        with patch.dict(os.environ, {"SERPAPI_API_KEY": "test-key"}):
            repository = SerpApiProductRepository(SerpApiClient())
            assert repository.search(query="headphones", in_stock=False)


def test_missing_key():
    with patch("integrations.serpapi.client.load_dotenv"):
        with patch.dict(os.environ, {}, clear=True):
            try:
                SerpApiClient()
            except SerpApiError as error:
                assert "SERPAPI_API_KEY" in str(error)
            else:
                raise AssertionError("Expected missing-key error")


def test_invalid_response_and_http_errors():
    with patch.dict(os.environ, {"SERPAPI_API_KEY": "test-key"}):
        for response in (
            FakeResponse(payload=ValueError()),
            FakeResponse(status_code=401, payload={}),
            FakeResponse(status_code=429, payload={}),
        ):
            with patch(
                "integrations.serpapi.client.httpx.get",
                return_value=response,
            ):
                try:
                    SerpApiClient().search_ebay("headphones")
                except SerpApiError:
                    pass
                else:
                    raise AssertionError("Expected SerpApiError")


def test_timeout():
    with patch.dict(os.environ, {"SERPAPI_API_KEY": "test-key"}):
        with patch(
            "integrations.serpapi.client.httpx.get",
            side_effect=httpx.TimeoutException("timeout"),
        ):
            try:
                SerpApiClient().search_ebay("headphones")
            except SerpApiError as error:
                assert "timed out" in str(error)
            else:
                raise AssertionError("Expected timeout error")


if __name__ == "__main__":
    test_search_parameters_and_normalization()
    test_empty_results()
    test_category_brand_and_stock_constraints_are_applied()
    test_missing_key()
    test_invalid_response_and_http_errors()
    test_timeout()
    print("SERPAPI TESTS PASSED")
