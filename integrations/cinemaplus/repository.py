from typing import Any

from .client import CinemaPlusAPIError, CinemaPlusClient


class CinemaPlusRepository:
    def __init__(self, client: CinemaPlusClient):
        self.client = client
        self._movies: dict[str, dict[str, Any]] = {}
        self._showtimes: dict[str, dict[str, Any]] = {}

    def search_movies(self, query=None, genre=None, language=None, age_rating=None, min_rating=None):
        movies = self.client.list_movies()
        results = []
        for movie in movies:
            if query and query.lower() not in movie["title"].lower():
                continue
            normalized = {
                "id": movie["id"],
                "title": movie["title"],
                "synopsis": "",
                "genre": [],
                "language": None,
                "age_rating": None,
                "rating": None,
                "url": movie["url"],
            }
            self._movies[normalized["id"]] = normalized
            results.append(normalized)
        return results

    def search(self, query=None, genre=None, language=None, age_rating=None, min_rating=None):
        return self.search_movies(query, genre, language, age_rating, min_rating)

    def get_movie_by_id(self, movie_id):
        movie = self._movies.get(movie_id)
        if movie is None:
            return None
        details = self.client.movie_details(
            "/" + "/".join(movie["url"].split("/")[-4:])
        )
        movie.update(details)
        return movie

    def get_by_id(self, movie_id):
        return self.get_movie_by_id(movie_id)

    def search_cinemas(self, name=None, district=None):
        results = self.client.list_cinemas()
        if name:
            results = [item for item in results if name.lower() in item["name"].lower()]
        return results

    def search_showtimes(
        self,
        movie_title=None,
        cinema_name=None,
        district=None,
        date=None,
        max_price=None,
        min_seats=None,
        available_only=True,
    ):
        rows = self.client.sessions_by_date(date=self._api_date(date))
        results = []
        for row in rows:
            if movie_title and movie_title.lower() not in row["title"].lower():
                continue
            if cinema_name:
                requested_cinema = cinema_name.lower().replace("cinemaplus", "").strip()
                actual_cinema = row["cinema_name"].lower()
                if (
                    requested_cinema not in actual_cinema
                    and actual_cinema not in requested_cinema
                ):
                    continue
            price = self._price(row["price_text"], row["data"].get("price"))
            if max_price is not None and (price is None or price > max_price):
                continue
            showtime = {
                "id": row["data"].get("session") or f"{row['cinema_code']}-{row['time']}",
                "movie_id": row["movie_path"].rstrip("/").split("/")[-1],
                "movie_title": row["title"],
                "cinema_id": row["cinema_code"],
                "cinema_name": row["cinema_name"],
                "date": row["date"],
                "time": row["time"],
                "price_azn": price,
                "currency": "AZN",
                "hall": row["hall"],
                "language": row["language_id"],
                "format": row["hall"],
                "seats_available": None,
                "purchase_url": None,
                "external": True,
                "raw": row,
            }
            movie = {
                "id": showtime["movie_id"],
                "title": row["title"],
                "synopsis": "",
                "genre": [],
                "language": row.get("language_id"),
                "age_rating": row["data"].get("age"),
                "rating": None,
                "url": self.client.base_url.rstrip("/") + row["movie_path"],
            }
            self._movies[showtime["movie_id"]] = movie
            if min_seats is not None or available_only:
                hall = self.client.hall(
                    row["cinema_code"],
                    row["data"].get("session") or "",
                    row["data"].get("price"),
                    row["data"].get("repeater"),
                )
                available = sum(
                    1 for place in hall["places"] if str(place.get("Status")) == "4"
                )
                showtime["seats_available"] = available
                if min_seats is not None and available < min_seats:
                    continue
                if available_only and available == 0:
                    continue
            self._showtimes[str(showtime["id"])] = showtime
            results.append({
                "showtime": showtime,
                "movie": movie,
                "cinema": {"id": row["cinema_code"], "name": row["cinema_name"]},
            })
        return sorted(results, key=lambda item: (item["showtime"]["date"], item["showtime"]["time"], item["showtime"]["price_azn"] or 0))

    def get_showtime_by_id(self, showtime_id):
        return self._showtimes.get(showtime_id)

    def get_available_seats(self, showtime_id):
        showtime = self._showtimes.get(str(showtime_id))
        if showtime is None:
            return None
        hall = self.client.hall(
            showtime["cinema_id"],
            showtime["id"],
            showtime["raw"]["data"].get("price"),
            showtime["raw"]["data"].get("repeater"),
        )
        return sum(
            1 for place in hall["places"] if str(place.get("Status")) == "4"
        )

    @staticmethod
    def _api_date(value):
        if not value:
            return None
        if "." in value:
            return value
        parts = value.split("-")
        if len(parts) == 3:
            return f"{parts[2]}.{parts[1]}.{parts[0]}"
        return value

    @staticmethod
    def _price(text, value):
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
        import re
        match = re.search(r"\d+(?:\.\d+)?", text or "")
        return float(match.group()) if match else None
