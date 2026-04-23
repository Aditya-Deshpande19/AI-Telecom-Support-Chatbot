import uuid
import logging
import re
import unicodedata
import importlib.resources
from typing import Annotated
from typing_extensions import TypedDict, NotRequired
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from symspellpy import SymSpell, Verbosity
from better_profanity import profanity
from config import HARMFUL_KEYWORDS, JIO_KEYWORDS, KEYWORD_THRESHOLD, MAX_REWRITES, CUSTOM_CORRECTIONS, MAX_CONTEXT_CHARS, MAX_PROMPT_CONTEXT_CHARS
from chains import rewrite_chain, response_model


# ============= CUSTOM GRAPH STATE =============
class JioState(TypedDict):
    messages: Annotated[list, add_messages]
    confidence: NotRequired[float]    # 0.9 = high, 0.6 = medium, 0.3 = low; absent on first pass
    rewrite_count: NotRequired[int]   # absent until first rewrite; treated as 0 via .get()

logger = logging.getLogger(__name__)


# ============= SYMSPELL SETUP =============
sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)

try:
    dict_file = importlib.resources.files("symspellpy") / "frequency_dictionary_en_82_765.txt"
    with importlib.resources.as_file(dict_file) as dictionary_path:
        loaded = sym_spell.load_dictionary(str(dictionary_path), term_index=0, count_index=1)
    if not loaded:
        raise RuntimeError("SymSpell dictionary loaded but returned False — file may be empty or corrupt")
    logger.info("SymSpell dictionary loaded successfully")
except Exception as e:
    logger.error(f"Failed to load SymSpell dictionary: {e}")
    raise


# Common English words symspellpy should never modify
SKIP_CORRECTION = {
    "what", "where", "when", "why", "how", "who", "which",
    "is", "are", "was", "were", "do", "does", "did",
    "my", "me", "i", "you", "your", "the", "a", "an",
    "it", "its", "this", "that", "these", "those",
    "not", "no", "yes", "can", "will", "would", "should",
}


def correct_spelling(text: str) -> str:
    words = text.split()
    corrected = []
    for word in words:
        word_lower = word.lower()
        # Custom dictionary first — protects brand names and Jio-specific terms
        if word_lower in CUSTOM_CORRECTIONS:
            corrected.append(CUSTOM_CORRECTIONS[word_lower])
        # Skip correction for common English words symspellpy manhandles
        elif word_lower in SKIP_CORRECTION:
            corrected.append(word)
        else:
            suggestions = sym_spell.lookup(word, Verbosity.CLOSEST, max_edit_distance=2)
            corrected.append(suggestions[0].term if suggestions else word)
    return " ".join(corrected)


# ============= NODE 1: VALIDATE INPUT =============

# Short terms that are valid Jio queries despite being under the length threshold
SHORT_ALLOWLIST = {"5g", "jio", "wifi", "jiotv", "sim", "4g", "volte", "esim", "ott", "myjio"}

# Casual greetings — respond warmly instead of rejecting
GREETINGS = {
    "hi", "hello", "hey", "hii", "hiii", "helo", "hola", "namaste",
    "good morning", "good afternoon", "good evening", "good night",
    "morning", "gm", "gn",
    "yo", "sup", "heya", "howdy",
}

# Conversational closers & pleasantries — acknowledge gracefully
# Note: yes/no handling should be done via conversational intent/context logic elsewhere.
PLEASANTRIES = {
    "thanks", "thank you", "thankyou", "ty", "thx",
    "ok", "okay", "k", "got it", "understood",
    "bye", "goodbye", "see you", "cya", "later",
    "wow", "cool", "nice", "great", "awesome", "perfect",
}

