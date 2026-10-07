# ⚡ BijliSmart AI

AI-powered electricity bill intelligence for Pakistani consumers. Upload a bill (image or PDF), track history, estimate appliance usage and ask a bill-aware AI assistant.

## Problem
Electricity bills are hard to read, bills spike without clear reasons, and generic advice does not reflect a household's real data.

## Solution
BijliSmart AI extracts the bill with Mistral OCR, validates it, stores monthly history, compares months, estimates appliance consumption from user-entered wattage and hours, retrieves tariff knowledge with RAG, and answers questions through a LangGraph agent that only uses the user's own data.

## Features
- Bill upload (PNG, JPG, JPEG, WEBP, PDF) with OCR extraction and numeric validation
- Bill history, trends and current vs previous vs average comparison
- Appliance estimator: `monthly_kwh = (watts / 1000) × quantity × hours/day × days`
- Rule-based saving recommendations with estimated kWh and cost
- Bill-aware AI assistant (RAG + agent tools), including "what if I reduce AC by 2 hours" scenarios
- Clear labels: User Bill Data / Retrieved Data / Calculated Estimate / AI Recommendation

## Architecture
```
Browser (HTML/CSS/JS) -> FastAPI -> LangGraph workflow -> services / tools -> SQLAlchemy DB
                                          |-> Mistral (OCR, chat) and Mistral embeddings -> ChromaDB (RAG)
```
Layers: `api` (routes) · `services` (business logic) · `ai` (Mistral, embeddings, RAG, tools, prompts) · `agents` (LangGraph) · `database` · `utils` (calculations, validators).

## Technology stack
Python 3.12, FastAPI, Uvicorn, Pydantic, SQLAlchemy (SQLite locally, PostgreSQL-compatible), Mistral API, Mistral embeddings, LangChain, ChromaDB, LangGraph, vanilla HTML/CSS/JS with Chart.js.

## Agentic AI / LangGraph workflow
One graph, three modes (`app/agents/graph.py`):
```
upload : extract_bill -> validate_bill
analyze: plan -> analyze_bill -> analyze_history -> analyze_consumption -> retrieve_tariff
              -> analyze_appliances -> generate_recommendations
chat   : plan -> (only the nodes the question needs) -> assistant_response
```
The `plan` node asks Mistral which nodes a question needs (with a keyword fallback). Conditional edges route to the next required node, so "Why did my bill increase?" runs bill, history, consumption and tariff nodes, while "How can I reduce my bill?" runs appliance and recommendation nodes. A failing node records an error and the workflow continues. Tools are in `app/ai/tools.py`: `get_current_bill`, `get_bill_history`, `compare_previous_bill`, `calculate_appliance_usage`, `calculate_estimated_savings`, `search_tariff_knowledge`, `analyze_consumption`.

## RAG architecture
Documents in `data/knowledge_base/` (sub-folder = category) -> load -> clean -> chunk (900 / 150 overlap) -> Mistral embeddings -> ChromaDB -> retriever -> Mistral answer. The index builds on first use or with `python -m app.ai.rag`.

**Tariff documents are not bundled.** No rates are invented. Download the official NEPRA / FESCO tariff documents and place the PDFs in `data/knowledge_base/` (for example in new `tariff/` and `fesco/` folders), then rebuild the index. Without them the assistant says tariff data was not found.

## Mistral integration
`app/ai/mistral.py` wraps the official SDK (OCR + chat). Model names are set by environment variables (`MISTRAL_CHAT_MODEL`, `MISTRAL_EMBEDDING_MODEL`, `MISTRAL_OCR_MODEL`). Extraction sits behind the `BillExtractor` interface in `app/services/bill_extractor.py`, so the OCR provider is replaceable.

## Folder structure
```
app/            api, core, models, schemas, services, ai, agents, database, utils
frontend/       index.html (dashboard), bills, history, appliances, assistant + css/js
data/knowledge_base/   RAG documents
tests/          unit tests
```

## Environment variables
| Variable | Where it comes from |
|---|---|
| `MISTRAL_API_KEY` | https://console.mistral.ai -> API Keys |
| `DATABASE_URL` | Empty = local SQLite. For PostgreSQL use your provider's connection string (Render: Internal Database URL) |
| `CHROMA_PERSIST_DIRECTORY` | Empty = `./data/chroma` |

Optional: `MISTRAL_CHAT_MODEL`, `MISTRAL_EMBEDDING_MODEL`, `MISTRAL_OCR_MODEL`, `MAX_UPLOAD_MB`.

## Local development (Windows PowerShell)
```powershell
cd C:\Projects\bijliwise-ai
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env                      # paste MISTRAL_API_KEY
python -m app.ai.rag              # build the RAG knowledge base
uvicorn app.main:app --reload --port 8000
```
Open http://localhost:8000. API docs: http://localhost:8000/docs

Test:
```powershell
Invoke-RestMethod http://localhost:8000/health
curl.exe -F "file=@C:\path\to\bill.png" http://localhost:8000/api/bills/upload
python -m pytest -q
```
If script activation is blocked: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.

## API
| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/api/bills/upload` | Upload + extract + validate + store a bill |
| GET | `/api/bills`, `/api/bills/{id}` | List bills / bill with analysis and recommendations |
| POST | `/api/bills/{id}/analyze` | Run the LangGraph analysis |
| GET | `/api/history`, `/api/history/summary` | Monthly history / comparison |
| POST, GET, DELETE | `/api/appliances` | Add, list (with estimates), remove |
| POST | `/api/assistant/chat` | Bill-aware chat |
| POST | `/api/rag/search` | Search the knowledge base |

A bill for a month that already exists replaces the stored one.

## Deploy to Render (no Docker)
```powershell
git init
git add .
git commit -m "BijliWise AI"
git branch -M main
git remote add origin https://github.com/<your-username>/bijliwise-ai.git
git push -u origin main
```
In Render: New -> Blueprint -> select the repo (uses `render.yaml`) -> set `MISTRAL_API_KEY` (and `DATABASE_URL` for PostgreSQL). Free-tier disks are ephemeral: use Render PostgreSQL for persistent bills, and the knowledge-base index rebuilds automatically on first search.

## Screenshots
Add screenshots here: `docs/dashboard.png`, `docs/assistant.png`.

## Future improvements
User accounts, more DISCOs, time-of-use peak analysis, persistent vector storage, export reports.
