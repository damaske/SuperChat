from repositories.data_loader import load_all_data
from repositories.movie_repository import MovieRepository


data = load_all_data()

movie_repository = MovieRepository(data["movies"])


results = movie_repository.search(
    genre="sci-fi",
    min_rating=8.0
)


for movie in results:
    print(
        movie["id"],
        movie["title"],
        movie["genre"],
        movie["rating"]
    )
