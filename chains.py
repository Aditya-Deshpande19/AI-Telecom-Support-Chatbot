import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama
from config import LLM_MODEL

_OLLAMA_BASE = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
response_model = ChatOllama(model=LLM_MODEL, timeout=60, base_url=_OLLAMA_BASE)

REWRITE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a query optimization tool for Jio knowledge base. "
        "Transform vague queries into specific, searchable questions. "
        "Output ONLY the improved query."
    ),
    ("user", "Original: {question}\n\nImproved:"),
])

rewrite_chain = REWRITE_PROMPT | response_model | StrOutputParser()