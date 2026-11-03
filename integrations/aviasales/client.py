import os
import time
from typing import Any

import httpx
from dotenv import load_dotenv


class AviasalesAPIError(RuntimeError):
    """Raised when the Aviasales Data API cannot serve a request."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class AviasalesClient:
    BASE_URL = "https://api.travelpayouts.com"
    DATA_API_TOKEN_VARIABLE = "AVIASALES_API_TOKEN"

    def __init__(self, timeout: float = 30.0, cache_ttl: float = 60.0):
        load_dotenv()
        self.token = os.getenv(self.DATA_API_TOKEN_VARIABLE)
        if not self.token:
            raise AviasalesAPIError(
                f"{self.DATA_API_TOKEN_VARIABLE} is not configured."
            )
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self._cache: dict[tuple, tuple[float, dict[str, Any]]] = {}

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        cache_key = (path, tuple(sorted(params.items())))
        cached = self._cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < self.cache_ttl:
            return cached[1]

        response = None
        for attempt in range(2):
            try:
                response = httpx.get(
                    f"{self.BASE_URL}{path}",
                    headers={"X-Access-Token": self.token},
                    params=params,
                    timeout=self.timeout,
                )
            except httpx.TimeoutException as error:
                raise AviasalesAPIError(
                    "Aviasales request timed out."
                ) from error
            except httpx.RequestError as error:
                raise AviasalesAPIError(
                    "Aviasales is unavailable."
                ) from error
            if response.status_code != 429 or attempt == 1:
                break
            time.sleep(0.2)

        if response.status_code in {401, 403}:
            raise AviasalesAPIError(
                "Aviasales authentication was rejected.",
                response.status_code,
            )
        if response.status_code == 429:
            raise AviasalesAPIError(
                "Aviasales rate limit reached. Please retry later.",
                response.status_code,
            )
        if response.is_error:
            raise AviasalesAPIError(
                f"Aviasales returned HTTP {response.status_code}.",
                response.status_code,
            )

        try:
            payload = response.json()
        except ValueError as error:
            raise AviasalesAPIError(
                "Aviasales returned invalid JSON.",
                response.status_code,
            ) from error

        if not isinstance(payload, dict):
            raise AviasalesAPIError("Aviasales returned an invalid response.")
        if payload.get("success") is False:
            raise AviasalesAPIError(
                "Aviasales did not find valid data for this request.",
                response.status_code,
            )
        self._cache[cache_key] = (time.monotonic(), payload)
        return payload

    def prices_for_dates(
        self,
        origin: str | None = None,
        destination: str | None = None,
        departure_at: str | None = None,
        return_at: str | None = None,
        one_way: bool = True,
        currency: str = "USD",
        direct: bool = False,
        sorting: str = "price",
        limit: int = 30,
        page: int = 1,
        market: str | None = None,
    ) -> dict[str, Any]:
        if not origin and not destination:
            raise AviasalesAPIError(
                "At least one origin or destination is required."
            )
        if limit < 1 or limit > 1000:
            raise AviasalesAPIError("Aviasales limit must be between 1 and 1000.")
        if sorting not in {"price", "route"}:
            raise AviasalesAPIError("Unsupported Aviasales sorting value.")

        params: dict[str, Any] = {
            "currency": currency.lower(),
            "one_way": str(one_way).lower(),
            "direct": str(direct).lower(),
            "sorting": sorting,
            "limit": limit,
            "page": page,
        }
        for key, value in {
            "origin": origin,
            "destination": destination,
            "departure_at": departure_at,
            "return_at": return_at,
            "market": market,
        }.items():
            if value is not None:
                params[key] = value

        return self._get("/aviasales/v3/prices_for_dates", params)

    def cheap_prices(
        self,
        origin: str | None = None,
        destination: str | None = None,
        depart_date: str | None = None,
        return_date: str | None = None,
        currency: str = "USD",
        page: int = 1,
        market: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "currency": currency.lower(),
            "page": page,
        }
        for key, value in {
            "origin": origin,
            "destination": destination,
            "depart_date": depart_date,
            "return_date": return_date,
            "market": market,
        }.items():
            if value is not None:
                params[key] = value
        return self._get("/v1/prices/cheap", params)
