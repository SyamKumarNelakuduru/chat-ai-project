from dotenv import load_dotenv
import os
from google import genai

load_dotenv()

print("Has GEMINI_API_KEY?", bool(os.getenv("GEMINI_API_KEY")))

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

resp = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Say 'Gemini is working' in one line."
)

print("Response:", resp.text)