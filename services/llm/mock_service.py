"""
Mock LLM service for testing and development.
"""

from typing import Optional

from schemas.intake import InputIntake
from schemas.llm import LLMOutput, OperatorEnum, SimpleFieldQuery, TermGroup, TextualFieldQuery
from services.llm.base import BaseLLMService


class MockLLMService(BaseLLMService):
    """
    Serviço LLM simulado para testes e desenvolvimento.

    Retorna respostas estruturadas pré-definidas sem fazer chamadas
    reais a um provedor LLM, acelerando testes e prototipagem.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Inicializa o serviço mock.

        Args:
            api_key: Ignorado para mock, pode ser None.
        """
        super().__init__(api_key)

    @property
    def provider_name(self) -> str:
        """
        Retorna nome do provedor mock.
        """
        return "mock"

    def is_available(self) -> bool:
        """
        Mock sempre está disponível.

        Returns:
            True.
        """
        return True

    async def process_intake(
        self,
        intake: InputIntake,
        system_prompt: str,
    ) -> LLMOutput:
        """
        Processa entrada e retorna estrutura mock de consultas.

        Gera uma resposta pré-definida baseada no tema da entrada
        para fins de desenvolvimento e teste.

        Args:
            intake: Entrada do usuário.
            system_prompt: Prompt do sistema (ignorado).

        Returns:
            Estrutura LLMOutput com consultas pré-definidas.
        """
        # Extrair termos do tema
        theme_terms = intake.theme.lower().split()[:3]

        # Extrair termos das palavras-chave iniciais
        keyword_terms = (
            [kw.lower() for kw in intake.initial_keywords[:3]]
            if intake.initial_keywords
            else []
        )

        # Construir consultas mock
        title_query = TextualFieldQuery(
            group_operator=OperatorEnum.AND,
            groups=[
                TermGroup(
                    operator=OperatorEnum.OR,
                    terms=theme_terms + keyword_terms,
                )
            ],
        )

        abstract_query = TextualFieldQuery(
            group_operator=OperatorEnum.AND,
            groups=[
                TermGroup(
                    operator=OperatorEnum.OR,
                    terms=theme_terms,
                )
            ],
        )

        keywords_query = SimpleFieldQuery(
            values=theme_terms + keyword_terms,
        )

        return LLMOutput(
            title=title_query,
            abstract=abstract_query,
            claims=TextualFieldQuery(),
            description=TextualFieldQuery(),
            full_text=TextualFieldQuery(),
            ipc=SimpleFieldQuery(),
            cpc=SimpleFieldQuery(),
            authors=SimpleFieldQuery(),
            affiliation=SimpleFieldQuery(),
            applicant=SimpleFieldQuery(),
            inventor=SimpleFieldQuery(),
            field_of_study=SimpleFieldQuery(),
            keywords=keywords_query,
            source_title=SimpleFieldQuery(),
            year=SimpleFieldQuery(),
        )
