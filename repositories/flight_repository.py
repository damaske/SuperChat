class FlightRepository:

    def __init__(self, flights: list):
        self.flights = flights

    def search(
        self,
        origin: str = None,
        destination: str = None,
        date: str = None,
        return_date: str = None,
        max_price: float = None,
        max_stops: int = None,
        cabin: str = None,
        passengers: int = None,
        currency: str = "AZN",
    ) -> list:
        del return_date, passengers, currency

        results = self.flights

        if origin:
            results = [
                flight for flight in results
                if flight["origin"]["city"].lower() == origin.lower()
            ]

        if destination:
            results = [
                flight for flight in results
                if flight["destination"]["city"].lower() == destination.lower()
            ]

        if date:
            results = [
                flight for flight in results
                if flight["departure_local"].startswith(date)
            ]

        if max_price is not None:
            results = [
                flight for flight in results
                if flight["price_azn"] <= max_price
            ]

        if max_stops is not None:
            results = [
                flight for flight in results
                if flight["stops"] <= max_stops
            ]

        if cabin:
            results = [
                flight for flight in results
                if flight["cabin"].lower() == cabin.lower()
            ]

        return sorted(results, key=lambda flight: flight["price_azn"])

    def get_by_id(self, flight_id: str):
        for flight in self.flights:
            if flight["id"] == flight_id:
                return flight

        return None
