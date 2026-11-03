import os
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from agents.llm_router import ExtractedEntities, RouteDecision
from app import SuperChat
from models.session_state import SessionState


def decision(category, domains, intent, clarification_question=None, **entities):
    return RouteDecision(
        category=category,
        domains=domains,
        intent=intent,
        language="en",
        entities=ExtractedEntities(**entities),
        clarification_question=clarification_question,
    )


class FakeFlightService:
    def search_flights(self, session, **params):
        session.flights.search_params = params
        session.flights.results = [
            {
                "id": "AV-1",
                "origin": {"code": "GYD"},
                "destination": {"code": "IST"},
                "price": 100,
                "currency": "USD",
                "departure_local": "2026-11-03T10:00:00",
                "airline": "Example Air",
                "flight_number": "EA1",
                "stops": 0,
            },
            {
                "id": "AV-2",
                "origin": {"code": "GYD"},
                "destination": {"code": "IST"},
                "price": 150,
                "currency": "USD",
                "departure_local": "2026-11-03T12:00:00",
                "airline": "Example Air",
                "flight_number": "EA2",
                "stops": 1,
            },
        ]
        session.last_active_domain = "flights"
        return session.flights.results


class FakeShoppingService:
    def search_products(self, session, **params):
        session.shopping.search_params = params
        session.shopping.results = [
            {
                "id": "P001",
                "name": {"en": "Headphones"},
                "price": 50,
                "currency": "USD",
                "stock": None,
            }
        ]
        session.last_active_domain = "shopping"
        return session.shopping.results


class FakeCinemaService:
    def search_showtimes(self, session, **params):
        session.cinema.search_params = params
        session.cinema.showtimes = [
            {
                "showtime": {
                    "id": "198423",
                    "movie_title": "Yad Ana",
                    "date": params.get("date"),
                    "time": "10:00",
                    "price_azn": 20,
                    "seats_available": 30,
                    "external": True,
                },
                "movie": {"id": "yad-ana", "title": "Yad Ana"},
                "cinema": {"name": params.get("cinema_name") or "28 Mall"},
            }
        ]
        session.last_active_domain = "cinema"
        return session.cinema.showtimes


def build_app(decisions):
    app = object.__new__(SuperChat)
    app.data = {}
    app.session = SessionState()
    app.flight_service = FakeFlightService()
    app.shopping_service = FakeShoppingService()
    app.cinema_service = FakeCinemaService()

    class FakeRouter:
        def classify(self, message, session):
            return decisions.pop(0)

    app.router = FakeRouter()
    return app


def run(app, message):
    output = StringIO()
    with redirect_stdout(output):
        app.handle_message(message)
    return output.getvalue()


def test_actual_dispatch_for_all_domain_combinations():
    cases = [
        (
            decision("Flights", ["flights"], "search_flights",
                     origin="GYD", destination="IST"),
            "Find flights",
            "flights",
        ),
        (
            decision("Shopping", ["shopping"], "search_products",
                     query="headphones"),
            "Find headphones",
            "shopping",
        ),
        (
            decision("Cinema", ["cinema"], "search_showtimes",
                     cinema_name="28 Mall"),
            "Show cinema sessions",
            "cinema",
        ),
    ]
    for route, message, domain in cases:
        app = build_app([route])
        run(app, message)
        assert app.session.last_active_domain == domain
        assert getattr(app.session, domain).results if domain != "cinema" else app.session.cinema.showtimes


def test_mixed_domains_execute_each_domain():
    route = decision(
        "Mixed",
        ["flights", "shopping", "cinema"],
        "search_all",
        origin="GYD",
        destination="IST",
        query="headphones",
        cinema_name="28 Mall",
    )
    app = build_app([route])
    run(app, "Find flights, headphones and cinema sessions")
    assert app.session.flights.results
    assert app.session.shopping.results
    assert app.session.cinema.showtimes


def test_switching_domains_preserves_each_domain_context():
    app = build_app(
        [
            decision("Shopping", ["shopping"], "search_products",
                     query="headphones"),
            decision("Cinema", ["cinema"], "search_showtimes",
                     cinema_name="28 Mall"),
            decision("Flights", ["flights"], "search_flights",
                     origin="GYD", destination="IST"),
            decision("Follow-up", ["shopping"], "follow_up"),
        ]
    )
    run(app, "Find headphones")
    run(app, "What is playing at 28 Mall?")
    run(app, "Find flights from Baku to Istanbul")
    run(app, "Is the product in stock?")

    assert app.session.shopping.search_params["query"] == "headphones"
    assert app.session.cinema.search_params["cinema_name"] == "28 Mall"
    assert app.session.flights.search_params["origin"] == "GYD"
    assert app.session.last_active_domain == "shopping"


def test_flight_comparison_uses_two_existing_results():
    app = build_app(
        [
            decision("Flights", ["flights"], "search_flights",
                     origin="GYD", destination="IST"),
            decision("Follow-up", ["flights"], "compare_flights"),
        ]
    )
    run(app, "Find flights")
    output = run(app, "Compare these flights")
    assert "AV-1" in output
    assert "AV-2" in output
    assert (
        "Сравнение вариантов" in output
        or "Comparison of flight options:" in output
    )


def test_ambiguous_and_out_of_scope_do_not_call_services():
    ambiguous = decision(
        "Ambiguous", [], "clarify",
        clarification_question="Which domain do you mean?",
    )
    out_of_scope = decision("Out of scope", [], "unsupported_request")
    app = build_app([ambiguous, out_of_scope])
    first = run(app, "Help me")
    second = run(app, "Tell me a joke")
    assert "Which domain" in first
    assert "авиабилетами" in second
    assert app.session.flights.results == []
    assert app.session.shopping.results == []
    assert app.session.cinema.showtimes == []


if __name__ == "__main__":
    test_actual_dispatch_for_all_domain_combinations()
    test_mixed_domains_execute_each_domain()
    test_switching_domains_preserves_each_domain_context()
    test_flight_comparison_uses_two_existing_results()
    test_ambiguous_and_out_of_scope_do_not_call_services()
    print("PHASE 2 GAP CLOSURE TESTS PASSED")
