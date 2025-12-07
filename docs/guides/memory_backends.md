# Memory Backends Guide

This guide shows how to implement custom memory backends for bruno-core.

## Overview

Bruno-core uses the `MemoryInterface` to abstract conversation storage and retrieval. You can implement this interface to integrate any storage backend:

- **In-Memory**: Simple dict-based storage for development
- **SQL Databases**: PostgreSQL, MySQL, SQLite
- **NoSQL Databases**: MongoDB, DynamoDB
- **Vector Databases**: Pinecone, Weaviate, ChromaDB, Qdrant
- **Cache Systems**: Redis, Memcached
- **Hybrid**: Combine multiple backends

## MemoryInterface Contract

```python
from bruno_core.interfaces import MemoryInterface
from bruno_core.models import Message, MemoryEntry
from typing import Optional

class CustomMemory(MemoryInterface):
    async def store_message(
        self,
        message: Message,
        user_id: str,
        conversation_id: str
    ):
        """Store a message."""
        raise NotImplementedError
    
    async def retrieve_context(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        conversation_id: Optional[str] = None
    ) -> list[Message]:
        """Retrieve recent context."""
        raise NotImplementedError
    
    async def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> list[MemoryEntry]:
        """Search memories semantically."""
        raise NotImplementedError
    
    async def clear_conversation(self, user_id: str, conversation_id: str):
        """Clear a conversation."""
        raise NotImplementedError
```

## Basic Implementations

### In-Memory Storage

```python
from bruno_core.interfaces import MemoryInterface
from bruno_core.models import Message, MemoryEntry
from typing import Optional
from collections import defaultdict

class InMemoryStorage(MemoryInterface):
    """Simple dictionary-based storage."""
    
    def __init__(self):
        # Structure: {user_id: {conversation_id: [messages]}}
        self.storage = defaultdict(lambda: defaultdict(list))
    
    async def store_message(
        self,
        message: Message,
        user_id: str,
        conversation_id: str
    ):
        self.storage[user_id][conversation_id].append(message)
    
    async def retrieve_context(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        conversation_id: Optional[str] = None
    ) -> list[Message]:
        if conversation_id:
            messages = self.storage[user_id][conversation_id]
        else:
            # Merge all conversations
            messages = []
            for conv_messages in self.storage[user_id].values():
                messages.extend(conv_messages)
        
        return messages[-limit:]
    
    async def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> list[MemoryEntry]:
        results = []
        
        for conv_id, messages in self.storage[user_id].items():
            for msg in messages:
                if query.lower() in msg.content.lower():
                    entry = MemoryEntry(
                        id=f"{user_id}:{conv_id}:{msg.timestamp}",
                        user_id=user_id,
                        content=msg.content,
                        metadata={"conversation_id": conv_id},
                        timestamp=msg.timestamp
                    )
                    results.append(entry)
        
        return results[:limit]
    
    async def clear_conversation(self, user_id: str, conversation_id: str):
        if user_id in self.storage:
            self.storage[user_id].pop(conversation_id, None)
```

## SQL Database Implementations

### PostgreSQL Backend

