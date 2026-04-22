"""
Factory for creating LLM service instances based on configuration.
"""

import os
from typing import Optional

from core.config import settings
from core.logging import get_logger
from services.llm.anthropic_service import AnthropicLLMService
from services.llm.base import BaseLLMService
from services.llm.gemini_service import GeminiLLMService
from services.llm.mock_service import MockLLMService
from services.llm.qwen3_service import Qwen3LLMService

logger = get_logger(__name__)

logger = get_logger(__name__)


class LLMServiceFactory:
    """
    Factory para criação de serviços LLM.

    Gerencia a instanciação de diferentes provedores de LLM baseado
    em configuração, respeitando o modo de teste.
    """

    _instance: Optional[BaseLLMService] = None

    @staticmethod
    def create(provider: Optional[str] = None, api_key: Optional[str] = None) -> BaseLLMService:
        """
        Cria instância de serviço LLM.

        Se TEST_MODE=true, sempre retorna MockLLMService.
        Caso contrário, cria serviço baseado no provedor especificado.

        Args:
            provider: Nome do provedor (gemini, anthropic, mock).
                     Se None, usa configuração do ambiente.
            api_key: Chave de API do provedor (se necessário).
                    Se None, tenta obter de variáveis de ambiente.

        Returns:
            Instância de BaseLLMService.

        Raises:
            ValueError: Se provedor não for suportado.
            RuntimeError: Se nenhum serviço puder ser criado.
        """
        # Verificar modo de teste
        test_mode = settings.test_mode
        if test_mode:
            logger.info("LLM factory: TEST_MODE enabled, using MockLLMService")
            return MockLLMService()

        # Determinar provedor (usar settings em vez de os.getenv para respeitar .env)
        provider = provider or settings.llm_provider.lower()

        # Criar baseado no provedor
        if provider == "gemini":
            return LLMServiceFactory._create_gemini(api_key)
        elif provider == "anthropic":
            return LLMServiceFactory._create_anthropic(api_key)
        elif provider == "qwen3":
            return LLMServiceFactory._create_qwen3(api_key)
        elif provider == "mock":
            return MockLLMService()
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    @staticmethod
    def _create_gemini(api_key: Optional[str] = None) -> GeminiLLMService:
        """
        Cria serviço Gemini.

        Args:
            api_key: Chave de API (se None, tenta obter de settings).

        Returns:
            Instância de GeminiLLMService.

        Raises:
            ValueError: Se API key não estiver disponível.
        """
        api_key = api_key or settings.llm_gemini_api_key
        model = settings.llm_gemini_model

        if not api_key:
            logger.warning("Gemini API key not found, falling back to mock")
            return MockLLMService()

        try:
            service = GeminiLLMService(api_key=api_key, model=model)
            if service.is_available():
                logger.info("LLM factory: Gemini service created successfully")
                return service
            else:
                logger.warning("Gemini service not available, falling back to mock")
                return MockLLMService()
        except Exception as exc:
            logger.warning(f"Failed to create Gemini service: {exc}, falling back to mock")
            return MockLLMService()

    @staticmethod
    def _create_anthropic(api_key: Optional[str] = None) -> AnthropicLLMService:
        """
        Cria serviço Anthropic.

        Args:
            api_key: Chave de API (se None, tenta obter de settings).

        Returns:
            Instância de AnthropicLLMService.

        Raises:
            ValueError: Se API key não estiver disponível.
        """
        api_key = api_key or settings.llm_anthropic_api_key
        model = settings.llm_anthropic_model

        if not api_key:
            logger.warning("Anthropic API key not found, falling back to mock")
            return MockLLMService()

        try:
            service = AnthropicLLMService(api_key=api_key, model=model)
            if service.is_available():
                logger.info("LLM factory: Anthropic service created successfully")
                return service
            else:
                logger.warning("Anthropic service not available, falling back to mock")
                return MockLLMService()
        except Exception as exc:
            logger.warning(f"Failed to create Anthropic service: {exc}, falling back to mock")
            return MockLLMService()

    @staticmethod
    def _create_qwen3(api_key: Optional[str] = None) -> Qwen3LLMService:
        """
        Cria serviço Qwen3 (Alibaba Cloud).

        Args:
            api_key: Chave de API (se None, tenta obter de settings).

        Returns:
            Instância de Qwen3LLMService.

        Raises:
            ValueError: Se API key não estiver disponível.
        """
        api_key = api_key or settings.llm_qwen3_api_key
        model = settings.llm_qwen3_model

        if not api_key:
            logger.warning("Qwen3 API key not found, falling back to mock")
            return MockLLMService()

        try:
            service = Qwen3LLMService(api_key=api_key, model=model)
            if service.is_available():
                logger.info("LLM factory: Qwen3 service created successfully")
                return service
            else:
                logger.warning("Qwen3 service not available, falling back to mock")
                return MockLLMService()
        except Exception as exc:
            logger.warning(f"Failed to create Qwen3 service: {exc}, falling back to mock")
            return MockLLMService()

    @staticmethod
    def get_instance(provider: Optional[str] = None) -> BaseLLMService:
        """
        Obtém instância singleton de LLM service (recomendado para produção).

        Args:
            provider: Nome do provedor. Se None, usa default.

        Returns:
            Instância global de BaseLLMService.
        """
        if LLMServiceFactory._instance is None:
            LLMServiceFactory._instance = LLMServiceFactory.create(provider)

        return LLMServiceFactory._instance

    @staticmethod
    def reset_instance() -> None:
        """
        Reseta instância singleton (útil para testes).
        """
        LLMServiceFactory._instance = None
