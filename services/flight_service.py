
from uuid import uuid4


class FlightService:
    def __init__(self, flight_repository):
        self.flight_repository = flight_repository

    def search_flights(
        self,
        session,
        origin=None,
        destination=None,
        date=None,
        return_date=None,
        max_price=None,
        max_stops=None,
        cabin=None,
        passengers=None,
        currency="USD",
    ):
        """Search flights and save results in the user's session."""

        results = self.flight_repository.search(
            origin=origin,
            destination=destination,
            date=date,
            return_date=return_date,
            max_price=max_price,
            max_stops=max_stops,
            cabin=cabin,
            passengers=passengers,
            currency=currency,
        )

        session.flights.search_params = {
            "origin": origin,
            "destination": destination,
            "date": date,
            "return_date": return_date,
            "max_price": max_price,
            "max_stops": max_stops,
            "cabin": cabin,
            "passengers": passengers,
            "currency": currency,
        }

        session.flights.results = results
        session.flights.selected_flight = None
        session.flights.reservation = None

        session.last_active_domain = "flights"

        return results

    def get_flight_details(self, flight_id):
        """Return details of a flight by its ID."""

        return self.flight_repository.get_by_id(flight_id)

    def select_flight(self, session, flight_id):
        """Select a flight and save it in the session."""

        flight = self.flight_repository.get_by_id(flight_id)

        if flight is None:
            return None

        session.flights.selected_flight = flight
        session.last_active_domain = "flights"

        return flight

    def reserve_selected_flight(self, session):
        """Create a mock reservation without processing payment."""

        flight = session.flights.selected_flight

        if flight is None:
            return {
                "success": False,
                "message": "Please select a flight first."
            }

        if flight.get("seats_available") == 0:
            return {
                "success": False,
                "message": "No seats are available for this flight."
            }

        reservation = {
            "reservation_id": str(uuid4())[:8].upper(),
            "flight_id": flight["id"],
            "airline": flight.get("airline"),
            "flight_number": flight.get("flight_number"),
            "status": "confirmed",
            "payment_status": "not_required_mock"
        }

        session.flights.reservation = reservation

        return {
            "success": True,
            "reservation": reservation,
            "message": "Your mock flight reservation is confirmed."
        }
