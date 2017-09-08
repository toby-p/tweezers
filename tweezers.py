#!/usr/bin/env python

# Dependencies
import requests
import json
from requests_oauthlib import OAuth1
from collections import OrderedDict
import re
import datetime
from math import nan
import pandas as pd
from textblob import TextBlob # For sentiment analysis
from numpy import mean

class tweezer_auth(object):
    """Primary object for authenticating a twitter API instance ."""
    
    # Class attributes
    # Base url for all requests
    base_url = 'https://api.twitter.com/1.1/'
    
    # Instance attributes
    def __init__(self, consumer_key, consumer_secret, access_token, access_token_secret):
        
        # Twitter auth variables
        self.consumer_key = consumer_key
        self.__consumer_secret = consumer_secret
        self.access_token = access_token
        self.__access_token_secret = access_token_secret

        # Auth for all requests
        self.auth = OAuth1(self.consumer_key,
                           self.__consumer_secret,
                           self.access_token,
                           self.__access_token_secret)

    def verify(self):
        verify_url = self.base_url + \
                    'account/verify_credentials.json'
        self.status_code = requests.get(verify_url, auth = self.auth).status_code
        if self.status_code == 200:
            return 'Congratulations! Your credentials are valid.'
        else:
            return 'Oops, something wrong with your credentials - HTTP response error code %d.' % self.status_code

    def __str__(self):
        return """Twitter API instance created with:
        \t public consumer key = %s
        \t public access token = %s""" % (self.consumer_key, self.access_token)

class NoResults(Exception):
    pass
    
