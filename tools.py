from langchain_core.tools import tool
from database import retriever


@tool
def retriever_tool(query: str) -> str:
    """Search knowledge base for Jio information"""
    docs = retriever.invoke(query)
    if not docs:
        return "No results found"
    docs_limited = docs[:5]
    return "\n".join([f"[{i+1}] {doc.page_content}" for i, doc in enumerate(docs_limited)])


tools = [retriever_tool]