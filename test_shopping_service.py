
from repositories.data_loader import load_all_data
from repositories.product_repository import ProductRepository
from services.shopping_service import ShoppingService
from models.session_state import SessionState


data = load_all_data()

repository = ProductRepository(data["products"])
service = ShoppingService(repository)

session = SessionState()

# 1. Search products
results = service.search_products(
    session,
    category="audio",
    max_price=100,
    in_stock=True
)

print("SEARCH RESULTS:", len(results))

for product in results:
    print(
        product["id"],
        product["name"]["en"],
        product["price_azn"]
    )

assert len(results) == 2

# 2. Select a product
selected = service.select_product(session, "P001")

assert selected is not None
print("\nSELECTED:", selected["name"]["en"])

# 3. Add products to cart
result = service.add_to_cart(session, "P001", 2)

print("\nADD TO CART:", result)

assert result["success"] is True

# 4. Check cart total
cart = service.get_cart_summary(session)

print("\nCART ITEMS:", len(cart["items"]))
print("CART TOTAL:", cart["total"], cart["currency"])

assert len(cart["items"]) == 1
assert cart["items"][0]["quantity"] == 2
assert cart["total"] == round(selected["price_azn"] * 2, 2)

# 5. Remove one product
result = service.remove_from_cart(session, "P001", 1)

print("\nREMOVE FROM CART:", result)

assert result["success"] is True
assert session.shopping.cart["P001"] == 1

print("\nALL SHOPPING SERVICE TESTS PASSED")
