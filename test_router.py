
from router import Router
from models.session_state import SessionState


router = Router()

passed = 0
total = 0


def check(message, expected_category, expected_domains, session=None):
    global passed, total

    result = router.classify(message, session)

    total += 1

    success = (
        result.category == expected_category
        and result.domains == expected_domains
    )

    if success:
        passed += 1
        status = "PASS"
    else:
        status = "FAIL"

    print(f"\n[{status}] {message}")
    print(f"Expected: {expected_category} -> {expected_domains}")
    print(f"Actual:   {result.category} -> {result.domains}")

    assert success, f"Routing failed for: {message}"


# 1. Flights

check(
    "Найди рейс из Баку в Стамбул",
    "Flights",
    ["flights"]
)


# 2. Shopping

check(
    "Найди наушники до 100 манатов",
    "Shopping",
    ["shopping"]
)


# 3. Cinema

check(
    "Какие фильмы идут сегодня?",
    "Cinema",
    ["cinema"]
)


# 4. Mixed

check(
    "Найди рейс в Стамбул и рюкзак для поездки",
    "Mixed",
    ["flights", "shopping"]
)


# 5. Ambiguous

result = router.classify("Покажи что-нибудь хорошее")

check(
    "Покажи что-нибудь хорошее",
    "Ambiguous",
    []
)

assert result.needs_clarification is True


# 6. Out of scope

check(
    "Какая погода в Гяндже?",
    "Out of scope",
    []
)


# 7. Follow-up: Shopping

shopping_session = SessionState()
shopping_session.last_active_domain = "shopping"

check(
    "The second one, is it in stock?",
    "Follow-up",
    ["shopping"],
    shopping_session
)


# 8. Follow-up: Flights

flight_session = SessionState()
flight_session.last_active_domain = "flights"

check(
    "The cheaper one, is it direct?",
    "Follow-up",
    ["flights"],
    flight_session
)


# 9. Follow-up in Russian

check(
    "А второй вариант есть в наличии?",
    "Follow-up",
    ["shopping"],
    shopping_session
)


# 10. Booking without context

result = router.classify("Book two seats")

check(
    "Book two seats",
    "Ambiguous",
    []
)

assert result.needs_clarification is True


# 11. Booking with cinema context

cinema_session = SessionState()
cinema_session.last_active_domain = "cinema"

check(
    "Book two seats",
    "Follow-up",
    ["cinema"],
    cinema_session
)


# 12. Follow-up without context

result = router.classify("The second one")

check(
    "The second one",
    "Ambiguous",
    []
)

assert result.needs_clarification is True


# Final report

print("\n================================")
print(f"TESTS PASSED: {passed}/{total}")
print("ALL ROUTING TESTS COMPLETED")
print("================================")
