"""
Base abstract class for LLM service providers.
"""

import json
import re
from abc import ABC, abstractmethod
from typing import Any, Optional

from app.core.domain.types import LLMUsage
from schemas.intake import InputIntake
from schemas.llm import LLMOutput


_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")
_MAX_JSON_REPAIRS = 20


def parse_llm_json(text: str) -> Any:
    """json.loads tolerante aos erros de formatação mais comuns de LLMs
    (principalmente modelos locais pequenos, ex.: gemma3:4b): vírgula
    sobrando antes de "}"/"]" e vírgula FALTANDO entre itens/chaves
    ("Expecting ',' delimiter") - essa é inserida exatamente na posição que
    o próprio json.loads aponta, repetindo até _MAX_JSON_REPAIRS vezes.
    Levanta o json.JSONDecodeError original se não conseguir."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as original:
        candidate = _TRAILING_COMMA_RE.sub(r"\1", text)
        for _ in range(_MAX_JSON_REPAIRS):
            try:
                return json.loads(candidate)
            except json.JSONDecodeError as exc:
                if exc.msg == "Expecting ',' delimiter":
                    candidate = candidate[: exc.pos] + "," + candidate[exc.pos :]
                    candidate = _TRAILING_COMMA_RE.sub(r"\1", candidate)
                    continue
                raise original
        raise original


class LLMJSONParseError(ValueError):
    """
    JSON malformado retornado pelo LLM (ex: aspa não escapada dentro de um
    campo de texto livre). Carrega a resposta bruta para permitir que o
    chamador tente uma recuperação parcial (ex: extrair os itens de uma
    lista que individualmente ainda são JSON válido) em vez de descartar a
    resposta inteira.
    """

    def __init__(self, message: str, raw_response: str) -> None:
        super().__init__(message)
        self.raw_response = raw_response


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
    ) -> tuple[LLMOutput, LLMUsage]:
        """
        Processa entrada de prospecção e retorna consultas estruturadas.

        Args:
            intake: Entrada do usuário com tema, objetivo e palavras-chave.
            system_prompt: Prompt do sistema com instruções para o LLM.

        Returns:
            Saída estruturada do LLM com campos de busca, e a duração/tokens
            da chamada.

        Raises:
            Exception: Se o processamento falhar.
        """
        pass

    @abstractmethod
    async def call_raw_json(
        self,
        prompt: str,
        user_input: str,
    ) -> tuple[dict[str, Any], LLMUsage]:
        """
        Chama LLM e retorna JSON bruto parseado.

        Diferente de process_intake que retorna LLMOutput estruturado,
        este método retorna exatamente o JSON que a LLM gerou.

        Args:
            prompt: Prompt do sistema com instruções.
            user_input: Entrada do usuário.

        Returns:
            Dicionário com resposta JSON bruta da LLM, e a duração/tokens da
            chamada.

        Raises:
            Exception: Se a chamada LLM falhar ou JSON for inválido.
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
