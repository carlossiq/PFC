"""
Alibaba Cloud Qwen3 LLM service implementation.
"""

import json
from typing import Optional

from pydantic import ValidationError

from core.logging import get_logger
from schemas.intake import InputIntake
from schemas.llm import LLMOutput
from services.llm.base import BaseLLMService

logger = get_logger(__name__)


class Qwen3LLMService(BaseLLMService):
    """
    Serviço LLM usando Alibaba Cloud Qwen3 API.

    Integra com Qwen3 para processar requisições de prospecção
    e retornar consultas estruturadas em JSON.
    """

    def __init__(
        self, api_key: Optional[str] = None, model: Optional[str] = None
    ) -> None:
        """
        Inicializa o serviço Qwen3.

        Args:
            api_key: Chave de API do Qwen3 (Alibaba Cloud).
            model: Versão do modelo Qwen3 (ex: 'qwen-max').
                   Se None, usa o padrão da configuração.

        Raises:
            ValueError: Se api_key não for fornecida.
        """
        if not api_key:
            raise ValueError("Qwen3 API key is required")

        super().__init__(api_key)

        # Se model não for fornecido, tenta obter da configuração
        if model is None:
            from core.config import settings

            model = settings.llm_qwen3_model

        self.model = model

        try:
            import dashscope

            dashscope.api_key = api_key
            self.client = dashscope
            self._is_available = True
        except ImportError:
            logger.error("dashscope package not installed")
            self._is_available = False
        except Exception as exc:
            logger.error(f"Failed to initialize Qwen3 client: {exc}")
            self._is_available = False

    @property
    def provider_name(self) -> str:
        """
        Retorna nome do provedor Qwen3.
        """
        return "qwen3"

    def is_available(self) -> bool:
        """
        Verifica se Qwen3 está disponível.

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
        Processa entrada usando Qwen3 API.

        Envia o tema e objetivo para Qwen3 e recebe consultas
        estruturadas em JSON que são validadas como LLMOutput.

        Args:
            intake: Entrada do usuário.
            system_prompt: Prompt do sistema com instruções.

        Returns:
            Saída estruturada do Qwen3 validada como LLMOutput.

        Raises:
            RuntimeError: Se falhar na chamada à API.
        """
        try:
            from dashscope import Generation

            # Construir prompt com instrução de JSON
            user_message = intake.to_prompt()
            full_prompt = f"{system_prompt}\n\n{user_message}"

            logger.info(
                "qwen3_request_starting",
                model=self.model,
                prompt_length=len(full_prompt),
            )

            # Fazer chamada síncron (dashscope é síncrono por padrão)
            response = Generation.call(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": full_prompt,
                    }
                ],
                result_format="message",
            )

            if response.status_code != 200:
                error_msg = response.message if hasattr(response, "message") else str(response)
                logger.error(
                    "qwen3_request_failed",
                    status_code=response.status_code,
                    error=error_msg,
                )
                raise RuntimeError(f"Qwen3 API error: {error_msg}")

            # Extrair resposta
            response_text = response.output.choices[0].message.content

            logger.info(
                "qwen3_raw_response",
                response_length=len(response_text),
                response_preview=response_text[:500],
            )

            # Parse JSON
            try:
                json_match = response_text
                # Se estiver envolto em ```json, extrair
                if "```json" in response_text:
                    json_match = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    json_match = response_text.split("```")[1].split("```")[0]

                parsed = json.loads(json_match.strip())

                logger.info(
                    "qwen3_json_parsed",
                    json_keys=list(parsed.keys()),
                    json_preview=str(parsed)[:200],
                )
            except json.JSONDecodeError as exc:
                logger.error(f"Failed to parse Qwen3 JSON response: {exc}")
                raise RuntimeError(f"Invalid JSON in Qwen3 response: {exc}")

            # Validar e converter para LLMOutput
            try:
                output = LLMOutput.from_dict(parsed)
                logger.info("qwen3_processing_success", has_queries=output.has_queries())
                return output
            except ValidationError as exc:
                logger.error(f"Validation error in Qwen3 output: {exc}")
                raise RuntimeError(f"Invalid LLMOutput from Qwen3: {exc}")

        except RuntimeError:
            raise
        except Exception as exc:
            logger.error(
                "qwen3_processing_error",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise RuntimeError(f"Failed to process intake with Qwen3: {exc}") from exc
