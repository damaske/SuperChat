class CinemaRepository:

    def __init__(self, movies: list, cinemas: list, showtimes: list):
        self.movies = movies
        self.cinemas = cinemas
        self.showtimes = showtimes

        self.movies_by_id = {
            movie["id"]: movie for movie in movies
        }

        self.cinemas_by_id = {
            cinema["id"]: cinema for cinema in cinemas
        }

    def search_cinemas(
        self,
        name: str = None,
        district: str = None
    ) -> list:

        results = self.cinemas

        if name:
            results = [
                cinema for cinema in results
                if name.lower() in cinema["name"].lower()
            ]

        if district:
            results = [
                cinema for cinema in results
                if cinema["district"].lower() == district.lower()
            ]

        return results

    def search_showtimes(
        self,
        movie_title: str = None,
        cinema_name: str = None,
        district: str = None,
        date: str = None,
        max_price: float = None,
        min_seats: int = None,
        available_only: bool = False
    ) -> list:

        results = []

        for showtime in self.showtimes:

            movie = self.movies_by_id.get(showtime["movie_id"])
            cinema = self.cinemas_by_id.get(showtime["cinema_id"])

            if movie is None or cinema is None:
                continue

            if movie_title:
                if movie_title.lower() not in movie["title"].lower():
                    continue

            if cinema_name:
                if cinema_name.lower() not in cinema["name"].lower():
                    continue

            if district:
                if district.lower() != cinema["district"].lower():
                    continue

            if date:
                if showtime["date"] != date:
                    continue

            if max_price is not None:
                if showtime["price_azn"] > max_price:
                    continue

            if min_seats is not None:
                if showtime["seats_available"] < min_seats:
                    continue

            if available_only:
                if showtime["seats_available"] <= 0:
                    continue

            results.append({
                "showtime": showtime,
                "movie": movie,
                "cinema": cinema
            })

        return sorted(
            results,
            key=lambda item: (
                item["showtime"]["date"],
                item["showtime"]["time"]
            )
        )

    def get_showtime_by_id(self, showtime_id: str):
        for showtime in self.showtimes:
            if showtime["id"] == showtime_id:
                return showtime

        return None
