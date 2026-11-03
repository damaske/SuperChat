import re
from datetime import datetime
import time
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import httpx


class CinemaPlusAPIError(RuntimeError):
    """Raised when the public CinemaPlus site cannot serve cinema data."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


BASE_URL = "https://cinemastercard.az/"


class _SessionParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows: list[dict[str, Any]] = []
        self._row: dict[str, Any] | None = None
        self._cell = ""
        self._link = ""
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self._row = {
                "cinema_code": attrs.get("data-cinema"),
                "date": attrs.get("data-date"),
                "real_date": attrs.get("data-real-date"),
                "language_id": attrs.get("data-language"),
                "cells": [],
                "data": {},
            }
        elif self._row is not None and tag == "td":
            self._in_cell = True
            self._cell = ""
            self._link = ""
        elif self._row is not None and tag == "a":
            self._link = attrs.get("href") or ""
        elif self._row is not None and tag == "div":
            for key in (
                "price",
                "hall",
                "language",
                "session",
                "repeater",
                "cinema",
                "age",
                "kids",
                "break",
            ):
                if f"data-{key}" in attrs:
                    self._row["data"][key] = attrs[f"data-{key}"]

    def handle_data(self, data):
        if self._row is not None and self._in_cell:
            self._cell += data

    def handle_endtag(self, tag):
        if self._row is None:
            return
        if tag == "td":
            self._row["cells"].append(
                {"text": " ".join(self._cell.split()), "href": self._link}
            )
            self._in_cell = False
        elif tag == "tr":
            cells = self._row["cells"]
            if len(cells) >= 6:
                self._row["title"] = cells[0]["text"]
                self._row["movie_path"] = cells[0]["href"]
                self._row["time"] = cells[1]["text"]
                self._row["cinema_name"] = cells[2]["text"]
                self._row["cinema_path"] = cells[2]["href"]
                self._row["hall"] = cells[3]["text"]
                self._row["price_text"] = cells[5]["text"]
                self.rows.append(self._row)
            self._row = None


class _OptionParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.options: list[dict[str, str | None]] = []
        self._option: dict[str, str | None] | None = None
        self._text = ""

    def handle_starttag(self, tag, attrs):
        if tag == "option":
            values = dict(attrs)
            self._option = {"value": values.get("value"), "data-session": values.get("data-session")}
            self._text = ""

    def handle_data(self, data):
        if self._option is not None:
            self._text += data

    def handle_endtag(self, tag):
        if tag == "option" and self._option is not None:
            self._option["text"] = " ".join(self._text.split())
            self.options.append(self._option)
            self._option = None


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text = ""

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = ""

    def handle_data(self, data):
        if self._href is not None:
            self._text += data

    def handle_endtag(self, tag):
        if tag == "a" and self._href:
            self.links.append((self._href, " ".join(self._text.split())))
            self._href = None


class CinemaPlusClient:
    def __init__(
        self,
        timeout: float = 30.0,
        base_url: str = BASE_URL,
        cache_ttl: float = 60.0,
    ):
        self.timeout = timeout
        self.base_url = base_url.rstrip("/") + "/"
        self.cache_ttl = cache_ttl
        self._cache: dict[tuple, tuple[float, Any]] = {}

    def _get(self, path: str, params: dict[str, Any] | None = None):
        cache_key = (path, tuple(sorted((params or {}).items())))
        cached = self._cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < self.cache_ttl:
            return cached[1]

        response = None
        for attempt in range(2):
            try:
                response = httpx.get(
                    urljoin(self.base_url, path.lstrip("/")),
                    params=params,
                    timeout=self.timeout,
                    headers={"Accept": "text/html, application/json"},
                )
            except httpx.TimeoutException as error:
                raise CinemaPlusAPIError("CinemaPlus request timed out.") from error
            except httpx.RequestError as error:
                raise CinemaPlusAPIError("CinemaPlus is unavailable.") from error
            if response.status_code != 429 or attempt == 1:
                break
            time.sleep(0.2)
        if response.status_code in {401, 403}:
            raise CinemaPlusAPIError(
                "CinemaPlus rejected the public request.",
                response.status_code,
            )
        if response.is_error:
            raise CinemaPlusAPIError(
                f"CinemaPlus returned HTTP {response.status_code}.",
                response.status_code,
            )
        self._cache[cache_key] = (time.monotonic(), response)
        return response

    def sessions_by_date(
        self,
        date: str | None = None,
        movie: str | None = None,
        language: str = "default",
    ) -> list[dict[str, Any]]:
        date = date or datetime.now(ZoneInfo("Asia/Baku")).strftime("%d.%m.%Y")
        params = {"lang": language, "datex": date}
        if movie:
            params["movie"] = movie
        response = self._get("/get_sessions_by_date.php", params)
        parser = _SessionParser()
        parser.feed(response.text)
        return parser.rows

    def hall(
        self,
        cinema: str,
        session_id: str,
        price: str | None = None,
        repeater_id: str | None = None,
    ) -> dict[str, Any]:
        params = {
            "cinema": cinema,
            "session_id": session_id,
            "price": price or "",
            "repeater_id": repeater_id or "",
        }
        response = self._get("/getHall.php", params)
        try:
            payload = response.json()
        except ValueError as error:
            raise CinemaPlusAPIError("CinemaPlus returned invalid hall JSON.") from error
        if not isinstance(payload, dict) or not isinstance(payload.get("places"), list):
            raise CinemaPlusAPIError("CinemaPlus returned an invalid hall response.")
        return payload

    def session_info(self, session_id: str, cinema: str) -> str:
        return self._get(
            "/session_info.php",
            {"session": session_id, "cinema": cinema},
        ).text

    def session_dates(self, movie: str) -> list[str]:
        response = self._get("/getSessionsDates.php", {"movie": movie})
        parser = _OptionParser()
        parser.feed(response.text)
        return [str(item["value"]) for item in parser.options if item.get("value")]

    def sessions(self, cinema: str, movie: str, date: str) -> list[dict[str, str | None]]:
        response = self._get(
            "/getSessions.php",
            {"cinema": cinema, "movie": movie, "datex": date},
        )
        parser = _OptionParser()
        parser.feed(response.text)
        return parser.options

    def list_movies(self, date: str | None = None) -> list[dict[str, Any]]:
        rows = self.sessions_by_date(date=date)
        movies: dict[str, dict[str, Any]] = {}
        for row in rows:
            path = row.get("movie_path") or ""
            key = path or row["title"]
            movies[key] = {
                "id": self._movie_id(path),
                "title": row["title"],
                "url": urljoin(self.base_url, path),
            }
        return list(movies.values())

    def movie_details(self, path: str) -> dict[str, Any]:
        response = self._get(path)
        title_match = re.search(r"<title>\s*(.*?)\s*(?:&bull;|</title>)", response.text, re.I | re.S)
        description_match = re.search(
            r'<meta[^>]+(?:name|property)="(?:description|og:description)"[^>]+content="([^"]*)"',
            response.text,
            re.I,
        )
        return {
            "id": self._movie_id(path),
            "title": re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else path,
            "synopsis": description_match.group(1).strip() if description_match else "",
            "url": urljoin(self.base_url, path),
        }

    def list_cinemas(self) -> list[dict[str, str]]:
        response = self._get("/az/")
        parser = _LinkParser()
        parser.feed(response.text)
        cinemas = {}
        for href, text in parser.links:
            if "/cinema/about-cinemaplus/" in href and text:
                cinemas[href] = {
                    "id": href.rstrip("/").split("/")[-1],
                    "name": text,
                    "url": urljoin(self.base_url, href),
                }
        if not cinemas:
            for row in self.sessions_by_date():
                href = row.get("cinema_path") or ""
                code = row.get("cinema_code")
                name = row.get("cinema_name")
                if code and name:
                    cinemas[code] = {
                        "id": code,
                        "name": name,
                        "url": urljoin(self.base_url, href),
                    }
        return list(cinemas.values())

    @staticmethod
    def _movie_id(path: str) -> str:
        return path.rstrip("/").split("/")[-1] or "unknown"
