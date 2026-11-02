import json
from pathlib import Path

DATA_DIR = Path("data")

files = [
    "flights.json",
    "products.json",
    "movies.json",
    "cinemas.json",
    "showtimes.json",
]

for filename in files:
    file_path = DATA_DIR / filename

    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    print(f"{filename}: {len(data)} records")
