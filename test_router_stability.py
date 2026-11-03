
import json

from agents.llm_router import LLMRouter
from models.session_state import SessionState
from openai import APIStatusError


def main():
    router = LLMRouter()

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

    tests = [
        (
            "MIXED",
            "Найди билет из Баку в Стамбул и фильмы ужасов на сегодня.",
            None
        ),
        (
            "INCOMPLETE",
            "Найди билет в Стамбул.",
            None
        ),
        (
            "FOLLOW-UP",
            "А если без пересадок?",
            session
        )
    ]

    for attempt in range(1, 3):
        print(f"\n{'#' * 65}")
        print(f"ATTEMPT {attempt}")

        for name, message, test_session in tests:
            print(f"\n{'=' * 50}")
            print("TEST:", name)

            try:
                result = router.classify(
                    message,
                    session=test_session
                )

                print("SUCCESS")
                print(result.model_dump_json(indent=2))

            except APIStatusError as error:
                print("API ERROR:", error.status_code)

                if isinstance(error.body, dict):
                    print(json.dumps(
                        error.body,
                        ensure_ascii=False,
                        indent=2
                    ))
                else:
                    print(error.body)

            except Exception as error:
                print(type(error).__name__, str(error))


if __name__ == "__main__":
    main()