```python
import asyncpg
from bruno_core.interfaces import MemoryInterface
from bruno_core.models import Message, MemoryEntry, MessageRole
from typing import Optional
from datetime import datetime

class PostgresMemory(MemoryInterface):
    """PostgreSQL-based memory storage."""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool = None
    
    async def initialize(self):
        """Create connection pool and tables."""
        self.pool = await asyncpg.create_pool(self.connection_string)
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    conversation_id VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    metadata JSONB,
                    INDEX idx_user_conv (user_id, conversation_id),
                    INDEX idx_timestamp (timestamp)
                )
            """)
    
    async def store_message(
        self,
        message: Message,
        user_id: str,
        conversation_id: str
    ):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO messages (user_id, conversation_id, role, content, timestamp, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, user_id, conversation_id, message.role.value, message.content,
                message.timestamp, message.metadata or {})
    
    async def retrieve_context(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        conversation_id: Optional[str] = None
    ) -> list[Message]:
        async with self.pool.acquire() as conn:
            if conversation_id:
                rows = await conn.fetch("""
                    SELECT role, content, timestamp, metadata
                    FROM messages
                    WHERE user_id = $1 AND conversation_id = $2
                    ORDER BY timestamp DESC
                    LIMIT $3
                """, user_id, conversation_id, limit)
            else:
                rows = await conn.fetch("""
                    SELECT role, content, timestamp, metadata
                    FROM messages
                    WHERE user_id = $1
                    ORDER BY timestamp DESC
                    LIMIT $2
                """, user_id, limit)
        
        messages = []
        for row in reversed(rows):
            messages.append(Message(
                role=MessageRole(row['role']),
                content=row['content'],
                timestamp=row['timestamp'],
                metadata=row['metadata']
            ))
        
        return messages
    
    async def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> list[MemoryEntry]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, content, timestamp, conversation_id
                FROM messages
                WHERE user_id = $1 AND content ILIKE $2
                ORDER BY timestamp DESC
                LIMIT $3
            """, user_id, f"%{query}%", limit)
        
        return [
            MemoryEntry(
                id=str(row['id']),
                user_id=user_id,
                content=row['content'],
                timestamp=row['timestamp'],
                metadata={"conversation_id": row['conversation_id']}
            )
            for row in rows
        ]
    
    async def clear_conversation(self, user_id: str, conversation_id: str):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM messages
                WHERE user_id = $1 AND conversation_id = $2
            """, user_id, conversation_id)
    
    async def shutdown(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
```

### SQLite Backend

```python
import aiosqlite
from bruno_core.interfaces import MemoryInterface
from bruno_core.models import Message, MemoryEntry, MessageRole
from datetime import datetime
import json

class SQLiteMemory(MemoryInterface):
    """SQLite-based memory storage."""
    
    def __init__(self, db_path: str = "bruno_memory.db"):
        self.db_path = db_path
        self.conn = None
    
    async def initialize(self):
        """Create database and tables."""
        self.conn = await aiosqlite.connect(self.db_path)
        
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT
            )
        """)
        
        await self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_conv
            ON messages(user_id, conversation_id)
        """)
        
        await self.conn.commit()
    
    async def store_message(
        self,
        message: Message,
        user_id: str,
        conversation_id: str
    ):
        await self.conn.execute("""
            INSERT INTO messages (user_id, conversation_id, role, content, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, conversation_id, message.role.value, message.content,
              message.timestamp.isoformat(), json.dumps(message.metadata or {})))
        
        await self.conn.commit()
    
    async def retrieve_context(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        conversation_id: Optional[str] = None
    ) -> list[Message]:
        if conversation_id:
            cursor = await self.conn.execute("""
                SELECT role, content, timestamp, metadata
                FROM messages
                WHERE user_id = ? AND conversation_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, conversation_id, limit))
        else:
            cursor = await self.conn.execute("""
                SELECT role, content, timestamp, metadata
                FROM messages
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))
        
        rows = await cursor.fetchall()
        
        messages = []
        for row in reversed(rows):
            messages.append(Message(
                role=MessageRole(row[0]),
                content=row[1],
                timestamp=datetime.fromisoformat(row[2]),
                metadata=json.loads(row[3])
            ))
        
        return messages
    
    async def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> list[MemoryEntry]:
        cursor = await self.conn.execute("""
            SELECT id, content, timestamp, conversation_id
            FROM messages
            WHERE user_id = ? AND content LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (user_id, f"%{query}%", limit))
        
        rows = await cursor.fetchall()
        
        return [
            MemoryEntry(
                id=str(row[0]),
                user_id=user_id,
                content=row[1],
                timestamp=datetime.fromisoformat(row[2]),
                metadata={"conversation_id": row[3]}
            )
            for row in rows
        ]
    
    async def clear_conversation(self, user_id: str, conversation_id: str):
        await self.conn.execute("""
            DELETE FROM messages
            WHERE user_id = ? AND conversation_id = ?
        """, (user_id, conversation_id))
        
        await self.conn.commit()
    
    async def shutdown(self):
        """Close database connection."""
        if self.conn:
            await self.conn.close()
```

## Vector Database Implementations

### ChromaDB Backend (Semantic Search)

