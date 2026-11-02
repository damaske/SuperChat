
from repositories.data_loader import load_all_data
from repositories.flight_repository import FlightRepository
from services.flight_service import FlightService
from models.session_state import SessionState


data = load_all_data()

repository = FlightRepository(data["flights"])
service = FlightService(repository)

session = SessionState()

# 1. Search flights
results = service.search_flights(
    session,
    origin="Baku",
    destination="Istanbul",
    max_price=300
)

print("SEARCH RESULTS:", len(results))

for flight in results:
    print(
        flight["id"],
        flight["airline"],
        flight["price_azn"]
    )

# 2. Select a flight
selected = service.select_flight(session, results[0]["id"])

print("\nSELECTED FLIGHT:", selected["flight_number"])

# 3. Create mock reservation
reservation = service.reserve_selected_flight(session)

print("\nRESERVATION:", reservation)

assert len(results) == 3
assert selected is not None
assert reservation["success"] is True

print("\nALL FLIGHT SERVICE TESTS PASSED")
