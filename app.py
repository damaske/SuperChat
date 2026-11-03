
import re

from agents.llm_router import LLMRouter
from integrations.aviasales import (
    AviasalesAPIError,
    AviasalesClient,
    AviasalesFlightRepository,
)
from integrations.serpapi import SerpApiClient, SerpApiError, SerpApiProductRepository
from models.session_state import SessionState

from repositories.data_loader import load_all_data
from repositories.movie_repository import MovieRepository
from repositories.cinema_repository import CinemaRepository

from services.flight_service import FlightService
from services.shopping_service import ShoppingService
from services.cinema_service import CinemaService


class SuperChat:
    CITY_CODES = {
        "GYD": "Baku",
        "IST": "Istanbul",
        "SAW": "Istanbul",
        "DXB": "Dubai",
        "MOW": "Moscow",
        "TBS": "Tbilisi",
        "TAS": "Tashkent",
    }

    CITY_ALIASES = {
        "баку": "Baku",
        "baku": "Baku",
        "бакy": "Baku",
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
        "tashkent": "Tashkent",
    }

    def __init__(self):
        self.data = load_all_data()
        self.session = SessionState()
        self.router = LLMRouter()

        self.flight_service = FlightService(
            AviasalesFlightRepository(AviasalesClient())
        )

        self.shopping_service = ShoppingService(
            SerpApiProductRepository(SerpApiClient())
        )

        self.cinema_service = CinemaService(
            MovieRepository(self.data["movies"]),
            CinemaRepository(
                self.data["movies"],
                self.data["cinemas"],
                self.data["showtimes"],
            ),
        )

    # --------------------------------------------------
    # HELPERS
    # --------------------------------------------------

    @staticmethod
    def _merge_params(previous: dict, new_values: dict) -> dict:
        """
        Update previous search parameters without replacing
        existing values with None.
        """
        merged = dict(previous or {})

        for key, value in new_values.items():
            if value is not None:
                merged[key] = value

        return merged

    @staticmethod
    def _clean_params(params: dict, allowed: set) -> dict:
        """
        Keep only parameters supported by a service.
        """
        return {
            key: value
            for key, value in params.items()
            if key in allowed
        }

    @staticmethod
    def _entities_to_dict(decision) -> dict:
        return decision.entities.model_dump(exclude_none=True)

    @staticmethod
    def _city_for_repository(city: str | None) -> str | None:
        if not city:
            return None

        normalized = city.strip()

        return SuperChat.CITY_CODES.get(
            normalized.upper(),
            normalized,
        )

    @staticmethod
    def _ordinal_index(text: str):
        text = text.lower()

        if re.search(
            r"\b(second|2nd)\b|втор",
            text,
        ):
            return 1

        if re.search(
            r"\b(third|3rd)\b|трет",
            text,
        ):
            return 2

        if re.search(
            r"\b(first|1st)\b|перв",
            text,
        ):
            return 0

        return None

    def _set_active_domain(self, domain: str):
        self.session.last_active_domain = domain

    # --------------------------------------------------
    # OUTPUT
    # --------------------------------------------------

    def print_flights(self, flights):
        if not flights:
            print("\nНе найдено подходящих авиабилетов.")
            return

        print(
            "\nОриентировочные цены Aviasales Data API "
            "(кэшированные данные, не гарантия наличия):"
        )

        for flight in flights:
            print(
                f"{flight['id']} | "
                f"{flight['origin']['code']} → "
                f"{flight['destination']['code']} | "
                f"{flight['price']} {flight['currency']} | "
                f"Дата: {flight.get('departure_local') or 'не указана'}"
            )
            if flight.get("airline") or flight.get("flight_number"):
                print(
                    f"  Перевозчик/рейс: "
                    f"{flight.get('airline') or 'не указан'} "
                    f"{flight.get('flight_number') or ''}".rstrip()
                )
            if flight.get("link"):
                print(f"  Ссылка Aviasales: {flight['link']}")

        print(
            "\nЦены получены из кэша Aviasales и могут измениться. "
            "Data API не гарантирует наличие мест."
        )

    def print_products(self, products):
        if not products:
            print("\nНе найдено подходящих товаров.")
            return

        print("\nНайденные товары:")

        for product in products:
            name = product.get("name", {}).get("en", "Без названия")
            price = product.get("price")
            currency = product.get("currency") or "валюта не указана"
            print(
                f"{product['id']} | {name} | "
                f"{price if price is not None else 'цена не указана'} "
                f"{currency}"
            )
            for label, key in (
                ("Состояние", "condition"),
                ("Продавец", "seller"),
                ("Доставка", "shipping"),
            ):
                if product.get(key):
                    print(f"  {label}: {product[key]}")
            if product.get("rating") is not None:
                print(
                    f"  Рейтинг: {product['rating']}"
                    f" ({product.get('reviews') or 'отзывы не указаны'})"
                )
            if product.get("product_url"):
                print(f"  Ссылка eBay: {product['product_url']}")
            if product.get("image_url"):
                print(f"  Изображение: {product['image_url']}")

        print(
            "\nЧтобы выбрать товар, напишите его ID, "
            f"например: {products[0]['id']}"
        )

        print("Чтобы добавить товар в корзину: добавь P001 2")

    @staticmethod
    def _print_product_details(product):
        print(f"\n{product['name']['en']}")
        print(
            f"Цена: {product.get('price', 'не указана')} "
            f"{product.get('currency') or ''}"
        )
        for label, key in (
            ("Описание", "description"),
            ("Состояние", "condition"),
            ("Продавец", "seller"),
            ("Доставка", "shipping"),
            ("Рейтинг", "rating"),
            ("Отзывы", "reviews"),
        ):
            if product.get(key):
                print(f"{label}: {product[key]}")
        if product.get("product_url"):
            print(f"Ссылка eBay: {product['product_url']}")
        if product.get("image_url"):
            print(f"Изображение: {product['image_url']}")

    def print_movies(self, movies):
        if not movies:
            print("\nПодходящие фильмы не найдены.")
            return

        print("\nНайденные фильмы:")

        for movie in movies:
            print(
                f"{movie['id']} | "
                f"{movie['title']} | "
                f"Жанры: {', '.join(movie['genre'])} | "
                f"Рейтинг: {movie['rating']}"
            )

        print(
            "\nЧтобы выбрать фильм, напишите его ID, "
            f"например: {movies[0]['id']}"
        )

    def print_showtimes(self, showtimes):
        if not showtimes:
            print("\nПодходящих сеансов не найдено.")
            return

        print("\nДоступные сеансы:")

        for item in showtimes:
            showtime = item["showtime"]

            print(
                f"{showtime['id']} | "
                f"{item['movie']['title']} | "
                f"{item['cinema']['name']} | "
                f"{showtime['date']} "
                f"{showtime['time']} | "
                f"{showtime['price_azn']} AZN | "
                f"Мест: {showtime['seats_available']}"
            )

        print(
            "\nЧтобы выбрать сеанс, напишите его ID, "
            f"например: {showtimes[0]['showtime']['id']}"
        )

    # --------------------------------------------------
    # FLIGHTS
    # --------------------------------------------------

    def search_flights(self, entities):
        previous = self.session.flights.search_params.copy()

        params = self._merge_params(
            previous,
            {
                "origin": entities.get("origin"),
                "destination": entities.get("destination"),
                "date": entities.get("departure_date"),
                "return_date": entities.get("return_date"),
                "max_price": entities.get("max_price"),
                "max_stops": entities.get("max_stops"),
                "cabin": entities.get("cabin_class"),
                "passengers": entities.get("passengers"),
                "currency": entities.get("currency"),
            },
        )

        # Preserve partial parameters while asking for clarification.
        self.session.flights.search_params = params
        self._set_active_domain("flights")

        required = [
            ("origin", "Из какого города вы хотите вылететь?"),
            ("destination", "В какой город вы хотите полететь?"),
        ]

        for key, question in required:
            if not params.get(key):
                print(f"\n{question}")
                return

        if params.get("passengers"):
            print(
                "\nAviasales Data API не фильтрует цены по количеству "
                "пассажиров в этом запросе."
            )
        if params.get("cabin"):
            print(
                "\nAviasales Data API не предоставляет фильтр класса "
                "обслуживания для этого endpoint."
            )

        try:
            results = self.flight_service.search_flights(
                self.session,
                **self._clean_params(
                    params,
                    {
                        "origin",
                        "destination",
                        "date",
                        "return_date",
                        "max_price",
                        "max_stops",
                        "cabin",
                        "passengers",
                        "currency",
                    },
                ),
            )
        except AviasalesAPIError as error:
            print(f"\nНе удалось получить данные Aviasales: {error}")
            return

        self.print_flights(results)

    # --------------------------------------------------
    # SHOPPING
    # --------------------------------------------------

    def search_products(self, entities):
        previous = self.session.shopping.search_params.copy()

        params = self._merge_params(
            previous,
            {
                "query": entities.get("query"),
                "category": entities.get("product_category"),
                "brand": entities.get("brand"),
                "max_price": entities.get("max_price"),
                "min_price": entities.get("min_price"),
                "min_rating": entities.get("min_rating"),
                "in_stock": entities.get("in_stock"),
                "condition": entities.get("condition"),
            },
        )

        self.session.shopping.search_params = params
        self._set_active_domain("shopping")

        if entities.get("color"):
            print(
                "\nПримечание: отдельный фильтр по цвету "
                "пока не реализован в каталоге."
            )

        try:
            results = self.shopping_service.search_products(
                self.session,
                **self._clean_params(
                    params,
                    {
                        "query",
                        "category",
                        "brand",
                        "max_price",
                        "min_price",
                        "min_rating",
                        "in_stock",
                        "condition",
                    },
                ),
            )
        except SerpApiError as error:
            print(f"\nНе удалось получить товары из eBay через SerpApi: {error}")
            return

        if entities.get("in_stock") is not None:
            print(
                "\nSerpApi/eBay не предоставляет надёжный общий фильтр "
                "остатка для этих результатов; фильтр не применён."
            )
        if entities.get("condition"):
            print(
                "\nФильтр состояния применён только по полю condition, "
                "которое eBay вернул для найденных объявлений."
            )

        self.print_products(results)

    # --------------------------------------------------
    # CINEMA
    # --------------------------------------------------

    def search_cinema(self, entities, intent):
        previous = self.session.cinema.search_params.copy()

        is_showtime_search = (
            intent == "search_showtimes"
            or bool(entities.get("cinema_name"))
            or bool(entities.get("district"))
            or bool(entities.get("showtime_date"))
            or entities.get("max_ticket_price") is not None
            or entities.get("min_seats") is not None
        )

        if is_showtime_search:
            params = self._merge_params(
                previous,
                {
                    "movie_title": entities.get("movie_title"),
                    "cinema_name": entities.get("cinema_name"),
                    "district": entities.get("district"),
                    "date": entities.get("showtime_date"),
                    "max_price": entities.get("max_ticket_price"),
                    "min_seats": entities.get("min_seats"),
                },
            )

            self.session.cinema.search_params = params
            self._set_active_domain("cinema")

            results = self.cinema_service.search_showtimes(
                self.session,
                **self._clean_params(
                    params,
                    {
                        "movie_title",
                        "cinema_name",
                        "district",
                        "date",
                        "max_price",
                        "min_seats",
                    },
                ),
            )

            self.print_showtimes(results)

        else:
            params = self._merge_params(
                previous,
                {
                    "query": entities.get("movie_title"),
                    "genre": entities.get("genre"),
                    "language": entities.get("movie_language"),
                    "age_rating": entities.get("age_rating"),
                    "min_rating": entities.get("min_rating"),
                },
            )

            self.session.cinema.search_params = params
            self._set_active_domain("cinema")

            results = self.cinema_service.search_movies(
                self.session,
                **self._clean_params(
                    params,
                    {
                        "query",
                        "genre",
                        "language",
                        "age_rating",
                        "min_rating",
                    },
                ),
            )

            self.print_movies(results)

    # --------------------------------------------------
    # FOLLOW-UP SELECTIONS
    # --------------------------------------------------

    def handle_follow_up(self, message, domains, intent):
        text = message.lower().strip()
        index = self._ordinal_index(text)

        if "shopping" in domains:
            products = self.session.shopping.results

            if intent in {"search_products", "check_stock"}:
                self.search_products(
                    self._entities_to_dict_from_session()
                )
                return

            if not products:
                print("Сначала найдите товары.")
                return

            if any(word in text for word in ("дешев", "cheaper", "cheapest")):
                prices = [
                    product["price"]
                    for product in products
                    if isinstance(product.get("price"), (int, float))
                ]
                if not prices:
                    print("В результатах нет числовых цен для такой сортировки.")
                    return
                params = self.session.shopping.search_params.copy()
                params["max_price"] = min(prices) - 0.01
                self.search_products(params)
                return

            if "new" in text or "нов" in text:
                params = self.session.shopping.search_params.copy()
                params["condition"] = "new"
                self.search_products(params)
                return

            if "compare" in text or "сравн" in text:
                if len(products) < 2:
                    print("Для сравнения нужны минимум два товара.")
                    return
                print("\nСравнение первых двух товаров:")
                for product in products[:2]:
                    print(
                        f"{product['name']['en']} | "
                        f"{product.get('price', 'цена не указана')} "
                        f"{product.get('currency') or ''} | "
                        f"{product.get('condition') or 'состояние не указано'}"
                    )
                return

            if index is not None:
                if index >= len(products):
                    print(
                        "Такого варианта нет в предыдущем результате."
                    )
                    return

                product = products[index]

                self.shopping_service.select_product(
                    self.session,
                    product["id"],
                )
                if any(word in text for word in ("detail", "подроб", "инфо")):
                    self._print_product_details(product)
                    return

            elif any(word in text for word in ("detail", "подроб", "инфо")):
                product = products[0] if len(products) == 1 else None
                if product is None:
                    print("Укажите номер товара, например: первый товар.")
                    return
                self._print_product_details(product)
                return
            else:
                selected = self.session.shopping.selected_products

                if selected:
                    product = selected[-1]
                elif len(products) == 1:
                    product = products[0]
                else:
                    print("Какой товар вы имеете в виду?")
                    return

            if "stock" in text or "налич" in text:
                if product.get("stock") is None:
                    print(
                        f"Для {product['name']['en']} SerpApi не указал "
                        "надёжную информацию о наличии."
                    )
                elif product["stock"] > 0:
                    print(
                        f"Да, {product['name']['en']} есть в наличии. "
                        f"Остаток: {product['stock']} шт."
                    )
                else:
                    print(f"{product['name']['en']} сейчас нет в наличии.")
            else:
                print(
                    f"Выбран товар: {product['name']['en']}, "
                    f"{product.get('price', 'цена не указана')} "
                    f"{product.get('currency') or ''}."
                )

            return

        if "flights" in domains:
            flights = self.session.flights.results

            if intent in {"search_flights", "compare_flights"}:
                self.search_flights(
                    self._entities_to_dict_from_session()
                )
                return

            if not flights:
                print("Сначала найдите авиабилеты.")
                return

            if index is None:
                index = 0

            if index >= len(flights):
                print(
                    "Такого варианта нет в предыдущем результате."
                )
                return

            flight = flights[index]

            self.flight_service.select_flight(
                self.session,
                flight["id"],
            )

            print(
                f"Выбран вариант {flight['id']}, "
                f"цена {flight['price']} {flight['currency']}."
            )

            return

        if "cinema" in domains:
            movies = self.session.cinema.movies

            if intent in {"search_movies", "search_showtimes"}:
                self.search_cinema(
                    self._entities_to_dict_from_session(),
                    intent,
                )
                return

            if not movies:
                print("Сначала найдите фильмы.")
                return

            if index is None:
                index = 0

            if index >= len(movies):
                print(
                    "Такого фильма нет в предыдущем результате."
                )
                return

            movie = movies[index]

            self.cinema_service.select_movie(
                self.session,
                movie["id"],
            )

            print(f"Вы выбрали фильм: {movie['title']}.")

    def _entities_to_dict_from_session(self):
        """
        Return previously stored search parameters in the
        format expected by the domain search methods.
        """
        domain = self.session.last_active_domain

        if domain == "flights":
            params = self.session.flights.search_params.copy()

            return {
                "origin": params.get("origin"),
                "destination": params.get("destination"),
                "departure_date": params.get("date"),
                "return_date": params.get("return_date"),
                "max_price": params.get("max_price"),
                "max_stops": params.get("max_stops"),
                "cabin_class": params.get("cabin"),
                "passengers": params.get("passengers"),
                "currency": params.get("currency"),
            }

        if domain == "shopping":
            return self.session.shopping.search_params.copy()

        if domain == "cinema":
            params = self.session.cinema.search_params.copy()

            return {
                "movie_title": params.get("movie_title"),
                "genre": params.get("genre"),
                "movie_language": params.get("language"),
                "age_rating": params.get("age_rating"),
                "min_rating": params.get("min_rating"),
                "cinema_name": params.get("cinema_name"),
                "district": params.get("district"),
                "showtime_date": params.get("date"),
                "max_ticket_price": params.get("max_price"),
                "min_seats": params.get("min_seats"),
            }

        return {}

    # --------------------------------------------------
    # SELECTION BY ID
    # --------------------------------------------------

    def handle_selection(self, text):
        match = re.search(
            r"\b(F\d{3}|P\d{3}|M\d{3}|S\d{3})\b",
            text.upper(),
        )

        if not match:
            return False

        item_id = match.group(1)

        if item_id.startswith("F"):
            item = self.flight_service.select_flight(
                self.session,
                item_id,
            )

            print(
                f"Выбран рейс {item['flight_number']}."
                if item
                else "Рейс не найден."
            )

        elif item_id.startswith("P"):
            item = self.shopping_service.select_product(
                self.session,
                item_id,
            )

            print(
                f"Выбран товар: {item['name']['en']}."
                if item
                else "Товар не найден."
            )

        elif item_id.startswith("M"):
            item = self.cinema_service.select_movie(
                self.session,
                item_id,
            )

            print(
                f"Выбран фильм: {item['title']}."
                if item
                else "Фильм не найден."
            )

        elif item_id.startswith("S"):
            item = self.cinema_service.select_showtime(
                self.session,
                item_id,
            )

            print(
                f"Выбран сеанс: {item['time']}."
                if item
                else "Сеанс не найден."
            )

        return True

    # --------------------------------------------------
    # CART
    # --------------------------------------------------

    def handle_cart(self, text):
        match = re.search(
            r"(?:добавь|add)\s+(P\d{3})(?:\s+(\d+))?",
            text,
            re.IGNORECASE,
        )

        if match:
            product_id = match.group(1).upper()
            quantity = int(match.group(2) or 1)

            result = self.shopping_service.add_to_cart(
                self.session,
                product_id,
                quantity,
            )

            print(result["message"])
            return True

        if "корзин" in text or "cart" in text:
            cart = self.shopping_service.get_cart_summary(
                self.session,
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

    # --------------------------------------------------
    # BOOKINGS
    # --------------------------------------------------

    def handle_booking(self, text):
        if not any(
            word in text
            for word in [
                "бронь",
                "забронируй",
                "забронировать",
                "book",
                "reserve",
            ]
        ):
            return False

        domain = self.session.last_active_domain

        if domain == "flights":
            print(
                "\nAviasales Data API предоставляет кэшированные "
                "ценовые данные и не выполняет бронирование."
            )
            return True

        if domain == "cinema":
            match = re.search(
                r"\b(\d+)\s*(?:мест|билет|seat|ticket)",
                text,
            )

            seats = int(match.group(1)) if match else 1

            result = self.cinema_service.reserve_selected_showtime(
                self.session,
                seats,
            )

            print("\n[ДЕМО-БРОНИРОВАНИЕ]")
            print(result["message"])

            if result["success"]:
                print(
                    "Это локальная демонстрационная операция. "
                    "Реальная оплата и бронирование не выполнялись."
                )

                print("Данные:", result["reservation"])

            return True

        print("Сначала выберите рейс или киносеанс.")
        return True

    # --------------------------------------------------
    # MAIN MESSAGE HANDLER
    # --------------------------------------------------

    def handle_message(self, message):
        text = message.strip()

        if not text:
            return

        if self.handle_cart(text):
            return

        if self.handle_selection(text):
            return

        if self.handle_booking(text):
            return

        decision = self.router.classify(
            message,
            self.session,
        )

        entities = self._entities_to_dict(decision)

        print(f"\n[Router] Category: {decision.category}")
        print(f"[Router] Domains: {decision.domains}")
        print(f"[Router] Intent: {decision.intent}")
        print(f"[Router] Language: {decision.language}")
        print(f"[Router] Entities: {entities}")

        # Clarification must happen before any service call.
        if decision.clarification_question:
            print(f"\n{decision.clarification_question}")
            return

        if decision.category == "Ambiguous":
            print(
                decision.clarification_question
                or "Уточните, пожалуйста, ваш запрос."
            )
            return

        if decision.category == "Out of scope":
            print(
                "\nЯ могу помочь с авиабилетами, покупками "
                "и поиском фильмов и киносеансов."
            )
            return

        if decision.category == "Follow-up":
            self.handle_follow_up(
                message,
                decision.domains,
                decision.intent,
            )
            return

        if not decision.domains:
            print("Не удалось определить направление запроса.")
            return

        # Mixed requests execute every supported domain.
        for domain in decision.domains:
            if domain == "flights":
                self.search_flights(entities)

            elif domain == "shopping":
                self.search_products(entities)

            elif domain == "cinema":
                self.search_cinema(
                    entities,
                    decision.intent,
                )

        # Keep the last processed domain as the active context.
        if decision.domains:
            self._set_active_domain(decision.domains[-1])

    # --------------------------------------------------
    # APPLICATION LOOP
    # --------------------------------------------------

    def run(self):
        print("=" * 55)
        print("Welcome to SuperChat!")
        print("Авиабилеты | Покупки | Кино")
        print("Напишите 'выход', чтобы завершить работу.")
        print("=" * 55)

        while True:
            message = input("\nВы: ").strip()

            if message.lower() in {"выход", "exit", "quit"}:
                print("SuperChat: До свидания!")
                break

            try:
                self.handle_message(message)

            except Exception as error:
                print(
                    "\nПроизошла ошибка при обработке запроса."
                )
                print(f"[DEBUG] {type(error).__name__}: {error}")


if __name__ == "__main__":
    app = SuperChat()
    app.run()