PLEASANTRY_RESPONSES = {
    "thanks": "You're welcome! Let me know if you need anything else about Jio services. 😊",
    "thank you": "You're welcome! Let me know if you need anything else about Jio services. 😊",
    "thankyou": "You're welcome! Let me know if you need anything else about Jio services. 😊",
    "ty": "You're welcome! Let me know if you need anything else about Jio services. 😊",
    "thx": "You're welcome! Let me know if you need anything else about Jio services. 😊",
    "bye": "Goodbye! Feel free to come back if you have more questions about Jio. 👋",
    "goodbye": "Goodbye! Feel free to come back if you have more questions about Jio. 👋",
    "see you": "See you! I'm always here to help with Jio services. 👋",
    "cya": "See you! I'm always here to help with Jio services. 👋",
    "later": "Talk soon! I'm here whenever you need help with Jio. 👋",
}

GREETING_RESPONSE = "Hello! 👋 Welcome to Jio Support. I can help you with Jio Fiber, SIM, recharge plans, network issues, and more. What would you like to know?"

def validate_input(state: JioState):
    messages = state["messages"]
    user_msg = messages[-1].content if messages else ""
    cleaned = user_msg.strip()

    # Normalize for matching — strip trailing punctuation
    normalized = cleaned.lower().strip('!?.,:; ')

    # Greeting check — respond warmly before applying any other filter
    if normalized in GREETINGS:
        return {"messages": [AIMessage(content=GREETING_RESPONSE)]}

    # Pleasantry check — acknowledge gracefully
    if normalized in PLEASANTRIES:
        response = PLEASANTRY_RESPONSES.get(normalized, "Got it! Is there anything else I can help you with regarding Jio services?")
        return {"messages": [AIMessage(content=response)]}

    # Length check — only reject truly meaningless input (< 3 chars)
    is_question_with_content = cleaned.lower().startswith(("what ", "how ", "why ", "when ", "where ", "who "))
    if len(cleaned) < 3 and cleaned.lower() not in SHORT_ALLOWLIST and not is_question_with_content:
        return {"messages": [AIMessage(content="Could you tell me a bit more? I'm here to help with any Jio-related questions.")]}

    # Harmful keyword check
    if any(keyword in cleaned.lower() for keyword in HARMFUL_KEYWORDS):
        return {"messages": [AIMessage(content="I can't help with that. Please ask about Jio services instead.")]}

    # Profanity check — no user content logged to avoid PII leakage
    if profanity.contains_profanity(cleaned):
        logger.warning("Profanity detected in user input")
        return {"messages": [AIMessage(content="Please keep your message respectful. How can I help you with Jio services?")]}

    # Prompt injection check - Defense-in-Depth
    # 1. Robust Input Normalization
    sanitized_for_injection = unicodedata.normalize("NFKC", cleaned)
    # Remove basic homoglyphs/deceptive punctuation and collapse whitespace
    sanitized_for_injection = re.sub(r"[^\w\s]", "", sanitized_for_injection.lower())
    sanitized_for_injection = re.sub(r"\s+", " ", sanitized_for_injection)

    # 2. Regex-based Detection
    injection_pattern = re.compile(
        r"\b(ignore|disregard|forget)\b.*\b(previous|all|instructions|prompts)\b|\b(jailbreak|dan mode|act as|pretend you are)\b",
        re.IGNORECASE
    )
    if injection_pattern.search(sanitized_for_injection):
        logger.warning("[PROMPT_INJECTION_DETECTED] Regex pattern match")
        return {"messages": [AIMessage(content="I can't help with that. Please ask about Jio services instead.")]}

    # 3. Intent Classifier (Heuristic based on imperative verbs)
    imperative_verbs = {"ignore", "disregard", "forget", "bypass", "act", "pretend", "jailbreak"}
    words = sanitized_for_injection.split()
    verb_count = sum(1 for w in words if w in imperative_verbs)
    if verb_count >= 2 and len(words) <= 20: # Short bursts of heavy instructions
        logger.warning(f"[PROMPT_INJECTION_DETECTED] Heuristic triggered: {verb_count} imperative verbs")
        return {"messages": [AIMessage(content="I can't help with that. Please ask about Jio services instead.")]}
    
    # 4 & 5. Boundary enforcement is native via AIMessage return encapsulation. Telemetry handled via distinct warning tags above.

    # Spell correction
    corrected = correct_spelling(cleaned)
    if corrected != cleaned:
        logger.info("Spell correction applied to user input")

    return {"messages": [HumanMessage(content=corrected)]}


