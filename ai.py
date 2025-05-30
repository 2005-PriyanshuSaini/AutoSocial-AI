import os
import requests
import time
from typing import Dict
from dotenv import load_dotenv
from mistral import generate_mistral_content

# Load environment variables from .env file
load_dotenv()

# Load API keys from environment variables (SECURITY FIX)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Function to call OpenAI (ChatGPT)
def query_openai(prompt: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}]}
    retries = 5
    for attempt in range(retries):
        try:
            time.sleep(1 + attempt)  # Increase delay with each retry
            response = requests.post(url, json=data, headers=headers, timeout=10)
            if response.status_code == 429 and attempt < retries - 1:
                # Exponential backoff for rate limit
                time.sleep(2 ** attempt)
                continue
            response.raise_for_status()
            resp_json = response.json()
            if "choices" in resp_json and resp_json["choices"]:
                return resp_json["choices"][0].get("message", {}).get("content", "No response")
            return resp_json.get("error", {}).get("message", "No response")
        except requests.RequestException as e:
            if attempt == retries - 1:
                return f"Error: {str(e)}"
            time.sleep(2 ** attempt)
    return "Error: OpenAI API failed after retries (rate limit or quota exceeded)."

# Function to call Gemini (Google AI)
def query_gemini(prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateText?key={GEMINI_API_KEY}"
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 404:
            return ("Error: Gemini API returned 404. Check your API key and access at https://makersuite.google.com/app/apikey. "
                    f"Full response: {response.text}")
        if response.status_code == 401:
            return ("Error: Gemini API returned 401 Unauthorized. Your API key may be invalid or expired. "
                    f"Full response: {response.text}")
        response.raise_for_status()
        resp_json = response.json()
        # Debug: print full response for troubleshooting
        if not ("candidates" in resp_json and resp_json["candidates"]):
            return f"Error: Unexpected Gemini API response: {resp_json}"
        return resp_json["candidates"][0].get("output", "No response")
    except requests.RequestException as e:
        return f"Error: {str(e)}"

def query_mistral(prompt: str) -> str:
    try:
        return generate_mistral_content(prompt)
    except Exception as e:
        return f"Error: {str(e)}"

def query_all_models(prompt: str) -> Dict[str, str]:
    models = {
        "ChatGPT": query_openai,
        "Gemini": query_gemini,
        "Mistral": query_mistral
    }
    return {model: func(prompt) for model, func in models.items()}
