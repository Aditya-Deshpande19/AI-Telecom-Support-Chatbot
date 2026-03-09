from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama
from config import LLM_MODEL

response_model = ChatOllama(model=LLM_MODEL)

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
