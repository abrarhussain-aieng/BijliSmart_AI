# ⚡ BijliSmart AI — Intelligent Electricity Bill Analyzer & Energy Assistant

**BijliSmart AI** is a full-stack Agentic AI web application built to help households—especially across Pakistani DISCO billing slabs—extract, validate, track, and reduce their monthly electricity consumption without relying on paid AI APIs.

🔗 **Live Demo:** [https://bijlismart-ai.onrender.com](https://bijlismart-ai.onrender.com)

---

## ✨ Key Features

- **Automated Bill Scanning & Deterministic Validation:** Upload electricity bills (`PNG`, `JPG`, `WEBP`, or `PDF`). Extracted readings, units, taxes, FPA, GST, and payable amounts pass through strict invariant checks (`validators.py`) to catch OCR anomalies, swapped readings, or negative values before persistence.
- **Multi-Provider LLM Fallback Router:** Zero single-point-of-failure inference routing across **Groq → Cerebras → Google Gemini** with automatic JSON repair and `<think>` tag stripping.
- **Resilient Cloud-First Vision OCR:** Multi-model vision extraction (**Gemini `3.8-flash` → `3.5-flash-lite` → `3.1-flash-lite` → `4-hydrogen`** with exponential retry backoff + **Groq Vision** fallback) engineered to run smoothly within a **512 MB RAM** cloud container, with optional local **RapidOCR** (`onnxruntime`) support for offline environments.
- **Agentic RAG Energy Assistant:** Powered by **LangGraph**, **ChromaDB**, and **Google `gemini-embedding-001`**, combining live user bill history, appliance wattage calculators, and Pakistani tariff knowledge to deliver grounded, hallucination-free savings recommendations.
- **Appliance Load & History Analytics:** Interactive dashboard tracking month-over-month kWh trends, effective per-unit rates (`Rs./kWh`), and appliance-level consumption breakdowns.

---

## 🏗️ System Architecture

```text
┌──────────────────────────────────────────────────────────────────────┐
│                        Frontend (HTML / CSS / JS)                    │
│     Dashboard   │   Bills Upload   │   History   │   AI Assistant    │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │ REST API (FastAPI)
┌──────────────────────────────────▼───────────────────────────────────┐
│                      Application & Validation Layer                  │
│  • File Security & MIME Checks   • Deterministic Bill Validators     │
│  • SQLAlchemy + SQLite Persistence • Effective Rate & Slab Analytics │
└──────────────┬───────────────────────────────────────┬───────────────┘
               │                                       │
┌──────────────▼───────────────────────┐ ┌─────────────▼───────────────┐
│      Cloud-First OCR & Extraction    │ │   LangGraph Agent + RAG     │
│  1. Image Downscaling (1600px JPEG)  │ │  • ChromaDB Vector Store    │
│  2. Gemini 3.8-Flash / 3.5-Flash-Lite│ │  • gemini-embedding-001     │
│  3. Groq Vision (Llama-4-Scout)      │ │  • Tariff & Appliance Docs  │
│  4. Optional Local RapidOCR (ONNX)   │ │  • Multi-Provider LLM Chain │
└──────────────────────────────────────┘ └─────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python 3.12, FastAPI, Uvicorn, Pydantic v2, SQLAlchemy |
| **LLM Routing** | Groq (`openai/gpt-oss-120b`), Cerebras (`gpt-oss-120b`), Google Gemini (`gemini-3.8-flash`) |
| **OCR & Vision** | Gemini Vision (multi-model fallback), Groq Vision (`meta-llama/llama-4-scout-17b-16e-instruct`), RapidOCR (`onnxruntime`), `pypdfium2` |
| **RAG & Agents** | LangGraph, LangChain, ChromaDB, Google Generative AI Embeddings (`gemini-embedding-001`) |
| **Frontend** | Vanilla HTML5, CSS3, JavaScript (Responsive Dashboard UI) |
| **Testing & Deploy** | Pytest, Render Web Service (512 MB Free Tier) |

---

## 📁 Project Structure

```text
BijliSmart_AI/
├── app/
│   ├── ai/
│   │   ├── embeddings.py       # Google gemini-embedding-001 wrapper
│   │   ├── mistral.py          # Groq -> Cerebras -> Gemini router & Vision OCR
│   │   └── rag.py              # ChromaDB indexing & retrieval pipeline
│   ├── api/                    # FastAPI route handlers (bills, chat, appliances)
│   ├── core/
│   │   ├── config.py           # Pydantic settings & environment configuration
│   │   └── security.py         # Upload validation & magic-byte verification
│   ├── models/                 # SQLAlchemy ORM & Pydantic schemas
│   ├── services/
│   │   └── bill_extractor.py   # OCR-to-structured-JSON extraction service
│   └── utils/
│       ├── calculations.py     # kWh, effective rate & percentage change math
│       └── validators.py       # Deterministic bill normalization & guardrails
├── data/
│   └── knowledge/              # Tariff & appliance wattage markdown docs
├── frontend/                   # Static dashboard, bills, history & assistant UI
├── tests/                      # Unit & boundary validation test suite
├── pytest.ini                  # Pytest rootpath & async configuration
├── render.yaml                 # Render infrastructure blueprint
└── requirements.txt            # Production dependencies
```

---

## 🚀 Local Setup & Running

### 1. Clone the Repository
```bash
git clone [https://github.com/abrarhussain-aieng/BijliSmart_AI.git](https://github.com/abrarhussain-aieng/BijliSmart_AI.git)
cd BijliSmart_AI
```

### 2. Create Virtual Environment & Install Dependencies
Using `uv` (recommended):
```bash
uv venv --python 3.12
uv pip install -r requirements.txt
```

Or using standard `pip`:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and add your free-tier API keys:
```env
GROQ_API_KEY=your_groq_api_key
CEREBRAS_API_KEY=your_cerebras_api_key
GEMINI_API_KEY=your_gemini_api_key

GROQ_MODEL=openai/gpt-oss-120b
CEREBRAS_MODEL=gpt-oss-120b
GEMINI_MODEL=gemini-3.8-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
OCR_USE_GEMINI_VISION_FALLBACK=true
ENABLE_LOCAL_OCR=false
```

### 4. Run Tests & Start the Local Server
```bash
python -m pytest -v
uvicorn app.main:app --reload
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

---

## ☁️ Production Deployment Guide (Render Free Tier)

### 1. Environment Variables on Render
In your Render Web Service → **Environment**, configure the following variables:
- `PYTHON_VERSION` = `3.12.7` *(ensures prebuilt wheels for `onnxruntime` and `chromadb`)*
- `GROQ_API_KEY` = your Groq API key
- `CEREBRAS_API_KEY` = your Cerebras API key
- `GEMINI_API_KEY` = your Google Gemini API key
- `GROQ_MODEL` = `openai/gpt-oss-120b`
- `CEREBRAS_MODEL` = `gpt-oss-120b`
- `GEMINI_MODEL` = `gemini-3.8-flash`
- `GEMINI_EMBEDDING_MODEL` = `gemini-embedding-001`
- `OCR_USE_GEMINI_VISION_FALLBACK` = `true`
- `ENABLE_LOCAL_OCR` = `false` *(keeps memory usage well under Render's 512 MB RAM limit)*

### 2. Build & Start Commands
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 3. Prevent Free-Tier Cold Starts (Keep-Alive Monitor)
Render's free tier spins down web services after 15 minutes of inactivity. To keep the app warm 24/7 (within Render's 750 free monthly instance hours for a single service):

1. Create a free account at [uptimerobot.com](https://uptimerobot.com) (or [cron-job.org](https://cron-job.org)).
2. Click **+ Add New Monitor** and set:
   - **Monitor Type:** `HTTP(s)`
   - **Friendly Name:** `BijliSmart AI`
   - **URL:** `https://bijlismart-ai.onrender.com/health`
   - **Monitoring Interval:** `5 minutes` (or `14 minutes` on Cron-job.org)
3. Save the monitor and verify `/health` returns `200 OK`.

---

## 🔄 Git Workflow for Updates

```bash
git add .
git commit -m "Update BijliSmart AI documentation and configuration"
git push origin main
```
