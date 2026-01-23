"""
Example client script for testing the Gemini API
"""
from google import genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize client
api_key = os.getenv('GEMINI_API_KEY')
client = genai.Client(api_key=api_key)

# Generate content
response = client.models.generate_content(
    model="models/gemini-2.5-flash",
    contents="Explain how AI works in a few words",
)

print("Response from Gemini:")
print(response.text)
