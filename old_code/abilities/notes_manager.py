"""
NotesManager - Simplified notes management with CRUD operations.

Workflow:
1. Create note with "Untitled" → ask user for name → ask for entries
2. Entries are numbered for easy reference
3. Notes displayed with name and ID for CRUD operations
4. No categories - all notes are equal
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


class NotesManager:
    """
    Manages notes with a simplified, user-friendly workflow.
    
    Features:
    - Simple note creation without categories
    - Numbered entries for easy reference
    - CRUD by note ID or name
    - Interactive workflow for note creation
    """
    
    def __init__(self, db_path: str = "bruno_notes.db"):
        """
        Initialize notes manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Connect and initialize
        self._connect()
        self._init_database()
        self.logger.info(f"✅ NotesManager initialized: {self.db_path}")
    
    def _connect(self):
        """Establish database connection."""
        try:
            self.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False  # Allow multi-threaded access
            )
            self.conn.row_factory = sqlite3.Row  # Access columns by name
            
            # Enable foreign key constraints (required for CASCADE DELETE)
            self.conn.execute("PRAGMA foreign_keys = ON")
            
            self.logger.info(f"📂 Connected to notes database: {self.db_path}")
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to database: {e}")
            raise
    
    def _init_database(self):
        """Create simplified database schema."""
        cursor = self.conn.cursor()
        
        try:
            # Table: notes (simplified - no categories)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    note_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_notes_name 
                ON notes(note_name)
            """)
            
            # Table: note_entries (renamed from note_items, simplified)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS note_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    note_id INTEGER NOT NULL,
                    entry_text TEXT NOT NULL,
                    entry_number INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_entries_note 
                ON note_entries(note_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_entries_number 
                ON note_entries(note_id, entry_number)
            """)
            
            self.conn.commit()
            self.logger.info("✅ Notes database schema initialized")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize database: {e}")
            raise
    
    
    # ==================== Note CRUD Operations ====================
    
    def create_note(
        self,
        note_name: str = "Untitled",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Create a new note.
        
        Args:
            note_name: Name of the note (defaults to "Untitled")
            metadata: Additional metadata as dictionary
            
        Returns:
            Note ID if successful, None otherwise
        """
        try:
            # Convert metadata to JSON
            metadata_json = json.dumps(metadata) if metadata else None
            
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO notes (note_name, metadata)
                VALUES (?, ?)
            """, (note_name, metadata_json))
            
            self.conn.commit()
            note_id = cursor.lastrowid
            
            self.logger.info(f"✅ Created note: {note_name} (ID: {note_id})")
            return note_id
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create note: {e}")
            return None
    
    def get_note_by_id(self, note_id: int) -> Optional[Dict[str, Any]]:
        """
        Get note by ID.
        
        Args:
            note_id: Note ID
            
        Returns:
            Note dictionary or None
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM notes WHERE id = ?
            """, (note_id,))
            
            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get note by ID: {e}")
            return None
    
    def get_note_by_name(self, note_name: str) -> Optional[Dict[str, Any]]:
        """
        Get note by name with fuzzy matching.
        
        Args:
            note_name: Name of the note
            
        Returns:
            Note dictionary or None
        """
        try:
            cursor = self.conn.cursor()
            
            # Normalize input (removes " note", " list" suffixes/prefixes)
            normalized_name = self._normalize_note_name(note_name)
            
            # Try exact match with normalized name
            cursor.execute("""
                SELECT * FROM notes 
                WHERE note_name = ?
                ORDER BY created_at DESC LIMIT 1
            """, (normalized_name,))
            
            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)
            
            # Try case-insensitive match
            cursor.execute("""
                SELECT * FROM notes 
                WHERE LOWER(note_name) = LOWER(?)
                ORDER BY created_at DESC LIMIT 1
            """, (normalized_name,))
            
            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)
            
            # Try partial match (contains)
            cursor.execute("""
                SELECT * FROM notes 
                WHERE LOWER(note_name) LIKE LOWER(?)
                ORDER BY created_at DESC LIMIT 1
            """, (f"%{normalized_name}%",))
            
            row = cursor.fetchone()
            if row:
                self.logger.info(f"📝 Found note via fuzzy match: '{row['note_name']}' for search '{note_name}'")
                return self._row_to_dict(row)
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get note by name: {e}")
            return None
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get note: {e}")
            return None
    
    def _normalize_note_name(self, note_name: str) -> str:
        """
        Normalize note name by removing common suffixes/prefixes.
        
        Args:
            note_name: Raw note name
            
        Returns:
            Cleaned note name
        """
        if not note_name:
            return note_name
        
        # Convert to lowercase for comparison
        name_lower = note_name.lower().strip()
        
        # Remove trailing " note" or " list"
        if name_lower.endswith(' note'):
            note_name = note_name[:-5].strip()
        elif name_lower.endswith(' list'):
            note_name = note_name[:-5].strip()
        
        # Remove leading "note " or "list "
        name_lower = note_name.lower().strip()
        if name_lower.startswith('note '):
            note_name = note_name[5:].strip()
        elif name_lower.startswith('list '):
            note_name = note_name[5:].strip()
        
        return note_name.strip()
    
    def get_note_by_id(self, note_id: int) -> Optional[Dict[str, Any]]:
        """
        Get note by ID.
        
        Args:
            note_id: Note ID
            
        Returns:
            Note dictionary or None
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
            
            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get note by ID: {e}")
            return None
    
    def list_notes(self) -> List[Dict[str, Any]]:
        """
        List all notes.
        
        Returns:
            List of note dictionaries with id, name, and entry count
        """
        try:
            cursor = self.conn.cursor()
            
            # Get all notes with entry count
            cursor.execute("""
                SELECT n.*, COUNT(e.id) as entry_count
                FROM notes n
                LEFT JOIN note_entries e ON n.id = e.note_id
                GROUP BY n.id
                ORDER BY n.created_at DESC
            """)
            
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
            
        except Exception as e:
            self.logger.error(f"❌ Failed to list notes: {e}")
            return []
    
    def update_note(
        self,
        note_id: int,
        note_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update note properties.
        
        Args:
            note_id: Note ID
            note_name: New name (optional)
            metadata: New metadata (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            updates = []
            params = []
            
            if note_name is not None:
                updates.append("note_name = ?")
                params.append(note_name)
            
            if metadata is not None:
                updates.append("metadata = ?")
                params.append(json.dumps(metadata))
            
            if not updates:
                return True  # Nothing to update
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(note_id)
            
            cursor = self.conn.cursor()
            query = f"UPDATE notes SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            
            self.conn.commit()
            self.logger.info(f"✅ Updated note ID: {note_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to update note: {e}")
            return False
    
    def delete_note(self, note_id: int) -> bool:
        """
        Delete note and all its items.
        
        Args:
            note_id: Note ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            
            self.conn.commit()
            self.logger.info(f"✅ Deleted note ID: {note_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to delete note: {e}")
            return False
    
    # ==================== Entry CRUD Operations ====================
    
    def add_entry(
        self,
        note_id: int,
        entry_text: str
    ) -> Optional[Tuple[int, int]]:
        """
        Add entry to note.
        
        Args:
            note_id: Note ID
            entry_text: Entry text
            
        Returns:
            Tuple of (entry_id, entry_number) if successful, None otherwise
        """
        try:
            cursor = self.conn.cursor()
            
            # Get next entry number
            cursor.execute("""
                SELECT COALESCE(MAX(entry_number), 0) + 1 FROM note_entries WHERE note_id = ?
            """, (note_id,))
            entry_number = cursor.fetchone()[0]
            
            # Insert entry
            cursor.execute("""
                INSERT INTO note_entries (note_id, entry_text, entry_number)
                VALUES (?, ?, ?)
            """, (note_id, entry_text, entry_number))
            
            self.conn.commit()
            entry_id = cursor.lastrowid
            
            # Update note's updated_at
            cursor.execute("""
                UPDATE notes SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (note_id,))
            self.conn.commit()
            
            self.logger.info(f"✅ Added entry #{entry_number} to note {note_id}: {entry_text[:50]}")
            return (entry_id, entry_number)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to add entry: {e}")
            return None
    
    def get_entries(self, note_id: int) -> List[Dict[str, Any]]:
        """
        Get all entries for a note.
        
        Args:
            note_id: Note ID
            
        Returns:
            List of entry dictionaries sorted by entry number
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM note_entries 
                WHERE note_id = ? 
                ORDER BY entry_number ASC
            """, (note_id,))
            
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get entries: {e}")
            return []
    
    def update_entry(
        self,
        entry_id: int,
        entry_text: Optional[str] = None,
        entry_number: Optional[int] = None
    ) -> bool:
        """
        Update entry properties.
        
        Args:
            entry_id: Entry ID
            entry_text: New text (optional)
            entry_number: New number (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            updates = []
            params = []
            
            if entry_text is not None:
                updates.append("entry_text = ?")
                params.append(entry_text)
            
            if entry_number is not None:
                updates.append("entry_number = ?")
                params.append(entry_number)
            
            if not updates:
                return True  # Nothing to update
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(entry_id)
            
            cursor = self.conn.cursor()
            query = f"UPDATE note_entries SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            
            # Update parent note's updated_at
            cursor.execute("""
                UPDATE notes SET updated_at = CURRENT_TIMESTAMP 
                WHERE id = (SELECT note_id FROM note_entries WHERE id = ?)
            """, (entry_id,))
            
            self.conn.commit()
            self.logger.info(f"✅ Updated entry ID: {entry_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to update entry: {e}")
            return False
    
    def delete_entry(self, entry_id: int) -> bool:
        """
        Delete entry from note.
        
        Args:
            entry_id: Entry ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            
            # Get note_id before deleting
            cursor.execute("SELECT note_id FROM note_entries WHERE id = ?", (entry_id,))
            row = cursor.fetchone()
            if not row:
                return False
            
            note_id = row[0]
            
            # Delete entry
            cursor.execute("DELETE FROM note_entries WHERE id = ?", (entry_id,))
            
            # Update parent note's updated_at
            cursor.execute("""
                UPDATE notes SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (note_id,))
            
            self.conn.commit()
            self.logger.info(f"✅ Deleted entry ID: {entry_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to delete entry: {e}")
            return False
    
    # ==================== Helper Methods ====================
    
    def get_note_with_entries(self, note_id: int) -> Optional[Dict[str, Any]]:
        """
        Get note with all its entries.
        
        Args:
            note_id: Note ID
            
        Returns:
            Note dictionary with 'entries' key containing list of entries
        """
        note = self.get_note_by_id(note_id)
        if note:
            note['entries'] = self.get_entries(note_id)
            return note
        return None
    
    def get_entry_by_number(self, note_id: int, entry_number: int) -> Optional[Dict[str, Any]]:
        """
        Get entry by its number within a note.
        
        Args:
            note_id: Note ID
            entry_number: Entry number (1-based)
            
        Returns:
            Entry dictionary if found, None otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT * FROM note_entries 
                WHERE note_id = ? AND entry_number = ?
            """, (note_id, entry_number))
            
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get entry by number: {e}")
            return None
    
    def search_notes(self, search_term: str) -> List[Dict[str, Any]]:
        """
        Search notes by name or entry text.
        
        Args:
            search_term: Search term
            
        Returns:
            List of matching notes
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT DISTINCT n.* FROM notes n
                LEFT JOIN note_entries e ON n.id = e.note_id
                WHERE n.note_name LIKE ? OR e.entry_text LIKE ?
                ORDER BY n.updated_at DESC
            """, (f"%{search_term}%", f"%{search_term}%"))
            
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
            
        except Exception as e:
            self.logger.error(f"❌ Failed to search notes: {e}")
            return []
    
    def get_entry_count(self, note_id: int) -> int:
        """
        Get number of entries in a note.
        
        Args:
            note_id: Note ID
            
        Returns:
            Number of entries
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM note_entries WHERE note_id = ?", (note_id,))
            return cursor.fetchone()[0]
        except Exception as e:
            self.logger.error(f"❌ Failed to get entry count: {e}")
            return 0
    
    def format_note_summary(self, note: Dict[str, Any], include_entries: bool = False) -> str:
        """
        Format note as readable summary text.
        
        Args:
            note: Note dictionary
            include_entries: Whether to include entry list
            
        Returns:
            Formatted string
        """
        note_id = note.get('id', 'N/A')
        note_name = note.get('note_name', 'Untitled')
        entry_count = note.get('entry_count', 0)
        
        summary = f"📝 Note #{note_id}: {note_name} ({entry_count} entries)"
        
        if include_entries and 'entries' in note:
            entries = note['entries']
            if entries:
                summary += "\n"
                for entry in entries:
                    num = entry.get('entry_number', '?')
                    text = entry.get('entry_text', '')
                    summary += f"\n  {num}. {text}"
        
        return summary
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """
        Convert SQLite row to dictionary.
        
        Args:
            row: SQLite row object
            
        Returns:
            Dictionary representation
        """
        result = dict(row)
        
        # Parse JSON metadata if present
        if 'metadata' in result and result['metadata']:
            try:
                result['metadata'] = json.loads(result['metadata'])
            except:
                pass
        
        return result
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.logger.info("📂 Closed notes database connection")
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()
