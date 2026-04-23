
# Jio RAG Support Agent

An AI-powered customer support chatbot for Jio services that runs entirely on your local machine. No paid APIs required. It uses a Retrieval-Augmented Generation (RAG) pipeline to search a Jio knowledge base and generate accurate, context-grounded answers.

> **What is RAG?** Instead of relying on the AI's training data alone, RAG first searches a knowledge base for relevant documents, then uses those documents as context to generate an answer. This makes responses more accurate and grounded in real information.

---

## Features

- API Key Authentication — `X-API-Key` header secures all protected endpoints
- Persistent Conversation History — SQLite-backed multi-turn chat sessions
- RAG Pipeline — searches local Jio knowledge base (PDFs, FAQs, plans)
- Spell Correction — SymSpell with 50+ Jio-specific custom corrections
- Input Validation — harmful keyword filter, profanity filter, length checks
- Query Rewriting — automatically retries with improved query if results are poor (max 2 retries)
- Document Grading — scores retrieved documents for Jio relevance before answering
- Hallucination Check — validates answer is grounded in retrieved context via word overlap
- Source Attribution — appends "Retrieved from Jio Knowledge Base" footer to answers
- LangSmith Tracing — optional pipeline monitoring and debugging
- Swagger UI — interactive API docs at `/docs`

---

## How It Works

When a user sends a question, it passes through an 8-node LangGraph pipeline:

```text
User Question
      |
1. validate_input          — spell correct, block harmful/profanity/gibberish input
      |
      +-(blocked)---------------------------------------------------> END
      |
2. enrich_context          — detect intent (troubleshooting / billing / informational)
      |
3. generate_query_or_respond  — always forces a ChromaDB retrieval tool call
      |
4. retrieve                — ToolNode runs retriever_tool, returns top 5 docs from ChromaDB
      |
5. grade_documents         — keyword overlap scoring (threshold = 3 Jio keywords)
      |
      +-(not relevant)--> rewrite_question --> (max 2 rewrites, then fallback END)
      |                        |
      |                        +-(continue)--> back to generate_query_or_respond
      |
6. generate_answer         — llama3:8b generates plain-English answer from context
      |
7. format_answer           — appends sources footer (skipped for refusal messages)
      |
8. hallucination_router    — checks word overlap between answer and context (>= 5 words)
      |
      +-(low overlap)----> rewrite_question (retry)
      |
      +-(grounded)-------------------------------------------------> END
```

---

## Tech Stack

