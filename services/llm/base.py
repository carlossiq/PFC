"""
Base abstract class for LLM service providers.
"""

from abc import ABC, abstractmethod
from typing import Optional

from schemas.intake import InputIntake
from schemas.llm import LLMOutput


class BaseLLMService(ABC):
    """
    Interface abstrata para provedores de serviço LLM.

    Define contrato que todos os provedores de LLM devem implementar
    para processar requisições de prospecção e retornar consultas estruturadas.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Inicializa o serviço LLM.

        Args:
            api_key: Chave de API do provedor (se necessário).
        """
        self.api_key = api_key

    @abstractmethod
    async def process_intake(
        self,
        intake: InputIntake,
        system_prompt: str,
    ) -> LLMOutput:
        """
        Processa entrada de prospecção e retorna consultas estruturadas.

        Args:
            intake: Entrada do usuário com tema, objetivo e palavras-chave.
            system_prompt: Prompt do sistema com instruções para o LLM.

        Returns:
            Saída estruturada do LLM com campos de busca.

        Raises:
            Exception: Se o processamento falhar.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Verifica se o provedor está disponível e pronto para uso.

        Returns:
            True se disponível, False caso contrário.
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Nome do provedor de LLM.

        Returns:
            Nome identificador do provedor.
        """
        pass
