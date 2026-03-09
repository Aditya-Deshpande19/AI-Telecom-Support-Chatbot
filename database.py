import logging
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from config import DB_PATH, COLLECTION_NAME, EMBEDDING_MODEL, RETRIEVER_K

logger = logging.getLogger(__name__)

logger.info(f"Loading Chroma store: {DB_PATH}, collection: {COLLECTION_NAME}")

embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)

vectorstore = Chroma(
    persist_directory=DB_PATH,
    collection_name=COLLECTION_NAME,
    embedding_function=embeddings,
)

count = len(vectorstore.get().get("ids", []))
logger.info(f"Stored vectors in Chroma: {count}")

retriever = vectorstore.as_retriever(search_kwargs={"k": RETRIEVER_K})