```python
import chromadb
from chromadb.config import Settings
from bruno_core.interfaces import MemoryInterface, EmbeddingInterface
from bruno_core.models import Message, MemoryEntry, MessageRole
from typing import Optional
from datetime import datetime
import json

class ChromaMemory(MemoryInterface):
    """ChromaDB-based semantic memory."""
    
    def __init__(
        self,
        embedding_model: EmbeddingInterface,
        persist_directory: str = "./chroma_db"
    ):
        self.embedding_model = embedding_model
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_directory
        ))
        self.collection = self.client.get_or_create_collection("bruno_memories")
    
    async def store_message(
        self,
        message: Message,
        user_id: str,
        conversation_id: str
    ):
        # Generate embedding
        embedding = await self.embedding_model.embed(message.content)
        
        # Store in ChromaDB
        doc_id = f"{user_id}:{conversation_id}:{message.timestamp.isoformat()}"
        
        self.collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[message.content],
            metadatas=[{
                "user_id": user_id,
                "conversation_id": conversation_id,
                "role": message.role.value,
                "timestamp": message.timestamp.isoformat(),
                "metadata": json.dumps(message.metadata or {})
            }]
        )
    
    async def retrieve_context(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        conversation_id: Optional[str] = None
    ) -> list[Message]:
        # Generate query embedding
        query_embedding = await self.embedding_model.embed(query)
        
        # Build filter
        where_filter = {"user_id": user_id}
        if conversation_id:
            where_filter["conversation_id"] = conversation_id
        
        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where_filter
        )
        
        # Convert to messages
        messages = []
        for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
            messages.append(Message(
                role=MessageRole(metadata['role']),
                content=doc,
                timestamp=datetime.fromisoformat(metadata['timestamp']),
                metadata=json.loads(metadata['metadata'])
            ))
        
        return messages
    
    async def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> list[MemoryEntry]:
        query_embedding = await self.embedding_model.embed(query)
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where={"user_id": user_id}
        )
        
        memories = []
        for doc_id, doc, metadata in zip(
            results['ids'][0],
            results['documents'][0],
            results['metadatas'][0]
        ):
            memories.append(MemoryEntry(
                id=doc_id,
                user_id=user_id,
                content=doc,
                timestamp=datetime.fromisoformat(metadata['timestamp']),
                metadata={"conversation_id": metadata['conversation_id']}
            ))
        
        return memories
    
    async def clear_conversation(self, user_id: str, conversation_id: str):
        # Get all IDs for this conversation
        results = self.collection.get(
            where={
                "user_id": user_id,
                "conversation_id": conversation_id
            }
        )
        
        if results['ids']:
            self.collection.delete(ids=results['ids'])
```

## Redis Cache Backend

```python
import redis.asyncio as aioredis
from bruno_core.interfaces import MemoryInterface
from bruno_core.models import Message, MemoryEntry, MessageRole
from typing import Optional
import json

class RedisMemory(MemoryInterface):
    """Redis-based memory cache."""
    
    def __init__(self, redis_url: str = "redis://localhost"):
        self.redis_url = redis_url
        self.redis = None
    
    async def initialize(self):
        """Connect to Redis."""
        self.redis = await aioredis.from_url(self.redis_url)
    
    async def store_message(
        self,
        message: Message,
        user_id: str,
        conversation_id: str
    ):
        key = f"conv:{user_id}:{conversation_id}"
        
        message_data = {
            "role": message.role.value,
            "content": message.content,
            "timestamp": message.timestamp.isoformat(),
            "metadata": message.metadata or {}
        }
        
        # Add to list
        await self.redis.rpush(key, json.dumps(message_data))
        
        # Set expiration (optional)
        await self.redis.expire(key, 86400 * 30)  # 30 days
    
    async def retrieve_context(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        conversation_id: Optional[str] = None
    ) -> list[Message]:
        if conversation_id:
            key = f"conv:{user_id}:{conversation_id}"
            messages_data = await self.redis.lrange(key, -limit, -1)
        else:
            # Get all conversations for user
            pattern = f"conv:{user_id}:*"
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            
            messages_data = []
            for key in keys:
                messages_data.extend(await self.redis.lrange(key, -limit, -1))
        
        messages = []
        for data in messages_data:
            msg_dict = json.loads(data)
            messages.append(Message(
                role=MessageRole(msg_dict['role']),
                content=msg_dict['content'],
                timestamp=datetime.fromisoformat(msg_dict['timestamp']),
                metadata=msg_dict['metadata']
            ))
        
        return messages[-limit:]
    
    async def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> list[MemoryEntry]:
        # Redis doesn't have great full-text search
        # Consider RedisSearch for production
        pattern = f"conv:{user_id}:*"
        results = []
        
        async for key in self.redis.scan_iter(match=pattern):
            messages_data = await self.redis.lrange(key, 0, -1)
            
            for data in messages_data:
                msg_dict = json.loads(data)
                if query.lower() in msg_dict['content'].lower():
                    results.append(MemoryEntry(
                        id=f"{key}:{msg_dict['timestamp']}",
                        user_id=user_id,
                        content=msg_dict['content'],
                        timestamp=datetime.fromisoformat(msg_dict['timestamp']),
                        metadata={"conversation_id": key.split(":")[-1]}
                    ))
        
        return results[:limit]
    
    async def clear_conversation(self, user_id: str, conversation_id: str):
        key = f"conv:{user_id}:{conversation_id}"
        await self.redis.delete(key)
    
    async def shutdown(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
```

