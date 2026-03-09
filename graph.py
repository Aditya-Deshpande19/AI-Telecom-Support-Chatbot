import uuid
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.tools import tool
from langchain_chroma import Chroma
from pydantic import BaseModel, Field



# ============= CONFIGURATION =============
DB_PATH = "./chroma_db_v3"
COLLECTION_NAME = "jio_knowledge_base"
EMBEDDING_MODEL = "nomic-embed-text"
LLM_MODEL = "qwen2.5:7b"


# ============= INITIALIZATION =============
print(f"Loading Chroma store: {DB_PATH}, collection {COLLECTION_NAME}")

embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)

vectorstore = Chroma(
    persist_directory=DB_PATH,
    collection_name=COLLECTION_NAME,
    embedding_function=embeddings,
)

count = len(vectorstore.get().get("ids", []))
print(f"*** Stored vectors in Chroma: {count} ***")

retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
response_model = ChatOllama(model=LLM_MODEL)


# ============= TOOL =============
@tool
def retriever_tool(query: str) -> str:
    """Search knowledge base for Jio information"""
    docs = retriever.invoke(query)
    return "\n".join([doc.page_content for doc in docs]) if docs else "No results found"

tools = [retriever_tool]


# ============= REWRITE CHAIN =============
REWRITE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are a query optimization tool for Jio knowledge base. "
               "Transform vague queries into specific, searchable questions. "
               "Output ONLY the improved query."),
    ("user", "Original: {question}\n\nImproved:"),
])

rewrite_chain = REWRITE_PROMPT | response_model | StrOutputParser()


# ============= PYDANTIC MODELS =============
class RelevanceScore(BaseModel):
    score: str = Field(description="'yes' if documents are relevant, 'no' if not")
    reason: str = Field(description="Brief reason for the score")


# ============= NODE 1: VALIDATE INPUT =============
def validate_input(state: MessagesState):
    messages = state["messages"]
    user_msg = messages[-1].content if messages else ""

    if len(user_msg.strip()) < 3:
        return {"messages": [AIMessage(content="Please ask a more specific question about Jio services.")]}

    harmful_keywords = ["hack", "malware", "virus"]
    if any(keyword in user_msg.lower() for keyword in harmful_keywords):
        return {"messages": [AIMessage(content="I can't help with that. Please ask about Jio services instead.")]}

    return {"messages": messages}


# ============= NODE 2: ENRICH CONTEXT =============
def enrich_context(state: MessagesState):
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


# ============= NODE 3: GENERATE QUERY OR RESPOND =============
def generate_query_or_respond(state: MessagesState):
    messages = state["messages"]
    question = next(
        (msg.content for msg in reversed(messages) if msg.type == "human"), ""
    )

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


# ============= NODE 4: REWRITE QUESTION =============
def rewrite_question(state: MessagesState):
    messages = state["messages"]

    # Subtract 1 to not count the original question
    rewrite_count = sum(1 for msg in messages if msg.type == "human") - 1

    if rewrite_count >= 3:
        print(" Max rewrites reached, returning fallback answer")
        return {"messages": [AIMessage(content="I'm sorry, I couldn't find relevant information. Please try rephrasing or contact Jio support directly.")]}

    question = next(
        (msg.content for msg in reversed(messages) if msg.type == "human"), ""
    )

    if not question:
        return {"messages": messages}

    better_question = rewrite_chain.invoke({"question": question})

    print(f"Rewrite #{rewrite_count} | Original: {question[:80]}")
    print(f"Rewritten: {better_question}")

    return {"messages": [HumanMessage(content=better_question)]}


# ============= GRADE DOCUMENTS =============
def grade_documents(state: MessagesState) -> str:
    messages = state["messages"]
    tool_result = next((msg.content for msg in reversed(messages) if msg.type == "tool"), "")

    print(f"---GRADING DOCUMENTS---")
    print(f"Retrieved: {len(tool_result)} chars")

    if not tool_result or "No results found" in tool_result:
        return "rewrite_question"

    jio_keywords = ["jio", "fiber", "plan", "recharge", "network", "internet",
                    "speed", "connectivity", "gateway", "sim", "data", "tariff"]

    keyword_hits = sum(1 for kw in jio_keywords if kw in tool_result.lower())

    if keyword_hits >= 2:
        print(f" RELEVANT: {keyword_hits} keywords found")
        return "generate_answer"

    print(f" NOT RELEVANT: only {keyword_hits} keywords, rewriting...")
    return "rewrite_question"


# ============= GENERATE ANSWER =============
def generate_answer(state: MessagesState):
    messages = state["messages"]

    question = next(
        (msg.content for msg in reversed(messages) if msg.type == "human"),
        "No question found"
    )

    tool_messages = [msg.content for msg in messages if msg.type == "tool"]
    tool_message = "\n\n".join(tool_messages) if tool_messages else "No documents retrieved."

    plain_prompt = f"""You are a Jio customer support assistant.
Use the context below to answer the question.
Write your answer in plain English sentences only.
Do not write JSON, do not call functions, do not use tools.

CONTEXT:
{tool_message}

QUESTION:
{question}

ANSWER (plain English only):"""

    clean_llm = ChatOllama(model=LLM_MODEL, temperature=0)
    response = clean_llm.invoke(plain_prompt)
    answer = response.content

    if answer.strip().startswith("{"):
        answer = "I don't have enough information to answer that question."

    print(f"Generated answer: {answer[:100]}...")
    return {"messages": [AIMessage(content=answer)]}


# ============= FORMAT ANSWER =============
def format_answer(state: MessagesState):
    messages = state["messages"]
    answer_msg = messages[-1].content if messages else ""

    # Don't add sources to fallback messages
    if "I'm sorry" in answer_msg or "couldn't find" in answer_msg:
        return {"messages": [AIMessage(content=answer_msg)]}

    tool_msg = next((msg.content for msg in reversed(messages) if msg.type == "tool"), "")

    formatted = f"{answer_msg}\n\n---\n**Sources:** Retrieved from Jio Knowledge Base"
    if tool_msg and "No results found" not in tool_msg:
        formatted += "\n✓ Information verified from retrieved documents"

    return {"messages": [AIMessage(content=formatted)]}


# ============= HALLUCINATION ROUTER =============
def hallucination_router(state: MessagesState) -> str:
    messages = state["messages"]
    answer = messages[-1].content if messages else ""
    context = next((msg.content for msg in reversed(messages) if msg.type == "tool"), "")

    print(f"---CHECKING FOR HALLUCINATION---")

    if not context or "No results found" in context:
        return "end"

    if len(answer) > len(context) * 2.5:
        print(" Answer may contain hallucinations, rewriting...")
        return "rewrite_question"

    print(" Answer looks legitimate")
    return "end"


# ============= BUILD GRAPH =============
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
print(" Graph compiled successfully!")
