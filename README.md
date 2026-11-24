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
