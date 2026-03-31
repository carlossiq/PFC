"""
Pipeline orchestrator for technology prospecting workflow.

Coordinates all services in a structured multi-stage pipeline:
1. Intake validation
2. LLM strategy generation
3. Probe search execution
4. Semantic expansion (keyword extraction + reranking)
5. Final strategy generation
6. Production search execution
7. Relevance filtering
8. Deduplication
9. Metadata normalization
10. Persistence
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logging import get_logger
from schemas.intake import InputIntake
from schemas.llm import LLMOutput
from services.db.normalization_service import NormalizationService
from services.db.persistence_service import PersistenceService
from services.dedup import DedupService
from services.llm import (
    LLMOutputNormalizer,
    LLMServiceFactory,
    FieldSchemaService,
)
from services.nlp import (
    EmbeddingService,
    KeywordService,
    RelevanceService,
)
from services.prompt import PromptLoader
from services.query_builders import QueryBuilderFactory
from services.search import LensService, OPSService, ScopusService

logger = get_logger(__name__)


@dataclass
class StageOutput:
    """
    Resultado de uma etapa do pipeline.

    Armazena saída e erros de cada etapa para auditoria.
    """

    stage_name: str
    success: bool
    duration_seconds: float = 0.0
    output: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Converte resultado para dicionário.

        Returns:
            Dicionário com dados da etapa.
        """
        return {
            "stage_name": self.stage_name,
            "success": self.success,
            "duration_seconds": round(self.duration_seconds, 2),
            "output": self.output,
            "error": self.error,
            "error_type": self.error_type,
            "details": self.details,
        }


