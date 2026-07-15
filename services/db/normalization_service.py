"""
Metadata normalization service for standardizing document metadata.
"""

from typing import Any, Optional, Union

from core.config import settings
from core.logging import get_logger
from schemas.normalized_metadata import StandardizedPatentMetadata, StandardizedScholarlyMetadata
from app.core.services.dedup_service import DedupService

logger = get_logger(__name__)


class NormalizationService:
    """
    Serviço de normalização de metadados.

    Absorve diferenças entre APIs, padronizando metadados
    em estruturas unificadas de patente e publicação.
    """

    def __init__(self) -> None:
        """
        Inicializa o serviço de normalização.
        """
        self.dedup_service = DedupService()

    def normalize_patent(
        self,
        data: dict[str, Any],
        source: str,
        relevance_score: Optional[float] = None,
    ) -> StandardizedPatentMetadata:
        """
        Normaliza metadados genéricos de patente para formato padrão.

        Args:
            data: Dados da patente com campos variáveis.
            source: Fonte original (lens_patent, ops, wipo, etc).
            relevance_score: Score de relevância (0-1).

        Returns:
            StandardizedPatentMetadata normalizado.
        """
        # Extrair campos principais
        title = data.get("title", "")
        abstract = data.get("abstract") or data.get("description")
        publication_number = (
            data.get("publication_number")
            or data.get("patent_number")
            or data.get("number")
        )
        application_number = (
            data.get("application_number")
            or data.get("application_id")
        )

        # Extrair classificações
        ipc_codes = self._extract_list_field(
            data,
            ["ipc", "ipc_codes", "ipc_classification", "ipc_classes"],
        )
        cpc_codes = self._extract_list_field(
            data,
            ["cpc", "cpc_codes", "cpc_classification", "cpc_classes"],
        )

        # Extrair atores
        applicants = self._extract_list_field(
            data,
            ["applicants", "applicant", "assignees", "holders"],
        )
        inventors = self._extract_list_field(
            data,
            ["inventors", "inventor"],
        )

        # Extrair datas
        filing_date = data.get("filing_date") or data.get("application_date")
        publication_date = data.get("publication_date") or data.get("issue_date")
        grant_date = data.get("grant_date")
        year = self._extract_year(data, publication_date or filing_date)

        # Gerar chave de deduplicação
        dedup_key = self.dedup_service.create_dedup_key(
            "patent",
            publication_number=publication_number,
            title=title,
            year=year,
        )

        logger.info(
            "patent_normalized",
            source=source,
            dedup_key=dedup_key,
        )

        return StandardizedPatentMetadata(
            source=source,
            source_record_id=str(data.get("id", "")),
            dedup_key=dedup_key,
            title=title,
            abstract=abstract,
            publication_number=publication_number,
            application_number=application_number,
            family_id=data.get("family_id") or data.get("patent_family_id"),
            applicants=applicants,
            inventors=inventors,
            ipc_codes=ipc_codes,
            cpc_codes=cpc_codes,
            filing_date=filing_date,
            publication_date=publication_date,
            grant_date=grant_date,
            year=year,
            legal_status=data.get("legal_status") or data.get("status"),
            country=data.get("country"),
            relevance_score=relevance_score,
            raw_payload=data if settings.log_level == "DEBUG" else None,  # Debug only
        )

    def normalize_scholarly(
        self,
        data: dict[str, Any],
        source: str,
        relevance_score: Optional[float] = None,
    ) -> StandardizedScholarlyMetadata:
        """
        Normaliza metadados genéricos de publicação para formato padrão.

        Args:
            data: Dados da publicação com campos variáveis.
            source: Fonte original (scopus, lens_scholarly, etc).
            relevance_score: Score de relevância (0-1).

        Returns:
            StandardizedScholarlyMetadata normalizado.
        """
        # Extrair campos principais
        title = data.get("title", "")
        abstract = (
            data.get("abstract")
            or data.get("abstract_text")
            or data.get("description")
        )
        doi = data.get("doi")

        # Extrair autores
        authors = self._extract_list_field(
            data,
            ["authors", "author", "creator", "creators"],
        )
        affiliations = self._extract_list_field(
            data,
            ["affiliations", "affiliation", "author_affiliations", "institutions"],
        )
        affiliation_countries = self._extract_list_field(
            data,
            ["affiliation_countries"],
        )

        # Extrair publicação
        journal_or_source = (
            data.get("journal")
            or data.get("source")
            or data.get("source_title")
            or data.get("publication_name")
        )
        volume = data.get("volume")
        issue = data.get("issue") or data.get("issue_number")
        pages = data.get("pages")

        # Extrair datas
        publication_date = data.get("publication_date") or data.get("issued")
        year = self._extract_year(data, publication_date)

        # Extrair conteúdo
        keywords = self._extract_list_field(
            data,
            ["keywords", "keyword", "key_words", "subjects"],
        )
        field_of_study = self._extract_list_field(
            data,
            ["field_of_study", "fields_of_study", "subject_areas", "categories"],
        )

        # Extrair métricas
        citations = data.get("cited_by_count") or data.get("citation_count")

        # Gerar chave de deduplicação
        dedup_key = self.dedup_service.create_dedup_key(
            "scholarly",
            doi=doi,
            title=title,
            year=year,
        )

        logger.info(
            "scholarly_normalized",
            source=source,
            dedup_key=dedup_key,
        )

        return StandardizedScholarlyMetadata(
            source=source,
            source_record_id=str(data.get("id", "")),
            dedup_key=dedup_key,
            title=title,
            abstract=abstract,
            doi=doi,
            authors=authors,
            affiliations=affiliations,
            affiliation_countries=affiliation_countries,
            journal_or_source=journal_or_source,
            volume=volume,
            issue=issue,
            pages=pages,
            publication_date=publication_date,
            year=year,
            keywords=keywords,
            field_of_study=field_of_study,
            citations=int(citations) if citations else None,
            relevance_score=relevance_score,
            raw_payload=data if settings.log_level == "DEBUG" else None,  # Debug only
        )

    def normalize_from_lens_patent(
        self,
        data: dict[str, Any],
        relevance_score: Optional[float] = None,
    ) -> StandardizedPatentMetadata:
        """
        Normaliza documento Lens Patent API.

        Args:
            data: Resposta da Lens Patent API.
            relevance_score: Score de relevância.

        Returns:
            StandardizedPatentMetadata.
        """
        return self.normalize_patent(
            data,
            source="lens_patent",
            relevance_score=relevance_score,
        )

    def normalize_from_lens_scholarly(
        self,
        data: dict[str, Any],
        relevance_score: Optional[float] = None,
    ) -> StandardizedScholarlyMetadata:
        """
        Normaliza documento Lens Scholarly API.

        Args:
            data: Resposta da Lens Scholarly API.
            relevance_score: Score de relevância.

        Returns:
            StandardizedScholarlyMetadata.
        """
        return self.normalize_scholarly(
            data,
            source="lens_scholarly",
            relevance_score=relevance_score,
        )

    def normalize_from_ops(
        self,
        data: dict[str, Any],
        relevance_score: Optional[float] = None,
    ) -> StandardizedPatentMetadata:
        """
        Normaliza documento OPS (European Patent Office) API.

        Mapeia estrutura OPS para formato padrão.

        Args:
            data: Documento OPS.
            relevance_score: Score de relevância.

        Returns:
            StandardizedPatentMetadata.
        """
        # Mapear estrutura OPS - dict achatado (não aninhado) produzido por
        # _extract_biblio_fields/_extract_biblio_fields_xml em services/search/ops_service.py
        mapped_data = {
            "id": data.get("docdb_id"),
            "title": data.get("invention_title"),
            "abstract": data.get("abstract"),
            "publication_number": data.get("docdb_id"),
            "application_number": data.get("application_reference"),
            "family_id": data.get("family_id"),
            "applicants": self._extract_list_field(
                data,
                ["applicants", "applicant"],
            ),
            "inventors": self._extract_list_field(
                data,
                ["inventors", "inventor"],
            ),
            "ipc": self._extract_list_field(
                data,
                ["ipc_classifications"],
            ),
            "cpc": self._extract_list_field(
                data,
                ["cpc_classifications"],
            ),
            "publication_date": data.get("publication_date"),
            "status": None,  # não existe no dict achatado atual do OPS
            "country": data.get("country"),
        }

        return self.normalize_patent(
            mapped_data,
            source="ops",
            relevance_score=relevance_score,
        )

    def normalize_from_scopus(
        self,
        data: dict[str, Any],
        relevance_score: Optional[float] = None,
    ) -> StandardizedScholarlyMetadata:
        """
        Normaliza documento Scopus API.

        Mapeia estrutura Scopus para formato padrão.

        Args:
            data: Documento Scopus (entry do search-results).
            relevance_score: Score de relevância.

        Returns:
            StandardizedScholarlyMetadata.
        """
        # Mapear estrutura Scopus - chaves reais são planas, com dois-pontos
        # literais no nome ("dc:title", "prism:doi"), não aninhadas em
        # sub-dicts. "dc:description" é injetado pelo enriquecimento via
        # OpenAlex (ChatService._enrich_scopus_abstracts), assim como
        # "openalex_field_of_study" (concepts do OpenAlex, já que a Scopus
        # não libera área de assunto por artigo pra essa API key).
        mapped_data = {
            "id": data.get("eid"),
            "title": data.get("dc:title"),
            "abstract": data.get("dc:description"),
            "doi": data.get("prism:doi") or data.get("dc:identifier"),
            "authors": self._extract_scopus_authors(data),
            "affiliations": self._extract_scopus_affiliations(data),
            "affiliation_countries": self._extract_scopus_affiliation_countries(data),
            "source": data.get("prism:publicationName"),
            "journal": data.get("prism:publicationName"),
            "volume": data.get("prism:volume"),
            "issue": data.get("prism:issueIdentifier"),
            "pages": data.get("prism:pageRange"),
            "publication_date": data.get("prism:coverDate"),
            "keywords": self._extract_list_field(
                data,
                ["authkeywords", "keywords"],
            ),
            "field_of_study": data.get("openalex_field_of_study") or [],
            "cited_by_count": data.get("citedby-count"),
        }

        return self.normalize_scholarly(
            mapped_data,
            source="scopus",
            relevance_score=relevance_score,
        )

    @staticmethod
    def _extract_list_field(
        data: dict[str, Any],
        field_names: list[str],
    ) -> list[str]:
        """
        Extrai campo que pode ser lista ou string.

        Tenta múltiplos nomes de campo, retorna como lista.

        Args:
            data: Dicionário com dados.
            field_names: Nomes de campos a tentar.

        Returns:
            Lista com valores extraídos.
        """
        for field_name in field_names:
            value = data.get(field_name)

            if value:
                if isinstance(value, list):
                    return [str(v).strip() for v in value if v]
                elif isinstance(value, str):
                    return [value.strip()] if value.strip() else []
                else:
                    return [str(value).strip()] if str(value).strip() else []

        return []

    @staticmethod
    def _extract_year(data: dict[str, Any], date_string: Optional[str] = None) -> Optional[int]:
        """
        Extrai ano de data ou campo year.

        Args:
            data: Dicionário com dados.
            date_string: String de data opcional (YYYY-MM-DD).

        Returns:
            Ano como inteiro ou None.
        """
        # Tentar field "year"
        year = data.get("year")
        if year:
            try:
                return int(year)
            except (ValueError, TypeError):
                pass

        # Tentar extrair de date_string
        if date_string:
            try:
                return int(date_string[:4])
            except (ValueError, IndexError, TypeError):
                pass

        return None

    @staticmethod
    def _extract_scopus_authors(data: dict[str, Any]) -> list[str]:
        """
        Extrai autores de estrutura Scopus.

        Tenta primeiro a lista "author" (dicts com authname/surname) - formato
        não confirmado contra resposta real desta API key. Cai pra "dc:creator"
        (string única com o primeiro autor) se a lista vier vazia - esse
        campo é o confirmado-confiável, já usado em outros pontos do app
        (ver extractResultAuthor no frontend).

        Args:
            data: Documento Scopus.

        Returns:
            Lista de nomes de autores.
        """
        authors = []

        author_list = data.get("author", [])
        for author in author_list:
            if isinstance(author, dict):
                name = author.get("authname") or author.get("surname")
                if name:
                    authors.append(name)
            elif isinstance(author, str):
                authors.append(author)

        if authors:
            return authors

        creator = data.get("dc:creator")
        return [creator] if isinstance(creator, str) and creator.strip() else []

    @staticmethod
    def _extract_scopus_affiliations(data: dict[str, Any]) -> list[str]:
        """
        Extrai afiliações de estrutura Scopus.

        Args:
            data: Documento Scopus.

        Returns:
            Lista de afiliações.
        """
        affiliations = []

        # Scopus usa "affiliation" como lista de dicts
        affiliation_list = data.get("affiliation", [])
        for aff in affiliation_list:
            if isinstance(aff, dict):
                org = aff.get("organization", "")
                country = aff.get("country", "")
                aff_str = f"{org}, {country}".strip(", ")
                if aff_str:
                    affiliations.append(aff_str)
            elif isinstance(aff, str):
                affiliations.append(aff)

        return affiliations

    @staticmethod
    def _extract_scopus_affiliation_countries(data: dict[str, Any]) -> list[str]:
        """
        Extrai os países distintos das afiliações de uma entrada Scopus - usa
        o campo real da API ("affiliation-country" dentro de cada item de
        "affiliation"), não o "country" genérico usado (sem confirmação
        contra a resposta real desta API key) em _extract_scopus_affiliations.
        "affiliation" vem como lista normalmente, mas a Scopus devolve um
        dict solto (não envolto em lista) quando há só 1 afiliação.

        Args:
            data: Documento Scopus.

        Returns:
            Lista de países distintos (na ordem em que aparecem).
        """
        raw = data.get("affiliation")
        affiliation_list = raw if isinstance(raw, list) else [raw] if raw else []

        countries: list[str] = []
        for aff in affiliation_list:
            if isinstance(aff, dict):
                country = aff.get("affiliation-country")
                if country and country not in countries:
                    countries.append(country)
        return countries

    def normalize_batch(
        self,
        documents: list[dict[str, Any]],
        source: str,
        document_type: str,
        relevance_scores: Optional[list[float]] = None,
    ) -> Union[list[StandardizedPatentMetadata], list[StandardizedScholarlyMetadata]]:
        """
        Normaliza lote de documentos.

        Args:
            documents: Lista de documentos.
            source: Fonte original.
            document_type: 'patent' ou 'scholarly'.
            relevance_scores: Scores opcionais (deve ter mesmo tamanho).

        Returns:
            Lista de documentos normalizados.
        """
        normalized = []
        scores = relevance_scores or [None] * len(documents)

        for doc, score in zip(documents, scores):
            if document_type == "patent":
                normalized_doc = self.normalize_patent(doc, source, score)
            elif document_type == "scholarly":
                normalized_doc = self.normalize_scholarly(doc, source, score)
            else:
                logger.warning(f"Unknown document type: {document_type}")
                continue

            normalized.append(normalized_doc)

        logger.info(
            "batch_normalized",
            source=source,
            document_type=document_type,
            count=len(normalized),
        )

        return normalized
