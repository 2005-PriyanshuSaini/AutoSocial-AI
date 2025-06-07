import os
import requests
import time
from typing import Dict
from dotenv import load_dotenv
from prompt_templates import DEFAULT_PROMPT

# Load environment variables from .env file
load_dotenv()

# Load API keys from environment variables (SECURITY FIX)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
if not OPENAI_API_KEY or not GEMINI_API_KEY or not GROQ_API_KEY:
    raise ValueError("Please set OPENAI_API_KEY, GEMINI_API_KEY, and GROQ_API_KEY in your .env file.")

# Function to call OpenAI (ChatGPT)
def askopenai(prompt: str) -> str:
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
def askgemini(prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
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
        # Parse the new response structure
        if (
            "candidates" in resp_json and
            resp_json["candidates"] and
            "content" in resp_json["candidates"][0] and
            "parts" in resp_json["candidates"][0]["content"] and
            resp_json["candidates"][0]["content"]["parts"]
        ):
            return resp_json["candidates"][0]["content"]["parts"][0].get("text", "No response")
        return f"Error: Unexpected Gemini API response: {resp_json}"
    except requests.RequestException as e:
        return f"Error: {str(e)}"

def askgroq(prompt: str) -> str:
    """
    Generate content using GroqCloud Llama-4 API.
    """
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{
            "role": "user",
            "content": prompt
        }]
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        resp_json = response.json()
        if "choices" in resp_json and resp_json["choices"]:
            return resp_json["choices"][0]["message"]["content"]
        return f"Error: Unexpected Groq Llama API response: {resp_json}"
    except Exception as e:
        return f"Error: {str(e)}"

def askall_models(prompt: str = None) -> Dict[str, str]:
    if prompt is None:
        prompt = DEFAULT_PROMPT
    models = {
        "ChatGPT": askopenai,
        "Gemini": askgemini,
        "Llama-4": askgroq
    }
    return {model: func(prompt) for model, func in models.items()}