@dataclass
class PipelineResult:
    """
    Resultado completo da execução do pipeline.

    Agrupa saídas de todas as etapas com métricas finais.
    """

    run_id: str
    success: bool
    intake: InputIntake
    total_duration_seconds: float
    stages: list[StageOutput] = field(default_factory=list)

    # Contadores
    documents_found_total: int = 0
    documents_filtered: int = 0
    documents_unique: int = 0
    documents_persisted: int = 0

    # Falhas
    api_failures: dict[str, str] = field(default_factory=dict)

    # Saídas detalhadas por etapa (para test routes)
    initial_strategy: Optional[LLMOutput] = None
    probe_search_results: dict[str, Any] = field(default_factory=dict)
    extracted_keywords: dict[str, Any] = field(default_factory=dict)
    final_strategy: dict[str, LLMOutput] = field(default_factory=dict)
    production_search_results: dict[str, Any] = field(default_factory=dict)
    relevance_filtering: dict[str, Any] = field(default_factory=dict)
    dedup_results: dict[str, Any] = field(default_factory=dict)
    normalized_documents: dict[str, int] = field(default_factory=dict)
    persistence_results: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Converte resultado para dicionário.

        Returns:
            Dicionário com dados completos do pipeline.
        """
        return {
            "run_id": self.run_id,
            "success": self.success,
            "total_duration_seconds": round(self.total_duration_seconds, 2),
            "intake": self.intake.model_dump(),
            "stages": [stage.to_dict() for stage in self.stages],
            "statistics": {
                "documents_found_total": self.documents_found_total,
                "documents_filtered": self.documents_filtered,
                "documents_unique": self.documents_unique,
                "documents_persisted": self.documents_persisted,
            },
            "api_failures": self.api_failures,
        }

    def to_dict_detailed(self) -> dict[str, Any]:
        """
        Converte resultado com saídas detalhadas por etapa.

        Útil para test routes e debugging.

        Returns:
            Dicionário com dados completos e detalhes de cada etapa.
        """
        result = self.to_dict()
        result["detailed_outputs"] = {
            "initial_strategy": (
                self.initial_strategy.model_dump() if self.initial_strategy else None
            ),
            "probe_search_results": self.probe_search_results,
            "extracted_keywords": self.extracted_keywords,
            "final_strategy": {
                k: v.model_dump() for k, v in self.final_strategy.items()
            },
            "production_search_results": self.production_search_results,
            "relevance_filtering": self.relevance_filtering,
            "dedup_results": self.dedup_results,
            "normalized_documents": self.normalized_documents,
            "persistence_results": self.persistence_results,
        }
        return result


class PipelineOrchestrator:
    """
    Orquestrador do pipeline de prospecção tecnológica.

    Coordena múltiplos serviços em um fluxo estruturado
    com tratamento de erros e preservação de outputs.
    """

    def __init__(self) -> None:
        """
        Inicializa o orquestrador.
        """
        self.run_id: Optional[str] = None
        self.result: Optional[PipelineResult] = None

        # Serviços
        # Serviço de LLM (singleton recomendado para produção)
        self.llm_service = LLMServiceFactory.get_instance()
        # Serviço de esquema de campos (para passar informações dinâmicas à LLM)
        self.field_schema_service = FieldSchemaService()
        # Serviços de NLP: keyword extraction, embeddings, relevância
        self.keyword_service = KeywordService()
        # Serviços de processamento: deduplicação, normalização
        self.embedding_service = EmbeddingService()
        # RelevanceService depende de embeddings, então é inicializado depois
        self.relevance_service = RelevanceService(self.embedding_service)
        # Serviços de duplicação para remover documentos redundantes
        self.dedup_service = DedupService()
        # NormalizationService para padronizar metadados antes da persistência
        self.normalization_service = NormalizationService()

        # APIs de busca
        self.lens_service = LensService()
        self.ops_service = OPSService()
        self.scopus_service = ScopusService()

    async def execute(
        self,
        intake: InputIntake,
        session: AsyncSession,
    ) -> PipelineResult:
        """
        Executa o pipeline completo.

        Fluxo:
        1. Receber intake
        2. Gerar estratégia inicial via LLM
        3. Executar probe search
        4. Extrair termos
        5. Gerar estratégia final
        6. Executar busca real
        7. Filtrar por relevância
        8. Deduplicar
        9. Normalizar
        10. Persistir

        Args:
            intake: Entrada do usuário.
            session: Sessão de banco de dados.

        Returns:
            PipelineResult com execução completa.
        """
        # Gerar run_id
        self.run_id = str(uuid.uuid4())
        pipeline_start = time.time()

        logger.info(
            "pipeline_started",
            run_id=self.run_id,
            theme=intake.theme,
        )

        # Inicializar resultado
        self.result = PipelineResult(
            run_id=self.run_id,
            success=False,
            intake=intake,
            total_duration_seconds=0.0,
        )

        try:
            # Etapa 1: Validação (já feita por Pydantic em intake)
            logger.info("stage_1_intake_validated", run_id=self.run_id)

            # Etapa 2: Estratégia inicial via LLM
            await self._stage_initial_strategy()

            # Etapa 3: Probe search
            await self._stage_probe_search()

            # Etapa 4-5: Expansão semântica
            await self._stage_semantic_expansion()

            # Etapa 6: Estratégia final
            await self._stage_final_strategy()

            # Etapa 7: Busca real
            await self._stage_production_search()

            # Etapa 8: Filtro de relevância
            await self._stage_relevance_filtering()

            # Etapa 9: Deduplicação
            await self._stage_deduplication()

            # Etapa 10: Normalização
            await self._stage_normalization()

            # Etapa 11: Persistência
            await self._stage_persistence(session)

            self.result.success = True

        except Exception as exc:
            logger.error(
                "pipeline_error",
                error=str(exc),
                error_type=type(exc).__name__,
                run_id=self.run_id,
            )
            self.result.success = False

        finally:
            self.result.total_duration_seconds = time.time() - pipeline_start

            logger.info(
                "pipeline_completed",
                run_id=self.run_id,
                success=self.result.success,
                total_duration=self.result.total_duration_seconds,
                documents_persisted=self.result.documents_persisted,
            )

        return self.result

    async def _stage_initial_strategy(self) -> None:
        """
        Etapa 2: Gera estratégia inicial via LLM para probe search.

        Processa tema e objetivo para gerar consultas estruturadas
        otimizadas para a busca de sondagem (probe search).

        Os campos esperados variam dinamicamente de acordo com a PROBE_API configurada
        e PROBE_API_EXT (se habilitada).
        """
        stage_start = time.time()
        stage_name = "initial_strategy"

        try:
            logger.info(f"stage_{stage_name}_started", run_id=self.run_id)

            # Carregar prompt otimizado para probe search
            system_prompt = PromptLoader.load_probe_system_prompt()

            # Obter campos dinâmicos para PROBE (inclui PROBE_API e PROBE_API_EXT)
            probe_fields = self.field_schema_service.get_fields_for_probe()

            probe_api = getattr(settings, "probe_api", "lens_patent")
            probe_api_ext = getattr(settings, "probe_api_ext", None)

            # Enriquecer prompt com informação dinâmica dos campos esperados
            enriched_prompt = self._enrich_prompt_with_fields(
                system_prompt=system_prompt,
                available_fields=probe_fields,
                api_name=probe_api,
            )

            logger.info(
                "initial_strategy_context",
                probe_api=probe_api,
                probe_api_ext=probe_api_ext,
                available_fields_count=len(probe_fields),
                run_id=self.run_id,
            )

            # Processar com LLM usando prompt enriquecido
            llm_output = await self.llm_service.process_intake(
                intake=self.result.intake,
                system_prompt=enriched_prompt,
            )

            # Normalizar saída, filtrando apenas para campos habilitados da probe
            normalized = LLMOutputNormalizer.normalize(llm_output, enabled_fields=probe_fields)

            self.result.initial_strategy = normalized
            self.result.stages.append(
                StageOutput(
                    stage_name=stage_name,
                    success=True,
                    duration_seconds=time.time() - stage_start,
                    output={"has_queries": normalized.has_any_queries()},
                    details={
                        "active_fields": sum(normalized.get_active_fields().values()),
                    },
                )
            )

        except Exception as exc:
            logger.error(
                f"stage_{stage_name}_error",
                error=str(exc),
                run_id=self.run_id,
            )
            self.result.stages.append(
                StageOutput(
                    stage_name=stage_name,
                    success=False,
                    duration_seconds=time.time() - stage_start,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
            )

    async def _stage_probe_search(self) -> None:
        """
        Etapa 3: Executa probe search com estratégia inicial.

        Busca limitada para coleta de documentos para expansão.
        """
        stage_start = time.time()
        stage_name = "probe_search"

        try:
            logger.info(f"stage_{stage_name}_started", run_id=self.run_id)

            if not self.result.initial_strategy:
                raise ValueError("Initial strategy not available")

            # Determinar API de probe
            probe_api = getattr(settings, "probe_api", "lens_patent")

            # Construir query para probe
            builder = QueryBuilderFactory.create(probe_api, search_mode="probe")
            query = builder.build_query(
                llm_output=self.result.initial_strategy,
                year_from=getattr(settings, "search_year_from", 2015),
                year_to=getattr(settings, "search_year_to", 2024),
            )

            # Executar probe search
            if probe_api == "lens_patent":
                probe_result = await self.lens_service.search_patent(
                    query=query,
                    run_id=self.run_id,
                )
            elif probe_api == "lens_scholarly":
                probe_result = await self.lens_service.search_scholarly(
                    query=query,
                    run_id=self.run_id,
                )
            else:
                raise ValueError(f"Unsupported probe API: {probe_api}")

            # Armazenar resultados
            probe_docs = probe_result.results[:50]  # Limitar a 50 documentos

            self.result.probe_search_results = {
                "api": probe_api,
                "success": probe_result.success,
                "documents_found": len(probe_docs),
                "duration": probe_result.duration_seconds,
            }

            self.result.stages.append(
                StageOutput(
                    stage_name=stage_name,
                    success=probe_result.success,
                    duration_seconds=time.time() - stage_start,
                    output=self.result.probe_search_results,
                    details={"total_available": probe_result.total_count},
                )
            )

            # Armazenar documentos para etapa seguinte
            self.result.details = {"probe_documents": probe_docs}

        except Exception as exc:
            logger.error(
                f"stage_{stage_name}_error",
                error=str(exc),
                run_id=self.run_id,
            )
            self.result.stages.append(
                StageOutput(
                    stage_name=stage_name,
                    success=False,
                    duration_seconds=time.time() - stage_start,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
            )

    async def _stage_semantic_expansion(self) -> None:
        """
        Etapa 4-5: Extrai termos e rerank documentos.

        Usa KeyBERT para extrair keywords e SBERT para reranking.
        """
        stage_start = time.time()
        stage_name = "semantic_expansion"

        try:
            logger.info(f"stage_{stage_name}_started", run_id=self.run_id)

            probe_docs = self.result.details.get("probe_documents", [])

            if not probe_docs:
                logger.warning("No probe documents for semantic expansion")
                self.result.stages.append(
                    StageOutput(
                        stage_name=stage_name,
                        success=True,
                        duration_seconds=time.time() - stage_start,
                        output={"extracted_keywords": [], "reranked": []},
                    )
                )
                return

            # Extrair keywords com KeyBERT
            keywords_by_doc = self.keyword_service.batch_extract(probe_docs, top_k=10)
            unique_keywords = self.keyword_service.get_unique_keywords(keywords_by_doc)

            # Rerank documentos por relevância semântica
            # TODO: Implementar lógica de reranking sofisticada
            # - Calcular embedding do tema
            # - Calcular embedding de cada documento
            # - Reordenar por similaridade descendente
            # - Implementar stratégia de cutoff (top-k documentos)

            self.result.extracted_keywords = {
                "total_unique": len(unique_keywords),
                "top_keywords": unique_keywords[:20],
                "documents_analyzed": len(probe_docs),
            }

            self.result.stages.append(
                StageOutput(
                    stage_name=stage_name,
                    success=True,
                    duration_seconds=time.time() - stage_start,
                    output=self.result.extracted_keywords,
                    details={
                        "extraction_method": "keybert",
                        "reranking_method": "sbert_cosine_similarity",
                    },
                )
            )

        except Exception as exc:
            logger.error(
                f"stage_{stage_name}_error",
                error=str(exc),
                run_id=self.run_id,
            )
            self.result.stages.append(
                StageOutput(
                    stage_name=stage_name,
                    success=False,
                    duration_seconds=time.time() - stage_start,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
            )

    async def _stage_final_strategy(self) -> None:
        """
        Etapa 6: Gera estratégia final refinada com keywords da expansão semântica.

        Usa termos expandidos (extraídos da probe) para gerar queries mais
        abrangentes para a busca final/exploratória, otimizadas para TODAS as APIs habilitadas.
        """
        stage_start = time.time()
        stage_name = "final_strategy"

        try:
            logger.info(f"stage_{stage_name}_started", run_id=self.run_id)

            # Carregar prompt otimizado para busca geral/final
            system_prompt = PromptLoader.load_general_system_prompt()

            # Obter keywords extraídos na etapa anterior
            expanded_keywords = self.result.extracted_keywords.get("top_keywords", [])

            # TODO: Integrar keywords expandidos no contexto do LLM
            # Por enquanto, processa novamente com o intake original usando o prompt geral
            # Melhorias futuras: passar keywords como contexto adicional ao LLM

            # Obter campos dinâmicos para busca final (todas as APIs habilitadas)
            final_fields = self.field_schema_service.get_fields_for_final()

            # Enriquecer prompt com campos de todas as APIs habilitadas
            enriched_prompt = self._enrich_prompt_with_final_fields(
                system_prompt=system_prompt,
                available_fields=final_fields,
            )

            logger.info(
                "final_strategy_context",
                available_fields_count=len(final_fields),
                expanded_keywords_count=len(expanded_keywords),
                run_id=self.run_id,
            )

            # Processar com LLM para gerar estratégia refinada (mais abrangente)
            refined_output = await self.llm_service.process_intake(
                intake=self.result.intake,
                system_prompt=enriched_prompt,
            )

            # Normalizar saída, filtrando apenas para campos habilitados da busca final
            normalized_refined = LLMOutputNormalizer.normalize(refined_output, enabled_fields=final_fields)

            # Armazenar estratégia final (igual para ambos por enquanto)
            # TODO: Gerar strategies separadas otimizadas para patent e scholarly
            # - Patent: ênfase em IPC, CPC, CLAIMS, APPLICANT, INVENTOR
            # - Scholarly: ênfase em KEYWORDS, FIELD_OF_STUDY, AUTHORS, AFFILIATION
            self.result.final_strategy = {
                "patent": normalized_refined,
                "scholarly": normalized_refined,
            }

            self.result.stages.append(
                StageOutput(
                    stage_name=stage_name,
                    success=True,
                    duration_seconds=time.time() - stage_start,
                    output={
                        "patent_strategy_ready": True,
                        "scholarly_strategy_ready": True,
                        "expanded_keywords_used": len(expanded_keywords),
                    },
                    details={
                        "active_fields_patent": sum(
                            normalized_refined.get_active_fields().values()
                        ),
                        "active_fields_scholarly": sum(
                            normalized_refined.get_active_fields().values()
                        ),
                    },
                )
            )

        except Exception as exc:
            logger.error(
                f"stage_{stage_name}_error",
                error=str(exc),
                run_id=self.run_id,
            )
            self.result.stages.append(
                StageOutput(
                    stage_name=stage_name,
                    success=False,
                    duration_seconds=time.time() - stage_start,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
            )

    async def _stage_production_search(self) -> None:
        """
        Etapa 7: Executa busca real em APIs habilitadas.

        Executa em ordem: Lens Scholarly → Lens Patent → OPS → Scopus.
        Continua se uma API falhar.
        """
        stage_start = time.time()
        stage_name = "production_search"

        try:
            logger.info(f"stage_{stage_name}_started", run_id=self.run_id)

            results_by_api = {}
            all_documents = []

            # Lens Scholarly
            if getattr(settings, "lens_enabled", True):
                try:
                    builder = QueryBuilderFactory.create("lens_scholarly")
                    query = builder.build_query(
                        llm_output=self.result.final_strategy["scholarly"],
                        year_from=getattr(settings, "search_year_from", 2015),
                        year_to=getattr(settings, "search_year_to", 2024),
                    )
                    result = await self.lens_service.search_scholarly(
                        query, self.run_id
                    )
                    results_by_api["lens_scholarly"] = result
                    if result.success:
                        all_documents.extend(result.results)
                        self.result.documents_found_total += result.results_returned
                except Exception as exc:
                    logger.error(f"lens_scholarly_error: {exc}", run_id=self.run_id)
                    self.result.api_failures["lens_scholarly"] = str(exc)

            # Lens Patent
            if getattr(settings, "lens_enabled", True):
                try:
                    builder = QueryBuilderFactory.create("lens_patent")
                    query = builder.build_query(
                        llm_output=self.result.final_strategy["patent"],
                        year_from=getattr(settings, "search_year_from", 2015),
                        year_to=getattr(settings, "search_year_to", 2024),
                    )
                    result = await self.lens_service.search_patent(query, self.run_id)
                    results_by_api["lens_patent"] = result
                    if result.success:
                        all_documents.extend(result.results)
                        self.result.documents_found_total += result.results_returned
                except Exception as exc:
                    logger.error(f"lens_patent_error: {exc}", run_id=self.run_id)
                    self.result.api_failures["lens_patent"] = str(exc)

            # OPS
            if getattr(settings, "ops_enabled", True):
                try:
                    builder = QueryBuilderFactory.create("ops")
                    query = builder.build_query(
                        llm_output=self.result.final_strategy["patent"],
                        year_from=getattr(settings, "search_year_from", 2015),
                        year_to=getattr(settings, "search_year_to", 2024),
                    )
                    result = await self.ops_service.search(query, self.run_id)
                    results_by_api["ops"] = result
                    if result.success:
                        all_documents.extend(result.results)
                        self.result.documents_found_total += result.results_returned
                except Exception as exc:
                    logger.error(f"ops_error: {exc}", run_id=self.run_id)
                    self.result.api_failures["ops"] = str(exc)

            # Scopus
            if getattr(settings, "scopus_enabled", True):
                try:
                    builder = QueryBuilderFactory.create("scopus")
                    query = builder.build_query(
                        llm_output=self.result.final_strategy["scholarly"],
                        year_from=getattr(settings, "search_year_from", 2015),
                        year_to=getattr(settings, "search_year_to", 2024),
                    )
                    result = await self.scopus_service.search(query, run_id=self.run_id)
                    results_by_api["scopus"] = result
                    if result.success:
                        all_documents.extend(result.results)
                        self.result.documents_found_total += result.results_returned
                except Exception as exc:
                    logger.error(f"scopus_error: {exc}", run_id=self.run_id)
                    self.result.api_failures["scopus"] = str(exc)

            self.result.production_search_results = {
                "apis_executed": len(results_by_api),
                "total_documents": len(all_documents),
                "by_api": {
                    api: {
                        "success": result.success,
                        "documents": result.results_returned,
                    }
                    for api, result in results_by_api.items()
                },
            }

            # Armazenar documentos para etapas seguintes
            self.result.details["production_documents"] = all_documents

            self.result.stages.append(
                StageOutput(
                    stage_name=stage_name,
                    success=len(all_documents) > 0,
                    duration_seconds=time.time() - stage_start,
                    output=self.result.production_search_results,
                    details={"api_failures": len(self.result.api_failures)},
                )
            )

        except Exception as exc:
            logger.error(
                f"stage_{stage_name}_error",
                error=str(exc),
                run_id=self.run_id,
            )
            self.result.stages.append(
                StageOutput(
                    stage_name=stage_name,
                    success=False,
                    duration_seconds=time.time() - stage_start,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
            )

    async def _stage_relevance_filtering(self) -> None:
        """
        Etapa 8: Aplica filtro de relevância semântica.

        Separa documentos em aprovados/rejeitados.
        """
        stage_start = time.time()
        stage_name = "relevance_filtering"

        try:
            logger.info(f"stage_{stage_name}_started", run_id=self.run_id)

            prod_docs = self.result.details.get("production_documents", [])

            if not prod_docs:
                logger.warning("No production documents to filter")
                self.result.stages.append(
                    StageOutput(
                        stage_name=stage_name,
                        success=True,
                        duration_seconds=time.time() - stage_start,
                        output={"approved": 0, "rejected": 0},
                    )
                )
                return

            # Filtrar por relevância
            filtered = self.relevance_service.filter_documents(
                theme=self.result.intake.theme,
                documents=prod_docs,
                run_id=self.run_id,
            )

            self.result.documents_filtered = filtered.approved_count
            self.result.relevance_filtering = {
                "total_input": filtered.total_documents,
                "approved": filtered.approved_count,
                "rejected": filtered.rejected_count,
                "approval_rate": round(filtered.approval_rate, 4),
                "threshold": filtered.threshold_applied,
            }

            # Armazenar documentos filtrados
            self.result.details["filtered_documents"] = filtered.approved_documents

            self.result.stages.append(
                StageOutput(
                    stage_name=stage_name,
                    success=True,
                    duration_seconds=time.time() - stage_start,
                    output=self.result.relevance_filtering,
                )
            )

        except Exception as exc:
            logger.error(
                f"stage_{stage_name}_error",
                error=str(exc),
                run_id=self.run_id,
            )
            self.result.stages.append(
                StageOutput(
                    stage_name=stage_name,
                    success=False,
                    duration_seconds=time.time() - stage_start,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
            )

    async def _stage_deduplication(self) -> None:
        """
        Etapa 9: Deduplica documentos.

        Separa documentos únicos de duplicatas.
        """
        stage_start = time.time()
        stage_name = "deduplication"

        try:
            logger.info(f"stage_{stage_name}_started", run_id=self.run_id)

            filtered_docs = self.result.details.get("filtered_documents", [])

            if not filtered_docs:
                logger.warning("No filtered documents to deduplicate")
                self.result.stages.append(
                    StageOutput(
                        stage_name=stage_name,
                        success=True,
                        duration_seconds=time.time() - stage_start,
                        output={"unique": 0, "duplicates": 0},
                    )
                )
                return

            # Separar por tipo (patent/scholarly) e deduplicar
            # TODO: Detectar tipo de documento automaticamente

            unique_patents, dup_patents = self.dedup_service.deduplicate_patents(
                [d for d in filtered_docs if self._is_patent(d)]
            )
            unique_scholarly, dup_scholarly = self.dedup_service.deduplicate_scholarly(
                [d for d in filtered_docs if self._is_scholarly(d)]
            )

            unique_total = len(unique_patents) + len(unique_scholarly)
            dup_total = len(dup_patents) + len(dup_scholarly)

            self.result.documents_unique = unique_total

            self.result.dedup_results = {
                "total_input": len(filtered_docs),
                "patents_unique": len(unique_patents),
                "patents_duplicates": len(dup_patents),
                "scholarly_unique": len(unique_scholarly),
                "scholarly_duplicates": len(dup_scholarly),
                "total_unique": unique_total,
                "total_duplicates": dup_total,
            }

            # Armazenar documentos únicos
            self.result.details["unique_documents"] = unique_patents + unique_scholarly

            self.result.stages.append(
                StageOutput(
                    stage_name=stage_name,
                    success=True,
                    duration_seconds=time.time() - stage_start,
                    output=self.result.dedup_results,
                )
            )

        except Exception as exc:
            logger.error(
                f"stage_{stage_name}_error",
                error=str(exc),
                run_id=self.run_id,
            )
            self.result.stages.append(
                StageOutput(
                    stage_name=stage_name,
                    success=False,
                    duration_seconds=time.time() - stage_start,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
            )

    async def _stage_normalization(self) -> None:
        """
        Etapa 10: Normaliza metadados.

        Converte para estrutura padrão.
        """
        stage_start = time.time()
        stage_name = "normalization"

        try:
            logger.info(f"stage_{stage_name}_started", run_id=self.run_id)

            unique_docs = self.result.details.get("unique_documents", [])

            if not unique_docs:
                logger.warning("No unique documents to normalize")
                self.result.stages.append(
                    StageOutput(
                        stage_name=stage_name,
                        success=True,
                        duration_seconds=time.time() - stage_start,
                        output={"patents_normalized": 0, "scholarly_normalized": 0},
                    )
                )
                return

            # Normalizar patentes
            patents = [d for d in unique_docs if self._is_patent(d)]
            normalized_patents = self.normalization_service.normalize_batch(
                documents=patents,
                source="mixed",
                document_type="patent",
            )

            # Normalizar publicações
            scholarly = [d for d in unique_docs if self._is_scholarly(d)]
            normalized_scholarly = self.normalization_service.normalize_batch(
                documents=scholarly,
                source="mixed",
                document_type="scholarly",
            )

            self.result.normalized_documents = {
                "patents": len(normalized_patents),
                "scholarly": len(normalized_scholarly),
                "total": len(normalized_patents) + len(normalized_scholarly),
            }

            # Armazenar para persistência
            self.result.details["normalized_patents"] = normalized_patents
            self.result.details["normalized_scholarly"] = normalized_scholarly

            self.result.stages.append(
                StageOutput(
                    stage_name=stage_name,
                    success=True,
                    duration_seconds=time.time() - stage_start,
                    output=self.result.normalized_documents,
                )
            )

        except Exception as exc:
            logger.error(
                f"stage_{stage_name}_error",
                error=str(exc),
                run_id=self.run_id,
            )
            self.result.stages.append(
                StageOutput(
                    stage_name=stage_name,
                    success=False,
                    duration_seconds=time.time() - stage_start,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
            )

    async def _stage_persistence(self, session: AsyncSession) -> None:
        """
        Etapa 11: Persiste documentos normalizados.

        Armazena em banco de dados.
        """
        stage_start = time.time()
        stage_name = "persistence"

        try:
            logger.info(f"stage_{stage_name}_started", run_id=self.run_id)

            normalized_patents = self.result.details.get("normalized_patents", [])
            normalized_scholarly = self.result.details.get("normalized_scholarly", [])

            persistence = PersistenceService(session)

            # Persistir patentes
            patent_result = {}
            if normalized_patents:
                patent_result = await persistence.persist_batch_patent(
                    metadata_list=normalized_patents,
                    skip_if_exists=True,
                    run_id=self.run_id,
                )

            # Persistir publicações
            scholarly_result = {}
            if normalized_scholarly:
                scholarly_result = await persistence.persist_batch_scholarly(
                    metadata_list=normalized_scholarly,
                    skip_if_exists=True,
                    run_id=self.run_id,
                )

            total_persisted = (
                patent_result.get("created", 0)
                + patent_result.get("updated", 0)
                + scholarly_result.get("created", 0)
                + scholarly_result.get("updated", 0)
            )

            self.result.documents_persisted = total_persisted
            self.result.persistence_results = {
                "patents": patent_result,
                "scholarly": scholarly_result,
                "total_persisted": total_persisted,
            }

            self.result.stages.append(
                StageOutput(
                    stage_name=stage_name,
                    success=True,
                    duration_seconds=time.time() - stage_start,
                    output=self.result.persistence_results,
                )
            )

        except Exception as exc:
            logger.error(
                f"stage_{stage_name}_error",
                error=str(exc),
                run_id=self.run_id,
            )
            self.result.stages.append(
                StageOutput(
                    stage_name=stage_name,
                    success=False,
                    duration_seconds=time.time() - stage_start,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
            )

    @staticmethod
    def _is_patent(doc: dict) -> bool:
        """
        Verifica se documento é patente.

        Args:
            doc: Documento.

        Returns:
            True se é patente.
        """
        # TODO: Implementar detecção automática baseada em campos
        return doc.get("document_type") == "patent" or "publication_number" in doc

    def _enrich_prompt_with_fields(
        self,
        system_prompt: str,
        available_fields: list[str],
        api_name: str,
    ) -> str:
        """
        Enriquece prompt com especificação dinâmica de campos para busca PROBE.

        Adiciona ao sistema prompt informação sobre quais campos a LLM deve
        retornar baseado na API de PROBE configurada.

        Args:
            system_prompt: Prompt base do sistema (probe_system_prompt.txt).
            available_fields: Lista de nomes de campos disponíveis na API.
            api_name: Nome da API de PROBE (lens_patent, lens_scholarly, etc).

        Returns:
            Prompt enriquecido com especificação dinâmica dos campos esperados.
        """
        fields_section = f"""