| Tool | Version / Model | Purpose |
| ------ | ---------------- | --------- |
| [FastAPI](https://fastapi.tiangolo.com) | 0.110+ | REST API backend |
| [LangGraph](https://github.com/langchain-ai/langgraph) | latest | Agent graph orchestration |
| [LangChain](https://python.langchain.com) | latest | LLM chains and tooling |
| [ChromaDB](https://www.trychroma.com) | latest | Local vector database |
| [Ollama](https://ollama.com) | latest | Run LLMs locally |
| [llama3:8b](https://ollama.com/library/llama3.2) | 3b | Local LLM for answer generation |
| [nomic-embed-text](https://ollama.com/library/nomic-embed-text) | latest | Local embedding model |
| [SymSpellPy](https://github.com/mammothb/symspellpy) | latest | Spell correction |
| [better-profanity](https://github.com/snguyenthanh/better_profanity) | latest | Profanity filtering |
| [SQLite](https://www.sqlite.org) | built-in | Conversation history persistence |
| [LangSmith](https://smith.langchain.com) | — | Optional tracing and monitoring |

---

## Project Structure

```text
RaG_App/
├── main.py            # FastAPI app — endpoints, auth, conversation wiring
├── rag_graph.py       # LangGraph graph assembly — wires all nodes together
├── nodes.py           # All 8 node functions and routing logic
├── chains.py          # Rewrite chain (prompt -> llama3:8b -> string)
├── tools.py           # retriever_tool — searches ChromaDB, returns top 5 docs
├── database.py        # ChromaDB and embeddings setup, Ollama health check
├── chat_history.py    # SQLite CRUD — conversations and messages tables
├── config.py          # All configuration constants and keyword lists
├── rag.ipynb          # Jupyter notebook — data ingestion and vector indexing
├── Dockerfile         # Container image — python:3.12-slim + uv
├── docker-compose.yml # Service definition — Ollama on host, volumes for data
├── .dockerignore      # Excludes venvs, data, .env from Docker build context
├── Makefile           # Docker helpers: up, down, logs, migrate-db
├── .env               # API keys (never committed to git)
├── .env.example       # Template for setting up .env
├── requirements.txt   # Python dependencies
└── chat_history.db    # SQLite database (auto-created on first run, git-ignored)
```

---

## Prerequisites

Before you start, make sure you have the following installed:

- **Python 3.12+** — [Download here](https://www.python.org/downloads/)
- **uv** (fast Python package manager) — `pip install uv`
- **Ollama** — [Download here](https://ollama.com) — runs LLMs locally
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

Make sure Ollama is running first (`ollama serve`), then pull:

```bash
ollama pull llama3:8b
ollama pull nomic-embed-text
```

### Step 5 — Set up environment variables

Copy `.env.example` to `.env`:

```bash
# Windows
copy .env.example .env

# Mac/Linux
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
# Required — your API security key (use a long random string)
JIO_RAG_API_KEY=your-secret-api-key-here

# Optional — LangSmith tracing (get a free key at smith.langchain.com)
LANGCHAIN_API_KEY=your-langsmith-key-here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=Jio_RAG_Project
```

> If you do not have a LangSmith key, set `LANGCHAIN_TRACING_V2=false` to disable tracing.

### Step 6 — Build the knowledge base

Open `rag.ipynb` in Jupyter and run all cells. This loads Jio documents (PDFs, JSONs) into ChromaDB and saves the vector store to `./chroma_db_v4`.

> **This step is required before running the API.** The ChromaDB folder is excluded from the repo due to its size.

### Step 7 — Start the API

```bash
python main.py
```

The API starts on `http://0.0.0.0:8080` and is accessible at:

- **API base:** `http://127.0.0.1:8080`
- **Swagger UI:** `http://127.0.0.1:8080/docs`

---

## Running with Docker

Docker runs the FastAPI backend in a container while Ollama continues to run on your host machine.

### Docker Prerequisites

- Docker and Docker Compose installed
- Ollama running on your host (`ollama serve`)
- ChromaDB populated — run `rag.ipynb` first to build `./chroma_db_v4`

### Step 1 — Build and start

```bash
docker-compose up --build
```

The API will be available at `http://localhost:8080`.

### Step 2 — Verify

```bash
curl http://localhost:8080/health
```

### Step 3 — Stop

```bash
docker-compose down
```

### Notes

- Ollama runs on your host machine, not inside the container. The container connects to it via `host.docker.internal:11434`.
- On Linux, `host.docker.internal` resolves via the `extra_hosts` setting in `docker-compose.yml`.
- ChromaDB is mounted as a bind-mount volume (`./chroma_db_v4`) — data persists across container restarts.
- `chat_history.db` is stored in the **named volume** `chat_history_data` managed by Docker — data persists across restarts. The command `docker-compose down -v` uses the `-v`/`--volumes` flag which removes **all** volumes defined in the compose file and may delete other important data. To delete only the chat history without affecting others, use the safer alternative `docker volume rm chat_history_data`.
- Never build with `.env` inside the image — it is passed in at runtime via `env_file`.

### Migrating existing chat history into Docker

> **Only needed if** you previously ran the container with the old bind-mount (`./chat_history.db:/app/chat_history.db`) and want to preserve existing conversation data after upgrading to the named-volume configuration.

#### Option A — One command (requires `make`)

```bash
make migrate-db
```

#### Option B — Manual steps

```bash
# 1. Back up your existing file first
cp ./chat_history.db ./chat_history.db.bak

# 2. Start the container so Docker creates the named volume
docker-compose up -d

# 3. Copy the host file into the chat_history_data named volume (requires Compose v2.18+)
docker compose cp ./chat_history.db api:/app/data/chat_history.db

# 4. Restart the container so it picks up the migrated database
docker-compose restart api

# 5. Verify the API is healthy
curl http://localhost:8080/health
```

After confirming the container works correctly, you can safely remove or rename `./chat_history.db` from the host — it is no longer read by the container.

#### Backing up the named volume

*Note: The command below uses `$(pwd)` which works on Mac/Linux shells. Windows cmd.exe requires `%cd%` and PowerShell requires `${PWD}` in place of `$(pwd)`.*

**Mac/Linux:**

```bash
docker run --rm -v chat_history_data:/data -v $(pwd):/backup alpine tar czf /backup/chat_history_backup.tar.gz -C /data .
```

**Windows (cmd):**

```bash
docker run --rm -v chat_history_data:/data -v %cd%:/backup alpine tar czf /backup/chat_history_backup.tar.gz -C /data .
```

**Windows (PowerShell):**

```bash
docker run --rm -v chat_history_data:/data -v ${PWD}:/backup alpine tar czf /backup/chat_history_backup.tar.gz -C /data .
```

---

## API Endpoints

| Method | Endpoint | Auth | Description |
| -------- | ---------- | ------ | ------------- |
| GET | `/health` | None | Server liveness check |
| GET | `/stats` | Required | Vector store document count |
| POST | `/chat` | Required | Send a question, get an answer |
| GET | `/conversations/{id}` | Required | Get full conversation history |
| DELETE | `/conversations/{id}` | Required | Delete a conversation |

All protected endpoints require the header: `X-API-Key: <your key>`

---

### Example: Start a conversation

```bash
curl -X POST http://127.0.0.1:8080/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"query": "What is Jio Fiber?"}'
```

**Response:**

```json
{
  "request_id": "a1b2c3d4",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "answer": "Jio Fiber is a high-speed broadband service...\n\n---\n**Sources:** Retrieved from Jio Knowledge Base\nInformation verified from retrieved documents",
  "status": "success",
  "response_time_ms": 3241.87
}
```

### Example: Continue a conversation (multi-turn)

Pass the `conversation_id` from the previous response to maintain context:

```bash
curl -X POST http://127.0.0.1:8080/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "query": "What plans does it offer?",
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

---

## Configuration

All settings are in `config.py`. You can adjust these without modifying the core pipeline logic:

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `DB_PATH` | `./chroma_db_v4` | Where ChromaDB stores vectors |
| `COLLECTION_NAME` | `jio_knowledge_base` | ChromaDB collection name |
| `LLM_MODEL` | `llama3:8b` | Ollama model for answer generation |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Ollama model for embeddings |
| `MAX_REWRITES` | `2` | Max query rewrites before fallback answer |
| `RETRIEVER_K` | `3` | Number of docs to retrieve per search |
| `KEYWORD_THRESHOLD` | `3` | Min Jio keyword matches to grade docs as relevant |

---

## Troubleshooting

**`JIO_RAG_API_KEY` not set — requests rejected with 500**
Add `JIO_RAG_API_KEY=your-key` to your `.env` file and restart the API.

**401 Unauthorized on all requests**
All endpoints except `/health` require the `X-API-Key: YOUR_API_KEY` header.

**Ollama not found / connection refused**
Start Ollama in a separate terminal with `ollama serve`. The API will refuse to start if Ollama is unreachable.

**ChromaDB not found / empty stats response**
Run the `rag.ipynb` notebook first to create and populate the vector store. The `./chroma_db_v4` folder is not included in the repo.

**Port already in use**
Edit the `port` value in the `uvicorn.run()` call at the bottom of `main.py`.

**Slow responses**
Expected when running `llama3:8b` on CPU — allow 3–10 seconds per request. A GPU significantly reduces this. Queries that trigger rewrites will take proportionally longer.

---

## General Notes

- ChromaDB folders (`chroma_db_v4`, etc.) are excluded from the repo — rebuild locally using `rag.ipynb`
- Ollama must be running before starting the API (`ollama serve`)
- Keep `workers=1` in uvicorn — Ollama handles one inference at a time
- The `.env` file is excluded from git — never commit API keys
- `chat_history.db` is auto-created on first startup and excluded from git via `.gitignore`