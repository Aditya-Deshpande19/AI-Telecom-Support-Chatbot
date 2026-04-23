import sqlite3
import logging
import uuid
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Inside the Docker container the named volume is mounted at /app/data (a directory),
# so the DB file must live at /app/data/chat_history.db.
# During local development /app/data does not exist, so we fall back to a file
# alongside this module (e.g. ./chat_history.db relative to the project root).
_DOCKER_DATA_DIR = "/app/data"
if os.path.isdir(_DOCKER_DATA_DIR):
    DB_FILE = os.path.join(_DOCKER_DATA_DIR, "chat_history.db")
else:
    DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_history.db")

# Ensure the parent directory exists before SQLite tries to create the file
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    # Enforce foreign key constraints on every connection
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables if they don't exist"""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        # Safe migration: add owner_id column if it doesn't exist yet (for existing DBs)
        try:
            conn.execute("ALTER TABLE conversations ADD COLUMN owner_id TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass  # Column already exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
            ON messages(conversation_id)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                query TEXT NOT NULL,
                response_time_ms REAL NOT NULL,
                confidence REAL NOT NULL,
                rewrite_count INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        conn.commit()
    logger.info("Chat history database initialized")


def create_conversation(owner_id: str = "") -> str:
    """Create a new conversation and return its ID"""
    conversation_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO conversations (conversation_id, owner_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (conversation_id, owner_id, now, now)
        )
        conn.commit()
    return conversation_id


def conversation_exists(conversation_id: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM conversations WHERE conversation_id = ?",
            (conversation_id,)
        ).fetchone()
    return row is not None


def save_message(conversation_id: str, role: str, content: str):
    """Save a single message to the database"""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        # Verify conversation exists before inserting to prevent orphaned rows
        row = conn.execute(
            "SELECT 1 FROM conversations WHERE conversation_id = ?",
            (conversation_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Cannot save message — conversation '{conversation_id}' does not exist")
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, now)
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE conversation_id = ?",
            (now, conversation_id)
        )
        conn.commit()


def save_messages_batch(conversation_id: str, messages: list[tuple[str, str]]):
    """Save multiple messages atomically in a single transaction.

    Each entry in *messages* is a (role, content) tuple.
    If any insert fails the entire batch is rolled back — no orphaned rows.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM conversations WHERE conversation_id = ?",
            (conversation_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Cannot save messages — conversation '{conversation_id}' does not exist")
        for role, content in messages:
            conn.execute(
                "INSERT INTO messages (conversation_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (conversation_id, role, content, now)
            )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE conversation_id = ?",
            (now, conversation_id)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def load_history(conversation_id: str) -> list[dict]:
    """Load full message history for a conversation"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT role, content, timestamp FROM messages WHERE conversation_id = ? ORDER BY id ASC",
            (conversation_id,)
        ).fetchall()
    return [{"role": row["role"], "content": row["content"], "timestamp": row["timestamp"]} for row in rows]


def get_conversation_summary(conversation_id: str, owner_id: str = "") -> Optional[dict]:
    """Get conversation metadata — enforces owner_id isolation if provided"""
    with get_connection() as conn:
        conv = conn.execute(
            "SELECT conversation_id, created_at, updated_at FROM conversations WHERE conversation_id = ? AND owner_id = ?",
            (conversation_id, owner_id)
        ).fetchone()
        if not conv:
            return None
        count = conn.execute(
            "SELECT COUNT(*) as total FROM messages WHERE conversation_id = ?",
            (conversation_id,)
        ).fetchone()
    return {
        "conversation_id": conv["conversation_id"],
        "created_at": conv["created_at"],
        "updated_at": conv["updated_at"],
        "message_count": count["total"]
    }


def delete_conversation(conversation_id: str, owner_id: str = "") -> bool:
    """Delete a conversation and all its messages — enforces owner_id isolation. Returns True if deleted."""
    with get_connection() as conn:
        # Only delete if owner matches
        convo_check = conn.execute(
            "SELECT 1 FROM conversations WHERE conversation_id = ? AND owner_id = ?",
            (conversation_id, owner_id)
        ).fetchone()
        if not convo_check:
            return False
        conn.execute(
            "DELETE FROM messages WHERE conversation_id = ?",
            (conversation_id,)
        )
        convo_result = conn.execute(
            "DELETE FROM conversations WHERE conversation_id = ? AND owner_id = ?",
            (conversation_id, owner_id)
        )
        conn.commit()
    return convo_result.rowcount > 0


def log_query(
    conversation_id: str,
    request_id: str,
    query: str,
    response_time_ms: float,
    confidence: float,
    rewrite_count: int,
):
    """Persist query metadata for analytics and debugging"""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO query_logs
               (conversation_id, request_id, query, response_time_ms, confidence, rewrite_count, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (conversation_id, request_id, query, response_time_ms, confidence, rewrite_count, now)
        )
        conn.commit()