from dotenv import load_dotenv
import os
from google import genai

# Load environment variables from .env
load_dotenv()

# Check if API key exists
print("Gemini key loaded:", bool(os.getenv("GEMINI_API_KEY")))

# Create Gemini client
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# Send a test message
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Say 'Gemini AI is working'"
)

# Print response
print("Response:", response.text)