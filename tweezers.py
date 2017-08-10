#!/usr/bin/env python

# Dependencies
import requests
import json
from requests_oauthlib import OAuth1
from collections import OrderedDict
import re
import datetime


# Primary class for running twitter searches and getting multiple results back.
class tweezer(object):
    """Class to scrape data for a user-defined search term using the twitter Search API."""

    def __init__(self, consumer_key, consumer_secret, access_token, access_token_secret):

        # Twitter auth variables
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret

        # Auth for all requests
        self.auth = OAuth1(consumer_key, consumer_secret, access_token, access_token_secret)

        # Base url for all requests
        self.base_url = 'https://api.twitter.com/1.1/'

    def verify(self):
        verify_url = self.base_url + \
                    'account/verify_credentials.json'
        status_code = requests.get(verify_url, auth = self.auth).status_code
        if status_code == 200:
            return 'Congratulations! Your credentials are valid.'
        else:
            return 'Oops, something wrong with your credentials - HTTP response error code %d.' %status_code

    def __str__(self):
        return """Twitter API instance created with:
        \t public consumer key = %s
        \t public access token = %s""" % (self.consumer_key, self.access_token)

    def __percent_encode(self, string):
        """Takes a raw input string and URL encodes it."""

        replacements = {"!":"%21","#":"%23","$":"%24","&":"%26","'":"%27","(":"%28",\
                ")":"%29","*":"%2A","+":"%2B",",":"%2C","/":"%2F",":":"%3A",\
                ";":"%3B","=":"%3D","?":"%3F","@":"%40","[":"%5B","]":"%5D",\
                " ":"%20","\"":"%22","-":"%2D",".":"%2E","<":"%3C",">":"%3E",\
                "\\":"%5C","^":"%5E","_":"%5F","`":"%60","{":"%7B","|":"%7C",\
                "}":"%7D","~":"%7E"}

        # Percent has to be first otherwise replacement characters will themselves be replaced.
        encoding = OrderedDict()
        encoding["%"] = "%25"

        for key, value in replacements.items():
            encoding[key] = value

        for character in encoding:
            if character in string:
                string = string.replace(character, encoding[character])

        return string

    def search(self, search_term, language='en', count=100, result_type='mixed', search_type='words', include_RTs=False):
        """Performs a twitter search on the given search term(s). Optional parameters are:
        * language: as per the twitter documentation at https://dev.twitter.com/rest/reference/get/search/tweets
        * count: as per the twitter documentation at https://dev.twitter.com/rest/reference/get/search/tweets
        * result_type: as per the twitter documentation at https://dev.twitter.com/rest/reference/get/search/tweets
        * search_type: Valid options are 'words' (default) and 'phrase'. If 'phrase' is used then
          multiple search words will be searched as one phrase, and will only be returned in the
          results if all words are found in the given order in a tweet.
        * include_RTs: whether to include retweets in the search results (default False).
          """

        if count > 100:
            raise ValueError("Maximum value for *count* cannot exceed 100.")

        search_string = self.__percent_encode(search_term)

        if search_type == "phrase":
            if search_string[0:2] != "%22":
                search_string = "%22" + search_string +"%22"

        if include_RTs==False:
            search_string = search_string + "-filter%3Aretweets"

        search_url = self.base_url + \
                    'search/tweets.json?q=' + search_string + \
                    '&lang=' + language + \
                    '&count=' + str(count) + \
                    '&result_type=' + result_type

        tweets = requests.get(search_url, auth = self.auth)

        return tweets.json()

    def search_multipage(self, search_term, language='en', count=100, result_type='mixed', \
                         search_type='words', max_pages=10, include_RTs=False):
        """Performs a twitter search on the given search term(s), with the additional parameter of max_pages to enable
        twitter searches returning multiple pages of results.

        The search will return a list of n dictionaries with keys 'search_metadata' and 'statuses', where n is max_pages.

        Optional parameters are:
        * language
        * count
        * result_type
        * search_type: Valid options are 'words' (default) and 'phrase'. If 'phrase' is used then
          multiple search words will be searched as one phrase, and will only be returned in the
          results if all words are found in the given order in a tweet.
        * max_pages: number of pages of results the search will return.
        * include_RTs: whether to include retweets in the search results (default False).
          """

        search_string = self.__percent_encode(search_term)
        if search_type == 'phrase':
            if search_string[0:2] != "%22":
                search_string = "%22" + search_string +"%22"

        if include_RTs==False:
            search_string = search_string + '-filter%3Aretweets'

        search_url = self.base_url + \
                    'search/tweets.json?q=' + search_string + \
                    '&lang=' + language + \
                    '&count=' + str(count) + \
                    '&result_type=' + result_type
        request = requests.get(search_url, auth = self.auth)
        tweets = request.json()
        ids = [tweets['statuses'][tweet]['id'] for tweet in range(len(tweets['statuses']))]
        next_max_id = min(ids) - 1
        new_search_url = search_url + '&max_id=' + str(next_max_id)

        all_results = []
        all_results.append(tweets)

        for page in range(max_pages - 1):
            request = requests.get(new_search_url, auth = self.auth)
            tweets = request.json()
            ids = [tweets['statuses'][tweet]['id'] for tweet in range(len(tweets['statuses']))]
            next_max_id = min(ids) - 1
            new_search_url = search_url + '&max_id=' + str(next_max_id)
            all_results.append(tweets)

        return all_results

    def list_features(self, search_results, feature='created_at'):
        """Creates a list of the specified feature from a set of results from the .search() method.
        Default feature is time-stamp of when each tweet was created."""
        return [search_results['statuses'][tweet][feature] for tweet in range(len(search_results['statuses']))]

    def time_per_tweet(self, one_page_search_results):
        if len(one_page_search_results['statuses']) == 0:
            return datetime.timedelta(0)
        number_tweets = len(one_page_search_results['statuses']) - 2
        create_dates = [datetime.datetime.strptime(one_page_search_results['statuses'][tweet]['created_at'],\
                                                   '%a %b %d %H:%M:%S +0000 %Y') for tweet in range(number_tweets)]
        oldest = min(create_dates)
        newest = max(create_dates)
        difference = newest - oldest
        time_per_tweet = difference / number_tweets
        return time_per_tweet

    def tweets_per_week(self, one_page_search_results):
        time_per_tweet = self.time_per_tweet(one_page_search_results)
        days_in_seconds = time_per_tweet.days * 24 * 60 * 60
        seconds = time_per_tweet.seconds
        total_seconds = days_in_seconds + seconds
        seconds_in_week = 60 * 60 * 24 * 7
        microseconds_in_week = seconds_in_week * 1000000
        if total_seconds > 0:
            return int(seconds_in_week / total_seconds)
        elif time_per_tweet.microseconds > 0:
            return int(microseconds_in_week / time_per_tweet.microseconds)

    def stripped_tweets(self, one_page_search_results):
        full_tweets = []
        mentions = []
        urls = []
        hashtags = []
        stripped_tweets = []

        for tweet in one_page_search_results['statuses']:

            # Original tweets
            full_tweet = tweet['text']
            full_tweets.append(full_tweet)

            # Mentions
            tweet_mentions = [tweet['entities']['user_mentions'][at]['screen_name'] \
                              for at in range(len(tweet['entities']['user_mentions']))]
            mentions.append(tweet_mentions)

            # URLs
            tweet_urls = [tweet['entities']['urls'][url]['url'] \
                          for url in range(len(tweet['entities']['urls']))]
            urls.append(tweet_urls)

            # Hashtags
            tweet_hashtags = [tweet['entities']['hashtags'][hashtag]['text'] \
                              for hashtag in range(len(tweet['entities']['hashtags']))]
            hashtags.append(tweet_hashtags)

            # Stripped tweet
            stripped_tweet = tweet['text']
            dissected_tweet = strip_tweeze(stripped_tweet)
            stripped_tweet = dissected_tweet.strip_ats()[2]
            dissected_tweet = strip_tweeze(stripped_tweet)
            stripped_tweet = dissected_tweet.strip_urls()[2]
            stripped_tweets.append(stripped_tweet)

        return_dict = {"full_tweets":full_tweets,
                        "mentions":mentions,
                        "urls":urls,
                        "hashtags":hashtags,
                        "stripped_tweets":stripped_tweets}

        return return_dict

