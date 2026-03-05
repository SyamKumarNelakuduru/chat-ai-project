import os
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google.cloud import bigquery
from google import genai

# ----------------------------------------------------
# Load environment variables
# ----------------------------------------------------
load_dotenv()

# ----------------------------------------------------
# Create FastAPI app
# ----------------------------------------------------
app = FastAPI()

# ----------------------------------------------------
# Allow Angular frontend to access backend
# ----------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------
# Environment variables
# ----------------------------------------------------
PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]
TABLE = f"{PROJECT_ID}.chat_app.pharmacy_employee_drug_usage"

# ----------------------------------------------------
# BigQuery client
# ----------------------------------------------------
bq_client = bigquery.Client()

# ----------------------------------------------------
# Gemini client
# ----------------------------------------------------
gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


# ----------------------------------------------------
# Request / Response models
# ----------------------------------------------------
class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str


# ----------------------------------------------------
# Helper function to run BigQuery query
# ----------------------------------------------------
def run_query(sql: str):
    print("\n📊 Running BigQuery query...")
    print(sql)

    query_job = bq_client.query(sql)
    results = [dict(row) for row in query_job.result()]

    print("📊 BigQuery Results:", results)

    return results


# ----------------------------------------------------
# Root endpoint
# ----------------------------------------------------
@app.get("/")
def root():
    return {"status": "Backend running", "open_docs": "/docs"}


# ----------------------------------------------------
# AI endpoint
# ----------------------------------------------------
@app.post("/api/ask", response_model=AskResponse)
def ask(req: AskRequest):

    print("\n====================================")
    print("🚀 BACKEND REQUEST RECEIVED")
    print("User Question:", req.question)
    print("====================================")

    question = req.question.strip()

    if not question:
        print("⚠️ Empty question received")
        return {"answer": "Please ask a question."}

    # Optional: avoid running BigQuery for greetings (saves time/cost)
    smalltalk = {"hi", "hello", "hey", "hii", "good morning", "good afternoon", "good evening"}
    if question.lower() in smalltalk:
        return {
            "answer": "Hi! Ask me something about the pharmacy dataset—like top drug classes, providers, or age groups."
        }

    # ------------------------------------------------
    # Run BigQuery queries
    # ------------------------------------------------
    print("📊 Querying BigQuery for top drugs...")

    top_drugs = run_query(f"""
        SELECT drug_name, COUNT(*) AS usage_count
        FROM `{TABLE}`
        GROUP BY drug_name
        ORDER BY usage_count DESC
        LIMIT 5
    """)

    print("📊 Querying BigQuery for top drug classes...")

    top_classes = run_query(f"""
        SELECT drug_class, COUNT(*) AS usage_count
        FROM `{TABLE}`
        GROUP BY drug_class
        ORDER BY usage_count DESC
        LIMIT 5
    """)

    print("📊 Querying BigQuery for provider types...")

    by_provider = run_query(f"""
        SELECT prescribing_provider_type, COUNT(*) AS usage_count
        FROM `{TABLE}`
        GROUP BY prescribing_provider_type
        ORDER BY usage_count DESC
        LIMIT 5
    """)

    print("📊 Querying BigQuery for age group vs provider...")

    age_by_provider = run_query(f"""
        SELECT age_group, prescribing_provider_type, COUNT(*) AS usage_count
        FROM `{TABLE}`
        GROUP BY age_group, prescribing_provider_type
        ORDER BY prescribing_provider_type, usage_count DESC
        LIMIT 200
    """)

    # ------------------------------------------------
    # Prepare AI prompt
    # ------------------------------------------------
    context = {
        "top_drugs": top_drugs,
        "top_classes": top_classes,
        "by_provider": by_provider,
        "age_by_provider": age_by_provider,
    }

    print("\n🤖 Sending data to Gemini AI...")
    print("Context sent to Gemini:", context)

    prompt = f"""
You are a healthcare data analyst.

User question:
{question}

Dataset summary (from BigQuery):
{context}

Rules:
- Use ONLY the dataset summary above.
- If the question cannot be answered from the summary, say what is missing.
- Keep the answer clear and short (3-6 lines).
"""

    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    answer = response.text

    print("\n🤖 Gemini AI response:")
    print(answer)

    print("\n✅ Sending response back to frontend")
    print("====================================\n")

    return {"answer": answer}