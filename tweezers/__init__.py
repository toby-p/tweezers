
from tweezers.auth import TweezerAuth
from tweezers.search import TweezerSearch


class Tweezers:
    """Class to perform a twitter search on given search term(s)."""

    def __init__(self, api_key: str, api_secret_key: str,
                 access_token: str, access_token_secret: str):
        """Initialize a Tweezers instance by passing valid Twitter app
        credentials, which can be obtained from:
            https://developer.twitter.com/en/apps/
        """
        self.__auth = TweezerAuth(api_key, api_secret_key, access_token, access_token_secret)
        self.status_code = self.get_status()
        self.search_history = list()

    def get_status(self):
        return self.__auth.get_status()

    def search(self, search_term: str, language: str = "en", total: int = 100,
               result_type: str = "recent", search_type: str = "words",
               include_rts: bool = False):
        """Perform a search via the Twitter API. For additional documentation,
        see the Twitter docs at:
            https://developer.twitter.com/en/docs/tweets/search/api-reference/get-search-tweets

        Args:
            search_term (str): term to search for.
            language (str): language to search in.
            total (int): desired number of tweets to return. Note that it may
                not be possible to return the full number requested, either due
                to a lack of available tweets meeting the criteria, or rate-
                limiting by the twitter API - see:
                https://dev.twitter.com/rest/public/rate-limiting
            result_type (str): either `mixed`, `recent`, or `popular`.
            search_type (str): either `words` or `phrase`. If 'phrase` then
                all words are searched as one phrase, and will only return
                tweets containing all words in the given order.
            include_rts (bool): whether to include retweets in search results.
        """
        s = TweezerSearch(auth=self.__auth, search_term=search_term, language=language,
                          total=total, result_type=result_type, search_type=search_type,
                          include_rts=include_rts)
        self.search_history.append(s)
        return s

    def __str__(self):
        return f"Tweezers instance with status code {self.status_code}"

    def __repr__(self):
        return f"Tweezers instance with status code {self.status_code}"
