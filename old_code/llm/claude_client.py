"""Claude/Anthropic LLM client for Bruno."""

import logging
from typing import Optional, List, Generator

from bruno.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


class ClaudeClient(BaseLLMClient):
    """
    Client for interacting with Anthropic Claude API.
    Handles conversation context and generates responses.
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-sonnet-20240229",
        system_prompt: Optional[str] = None,
        timeout: int = 30,
        max_tokens: int = 4096
    ):
        """
        Initialize Claude client.
        
        Args:
            api_key: Anthropic API key
            model: Model name to use (default: claude-3-sonnet-20240229)
            system_prompt: System prompt to set context (optional)
            timeout: Request timeout in seconds (default: 30)
            max_tokens: Maximum tokens in response (default: 4096)
        """
        super().__init__(model=model, system_prompt=system_prompt, timeout=timeout)
        
        self.api_key = api_key
        self.max_tokens = max_tokens
        self._client = None
        self._system_prompt_text = system_prompt  # Store separately for Claude API
        
        self._init_client()
        logger.info(f"Initialized ClaudeClient (model: {model})")
        self._check_connection()
    
    def _init_client(self):
        """Initialize the Anthropic client."""
        try:
            from anthropic import Anthropic
            
            self._client = Anthropic(
                api_key=self.api_key,
                timeout=self.timeout
            )
        except ImportError:
            logger.error("❌ Anthropic package not installed. Run: pip install anthropic")
            raise ImportError("Anthropic package required. Install with: pip install anthropic")
    
    def _check_connection(self) -> bool:
        """
        Check if Anthropic API is accessible.
        
        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Make a minimal API call to verify the API key
            # Claude doesn't have a list models endpoint, so we just log success
            logger.info("✅ Claude client initialized")
            return True
        except Exception as e:
            logger.warning(f"⚠️  Claude connection check failed: {e}")
            return False
    
    def list_models(self) -> List[str]:
        """
        List available Claude models.
        
        Returns:
            List of model names (static list since API doesn't provide this)
        """
        # Claude doesn't have a list models endpoint, return known models
        models = [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022"
        ]
        logger.info(f"Available Claude models: {', '.join(models)}")
        return models
    
    def _get_messages_without_system(self) -> List[dict]:
        """
        Get conversation history without system messages.
        Claude handles system prompt separately.
        
        Returns:
            List of messages excluding system role
        """
        return [
            msg for msg in self.conversation_history 
            if msg.get("role") != "system"
        ]
    
    def generate(self, prompt: str, use_history: bool = True) -> Optional[str]:
        """
        Generate a response to the given prompt.
        
        Args:
            prompt: User prompt/question
            use_history: If True, include conversation history for context
        
        Returns:
            Generated response text, or None on error
        """
        try:
            # Add user message to history
            if use_history:
                self.conversation_history.append({
                    "role": "user",
                    "content": prompt
                })
                messages = self._get_messages_without_system()
            else:
                messages = [{"role": "user", "content": prompt}]
            
            logger.info(f"💭 Generating response to: '{prompt}'")
            logger.info(f"🤖 Calling Claude API - Model: {self.model}")
            
            # Build API request kwargs
            kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": messages
            }
            
            # Add system prompt if set
            if self._system_prompt_text:
                kwargs["system"] = self._system_prompt_text
            
            # Make API request
            response = self._client.messages.create(**kwargs)
            
            # Extract response
            assistant_message = response.content[0].text.strip()
            
            if assistant_message:
                # Add assistant response to history
                if use_history:
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": assistant_message
                    })
                
                logger.info(f"✅ Response generated ({len(assistant_message)} chars)")
                return assistant_message
            else:
                logger.warning("⚠️  Empty response from Claude")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error generating Claude response: {e}")
            return None
    
    def generate_streaming(self, prompt: str, use_history: bool = True) -> Generator[str, None, None]:
        """
        Generate a streaming response (yields chunks as they arrive).
        
        Args:
            prompt: User prompt/question
            use_history: If True, include conversation history for context
        
        Yields:
            Response chunks as they are generated
        """
        try:
            # Add user message to history
            if use_history:
                self.conversation_history.append({
                    "role": "user",
                    "content": prompt
                })
                messages = self._get_messages_without_system()
            else:
                messages = [{"role": "user", "content": prompt}]
            
            logger.info(f"💭 Generating streaming response to: '{prompt}'")
            
            # Build API request kwargs
            kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": messages
            }
            
            # Add system prompt if set
            if self._system_prompt_text:
                kwargs["system"] = self._system_prompt_text
            
            # Make streaming API request
            full_response = []
            
            with self._client.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    full_response.append(text)
                    yield text
            
            # Add complete response to history
            if use_history and full_response:
                complete_response = "".join(full_response)
                self.conversation_history.append({
                    "role": "assistant",
                    "content": complete_response
                })
            
            logger.info("✅ Streaming response complete")
            
        except Exception as e:
            logger.error(f"❌ Error in Claude streaming generation: {e}")
    
    def set_system_prompt(self, prompt: str):
        """
        Set or update system prompt.
        
        Args:
            prompt: System prompt text
        """
        # Store for Claude's separate system parameter
        self._system_prompt_text = prompt
        
        # Also call parent to maintain history consistency
        super().set_system_prompt(prompt)