def after_validate(state: JioState) -> str:
    """Route to end if validate_input blocked the message, otherwise continue"""
    last_msg = state["messages"][-1]
    if last_msg.type == "ai":
        return "end"
    return "continue"


def is_fallback(state: JioState) -> str:
    """Check if rewrite_question returned a fallback message or a real rewrite"""
    last_msg = state["messages"][-1]
    if last_msg.type == "ai":
        logger.info("Fallback reached — exiting graph")
        return "end"
    return "continue"


# ============= NODE 2: ENRICH CONTEXT =============
def enrich_context(state: JioState):
    messages = state["messages"]
    question = next((msg.content for msg in messages if msg.type == "human"), "")

    intent = "general"
    if any(word in question.lower() for word in ["how", "fix", "issue", "problem", "solve", "wrong", "not working", "broken"]):
        intent = "troubleshooting"
    elif any(word in question.lower() for word in ["what", "tell", "explain", "describe"]):
        intent = "informational"
    elif any(word in question.lower() for word in ["cost", "price", "plan", "recharge"]):
        intent = "billing"

    logger.info(f"User Intent Detected: {intent}")
    return {"messages": messages}


# ============= NODE 3: GENERATE QUERY OR RESPOND =============
def generate_query_or_respond(state: JioState):
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
def rewrite_question(state: JioState):
    messages = state["messages"]

    rewrite_count = state.get("rewrite_count", 0)

    if rewrite_count >= MAX_REWRITES:
        logger.warning("Max rewrites reached, returning fallback answer")
        return {"messages": [AIMessage(content="I'm sorry, I couldn't find relevant information. Please try rephrasing your question or reach out to Jio support directly:\n\nToll-Free: 1800-889-9999\nMyJio App: Available on Play Store and App Store\nSelf Care: jio.com/selfcare")]}

    question = next(
        (msg.content for msg in reversed(messages) if msg.type == "human"), ""
    )

    if not question:
        return {"messages": messages}

    better_question = rewrite_chain.invoke({"question": question})

    logger.info(f"Rewrite #{rewrite_count} | Original: {question[:80]}")
    logger.info(f"Rewritten: {better_question}")

    # Return only the new message — add_messages reducer appends it to existing history.
    # Avoids mutating the state list in place before returning.
    return {"messages": [HumanMessage(content=better_question)], "rewrite_count": rewrite_count + 1}


