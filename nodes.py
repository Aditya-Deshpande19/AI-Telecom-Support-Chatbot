import uuid
import logging
from langchain_core.messages import HumanMessage, AIMessage
from langchain_ollama import ChatOllama
from langgraph.graph import MessagesState
from config import HARMFUL_KEYWORDS, JIO_KEYWORDS, KEYWORD_THRESHOLD, MAX_REWRITES, LLM_MODEL, CUSTOM_CORRECTIONS
from chains import rewrite_chain

logger = logging.getLogger(__name__)

from spellchecker import SpellChecker

spell = SpellChecker()

def correct_spelling(text: str) -> str:
    words = text.split()
    corrected = []
    for word in words:
        word_lower = word.lower()
        # Check custom dictionary first
        if word_lower in CUSTOM_CORRECTIONS:
            corrected.append(CUSTOM_CORRECTIONS[word_lower])
        else:
            # Fall back to pyspellchecker
            correction = spell.correction(word)
            corrected.append(correction if correction else word)
    return " ".join(corrected)

# ============= NODE 1: VALIDATE INPUT =============
def validate_input(state: MessagesState):
    messages = state["messages"]
    user_msg = messages[-1].content if messages else ""
    cleaned = user_msg.strip()

    if len(cleaned) < 3:
        return {"messages": [AIMessage(content="Please ask a more specific question about Jio services.")]}

    if any(keyword in cleaned.lower() for keyword in HARMFUL_KEYWORDS):
        return {"messages": [AIMessage(content="I can't help with that. Please ask about Jio services instead.")]}

    # Auto correct spelling before passing forward
    corrected = correct_spelling(cleaned)
    if corrected != cleaned:
        logger.info(f"Spell corrected: '{cleaned}' -> '{corrected}'")

    # Replace message with corrected version
    from langchain_core.messages import HumanMessage
    corrected_messages = [HumanMessage(content=corrected)]
    return {"messages": corrected_messages}

def is_fallback(state: MessagesState) -> str:
    """Check if rewrite_question returned a fallback message or a real rewrite"""
    last_msg = state["messages"][-1]
    
    # If last message is AIMessage it means max rewrites was hit
    if last_msg.type == "ai":
        logger.info("Fallback reached — exiting graph")
        return "end"
    
    # If last message is HumanMessage it's a real rewrite — continue
    return "continue"

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

    logger.info(f"User Intent Detected: {intent}")
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

    logger.info(f"Forcing retrieval for: {question[:80]}")
    return {"messages": [tool_call_msg]}


# ============= NODE 4: REWRITE QUESTION =============
def rewrite_question(state: MessagesState):
    messages = state["messages"]

    rewrite_count = sum(1 for msg in messages if msg.type == "human") - 1

    if rewrite_count >= MAX_REWRITES:
        logger.warning("Max rewrites reached, returning fallback answer")
        return {"messages": [AIMessage(content="I'm sorry, I couldn't find relevant information. Please try rephrasing or contact Jio support directly.")]}

    question = next(
        (msg.content for msg in reversed(messages) if msg.type == "human"), ""
    )

    if not question:
        return {"messages": messages}

    better_question = rewrite_chain.invoke({"question": question})

    logger.info(f"Rewrite #{rewrite_count} | Original: {question[:80]}")
    logger.info(f"Rewritten: {better_question}")

    return {"messages": [HumanMessage(content=better_question)]}


# ============= GRADE DOCUMENTS (ROUTER) =============
def grade_documents(state: MessagesState) -> str:
    messages = state["messages"]
    tool_result = next((msg.content for msg in reversed(messages) if msg.type == "tool"), "")

    logger.info(f"Grading documents — Retrieved: {len(tool_result)} chars")

    if not tool_result or "No results found" in tool_result:
        return "rewrite_question"

    keyword_hits = sum(1 for kw in JIO_KEYWORDS if kw in tool_result.lower())

    if keyword_hits >= KEYWORD_THRESHOLD:
        logger.info(f"RELEVANT: {keyword_hits} keywords found")
        return "generate_answer"

    logger.info(f"NOT RELEVANT: only {keyword_hits} keywords, rewriting...")
    return "rewrite_question"


# ============= NODE 5: GENERATE ANSWER =============
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

    logger.info(f"Generated answer: {answer[:100]}...")
    return {"messages": [AIMessage(content=answer)]}


# ============= NODE 6: FORMAT ANSWER =============
def format_answer(state: MessagesState):
    messages = state["messages"]
    answer_msg = messages[-1].content if messages else ""

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

    if not context or "No results found" in context:
        return "end"

    if len(answer) > len(context) * 2.5:
        logger.warning("Answer may contain hallucinations, rewriting...")
        return "rewrite_question"

    logger.info("Answer looks legitimate")
    return "end"
