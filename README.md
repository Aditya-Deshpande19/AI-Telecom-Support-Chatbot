# Jio RAG Support Agent

An AI-powered customer support chatbot for Jio services that runs entirely on your local machine — no paid APIs required. It uses a Retrieval-Augmented Generation (RAG) pipeline to search a Jio knowledge base and generate accurate, context-grounded answers.

> **What is RAG?** Instead of relying on the AI's training data alone, RAG first searches a knowledge base for relevant documents, then uses those documents as context to generate an answer. This makes responses more accurate and grounded in real information.

---

## Features

- Searches a local Jio knowledge base (PDFs, FAQs, user guides)
- Automatically rewrites vague queries for better search results
- Grades retrieved documents for relevance before answering
- Validates and filters harmful or gibberish input
- LangSmith tracing support for debugging and monitoring
- Production-ready FastAPI backend with logging and error handling

---

## How It Works

When a user sends a question, it goes through the following pipeline:

```text
User sends a question
        |
1. Validate Input          — block harmful or gibberish queries
        |
2. Detect Intent           — classify as troubleshooting / billing / informational
        |
3. Retrieve Documents      — search ChromaDB vector store
        |
4. Grade Documents         — are the results relevant?
        |                               |
       Yes                    No (max 2 retries)
        |                               |
5. Generate Answer          Rewrite and Search Again
        |
6. Format Answer            — add sources footer
        |
7. Hallucination Check      — verify answer length vs context
        |
   Final Response
```

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| [LangGraph](https://github.com/langchain-ai/langgraph) | Agent graph orchestration |
| [LangChain](https://python.langchain.com) | LLM chains and tooling |
| [ChromaDB](https://www.trychroma.com) | Local vector database |
| [Ollama](https://ollama.com) | Run LLMs locally |
| [llama3.1](https://ollama.com/library/llama3.1) | Local LLM for answer generation |
| [nomic-embed-text](https://ollama.com/library/nomic-embed-text) | Local embedding model |
| [FastAPI](https://fastapi.tiangolo.com) | REST API backend |
| [LangSmith](https://smith.langchain.com) | Tracing and monitoring |

---

## Project Structure

```text
RaG_App/
├── backend/
│   ├── main.py          # FastAPI app — API endpoints and request handling
│   ├── rag_graph.py     # Graph assembly — connects all nodes together
│   ├── nodes.py         # Node functions — each step in the pipeline
│   ├── chains.py        # Rewrite chain — improves vague queries
│   ├── tools.py         # Retriever tool — searches ChromaDB
│   ├── database.py      # Database setup — loads ChromaDB on startup
│   └── config.py        # Configuration — all settings in one place
├── rag.ipynb            # Jupyter notebook — data ingestion and indexing
├── .env                 # API keys (never committed to git)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Prerequisites

Before you start, make sure you have the following installed:

- **Python 3.12+** — [Download here](https://www.python.org/downloads/)
- **uv** (fast Python package manager) — `pip install uv`
- **Ollama** — [Download here](https://ollama.com) — used to run LLMs locally
- **Git** — [Download here](https://git-scm.com)

---

## Getting Started

### Step 1 — Clone the repository

```bash
git clone https://github.com/DenisAnthony871/RaG_App.git
cd RaG_App
```

### Step 2 — Create a virtual environment

```bash
uv venv

# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate
```

### Step 3 — Install dependencies

```bash
uv pip install -r requirements.txt
```

### Step 4 — Pull the required Ollama models

Make sure Ollama is running, then pull the models:

```bash
ollama pull llama3.1
ollama pull nomic-embed-text
```

### Step 5 — Set up environment variables

Copy `.env.example` to `.env` and fill in your API keys:

```bash
# Windows
copy .env.example .env

# Mac/Linux
cp .env.example .env
```

Edit `.env` and add your LangSmith API key:

```bash
LANGCHAIN_API_KEY=YOUR_LANGSMITH_API_KEY_HERE
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=Jio_RAG_Project
```

**API Key Source:**
- **LangSmith API:** Get a free key at [smith.langchain.com](https://smith.langchain.com)
  - LangSmith is optional but recommended for debugging and monitoring the RAG pipeline
  - If you skip this, set `LANGCHAIN_TRACING_V2=false` to disable tracing

### Step 6 — Build the knowledge base

Open `rag.ipynb` in Jupyter and run the indexing cells. This loads your Jio documents (PDFs, JSONs) into ChromaDB. The vector store will be saved locally to `./chroma_db_v4`.

**Note:** This step is required before running the API. The ChromaDB folder is not included in the repo due to its large file size.

### Step 7 — Start the API

```bash
cd backend
uvicorn main:app --host 127.0.0.1 --port 8080
```

The API will be available at `http://127.0.0.1:8080`

Interactive API docs are available at `http://127.0.0.1:8080/docs`

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Check if the API is running |
| GET | `/stats` | Show vector count in ChromaDB |
| POST | `/chat` | Send a question, get an answer |

### Example Request

```bash
curl -X POST http://127.0.0.1:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I fix slow internet on Jio Fiber?"}'
```

### Example Response

```json
{
  "request_id": "a1b2c3d4",
  "answer": "To fix slow internet on Jio Fiber, try restarting your Home Gateway...",
  "status": "success",
  "response_time_ms": 4821.23
}
```

---

## Configuration

All settings are in `backend/config.py`. You can adjust these without modifying the core logic:

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `./chroma_db_v4` | Where ChromaDB is stored |
| `LLM_MODEL` | `llama3.1` | Ollama model used for answers |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Ollama model used for search |
| `MAX_REWRITES` | `2` | How many times to retry a bad search |
| `RETRIEVER_K` | `3` | Number of documents to retrieve per search |
| `KEYWORD_THRESHOLD` | `2` | Minimum keyword matches to consider docs relevant |

---

## Troubleshooting

**Ollama not found / connection refused**
Make sure Ollama is running before starting the API. Open a separate terminal and run `ollama serve`.

**ChromaDB not found error**
You need to run the indexing notebook first (`rag.ipynb`) to create the vector store.

**Port already in use**
Change the port in `main.py` or kill the existing process using port 8080.

**Slow responses**
This is expected when running `llama3.1` locally on CPU — responses can take 10 to 60 seconds depending on your hardware. A GPU will significantly improve speed.

---

Author

Aditya Deshpande

AI / Machine Learning Projects and Experiments
