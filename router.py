
from dataclasses import dataclass

from models.session_state import SessionState


@dataclass
class RoutingResult:
    category: str
    domains: list[str]
    needs_clarification: bool = False
    clarification_question: str | None = None


class Router:
    VALID_DOMAINS = {"flights", "shopping", "cinema"}

    def __init__(self):
        self.domain_keywords = {
            "flights": [
                "flight", "flights", "рейс", "рейсы",
                "перелет", "перелёт", "авиабилет",
                "авиабилеты", "самолет", "самолёт",
                "авиаперелет", "авиаперелёт"
            ],

            "shopping": [
                "product", "products", "товар", "товары",
                "купить", "наушник", "наушники", "рюкзак",
                "ноутбук", "телефон", "цена", "корзина",
                "магазин", "headphones", "backpack",
                "laptop", "phone", "speaker"
            ],

            "cinema": [
                "movie", "movies", "film", "films",
                "фильм", "фильмы", "кино", "кинотеатр",
                "сеанс", "сеансы", "cinema", "showtime"
            ]
        }

        self.follow_up_phrases = [
            "подешевле", "дороже",
            "первый", "второй", "третий",
            "а этот", "а эта", "а это",
            "он есть", "она есть",
            "есть ли еще", "есть ли ещё",
            "покажи остальные",

            "the second one",
            "the first one",
            "the third one",
            "the cheaper one",
            "the more expensive one",
            "is it in stock",
            "is it direct",
            "what about this one",
            "show me the next",
            "the other one",
            "does it have"
        ]

        self.booking_phrases = [
            "забронируй",
            "забронировать",
            "бронь",
            "бронировать",
            "book",
            "reserve",
            "reservation"
        ]

        self.ambiguous_phrases = [
            "что-нибудь",
            "что нибудь",
            "что-то хорошее",
            "что то хорошее",
            "покажи что-нибудь",
            "покажи что нибудь",
            "something good",
            "show me something"
        ]

    def classify(
        self,
        message: str,
        session: SessionState | None = None
    ) -> RoutingResult:

        text = " ".join(message.lower().strip().split())

        active_domain = (
            session.last_active_domain if session else None
        )

        if active_domain not in self.VALID_DOMAINS:
            active_domain = None

        # 1. Empty message

        if not text:
            return RoutingResult(
                category="Ambiguous",
                domains=[],
                needs_clarification=True,
                clarification_question="Что именно вы хотите найти?"
            )

        # 2. Detect explicitly mentioned domains

        matched_domains = []

        for domain, keywords in self.domain_keywords.items():
            if any(keyword in text for keyword in keywords):
                matched_domains.append(domain)

        # 3. Multiple domains = Mixed

        if len(matched_domains) > 1:
            return RoutingResult(
                category="Mixed",
                domains=matched_domains
            )

        # 4. One explicit domain

        if len(matched_domains) == 1:
            domain = matched_domains[0]

            return RoutingResult(
                category=domain.capitalize(),
                domains=[domain]
            )

        # 5. Booking requests

        is_booking = any(
            phrase in text
            for phrase in self.booking_phrases
        )

        if is_booking:
            if active_domain:
                return RoutingResult(
                    category="Follow-up",
                    domains=[active_domain]
                )

            return RoutingResult(
                category="Ambiguous",
                domains=[],
                needs_clarification=True,
                clarification_question=(
                    "Вы хотите забронировать авиабилет "
                    "или места в кинотеатре?"
                )
            )

        # 6. Follow-up requests

        is_follow_up = any(
            phrase in text
            for phrase in self.follow_up_phrases
        )

        if is_follow_up:
            if active_domain:
                return RoutingResult(
                    category="Follow-up",
                    domains=[active_domain]
                )

            return RoutingResult(
                category="Ambiguous",
                domains=[],
                needs_clarification=True,
                clarification_question=(
                    "Уточните, пожалуйста, к какому "
                    "предыдущему запросу относится сообщение?"
                )
            )

        # 7. General ambiguous requests

        is_ambiguous = any(
            phrase in text
            for phrase in self.ambiguous_phrases
        )

        if is_ambiguous:
            return RoutingResult(
                category="Ambiguous",
                domains=[],
                needs_clarification=True,
                clarification_question=(
                    "Вы хотите найти авиабилеты, товары или фильмы?"
                )
            )

        # 8. Unsupported requests

        return RoutingResult(
            category="Out of scope",
            domains=[]
        )
