import os
import requests
import urllib.parse
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET") 
REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI") 

SCOPE = "openid profile email w_member_social"

def get_authorization_url():
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "state": "random_string_123" 
    }
    url = "https://www.linkedin.com/oauth/v2/authorization?" + urllib.parse.urlencode(params)
    return url

def exchange_code_for_token(code):
    url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.post(url, data=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

def get_member_id(access_token):
    """Get member ID using the new token"""
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers)
    
    if resp.status_code == 200:
        data = resp.json()
        member_id = data.get("sub")
        print(f"✅ Your LinkedIn member ID: {member_id}")
        print(f"✅ Your LinkedIn author URN: urn:li:person:{member_id}")
        return member_id
    else:
        print(f"❌ Failed to get member ID: {resp.status_code}")
        print(resp.text)
        return None

if __name__ == "__main__":
    print("Step 1: Go to this URL in your browser and authorize the app:")
    print(get_authorization_url())
    print("\nStep 2: After authorizing, you will be redirected to your redirect_uri with a code parameter.")
    code = input("Paste the 'code' parameter from the URL here: ").strip()
    
    print("Step 3: Exchanging code for access token...")
    try:
        token_response = exchange_code_for_token(code)
        access_token = token_response.get("access_token")
        
        print("✅ Access Token Response:")
        print(token_response)
        print(f"\n✅ Access Token: {access_token}")
        
        # Step 4: Get member ID immediately
        print("\nStep 4: Getting your member ID...")
        member_id = get_member_id(access_token)
        
        print(f"\n📝 Add these to your .env file:")
        print(f"LINKEDIN_ACCESS_TOKEN={access_token}")
        print(f"LINKEDIN_MEMBER_ID={member_id}")
        
    except Exception as e:
        print("❌ Error exchanging code for token:", e)
