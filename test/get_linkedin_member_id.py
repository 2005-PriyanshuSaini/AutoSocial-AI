import os
import requests
from dotenv import load_dotenv

load_dotenv()

def get_linkedin_member_id():
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    
    if not access_token:
        print("❌ LINKEDIN_ACCESS_TOKEN not found in environment")
        return
    
    print(f"✅ Token loaded: {access_token[:10]}...")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    print("🔄 Making API request to /v2/userinfo...")
    resp = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers)
    
    print(f"📊 Status Code: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        member_id = data.get("sub")
        print(f"✅ Your LinkedIn member id: {member_id}")
        print(f"✅ Your LinkedIn author URN: urn:li:person:{member_id}")
        print(f"📋 Full response: {data}") 
        return member_id
    else:
        print("❌ Failed to fetch member id. Response:")
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")

if __name__ == "__main__":
    get_linkedin_member_id()
