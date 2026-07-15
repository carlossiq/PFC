"""
Anthropic Claude LLM service implementation.
"""

import json
import time
from typing import Any, Optional

from pydantic import ValidationError

from app.core.domain.types import LLMUsage
from core.logging import get_logger
from schemas.intake import InputIntake
from schemas.llm import LLMOutput
from services.llm.base import BaseLLMService, LLMJSONParseError

logger = get_logger(__name__)


class AnthropicLLMService(BaseLLMService):
    """
    Serviço LLM usando Anthropic Claude API.

    Integra com Claude para processar requisições de prospecção
    e retornar consultas estruturadas em JSON.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        """
        Inicializa o serviço Anthropic.

        Args:
            api_key: Chave de API do Anthropic Claude.
            model: Versão do modelo Claude (ex: 'claude-3-5-sonnet-20241022').
                   Se None, usa o padrão da configuração.

        Raises:
            ValueError: Se api_key não for fornecida.
        """
        if not api_key:
            raise ValueError("Anthropic API key is required")

        super().__init__(api_key)

        # Se model não for fornecido, tenta obter da configuração
        if model is None:
            from core.config import settings
            model = settings.llm_anthropic_model

        self.model = model

        try:
            from anthropic import Anthropic

            self.client = Anthropic(api_key=api_key)
            self._is_available = True
        except ImportError:
            logger.error("anthropic package not installed")
            self._is_available = False
        except Exception as exc:
            logger.error(f"Failed to initialize Anthropic client: {exc}")
            self._is_available = False

    @property
    def provider_name(self) -> str:
        """
        Retorna nome do provedor Anthropic.
        """
        return "anthropic"

    def is_available(self) -> bool:
        """
        Verifica se Anthropic está disponível.

        Returns:
            True se cliente foi inicializado com sucesso.
        """
        return self._is_available

    async def process_intake(
        self,
        intake: InputIntake,
        system_prompt: str,
    ) -> tuple[LLMOutput, LLMUsage]:
        """
        Processa entrada usando Anthropic Claude API.

        Envia o tema e objetivo para Claude e recebe consultas
        estruturadas em JSON que são validadas como LLMOutput.

        Args:
            intake: Entrada do usuário.
            system_prompt: Prompt do sistema com instruções.

        Returns:
            Saída estruturada do Claude validada como LLMOutput, e a
            duração/tokens da chamada.

        Raises:
            Exception: Se Claude API falhar ou resposta inválida.
        """
        if not self.is_available():
            raise RuntimeError("Anthropic service is not available")

        # Construir mensagem de usuário
        user_message = self._build_user_message(intake)

        try:
            # Chamar Claude API
            response, usage = await self._call_claude(system_prompt, user_message)

            # Log raw response para debugging
            logger.info(
                "anthropic_raw_response",
                theme=intake.theme,
                response_length=len(response),
                response_preview=response[:500] if response else "EMPTY",
            )

            # Extrair JSON da resposta
            try:
                json_output = self._extract_json(response)
            except ValueError as parse_exc:
                logger.error(
                    "anthropic_json_parse_failed",
                    theme=intake.theme,
                    error=str(parse_exc),
                    raw_response=response,
                )
                raise

            # Log JSON parseado ANTES de converter para LLMOutput
            logger.info(
                "anthropic_json_parsed",
                theme=intake.theme,
                json_keys=list(json_output.keys()),
                abstract_exists="ABSTRACT" in json_output,
                title_exists="TITLE" in json_output,
                json_preview=str(json_output)[:500],
            )

            # Converter chaves de UPPERCASE para lowercase (Claude usa UPPERCASE)
            json_output_normalized = {k.lower(): v for k, v in json_output.items()}

            logger.info(
                "anthropic_json_keys_normalized",
                original_keys=list(json_output.keys()),
                normalized_keys=list(json_output_normalized.keys()),
            )

            # Validar e retornar
            llm_output = LLMOutput(**json_output_normalized)

            logger.info(
                "anthropic_processing_success",
                theme=intake.theme,
                has_queries=llm_output.has_any_queries(),
            )

            return llm_output, usage

        except ValidationError as exc:
            logger.error(
                "anthropic_validation_error",
                theme=intake.theme,
                error=str(exc),
            )
            raise ValueError(f"Claude output validation failed: {exc}")
        except Exception as exc:
            logger.error(
                "anthropic_processing_error",
                theme=intake.theme,
                error=str(exc),
            )
            raise

    async def call_raw_json(
        self,
        prompt: str,
        user_input: str,
    ) -> tuple[dict[str, Any], LLMUsage]:
        """
        Chama Claude e retorna JSON bruto parseado.

        Diferente de process_intake que retorna LLMOutput estruturado,
        este método retorna exatamente o JSON que o Claude gerou.

        Args:
            prompt: Prompt do sistema com instruções.
            user_input: Entrada do usuário.

        Returns:
            Dicionário com resposta JSON bruta do Claude, e a duração/tokens
            da chamada.

        Raises:
            Exception: Se a chamada Claude falhar ou JSON for inválido.
        """
        if not self.is_available():
            raise RuntimeError("Anthropic service is not available")

        try:
            response, usage = await self._call_claude(prompt, user_input)

            logger.info(
                "anthropic_raw_json_response",
                response_length=len(response),
            )

            json_output = self._extract_json(response)

            logger.info(
                "anthropic_raw_json_extracted",
                json_keys=list(json_output.keys()),
            )

            return json_output, usage

        except Exception as exc:
            logger.error(
                "anthropic_raw_json_error",
                error=str(exc),
            )
            raise

    def _build_user_message(self, intake: InputIntake) -> str:
        """
        Constrói mensagem do usuário para Claude.

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

    async def _call_claude(
        self,
        system_prompt: str,
        user_message: str,
    ) -> tuple[str, LLMUsage]:
        """
        Faz chamada à API Claude.

        Args:
            system_prompt: Prompt do sistema.
            user_message: Mensagem do usuário.

        Returns:
            Resposta em texto do Claude, e a duração/tokens da chamada.

        Raises:
            Exception: Se chamada à API falhar.
        """
        try:
            start = time.perf_counter()
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_message,
                    }
                ],
            )
            duration_ms = (time.perf_counter() - start) * 1000

            usage = LLMUsage(
                provider=self.provider_name,
                model=self.model,
                duration_ms=duration_ms,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            )
            return response.content[0].text, usage

        except Exception as exc:
            logger.error(f"Claude API call failed: {exc}")
            raise

    @staticmethod
    def _extract_json(response: str) -> dict:
        """
        Extrai JSON da resposta do Claude.

        Procura por bloco JSON delimitado por ``` ou direto no texto.

        Args:
            response: Resposta em texto do Claude.

        Returns:
            Dicionário com JSON extraído.

        Raises:
            ValueError: Se JSON não for encontrado ou inválido.
        """
        if not response or not response.strip():
            raise ValueError("Empty response from Claude")

        # Tentar extrair JSON entre ```json e ```
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                json_str = response[start:end].strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as exc:
                    raise LLMJSONParseError(f"Invalid JSON in ```json block: {exc}", raw_response=response)

        # Tentar extrair JSON entre ``` e ```
        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end > start:
                json_str = response[start:end].strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as exc:
                    raise LLMJSONParseError(f"Invalid JSON in ``` block: {exc}", raw_response=response)

        # Tentar parse direto
        try:
            return json.loads(response)
        except json.JSONDecodeError as exc:
            raise LLMJSONParseError(
                f"Could not parse response as JSON: {exc}. Response preview: {response[:200]}",
                raw_response=response,
            )
