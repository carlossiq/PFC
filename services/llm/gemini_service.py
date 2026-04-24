"""
Google Gemini LLM service implementation.
"""

import json
from typing import Any, Optional

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

    def __init__(
        self, api_key: Optional[str] = None, model: Optional[str] = None
    ) -> None:
        """
        Inicializa o serviço Gemini.

        Args:
            api_key: Chave de API do Google Gemini.
            model: Versão do modelo Gemini (ex: 'gemini-2.0-flash-exp').
                   Se None, usa o padrão da configuração.

        Raises:
            ValueError: Se api_key não for fornecida.
        """
        if not api_key:
            raise ValueError("Gemini API key is required")

        super().__init__(api_key)

        # Se model não for fornecido, tenta obter da configuração
        if model is None:
            from core.config import settings

            model = settings.llm_gemini_model

        self.model = model

        try:
            import google.generativeai as genai

            self.client = genai.GenerativeModel(self.model)
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

            # Log raw response para debugging
            logger.info(
                "gemini_raw_response",
                theme=intake.theme,
                response_length=len(response),
                response_preview=response[:500] if response else "EMPTY",
            )

            # Extrair JSON da resposta
            try:
                json_output = self._extract_json(response)
            except ValueError as parse_exc:
                logger.error(
                    "gemini_json_parse_failed",
                    theme=intake.theme,
                    error=str(parse_exc),
                    raw_response=response,
                )
                raise

            # Log JSON parseado ANTES de converter para LLMOutput
            logger.info(
                "gemini_json_parsed",
                theme=intake.theme,
                json_keys=list(json_output.keys()),
                abstract_exists="ABSTRACT" in json_output,
                title_exists="TITLE" in json_output,
                json_preview=str(json_output)[:500],
            )

            # Converter chaves de UPPERCASE para lowercase (Gemini usa UPPERCASE)
            json_output_normalized = {k.lower(): v for k, v in json_output.items()}

            logger.info(
                "gemini_json_keys_normalized",
                original_keys=list(json_output.keys()),
                normalized_keys=list(json_output_normalized.keys()),
            )

            # Validar e retornar
            llm_output = LLMOutput(**json_output_normalized)

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

    async def call_raw_json(
        self,
        prompt: str,
        user_input: str,
    ) -> dict[str, Any]:
        """
        Chama Gemini e retorna JSON bruto parseado.

        Diferente de process_intake que retorna LLMOutput estruturado,
        este método retorna exatamente o JSON que a Gemini gerou.

        Args:
            prompt: Prompt do sistema com instruções.
            user_input: Entrada do usuário.

        Returns:
            Dicionário com resposta JSON bruta da Gemini.

        Raises:
            Exception: Se a chamada Gemini falhar ou JSON for inválido.
        """
        if not self.is_available():
            raise RuntimeError("Gemini service is not available")

        try:
            response = await self._call_gemini(prompt, user_input)

            logger.info(
                "gemini_raw_json_response",
                response_length=len(response),
            )

            json_output = self._extract_json(response)

            logger.info(
                "gemini_raw_json_extracted",
                json_keys=list(json_output.keys()),
            )

            return json_output

        except Exception as exc:
            logger.error(
                "gemini_raw_json_error",
                error=str(exc),
            )
            raise

    def _build_user_message(self, intake: InputIntake) -> str:
        """
        Constrói mensagem do usuário para Gemini.

        Args:
            intake: Entrada do usuário.

        Returns:
            Mensagem formatada com tema, descrição, área de estudo e palavras-chave.
        """
        message = f"Theme: {intake.theme}\n"

        if intake.description:
            message += f"Description: {intake.description}\n"

        if intake.area_of_study:
            message += f"Area of Study: {intake.area_of_study}\n"

        if intake.keywords:
            message += f"Keywords: {', '.join(intake.keywords)}\n"

        return message

    async def _call_gemini(
        self,
        system_prompt: str,
        user_message: str,
    ) -> str:
        """
        Faz chamada à API Gemini de forma assíncrona.

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

            # Fazer chamada assíncrona à API
            response = await self.client.generate_content_async(full_prompt)

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
        if not response or not response.strip():
            raise ValueError("Empty response from Gemini")

        # Tentar extrair JSON entre ```json e ```
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                json_str = response[start:end].strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON in ```json block: {exc}")

        # Tentar extrair JSON entre ``` e ```
        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end > start:
                json_str = response[start:end].strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON in ``` block: {exc}")

        # Tentar parse direto
        try:
            return json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Could not parse response as JSON: {exc}. Response preview: {response[:200]}")
