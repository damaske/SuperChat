# SuperChat

SuperChat is a conversational assistant for three Phase 2 domains:

- Flights through the Aviasales Data API;
- Shopping through SerpApi's eBay Search engine;
- Cinema through the public, read-only CinemaPlus frontend endpoints.

The application uses a Streamlit interface and an LLM router with a
context-aware fallback. Flights use cached/indicative Aviasales prices; they
are not guaranteed live availability. CinemaPlus is read-only: SuperChat does
not purchase tickets, process payments, or call `preSale.php`.

## Architecture

`streamlit_app.py` calls `SuperChat.handle_message()`. The message is
classified by `agents/llm_router.py`, passed to the relevant domain service,
then to a repository and provider client:

```text
Streamlit -> SuperChat -> LLMRouter -> Service -> Repository -> Provider API
```

Conversation state is stored in `models/session_state.py`, with independent
Flight, Shopping, and Cinema state plus the active domain.

## Installation

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Environment variables

Set these in the environment or in a local, untracked `.env` file:

```text
AVIASALES_API_TOKEN=...
SERPAPI_API_KEY=...
GROQ_API_KEY=...
GROQ_MODEL=...
```

Never commit `.env` or print the values. Render variables are declared as
unsynchronised secrets in `render.yaml`.

## Run locally

```powershell
streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501
```

Render uses the platform-provided port:

```powershell
streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port $PORT
```

## Test

The repository uses executable Python regression scripts:

```powershell
Get-ChildItem test_*.py | ForEach-Object { python $_.FullName }
```

Tests that call external providers require the corresponding environment
variables. Unit tests use mocked HTTP responses and do not perform purchases,
payments, or reservations.

The provider clients use a bounded, per-process 60-second in-memory cache and
retry HTTP 429 once with a short delay. These safeguards are not distributed
and do not make provider data live or guarantee inventory. Router
classification emits structured log fields for domain, status, and duration;
secrets, prompts, and personal data are not logged.

## Integration limitations

- Aviasales Data API returns cached price data, not a live flight-search or
  booking inventory. The UI states this limitation.
- SerpApi eBay results do not guarantee inventory. Unknown stock is displayed
  conservatively and cannot be added to the cart.
- CinemaPlus endpoints are internal frontend endpoints rather than a documented
  developer API. They are used only for public read-only schedule, session, and
  hall data. Purchase and payment endpoints are intentionally excluded.
- The production application does not expose local fixture data or simulated
  reservation workflows. Flight and CinemaPlus booking requests return an
  honest provider-capability message instead.
- The conversation language is detected per request for Azerbaijani, Russian,
  and English. Confident language switches update only the language; domain
  search parameters, selections, filters, and cart state remain intact.
  Short or ambiguous follow-ups retain the previous language.
- Airline/departure-time flight filters are unavailable because the current
  Aviasales response path does not expose reliable fields for them.
- Product stock is unknown when eBay omits it; unknown listings are not treated
  as available for cart operations.
