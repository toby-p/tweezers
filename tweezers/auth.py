
import requests
from requests_oauthlib import OAuth1


class TweezerAuth:
    """Authentication for the Twitter API."""

    # Base url for all requests:
    base_url = "https://api.twitter.com/1.1/"

    # Instance attributes:
    def __init__(self, api_key: str, api_secret_key: str,
                 access_token: str, access_token_secret: str):
        """Authenticate credentials with Twitter API to make requests."""
        self.api_key = api_key
        self.access_token = access_token

        # Auth for all requests:
        self.auth = OAuth1(api_key, api_secret_key, access_token, access_token_secret)
        self.status_code = self.get_status()

    def get_status(self):
        verify_url = f"{self.base_url}account/verify_credentials.json"
        return requests.get(verify_url, auth=self.auth).status_code

    def __str__(self):
        return f"Twitter Auth with status code {self.status_code}"

    def __repr__(self):
        return f"Twitter Auth with status code {self.status_code}"