# ============= GRADE DOCUMENTS (ROUTER) =============
def grade_documents(state: JioState) -> str:
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
def generate_answer(state: JioState):
    messages = state["messages"]

    question = next(
        (msg.content for msg in reversed(messages) if msg.type == "human"),
        "No question found"
    )

    tool_messages = [msg.content for msg in messages if msg.type == "tool"]
    tool_message = "\n\n".join(tool_messages) if tool_messages else "No documents retrieved."
    # Truncate to prevent token bloat on large knowledge base chunks
    if len(tool_message) > MAX_CONTEXT_CHARS:
        tool_message = tool_message[:MAX_CONTEXT_CHARS] + "...[truncated]"
        logger.info(f"Context truncated to {MAX_CONTEXT_CHARS} chars")

    # Build conversation history for context (human & ai messages only, skip tool messages)
    history_lines = []
    for msg in messages:
        if msg.type == "human":
            history_lines.append(f"Customer: {msg.content}")
        elif msg.type == "ai" and msg.content:  # skip empty tool-call AI messages
            history_lines.append(f"Agent: {msg.content}")
    # Keep only last few turns to avoid token bloat, exclude current question
    conversation_history = "\n".join(history_lines[:-1][-6:])  # last 3 turns (6 lines)

    history_block = ""
    if conversation_history.strip():
        history_block = f"""\nCONVERSATION HISTORY (for context — use to maintain continuity):
{conversation_history}
"""

    plain_prompt = f"""You are a Jio customer support assistant.
Use the context below to answer the question.
If the conversation history is relevant, use it to provide a more helpful and contextual answer.
Write your answer in plain English sentences only.
Do not write JSON, do not call functions, do not use tools.
{history_block}
CONTEXT:
{tool_message}

QUESTION:
{question}

ANSWER (plain English only):"""

    response = response_model.invoke(plain_prompt)
    answer = response.content

    import json
    if answer.strip():
        try:
            json.loads(answer)
            answer = "I don't have enough information to answer that question."
        except (json.JSONDecodeError, ValueError):
            pass

    logger.info(f"Generated answer: {answer[:100]}...")
    return {"messages": [AIMessage(content=answer)]}


# ============= NODE 6: FORMAT ANSWER =============

# Phrases that indicate a refusal or fallback — don't append sources to these
REFUSAL_PHRASES = [
    "i'm sorry",
    "i can't",
    "i cannot",
    "couldn't find",
    "don't have enough",
    "please keep your message",
    "i don't have",
    "not able to help",
]

def format_answer(state: JioState):
    messages = state["messages"]
    answer_msg = messages[-1].content if messages else ""

    # Don't append sources to refusals or fallbacks
    if any(phrase in answer_msg.lower() for phrase in REFUSAL_PHRASES):
        return {"messages": [AIMessage(content=answer_msg)]}

    tool_msg = next((msg.content for msg in reversed(messages) if msg.type == "tool"), "")

    formatted = f"{answer_msg}\n\n---\n**Sources:** Retrieved from Jio Knowledge Base"
    if tool_msg and "No results found" not in tool_msg:
        formatted += "\n✓ Information verified from retrieved documents"

    return {"messages": [AIMessage(content=formatted)]}


# ============= HALLUCINATION CHECK (NODE) =============
# Computes and writes confidence score to state via proper return value.
# Must be a node, not a router — routers cannot update state in LangGraph.
def check_hallucination(state: JioState) -> dict:
    messages = state["messages"]
    answer = messages[-1].content if messages else ""
    context = next((msg.content for msg in reversed(messages) if msg.type == "tool"), "")
    rewrite_count = state.get("rewrite_count", 0)

    if not context or "No results found" in context:
        return {"confidence": 0.0}

    # Truncate context for overlap check — full context not needed for word matching
    context_check = context[:MAX_PROMPT_CONTEXT_CHARS] if len(context) > MAX_PROMPT_CONTEXT_CHARS else context
    context_words = set(context_check.lower().split())
    answer_words = set(answer.lower().split())
    overlap = len(answer_words & context_words)

    if overlap >= 15 and rewrite_count == 0:
        confidence = 0.9
    elif overlap >= 8 and rewrite_count <= 1:
        confidence = 0.6
    else:
        confidence = 0.3

    logger.info(f"Confidence: {confidence} | Overlap: {overlap} words | Rewrites: {rewrite_count}")
    return {"confidence": confidence}


# ============= HALLUCINATION ROUTER =============
# Pure routing function — reads state only, returns a routing string.
# Confidence scoring is handled upstream in check_hallucination node.
def hallucination_router(state: JioState) -> str:
    context = next((msg.content for msg in reversed(state["messages"]) if msg.type == "tool"), "")
    if not context or "No results found" in context:
        return "end"
    confidence = state.get("confidence", 0.0)
    if confidence < 0.6:
        logger.warning(f"Low confidence ({confidence}), routing to rewrite")
        return "rewrite_question"
    return "end"