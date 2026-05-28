# 📊 BizInsight AI

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32%2B-FF4B4B.svg)](https://streamlit.io)
[![Tests](https://img.shields.io/badge/tests-56%20passed-brightgreen.svg)](#-testing)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

BizInsight AI is an **AI-powered customer feedback analytics platform** that helps businesses understand customer sentiment, detect emerging risks, cluster complaints, and ask AI-powered questions about review data — all from a single dashboard.

> **What makes it different?** Most analytics tools are *reactive* — you notice problems only after manually inspecting charts. BizInsight AI is *proactive*: it **automatically detects negative sentiment spikes, identifies recurring complaint keywords, and assigns a risk level** so you catch problems early.

---

## 🚀 Features

| Feature | Description |
|---------|-------------|
| 📂 **CSV Upload** | Upload customer reviews and auto-score sentiment |
| 📊 **Dashboard** | Satisfaction trends, sentiment distribution, top keywords, pie charts |
| ⚠️ **Trend Alert & Risk Detection** | Automatic spike detection, risk scoring (High/Medium/Low), recurring complaint keywords |
| 🔍 **Smart Complaint Clustering** | Groups negative reviews into categories using BERTopic + HDBSCAN |
| 🤖 **AI Business Assistant** | Ask natural language questions about your reviews |
| 🧠 **RAG Chatbot** | Conversational AI grounded in your actual review data (FastAPI + ChromaDB) |
| ⬇️ **CSV Export** | Download processed feedback data |

---

## ⚠️ Trend Alert & Risk Detection (New Feature)

The alerts module makes BizInsight AI **proactive** by automatically flagging problems before they escalate.

### How it works

1. **Time-windowed analysis** — Compares the last 7 days of reviews against the prior 7-day baseline.
2. **Negative sentiment tracking** — Calculates the percentage of reviews with `sentiment < 0`.
3. **Spike detection** — Flags a spike when the negative % jumps by ≥ 15 points vs baseline.
4. **Risk scoring** — Assigns a risk level based on thresholds:

   | Level | Condition |
   |-------|-----------|
   | 🟢 Low | < 40% negative AND < 15% delta |
   | 🟡 Medium | ≥ 40% negative OR ≥ 15% delta |
   | 🔴 High | ≥ 60% negative OR ≥ 30% delta |

5. **Risk keywords** — Extracts top recurring complaint terms using TF-IDF on negative reviews.
6. **Insufficient data warning** — Warns when < 5 reviews exist in the recent window.

### What you see in the dashboard

- **Risk banner** — Color-coded alert (green/yellow/red) with actionable message
- **Metric cards** — Risk score, recent negative %, review count, spike indicator
- **Keyword badges** — Top 8 risk keywords highlighted for quick scanning
- **Methodology expander** — Full breakdown of how the score is calculated

---

## 🔍 Smart Complaint Clustering

Automatically groups negative reviews into meaningful categories using unsupervised ML:

1. **Embedding** → Sentence-Transformer (`all-mpnet-base-v2`)
2. **Dimensionality reduction** → UMAP (5 components, cosine distance)
3. **Clustering** → HDBSCAN (density-based, auto noise detection)
4. **Topic extraction** → BERTopic with c-TF-IDF
5. **Category mapping** → Maps to 11 predefined categories (Payment, Delivery, Technical, etc.) or generates dynamic names

---

## 🧠 RAG Chatbot

A conversational AI that answers business questions grounded **only** in your uploaded reviews.

- **Vector Store** — ChromaDB with `all-MiniLM-L6-v2` embeddings
- **Smart Retrieval** — Sentiment-aware filtering + multi-query expansion + cross-encoder re-ranking
- **Grounded Answers** — LLM instructed to answer only from provided context
- **Session Memory** — Follow-up questions with conversation history

---

## 🛠 Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | Streamlit |
| **Sentiment** | VADER, RoBERTa (BERT ensemble available in `sentiment.py`) |
| **Clustering** | BERTopic, HDBSCAN, UMAP, Sentence-Transformers |
| **RAG** | LangChain, ChromaDB, HuggingFace Embeddings, FastAPI |
| **LLM** | OpenRouter (DeepSeek / Google Gemini) |
| **Database** | SQLite |
| **Alerts** | Pandas, scikit-learn (TF-IDF) |

---

## 📂 Project Structure

```
BizInsight-AI/
├── app.py                  # Main Streamlit application (6 tabs)
├── alerts.py               #  Trend Alert & Risk Detection module
├── database.py             # SQLite CRUD layer
├── sentiment.py            # VADER + BERT ensemble scorer
├── pdf_generator.py        # PDF report generator
├── sync_vectors.py         # CLI tool to sync SQLite → ChromaDB
├── run_chatbot_api.py      # FastAPI server launcher
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
│
├── clustering/             # Complaint clustering pipeline
│   ├── run_clustering.py   # Full pipeline: embed → UMAP → HDBSCAN → BERTopic
│   ├── vectorize.py        # Sentence-transformer model loading
│   └── preprocess.py       # Text cleaning for clustering
│
├── rag_api/                # RAG chatbot backend
│   ├── api.py              # FastAPI endpoints (/chat, /sync)
│   ├── chains.py           # LangChain RAG chain with memory
│   ├── vector_store.py     # ChromaDB integration
│   ├── embeddings.py       # HuggingFace embeddings
│   └── config.py           # Configuration constants
│
├── tests/                  # Test suite
│   ├── test_alerts.py      # 38 tests for alerts module
│   ├── test_database.py    # 18 tests for database layer
│   └── alerts_test_reviews.csv
│
├── data/
│   └── reviews.csv         # Sample review data
└── docs/
    └── ARCHITECTURE.md     # Architecture documentation
```

---

## 📥 Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Rajarshisaha10/BizInsight-AI.git
cd BizInsight-AI
```

### 2. Set Up a Virtual Environment

**Using venv (recommended):**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

**Using conda:**
```bash
conda create --name bizinsight python=3.10 -y
conda activate bizinsight
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

1. Get a free API key from [OpenRouter](https://openrouter.ai/)
2. Copy the example env file:
   ```bash
   # macOS / Linux
   cp .env.example .env

   # Windows
   copy .env.example .env
   ```
3. Add your key to `.env`:
   ```
   OPENROUTER_API_KEY=your_api_key_here
   ```

> ⚠️ Never commit your `.env` file. It is already in `.gitignore`.

### 5. Run the Application

```bash
streamlit run app.py
```

### 6. (Optional) Start the RAG Chatbot Backend

In a separate terminal:
```bash
python run_chatbot_api.py
```

---

## 📄 CSV Format

Your CSV file must contain a column named `review`:

```csv
review
"The product quality is amazing, will buy again!"
"Shipping was late and the item arrived damaged."
"Decent for the price, nothing special."
```

---

## 🧪 Testing

The project includes **56 automated tests** covering the alerts module and database layer.

```bash
# Run all tests
python -m pytest tests/ -v

# Run only alerts tests
python -m pytest tests/test_alerts.py -v

# Run only database tests
python -m pytest tests/test_database.py -v
```

### Test Coverage

| Module | Tests | Areas Covered |
|--------|-------|---------------|
| `alerts.py` | 38 | Risk scoring, spike detection, keyword extraction, DB integration, edge cases, constants |
| `database.py` | 18 | Table creation, CRUD operations, validation, unicode, ordering |

---

## 📈 Example Use Cases

- E-commerce customer experience monitoring
- Service quality trend analysis
- Product feedback insights and issue detection
- Early warning system for customer satisfaction drops
- Competitive analysis through review data

---

## 🏆 Why BizInsight AI?

Manually analyzing customer feedback is time-consuming and error-prone. BizInsight AI converts raw reviews into **actionable business intelligence** using AI — and now, with the Trend Alert system, it **catches problems before you do**.

---

## 📌 Future Enhancements

- Multi-business login system
- Automated PDF report generation
- Email / Slack notifications for high-risk alerts
- Historical alert timeline and trend tracking
- Category-level risk breakdown

---

## 👨‍💻 Contributors

Built by **Prateek Singh** & **Rajarshi Saha**
BTech Students | AI & Software Development Enthusiasts

---

⭐ If you like this project, consider giving it a star!
