"""
Google Gemini LLM service implementation.
"""

import json
from typing import Optional

from pydantic import ValidationError

from core.logging import get_logger
from schemas.intake import InputIntake
from schemas.llm import LLMOutput
from services.llm.base import BaseLLMService

logger = get_logger(__name__)


class GeminiLLMService(BaseLLMService):
    """
    Serviço LLM usando Google Gemini API.

    Integra com Google Gemini para processar requisições de prospecção
    e retornar consultas estruturadas em JSON.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Inicializa o serviço Gemini.

        Args:
            api_key: Chave de API do Google Gemini.

        Raises:
            ValueError: Se api_key não for fornecida.
        """
        if not api_key:
            raise ValueError("Gemini API key is required")

        super().__init__(api_key)

        try:
            import google.generativeai as genai

            self.client = genai.GenerativeModel("gemini-2.0-flash-exp")
            genai.configure(api_key=api_key)
            self._is_available = True
        except ImportError:
            logger.error("google-generativeai package not installed")
            self._is_available = False
        except Exception as exc:
            logger.error(f"Failed to initialize Gemini client: {exc}")
            self._is_available = False

    @property
    def provider_name(self) -> str:
        """
        Retorna nome do provedor Gemini.
        """
        return "gemini"

    def is_available(self) -> bool:
        """
        Verifica se Gemini está disponível.

        Returns:
            True se cliente foi inicializado com sucesso.
        """
        return self._is_available

    async def process_intake(
        self,
        intake: InputIntake,
        system_prompt: str,
    ) -> LLMOutput:
        """
        Processa entrada usando Google Gemini API.

        Envia o tema e objetivo para Gemini e recebe consultas
        estruturadas em JSON que são validadas como LLMOutput.

        Args:
            intake: Entrada do usuário.
            system_prompt: Prompt do sistema com instruções.

        Returns:
            Saída estruturada do Gemini validada como LLMOutput.

        Raises:
            Exception: Se Gemini API falhar ou resposta inválida.
        """
        if not self.is_available():
            raise RuntimeError("Gemini service is not available")

        # Construir mensagem de usuário
        user_message = self._build_user_message(intake)

        try:
            # Chamar Gemini API
            response = await self._call_gemini(system_prompt, user_message)

            # Extrair JSON da resposta
            json_output = self._extract_json(response)

            # Validar e retornar
            llm_output = LLMOutput(**json_output)

            logger.info(
                "gemini_processing_success",
                theme=intake.theme,
                has_queries=llm_output.has_any_queries(),
            )

            return llm_output

        except ValidationError as exc:
            logger.error(
                "gemini_validation_error",
                theme=intake.theme,
                error=str(exc),
            )
            raise ValueError(f"Gemini output validation failed: {exc}")
        except Exception as exc:
            logger.error(
                "gemini_processing_error",
                theme=intake.theme,
                error=str(exc),
            )
            raise

    def _build_user_message(self, intake: InputIntake) -> str:
        """
        Constrói mensagem do usuário para Gemini.

        Args:
            intake: Entrada do usuário.

        Returns:
            Mensagem formatada com tema, objetivo e palavras-chave.
        """
        message = f"Theme: {intake.theme}\n"

        if intake.objective:
            message += f"Objective: {intake.objective}\n"

        if intake.initial_keywords:
            message += f"Initial Keywords: {', '.join(intake.initial_keywords)}\n"

        return message

    async def _call_gemini(
        self,
        system_prompt: str,
        user_message: str,
    ) -> str:
        """
        Faz chamada à API Gemini.

        Args:
            system_prompt: Prompt do sistema.
            user_message: Mensagem do usuário.

        Returns:
            Resposta em texto do Gemini.

        Raises:
            Exception: Se chamada à API falhar.
        """
        try:
            # Combinar prompts
            full_prompt = f"{system_prompt}\n\n{user_message}"

            # Fazer chamada (síncrona pois API Gemini não é async)
            response = self.client.generate_content(full_prompt)

            return response.text

        except Exception as exc:
            logger.error(f"Gemini API call failed: {exc}")
            raise

    @staticmethod
    def _extract_json(response: str) -> dict:
        """
        Extrai JSON da resposta do Gemini.

        Procura por bloco JSON delimitado por ``` ou direto no texto.

        Args:
            response: Resposta em texto do Gemini.

        Returns:
            Dicionário com JSON extraído.

        Raises:
            ValueError: Se JSON não for encontrado ou inválido.
        """
        # Tentar extrair JSON entre ```json e ```
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                json_str = response[start:end].strip()
                return json.loads(json_str)

        # Tentar extrair JSON entre ``` e ```
        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end > start:
                json_str = response[start:end].strip()
                return json.loads(json_str)

        # Tentar parse direto
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            raise ValueError("Could not extract valid JSON from Gemini response")
