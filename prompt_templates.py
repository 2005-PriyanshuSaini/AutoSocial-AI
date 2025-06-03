# Default prompt for content generation
DEFAULT_PROMPT = "Write a creative tweet announcing a new AI app that generates social media content automatically."

# Prompt for summarizing code changes into a social post
SUMMARY_PROMPT_TEMPLATE = """
You are an expert technical writer and developer advocate.

Given the following code changes:
{diff_summary}

Write a concise, engaging, and professional LinkedIn/Twitter post summarizing what was changed and how it positively impacts the project. 
Highlight improvements, new features, or bug fixes, and use a friendly, motivating tone suitable for a public audience and avoid the use of buzz words.
"""
