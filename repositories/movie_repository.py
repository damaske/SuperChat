class MovieRepository:

    def __init__(self, movies: list):
        self.movies = movies

    def search(
        self,
        query: str = None,
        genre: str = None,
        language: str = None,
        age_rating: str = None,
        min_rating: float = None
    ) -> list:

        results = self.movies

        if query:
            query = query.lower()

            results = [
                movie for movie in results
                if query in movie["title"].lower()
                or query in movie["synopsis"].lower()
            ]

        if genre:
            results = [
                movie for movie in results
                if genre.lower() in [
                    item.lower() for item in movie["genre"]
                ]
            ]

        if language:
            results = [
                movie for movie in results
                if movie["language"].lower() == language.lower()
            ]

        if age_rating:
            results = [
                movie for movie in results
                if movie["age_rating"] == age_rating
            ]

        if min_rating is not None:
            results = [
                movie for movie in results
                if movie["rating"] >= min_rating
            ]

        return sorted(
            results,
            key=lambda movie: movie["rating"],
            reverse=True
        )

    def get_by_id(self, movie_id: str):
        for movie in self.movies:
            if movie["id"] == movie_id:
                return movie

        return None
