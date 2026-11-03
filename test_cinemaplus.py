import os
from unittest.mock import patch

import httpx

from integrations.cinemaplus import (
    CinemaPlusAPIError,
    CinemaPlusClient,
    CinemaPlusRepository,
)


SESSION_HTML = """
<tr data-cinema="28Mall" data-date="03.11.2026"
    data-real-date="03.11.2026" data-language="1798">
  <td><a href="/az/films/yad-ana/">Yad Ana</a></td>
  <td>10:00</td>
  <td><a href="/az/cinema/about-cinemaplus/28-mall/">28 Mall</a></td>
  <td>Platinum</td><td></td><td>20.00 AZN</td>
  <td><div class="zone_input" data-price="20.00"
      data-session="198423" data-repeater="4358988"></div></td>
</tr>
"""


class FakeResponse:
    def __init__(self, text="", payload=None, status_code=200):
        self.text = text
        self._payload = payload
        self.status_code = status_code

    @property
    def is_error(self):
        return self.status_code >= 400

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def test_sessions_request_and_html_parsing():
    with patch(
        "integrations.cinemaplus.client.httpx.get",
        return_value=FakeResponse(text=SESSION_HTML),
    ) as get:
        rows = CinemaPlusClient().sessions_by_date("03.11.2026")

    params = get.call_args.kwargs["params"]
    assert params == {"lang": "default", "datex": "03.11.2026"}
    assert rows[0]["title"] == "Yad Ana"
    assert rows[0]["data"]["session"] == "198423"
    assert rows[0]["price_text"] == "20.00 AZN"


def test_hall_json_and_repository_normalization():
    hall = {"places": [{"Status": "4"}, {"Status": "2"}], "price": "20.00"}
    with patch(
        "integrations.cinemaplus.client.httpx.get",
        side_effect=[
            FakeResponse(text=SESSION_HTML),
            FakeResponse(payload=hall),
        ],
    ):
        repository = CinemaPlusRepository(CinemaPlusClient())
        results = repository.search_showtimes(
            cinema_name="28 Mall",
            date="03.11.2026",
            available_only=True,
        )

    showtime = results[0]["showtime"]
    assert showtime["price_azn"] == 20.0
    assert showtime["seats_available"] == 1
    assert showtime["external"] is True
    assert showtime["purchase_url"] is None


def test_empty_results_and_http_errors():
    with patch(
        "integrations.cinemaplus.client.httpx.get",
        return_value=FakeResponse(text=""),
    ):
        assert CinemaPlusClient().sessions_by_date("01.01.2099") == []

    with patch(
        "integrations.cinemaplus.client.httpx.get",
        return_value=FakeResponse(status_code=403),
    ):
        try:
            CinemaPlusClient().sessions_by_date("03.11.2026")
        except CinemaPlusAPIError as error:
            assert error.status_code == 403
        else:
            raise AssertionError("Expected CinemaPlusAPIError")


def test_timeout():
    with patch(
        "integrations.cinemaplus.client.httpx.get",
        side_effect=httpx.TimeoutException("timeout"),
    ):
        try:
            CinemaPlusClient().sessions_by_date("03.11.2026")
        except CinemaPlusAPIError as error:
            assert "timed out" in str(error)
        else:
            raise AssertionError("Expected timeout error")


if __name__ == "__main__":
    test_sessions_request_and_html_parsing()
    test_hall_json_and_repository_normalization()
    test_empty_results_and_http_errors()
    test_timeout()
    print("CINEMAPLUS TESTS PASSED")