class search(object):
    """Class to perform a twitter search on given search term(s). Parameters are:
    
        * total: the desired number of tweets to return. Note that it may not be possible to
          return the full number requested, either due to a lack of available tweets meeting
          the criteria, or rate-limiting by the twitter API 
          (see https://dev.twitter.com/rest/public/rate-limiting).
        * language / result_type: as per the twitter documentation at 
          https://dev.twitter.com/rest/reference/get/search/tweets
        * search_type: Valid options are 'words' (default) and 'phrase'. If 'phrase' is used then
          multiple search words will be searched as one phrase, and will only be returned in the
          results if all words are found in the given order in a tweet.
        * include_RTs: whether to include retweets in the search results (default False).
        
        Attributes:
            polarity_score          Float between -1.0 and 1.0 which represents the average 
                                    sentiment of the tweets returned by the search.
            subjectivity_score      Float between 0.0 and 1.0 representing the average objectivity
                                    of the tweets returned by the search, where 0 is very 
                                    objective and 1 is very subjective.
            
        """

    def __init__(self, tweezer_auth, search_term, \
                 language = 'en', total = 100, result_type = 'recent',\
                 search_type = 'words', include_RTs = False):
        
        # Save the search terms as variables
        self.search_term = search_term
        self.total = total
        self.result_type = result_type
        self.language = language
        self.search_type = search_type
        self.include_RTs = include_RTs
        
        # Encode the search term for URL use
        self.search_string = self.__percent_encode(search_term)
        if search_type == 'phrase':
            if self.search_string[0:2] != "%22":
                self.search_string = "%22" + self.search_string +"%22"
        
        # Add in the filter for no RTs if applicable
        if include_RTs==False:
            self.search_string = self.search_string + '-filter%3Aretweets'
        
        # Initialise variables
        self.results_json = [] # The full json tweets.
        self.tweets = [] # List of just the original tweet text.
        self.stripped_tweets = [] # List of tweet texts with URLS, @ and # symbol stripped.
        self.ids = [] # Unique tweet ids.
        self.completed_in = 0.0 # Total length of time taken to complete all search iterations.
        self.result_count = 0 # Number of tweets that have actually been collected.
        self.urls = []  # URLs contained in each tweet.
        self.ats = []  # Users mentioned in each tweet.
        self.hashtags = [] # Hashtags used in each tweet.
        self.polarity = [] # Sentiment analysis of tweet polarity
        self.subjectivity = [] # Sentiment analysis of tweet subjectivity
        
        
        # This loop will iterate through twitter searches, using a new max_id
        # value each iteration to collect the set of next oldest tweets. The loop 
        # will continue until the number of results collected exceeds the 
        # requested total.
        while self.result_count < total:
            
            # Generate the full search URL.
            self.search_url = tweezer_auth.base_url + \
                        'search/tweets.json?q=' + self.search_string + \
                        '&lang=' + language + \
                        '&count=100&result_type=' + result_type
            if self.result_count > 0:
                self.search_url = self.search_url + '&max_id=' + str(next_max_id)
            
            # Make the GET request.
            results = requests.get(self.search_url, auth = tweezer_auth.auth)
            
            # Request was successful
            if results.status_code == 200:
                # Raise an error if no results at all returned by the search.
                if len(results.json()['statuses']) == 0 and self.result_count == 0:
                    raise NoResults("""
                    The search criteria did not return any results, please try again. 
                    If this error persists you likely need to broaden your 
                    search criteria.""")

                # If results are returned add them to the main results variable
                elif len(results.json()["statuses"]) > 0:

                    # Get the full tweet json returned by this iteration of the search.
                    search_tweets = results.json()['statuses']

                    # Add the tweets to the main results variable.
                    self.results_json += search_tweets

                    # Update the count of tweets collected.
                    self.result_count = len(self.results_json)

                    # Set the max_id for the next iteration
                    self.ids = [self.results_json[tweet]['id'] for tweet in range(self.result_count)]
                    next_max_id = min(self.ids) - 1

                    # Add the time taken to the total .completed_in variable.
                    self.completed_in += float(results.json()['search_metadata']['completed_in'])

                # If no more results are returned, just end the loop here.
                elif len(results.json()["statuses"]) == 0:
                    break
            
            # Request was not successful
            else:
                # Print the status code
                print(results)
                if results.status_code == 429:
                    print("Twitter API rate limit exceeded.")
                break
        
        # Trim the results to the count limit.
        if self.result_count > self.total:
            self.results_json = self.results_json[:total]
            self.result_count = len(self.results_json)
            self.ids = self.ids[:total]
        
        print("%s tweets requested, %s tweets returned" % (self.total, self.result_count))
        
        # Add features from each tweet to the variables.
        for tweet in range(self.result_count):
            tweet = self.results_json[tweet]['text']
            self.tweets.append(tweet)
            tweet_stripped = self.__stripped_tweet(tweet)
            self.stripped_tweets.append(tweet_stripped)
            self.urls.append(self.__strip_urls(tweet)[0])
            self.ats.append(self.__strip_ats(tweet)[0])
            self.hashtags.append(self.__strip_hashtags(tweet)[0])
            
            # Sentiment analysis
            tweet_blob = TextBlob(tweet_stripped)
            self.polarity.append(tweet_blob.sentiment.polarity)
            self.subjectivity.append(tweet_blob.sentiment.subjectivity)
        
        # Create .users variable with list of users who authored each tweet in the results.
        self.__parse_users()
        
        # Create .variables with lists of key features from the tweets.
        self.retweet_count = self.list_tweet_feature(feature = "retweet_count")
        self.favorite_count = self.list_tweet_feature(feature = "favorite_count")
        
        # Add the .time_per_tweet and .tweets_per_week variables.
        self.__time_per_tweet()
        self.__tweets_per_week()
        
        # Generate lists of the available features in the tweets.
        self.tweet_features = list(self.results_json[0].keys())
        self.entities = list(self.results_json[0]['entities'].keys())
        self.user_features = list(self.results_json[0]['user'].keys())
        
        # Create the sentiment analysis scores
        self.__polarity_score()
        self.__subjectivity_score()
    
    def __str__(self):
        return """Twitter search instance created with arguments:
        \t search_term = %s
        \t total = %s""" % (self.search_term, str(self.total))
    
    def __create_dates(self):
        """Function to add the .create_dates variable which gives a list of the 
           create dates of the tweets returned by the search."""
        
        self.create_dates = self.list_tweet_feature(feature = "created_at")
        
    def __time_per_tweet(self):
        """Function to add the .time_per_tweet variable which gives a datetime.timedelta 
        object representing the average amount of time elapsing between each tweet 
        returned by the search."""
        
        if self.result_count == 0:
            self.time_per_tweet = nan
        
        self.__create_dates()

        formatted_create_dates = [datetime.datetime.strptime(create_date, '%a %b %d %H:%M:%S +0000 %Y') for \
                                  create_date in self.create_dates]
        oldest = min(formatted_create_dates)
        newest = max(formatted_create_dates)
        difference = newest - oldest
        self.time_per_tweet = difference / self.result_count
    
    def __tweets_per_week(self):
        """Function to add the .tweets_per_week variable which gives a rough estimate 
        of the number of tweets about the search term per week."""
        self.tweets_per_week = nan
        days_in_seconds = self.time_per_tweet.days * 24 * 60 * 60
        seconds = self.time_per_tweet.seconds
        total_seconds = days_in_seconds + seconds
        seconds_in_week = 60 * 60 * 24 * 7
        microseconds_in_week = seconds_in_week * 1000000
        if total_seconds > 0:
            self.tweets_per_week = int(seconds_in_week / total_seconds)
        elif time_per_tweet.microseconds > 0:
            self.tweets_per_week = int(microseconds_in_week / time_per_tweet.microseconds)
    
    def __parse_users(self):
        """Creates a variable .users which returns a list of the users who authored
        each tweet in the results. Will contain duplicates if users created more then
        one tweet returned by the search."""
        self.users = [self.results_json[status]["user"]["screen_name"] for status in range(self.result_count)]    
        
    def __percent_encode(self, string):
        """Function to take a raw input string and URL encodes it."""

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
    
    def list_tweet_feature(self, feature = 'created_at'):
        """Generates a list of the specified feature from the search results.
        Default feature is time-stamp of when each tweet was created."""
        
        return [self.results_json[tweet][feature] for tweet in range(self.result_count)]

    
    # The below __strip_* functions are hidden functions used to carry 
    # out the text processing of individual tweets.
    
    def __strip_regex(self, tweet, regex):
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

        # Remove any double spaces left behind from text stripping.
        stripped_tweet = re.sub('\s+', ' ', stripped_tweet).strip()

        return matches, match_count, stripped_tweet
    
    def __strip_urls(self, tweet):
        """Function to find urls in an individual tweet.
        Returns the url(s), count of url(s), and tweet text minus url(s)."""

        # This is a fairly crude method to extract URLs. It will not identify bad links.
        # It will also miss certain non-HTTP format URLs, e.g. mailto: ftp:// etc.
        regex = r'([Hh][Tt][Tt][Pp][Ss]?[://][^\s]+)'

        return self.__strip_regex(tweet, regex)

    def __strip_ats(self, tweet):
        """Function to find twitter accounts mentioned in an individual tweet.
        Returns the twitter handle(s), count of twitter handle(s), and tweet text minus twitter handle(s).
        """
        
        regex = r'(?<=^|(?<=[^a-zA-Z0-9-_\.]))([@][A-Za-z]+[A-Za-z0-9]+)'

        return self.__strip_regex(tweet, regex)
    
    def __strip_hashtags(self, tweet):
        """Function to find hashtags in an individual tweet.
        Returns the hashtag(s), count of hashtag(s), and tweet text minus hashtag(s).
        """
        
        regex = r"#(\w+)"

        return self.__strip_regex(tweet, regex)
    
    def __stripped_tweet(self, tweet):
        """Function to strip a tweet's text of @ and # symbols, and any urls."""
        stripped_tweet = tweet.replace("#", "")
        stripped_tweet = stripped_tweet.replace("@", "")
        return self.__strip_urls(stripped_tweet)[2]
    
    def pandas_df(self, sentiments = False):
        """Function to generate a full Pandas dataframe containing the tweets
        and their component parts for analysis.
        """
        pandas_df = pd.DataFrame({"tweet":self.tweets,
                                 "stripped_tweet":self.stripped_tweets,
                                 "id":self.ids,
                                 "urls":self.urls,
                                 "hashtags":self.hashtags,
                                 "ats":self.ats,
                                 "created_at":self.create_dates,
                                 "user":self.users,
                                 "favorite_count":self.favorite_count,
                                 "retweet_count":self.retweet_count,
                                 "subjectivity":self.subjectivity,
                                 "polarity":self.polarity})
        
        return pandas_df
    
    def __list_of_lists_to_df(self, thing, list_of_lists, return_type):
        """Function used by the *_data methods to convert lists of lists
        to Pandas dataframes/json."""
        
        # Create a list of all items contained in the list of lists.
        # Will contain duplicates.
        long_list = []
        for list_of_list in list_of_lists:
            for item in list_of_list:
                long_list.append(item)
        
        # Convert the long list to a DataFrame.
        df = pd.DataFrame(long_list)
        
        # Summarise the long list DataFrame by value_counts.
        count_df = pd.DataFrame(df.loc[:,0].value_counts())
        count_df.reset_index(level = 0, inplace = True)
        count_df.rename(columns = {'index':thing, 0:'count'}, inplace=True)
        
        if return_type == "df":
            return count_df
        elif return_type == "json":
            return count_df.to_json()
    
    def urls_df(self, return_type = "df"):
        """Function to return either Pandas dataframe or json file of all URLs
        returned by the search, with the number of times each url features in the 
        tweets returned by the search.
                
        Parameters:
        * return_type: valid options are 'json' or 'df'
        
        """
        return self.__list_of_lists_to_df(thing = "url", 
                                          list_of_lists = self.urls, 
                                          return_type = return_type)
    
    def mentioned_df(self, return_type = "df"):
        """Function to return either Pandas dataframe or json file of all twitter
        users who were mentioned in the tweets returned by the search, with the 
        number of times each user was mentioned.
                
        Parameters:
        * return_type: valid options are 'json' or 'df'
        
        """
        return self.__list_of_lists_to_df(thing = "mentions", 
                                          list_of_lists = self.ats, 
                                          return_type = return_type)
    
    def users_df(self, return_type = "df"):
        """Function to return either Pandas dataframe or json file with a list of all 
        users who authored tweets returned by the search and the count of their tweets.
        
        Parameters:
        * return_type: valid options are 'json' or 'df'
        """
        return self.__list_of_lists_to_df(thing = "users", 
                                          list_of_lists = [self.users], 
                                          return_type = return_type)
    
    def hashtags_df(self, return_type = "df"):
        """Function to return either Pandas dataframe or json file with a list of all 
        hashtags in the tweets returned by the search and the count of times used.
        
        Parameters:
        * return_type: valid options are 'json' or 'df'
        """
        return self.__list_of_lists_to_df(thing = "hashtags", 
                                          list_of_lists = [self.hashtags], 
                                          return_type = return_type)
    
    # Sentiment analysis
    def __polarity_score(self):
        self.polarity_score = mean(self.polarity)
    
    def __subjectivity_score(self):
        self.subjectivity_score = mean(self.subjectivity)