# Primary class for dissecting content of individual tweets.
class strip_tweeze(object):
    """Class containing various functions to parse the contents of an individual tweet."""

    def __init__(self, tweet):
        self.tweet = tweet

    def strip_regex(self, tweet, regex):
        """Function to strip an individual tweet of any text matching the supplied regex.
        Returns the text(s) removed, count of text(s) removed, and remaining tweet minus the removed text(s).
        """

        # Extract all matches from the tweet.
        matches = re.findall(regex, tweet)

        # Count all matches
        match_count = len(matches)

        # Remove matches from tweet
        stripped_tweet = tweet
        for text in matches:
            stripped_tweet = stripped_tweet.replace(text, '')

        # Remove any double spaces left behind from URL stripping.
        stripped_tweet = re.sub('\s+', ' ', stripped_tweet).strip()

        return matches, match_count, stripped_tweet

    def strip_ats(self, tweet = None):
        """Function to find twitter accounts mentioned in an individual tweet.
        Returns the twitter handle(s), count of twitter handle(s), and tweet text minus twitter handle(s).
        """
        if tweet == None: tweet = self.tweet

        regex = r'(?<=^|(?<=[^a-zA-Z0-9-_\.]))([@][A-Za-z]+[A-Za-z0-9]+)'

        return self.strip_regex(tweet, regex)


    def strip_urls(self, tweet = None):
        """Function to find urls in an individual tweet.
        Returns the url(s), count of url(s), and tweet text minus url(s)."""

        if tweet == None: tweet = self.tweet

        # This is a fairly crude method to extract URLs. It will not identify bad links.
        # It will also miss certain non-HTTP format URLs, e.g. mailto: ftp:// etc.
        regex = r'([Hh][Tt][Tt][Pp][Ss]?[://][^\s]+)'

        return self.strip_regex(tweet, regex)

    def strip_tweeze(self, tweet = None):
        """Function to strip a tweet of all mentions and hyperlinks, and return the separated
        components in a dictionary, including meta-data counting the number of each."""

        if tweet == None: tweet = self.tweet

        at_stripped = self.strip_ats(tweet)
        ats = at_stripped[0]
        no_ats = at_stripped[1]
        stripped_tweet = at_stripped[2]

        url_stripped = self.strip_urls(stripped_tweet)
        urls = url_stripped[0]
        no_urls = url_stripped[1]
        stripped_tweet = url_stripped[2]

        return {'original_tweet':tweet,
                'mentions':ats,
                'number_mentions':no_ats,
                'urls':urls,
                'numbers_urls':no_urls,
                'stripped_tweet':stripped_tweet}
