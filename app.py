
import re

from models.session_state import SessionState
from router import Router

from repositories.data_loader import load_all_data
from repositories.flight_repository import FlightRepository
from repositories.product_repository import ProductRepository
from repositories.movie_repository import MovieRepository
from repositories.cinema_repository import CinemaRepository

from services.flight_service import FlightService
from services.shopping_service import ShoppingService
from services.cinema_service import CinemaService


class SuperChat:
    def __init__(self):
        self.data = load_all_data()
        self.session = SessionState()
        self.router = Router()

        self.flight_service = FlightService(
            FlightRepository(self.data["flights"])
        )

        self.shopping_service = ShoppingService(
            ProductRepository(self.data["products"])
        )

        self.cinema_service = CinemaService(
            MovieRepository(self.data["movies"]),
            CinemaRepository(
                self.data["movies"],
                self.data["cinemas"],
                self.data["showtimes"]
            )
        )

    def extract_price(self, text):
        match = re.search(
            r"(?:до|under|below|less than)\s*(\d+(?:[.,]\d+)?)",
            text,
            re.IGNORECASE
        )

        if match:
            return float(match.group(1).replace(",", "."))

        return None

    def extract_date(self, text):
        match = re.search(r"\b2026-\d{2}-\d{2}\b", text)
        return match.group(0) if match else None

    def print_flights(self, flights):
        if not flights:
            print("Не найдено подходящих авиабилетов.")
            return

        print("\nНайденные рейсы:")

        for flight in flights:
            stops = (
                "Без пересадок"
                if flight["stops"] == 0
                else f"Пересадок: {flight['stops']}"
            )

            print(
                f"{flight['id']} | {flight['airline']} | "
                f"{flight['origin']['city']} → "
                f"{flight['destination']['city']} | "
                f"{flight['departure_local']} | "
                f"{flight['price_azn']} AZN | {stops}"
            )

        print("\nЧтобы выбрать рейс, напишите ID, например: F013")

    def print_products(self, products):
        if not products:
            print("Не найдено подходящих товаров.")
            return

        print("\nНайденные товары:")

        for product in products:
            print(
                f"{product['id']} | "
                f"{product['name']['en']} | "
                f"{product['price_azn']} AZN | "
                f"В наличии: {product['stock']}"
            )

        print(
            "\nЧтобы выбрать товар, напишите его ID, "
            f"например: {products[0]['id']}"
        )
        print("Чтобы добавить товар в корзину: добавь P001 2")

    def print_movies(self, movies):
        if not movies:
            print("Подходящие фильмы не найдены.")
            return

        print("\nНайденные фильмы:")

        for movie in movies:
            print(
                f"{movie['id']} | {movie['title']} | "
                f"Жанры: {', '.join(movie['genre'])} | "
                f"Рейтинг: {movie['rating']}"
            )

        print(
            "\nЧтобы выбрать фильм, напишите его ID, "
            f"например: {movies[0]['id']}"
        )

    def print_showtimes(self, showtimes):
        if not showtimes:
            print("Подходящих сеансов не найдено.")
            return

        print("\nДоступные сеансы:")

        for item in showtimes:
            showtime = item["showtime"]

            print(
                f"{showtime['id']} | "
                f"{item['movie']['title']} | "
                f"{item['cinema']['name']} | "
                f"{showtime['date']} {showtime['time']} | "
                f"{showtime['price_azn']} AZN | "
                f"Мест: {showtime['seats_available']}"
            )

        print(
            "\nЧтобы выбрать сеанс, напишите его ID, "
            f"например: {showtimes[0]['showtime']['id']}"
        )

    def search_flights(self, text):
        city_aliases = {
            "баку": "Baku",
            "baku": "Baku",
            "стамбул": "Istanbul",
            "стамбуле": "Istanbul",
            "istanbul": "Istanbul",
            "дубай": "Dubai",
            "дубае": "Dubai",
            "dubai": "Dubai",
            "москва": "Moscow",
            "москве": "Moscow",
            "moscow": "Moscow",
            "тбилиси": "Tbilisi",
            "tbilisi": "Tbilisi",
            "ташкент": "Tashkent",
            "ташкенте": "Tashkent",
            "tashkent": "Tashkent"
        }

        params = self.session.flights.search_params.copy()

        for alias, city in city_aliases.items():
            if f"из {alias}" in text or f"from {alias}" in text:
                params["origin"] = city

            if f"в {alias}" in text or f"to {alias}" in text:
                params["destination"] = city

        date = self.extract_date(text)
        if date:
            params["date"] = date

        price = self.extract_price(text)
        if price is not None:
            params["max_price"] = price

        if (
            "без пересадок" in text
            or "direct" in text
            or "non-stop" in text
        ):
            params["max_stops"] = 0

        results = self.flight_service.search_flights(
            self.session,
            **params
        )

        self.print_flights(results)

    def search_products(self, text):
        params = self.session.shopping.search_params.copy()

        price = self.extract_price(text)
        if price is not None:
            params["max_price"] = price

        if "наушник" in text or "headphone" in text:
            params["query"] = "headphones"
        elif "рюкзак" in text or "backpack" in text:
            params["query"] = "backpack"
        elif "телефон" in text or "phone" in text:
            params["query"] = "phone"
        elif "колонк" in text or "speaker" in text:
            params["query"] = "speaker"
        elif "товар" in text or "product" in text:
            params["query"] = None

        results = self.shopping_service.search_products(
            self.session,
            **params
        )

        self.print_products(results)

    def search_cinema(self, text):
        params = self.session.cinema.search_params.copy()

        if "sci-fi" in text or "фантаст" in text:
            params["genre"] = "sci-fi"
        elif "комеди" in text or "comedy" in text:
            params["genre"] = "comedy"
        elif "ужас" in text or "horror" in text:
            params["genre"] = "horror"

        date = self.extract_date(text)
        if date:
            params["date"] = date

        movie_query = params.get("movie_title")

        if (
            movie_query
            or "сеанс" in text
            or "сеансы" in text
            or "showtime" in text
        ):
            results = self.cinema_service.search_showtimes(
                self.session,
                **{
                    key: value
                    for key, value in params.items()
                    if key in {
                        "movie_title", "cinema_name", "district",
                        "date", "max_price", "min_seats"
                    }
                }
            )
            self.print_showtimes(results)
        else:
            results = self.cinema_service.search_movies(
                self.session,
                **{
                    key: value
                    for key, value in params.items()
                    if key in {
                        "query", "genre", "language",
                        "age_rating", "min_rating"
                    }
                }
            )
            self.print_movies(results)

    def handle_follow_up(self, message, domains):
        text = message.lower().strip()

        if "shopping" in domains:
            products = self.session.shopping.results

            if not products:
                print("Сначала найдите товары.")
                return

            if any(word in text for word in [
                "second", "второй", "вторая", "второе"
            ]):
                index = 1
            elif any(word in text for word in [
                "third", "третий", "третья", "третье"
            ]):
                index = 2
            elif any(word in text for word in [
                "first", "первый", "первая", "первое"
            ]):
                index = 0
            else:
                selected = self.session.shopping.selected_products

                if selected:
                    product = selected[-1]
                elif len(products) == 1:
                    product = products[0]
                else:
                    print("Какой товар вы имеете в виду?")
                    return

                index = None

            if index is not None:
                if index >= len(products):
                    print(
                        f"В предыдущем результате найдено "
                        f"только {len(products)} товар(а). "
                        "Другого варианта нет."
                    )
                    return

                product = products[index]

                self.shopping_service.select_product(
                    self.session,
                    product["id"]
                )

            if "stock" in text or "налич" in text:
                if product["stock"] > 0:
                    print(
                        f"Да, {product['name']['en']} есть в наличии. "
                        f"Остаток: {product['stock']} шт."
                    )
                else:
                    print(
                        f"К сожалению, {product['name']['en']} "
                        "нет в наличии."
                    )
            else:
                print(
                    f"Выбран товар: {product['name']['en']}, "
                    f"{product['price_azn']} AZN."
                )

            return

        if "flights" in domains:
            flights = self.session.flights.results

            if not flights:
                print("Сначала найдите авиабилеты.")
                return

            if "second" in text or "втор" in text:
                index = 1
            elif "third" in text or "трет" in text:
                index = 2
            else:
                index = 0

            if index >= len(flights):
                print("Такого варианта нет в предыдущем результате.")
                return

            flight = flights[index]

            self.flight_service.select_flight(
                self.session,
                flight["id"]
            )

            if "direct" in text or "пересад" in text:
                if flight["stops"] == 0:
                    print(
                        f"Да, рейс {flight['flight_number']} "
                        "прямой, без пересадок."
                    )
                else:
                    print(
                        f"Нет, рейс {flight['flight_number']} "
                        f"имеет {flight['stops']} пересадку(и)."
                    )
            else:
                print(
                    f"Выбран рейс {flight['flight_number']}, "
                    f"цена {flight['price_azn']} AZN."
                )

            return

        if "cinema" in domains:
            movies = self.session.cinema.movies

            if not movies:
                print("Сначала найдите фильмы.")
                return

            if "second" in text or "втор" in text:
                index = 1
            else:
                index = 0

            if index >= len(movies):
                print("Такого фильма нет в предыдущем результате.")
                return

            movie = movies[index]
            self.cinema_service.select_movie(
                self.session,
                movie["id"]
            )
            print(f"Вы выбрали фильм: {movie['title']}.")

    def handle_selection(self, text):
        match = re.search(
            r"\b(F\d{3}|P\d{3}|M\d{3}|S\d{3})\b",
            text.upper()
        )

        if not match:
            return False

        item_id = match.group(1)

        if item_id.startswith("F"):
            item = self.flight_service.select_flight(
                self.session, item_id
            )
            print(
                f"Выбран рейс {item['flight_number']}."
                if item else "Рейс не найден."
            )

        elif item_id.startswith("P"):
            item = self.shopping_service.select_product(
                self.session, item_id
            )
            print(
                f"Выбран товар: {item['name']['en']}."
                if item else "Товар не найден."
            )

        elif item_id.startswith("M"):
            item = self.cinema_service.select_movie(
                self.session, item_id
            )
            print(
                f"Выбран фильм: {item['title']}."
                if item else "Фильм не найден."
            )

        elif item_id.startswith("S"):
            item = self.cinema_service.select_showtime(
                self.session, item_id
            )
            print(
                f"Выбран сеанс: {item['time']}."
                if item else "Сеанс не найден."
            )

        return True

    def handle_cart(self, text):
        match = re.search(
            r"(?:добавь|add)\s+(P\d{3})(?:\s+(\d+))?",
            text,
            re.IGNORECASE
        )

        if match:
            product_id = match.group(1).upper()
            quantity = int(match.group(2) or 1)

            result = self.shopping_service.add_to_cart(
                self.session,
                product_id,
                quantity
            )

            print(result["message"])
            return True

        if "корзин" in text or "cart" in text:
            cart = self.shopping_service.get_cart_summary(
                self.session
            )

            print("\nВаша корзина:")

            if not cart["items"]:
                print("Корзина пока пуста.")
            else:
                for item in cart["items"]:
                    product = item["product"]
                    print(
                        f"{product['name']['en']} × "
                        f"{item['quantity']} = "
                        f"{item['subtotal']} AZN"
                    )

                print(f"Итого: {cart['total']} AZN")

            return True

        return False

    def handle_booking(self, text):
        if not any(word in text for word in [
            "бронь", "забронируй", "забронировать",
            "book", "reserve"
        ]):
            return False

        domain = self.session.last_active_domain

        if domain == "flights":
            result = self.flight_service.reserve_selected_flight(
                self.session
            )
        elif domain == "cinema":
            match = re.search(
                r"\b(\d+)\s*(?:мест|билет|seat|ticket)",
                text
            )
            seats = int(match.group(1)) if match else 1

            result = self.cinema_service.reserve_selected_showtime(
                self.session, seats
            )
        else:
            print("Сначала выберите рейс или киносеанс.")
            return True

        print(result["message"])

        if result["success"]:
            print("Данные бронирования:", result["reservation"])

        return True

    def handle_message(self, message):
        text = message.lower().strip()

        if not text:
            return

        if self.handle_cart(text):
            return

        if self.handle_selection(text):
            return

        if self.handle_booking(text):
            return

        result = self.router.classify(message, self.session)

        print(f"\n[Router] Category: {result.category}")
        print(f"[Router] Domains: {result.domains}")

        if result.category == "Ambiguous":
            print(result.clarification_question)
            return

        if result.category == "Out of scope":
            print(
                "Я могу помочь с авиабилетами, покупками "
                "и бронированием билетов в кино."
            )
            return

        if result.category == "Follow-up":
            self.handle_follow_up(message, result.domains)
            return

        for domain in result.domains:
            if domain == "flights":
                self.search_flights(text)
            elif domain == "shopping":
                self.search_products(text)
            elif domain == "cinema":
                self.search_cinema(text)

    def run(self):
        print("=" * 50)
        print("Welcome to SuperChat!")
        print("Авиабилеты | Покупки | Кино")
        print("Напишите 'выход', чтобы завершить работу.")
        print("=" * 50)

        while True:
            message = input("\nВы: ").strip()

            if message.lower() in {"выход", "exit", "quit"}:
                print("SuperChat: До свидания!")
                break

            try:
                self.handle_message(message)
            except Exception:
                print(
                    "Произошла ошибка при обработке запроса. "
                    "Попробуйте переформулировать сообщение."
                )


if __name__ == "__main__":
    app = SuperChat()
    app.run()
