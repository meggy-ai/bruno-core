"""Ollama LLM client for Bruno."""

import logging
from typing import Optional, List, Dict, Generator
import requests

from bruno.llm.base import BaseLLMClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OllamaClient(BaseLLMClient):
    """
    Client for interacting with Ollama LLM API.
    Handles conversation context and generates responses.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama2",
        system_prompt: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize Ollama client.
        
        Args:
            base_url: Ollama API base URL (default: http://localhost:11434)
            model: Model name to use (default: llama2)
            system_prompt: System prompt to set context (optional)
            timeout: Request timeout in seconds (default: 30)
        """
        super().__init__(model=model, system_prompt=system_prompt, timeout=timeout)
        self.base_url = base_url.rstrip('/')
        
        logger.info(f"Initialized OllamaClient (model: {model}, url: {base_url})")
        self._check_connection()
    
    def _check_connection(self) -> bool:
        """
        Check if Ollama server is accessible.
        
        Returns:
            True if server is accessible, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Connected to Ollama server")
                return True
            else:
                logger.warning(f"⚠️  Ollama server returned status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Cannot connect to Ollama server: {e}")
            logger.error(f"   Make sure Ollama is running: ollama serve")
            return False
    
    def list_models(self) -> List[str]:
        """
        List available models on Ollama server.
        
        Returns:
            List of model names
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            
            models_data = response.json()
            models = [model['name'] for model in models_data.get('models', [])]
            
            logger.info(f"Available models: {', '.join(models)}")
            return models
            
        except Exception as e:
            logger.error(f"Error listing models: {e}")
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
            logger.info(f"🤖 Calling Ollama - Model: {self.model}")
            
            # Make API request with performance options
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "num_ctx": 4096,  # Context window (reduce from 8192+ for faster inference)
                        "num_predict": 512,  # Max tokens to generate (concise responses)
                        "temperature": 0.7,  # Creativity (0.7 = balanced)
                        "top_p": 0.9,  # Nucleus sampling
                        "top_k": 40  # Top-k sampling
                    }
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Extract response
            result = response.json()
            assistant_message = result.get("message", {}).get("content", "").strip()
            
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
                logger.warning("⚠️  Empty response from Ollama")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"❌ Request timeout after {self.timeout}s")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error generating response: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
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
            
            # Make streaming API request with performance options
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "num_ctx": 4096,  # Context window
                        "num_predict": 512,  # Max tokens to generate
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "top_k": 40
                    }
                },
                stream=True,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            full_response = []
            
            # Process streaming chunks
            for line in response.iter_lines():
                if line:
                    try:
                        import json
                        chunk = json.loads(line)
                        
                        if chunk.get("done"):
                            break
                        
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            full_response.append(content)
                            yield content
                            
                    except json.JSONDecodeError:
                        continue
            
            # Add complete response to history
            if use_history and full_response:
                complete_response = "".join(full_response)
                self.conversation_history.append({
                    "role": "assistant",
                    "content": complete_response
                })
            
            logger.info("✅ Streaming response complete")
            
        except Exception as e:
            logger.error(f"❌ Error in streaming generation: {e}")
