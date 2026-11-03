import os
from unittest.mock import patch

from integrations.aviasales.client import AviasalesClient
from integrations.cinemaplus.client import CinemaPlusClient
from integrations.serpapi.client import SerpApiClient


class Response:
    def __init__(self, payload, status_code=200, text=""):
        self._payload = payload
        self.status_code = status_code
        self.text = text
        self.is_error = status_code >= 400

    def json(self):
        return self._payload


def test_aviasales_cache_hit_and_expiry():
    response = Response({"success": True, "data": []})
    client = AviasalesClient(cache_ttl=10)
    with patch(
        "integrations.aviasales.client.httpx.get", return_value=response
    ) as request, patch(
        "integrations.aviasales.client.time.monotonic",
        side_effect=[100, 105, 111, 112],
    ):
        client.prices_for_dates(origin="GYD")
        client.prices_for_dates(origin="GYD")
        client.prices_for_dates(origin="GYD")
    assert request.call_count == 2


def test_aviasales_retries_rate_limit_once():
    responses = [
        Response({}, status_code=429),
        Response({"success": True, "data": []}),
    ]
    client = AviasalesClient()
    with patch(
        "integrations.aviasales.client.httpx.get", side_effect=responses
    ) as request, patch("integrations.aviasales.client.time.sleep"):
        client.prices_for_dates(origin="GYD")
    assert request.call_count == 2


def test_serpapi_cache_hit_and_expiry():
    response = Response({"organic_results": []})
    client = SerpApiClient(cache_ttl=10)
    with patch(
        "integrations.serpapi.client.httpx.get", return_value=response
    ) as request, patch(
        "integrations.serpapi.client.time.monotonic",
        side_effect=[100, 105, 111, 112],
    ):
        client.search_ebay("headphones")
        client.search_ebay("headphones")
        client.search_ebay("headphones")
    assert request.call_count == 2


def test_serpapi_retries_rate_limit_once():
    responses = [
        Response({}, status_code=429),
        Response({"organic_results": []}),
    ]
    client = SerpApiClient()
    with patch(
        "integrations.serpapi.client.httpx.get", side_effect=responses
    ) as request, patch("integrations.serpapi.client.time.sleep"):
        client.search_ebay("headphones")
    assert request.call_count == 2


def test_cinemaplus_cache_hit_and_expiry():
    response = Response({}, text="")
    client = CinemaPlusClient(cache_ttl=10)
    with patch(
        "integrations.cinemaplus.client.httpx.get", return_value=response
    ) as request, patch(
        "integrations.cinemaplus.client.time.monotonic",
        side_effect=[100, 105, 111, 112],
    ):
        client.sessions_by_date("03.11.2026")
        client.sessions_by_date("03.11.2026")
        client.sessions_by_date("03.11.2026")
    assert request.call_count == 2


def test_cinemaplus_retries_rate_limit_once():
    responses = [
        Response({}, status_code=429),
        Response({}, text=""),
    ]
    client = CinemaPlusClient()
    with patch(
        "integrations.cinemaplus.client.httpx.get", side_effect=responses
    ) as request, patch("integrations.cinemaplus.client.time.sleep"):
        client.sessions_by_date("03.11.2026")
    assert request.call_count == 2


if __name__ == "__main__":
    os.environ.setdefault("SERPAPI_API_KEY", "test")
    os.environ.setdefault("AVIASALES_API_TOKEN", "test")
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("PROVIDER RESILIENCE TESTS PASSED")
