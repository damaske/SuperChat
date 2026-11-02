import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_json(filename: str) -> list:
    file_path = DATA_DIR / filename

    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"{filename} must contain a JSON list")

    return data


def load_all_data() -> dict:
    return {
        "flights": load_json("flights.json"),
        "products": load_json("products.json"),
        "movies": load_json("movies.json"),
        "cinemas": load_json("cinemas.json"),
        "showtimes": load_json("showtimes.json"),
    }
