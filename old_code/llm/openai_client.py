"""OpenAI/GPT LLM client for Bruno."""

import logging
from typing import Optional, List, Generator

from bruno.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLMClient):
    """
    Client for interacting with OpenAI GPT API.
    Handles conversation context and generates responses.
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-3.5-turbo",
        system_prompt: Optional[str] = None,
        timeout: int = 30,
        base_url: Optional[str] = None
    ):
        """
        Initialize OpenAI client.
        
        Args:
            api_key: OpenAI API key
            model: Model name to use (default: gpt-3.5-turbo)
            system_prompt: System prompt to set context (optional)
            timeout: Request timeout in seconds (default: 30)
            base_url: Optional custom base URL (for Azure OpenAI or compatible APIs)
        """
        super().__init__(model=model, system_prompt=system_prompt, timeout=timeout)
        
        self.api_key = api_key
        self.base_url = base_url
        self._client = None
        
        self._init_client()
        logger.info(f"Initialized OpenAIClient (model: {model})")
        self._check_connection()
    
    def _init_client(self):
        """Initialize the OpenAI client."""
        try:
            from openai import OpenAI
            
            kwargs = {"api_key": self.api_key, "timeout": self.timeout}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            
            self._client = OpenAI(**kwargs)
        except ImportError:
            logger.error("❌ OpenAI package not installed. Run: pip install openai")
            raise ImportError("OpenAI package required. Install with: pip install openai")
    
    def _check_connection(self) -> bool:
        """
        Check if OpenAI API is accessible.
        
        Returns:
            True if API is accessible, False otherwise
        """
        try:
            # Try listing models to verify API key
            self._client.models.list()
            logger.info("✅ Connected to OpenAI API")
            return True
        except Exception as e:
            logger.warning(f"⚠️  OpenAI connection check failed: {e}")
            return False
    
    def list_models(self) -> List[str]:
        """
        List available models from OpenAI.
        
        Returns:
            List of model names
        """
        try:
            models = self._client.models.list()
            model_names = [model.id for model in models.data if 'gpt' in model.id.lower()]
            logger.info(f"Available OpenAI models: {', '.join(model_names[:5])}...")
            return model_names
        except Exception as e:
            logger.error(f"Error listing OpenAI models: {e}")
            return []
    
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
                messages = self.conversation_history
            else:
                messages = [{"role": "user", "content": prompt}]
            
            logger.info(f"💭 Generating response to: '{prompt}'")
            logger.info(f"🤖 Calling OpenAI API - Model: {self.model}")
            
            # Make API request
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                timeout=self.timeout
            )
            
            # Extract response
            assistant_message = response.choices[0].message.content.strip()
            
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
                logger.warning("⚠️  Empty response from OpenAI")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error generating OpenAI response: {e}")
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
                messages = self.conversation_history
            else:
                messages = [{"role": "user", "content": prompt}]
            
            logger.info(f"💭 Generating streaming response to: '{prompt}'")
            
            # Make streaming API request
            stream = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                timeout=self.timeout
            )
            
            full_response = []
            
            # Process streaming chunks
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response.append(content)
                    yield content
            
            # Add complete response to history
            if use_history and full_response:
                complete_response = "".join(full_response)
                self.conversation_history.append({
                    "role": "assistant",
                    "content": complete_response
                })
            
            logger.info("✅ Streaming response complete")
            
        except Exception as e:
            logger.error(f"❌ Error in OpenAI streaming generation: {e}")
