
import traceback

from agents.llm_router import LLMRouter
from models.session_state import SessionState


def print_result(title, message, router, session=None):
    print("\n" + "=" * 75)
    print(title)
    print("USER:", message)

    try:
        result = router.classify(message, session=session)

        print("\nROUTING RESULT:")
        print(result.model_dump_json(indent=4))

        return result

    except Exception:
        print("\nERROR:")
        traceback.print_exc()
        return None


def main():
    print("Initializing LLM Router...")

    try:
        router = LLMRouter()
        print("LLM Router initialized successfully.")

    except Exception:
        traceback.print_exc()
        return

    # TEST 1: Mixed domains
    print_result(
        "TEST 1 — MIXED DOMAINS",
        "Найди билет из Баку в Стамбул и фильмы ужасов на сегодня.",
        router
    )

    # TEST 2: Incomplete flight request
    print_result(
        "TEST 2 — INCOMPLETE REQUEST",
        "Найди билет в Стамбул.",
        router
    )

    # TEST 3: Follow-up with real session context
    session = SessionState()

    session.last_active_domain = "flights"

    session.flights.search_params = {
        "origin": "GYD",
        "destination": "IST",
        "date": "2026-12-01",
        "max_price": 300,
        "max_stops": None,
        "cabin": None
    }

    session.history = [
        {
            "role": "user",
            "content": "Найди билет из Баку в Стамбул на 1 декабря."
        }
    ]

    print_result(
        "TEST 3 — FOLLOW-UP WITH SESSION",
        "А если без пересадок?",
        router,
        session
    )

    # TEST 4: Switch domain
    session.last_active_domain = "flights"

    print_result(
        "TEST 4 — DOMAIN SWITCH",
        "Теперь найди беспроводные наушники до 100 долларов.",
        router,
        session
    )

    # TEST 5: Out of scope
    print_result(
        "TEST 5 — OUT OF SCOPE",
        "Какая погода сегодня в Баку?",
        router
    )


if __name__ == "__main__":
    main()
