import os
from typing import Any
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
# CORS (allow your Angular dev server)
# NOTE: If your Angular port changes, either add it here
# or keep allow_origin_regex for localhost ports.
# ----------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_origin_regex=r"^http:\/\/localhost:\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------
# Environment variables
# ----------------------------------------------------
PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]
DATASET = os.environ.get("BQ_DATASET", "chat_app")
TABLE_NAME = os.environ.get("BQ_TABLE", "pharmacy_employee_drug_usage")

# Fully-qualified BigQuery table ID (no backticks)
FULL_TABLE_ID = f"{PROJECT_ID}.{DATASET}.{TABLE_NAME}"
# Backticked table ID for BigQuery SQL
ALLOWED_TABLE = f"`{FULL_TABLE_ID}`"

# ----------------------------------------------------
# BigQuery client (uses GOOGLE_APPLICATION_CREDENTIALS from env)
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
# Helper: run BigQuery SQL and return rows as list[dict]
# ----------------------------------------------------
def run_query(sql: str) -> list[dict[str, Any]]:
    print("\n📊 Running BigQuery query...")
    print(sql)

    query_job = bq_client.query(sql)
    results = [dict(row) for row in query_job.result()]

    print("📊 BigQuery Results (first rows):", results[:10])
    return results


# ----------------------------------------------------
# Helper: validate Gemini-generated SQL for safety
# ----------------------------------------------------
def validate_sql(sql: str, allowed_table: str) -> str:
    s = (sql or "").strip()

    # If Gemini returns markdown fences, strip them
    if s.startswith("```"):
        s = s.strip().strip("`").strip()
        if s.lower().startswith("sql"):
            s = s[3:].strip()

    upper = s.upper()

    # Only SELECT allowed
    if not upper.startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed.")

    # Must reference our allowed table
    if allowed_table not in s:
        raise ValueError(f"Query must use the allowed table only: {allowed_table}")

    # Block dangerous keywords (extra safety)
    blocked = ["DELETE", "UPDATE", "INSERT", "DROP", "CREATE", "ALTER", "MERGE", "TRUNCATE"]
    if any(word in upper for word in blocked):
        raise ValueError("Unsafe SQL detected (non-SELECT operation).")

    # Require LIMIT to avoid huge scans
    if "LIMIT" not in upper:
        raise ValueError("Query must include LIMIT (e.g., LIMIT 50).")

    return s


# ----------------------------------------------------
# Helper: Ask Gemini to generate SQL for the question
# ----------------------------------------------------
def generate_sql_with_gemini(question: str, allowed_table: str) -> str:
    prompt = f"""
You are a BigQuery SQL generator.

Rules (MUST follow):
- Output ONLY SQL (no markdown, no explanation).
- Use ONLY this table: {allowed_table}
- Only SELECT queries (no DML/DDL).
- Always include LIMIT 50 (or smaller).
- Use these columns if needed:
  employee_id, drug_name, drug_class, prescribing_provider_type, age_group

User question:
{question}
""".strip()

    resp = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return (resp.text or "").strip()


# ----------------------------------------------------
# Helper: Ask Gemini to explain query results
# ----------------------------------------------------
def explain_results_with_gemini(question: str, sql: str, rows: list[dict[str, Any]]) -> str:
    # Keep prompt small: send only first 50 rows to Gemini
    rows_preview = rows[:50]

    prompt = f"""
You are a healthcare data analyst.

User question:
{question}

SQL executed:
{sql}

Query results (JSON, up to 50 rows):
{rows_preview}

Answer clearly and briefly (3-6 lines).
If results are empty, say: "No matching data found in the table."
""".strip()

    resp = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return (resp.text or "").strip()


# ----------------------------------------------------
# Root endpoint
# ----------------------------------------------------
@app.get("/")
def root():
    return {"status": "Backend running", "open_docs": "/docs", "table": FULL_TABLE_ID}


# ----------------------------------------------------
# AI endpoint (Gemini -> SQL -> BigQuery -> Gemini explanation)
# ----------------------------------------------------
@app.post("/api/ask", response_model=AskResponse)
def ask(req: AskRequest):
    print("\n====================================")
    print("🚀 BACKEND REQUEST RECEIVED")
    print("User Question:", req.question)
    print("====================================")

    question = (req.question or "").strip()
    if not question:
        return {"answer": "Please ask a question."}

    # Optional: small talk without querying BigQuery
    smalltalk = {"hi", "hello", "hey", "hii", "good morning", "good afternoon", "good evening"}
    if question.lower() in smalltalk:
        return {"answer": "Hi! Ask me something about the pharmacy dataset (drugs, classes, providers, age groups)."}

    # 1) Gemini generates SQL
    print("🧠 Generating SQL with Gemini...")
    sql_raw = generate_sql_with_gemini(question, ALLOWED_TABLE)
    print("🧠 Raw SQL from Gemini:\n", sql_raw)

    # 2) Validate SQL (safety)
    try:
        sql = validate_sql(sql_raw, ALLOWED_TABLE)
    except Exception as e:
        print("❌ SQL validation failed:", e)
        return {
            "answer": f"Sorry, I couldn't generate a safe SQL query for that question. Reason: {e}"
        }

    print("✅ Final SQL to run:\n", sql)

    # 3) Run BigQuery (ONE query per question)
    try:
        rows = run_query(sql)
    except Exception as e:
        print("❌ BigQuery execution failed:", e)
        return {"answer": f"BigQuery error while running the generated SQL: {e}"}

    # 4) Gemini explains results
    print("🤖 Explaining results with Gemini...")
    try:
        answer = explain_results_with_gemini(question, sql, rows)
    except Exception as e:
        print("❌ Gemini explanation failed:", e)
        # Fallback: return raw rows preview
        return {"answer": f"SQL ran successfully but Gemini explanation failed: {e}\n\nRows: {rows[:10]}"}

    print("✅ Sending response back to frontend")
    print("====================================\n")
    return {"answer": answer}