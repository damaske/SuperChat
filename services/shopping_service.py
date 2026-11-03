
class ShoppingService:
    def __init__(self, product_repository):
        self.product_repository = product_repository

    def search_products(
        self,
        session,
        query=None,
        category=None,
        brand=None,
        max_price=None,
        min_price=None,
        min_rating=None,
        in_stock=None,
        sort=None,
        condition=None
    ):
        """Search products and save results in the user's session."""

        results = self.product_repository.search(
            query=query,
            category=category,
            brand=brand,
            max_price=max_price,
            min_price=min_price,
            min_rating=min_rating,
            in_stock=in_stock,
            sort=sort,
            condition=condition,
        )

        session.shopping.search_params = {
            "query": query,
            "category": category,
            "brand": brand,
            "max_price": max_price,
            "min_price": min_price,
            "min_rating": min_rating,
            "in_stock": in_stock,
            "sort": sort,
            "condition": condition,
        }

        session.shopping.results = results
        session.shopping.selected_products = []
        session.last_active_domain = "shopping"

        return results

    def get_product_details(self, product_id):
        """Return product details by ID."""

        return self.product_repository.get_by_id(product_id)

    def select_product(self, session, product_id):
        """Select a product and save it in the session."""

        product = self.product_repository.get_by_id(product_id)

        if product is None:
            return None

        if product not in session.shopping.selected_products:
            session.shopping.selected_products.append(product)

        session.last_active_domain = "shopping"

        return product

    def add_to_cart(self, session, product_id, quantity=1):
        """Add a product to the cart if enough stock is available."""

        if quantity <= 0:
            return {
                "success": False,
                "message": "Quantity must be greater than zero."
            }

        product = self.product_repository.get_by_id(product_id)

        if product is None:
            return {
                "success": False,
                "message": "Product not found."
            }

        current_quantity = session.shopping.cart.get(product_id, 0)
        new_quantity = current_quantity + quantity

        if product.get("stock") is None:
            return {
                "success": False,
                "message": "Stock availability is not provided for this listing."
            }

        if new_quantity > product["stock"]:
            return {
                "success": False,
                "message": f"Only {product['stock']} units are available."
            }

        session.shopping.cart[product_id] = new_quantity
        session.last_active_domain = "shopping"

        return {
            "success": True,
            "message": f"{product['name']['en']} added to cart.",
            "quantity": new_quantity
        }

    def remove_from_cart(self, session, product_id, quantity=None):
        """Remove a product or reduce its quantity in the cart."""

        current_quantity = session.shopping.cart.get(product_id, 0)

        if current_quantity == 0:
            return {
                "success": False,
                "message": "Product is not in the cart."
            }

        if quantity is None or quantity >= current_quantity:
            del session.shopping.cart[product_id]
            remaining = 0
        elif quantity <= 0:
            return {
                "success": False,
                "message": "Quantity must be greater than zero."
            }
        else:
            remaining = current_quantity - quantity
            session.shopping.cart[product_id] = remaining

        session.last_active_domain = "shopping"

        return {
            "success": True,
            "message": "Cart updated.",
            "remaining_quantity": remaining
        }

    def get_cart_summary(self, session):
        """Return cart items and the total price."""

        items = []
        total = 0.0

        for product_id, quantity in session.shopping.cart.items():
            product = self.product_repository.get_by_id(product_id)

            if product is None:
                continue

            price = product.get("price", product.get("price_azn"))
            if price is None:
                continue
            subtotal = round(price * quantity, 2)
            total += subtotal

            items.append({
                "product": product,
                "quantity": quantity,
                "subtotal": subtotal
            })

        return {
            "items": items,
            "total": round(total, 2),
            "currency": items[0]["product"].get("currency", "AZN")
            if items else "AZN"
        }
