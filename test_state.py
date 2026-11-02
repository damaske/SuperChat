
from models.session_state import SessionState

session = SessionState()

session.flights.search_params = {
    "origin": "Baku",
    "destination": "Istanbul",
    "date": "2026-11-06"
}

session.shopping.cart["P001"] = 2

session.last_active_domain = "shopping"

print("Session ID:", session.session_id)
print("Flight search:", session.flights.search_params)
print("Shopping cart:", session.shopping.cart)
print("Last active domain:", session.last_active_domain)
