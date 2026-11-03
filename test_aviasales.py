import os
from pathlib import Path
from unittest.mock import Mock, patch

from dotenv import load_dotenv

from integrations.aviasales.client import (
    AviasalesAPIError,
    AviasalesClient,
)
from integrations.aviasales.repository import AviasalesFlightRepository
from models.session_state import SessionState
from services.flight_service import FlightService


load_dotenv(Path(".env"))


def test_client_configuration():
    assert os.getenv("AVIASALES_API_TOKEN")
    client = AviasalesClient()
    assert client.token


def test_client_request_parameters():
    client = AviasalesClient()
    response = Mock()
    response.status_code = 200
    response.is_error = False
    response.json.return_value = {"success": True, "data": []}

    with patch(
        "integrations.aviasales.client.httpx.get",
        return_value=response,
    ) as request:
        client.prices_for_dates(
            origin="GYD",
            destination="IST",
            departure_at="2026-12",
            currency="USD",
            one_way=True,
        )

    kwargs = request.call_args.kwargs
    assert kwargs["headers"] == {"X-Access-Token": client.token}
    assert kwargs["params"]["origin"] == "GYD"
    assert kwargs["params"]["destination"] == "IST"
    assert kwargs["params"]["departure_at"] == "2026-12"
    assert kwargs["params"]["one_way"] == "true"


def test_repository_normalizes_response_and_service_wiring():
    client = Mock()
    client.prices_for_dates.return_value = {
        "success": True,
        "currency": "USD",
        "data": [
            {
                "origin": "GYD",
                "destination": "IST",
                "origin_airport": "GYD",
                "destination_airport": "IST",
                "price": 120,
                "airline": "XX",
                "flight_number": "123",
                "departure_at": "2026-12-10T10:00:00+04:00",
                "transfers": 0,
                "link": "/search/example",
            }
        ],
    }
    repository = AviasalesFlightRepository(client)
    service = FlightService(repository)
    session = SessionState()

    results = service.search_flights(
        session,
        origin="GYD",
        destination="IST",
        date="2026-12",
        currency="USD",
    )

    assert len(results) == 1
    assert results[0]["price"] == 120
    assert results[0]["currency"] == "USD"
    assert results[0]["cached"] is True
    assert session.flights.results == results
    client.prices_for_dates.assert_called_once()


def test_client_errors_are_explicit():
    client = AviasalesClient()
    response = Mock()
    response.status_code = 429
    response.is_error = True

    with patch(
        "integrations.aviasales.client.httpx.get",
        return_value=response,
    ):
        try:
            client.cheap_prices(origin="GYD")
        except AviasalesAPIError as error:
            assert error.status_code == 429
            assert "rate limit" in str(error).lower()
        else:
            raise AssertionError("Expected AviasalesAPIError")


if __name__ == "__main__":
    test_client_configuration()
    test_client_request_parameters()
    test_repository_normalizes_response_and_service_wiring()
    test_client_errors_are_explicit()
    print("ALL AVIASALES TESTS PASSED")
