# Phase 2 Test Log and Five-Minute Demo

## Test environment

- Repository: `C:\Users\user\SuperChat`
- UI: local Streamlit on `http://localhost:8511`
- Browser automation: Playwright
- Date used by the application: 2026-11-03
- No API keys or secret values are included in this log.

## UI scenarios

| Input | Expected behavior | Actual result |
|---|---|---|
| `What is playing at CinemaPlus 28 Mall?` | Live CinemaPlus sessions with title, cinema, date, time, price, and link | Passed; two sessions and official links rendered |
| `Which one is cheaper?` | Preserve Cinema context and sort current sessions | Passed; 8 AZN result appeared before 20 AZN |
| `Tomorrow?` | Preserve Cinema context and query next date | Passed; live empty result displayed without mock fallback |
| `Show me available seats.` | Query live hall data | Passed; 30 seats reported for session 198423 |
| `Find flights from Baku to Istanbul.` | Route to Aviasales and disclose cached prices | Passed; real API-derived prices and Aviasales links rendered |
| `Show me the cheaper options.` | Preserve flight route and return cheaper results | Passed |
| `Find wireless headphones.` | Route to SerpApi/eBay and render listings | Passed; real titles, prices, and eBay links rendered |
| `Show me cheaper options.` | Preserve product query and apply price constraint | Passed |

## Regression commands

All existing `test_*.py` scripts completed successfully, including:

- `test_router.py` (12/12 cases);
- `test_router_stability.py`;
- `test_cinemaplus.py`;
- `test_cinema_service.py`;
- `test_aviasales.py`;
- `test_flight_service.py`;
- `test_serpapi.py`;
- `test_shopping_service.py`;
- `test_phase2_gap_closure.py` (actual dispatch for all three domains,
  all-domain mixed execution, domain switching/context restoration, and
  ambiguous/out-of-scope non-execution);
- legacy fixture regressions for movies, products, flights, state, and
  Streamlit-adjacent application flows.

Also passed:

```text
python -m py_compile <modified application and integration modules>
git diff --check
GET /_stcore/health -> HTTP 200, body "ok"
```

## Router measurement

The deterministic Router regression set contains 12 labeled cases covering
Flights, Shopping, Cinema, Mixed, Follow-up, Ambiguous, and Out of scope.
The observed result was 12/12 for that set. This is a test-set result, not a
claim of production-wide routing accuracy.

## Five-minute demo plan

1. Start Streamlit with the command in `README.md`.
2. Ask for CinemaPlus 28 Mall sessions and point out real prices, times, and
   official movie links.
3. Ask `Which one is cheaper?`, then `Show me available seats.`.
4. Start a new conversation and search Baku to Istanbul flights. Point out the
   cached-price disclaimer.
5. Ask for cheaper flight options.
6. Start a new conversation and search wireless headphones. Point out eBay
   listing links and conservative handling of missing stock.
7. Ask for cheaper products.

The demo must not claim live flight availability, guaranteed eBay inventory,
CinemaPlus booking, payment, or real reservations.

## Gap-closure notes

- `in_stock=False` is treated as no positive stock constraint. Unknown stock is
  not converted into an out-of-stock claim.
- Flight airline and departure-time filters remain unavailable because neither
  the current Router schema nor the Aviasales Data API adapter supplies those
  fields.
- The existing reservation workflow is a local/mock fixture workflow. Live
  Aviasales and CinemaPlus integrations remain read-only.
- The production `SuperChat.handle_booking` path no longer exposes fixture
  reservation creation, viewing, or cancellation. Booking requests now return
  provider-capability messages.
- Category/brand, stock semantics, cart service behavior, flight comparison,
  and all-three-domain mixed dispatch were covered by code-level regression
  tests; pairwise mixed combinations and the new filter/cart flows were not
  separately submitted through the browser UI.
- Flight comparison now prints two existing stored results instead of
  re-running the search. Flight detail UI evidence remains not verified.
- `test_provider_resilience.py` passed for Aviasales, SerpApi, and CinemaPlus:
  cache hits, cache expiry, and one bounded retry after HTTP 429 are covered.
- The full executable `test_*.py` regression suite passed after installing
  only the dependencies already listed in `requirements.txt`. Compilation and
  `git diff --check` also passed.
- The latest repeated flight UI attempt did not render visible results within
  the verification window, so flight details/comparison/reservation UI remain
  unverified rather than being inferred from service tests.
- Shopping category, brand, price, sort, and successful live cart add/remove
  flows remain unverified through the browser. The real eBay response used for
  the UI search did not provide reliable stock, so the application correctly
  refused to add it and no live cart total was claimed.
