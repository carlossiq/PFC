"""
Ollama service for local LLM text generation and embeddings.

Uses local Ollama instance running on http://localhost:11434
"""

import asyncio
import json
from typing import Optional

import httpx

from core.logging import get_logger

logger = get_logger(__name__)

# Ollama configuration
OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_TEXT_MODEL = "qwen2.5:3b-instruct"
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"
REQUEST_TIMEOUT = 300  # 5 minutes for long generations


class OllamaService:
    """Service for interacting with local Ollama instance."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        text_model: str = DEFAULT_TEXT_MODEL,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    ):
        """
        Initialize Ollama service.

        Args:
            base_url: Ollama server URL
            text_model: Model for text generation
            embedding_model: Model for embeddings
        """
        self.base_url = base_url
        self.text_model = text_model
        self.embedding_model = embedding_model
        self.client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)

    async def health_check(self) -> bool:
        """
        Check if Ollama server is running.

        Returns:
            True if Ollama is accessible, False otherwise
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception as exc:
            logger.error(
                "ollama_health_check_failed",
                error=str(exc),
                base_url=self.base_url,
            )
            return False

    async def list_models(self) -> list[str]:
        """
        List available models in Ollama.

        Returns:
            List of model names
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            models = [model["name"] for model in data.get("models", [])]
            logger.info("ollama_models_listed", count=len(models))
            return models
        except Exception as exc:
            logger.error("ollama_list_models_failed", error=str(exc))
            return []

    async def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate text using Ollama model.

        Args:
            prompt: Input prompt
            model: Model name (uses default if None)
            system: System prompt
            temperature: Sampling temperature (0-1)
            top_p: Top-p sampling parameter
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        model = model or self.text_model

        # Build request payload
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "temperature": temperature,
            "top_p": top_p,
        }

        if system:
            payload["system"] = system

        if max_tokens:
            payload["num_predict"] = max_tokens

        try:
            logger.info(
                "ollama_generate_start",
                model=model,
                prompt_length=len(prompt),
            )

            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )

            response.raise_for_status()
            data = response.json()
            text = data.get("response", "")

            logger.info(
                "ollama_generate_success",
                model=model,
                response_length=len(text),
            )

            return text.strip()

        except httpx.ConnectError:
            logger.error(
                "ollama_connection_error",
                base_url=self.base_url,
            )
            raise Exception(
                f"Ollama server not running at {self.base_url}. "
                "Start it with: ollama serve"
            )
        except Exception as exc:
            logger.error(
                "ollama_generate_error",
                error=str(exc),
                model=model,
            )
            raise

    async def generate_text_with_context(
        self,
        prompt: str,
        context: str,
        model: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: Optional[int] = 1000,
    ) -> str:
        """
        Generate text with provided context.

        Args:
            prompt: Main prompt
            context: Context information
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Returns:
            Generated text
        """
        # Build a combined prompt with context
        full_prompt = f"""Contexto:
{context}

Tarefa:
{prompt}

Resposta (use apenas o contexto fornecido, não invente informações):"""

        return await self.generate_text(
            prompt=full_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def generate_embedding(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> list[float]:
        """
        Generate embedding for text using Ollama.

        Args:
            text: Input text
            model: Model name (uses embedding model if None)

        Returns:
            Embedding vector
        """
        model = model or self.embedding_model

        payload = {
            "model": model,
            "prompt": text,
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/api/embeddings",
                json=payload,
            )

            response.raise_for_status()
            data = response.json()
            embedding = data.get("embedding", [])

            if not embedding:
                logger.warning(
                    "ollama_embedding_empty",
                    model=model,
                    text_length=len(text),
                )

            return embedding

        except httpx.ConnectError:
            logger.error("ollama_connection_error", base_url=self.base_url)
            raise Exception(
                f"Ollama server not running at {self.base_url}. "
                "Start it with: ollama serve"
            )
        except Exception as exc:
            logger.error(
                "ollama_embedding_error",
                error=str(exc),
                model=model,
            )
            raise

    async def generate_embeddings_batch(
        self,
        texts: list[str],
        model: Optional[str] = None,
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts
            model: Model name

        Returns:
            List of embeddings
        """
        embeddings = []

        for text in texts:
            try:
                embedding = await self.generate_embedding(text, model)
                embeddings.append(embedding)
            except Exception as exc:
                logger.warning(
                    "ollama_batch_embedding_failed",
                    text_length=len(text),
                    error=str(exc),
                )
                # Return zero vector for failed embeddings
                embeddings.append([])

        return embeddings

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
