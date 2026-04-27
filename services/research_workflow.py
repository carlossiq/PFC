"""
Research workflow coordinator.

Orchestrates the complete research workflow, coordinating between
pipeline functions and database persistence via ResearchService.
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from db.research_models import Research
from schemas.intake import InputIntake
from services.research_service import ResearchService
from services.tools import pipeline

logger = get_logger(__name__)


class ResearchWorkflow:
    """
    Coordena todo o fluxo de pesquisa de ponta a ponta.

    Gerencia:
    - Criação do registro de pesquisa
    - Coordenação entre funções do pipeline
    - Persistência de dados em cada etapa
    - Rastreamento de timing de cada fase
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Inicializa o coordenador de fluxo.

        Args:
            session: Sessão de banco de dados.
        """
        self.session = session
        self.research_service = ResearchService()
        self.research: Optional[Research] = None
        self.research_id: Optional[int] = None

    async def start_research(self, title: str, description: Optional[str] = None) -> Research:
        """
        Inicia uma nova pesquisa.

        Args:
            title: Título da pesquisa.
            description: Descrição (opcional).

        Returns:
            Research record criado.
        """
        self.research = await self.research_service.create_research(
            self.session,
            title=title,
            description=description,
        )
        self.research_id = self.research.id
        logger.info("research_workflow_started", research_id=self.research_id, title=title)
        return self.research

    async def refine_topic(
        self,
        theme: str,
        description: Optional[str] = None,
        area_of_study: Optional[str] = None,
        keywords: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Refina o tema inicial com 4 variações.

        Args:
            theme: Tema principal.
            description: Descrição (opcional).
            area_of_study: Área de estudo (opcional).
            keywords: Palavras-chave (opcional).

        Returns:
            Resultado do pipeline com 4 tópicos refinados.
        """
        if not self.research_id:
            raise RuntimeError("Research not started. Call start_research() first.")

        start_time = datetime.utcnow()

        try:
            result = await pipeline.refine_topic(
                theme=theme,
                description=description,
                area_of_study=area_of_study,
                keywords=keywords,
            )

            # Armazenar parâmetros iniciais
            user_input = {
                "theme": theme,
                "description": description,
                "area_of_study": area_of_study,
                "keywords": keywords,
            }

            self.research.user_input = user_input

            # Armazenar candidatos refinados
            if result.get("success"):
                candidates = result.get("candidates", [])
                await self.research_service.update_refined_candidates(
                    self.session,
                    self.research_id,
                    candidates=candidates,
                    chosen={},
                )

            # Registar timing
            await self.research_service.add_phase_timing(
                self.session,
                self.research_id,
                phase_name="refine_topic",
                started_at=start_time,
                completed_at=datetime.utcnow(),
                status="completed" if result.get("success") else "failed",
                error_message=result.get("error") if not result.get("success") else None,
            )

            logger.info(
                "research_workflow_refine_topic_completed",
                research_id=self.research_id,
                candidates_count=len(result.get("candidates", [])),
            )

            return result

        except Exception as exc:
            logger.error(
                "research_workflow_refine_topic_error",
                research_id=self.research_id,
                error=str(exc),
            )
            # Registar erro
            await self.research_service.add_phase_timing(
                self.session,
                self.research_id,
                phase_name="refine_topic",
                started_at=start_time,
                completed_at=datetime.utcnow(),
                status="failed",
                error_message=str(exc),
            )
            raise

    async def build_and_execute_probe_search(
        self,
        intake: InputIntake,
        api: str = "ops",
    ) -> dict[str, Any]:
        """
        Constrói e executa a busca exploratória (probe search).

        Args:
            intake: Parâmetros da busca (tema escolhido).
            api: API a usar (ops, scopus, etc).

        Returns:
            Resultados da busca com dados enriquecidos.
        """
        if not self.research_id:
            raise RuntimeError("Research not started. Call start_research() first.")

        start_time = datetime.utcnow()

        try:
            # Construir query de probe
            query_result = await pipeline.build_probe_query(intake, api)
            if not query_result.get("success"):
                raise ValueError(f"Failed to build probe query: {query_result.get('error')}")

            probe_query = query_result.get("query")

            # Armazenar query de probe
            await self.research_service.update_probe_query(
                self.session,
                self.research_id,
                query=probe_query,
                api=api,
            )

            # Executar busca de probe
            search_result = await pipeline.run_probe_search(query=probe_query, api=api)

            logger.info(
                "research_workflow_probe_search_completed",
                research_id=self.research_id,
                results_count=search_result.get("results_count", 0),
                api=api,
            )

            # Registar timing
            await self.research_service.add_phase_timing(
                self.session,
                self.research_id,
                phase_name="probe_search",
                started_at=start_time,
                completed_at=datetime.utcnow(),
                status="completed" if search_result.get("success") else "failed",
                error_message=search_result.get("error") if not search_result.get("success") else None,
            )

            return search_result

        except Exception as exc:
            logger.error(
                "research_workflow_probe_search_error",
                research_id=self.research_id,
                error=str(exc),
            )
            await self.research_service.add_phase_timing(
                self.session,
                self.research_id,
                phase_name="probe_search",
                started_at=start_time,
                completed_at=datetime.utcnow(),
                status="failed",
                error_message=str(exc),
            )
            raise

    async def extract_terms(
        self,
        enriched_results: list[dict[str, Any]],
        original_params: dict[str, Any],
        top_k: int = 20,
    ) -> dict[str, Any]:
        """
        Extrai termos relevantes de resultados.

        Args:
            enriched_results: Resultados da busca de probe.
            original_params: Parâmetros originais da busca.
            top_k: Número de termos a extrair.

        Returns:
            Termos extraídos com scores.
        """
        if not self.research_id:
            raise RuntimeError("Research not started. Call start_research() first.")

        start_time = datetime.utcnow()

        try:
            result = await pipeline.extract_relevant_terms(
                enriched_results=enriched_results,
                original_params=original_params,
                top_k=top_k,
            )

            # Armazenar termos extraídos
            if result.get("success"):
                terms = result.get("terms", [])
                await self.research_service.update_extracted_terms(
                    self.session,
                    self.research_id,
                    terms=terms,
                )

            # Registar timing
            await self.research_service.add_phase_timing(
                self.session,
                self.research_id,
                phase_name="term_extraction",
                started_at=start_time,
                completed_at=datetime.utcnow(),
                status="completed" if result.get("success") else "failed",
                error_message=result.get("error") if not result.get("success") else None,
            )

            logger.info(
                "research_workflow_term_extraction_completed",
                research_id=self.research_id,
                terms_count=len(result.get("terms", [])),
            )

            return result

        except Exception as exc:
            logger.error(
                "research_workflow_term_extraction_error",
                research_id=self.research_id,
                error=str(exc),
            )
            await self.research_service.add_phase_timing(
                self.session,
                self.research_id,
                phase_name="term_extraction",
                started_at=start_time,
                completed_at=datetime.utcnow(),
                status="failed",
                error_message=str(exc),
            )
            raise

    async def build_final_queries(
        self,
        intake: InputIntake,
        extracted_terms: list[dict[str, Any]],
        api: str = "ops",
    ) -> dict[str, Any]:
        """
        Constrói 3 variações de query final.

        Args:
            intake: Parâmetros da busca.
            extracted_terms: Termos extraídos com scores.
            api: API a usar.

        Returns:
            3 variações de query (specific, balanced, generic).
        """
        if not self.research_id:
            raise RuntimeError("Research not started. Call start_research() first.")

        start_time = datetime.utcnow()

        try:
            result = await pipeline.build_final_queries_with_extraction(
                intake=intake,
                extracted_terms=extracted_terms,
                api=api,
            )

            # Armazenar queries finais
            if result.get("success"):
                queries = result.get("queries", {})
                await self.research_service.update_final_queries(
                    self.session,
                    self.research_id,
                    specific_query=queries.get("specific", {}),
                    balanced_query=queries.get("balanced", {}),
                    generic_query=queries.get("generic", {}),
                    chosen="balanced",  # Default to balanced
                )

            # Registar timing
            await self.research_service.add_phase_timing(
                self.session,
                self.research_id,
                phase_name="final_query_generation",
                started_at=start_time,
                completed_at=datetime.utcnow(),
                status="completed" if result.get("success") else "failed",
                error_message=result.get("error") if not result.get("success") else None,
            )

            logger.info(
                "research_workflow_final_queries_completed",
                research_id=self.research_id,
                queries_count=len(result.get("queries", {})),
            )

            return result

        except Exception as exc:
            logger.error(
                "research_workflow_final_queries_error",
                research_id=self.research_id,
                error=str(exc),
            )
            await self.research_service.add_phase_timing(
                self.session,
                self.research_id,
                phase_name="final_query_generation",
                started_at=start_time,
                completed_at=datetime.utcnow(),
                status="failed",
                error_message=str(exc),
            )
            raise

    async def execute_final_search(
        self,
        query: dict[str, Any],
        api: str,
        query_variant: str = "balanced",
        max_results: int = 500,
    ) -> dict[str, Any]:
        """
        Executa a busca final e armazena resultados.

        Args:
            query: Query final selecionada.
            api: API a usar.
            query_variant: Qual variação foi escolhida (specific, balanced, generic).
            max_results: Máximo de resultados.

        Returns:
            Resultados completos da busca.
        """
        if not self.research_id:
            raise RuntimeError("Research not started. Call start_research() first.")

        start_time = datetime.utcnow()

        try:
            result = await pipeline.run_final_search(
                query=query,
                api=api,
                max_results=max_results,
            )

            # Armazenar resultados
            if result.get("success"):
                results = result.get("results", [])

                # Determinar se são patentes ou artigos baseado na API
                is_patent = api in ["ops", "lens_patent"]

                for doc in results:
                    if is_patent:
                        await self.research_service.add_patent_result(
                            self.session,
                            self.research_id,
                            patent_data=doc,
                            query_variant=query_variant,
                        )
                    else:
                        await self.research_service.add_scholarly_result(
                            self.session,
                            self.research_id,
                            article_data=doc,
                            query_variant=query_variant,
                        )

            # Registar timing
            await self.research_service.add_phase_timing(
                self.session,
                self.research_id,
                phase_name="final_search",
                started_at=start_time,
                completed_at=datetime.utcnow(),
                status="completed" if result.get("success") else "failed",
                error_message=result.get("error") if not result.get("success") else None,
            )

            logger.info(
                "research_workflow_final_search_completed",
                research_id=self.research_id,
                results_count=result.get("results_count", 0),
                api=api,
                variant=query_variant,
            )

            return result

        except Exception as exc:
            logger.error(
                "research_workflow_final_search_error",
                research_id=self.research_id,
                error=str(exc),
            )
            await self.research_service.add_phase_timing(
                self.session,
                self.research_id,
                phase_name="final_search",
                started_at=start_time,
                completed_at=datetime.utcnow(),
                status="failed",
                error_message=str(exc),
            )
            raise
