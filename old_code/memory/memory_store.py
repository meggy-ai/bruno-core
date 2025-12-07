"""
MemoryStore - SQLite database interface for conversation memory.
Handles all database operations for conversations, messages, and memories.
"""

import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any


class MemoryStore:
    """
    SQLite-based storage for conversations, messages, and memories.
    Handles short-term memory (STM) and long-term memory (LTM).
    """
    
    def __init__(self, db_path: str = "bruno_memory.db"):
        """
        Initialize memory store.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self._db_lock = threading.Lock()  # Thread-safe database access
        
        # Connect and initialize
        self._connect()
        self._init_database()
        self.logger.info(f"✅ MemoryStore initialized: {self.db_path}")
    
    def _connect(self):
        """Establish database connection with WAL mode for thread safety."""
        try:
            self.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,  # Allow multi-threaded access
                timeout=30.0  # Longer timeout for concurrent access
            )
            self.conn.row_factory = sqlite3.Row  # Access columns by name
            
            # Enable WAL mode for better concurrent access
            # WAL allows multiple readers + one writer simultaneously
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")  # Faster with WAL
            
            self.logger.info(f"📂 Connected to database: {self.db_path} (WAL mode)")
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to database: {e}")
            raise
    
    def _init_database(self):
        """Create database schema if not exists."""
        cursor = self.conn.cursor()
        
        try:
            # Table: conversations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    title TEXT,
                    message_count INTEGER DEFAULT 0,
                    compressed_summary TEXT,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_session 
                ON conversations(session_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_active 
                ON conversations(is_active)
            """)
            
            # Table: messages
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sequence_number INTEGER NOT NULL,
                    intent TEXT,
                    entities TEXT,
                    embedding_vector TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation 
                ON messages(conversation_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
                ON messages(timestamp)
            """)
            
            # Table: short_term_memory
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS short_term_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact TEXT NOT NULL,
                    source_message_id INTEGER,
                    confidence REAL DEFAULT 1.0,
                    category TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    relevance_score REAL DEFAULT 1.0,
                    FOREIGN KEY (source_message_id) REFERENCES messages(id) ON DELETE SET NULL
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_stm_category 
                ON short_term_memory(category)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_stm_relevance 
                ON short_term_memory(relevance_score)
            """)
            
            # Table: long_term_memory
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS long_term_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact TEXT NOT NULL UNIQUE,
                    category TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    importance REAL DEFAULT 1.0,
                    first_learned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    source_conversation_id INTEGER,
                    metadata TEXT,
                    FOREIGN KEY (source_conversation_id) REFERENCES conversations(id) ON DELETE SET NULL
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ltm_category 
                ON long_term_memory(category)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ltm_importance 
                ON long_term_memory(importance)
            """)
            
            # Table: user_profile
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    name TEXT,
                    preferred_name TEXT,
                    preferences TEXT,
                    music_preferences TEXT,
                    schedule_info TEXT,
                    personality_notes TEXT,
                    last_name_prompt TIMESTAMP,
                    conversation_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Initialize empty user profile if not exists
            cursor.execute("""
                INSERT OR IGNORE INTO user_profile (id, preferences) 
                VALUES (1, '{}')
            """)
            
            # Table: conversation_tags (for conversation search/management)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    tag TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_tags_conversation
                ON conversation_tags(conversation_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_tags_tag
                ON conversation_tags(tag)
            """)
            
            # Run migrations to add any missing columns
            self._run_migrations(cursor)
            
            self.conn.commit()
            self.logger.info("✅ Database schema initialized")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize database: {e}")
            self.conn.rollback()
            raise
    
    def _run_migrations(self, cursor):
        """
        Run database migrations to add missing columns.
        Safely adds columns if they don't exist.
        """
        try:
            # Get existing columns in user_profile table
            cursor.execute("PRAGMA table_info(user_profile)")
            existing_columns = {row[1] for row in cursor.fetchall()}
            
            # Migration: Add last_name_prompt column
            if 'last_name_prompt' not in existing_columns:
                self.logger.info("🔄 Migrating: Adding last_name_prompt column")
                cursor.execute("""
                    ALTER TABLE user_profile 
                    ADD COLUMN last_name_prompt TIMESTAMP
                """)
            
            # Migration: Add conversation_count column
            if 'conversation_count' not in existing_columns:
                self.logger.info("🔄 Migrating: Adding conversation_count column")
                cursor.execute("""
                    ALTER TABLE user_profile 
                    ADD COLUMN conversation_count INTEGER DEFAULT 0
                """)
            
            # Migration: Create conversation_tags table if missing
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_tags'")
            if not cursor.fetchone():
                self.logger.info("🔄 Migrating: Creating conversation_tags table")
                cursor.execute("""
                    CREATE TABLE conversation_tags (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id INTEGER NOT NULL,
                        tag TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                    )
                """)
                cursor.execute("""
                    CREATE INDEX idx_conversation_tags_conversation
                    ON conversation_tags(conversation_id)
                """)
                cursor.execute("""
                    CREATE INDEX idx_conversation_tags_tag
                    ON conversation_tags(tag)
                """)
                
            self.logger.info("✅ Migrations completed")
            
        except Exception as e:
            self.logger.warning(f"⚠️ Migration warning: {e}")
            # Don't raise - migrations are best-effort
    
    # ==================== Conversation Operations ====================
    
    def create_conversation(self, session_id: Optional[str] = None) -> int:
        """
        Create new conversation session.
        
        Args:
            session_id: Optional custom session ID (generates UUID if None)
            
        Returns:
            conversation_id (database ID)
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO conversations (session_id, started_at, is_active)
            VALUES (?, ?, 1)
        """, (session_id, datetime.now()))
        
        self.conn.commit()
        conversation_id = cursor.lastrowid
        
        self.logger.info(f"📝 Created conversation {conversation_id} (session: {session_id})")
        return conversation_id
    
    def get_conversation(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get conversation by session ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary with conversation data or None
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM conversations WHERE session_id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def get_conversation_by_id(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """Get conversation by database ID."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM conversations WHERE id = ?
        """, (conversation_id,))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def update_conversation(self, session_id: str, **kwargs):
        """
        Update conversation fields.
        
        Args:
            session_id: Session identifier
            **kwargs: Fields to update (title, message_count, compressed_summary, etc.)
        """
        if not kwargs:
            return
        
        # Build SET clause
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values()) + [session_id]
        
        cursor = self.conn.cursor()
        cursor.execute(f"""
            UPDATE conversations SET {set_clause} WHERE session_id = ?
        """, values)
        
        self.conn.commit()
        self.logger.debug(f"Updated conversation {session_id}: {kwargs}")
    
    def end_conversation(self, session_id: str):
        """Mark conversation as ended."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE conversations 
            SET ended_at = ?, is_active = 0 
            WHERE session_id = ?
        """, (datetime.now(), session_id))
        
        self.conn.commit()
        self.logger.info(f"🏁 Ended conversation: {session_id}")
    
    def get_active_conversation(self) -> Optional[Dict[str, Any]]:
        """Get currently active conversation."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM conversations 
            WHERE is_active = 1 
            ORDER BY started_at DESC 
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    # ==================== Message Operations ====================
    
    def add_message(
        self, 
        conversation_id: int, 
        role: str, 
        content: str,
        intent: Optional[str] = None,
        entities: Optional[Dict] = None
    ) -> int:
        """
        Add message to conversation.
        
        Args:
            conversation_id: Conversation database ID
            role: 'user' or 'assistant'
            content: Message text
            intent: Optional intent (timer_set, music_play, etc.)
            entities: Optional extracted entities (JSON)
            
        Returns:
            message_id
        """
        # Get next sequence number
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT MAX(sequence_number) FROM messages WHERE conversation_id = ?
        """, (conversation_id,))
        
        max_seq = cursor.fetchone()[0]
        sequence_number = (max_seq or 0) + 1
        
        # Serialize entities to JSON
        entities_json = json.dumps(entities) if entities else None
        
        # Insert message
        cursor.execute("""
            INSERT INTO messages (
                conversation_id, role, content, sequence_number, intent, entities
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (conversation_id, role, content, sequence_number, intent, entities_json))
        
        # Update conversation message count
        cursor.execute("""
            UPDATE conversations 
            SET message_count = message_count + 1 
            WHERE id = ?
        """, (conversation_id,))
        
        self.conn.commit()
        message_id = cursor.lastrowid
        
        self.logger.debug(f"💬 Added message {message_id} ({role}): {content[:50]}...")
        return message_id
    
    def get_messages(
        self, 
        conversation_id: int, 
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get messages from conversation.
        
        Args:
            conversation_id: Conversation database ID
            limit: Maximum number of messages (None = all)
            offset: Number of messages to skip
            
        Returns:
            List of message dictionaries
        """
        cursor = self.conn.cursor()
        
        query = """
            SELECT * FROM messages 
            WHERE conversation_id = ? 
            ORDER BY sequence_number ASC
        """
        
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        
        cursor.execute(query, (conversation_id,))
        
        messages = []
        for row in cursor.fetchall():
            msg = dict(row)
            # Deserialize entities
            if msg['entities']:
                msg['entities'] = json.loads(msg['entities'])
            messages.append(msg)
        
        return messages
    
    def get_recent_messages(self, conversation_id: int, count: int = 10) -> List[Dict[str, Any]]:
        """Get last N messages from conversation."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM messages 
            WHERE conversation_id = ? 
            ORDER BY sequence_number DESC 
            LIMIT ?
        """, (conversation_id, count))
        
        messages = []
        for row in cursor.fetchall():
            msg = dict(row)
            if msg['entities']:
                msg['entities'] = json.loads(msg['entities'])
            messages.append(msg)
        
        # Return in chronological order
        return list(reversed(messages))
    
    def get_message_count(self, conversation_id: int) -> int:
        """Get total message count for conversation."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM messages WHERE conversation_id = ?
        """, (conversation_id,))
        return cursor.fetchone()[0]
    
    def get_recent_messages_across_conversations(
        self,
        days: int = 7,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent messages from all conversations within the last N days.
        
        Args:
            days: Look back N days (default: 7)
            limit: Maximum messages to return (default: 100)
            
        Returns:
            List of message dictionaries, ordered chronologically
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT m.* FROM messages m
            JOIN conversations c ON m.conversation_id = c.id
            WHERE datetime(m.timestamp) >= datetime('now', '-' || ? || ' days')
            ORDER BY m.timestamp ASC
            LIMIT ?
        """, (days, limit))
        
        messages = []
        for row in cursor.fetchall():
            msg = dict(row)
            if msg['entities']:
                try:
                    msg['entities'] = json.loads(msg['entities'])
                except (json.JSONDecodeError, TypeError):
                    msg['entities'] = None
            messages.append(msg)
        
        return messages
    
    # ==================== Short-Term Memory Operations ====================
    
    def add_short_term_memory(
        self,
        fact: str,
        category: str,
        confidence: float = 1.0,
        source_message_id: Optional[int] = None
    ) -> int:
        """
        Add fact to short-term memory.
        
        Args:
            fact: Memory fact/content
            category: Category (music_preference, schedule, mood, etc.)
            confidence: Confidence score (0.0 to 1.0)
            source_message_id: Source message ID
            
        Returns:
            memory_id
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO short_term_memory (
                fact, category, confidence, source_message_id
            ) VALUES (?, ?, ?, ?)
        """, (fact, category, confidence, source_message_id))
        
        self.conn.commit()
        memory_id = cursor.lastrowid
        
        self.logger.info(f"🧠 Added STM {memory_id}: {fact[:50]}... ({category})")
        return memory_id
    
    def get_short_term_memories(
        self,
        category: Optional[str] = None,
        min_relevance: float = 0.0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get short-term memories.
        
        Args:
            category: Filter by category (None = all)
            min_relevance: Minimum relevance score
            limit: Maximum results
            
        Returns:
            List of memory dictionaries
        """
        cursor = self.conn.cursor()
        
        query = """
            SELECT * FROM short_term_memory 
            WHERE relevance_score >= ?
        """
        params = [min_relevance]
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        query += " ORDER BY relevance_score DESC, created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        memories = [dict(row) for row in cursor.fetchall()]
        return memories
    
    def update_memory_access(self, memory_id: int, table: str = 'short_term_memory'):
        """Update memory access timestamp and count."""
        with self._db_lock:
            cursor = self.conn.cursor()
            cursor.execute(f"""
                UPDATE {table} 
                SET last_accessed = ?, access_count = access_count + 1 
                WHERE id = ?
            """, (datetime.now(), memory_id))
            self.conn.commit()
    
    def batch_update_memory_access(self, memory_ids: List[int], table: str = 'short_term_memory'):
        """
        Batch update memory access timestamps and counts.
        More efficient than individual updates - uses single transaction.
        
        Args:
            memory_ids: List of memory IDs to update
            table: Table name ('short_term_memory' or 'long_term_memory')
        """
        if not memory_ids:
            return
        
        with self._db_lock:
            cursor = self.conn.cursor()
            now = datetime.now()
            
            # Batch update all memories in single transaction
            for memory_id in memory_ids:
                cursor.execute(f"""
                    UPDATE {table} 
                    SET last_accessed = ?, access_count = access_count + 1 
                    WHERE id = ?
                """, (now, memory_id))
            
            # Single commit for all updates
            self.conn.commit()
    
    def decay_short_term_memories(self, decay_rate: float = 0.1):
        """
        Decay relevance scores of short-term memories.
        
        Args:
            decay_rate: Decay factor per day (0.0 to 1.0)
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE short_term_memory 
            SET relevance_score = relevance_score * (1 - ?)
            WHERE relevance_score > 0
        """, (decay_rate,))
        
        self.conn.commit()
        affected = cursor.rowcount
        self.logger.debug(f"📉 Decayed {affected} STM entries")
    
    def prune_old_short_term_memories(self, max_age_days: int = 7, min_relevance: float = 0.3):
        """
        Delete old or low-relevance short-term memories.
        
        Args:
            max_age_days: Delete memories older than this
            min_relevance: Delete memories below this relevance
        """
        cursor = self.conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        cursor.execute("""
            DELETE FROM short_term_memory 
            WHERE created_at < ? OR relevance_score < ?
        """, (cutoff_date, min_relevance))
        
        self.conn.commit()
        deleted = cursor.rowcount
        self.logger.info(f"🗑️  Pruned {deleted} old STM entries")
    
    def delete_short_term_memory(self, memory_id: int):
        """Delete a specific short-term memory by ID."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM short_term_memory WHERE id = ?", (memory_id,))
        self.conn.commit()
        self.logger.debug(f"🗑️  Deleted STM entry: {memory_id}")
    
    # ==================== Long-Term Memory Operations ====================
    
    def add_long_term_memory(
        self,
        fact: str,
        category: str,
        importance: float = 1.0,
        confidence: float = 1.0,
        source_conversation_id: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[int]:
        """
        Add fact to long-term memory.
        
        Args:
            fact: Memory fact/content (must be unique)
            category: Category (profile, preference, habit, knowledge)
            importance: Importance score (0.0 to 1.0)
            confidence: Confidence score (0.0 to 1.0)
            source_conversation_id: Source conversation ID
            metadata: Additional metadata (JSON)
            
        Returns:
            memory_id or None if fact already exists
        """
        cursor = self.conn.cursor()
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        try:
            cursor.execute("""
                INSERT INTO long_term_memory (
                    fact, category, importance, confidence, 
                    source_conversation_id, metadata
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (fact, category, importance, confidence, source_conversation_id, metadata_json))
            
            self.conn.commit()
            memory_id = cursor.lastrowid
            
            self.logger.info(f"💎 Added LTM {memory_id}: {fact[:50]}... ({category})")
            return memory_id
            
        except sqlite3.IntegrityError:
            # Fact already exists - update instead
            self.logger.debug(f"Fact already exists, updating: {fact[:50]}...")
            self.update_long_term_memory(fact, importance=importance, confidence=confidence)
            return None
    
    def get_long_term_memories(
        self,
        category: Optional[str] = None,
        min_importance: float = 0.0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get long-term memories.
        
        Args:
            category: Filter by category (None = all)
            min_importance: Minimum importance score
            limit: Maximum results
            
        Returns:
            List of memory dictionaries
        """
        cursor = self.conn.cursor()
        
        query = """
            SELECT * FROM long_term_memory 
            WHERE importance >= ?
        """
        params = [min_importance]
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        query += " ORDER BY importance DESC, access_count DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        memories = []
        for row in cursor.fetchall():
            mem = dict(row)
            if mem['metadata']:
                mem['metadata'] = json.loads(mem['metadata'])
            memories.append(mem)
        
        return memories
    
    def update_long_term_memory(self, fact: str, **kwargs):
        """
        Update long-term memory fields.
        
        Args:
            fact: Fact to update (unique identifier)
            **kwargs: Fields to update
        """
        if not kwargs:
            return
        
        # Always update last_updated
        kwargs['last_updated'] = datetime.now()
        
        # Serialize metadata if present
        if 'metadata' in kwargs and kwargs['metadata']:
            kwargs['metadata'] = json.dumps(kwargs['metadata'])
        
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values()) + [fact]
        
        cursor = self.conn.cursor()
        cursor.execute(f"""
            UPDATE long_term_memory SET {set_clause} WHERE fact = ?
        """, values)
        
        self.conn.commit()
        self.logger.debug(f"Updated LTM: {fact[:30]}...")
    
    def delete_long_term_memory(self, fact: str):
        """Delete long-term memory by fact."""
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM long_term_memory WHERE fact = ?
        """, (fact,))
        self.conn.commit()
        self.logger.info(f"Deleted LTM: {fact[:50]}...")
    
    # ==================== User Profile Operations ====================
    
    def get_user_profile(self) -> Dict[str, Any]:
        """Get user profile (single row)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM user_profile WHERE id = 1")
        
        row = cursor.fetchone()
        if row:
            profile = dict(row)
            # Deserialize JSON fields
            for field in ['preferences', 'music_preferences', 'schedule_info', 'personality_notes']:
                if profile.get(field):
                    try:
                        profile[field] = json.loads(profile[field])
                    except json.JSONDecodeError:
                        profile[field] = {}
            return profile
        
        # Return empty profile if not found
        return {
            'id': 1,
            'name': None,
            'preferred_name': None,
            'preferences': {},
            'music_preferences': {},
            'schedule_info': {},
            'personality_notes': {}
        }
    
    def update_user_profile(self, **kwargs):
        """
        Update user profile fields.
        
        Args:
            **kwargs: Fields to update (name, preferences, etc.)
        """
        if not kwargs:
            return
        
        # Serialize JSON fields
        for field in ['preferences', 'music_preferences', 'schedule_info', 'personality_notes']:
            if field in kwargs and isinstance(kwargs[field], dict):
                kwargs[field] = json.dumps(kwargs[field])
        
        # Always update updated_at
        kwargs['updated_at'] = datetime.now()
        
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values())
        
        cursor = self.conn.cursor()
        cursor.execute(f"""
            UPDATE user_profile SET {set_clause} WHERE id = 1
        """, values)
        
        self.conn.commit()
        self.logger.info(f"👤 Updated user profile: {list(kwargs.keys())}")
    
    def track_name_prompt(self):
        """Record that we asked the user for their name."""
        self.update_user_profile(last_name_prompt=datetime.now())
        self.logger.info("📝 Tracked name prompt")
    
    def should_ask_for_name(
        self,
        cooldown_days: int = 30,
        min_messages: int = 6
    ) -> bool:
        """
        Determine if we should ask user for their name.
        
        Args:
            cooldown_days: Days to wait before asking again
            min_messages: Minimum messages in current conversation
            
        Returns:
            True if should ask, False otherwise
        """
        profile = self.get_user_profile()
        
        # Already have name
        if profile.get('name'):
            return False
        
        # Check cooldown
        last_asked = profile.get('last_name_prompt')
        if last_asked:
            if isinstance(last_asked, str):
                last_asked = datetime.fromisoformat(last_asked)
            days_since = (datetime.now() - last_asked).days
            if days_since < cooldown_days:
                return False
        
        return True
    
    def increment_conversation_count(self):
        """Increment the conversation count in user profile."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE user_profile 
            SET conversation_count = conversation_count + 1,
                updated_at = ?
            WHERE id = 1
        """, (datetime.now(),))
        self.conn.commit()
    
    # ==================== Conversation Search & Management ====================
    
    def add_conversation_tags(self, conversation_id: int, tags: List[str]):
        """
        Add tags to a conversation.
        
        Args:
            conversation_id: Conversation ID
            tags: List of tags to add
        """
        cursor = self.conn.cursor()
        
        # Insert tags
        for tag in tags:
            cursor.execute("""
                INSERT INTO conversation_tags (conversation_id, tag)
                VALUES (?, ?)
            """, (conversation_id, tag.lower().strip()))
        
        self.conn.commit()
        self.logger.info(f"🏷️  Added {len(tags)} tags to conversation {conversation_id}")
    
    def get_conversation_tags(self, conversation_id: int) -> List[str]:
        """
        Get tags for a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            List of tags
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT tag FROM conversation_tags 
            WHERE conversation_id = ?
            ORDER BY created_at DESC
        """, (conversation_id,))
        
        return [row[0] for row in cursor.fetchall()]
    
    def search_conversations(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search conversations by various criteria.
        
        Args:
            query: Text search in title, summary, or messages
            tags: Filter by tags
            date_from: Start date filter
            date_to: End date filter
            limit: Maximum results
            
        Returns:
            List of matching conversations
        """
        cursor = self.conn.cursor()
        
        conditions = []
        params = []
        
        # Base query
        sql = """
            SELECT DISTINCT c.*, 
                   GROUP_CONCAT(DISTINCT ct.tag) as tags
            FROM conversations c
            LEFT JOIN conversation_tags ct ON c.id = ct.conversation_id
        """
        
        # Add message search if query provided
        if query:
            sql += """
                LEFT JOIN messages m ON c.id = m.conversation_id
            """
            conditions.append("""
                (c.title LIKE ? OR c.compressed_summary LIKE ? OR m.content LIKE ?)
            """)
            search_term = f"%{query}%"
            params.extend([search_term, search_term, search_term])
        
        # Add tag filter
        if tags:
            tag_conditions = " OR ".join(["ct.tag = ?" for _ in tags])
            conditions.append(f"({tag_conditions})")
            params.extend(tags)
        
        # Add date filters
        if date_from:
            conditions.append("c.started_at >= ?")
            params.append(date_from)
        
        if date_to:
            conditions.append("c.started_at <= ?")
            params.append(date_to)
        
        # Build WHERE clause
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        
        # Group and order
        sql += """
            GROUP BY c.id
            ORDER BY c.started_at DESC
            LIMIT ?
        """
        params.append(limit)
        
        cursor.execute(sql, params)
        
        results = []
        for row in cursor.fetchall():
            conv = dict(row)
            # Parse tags string back to list
            if conv.get('tags'):
                conv['tags'] = conv['tags'].split(',')
            else:
                conv['tags'] = []
            results.append(conv)
        
        return results
    
    def get_recent_conversations(
        self,
        limit: int = 10,
        date_from: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent conversations.
        
        Args:
            limit: Maximum number of conversations
            date_from: Optional start date filter
            
        Returns:
            List of conversations
        """
        cursor = self.conn.cursor()
        
        sql = "SELECT * FROM conversations WHERE 1=1"
        params = []
        
        if date_from:
            sql += " AND started_at >= ?"
            params.append(date_from)
        
        sql += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def delete_conversation(self, conversation_id: int):
        """
        Delete a conversation and all associated data.
        
        Args:
            conversation_id: ID of conversation to delete
        """
        cursor = self.conn.cursor()
        
        # Foreign keys will cascade delete messages, tags, etc.
        cursor.execute("""
            DELETE FROM conversations WHERE id = ?
        """, (conversation_id,))
        
        self.conn.commit()
        self.logger.info(f"🗑️  Deleted conversation {conversation_id}")
    
    # ==================== Utility Methods ====================
    
    def get_statistics(self) -> Dict[str, int]:
        """Get database statistics."""
        cursor = self.conn.cursor()
        
        stats = {}
        
        # Count conversations
        cursor.execute("SELECT COUNT(*) FROM conversations")
        stats['total_conversations'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM conversations WHERE is_active = 1")
        stats['active_conversations'] = cursor.fetchone()[0]
        
        # Count messages
        cursor.execute("SELECT COUNT(*) FROM messages")
        stats['total_messages'] = cursor.fetchone()[0]
        
        # Count memories
        cursor.execute("SELECT COUNT(*) FROM short_term_memory")
        stats['short_term_memories'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM long_term_memory")
        stats['long_term_memories'] = cursor.fetchone()[0]
        
        return stats
    
    def close(self):
        """Close database connection after ensuring all pending writes complete."""
        if self.conn:
            # Wait for any background writes to complete
            # Acquire and release lock to ensure no writes in progress
            with self._db_lock:
                self.conn.close()
                self.logger.info("👋 MemoryStore closed")
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()
