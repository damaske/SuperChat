
import re
import logging
import time
from contextlib import redirect_stdout
from datetime import date, datetime, timedelta
from io import StringIO

from agents.llm_router import LLMRouter
from integrations.aviasales import (
    AviasalesAPIError,
    AviasalesClient,
    AviasalesFlightRepository,
)
from integrations.serpapi import SerpApiClient, SerpApiError, SerpApiProductRepository
from integrations.cinemaplus import CinemaPlusAPIError, CinemaPlusClient, CinemaPlusRepository
from models.session_state import SessionState

from services.flight_service import FlightService
from services.shopping_service import ShoppingService
from services.cinema_service import CinemaService
from language import detect_language

logger = logging.getLogger("superchat")


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
        self.session = SessionState()
        self.router = LLMRouter()

        self.flight_service = FlightService(
            AviasalesFlightRepository(AviasalesClient())
        )

        self.shopping_service = ShoppingService(
            SerpApiProductRepository(SerpApiClient())
        )

        cinema_repository = CinemaPlusRepository(CinemaPlusClient())
        self.cinema_service = CinemaService(
            cinema_repository,
            cinema_repository,
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

    def _set_request_language(self, message: str, detected: str | None = None):
        language = detected or detect_language(message)
        if language:
            self.session.language = language

    def _localize_output(self, output: str) -> str:
        language = self.session.language
        if language == "ru":
            return output

        translations = {
            "Не найдено подходящих авиабилетов.": {
                "en": "No suitable flights were found.",
                "az": "Uyğun uçuş tapılmadı.",
            },
            "Найденные товары:": {
                "en": "Products found:",
                "az": "Tapılan məhsullar:",
            },
            "Найденные фильмы:": {
                "en": "Movies found:",
                "az": "Tapılan filmlər:",
            },
            "Доступные сеансы:": {
                "en": "Available sessions:",
                "az": "Mövcud seanslar:",
            },
            "Подходящие фильмы не найдены.": {
                "en": "No matching movies were found.",
                "az": "Uyğun film tapılmadı.",
            },
            "Подходящих сеансов не найдено.": {
                "en": "No matching sessions were found.",
                "az": "Uyğun seans tapılmadı.",
            },
            "Чтобы выбрать товар, напишите его ID,": {
                "en": "To select a product, send its ID,",
                "az": "Məhsulu seçmək üçün ID-ni yazın,",
            },
            "Чтобы выбрать фильм, напишите его ID,": {
                "en": "To select a movie, send its ID,",
                "az": "Filmi seçmək üçün ID-ni yazın,",
            },
            "Чтобы выбрать сеанс, напишите его ID,": {
                "en": "To select a session, send its ID,",
                "az": "Seansı seçmək üçün ID-ni yazın,",
            },
            "Чтобы добавить товар в корзину: добавь P001 2": {
                "en": "To add a product to the cart: add P001 2",
                "az": "Məhsulu səbətə əlavə etmək üçün: add P001 2",
            },
            "Состояние": {"en": "Condition", "az": "Vəziyyət"},
            "Продавец": {"en": "Seller", "az": "Satıcı"},
            "Доставка": {"en": "Shipping", "az": "Çatdırılma"},
            "Рейтинг": {"en": "Rating", "az": "Reytinq"},
            "Отзывы": {"en": "Reviews", "az": "Rəylər"},
            "Описание": {"en": "Description", "az": "Təsvir"},
            "Цена": {"en": "Price", "az": "Qiymət"},
            "Вылет": {"en": "Departure", "az": "Uçuş"},
            "Остановки": {"en": "Stops", "az": "Dayanacaqlar"},
            "Мест:": {"en": "Seats:", "az": "Yerlər:"},
            "Ссылка Aviasales:": {"en": "Aviasales link:", "az": "Aviasales linki:"},
            "Ссылка eBay:": {"en": "eBay link:", "az": "eBay linki:"},
            "Официальная страница CinemaPlus:": {
                "en": "Official CinemaPlus page:",
                "az": "CinemaPlus rəsmi səhifəsi:",
            },
            "Покупка через SuperChat недоступна; используйте официальный сайт CinemaPlus.": {
                "en": "Purchasing through SuperChat is unavailable; use the official CinemaPlus site.",
                "az": "SuperChat ilə alış mümkün deyil; CinemaPlus rəsmi saytından istifadə edin.",
            },
            "Не удалось определить направление запроса.": {
                "en": "I could not determine the request domain.",
                "az": "Sorğunun istiqamətini müəyyən etmək olmadı.",
            },
            "Я могу помочь с авиабилетами, покупками и поиском фильмов и киносеансов.": {
                "en": "I can help with flights, shopping, and finding movies and cinema sessions.",
                "az": "Uçuşlar, alış-veriş, filmlər və kino seanslarında kömək edə bilərəm.",
            },
            "Уточните, пожалуйста, ваш запрос.": {
                "en": "Please clarify your request.",
                "az": "Zəhmət olmasa, sorğunuzu dəqiqləşdirin.",
            },
            "Сначала найдите авиабилеты.": {
                "en": "Please search for flights first.",
                "az": "Əvvəlcə uçuş axtarın.",
            },
            "Сначала найдите товары.": {
                "en": "Please search for products first.",
                "az": "Əvvəlcə məhsul axtarın.",
            },
            "Сначала найдите фильмы или сеансы.": {
                "en": "Please search for movies or sessions first.",
                "az": "Əvvəlcə film və ya seans axtarın.",
            },
            "Не удалось получить данные Aviasales:": {
                "en": "Could not retrieve Aviasales data:",
                "az": "Aviasales məlumatlarını almaq olmadı:",
            },
            "Не удалось получить товары из eBay через SerpApi:": {
                "en": "Could not retrieve products from eBay through SerpApi:",
                "az": "SerpApi vasitəsilə eBay məhsullarını almaq olmadı:",
            },
            "Не удалось получить данные CinemaPlus:": {
                "en": "Could not retrieve CinemaPlus data:",
                "az": "CinemaPlus məlumatlarını almaq olmadı:",
            },
            "Ваша корзина:": {"en": "Your cart:", "az": "Səbətiniz:"},
            "Корзина пока пуста.": {"en": "Your cart is empty.", "az": "Səbət boşdur."},
            "Итого:": {"en": "Total:", "az": "Cəmi:"},
            "Сначала найдите товары.": {
                "en": "Please search for products first.",
                "az": "Əvvəlcə məhsul axtarın.",
            },
            "Сначала найдите авиабилеты.": {
                "en": "Please search for flights first.",
                "az": "Əvvəlcə uçuş axtarın.",
            },
            "Для сравнения нужны минимум два товара.": {
                "en": "At least two products are needed for comparison.",
                "az": "Müqayisə üçün ən azı iki məhsul lazımdır.",
            },
            "Для сравнения нужны минимум два варианта.": {
                "en": "At least two options are needed for comparison.",
                "az": "Müqayisə üçün ən azı iki seçim lazımdır.",
            },
            "Сравнение первых двух товаров:": {
                "en": "Comparison of the first two products:",
                "az": "İlk iki məhsulun müqayisəsi:",
            },
            "Сравнение вариантов перелёта:": {
                "en": "Comparison of flight options:",
                "az": "Uçuş seçimlərinin müqayisəsi:",
            },
            "Укажите номер товара, например: первый товар.": {
                "en": "Specify a product number, for example: the first product.",
                "az": "Məhsul nömrəsini göstərin, məsələn: birinci məhsul.",
            },
            "Какой товар вы имеете в виду?": {
                "en": "Which product do you mean?",
                "az": "Hansı məhsulu nəzərdə tutursunuz?",
            },
            "В результатах нет числовых цен для такой сортировки.": {
                "en": "The results contain no numeric prices for this sorting.",
                "az": "Bu çeşidləmə üçün nəticələrdə rəqəmsal qiymət yoxdur.",
            },
            "Не удалось получить схему выбранного зала.": {
                "en": "Could not retrieve the selected hall layout.",
                "az": "Seçilmiş zalın sxemini almaq olmadı.",
            },
            "Сначала найдите фильмы.": {
                "en": "Please search for movies first.",
                "az": "Əvvəlcə film axtarın.",
            },
        }
        localized = output
        for source, values in translations.items():
            localized = localized.replace(source, values[language])
        return localized

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

    @staticmethod
    def _print_flight_details(flight):
        print(
            f"\nДетали рейса {flight['id']}: "
            f"{flight['origin']['code']} → {flight['destination']['code']}"
        )
        print(f"Цена: {flight['price']} {flight['currency']}")
        if flight.get("departure_local"):
            print(f"Вылет: {flight['departure_local']}")
        if flight.get("airline") or flight.get("flight_number"):
            print(
                f"Перевозчик/рейс: {flight.get('airline') or 'не указан'} "
                f"{flight.get('flight_number') or ''}".rstrip()
            )
        if flight.get("stops") is not None:
            print(f"Остановки: {flight['stops']}")
        if flight.get("link"):
            print(f"Ссылка Aviasales: {flight['link']}")

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
                f"Мест: {showtime.get('seats_available') if showtime.get('seats_available') is not None else 'не указано'}"
            )
            if showtime.get("purchase_url"):
                print(f"  Ссылка на покупку: {showtime['purchase_url']}")
            elif showtime.get("external"):
                print(
                    "  Покупка через SuperChat недоступна; "
                    "используйте официальный сайт CinemaPlus."
                )
            if item.get("movie", {}).get("url"):
                print(
                    f"  Официальная страница CinemaPlus: "
                    f"{item['movie']['url']}"
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
                "sort": entities.get("sort"),
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
                        "sort",
                    },
                ),
            )
        except SerpApiError as error:
            print(f"\nНе удалось получить товары из eBay через SerpApi: {error}")
            return

        if entities.get("in_stock") is True:
            print(
                "\nФильтр наличия применён только к объявлениям, "
                "для которых eBay вернул положительный stock."
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

            if params.get("district"):
                print(
                    "\nCinemaPlus не передаёт район в расписании; "
                    "фильтр по району не применён."
                )

            try:
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
            except CinemaPlusAPIError as error:
                print(f"\nНе удалось получить данные CinemaPlus: {error}")
                return

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

            try:
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
            except CinemaPlusAPIError as error:
                print(f"\nНе удалось получить данные CinemaPlus: {error}")
                return

            self.print_movies(results)

    # --------------------------------------------------
    # FOLLOW-UP SELECTIONS
    # --------------------------------------------------

    def handle_follow_up(self, message, domains, intent):
        text = message.lower().strip()
        index = self._ordinal_index(text)

        if "shopping" in domains:
            self._set_active_domain("shopping")
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
            self._set_active_domain("flights")
            flights = self.session.flights.results

            if intent == "compare_flights" or "compar" in text or "сравн" in text:
                if len(flights) < 2:
                    print("Для сравнения нужны минимум два варианта.")
                    return
                print("\nСравнение вариантов перелёта:")
                for flight in flights[:2]:
                    print(
                        f"{flight['id']} | "
                        f"{flight['origin']['code']} → "
                        f"{flight['destination']['code']} | "
                        f"{flight['price']} {flight['currency']} | "
                        f"{flight.get('airline') or 'перевозчик не указан'} | "
                        f"{flight.get('stops') if flight.get('stops') is not None else 'остановки не указаны'} остановок"
                    )
                return

            if any(word in text for word in ("detail", "подроб", "инфо")):
                if not flights:
                    print("Сначала найдите авиабилеты.")
                    return
                selected = self.session.flights.selected_flight
                flight = selected or flights[0]
                self._print_flight_details(flight)
                return

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
            self._set_active_domain("cinema")
            showtimes = self.session.cinema.showtimes

            if showtimes and any(
                word in text
                for word in ("дешев", "cheaper", "cheapest", "сравн")
            ):
                self.print_showtimes(
                    sorted(
                        showtimes,
                        key=lambda item: (
                            item["showtime"].get("price_azn") is None,
                            item["showtime"].get("price_azn") or 0,
                        ),
                    )
                )
                return

            if showtimes and any(
                word in text for word in ("tomorrow", "завтра")
            ):
                current = self.session.cinema.search_params.get("date")
                try:
                    next_date = (
                        datetime.fromisoformat(current).date()
                        + timedelta(days=1)
                    ).isoformat()
                except (TypeError, ValueError):
                    next_date = (date.today() + timedelta(days=1)).isoformat()
                params = self._entities_to_dict_from_session()
                params["showtime_date"] = next_date
                self.search_cinema(params, "search_showtimes")
                return

            if showtimes and any(
                word in text
                for word in ("seat", "мест", "available", "доступн")
            ):
                selected = self.session.cinema.selected_showtime
                target = selected or showtimes[0]["showtime"]
                seats = self.cinema_service.get_available_seats(
                    self.session, target["id"]
                )
                if seats is None:
                    print("Не удалось получить схему выбранного зала.")
                else:
                    print(
                        f"Для сеанса {target['id']} доступно мест: {seats}."
                    )
                return

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
            r"\b(F\d{3}|P\d{3}|M\d{3}|S\d{3}|AV-[A-F0-9]+|\d{6,})\b",
            text.upper(),
        )

        if not match:
            return False

        item_id = match.group(1)

        if item_id.startswith("AV-") or item_id.startswith("F"):
            item = self.flight_service.select_flight(
                self.session,
                item_id,
            )

            print(
                f"Выбран рейс {item['flight_number']}."
                if item
                else "Рейс не найден."
            )

        elif (
            item_id.startswith("P")
            or item_id.isdigit()
            or item_id.startswith("EBAY-")
        ):
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
            r"(?:добавь|add)\s+(P\d{3}|AV-\w+|\d{6,})(?:\s+(\d+))?",
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

        match = re.search(
            r"(?:удали|remove)\s+(P\d{3}|AV-\w+|\d{6,})(?:\s+(\d+))?",
            text,
            re.IGNORECASE,
        )
        if match:
            product_id = match.group(1).upper()
            quantity = int(match.group(2)) if match.group(2) else None
            result = self.shopping_service.remove_from_cart(
                self.session, product_id, quantity
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

                print(f"Итого: {cart['total']} {cart['currency']}")

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
            print(
                "\nCinemaPlus integration is read-only. "
                "Use the official CinemaPlus site for ticket purchases."
            )
            return True

        print(
            "\nReal reservations are not supported by the configured "
            "providers."
        )
        return True

    # --------------------------------------------------
    # MAIN MESSAGE HANDLER
    # --------------------------------------------------

    def handle_message(self, message):
        self._set_request_language(message)
        output = StringIO()
        with redirect_stdout(output):
            self._handle_message_impl(message)
        localized = self._localize_output(output.getvalue())
        if localized:
            print(localized, end="" if localized.endswith("\n") else "\n")

    def _handle_message_impl(self, message):
        text = message.strip()

        if not text:
            return

        if self.handle_cart(text):
            return

        if self.handle_selection(text):
            return

        if self.handle_booking(text):
            return

        started = time.monotonic()
        decision = self.router.classify(
            message,
            self.session,
        )
        logger.info(
            "request domain=%s status=classified duration_ms=%d",
            ",".join(decision.domains) or "unknown",
            (time.monotonic() - started) * 1000,
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
