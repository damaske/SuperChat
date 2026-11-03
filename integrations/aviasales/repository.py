import hashlib
from typing import Any

from integrations.aviasales.client import AviasalesClient


class AviasalesFlightRepository:
    """Repository adapter for cached Aviasales Data API price records."""

    def __init__(self, client: AviasalesClient):
        self.client = client
        self.results: list[dict[str, Any]] = []

    def search(
        self,
        origin: str | None = None,
        destination: str | None = None,
        date: str | None = None,
        return_date: str | None = None,
        max_price: float | None = None,
        max_stops: int | None = None,
        cabin: str | None = None,
        passengers: int | None = None,
        currency: str = "USD",
    ) -> list[dict[str, Any]]:
        del cabin, passengers
        if date or return_date or destination:
            payload = self.client.prices_for_dates(
                origin=origin,
                destination=destination,
                departure_at=date,
                return_at=return_date,
                one_way=return_date is None,
                currency=currency,
                direct=max_stops == 0,
            )
            normalized = []
            for item in payload.get("data", []):
                if not isinstance(item, dict) or not isinstance(
                    item.get("price"), (int, float)
                ):
                    continue
                normalized.append(
                    self._normalize(item, payload.get("currency", currency))
                )
        else:
            payload = self.client.cheap_prices(
                origin=origin,
                currency=currency,
            )
            normalized = []
            for destination_code, months in payload.get("data", {}).items():
                if not isinstance(months, dict):
                    continue
                for month, item in months.items():
                    if isinstance(item, dict):
                        normalized.append(
                            self._normalize(
                                {
                                    **item,
                                    "origin": origin,
                                    "destination": destination_code,
                                    "departure_at": month,
                                },
                                payload.get("currency", currency),
                            )
                        )
        if max_price is not None:
            normalized = [
                item for item in normalized if item["price"] <= max_price
            ]
        if max_stops is not None:
            normalized = [
                item for item in normalized
                if item["stops"] is not None
                and item["stops"] <= max_stops
            ]
        self.results = sorted(normalized, key=lambda item: item["price"])
        return self.results

    @staticmethod
    def _normalize(item: dict[str, Any], currency: str) -> dict[str, Any]:
        identity = "|".join(
            str(item.get(key, ""))
            for key in (
                "origin",
                "destination",
                "departure_at",
                "return_at",
                "price",
                "airline",
                "flight_number",
            )
        )
        link = item.get("link")
        if isinstance(link, str) and link.startswith("/"):
            link = f"https://www.aviasales.com{link}"

        return {
            "id": f"AV-{hashlib.sha1(identity.encode()).hexdigest()[:10]}",
            "origin": {
                "code": item.get("origin_airport") or item.get("origin")
            },
            "destination": {
                "code": (
                    item.get("destination_airport")
                    or item.get("destination")
                )
            },
            "departure_local": item.get("departure_at"),
            "return_local": item.get("return_at"),
            "price": item.get("price"),
            "currency": item.get("currency", currency),
            "airline": item.get("airline"),
            "flight_number": item.get("flight_number"),
            "stops": item.get("transfers"),
            "return_stops": item.get("return_transfers"),
            "duration_min": item.get("duration"),
            "link": link,
            "cached": True,
        }

    def get_by_id(self, flight_id: str):
        return next(
            (flight for flight in self.results if flight["id"] == flight_id),
            None,
        )