## Hybrid Backend

```python
from bruno_core.interfaces import MemoryInterface
from bruno_core.models import Message, MemoryEntry
from typing import Optional

class HybridMemory(MemoryInterface):
    """Combine cache and persistent storage."""
    
    def __init__(
        self,
        cache: MemoryInterface,  # e.g., Redis
        persistent: MemoryInterface  # e.g., PostgreSQL
    ):
        self.cache = cache
        self.persistent = persistent
    
    async def store_message(
        self,
        message: Message,
        user_id: str,
        conversation_id: str
    ):
        # Store in both
        await self.cache.store_message(message, user_id, conversation_id)
        await self.persistent.store_message(message, user_id, conversation_id)
    
    async def retrieve_context(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        conversation_id: Optional[str] = None
    ) -> list[Message]:
        # Try cache first
        messages = await self.cache.retrieve_context(
            user_id, query, limit, conversation_id
        )
        
        if not messages:
            # Fallback to persistent storage
            messages = await self.persistent.retrieve_context(
                user_id, query, limit, conversation_id
            )
        
        return messages
    
    async def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> list[MemoryEntry]:
        # Use persistent storage for search
        return await self.persistent.search_memories(user_id, query, limit)
    
    async def clear_conversation(self, user_id: str, conversation_id: str):
        await self.cache.clear_conversation(user_id, conversation_id)
        await self.persistent.clear_conversation(user_id, conversation_id)
```

## Usage Examples

### Basic Usage

```python
from bruno_core.base import BaseAssistant

# PostgreSQL
memory = PostgresMemory("postgresql://user:pass@localhost/bruno")
await memory.initialize()

# Create assistant
assistant = BaseAssistant(llm=llm, memory=memory)
await assistant.initialize()
```

### With Semantic Search

```python
from your_app.embeddings import YourEmbeddingModel

embedding_model = YourEmbeddingModel()
memory = ChromaMemory(embedding_model)

assistant = BaseAssistant(llm=llm, memory=memory)
```

### Hybrid Setup

```python
cache = RedisMemory("redis://localhost")
persistent = PostgresMemory("postgresql://localhost/bruno")

await cache.initialize()
await persistent.initialize()

memory = HybridMemory(cache=cache, persistent=persistent)

assistant = BaseAssistant(llm=llm, memory=memory)
```

## Best Practices

1. **Choose the Right Backend**:
   - Development: In-memory or SQLite
   - Production: PostgreSQL + Redis cache
   - Semantic search: ChromaDB, Pinecone, Weaviate

2. **Implement Proper Indexing**:
   - Index user_id + conversation_id
   - Index timestamps for chronological queries
   - Full-text search indexes when needed

3. **Handle Errors Gracefully**:
   - Connection failures
   - Timeout handling
   - Retry logic

4. **Manage Data Lifecycle**:
   - Implement TTL for temporary data
   - Archive old conversations
   - GDPR compliance (right to deletion)

5. **Monitor Performance**:
   - Query execution times
   - Cache hit rates
   - Storage usage

## Next Steps

- [Custom LLM Guide](./custom_llm.md)
- [Creating Abilities Guide](./creating_abilities.md)
- [API Reference](../api/interfaces.md)
