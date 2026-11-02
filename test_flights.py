from repositories.data_loader import load_all_data
from repositories.flight_repository import FlightRepository


data = load_all_data()

flight_repository = FlightRepository(data["flights"])


results = flight_repository.search(
    origin="Baku",
    destination="Istanbul",
    max_price=300
)


for flight in results:
    print(
        flight["id"],
        flight["airline"],
        flight["price_azn"],
        flight["stops"]
    )
