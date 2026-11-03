from contextlib import redirect_stdout
from io import StringIO

from agents.llm_router import ExtractedEntities, RouteDecision
from app import SuperChat
from language import detect_language
from models.session_state import SessionState


def test_language_detection():
    cases = {
        "Find wireless headphones under 100 dollars": "en",
        "Найди беспроводные наушники дешевле 100 долларов": "ru",
        "100 dollardan ucuz simsiz qulaqlıqlar tap": "az",
        "CinemaPlus-da show me movies for tomorrow": "az",
    }
    for message, expected in cases.items():
        assert detect_language(message) == expected


def test_short_follow_up_keeps_context_signal():
    assert detect_language("Tomorrow?") is None
    assert detect_language("Which one?") is None


def _decision(language, category, domains, intent, **entities):
    return RouteDecision(
        category=category,
        domains=domains,
        intent=intent,
        language=language,
        entities=ExtractedEntities(**entities),
    )


class FakeShoppingService:
    def search_products(self, session, **params):
        session.shopping.search_params = params
        session.shopping.results = [
            {
                "id": "P001",
                "name": {"en": "Wireless Headphones"},
                "price": 50,
                "currency": "USD",
                "stock": None,
            }
        ]
        session.last_active_domain = "shopping"
        return session.shopping.results


def test_language_switch_preserves_domain_state_and_localizes_output():
    app = object.__new__(SuperChat)
    app.session = SessionState()
    app.shopping_service = FakeShoppingService()
    app.router = type(
        "Router",
        (),
        {
            "classify": lambda self, message, session: _decision(
                "en" if "Find" in message else "az",
                "Shopping",
                ["shopping"],
                "search_products",
                query="headphones",
            )
        },
    )()
    app.flight_service = None
    app.cinema_service = None

    first = StringIO()
    with redirect_stdout(first):
        app.handle_message("Find wireless headphones")
    assert "Products found:" in first.getvalue()
    assert app.session.language == "en"
    assert app.session.shopping.search_params["query"] == "headphones"

    second = StringIO()
    with redirect_stdout(second):
        app.handle_message("Simsiz qulaqlıqlar tap")
    assert "Tapılan məhsullar:" in second.getvalue()
    assert app.session.language == "az"
    assert app.session.shopping.search_params["query"] == "headphones"


if __name__ == "__main__":
    test_language_detection()
    test_short_follow_up_keeps_context_signal()
    test_language_switch_preserves_domain_state_and_localizes_output()
    print("MULTILINGUAL TESTS PASSED")
