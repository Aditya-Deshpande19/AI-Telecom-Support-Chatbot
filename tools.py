from langchain_core.tools import tool
from database import retriever


@tool
def retriever_tool(query: str) -> str:
    """Search knowledge base for Jio information"""
    docs = retriever.invoke(query)
    return "\n".join([doc.page_content for doc in docs]) if docs else "No results found"


tools = [retriever_tool]
