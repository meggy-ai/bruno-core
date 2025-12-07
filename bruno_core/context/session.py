"""
Session Manager implementation.

Manages session lifecycle, state, and metadata.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from bruno_core.models.context import SessionContext
from bruno_core.utils.exceptions import SessionError
from bruno_core.utils.logging import get_logger

logger = get_logger(__name__)


class SessionManager:
    """
    Manages conversation session lifecycle and state.

    Features:
    - Session creation and termination
    - Session state tracking
    - Session metadata management
    - Active session monitoring
    - Session timeout handling

    Example:
        >>> manager = SessionManager()
        >>> session = await manager.start_session(user_id="user_123")
        >>> await manager.update_session(session.session_id, active=True)
        >>> await manager.end_session(session.session_id)
    """

    def __init__(self, session_timeout_seconds: int = 3600):
        """
        Initialize session manager.

        Args:
            session_timeout_seconds: Session timeout in seconds (default: 1 hour)
        """
        self.session_timeout_seconds = session_timeout_seconds
        self._sessions: Dict[str, SessionContext] = {}

        logger.info(
            "session_manager_initialized",
            timeout_seconds=session_timeout_seconds,
        )

    async def start_session(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionContext:
        """
        Start a new session.

        Args:
            user_id: User identifier
            conversation_id: Optional conversation identifier
            metadata: Optional session metadata

        Returns:
            SessionContext for the new session
        """
        try:
            session_id = str(uuid.uuid4())
            now = datetime.utcnow()

            session = SessionContext(
                session_id=session_id,
                user_id=user_id,
                conversation_id=conversation_id or f"conv_{session_id[:8]}",
                start_time=now,
                last_activity=now,
                active=True,
                metadata=metadata or {},
            )

            self._sessions[session_id] = session

            logger.info(
                "session_started",
                session_id=session_id,
                user_id=user_id,
                conversation_id=session.conversation_id,
            )

            return session

        except Exception as e:
            logger.error("session_start_failed", user_id=user_id, error=str(e))
            raise SessionError(
                "Failed to start session",
                details={"user_id": user_id},
                cause=e,
            )

    async def get_session(self, session_id: str) -> Optional[SessionContext]:
        """
        Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            SessionContext or None if not found
        """
        session = self._sessions.get(session_id)

        if session:
            # Check if session is expired
            if self._is_expired(session):
                logger.info("session_expired", session_id=session_id)
                await self.end_session(session_id)
                return None

        return session

    async def update_session(
        self,
        session_id: str,
        active: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Update session state.

        Args:
            session_id: Session identifier
            active: Optional active state
            metadata: Optional metadata to merge

        Raises:
            SessionError: If session not found
        """
        session = self._sessions.get(session_id)
        if not session:
            raise SessionError(
                "Session not found",
                details={"session_id": session_id},
            )

        try:
            # Update last activity
            session.last_activity = datetime.utcnow()

            # Update active state
            if active is not None:
                session.active = active

            # Merge metadata
            if metadata:
                session.metadata.update(metadata)

            logger.debug("session_updated", session_id=session_id)

        except Exception as e:
            logger.error("session_update_failed", session_id=session_id, error=str(e))
            raise SessionError(
                "Failed to update session",
                details={"session_id": session_id},
                cause=e,
            )

    async def end_session(self, session_id: str) -> None:
        """
        End a session.

        Args:
            session_id: Session identifier
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning("session_not_found_for_end", session_id=session_id)
            return

        try:
            session.active = False
            session.end_time = datetime.utcnow()

            # Calculate duration
            if session.start_time:
                duration = (session.end_time - session.start_time).total_seconds()
                session.metadata["duration_seconds"] = duration

            logger.info(
                "session_ended",
                session_id=session_id,
                duration=session.metadata.get("duration_seconds"),
            )

            # Remove from active sessions after a delay
            # (keep for a bit for potential queries)
            del self._sessions[session_id]

        except Exception as e:
            logger.error("session_end_failed", session_id=session_id, error=str(e))

    async def resume_session(self, session_id: str) -> SessionContext:
        """
        Resume an inactive session.

        Args:
            session_id: Session identifier

        Returns:
            Resumed SessionContext

        Raises:
            SessionError: If session not found or expired
        """
        session = self._sessions.get(session_id)
        if not session:
            raise SessionError(
                "Session not found",
                details={"session_id": session_id},
            )

        if self._is_expired(session):
            raise SessionError(
                "Session expired, cannot resume",
                details={"session_id": session_id},
            )

        session.active = True
        session.last_activity = datetime.utcnow()

        logger.info("session_resumed", session_id=session_id)
        return session

    def _is_expired(self, session: SessionContext) -> bool:
        """
        Check if session is expired.

        Args:
            session: Session to check

        Returns:
            True if expired
        """
        if not session.last_activity:
            return False

        elapsed = (datetime.utcnow() - session.last_activity).total_seconds()
        return elapsed > self.session_timeout_seconds

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        expired_sessions = [
            session_id
            for session_id, session in self._sessions.items()
            if self._is_expired(session)
        ]

        for session_id in expired_sessions:
            await self.end_session(session_id)

        if expired_sessions:
            logger.info("expired_sessions_cleaned", count=len(expired_sessions))

        return len(expired_sessions)

    def list_active_sessions(self, user_id: Optional[str] = None) -> list[str]:
        """
        List active session IDs.

        Args:
            user_id: Optional user filter

        Returns:
            List of active session IDs
        """
        sessions = [
            session_id
            for session_id, session in self._sessions.items()
            if session.active and (user_id is None or session.user_id == user_id)
        ]
        return sessions

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get session manager statistics.

        Returns:
            Dict with statistics
        """
        active_count = sum(1 for s in self._sessions.values() if s.active)
        expired_count = sum(1 for s in self._sessions.values() if self._is_expired(s))

        return {
            "total_sessions": len(self._sessions),
            "active_sessions": active_count,
            "inactive_sessions": len(self._sessions) - active_count,
            "expired_sessions": expired_count,
            "timeout_seconds": self.session_timeout_seconds,
        }
