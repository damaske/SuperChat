
from uuid import uuid4


class CinemaService:
    def __init__(self, movie_repository, cinema_repository):
        self.movie_repository = movie_repository
        self.cinema_repository = cinema_repository

    def search_movies(
        self,
        session,
        query=None,
        genre=None,
        language=None,
        age_rating=None,
        min_rating=None
    ):
        """Search movies and save results in the user's session."""

        results = self.movie_repository.search(
            query=query,
            genre=genre,
            language=language,
            age_rating=age_rating,
            min_rating=min_rating
        )

        session.cinema.search_params = {
            "query": query,
            "genre": genre,
            "language": language,
            "age_rating": age_rating,
            "min_rating": min_rating
        }

        session.cinema.movies = results
        session.cinema.selected_movie = None
        session.last_active_domain = "cinema"

        return results

    def get_movie_details(self, movie_id):
        """Return movie details by ID."""

        return self.movie_repository.get_by_id(movie_id)

    def select_movie(self, session, movie_id):
        """Select a movie and save it in the session."""

        movie = self.movie_repository.get_by_id(movie_id)

        if movie is None:
            return None

        session.cinema.selected_movie = movie
        session.last_active_domain = "cinema"

        return movie

    def search_showtimes(
        self,
        session,
        movie_title=None,
        cinema_name=None,
        district=None,
        date=None,
        max_price=None,
        min_seats=None,
        available_only=True
    ):
        """Search showtimes and save results in the user's session."""

        results = self.cinema_repository.search_showtimes(
            movie_title=movie_title,
            cinema_name=cinema_name,
            district=district,
            date=date,
            max_price=max_price,
            min_seats=min_seats,
            available_only=available_only
        )

        session.cinema.search_params = {
            "movie_title": movie_title,
            "cinema_name": cinema_name,
            "district": district,
            "date": date,
            "max_price": max_price,
            "min_seats": min_seats
        }

        session.cinema.showtimes = results
        session.last_active_domain = "cinema"

        return results

    def select_showtime(self, session, showtime_id):
        """Select a showtime and save it in the session."""

        showtime = self.cinema_repository.get_showtime_by_id(
            showtime_id
        )

        if showtime is None:
            return None

        session.cinema.selected_showtime = showtime

        movie = self.movie_repository.get_by_id(
            showtime["movie_id"]
        )

        session.cinema.selected_movie = movie
        session.last_active_domain = "cinema"

        return showtime

    def get_available_seats(self, session, showtime_id):
        seats = self.cinema_repository.get_available_seats(showtime_id)
        if seats is not None:
            for item in session.cinema.showtimes:
                if str(item["showtime"]["id"]) == str(showtime_id):
                    item["showtime"]["seats_available"] = seats
        return seats

    def reserve_selected_showtime(self, session, seats=1):
        """Create a mock cinema reservation without payment."""

        if not isinstance(seats, int) or isinstance(seats, bool) or seats <= 0:
            return {
                "success": False,
                "message": "Number of seats must be a positive integer."
            }

        showtime = session.cinema.selected_showtime

        if showtime is None:
            return {
                "success": False,
                "message": "Please select a showtime first."
            }

        if showtime.get("external"):
            return {
                "success": False,
                "message": (
                    "CinemaPlus booking is not available through this public "
                    "read-only integration. Use the official CinemaPlus site."
                ),
            }

        if showtime["seats_available"] < seats:
            return {
                "success": False,
                "message": (
                    f"Only {showtime['seats_available']} seats are available."
                )
            }

        movie = self.movie_repository.get_by_id(
            showtime["movie_id"]
        )

        cinema = self.cinema_repository.cinemas_by_id.get(
            showtime["cinema_id"]
        )

        reservation = {
            "reservation_id": str(uuid4())[:8].upper(),
            "showtime_id": showtime["id"],
            "movie": movie["title"] if movie else "Unknown movie",
            "cinema": cinema["name"] if cinema else "Unknown cinema",
            "date": showtime["date"],
            "time": showtime["time"],
            "seats": seats,
            "total_price_azn": round(showtime["price_azn"] * seats, 2),
            "status": "confirmed",
            "payment_status": "not_required_mock"
        }

        showtime["seats_available"] -= seats
        session.cinema.reservations.append(reservation)
        session.last_active_domain = "cinema"

        return {
            "success": True,
            "reservation": reservation,
            "message": "Your mock cinema reservation is confirmed."
        }
