
import datetime
from math import nan
import pandas as pd
import re
import requests
from textblob import TextBlob  # For sentiment analysis.


class NoResults(Exception):
    pass


def url_encode(string: str):
    """Take a raw input string and URL encode it."""
    replacements = {"!": "%21", "#": "%23", "$": "%24", "&": "%26", "'": "%27",
                    "(": "%28", ")": "%29", "*": "%2A", "+": "%2B", ",": "%2C",
                    "/": "%2F", ":": "%3A", ";": "%3B", "=": "%3D", "?": "%3F",
                    "@": "%40", "[": "%5B", "]": "%5D", " ": "%20", "\"": "%22",
                    "-": "%2D", ".": "%2E", "<": "%3C", ">": "%3E", "\\": "%5C",
                    "^": "%5E", "_": "%5F", "`": "%60", "{": "%7B", "|": "%7C",
                    "}": "%7D", "~": "%7E", "%": "%25"}
    encoded = ""
    for char in string:
        encoded += replacements.get(char, char)
    return encoded


def strip_regex(tweet, regex):
    """Strip a tweet of any text matching the supplied regex. Returns the
    text(s) removed, count of text(s) removed, and remaining tweet minus the
    removed text(s)."""
    # Extract all matches from the tweet:
    matches = re.findall(regex, tweet)

    # Count all matches:
    match_count = len(matches)

    # Remove matches from tweet:
    stripped_tweet = tweet
    for text in matches:
        stripped_tweet = stripped_tweet.replace(text, "")

    # Remove any double spaces left behind from text stripping:
    stripped_tweet = re.sub("\s+", "  ", stripped_tweet).strip()

    return matches, match_count, stripped_tweet


def strip_urls(tweet):
    """Find urls in an individual tweet. Returns the url(s), count of url(s),
    and tweet text minus url(s)."""
    # This is a fairly crude method to extract URLs. It won't identify bad
    # links, and will also miss certain non-HTTP format URLs, e.g.
    # mailto: ftp:// etc.
    regex = r'([Hh][Tt][Tt][Pp][Ss]?[://][^\s]+)'
    return strip_regex(tweet, regex)


def strip_ats(tweet):
    """Find twitter accounts mentioned in an individual tweet. Returns the
    Twitter handle(s), count of Twitter handle(s), and tweet text minus Twitter
    handle(s)."""
    regex = r'(?<=^|(?<=[^a-zA-Z0-9-_\.]))([@][A-Za-z]+[A-Za-z0-9]+)'
    return strip_regex(tweet, regex)


def strip_hashtags(tweet):
    """Find hashtags in an individual tweet. Returns the hashtag(s), count of
    hashtag(s), and tweet text minus hashtag(s)."""
    regex = r"#(\w+)"
    return strip_regex(tweet, regex)


def strip_tweet(tweet):
    """Function to strip a tweet's text of @ and # symbols, and any urls."""
    stripped_tweet = tweet.replace("#", "")
    stripped_tweet = stripped_tweet.replace("@", "")
    return strip_urls(stripped_tweet)[2]


