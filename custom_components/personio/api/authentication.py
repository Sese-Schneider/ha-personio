"""Authentication for the Personio API"""

import logging
import time
import jwt
import requests
from requests import Response

from config.custom_components.personio.api.base import BASE_URL
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

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

        headers = {
            "Authorization": self.get_bearer()
        }

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