## DYNAMIC FIELD SPECIFICATION FOR THIS PROBE SEARCH

**Probe API: {api_name.upper()}**

Return ONLY these fields in your JSON response. Do not include any other fields.

### Available Fields for this API:
{', '.join(available_fields) if available_fields else 'NONE — API configuration error'}

### CRITICAL RULES FOR THIS RESPONSE:
1. Return ONLY a valid JSON object
2. Include ONLY the fields listed above — do not add extra fields
3. For each field, return the appropriate structure:
   - Textual fields (TITLE, ABSTRACT, CLAIMS, DESCRIPTION, FULL_TEXT, KEYWORDS):
     Use structure: {{"group_operator":"AND", "groups":[{{"operator":"OR","terms":["term1","term2"]}}]}}
   - Simple fields (IPC, CPC, AUTHORS, AFFILIATION, APPLICANT, INVENTOR, FIELD_OF_STUDY, SOURCE_TITLE, YEAR):
     Use flat list: ["value1", "value2"]
4. Use EXACT field names (uppercase, matching the list above)
5. Do not include fields NOT listed above
"""

        enriched = system_prompt + fields_section

        logger.debug(
            "prompt_enriched_for_probe",
            api=api_name,
            field_count=len(available_fields),
            run_id=self.run_id,
        )

        return enriched

    def _enrich_prompt_with_final_fields(
        self,
        system_prompt: str,
        available_fields: list[str],
    ) -> str:
        """
        Enriquece prompt com especificação dinâmica de campos para busca FINAL.

        A busca final usa TODAS as APIs habilitadas, então o prompt
        inclui a union de todos os campos suportados pelas APIs ativas.

        Args:
            system_prompt: Prompt base do sistema (general_system_prompt.txt).
            available_fields: Lista de nomes de campos disponíveis nas APIs habilitadas.

        Returns:
            Prompt enriquecido com especificação dinâmica dos campos esperados.
        """
        fields_section = f"""

