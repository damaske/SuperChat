class ProductRepository:

    def __init__(self, products: list):
        self.products = products

    def search(
        self,
        query: str = None,
        category: str = None,
        brand: str = None,
        max_price: float = None,
        min_price: float = None,
        min_rating: float = None,
        in_stock: bool = None,
        sort: str = None,
        condition: str = None
    ) -> list:

        results = self.products

        if query:
            query = query.lower()

            results = [
                product for product in results
                if query in product["name"]["en"].lower()
                or query in product["description"].lower()
                or query in product["category"].lower()
                or query in product["brand"].lower()
            ]

        if category:
            results = [
                product for product in results
                if product["category"].lower() == category.lower()
            ]

        if brand:
            results = [
                product for product in results
                if product["brand"].lower() == brand.lower()
            ]

        if max_price is not None:
            results = [
                product for product in results
                if product["price_azn"] <= max_price
            ]

        if min_price is not None:
            results = [
                product for product in results
                if product["price_azn"] >= min_price
            ]

        if min_rating is not None:
            results = [
                product for product in results
                if product["rating"] >= min_rating
            ]

        if in_stock is not None:
            results = [
                product for product in results
                if (product["stock"] > 0) == in_stock
            ]

        return sorted(
            results,
            key=lambda product: product["price_azn"]
        )

    def get_by_id(self, product_id: str):
        for product in self.products:
            if product["id"] == product_id:
                return product

        return None
