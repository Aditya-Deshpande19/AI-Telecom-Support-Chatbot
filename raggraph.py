from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from dotenv import load_dotenv
import os
import uuid

load_dotenv()

response_model = ChatOllama(model="llama3.1", temperature=0)

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

DB_PATH = "./chroma_db_v3"
COLLECTION_NAME = "jio_knowledge_base"
embeddings = OllamaEmbeddings(model="nomic-embed-text") 

print(f"Loading Chroma store: {DB_PATH}, collection {COLLECTION_NAME}")
vectorstore = Chroma(
    persist_directory=DB_PATH,
    collection_name=COLLECTION_NAME,
    embedding_function=embeddings,
)
count = len(vectorstore.get().get("ids", []))
print(f"*** Stored vectors in Chroma: {count} ***")

retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

@tool
def retriever_tool(query: str) -> str:
    """Search knowledge base for Jio information"""
    docs = retriever.invoke(query)
    if not docs:
        return "No results found"
    chunks = []
    for i, doc in enumerate(docs, start=1):
        src = None
        if hasattr(doc, "metadata") and isinstance(doc.metadata, dict):
            src = doc.metadata.get("source") or doc.metadata.get("file") or doc.metadata.get("url") or doc.metadata.get("title")
        header = f"[Source {i}{': ' + str(src) if src else ''}]"
        chunks.append(f"{header}\n{doc.page_content}")
    return "\n\n".join(chunks)

tools = [retriever_tool]
llm_with_tools = response_model.bind_tools(tools)


class RelevanceScore(BaseModel):
    """Relevance score for retrieved documents"""
    score: str = Field(description="'yes' if documents are relevant, 'no' if not")
    reason: str = Field(description="Brief reason for the score")

def _is_smalltalk(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return True
    smalltalk_phrases = {
        "hi",
        "hello",
        "hey",
        "hii",
        "hiii",
        "hey there",
        "hello jio",
        "hello jio ai",
        "how are you",
        "how are you?",
        "how do you do",
        "how do you do?",
        "good morning",
        "good afternoon",
        "good evening",
        "thanks",
        "thank you",
        "ok",
        "okay",
    }
    if t in smalltalk_phrases:
        return True
    # Treat very short pleasantries as smalltalk (but keep real “plan”, “recharge”, etc. flowing to RAG).
    if len(t) <= 25 and any(p in t for p in ["hi", "hello", "hey", "how are you", "how do you do", "good morning", "good evening", "thanks", "thank you"]):
        return True
    return False


def validate_input(state: MessagesState):
    """Validate and sanitize user input"""
    messages = state["messages"]
    user_msg = messages[-1].content if messages else ""
    
    msg = (user_msg or "").strip()
    if _is_smalltalk(msg):
        return {
            "messages": [
                AIMessage(
                    content=(
                        "Hello! I’m Jio AI.\n\n"
                        "How can I help you today?"
                    )
                )
            ]
        }

    if len(user_msg.strip()) < 3:
        return {"messages": [AIMessage(content="Please ask a more specific question about Jio services or connectivity.")]}
    
    harmful_keywords = ["hack", "malware", "virus"]
    if any(keyword in user_msg.lower() for keyword in harmful_keywords):
        return {"messages": [AIMessage(content="I can't help with that request. Please ask about Jio services instead.")]}
    
    return {"messages": messages}


def enrich_context(state: MessagesState):
    """Add user intent detection (for logging only)"""
    messages = state["messages"]
    question = next((msg.content for msg in messages if msg.type == "human"), "")
    
    intent = "general"
    if any(word in question.lower() for word in ["how", "fix", "issue", "problem", "solve"]):
        intent = "troubleshooting"
    elif any(word in question.lower() for word in ["what", "tell", "explain", "describe"]):
        intent = "informational"
    elif any(word in question.lower() for word in ["cost", "price", "plan", "recharge"]):
        intent = "billing"
    
    print(f"User Intent Detected: {intent}")
    

    return {"messages": messages}


def generate_query_or_respond(state: MessagesState):
    """Force retrieval unless it's smalltalk"""
    messages = state["messages"]

    question = next(
        (msg.content for msg in reversed(messages) if msg.type == "human"),
        ""
    )

    if _is_smalltalk(question):
        return {
            "messages": [
                AIMessage(
                    content=(
                        "How do you do! I’m Jio AI.\n\n"
                        "What can I help you with today?"
                    )
                )
            ]
        }

    tool_call_msg = AIMessage(
        content="",
        tool_calls=[{
            "name": "retriever_tool",
            "args": {"query": question},
            "id": str(uuid.uuid4()),
            "type": "tool_call"
        }]
    )
    
    print(f"Forcing retrieval for: {question[:80]}")
    return {"messages": [tool_call_msg]}


REWRITE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are a query optimization tool for Jio knowledge base. "
               "Transform vague queries into specific, searchable questions. "
               "Output ONLY the improved query."),
    ("user", "Original: {question}\n\nImproved:"),
])

rewrite_chain = REWRITE_PROMPT | response_model | StrOutputParser()