class TweezerSearch:
    def __init__(self, auth, search_term: str, language: str = "en",
                 total: int = 100, result_type: str = "recent",
                 search_type: str = "words", include_rts: bool = False):
        self.__auth = auth
        self.search_term = search_term
        self.total = total
        self.result_type = result_type
        self.language = language
        self.search_type = search_type
        self.include_RTs = include_rts

        # Encode the search term for URL use:
        self.search_string = self._make_search_string(search_term, search_type, include_rts)

        # Variables for storing data:
        self.results_json = list()  # Full list of json tweets.
        self.ids = list()  # Unique tweet ids.
        self.completed_in = 0.0  # Total length of time taken to complete all search iterations.
        self.result_count = 0  # Number of tweets that have actually been collected.

        # Iterate through twitter searches, using a new max_id value each
        # iteration to collect the set of next oldest tweets. Continues until
        # the number of results collected exceeds the requested total.
        next_max_id = None
        while self.result_count < total:

            # Generate the full search URL and make the GET request:
            url = self._make_url(next_max_id)
            results = requests.get(url, auth=self.__auth.auth)

            # Check request was successful and break loop if not:
            if results.status_code != 200:
                print(f"Unsuccessful request, status code: {results.status_code}")
                break

            # Raise an error if no results at all returned by the search:
            if not len(results.json()["statuses"]) and not self.result_count:
                raise NoResults("Search criteria didn't return any results.")

            # If results are returned add them to the main results variable
            if len(results.json()["statuses"]):

                # Add the tweets to the main results variable:
                self.results_json += results.json()["statuses"]
                self.result_count = len(self.results_json)

                # Set `max_id` for the next iteration:
                self.ids = [tweet["id"] for tweet in self.results_json]
                next_max_id = min(self.ids) - 1

                # Add the time taken to the total .completed_in variable.
                self.completed_in += float(results.json()["search_metadata"]['completed_in'])

            # If no more results are returned, end loop here:
            elif not len(results.json()["statuses"]):
                break

        # Trim the results to the count limit:
        if self.result_count > self.total:
            self.results_json = self.results_json[:total]
            self.result_count = self.total
            self.ids = self.ids[:total]

        print(f"{self.total:,} tweets requested, {self.result_count:,} tweets returned")
        self.df = self.clean_results(pd.DataFrame(self.results_json))

        # Generate lists of the available features in the tweets.
        self.tweet_features = list(self.results_json[0].keys())
        self.entities = list(self.results_json[0]["entities"].keys())
        self.user_features = list(self.results_json[0]["user"].keys())

    @staticmethod
    def clean_results(df: pd.DataFrame):
        df = df.copy()
        df["user"] = [u["screen_name"] for u in df["user"]]
        df["tweet"] = df["text"]
        df["stripped_tweet"] = [strip_tweet(t) for t in df["tweet"]]
        df["urls"] = [strip_urls(t)[0] for t in df["tweet"]]
        df["hashtags"] = [strip_hashtags(t)[0] for t in df["tweet"]]
        df["ats"] = [strip_ats(t)[0] for t in df["tweet"]]
        df["created_at"] = pd.to_datetime(df["created_at"], format="%a %b %d %H:%M:%S +0000 %Y")
        df["tweet_blob"] = [TextBlob(t) for t in df["stripped_tweet"]]
        df["polarity"] = [t.sentiment.polarity for t in df["tweet_blob"]]
        df["subjectivity"] = [t.sentiment.subjectivity for t in df["tweet_blob"]]
        df["coordinates"] = [t["coordinates"] if t else (None, None) for t in df["geo"]]

        columns = ["user", "tweet", "stripped_tweet", "urls", "hashtags", "ats", "created_at",
                   "favorite_count", "retweet_count", "polarity", "subjectivity", "coordinates"]

        return df[columns]

    @staticmethod
    def _make_search_string(search_term: str, search_type: str,
                            include_rts: bool):
        s = url_encode(search_term)
        if search_type == "phrase":
            if s[0:2] != "%22":
                s = f"%22{s}%22"

        # Add in the filter for no RTs if applicable:
        if not include_rts:
            s = s + "-filter%3Aretweets"
        return s

    def _make_url(self, next_max_id: int = None):
        base_url = self.__auth.base_url
        url = f"{base_url}search/tweets.json?q={self.search_string}"
        url += f"&lang={self.language}&count=100&result_type={self.result_type}"
        if next_max_id:
            url += f"&max_id={next_max_id}"
        return url

    def time_per_tweet(self):
        """Average amount of time elapsing between each tweet in the results."""
        if not self.result_count:
            self.time_per_tweet = nan
        oldest, newest = min(self.df["created_at"]), max(self.df["created_at"])
        difference = newest - oldest
        return difference / self.result_count

    def tweets_per_week(self):
        """Rough estimate of the number of tweets about the search term per
        week."""
        tweets_per_week = nan
        time_per_tweet = self.time_per_tweet
        days_in_seconds = time_per_tweet.days * 24 * 60 * 60
        seconds = time_per_tweet.seconds
        total_seconds = days_in_seconds + seconds
        seconds_in_week = 60 * 60 * 24 * 7
        microseconds_in_week = seconds_in_week * 1000000
        if total_seconds > 0:
            tweets_per_week = int(seconds_in_week / total_seconds)
        elif time_per_tweet.microseconds > 0:
            tweets_per_week = int(microseconds_in_week / time_per_tweet.microseconds)
        return tweets_per_week

    def count_list_col_values(self, col: str):
        """Count the values in one of the columns in `df` which contains lists.

        Args:
            col (str): column name in `df` attribute; valid options are:
                `urls`, `hashtags`, `ats`.
        """
        assert col in ("urls", "hashtags", "ats"), f"Invalid column name: {col}"
        all_values = [i for l in self.df[col] for i in l]
        return pd.Series(all_values).value_counts()

    def __str__(self):
        return f"TweezerSearch instance created with arguments:"\
            f"\n\tsearch_term = {self.search_term}"\
            f"\n\ttotal = {self.total:,}"

    def __repr__(self):
        return f"TweezerSearch instance created with arguments:"\
            f"\n\tsearch_term = {self.search_term}"\
            f"\n\ttotal = {self.total:,}"
