# Tweezers
## Lightweight Python library for scraping data via the Twitter search API.
```python
from tweezers import Tweezers
```
#### Create an instance of Tweezers with API credentials

```python
# Loading Twitter auth credentials from a local JSON file. Get yours here:
# https://developer.twitter.com/en/apps/
import json
fp = os.path.join(os.getcwd(), "credentials.json")
with open(fp) as f:
    credentials = json.load(f)

t = Tweezers(api_key=credentials["api_key"], 
             api_secret_key=credentials["api_secret_key"], 
             access_token=credentials["access_token"], 
             access_token_secret=credentials["access_token_secret"]
            )
```
#### Perform a search
Searching returns an instance of a class `TweezerSearch`, which contains various data attributes returned by the Twitter API:

```python
s = t.search(search_term="bitcoin", total=1000, result_type="recent")
# All the tweet results are returned in a Pandas DataFrame:
s.results_df.head()
```
