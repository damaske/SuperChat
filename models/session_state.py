
from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class FlightState:
    search_params: dict = field(default_factory=dict)
    results: list = field(default_factory=list)
    selected_flight: dict | None = None
    reservation: dict | None = None


@dataclass
class ShoppingState:
    search_params: dict = field(default_factory=dict)
    results: list = field(default_factory=list)
    selected_products: list = field(default_factory=list)
    cart: dict = field(default_factory=dict)


@dataclass
class CinemaState:
    search_params: dict = field(default_factory=dict)
    movies: list = field(default_factory=list)
    showtimes: list = field(default_factory=list)
    selected_movie: dict | None = None
    selected_showtime: dict | None = None
    reservations: list = field(default_factory=list)


@dataclass
class SessionState:
    session_id: str = field(default_factory=lambda: str(uuid4()))
    language: str = "ru"
    preferences: dict = field(default_factory=dict)
    last_active_domain: str | None = None

    flights: FlightState = field(default_factory=FlightState)
    shopping: ShoppingState = field(default_factory=ShoppingState)
    cinema: CinemaState = field(default_factory=CinemaState)

    history: list = field(default_factory=list)
    pending_clarification: str | None = None
