from repositories.data_loader import load_all_data
from repositories.cinema_repository import CinemaRepository


data = load_all_data()

cinema_repository = CinemaRepository(
    movies=data["movies"],
    cinemas=data["cinemas"],
    showtimes=data["showtimes"]
)


results = cinema_repository.search_showtimes(
    movie_title="Orbit Zero",
    date="2026-11-05",
    available_only=True
)


for item in results:
    showtime = item["showtime"]
    movie = item["movie"]
    cinema = item["cinema"]

    print(
        showtime["id"],
        movie["title"],
        cinema["name"],
        showtime["date"],
        showtime["time"],
        showtime["price_azn"],
        showtime["seats_available"]
    )
