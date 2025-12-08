"""
Base Assistant implementation.

Provides a default implementation of AssistantInterface that coordinates
LLM, memory, abilities, and other components.
"""

from typing import Any, Dict, List, Optional

from bruno_core.interfaces.ability import AbilityInterface
from bruno_core.interfaces.assistant import AssistantInterface
from bruno_core.interfaces.llm import LLMInterface
from bruno_core.interfaces.memory import MemoryInterface
from bruno_core.models.ability import AbilityRequest, AbilityResponse
from bruno_core.models.context import ConversationContext
from bruno_core.models.message import Message, MessageRole
from bruno_core.models.response import ActionResult, ActionStatus, AssistantResponse
from bruno_core.utils.exceptions import BrunoError, RegistryError
from bruno_core.utils.logging import get_logger

logger = get_logger(__name__)


class BaseAssistant(AssistantInterface):
    """
    Base implementation of Bruno assistant.

    Coordinates LLM, memory, and abilities to process user messages and
    generate responses.

    Attributes:
        llm: Language model client
        memory: Memory storage backend
        abilities: Dictionary of registered abilities
        config: Assistant configuration
        initialized: Whether assistant is initialized

    Example:
        >>> assistant = BaseAssistant(llm=my_llm, memory=my_memory)
        >>> await assistant.initialize()
        >>> message = Message(role="user", content="Hello")
        >>> response = await assistant.process_message(message)
    """

    def __init__(
        self,
        llm: LLMInterface,
        memory: MemoryInterface,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize base assistant.

        Args:
            llm: LLM interface implementation
            memory: Memory interface implementation
            config: Optional configuration dictionary
        """
        self.llm = llm
        self.memory = memory
        self.config = config or {}
        self.abilities: Dict[str, AbilityInterface] = {}
        self.initialized = False

        logger.info("base_assistant_created", llm=llm.__class__.__name__)

    async def process_message(
        self,
        message: Message,
        context: Optional[ConversationContext] = None,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> AssistantResponse:
        """
        Process an incoming message and generate a response.

        Args:
            message: User message to process
            context: Optional conversation context
            user_id: Optional user ID (used if context not provided)
            conversation_id: Optional conversation ID (used if context not provided)

        Returns:
            Assistant response with text and actions

        Raises:
            BrunoError: If processing fails
        """
        if not self.initialized:
            raise BrunoError("Assistant not initialized. Call initialize() first.")

        try:
            logger.info(
                "processing_message",
                message_id=str(message.id),
                role=message.role.value,
            )

            # Get or create context
            if context is None:
                context = await self._get_or_create_context(
                    message, user_id=user_id, conversation_id=conversation_id
                )

            # Set conversation_id on message if provided
            if conversation_id and message.conversation_id is None:
                message.conversation_id = conversation_id

            # Add user message to context
            context.add_message(message)

            # Store message in memory
            await self.memory.store_message(message, context.conversation_id)

            # Check for ability requests
            ability_actions = await self._detect_abilities(message, context)

            # Generate LLM response
            llm_response = await self._generate_response(context)

            # Create assistant message
            assistant_message = Message(
                role=MessageRole.ASSISTANT,
                content=llm_response,
                conversation_id=context.conversation_id,
            )

            # Add to context and store
            context.add_message(assistant_message)
            await self.memory.store_message(assistant_message, context.conversation_id)

            # Execute abilities if detected
            action_results = []
            if ability_actions:
                action_results = await self._execute_abilities(ability_actions)

            # Build response
            response = AssistantResponse(
                text=llm_response,
                actions=action_results,
                success=True,
            )

            logger.info(
                "message_processed",
                response_id=str(response.id),
                actions_count=len(action_results),
            )

            return response

        except Exception as e:
            logger.error("message_processing_failed", error=str(e))
            raise BrunoError("Failed to process message", cause=e)

    async def register_ability(self, ability: AbilityInterface) -> None:
        """
        Register a new ability with the assistant.

        Args:
            ability: Ability instance to register

        Raises:
            RegistryError: If registration fails
        """
        try:
            metadata = ability.get_metadata()
            ability_name = metadata.name

            if ability_name in self.abilities:
                logger.warning("ability_already_registered", name=ability_name)
                return

            # Initialize the ability
            await ability.initialize()

            self.abilities[ability_name] = ability
            logger.info("ability_registered", name=ability_name)

        except Exception as e:
            raise RegistryError(
                f"Failed to register ability: {ability.__class__.__name__}",
                cause=e,
            )

    async def unregister_ability(self, ability_name: str) -> None:
        """
        Unregister an ability from the assistant.

        Args:
            ability_name: Name of ability to unregister

        Raises:
            RegistryError: If ability not found
        """
        if ability_name not in self.abilities:
            raise RegistryError(f"Ability not found: {ability_name}")

        ability = self.abilities[ability_name]
        await ability.shutdown()
        del self.abilities[ability_name]

        logger.info("ability_unregistered", name=ability_name)

    async def get_abilities(self) -> List[str]:
        """
        Get list of registered ability names.

        Returns:
            List of ability names
        """
        return list(self.abilities.keys())

    async def initialize(self) -> None:
        """
        Initialize the assistant and all its components.

        Raises:
            BrunoError: If initialization fails
        """
        if self.initialized:
            logger.warning("assistant_already_initialized")
            return

        try:
            logger.info("initializing_assistant")

            # Check LLM connection
            if not await self.llm.check_connection():
                raise BrunoError("LLM connection failed")

            # Additional initialization can be added here
            self.initialized = True
            logger.info("assistant_initialized")

        except Exception as e:
            raise BrunoError("Assistant initialization failed", cause=e)

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the assistant and cleanup resources.
        """
        logger.info("shutting_down_assistant")

        # Shutdown all abilities
        for ability_name, ability in list(self.abilities.items()):
            try:
                await ability.shutdown()
            except Exception as e:
                logger.error("ability_shutdown_failed", name=ability_name, error=str(e))

        self.abilities.clear()
        self.initialized = False
        logger.info("assistant_shutdown_complete")

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health status of assistant and its components.

        Returns:
            Dict with health status information
        """
        health = {
            "status": "healthy" if self.initialized else "not_initialized",
            "abilities": {},
            "abilities_count": len(self.abilities),
            "llm": "unknown",
            "memory": "unknown",
        }

        # Check LLM
        try:
            if await self.llm.check_connection():
                health["llm"] = "connected"
            else:
                health["llm"] = "disconnected"
                health["status"] = "degraded"
        except Exception:
            health["llm"] = "error"
            health["status"] = "unhealthy"

        # Check abilities
        abilities_health: Dict[str, Any] = {}
        for name, ability in self.abilities.items():
            try:
                ability_health = await ability.health_check()
                abilities_health[name] = ability_health
            except Exception as e:
                abilities_health[name] = {"status": "error", "error": str(e)}
        health["abilities"] = abilities_health

        return health

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get assistant metadata.

        Returns:
            Dict with metadata
        """
        return {
            "name": self.config.get("name", "Bruno"),
            "version": "0.1.0",
            "llm": self.llm.get_model_info(),
            "abilities": list(self.abilities.keys()),
            "initialized": self.initialized,
        }

    async def _get_or_create_context(
        self, message: Message, user_id: Optional[str] = None, conversation_id: Optional[str] = None
    ) -> ConversationContext:
        """
        Get existing context or create new one.

        Args:
            message: User message
            user_id: Optional user ID
            conversation_id: Optional conversation ID

        Returns:
            Conversation context
        """
        # Extract user_id from params or message metadata
        uid = user_id or message.metadata.get("user_id", "default")

        # Get context from memory
        context = await self.memory.get_context(uid, conversation_id)

        # Set conversation_id if provided
        if conversation_id:
            context.conversation_id = conversation_id

        return context

    async def _generate_response(self, context: ConversationContext) -> str:
        """
        Generate LLM response based on context.

        Args:
            context: Conversation context

        Returns:
            Generated response text
        """
        messages = context.messages
        response = await self.llm.generate(messages)
        return response

    async def _detect_abilities(
        self, message: Message, context: ConversationContext
    ) -> List[AbilityRequest]:
        """
        Detect if message requires ability execution.

        Args:
            message: User message
            context: Conversation context

        Returns:
            List of ability requests
        """
        # Simple keyword-based detection for now
        # In a full implementation, this would use LLM to detect intents
        requests = []

        content_lower = message.content.lower()

        # Check each registered ability
        for ability_name, ability in self.abilities.items():
            # This is a simple check - real implementation would be more sophisticated
            if ability_name in content_lower:
                request = AbilityRequest(
                    ability_name=ability_name,
                    action="execute",
                    parameters={"message": message.content},
                    user_id=context.user.user_id,
                    conversation_id=context.conversation_id,
                )
                requests.append(request)

        return requests

    async def _execute_abilities(self, requests: List[AbilityRequest]) -> List[ActionResult]:
        """
        Execute ability requests.

        Args:
            requests: List of ability requests

        Returns:
            List of action results
        """
        results = []

        for request in requests:
            try:
                ability = self.abilities.get(request.ability_name)
                if not ability:
                    results.append(
                        ActionResult(
                            action_type=request.ability_name,
                            status=ActionStatus.FAILED,
                            error=f"Ability not found: {request.ability_name}",
                        )
                    )
                    continue

                if not ability.can_handle(request):
                    results.append(
                        ActionResult(
                            action_type=request.ability_name,
                            status=ActionStatus.SKIPPED,
                            message="Ability cannot handle this request",
                        )
                    )
                    continue

                response: AbilityResponse = await ability.execute(request)

                results.append(
                    ActionResult(
                        action_type=request.ability_name,
                        status=(ActionStatus.SUCCESS if response.success else ActionStatus.FAILED),
                        message=response.message,
                        data=response.data,
                        error=response.error,
                    )
                )

            except Exception as e:
                logger.error(
                    "ability_execution_failed",
                    ability=request.ability_name,
                    error=str(e),
                )
                results.append(
                    ActionResult(
                        action_type=request.ability_name,
                        status=ActionStatus.FAILED,
                        error=str(e),
                    )
                )

        return results
