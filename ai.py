import os
import requests
import time
from typing import Dict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load API keys from environment variables (SECURITY FIX)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Function to call OpenAI (ChatGPT)
def query_openai(prompt: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": prompt}]}
    try:
        time.sleep(1)  # Add delay to avoid rate limit
        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        resp_json = response.json()
        if "choices" in resp_json and resp_json["choices"]:
            return resp_json["choices"][0].get("message", {}).get("content", "No response")
        return resp_json.get("error", {}).get("message", "No response")
    except requests.RequestException as e:
        return f"Error: {str(e)}"

# Function to call Claude (Anthropic)
def query_claude(prompt: str) -> str:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "content-type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    data = {
        "model": "claude-3-opus-20240229",  # Use a valid model name
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        resp_json = response.json()
        # Claude's response may be a list of content blocks
        if "content" in resp_json:
            if isinstance(resp_json["content"], list):
                return " ".join([c.get("text", "") for c in resp_json["content"]])
            return resp_json["content"]
        return resp_json.get("error", {}).get("message", "No response")
    except requests.RequestException as e:
        return f"Error: {str(e)}"

# Function to call Gemini (Google AI)
def query_gemini(prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateText?key={GEMINI_API_KEY}"
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        resp_json = response.json()
        if "candidates" in resp_json and resp_json["candidates"]:
            return resp_json["candidates"][0].get("output", "No response")
        return resp_json.get("error", {}).get("message", "No response")
    except requests.RequestException as e:
        return f"Error: {str(e)}"

# Function to query all AI models
def query_all_models(prompt: str) -> Dict[str, str]:
    models = {
        "ChatGPT": query_openai,
        "Claude": query_claude,
        "Gemini": query_gemini
    }

    return {model: func(prompt) for model, func in models.items()}
