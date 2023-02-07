"""Employees for the Persionio API."""

import requests
from config.custom_components.personio.api.authentication import Authentication
from config.custom_components.personio.api.base import BASE_URL


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
