
from repositories.data_loader import load_all_data
from repositories.movie_repository import MovieRepository
from repositories.cinema_repository import CinemaRepository
from services.cinema_service import CinemaService
from models.session_state import SessionState


data = load_all_data()

movie_repository = MovieRepository(data["movies"])

cinema_repository = CinemaRepository(
    data["movies"],
    data["cinemas"],
    data["showtimes"]
)

service = CinemaService(
    movie_repository,
    cinema_repository
)

session = SessionState()

# 1. Search movies
movies = service.search_movies(
    session,
    genre="sci-fi",
    min_rating=8.0
)

print("MOVIES FOUND:", len(movies))

for movie in movies:
    print(movie["id"], movie["title"], movie["rating"])

assert len(movies) == 2

# 2. Select a movie
selected_movie = service.select_movie(session, "M001")

assert selected_movie is not None
print("\nSELECTED MOVIE:", selected_movie["title"])

# 3. Search showtimes
showtimes = service.search_showtimes(
    session,
    movie_title="Orbit Zero",
    date="2026-11-05",
    available_only=True
)

print("\nSHOWTIMES FOUND:", len(showtimes))

for item in showtimes:
    print(
        item["showtime"]["id"],
        item["cinema"]["name"],
        item["showtime"]["time"],
        item["showtime"]["price_azn"]
    )

assert len(showtimes) > 0

# 4. Select a showtime
selected_showtime = service.select_showtime(
    session,
    "S008"
)

assert selected_showtime is not None
print("\nSELECTED SHOWTIME:", selected_showtime["id"])

# 5. Reserve two seats
result = service.reserve_selected_showtime(session, seats=2)

print("\nRESERVATION:", result)

assert result["success"] is True
assert result["reservation"]["seats"] == 2
assert result["reservation"]["total_price_azn"] == 26.0

print(
    "\nREMAINING SEATS:",
    selected_showtime["seats_available"]
)

print("\nALL CINEMA SERVICE TESTS PASSED")
