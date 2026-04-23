import logging
import os
import requests
import sys
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from config import DB_PATH, COLLECTION_NAME, EMBEDDING_MODEL, RETRIEVER_K

logger = logging.getLogger(__name__)

# Respect OLLAMA_HOST from environment so container → host routing works.
# Default to localhost for local dev without Docker.
_OLLAMA_BASE = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")

logger.info(f"Loading Chroma store: {DB_PATH}, collection: {COLLECTION_NAME}")


def check_ollama_health(timeout=5):
    """
    Check if Ollama is running and accessible.
    Raises SystemExit with clear error message if unavailable.
    """
    try:
        response = requests.get(f"{_OLLAMA_BASE}/api/tags", timeout=timeout)

        # Check if response status is successful
        if response.status_code != 200:
            logger.error(
                f"✗ CRITICAL: Ollama returned non-200 status code"
                f"\nStatus Code: {response.status_code}"
                f"\nResponse: {response.text}"
                f"\n\nOllama is required to run this application."
                f"\n\nHow to fix:"
                f"\n1. Verify Ollama is running: ollama serve"
                f"\n2. Check Ollama is available at {_OLLAMA_BASE}"
                f"\n3. Then restart this application"
            )
            sys.exit(1)

        logger.info("✓ Ollama is running and accessible")
        return True

    except requests.RequestException as e:
        logger.error(
            f"✗ CRITICAL: Cannot connect to Ollama at {_OLLAMA_BASE}"
            f"\n\nOllama is required to run this application."
            f"\n\nHow to fix:"
            f"\n1. Download Ollama from https://ollama.com"
            f"\n2. Start Ollama: ollama serve"
            f"\n3. Pull the required model: ollama pull llama3:8b"
            f"\n4. Then restart this application"
            f"\n\nError details: {str(e)}"
        )
        sys.exit(1)


# Ollama health check is handled by lifespan() in main.py before this module's
# objects are used. Do not call check_ollama_health() here — it would run twice
# on startup and also fire during any import-time test setup.

embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=_OLLAMA_BASE)

vectorstore = Chroma(
    persist_directory=DB_PATH,
    collection_name=COLLECTION_NAME,
    embedding_function=embeddings,
)

result = vectorstore.get()
count = len(result.get("ids", []) if result else [])
logger.info(f"Stored vectors in Chroma: {count}")

retriever = vectorstore.as_retriever(search_kwargs={"k": RETRIEVER_K})