## DYNAMIC FIELD SPECIFICATION FOR THIS FINAL SEARCH

This is the comprehensive/final search across all enabled APIs.
Return results using ONLY the following fields:

### Available Fields for all enabled APIs:
{', '.join(sorted(available_fields)) if available_fields else 'NONE — API configuration error'}

### CRITICAL RULES FOR THIS RESPONSE:
1. Return ONLY a valid JSON object
2. Include ONLY the fields listed above — do not add extra fields
3. For each field, return the appropriate structure:
   - Textual fields (TITLE, ABSTRACT, CLAIMS, DESCRIPTION, FULL_TEXT, KEYWORDS):
     Use structure: {{"group_operator":"AND", "groups":[{{"operator":"OR","terms":["term1","term2"]}}]}}
   - Simple fields (IPC, CPC, AUTHORS, AFFILIATION, APPLICANT, INVENTOR, FIELD_OF_STUDY, SOURCE_TITLE, YEAR):
     Use flat list: ["value1", "value2"]
4. Use EXACT field names (uppercase, matching the list above)
5. Optimize for maximum coverage and recall across all enabled sources
"""

        enriched = system_prompt + fields_section

        logger.debug(
            "prompt_enriched_for_final",
            field_count=len(available_fields),
            run_id=self.run_id,
        )

        return enriched

    @staticmethod
    def _is_scholarly(doc: dict) -> bool:
        """
        Verifica se documento é publicação acadêmica.

        Args:
            doc: Documento.

        Returns:
            True se é publicação.
        """
        # TODO: Implementar detecção automática baseada em campos
        return doc.get("document_type") == "scholarly" or "doi" in doc