def rewrite_question(state: MessagesState):
    """Rewrite question for better retrieval using LLM"""
    messages = state["messages"]

    rewrite_count = sum(1 for msg in messages if msg.type == "human") - 1
    
    if rewrite_count >= 3:
        print(" Max rewrites reached, returning fallback answer")
        return {"messages": [AIMessage(content="I'm sorry, I couldn't find relevant information about your query in the Jio knowledge base. Please try rephrasing your question or contact Jio support directly.")]}
    
    question = next(
        (msg.content for msg in reversed(messages) if msg.type == "human"),
        ""
    )
    
    if not question:
        return {"messages": messages}
    
    better_question = rewrite_chain.invoke({"question": question})
    
    print(f"Rewrite #{rewrite_count} | Original: {question[:80]}")
    print(f"Rewritten: {better_question}")
    
    return {"messages": [HumanMessage(content=better_question)]}


def grade_documents(state: MessagesState) -> str:
    messages = state["messages"]
    
    question = next((msg.content for msg in messages if msg.type == "human"), "")
    tool_result = next((msg.content for msg in reversed(messages) if msg.type == "tool"), "")
    
    print(f"---GRADING DOCUMENTS---")
    print(f"Retrieved: {len(tool_result)} chars")
    
    if not tool_result or "No results found" in tool_result:
        return "rewrite_question"

    jio_keywords = ["jio", "fiber", "plan", "recharge", "network", "internet", 
                    "speed", "connectivity", "gateway", "sim", "data", "tariff"]
    
    content_lower = tool_result.lower()
    keyword_hits = sum(1 for kw in jio_keywords if kw in content_lower)
    
    if keyword_hits >= 2:
        print(f"RELEVANT: {keyword_hits} Jio keywords found, proceeding")
        return "generate_answer"
    
    print(f"NOT RELEVANT: only {keyword_hits} keywords, rewriting...")
    return "rewrite_question"


def generate_answer(state: MessagesState):
    messages = state["messages"]
    
    question = next(
        (msg.content for msg in reversed(messages) if msg.type == "human"),
        "No question found"
    )
    
    tool_messages = [msg.content for msg in messages if msg.type == "tool"]
    tool_message = "\n\n".join(tool_messages) if tool_messages else "No documents retrieved."
    

    plain_prompt = f"""You are Jio AI, a friendly customer support assistant.
Respond conversationally and naturally.
Be practical and step-by-step when troubleshooting.
Do not mention “context”, “knowledge base”, “sources”, or internal tool output.
Only claim things that are supported by the information provided. If information is missing or uncertain, say so.
If you cannot answer confidently, ask 1-2 clarifying questions and offer escalation.
If escalating, share: 7000570005, jiofibercare@jio.com, 1800-896-9999, and www.jio.com/fiber.
Write plain English only (no JSON).

INFORMATION YOU CAN USE (may be empty):
{tool_message}

USER:
{question}

ASSISTANT:"""
    
    from langchain_core.messages import SystemMessage
    
    clean_llm = ChatOllama(model="llama3.1", temperature=0)
  
    response = clean_llm.invoke(plain_prompt)
    answer = response.content

    if answer.strip().startswith("{"):
        answer = "I don't have enough information to answer that question based on the available documents."
    
    print(f"Generated answer: {answer[:100]}...")
    return {"messages": [AIMessage(content=answer)]}

def format_answer(state: MessagesState):
    messages = state["messages"]
    answer_msg = messages[-1].content if messages else ""
   
    if "I'm sorry" in answer_msg or "couldn't find" in answer_msg:
        return {"messages": [AIMessage(content=answer_msg)]}

    # Keep responses conversational; don't append “sources” unless the UI explicitly wants citations.
    return {"messages": [AIMessage(content=answer_msg)]}


def hallucination_router(state: MessagesState) -> str:
    """Check if answer aligns with context - ROUTING FUNCTION"""
    messages = state["messages"]
    
    answer = messages[-1].content if messages else ""
    context = next((msg.content for msg in reversed(messages) if msg.type == "tool"), "")
    
    print(f"---CHECKING FOR HALLUCINATION---")
    print(f"Answer length: {len(answer)}, Context length: {len(context)}")
    
    if not context or "No results found" in context:
        print(" No context to check, proceeding to END")
        return "end"
    
    if len(answer) > len(context) * 2.5:
        print(" Answer may contain hallucinations, rewriting...")
        return "rewrite_question"
    
    print(" Answer looks legitimate, proceeding to END")
    return "end"


workflow = StateGraph(MessagesState)

workflow.add_node("validate_input", validate_input)
workflow.add_node("enrich_context", enrich_context)
workflow.add_node("generate_query_or_respond", generate_query_or_respond)
workflow.add_node("retrieve", ToolNode(tools))
workflow.add_node("rewrite_question", rewrite_question)
workflow.add_node("generate_answer", generate_answer)
workflow.add_node("format_answer", format_answer)

workflow.add_edge(START, "validate_input")
workflow.add_edge("validate_input", "enrich_context")
workflow.add_edge("enrich_context", "generate_query_or_respond")

workflow.add_conditional_edges(
    "generate_query_or_respond",
    tools_condition,
    {"tools": "retrieve", END: END},
)

workflow.add_conditional_edges(
    "retrieve",
    grade_documents,
    {
        "generate_answer": "generate_answer",
        "rewrite_question": "rewrite_question",
    },
)

workflow.add_edge("generate_answer", "format_answer")

workflow.add_conditional_edges(
    "format_answer",
    hallucination_router,
    {
        "end": END,
        "rewrite_question": "rewrite_question",
    },
)

workflow.add_edge("rewrite_question", "generate_query_or_respond")

graph = workflow.compile()
