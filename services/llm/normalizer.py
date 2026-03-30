"""
LLM output normalization and validation.
"""

import re
from typing import Optional

from core.config import settings
from core.logging import get_logger
from schemas.llm import LLMOutput, OperatorEnum, SimpleFieldQuery, TermGroup, TextualFieldQuery

logger = get_logger(__name__)


class LLMOutputNormalizer:
    """
    Normaliza e valida saída do LLM aplicando regras de limpeza e validação.

    Aplica transformações para garantir qualidade e consistência dos dados:
    - Lowercase de todos os termos
    - Remoção de whitespace
    - Remoção de duplicatas
    - Remoção de strings vazias
    - Remoção de termos com menos de 2 caracteres
    - Validação de estrutura booleana
    - Validação de operadores
    - Injeção de YEAR se necessário
    """

    MIN_TERM_LENGTH = 2

    @staticmethod
    def normalize(llm_output: LLMOutput, inject_year: bool = True) -> LLMOutput:
        """
        Normaliza saída completa do LLM.

        Args:
            llm_output: Saída do LLM a normalizar.
            inject_year: Se True, injeta YEAR do config após normalização.

        Returns:
            LLMOutput normalizado.
        """
        # Normalizar campos textuais
        llm_output.title = LLMOutputNormalizer._normalize_textual_field(llm_output.title)
        llm_output.abstract = LLMOutputNormalizer._normalize_textual_field(llm_output.abstract)
        llm_output.claims = LLMOutputNormalizer._normalize_textual_field(llm_output.claims)
        llm_output.description = LLMOutputNormalizer._normalize_textual_field(
            llm_output.description
        )
        llm_output.full_text = LLMOutputNormalizer._normalize_textual_field(llm_output.full_text)

        # Normalizar campos simples
        llm_output.ipc = LLMOutputNormalizer._normalize_simple_field(llm_output.ipc)
        llm_output.cpc = LLMOutputNormalizer._normalize_simple_field(llm_output.cpc)
        llm_output.authors = LLMOutputNormalizer._normalize_simple_field(llm_output.authors)
        llm_output.affiliation = LLMOutputNormalizer._normalize_simple_field(
            llm_output.affiliation
        )
        llm_output.applicant = LLMOutputNormalizer._normalize_simple_field(llm_output.applicant)
        llm_output.inventor = LLMOutputNormalizer._normalize_simple_field(llm_output.inventor)
        llm_output.field_of_study = LLMOutputNormalizer._normalize_simple_field(
            llm_output.field_of_study
        )
        llm_output.keywords = LLMOutputNormalizer._normalize_simple_field(llm_output.keywords)
        llm_output.source_title = LLMOutputNormalizer._normalize_simple_field(
            llm_output.source_title
        )
        llm_output.year = LLMOutputNormalizer._normalize_simple_field(llm_output.year)

        # Injetar YEAR se necessário
        if inject_year:
            llm_output = LLMOutputNormalizer._inject_year(llm_output)

        logger.info(
            "llm_output_normalized",
            has_queries=llm_output.has_any_queries(),
            active_fields_count=sum(llm_output.get_active_fields().values()),
        )

        return llm_output

    @staticmethod
    def _normalize_textual_field(field: TextualFieldQuery) -> TextualFieldQuery:
        """
        Normaliza um campo textual.

        Args:
            field: Campo textual a normalizar.

        Returns:
            Campo normalizado.
        """
        if not field.groups:
            return field

        normalized_groups = []

        for group in field.groups:
            # Normalizar termos
            normalized_terms = LLMOutputNormalizer._normalize_terms(group.terms)

            # Criar grupo normalizado se houver termos
            if normalized_terms:
                normalized_groups.append(
                    TermGroup(
                        operator=group.operator,
                        terms=normalized_terms,
                    )
                )

        # Validar operador
        try:
            LLMOutputNormalizer._validate_operator(field.group_operator.value)
        except ValueError:
            field.group_operator = OperatorEnum.AND

        return TextualFieldQuery(
            group_operator=field.group_operator,
            groups=normalized_groups,
        )

    @staticmethod
    def _normalize_simple_field(field: SimpleFieldQuery) -> SimpleFieldQuery:
        """
        Normaliza um campo simples.

        Args:
            field: Campo simples a normalizar.

        Returns:
            Campo normalizado.
        """
        normalized_values = LLMOutputNormalizer._normalize_terms(field.values)

        return SimpleFieldQuery(values=normalized_values)

    @staticmethod
    def _normalize_terms(terms: list[str]) -> list[str]:
        """
        Normaliza lista de termos.

        Aplica:
        - Lowercase
        - Trim whitespace
        - Remove duplicatas
        - Remove vazios
        - Remove com menos de 2 caracteres

        Args:
            terms: Lista de termos a normalizar.

        Returns:
            Lista normalizada.
        """
        normalized = set()

        for term in terms:
            if not isinstance(term, str):
                continue

            # Lowercase e trim
            normalized_term = term.lower().strip()

            # Remover vazios
            if not normalized_term:
                continue

            # Remover muito curtos
            if len(normalized_term) < LLMOutputNormalizer.MIN_TERM_LENGTH:
                continue

            normalized.add(normalized_term)

        return sorted(list(normalized))

    @staticmethod
    def _validate_operator(operator: str) -> None:
        """
        Valida que operador é AND ou OR.

        Args:
            operator: Operador a validar.

        Raises:
            ValueError: Se operador inválido.
        """
        valid_operators = {op.value for op in OperatorEnum}

        if operator.upper() not in valid_operators:
            raise ValueError(f"Invalid operator: {operator}")

    @staticmethod
    def _inject_year(llm_output: LLMOutput) -> LLMOutput:
        """
        Injeta YEAR do config se disponível.

        Procura por campo YEAR_RANGE na config e injeta
        como valor no campo year da saída.

        Args:
            llm_output: Saída do LLM.

        Returns:
            Saída com YEAR injetado se disponível.
        """
        # Tentar obter YEAR_RANGE da config (campo customizado)
        year_range = getattr(settings, "year_range", None)

        if year_range:
            # Se for string, converter para lista
            if isinstance(year_range, str):
                years = [year_range]
            elif isinstance(year_range, list):
                years = year_range
            else:
                years = []

            if years:
                llm_output.year = SimpleFieldQuery(values=years)
                logger.info("llm_year_injected", years=years)

        return llm_output

    @staticmethod
    def validate_structure(llm_output: LLMOutput) -> bool:
        """
        Valida estrutura booleana completa de LLMOutput.

        Verifica:
        - Todos os operadores são válidos
        - Nenhum campo tem valores null
        - Estrutura de grupos está correta

        Args:
            llm_output: Saída do LLM a validar.

        Returns:
            True se válida, False caso contrário.
        """
        try:
            # Validar campos textuais
            for field in [
                llm_output.title,
                llm_output.abstract,
                llm_output.claims,
                llm_output.description,
                llm_output.full_text,
            ]:
                LLMOutputNormalizer._validate_operator(field.group_operator.value)

                for group in field.groups:
                    LLMOutputNormalizer._validate_operator(group.operator.value)

            # Campos simples não precisam validação além do que Pydantic faz

            return True

        except Exception as exc:
            logger.error(f"Structure validation failed: {exc}")
            return False
