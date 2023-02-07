"""Persionio API handler."""

from datetime import datetime, timedelta
import logging
import time

import jwt
import requests
from requests import Response

from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)
BASE_URL = "https://api.personio.de/v1"


class Authentication:
    """Authentication for the Personio API."""

    _current_config: dict = None
    _current_token: str = None

    def set_config(self, config: dict):
        """Set the current API configuration."""
        self._current_config = config["data"]

        # self test current auth config, fetch initial token for usage
        self.get_bearer(invalidate=False)

    def get_bearer(self, invalidate: bool = True):
        """Get a currently valid authentication bearer."""

        if not self._current_config:
            raise HomeAssistantError("Config not defined.")

        if self._current_token:
            jwt_token = jwt.decode(
                self._current_token,
                algorithms=["HS256"],
                options={"verify_signature": False},
            )
            if jwt_token["exp"] > time.time():
                _LOGGER.debug("Reusing existing JWT token")
                bearer = "Bearer " + self._current_token
                if invalidate:
                    # bearers are one-time use only
                    _LOGGER.debug("Invalidating JWT token")
                    self._current_token = None

                return bearer

        _LOGGER.debug("Requesting new JWT token")
        authentication = authenticate(
            self._current_config["client_id"],
            self._current_config["client_secret"],
            self._current_config["partner_id"],
            self._current_config["app_id"],
        )

        self._current_token = authentication.json()["data"]["token"]
        return self.get_bearer(invalidate=invalidate)

    def get_headers(self):
        """Returns all headers required for a successful Personio API request."""
        partner_id = self._current_config["partner_id"]
        app_id = self._current_config["app_id"]

        headers = {"Authorization": self.get_bearer()}

        if partner_id:
            headers["X-Personio-Partner-ID"] = partner_id
        if app_id:
            headers["X-Personio-App-ID"] = app_id
        return headers

    def set_response(self, response: Response):
        """Callback after receiving a new response.
        Call this to set new authorization headers after each successful request."""
        self._current_token = response.headers["authorization"].removeprefix("Bearer ")
        _LOGGER.debug("New JWT token received")


class Employees:
    """Employees for the Persionio API."""

    def __init__(self, authentication: Authentication) -> None:
        self._authentication = authentication

    def get_employee_id_by_mail(self, employee_email: int) -> bool:
        """Get Employees from the Personio API."""

        result = requests.get(
            BASE_URL + "/company/employees",
            headers=self._authentication.get_headers(),
            params={"email": employee_email},
            timeout=10000,
        )
        result.raise_for_status()
        self._authentication.set_response(result)

        return result.json()["data"][0]["attributes"]["id"]["value"]


class Attendances:
    """Attendances for the Persionio API."""

    def __init__(self, authentication: Authentication) -> None:
        self._authentication = authentication

    def add_attendance(
        self,
        employee_id: int,
        start_time: float,
        end_time: float,
        now: datetime,
    ):
        """Add attendances to the Personio API."""

        attendances = []

        start_date = datetime.fromtimestamp(start_time, tz=now.tzinfo)
        end_date = datetime.fromtimestamp(end_time, tz=now.tzinfo)

        for single_date in _daterange(start_date, end_date):
            attendances.append(
                {
                    "employee": employee_id,
                    "date": single_date.strftime("%Y-%m-%d"),
                    "start_time": start_date.strftime("%H:%M")
                    if _is_on_date(start_date, single_date)
                    else "00:00",
                    "end_time": end_date.strftime("%H:%M")
                    if _is_on_date(end_date, single_date)
                    else "23:59",
                    "break": 0,
                    "project_id": None,
                    "comment": "Generated by Sese-Schneider/ha-personio",
                }
            )

        result = requests.post(
            BASE_URL + "/company/attendances",
            headers=self._authentication.get_headers(),
            timeout=10000,
            json={"attendances": attendances},
        )
        result.raise_for_status()
        self._authentication.set_response(result)

        _LOGGER.info("Attendance for employee %s added successfully", employee_id)


def authenticate(
    client_id: str,
    client_secret: str,
    partner_id: str = None,
    app_id: str = None,
):
    """Authenticate agains the Personio API."""
    headers = {}
    if partner_id:
        headers["X-Personio-Partner-ID"] = partner_id
    if app_id:
        headers["X-Personio-App-ID"] = app_id

    result = requests.post(
        BASE_URL + "/auth",
        params={"client_id": client_id, "client_secret": client_secret},
        headers=headers,
        timeout=10000,
    )
    result.raise_for_status()
    return result


def _daterange(start_date: datetime, end_date: datetime):
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
    days = int((end_date - start_date).days)

    for n in range(days + 1):  # pylint: disable=invalid-name
        yield start_date + timedelta(days=n)


def _is_on_date(to_check: datetime, on_date: datetime) -> bool:
    return on_date < to_check < on_date + timedelta(days=1)