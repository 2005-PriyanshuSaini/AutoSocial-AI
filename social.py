import os
import requests
from requests_oauthlib import OAuth1

# --- X (Twitter) Integration ---

def fetch_x_trending_topics():
    """
    Fetch trending topics from X (Twitter).
    Requires Bearer Token and Twitter API v1.1 or v2.
    """
    BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")
    if not BEARER_TOKEN:
        return ["Set X_BEARER_TOKEN in .env"]
    url = "https://api.twitter.com/1.1/trends/place.json?id=1"  # 1 = Worldwide
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data and isinstance(data, list) and "trends" in data[0]:
            return [trend["name"] for trend in data[0]["trends"][:10]]
        return ["No trending topics found"]
    except Exception as e:
        return [f"Error fetching X trends: {e}"]

def post_to_x(content):
    """
    Post content to X (Twitter) using OAuth 1.0a (user context).
    """
    CONSUMER_KEY = os.getenv("X_CONSUMER_KEY")
    CONSUMER_SECRET = os.getenv("X_CONSUMER_SECRET")
    ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
    ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")
    if not all([CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET]):
        return {"error": "Set all X OAuth 1.0a credentials in .env"}
    url = "https://api.twitter.com/2/tweets"
    auth = OAuth1(CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    data = {"text": content}
    try:
        resp = requests.post(url, auth=auth, json=data, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": f"Error posting to X (OAuth 1.0a): {e}"}

# --- LinkedIn Integration ---

def fetch_linkedin_trending_topics():
    """
    Fetch trending topics from LinkedIn.
    LinkedIn does not provide a public trending topics API.
    """
    # TODO: Implement using third-party service or scraping if needed
    return ["LinkedIn trending topics API not available"]

def post_to_linkedin(content):
    """
    Post content to LinkedIn.
    Requires LINKEDIN_ACCESS_TOKEN and LINKEDIN_ORGANIZATION_URN or user URN in .env.
    """
    ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
    ORGANIZATION_URN = os.getenv("LINKEDIN_ORGANIZATION_URN")  # e.g., "urn:li:organization:xxxx"
    AUTHOR_URN = os.getenv("LINKEDIN_AUTHOR_URN")  # e.g., "urn:li:person:xxxx"
    if not ACCESS_TOKEN or not (ORGANIZATION_URN or AUTHOR_URN):
        return {"error": "Set LINKEDIN_ACCESS_TOKEN and LINKEDIN_ORGANIZATION_URN or LINKEDIN_AUTHOR_URN in .env"}
    url = "https://api.linkedin.com/v2/ugcPosts"
    author = ORGANIZATION_URN if ORGANIZATION_URN else AUTHOR_URN
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    data = {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": content},
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": f"Error posting to LinkedIn: {e}"}
