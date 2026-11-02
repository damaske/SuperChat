from repositories.data_loader import load_all_data
from repositories.product_repository import ProductRepository


data = load_all_data()

product_repository = ProductRepository(data["products"])


results = product_repository.search(
    category="audio",
    max_price=100,
    in_stock=True
)


for product in results:
    print(
        product["id"],
        product["name"]["en"],
        product["price_azn"],
        product["stock"]
    )
