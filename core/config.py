"""
Configuration module for application settings management.
"""

from typing import Optional

from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Aplicação de configurações usando Pydantic Settings.

    Carrega variáveis de ambiente do arquivo .env e sobrescreve com
    variáveis de ambiente do sistema operacional.
    """

    # Application
    app_name: str = "Technology Prospecting API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    # Ecoa toda query SQL executada (SQLAlchemy `echo`) - desligado por
    # padrão mesmo com debug=True, pra não poluir o log com uma query por
    # linha (era o principal motivo do log de inicialização ficar ilegível,
    # ver init_db()/seed_all_config() que rodam dezenas de INSERTs no boot).
    # Ligar só quando for depurar uma query específica.
    sql_echo: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # API
    api_prefix: str = "/api/v1"
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pfc_db"

    # Security
    secret_key: str = "65E3ifwj_6WAL3FBVmOIpg4axw656GNbEOqYTJdx-cg"
    algorithm: str = "HS256"

    # LLM Configuration
    llm_provider: str = "mock"
    test_mode: bool = False
    llm_gemini_api_key: Optional[str] = None
    llm_gemini_model: str = "gemini-2.0-flash-exp"
    llm_anthropic_api_key: Optional[str] = None
    llm_anthropic_model: str = "claude-haiku-4-5"

    # KeyBERT Model Configuration (sentence-transformers)
    # Options:
    #   - "distiluse-base-multilingual-cased-v2": genérico multilíngue
    #   - "all-mpnet-base-v2": melhor para patentes e textos técnicos (RECOMENDADO para OPS)
    #   - "allenai/specter": treinado em papers acadêmicos
    # Mude conforme seu dataset: patentes, artigos, ou genérico
    llm_keybert_model: str = "distiluse-base-multilingual-cased-v2"

    # External APIs
    lens_api_token: Optional[str] = None
    ops_consumer_key: Optional[str] = None
    ops_consumer_secret: Optional[str] = None
    scopus_api_key: Optional[str] = None

    # Search Configuration
    search_year_from: int = 2015
    search_year_to: int = 2026
    probe_top_k: int = 10  # Número de resultados para busca probe
    final_top_k: int = 100  # Número de resultados para busca final

    # Relevance Configuration
    relevance_threshold: float = 0.4

    # Query Complexity Configuration
    llm_max_query_complexity: float = 0.6

    # Term Extraction Configuration
    term_extraction_title_weight: float = 3.0  # Peso para termos extraídos de títulos
    term_extraction_abstract_weight: float = (
        1.0  # Peso para termos extraídos de abstracts
    )
    # Score threshold: mínimo para retornar termos
    # ATENÇÃO: escala mudou com a migração para BM25F+RRF (ver
    # TESTE_EXTRACAO_TERMOS_BM25F_RRF.md) - final_rrf_score é soma de dois
    # termos 1/(k+rank), faixa observada empiricamente em ~459 termos de
    # calibração: min=0.0184 max=0.0325 mean=0.0244 median=0.0244.
    # 0.024 ~ corta pela mediana (mantém a metade melhor de cada
    # amostra, ~20-25 termos/busca, comparável ao volume do threshold
    # antigo de 0.35 na escala 0-1).
    # Aumentar → menos termos, só os melhores
    # Diminuir → mais termos, incluindo contexto
    term_extraction_score_threshold: float = 0.024

    # Piso de termos devolvidos, independente do threshold acima.
    # final_rrf_score é relativo ao rank DENTRO do lote (RRF), não uma escala
    # absoluta - o intervalo numérico muda com o tamanho do lote e a
    # composição de qualidade dos candidatos, então o threshold fixo pode
    # deixar um lote inteiro abaixo do corte (observado: lote de 315
    # candidatos onde até o 1º colocado ficou abaixo de 0.024, devolvendo 0
    # termos). Se o threshold deixar menos que esse piso, completa com os
    # próximos melhor-ranqueados abaixo do corte em vez de devolver uma
    # lista vazia ou rala demais pro usuário selecionar.
    term_extraction_min_returned_terms: int = 10

    # N-gram Size-Based Score Adjustments
    # Usadas por TermExtractor._structural_quality_score() para RANKEAR
    # candidatos entre si via RRF (não são mais somadas ao score - ver
    # TESTE_EXTRACAO_TERMOS_BM25F_RRF.md)
    term_extraction_unigram_penalty: float = -0.4  # Penalidade para 1-grams
    term_extraction_bigram_bonus: float = 0.0  # Bônus/penalidade para 2-grams
    term_extraction_trigram_bonus: float = 0.25  # Bônus para 3-grams (e maiores)

    # Bad POS Pattern Penalties (applied when bad pattern detected)
    term_extraction_bad_bigram_penalty: float = (
        -0.8
    )  # Penalidade para 2-grams com padrão ruim
    term_extraction_bad_trigram_penalty: float = (
        -0.8
    )  # Penalidade para 3-grams com padrão ruim

    # BM25F (canal lexical, substitui TfidfVectorizer) - k1/b padrão de Okapi BM25
    term_extraction_bm25_k1: float = 1.2
    term_extraction_bm25_b: float = 0.75

    # RRF (Reciprocal Rank Fusion) - usado em 2 estágios: BM25F×KeyBERT
    # (salience_score) e salience×qualidade estrutural (final_rrf_score).
    # 60 é o default também usado pelo Elasticsearch para este parâmetro.
    term_extraction_rrf_k: int = 60

    # C-value: candidatos com frequência bruta abaixo deste piso são
    # descartados antes mesmo do cálculo de c_value (substitui o filtro de
    # sobreposição/subsunção antigo)
    term_extraction_cvalue_min_frequency: int = 1

    # MinIO Configuration (armazenamento dos gráficos gerados, ver ReportService/StoragePort)
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "session-charts"
    minio_secure: bool = False

    # Relatório LaTeX (RAG local + LLM compatível com OpenAI) - ver
    # app/core/services/report_writer_service.py e
    # app/adapters/driven/llm/openai_compatible_adapter.py. `ollama_base_url`
    # aponta pro container Ollama local em dev (docker-compose.yml) ou pro
    # endpoint da intranet em produção - troca é só configuração, o adapter
    # é o mesmo nos dois casos (ambos expõem /v1/chat/completions). Segredos
    # reais (API key da intranet) só em `.env`, nunca aqui/`.env.example`.
    ollama_base_url: str = "http://localhost:11434"
    ollama_api_key: Optional[str] = None
    ollama_model: str = "qwen2.5:3b-instruct"
    ollama_request_timeout_seconds: int = 600

    # ChromaDB (vector store do RAG) - roda como container HTTP (chromadb/chroma
    # em docker-compose.yml), não embutido, pra ser seguro com múltiplos
    # workers do backend (ver app/adapters/driven/storage/chroma_adapter.py).
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    rag_top_k_per_section: int = 5

    # Compilação de PDF do relatório - serviço HTTP dedicado (texlive), só
    # chamado sob demanda (POST /report/{session_id}/compile-pdf), nunca
    # automaticamente na montagem do .tex.
    latex_compiler_url: str = "http://localhost:8090"

    # Fuzzy Matching de entidades (busca final OPS/Scopus)
    # Agrupa entidades que provavelmente são a mesma (variações de
    # grafia/pontuação/sufixo societário, ex: "Acme Corp" vs "ACME CORP."
    # vs "Acme Corporation") antes de contar - compartilhado por
    # depositantes de patente (ChatService._fuzzy_group_depositants) e
    # instituições de artigo (ChatService._fuzzy_group_institutions), ambos
    # delegando pro mesmo helper (services.nlp.fuzzy_grouping.fuzzy_group_names)
    # com este threshold - mesma natureza de problema (variação de grafia de
    # nome de entidade) nas duas fontes. Score 0-100 do rapidfuzz (fuzz.WRatio); 90 é
    # conservador o suficiente pra não fundir entidades distintas com nomes
    # parecidos (ex: "Acme Inc" vs "Acme Solutions Inc"), mas pega
    # variações triviais de grafia. Diminuir agrupa mais agressivamente
    # (risco de falsos positivos); aumentar agrupa menos.
    depositant_fuzzy_match_threshold: float = 90.0

    # Statistical Inference Configuration (Chao1 + Bootstrap)
    # Ver app/core/services/statistical_inference_service.py e
    # app/core/services/sample_statistics.py. A rota /inference/final-search
    # pede iterações extras de run_final_search (iteration=1,2,...) até a
    # amostra "saturar" (Chao1) ou esse teto de tempo acabar - o que vier
    # primeiro.
    statistical_inference_max_duration_seconds: int = 60

    # Critério composto de "amostra insuficiente" (is_sample_insufficient) -
    # QUALQUER UM dos três abaixo sendo verdadeiro já conta como
    # insuficiente:
    # - saturação (S_obs/S_chao1, cobertura estimada) abaixo deste valor.
    statistical_inference_saturation_threshold: float = 0.5
    # - proporção de singletons (categorias vistas só 1x) acima deste valor
    #   entre as categorias observadas - sinal de cauda longa não capturada.
    statistical_inference_f1_ratio_threshold: float = 0.7
    # - nº de doubletons (categorias vistas exatamente 2x) abaixo deste
    #   valor - poucas repetições pra uma estimativa Chao1 estável.
    statistical_inference_f2_min: int = 5

    # Nº de reamostragens (bootstrap, com reposição) usadas pra medir a
    # estabilidade do ranking top-10 - xx de cada entidade no top10 da
    # resposta é a fração dessas reamostragens em que ela permaneceu entre
    # as 10 primeiras.
    statistical_inference_bootstrap_resamples: int = 1000

    # Nº máximo de títulos amostrados aleatoriamente (em inglês) pra
    # calcular a relevância semântica (SBERT) média com o tema da pesquisa.
    statistical_inference_max_titles_for_relevance: int = 20

    # Feature flags - APIs habilitadas (busca final)
    lens_patent_enabled: bool = True
    lens_scholarly_enabled: bool = True
    ops_enabled: bool = True
    scopus_enabled: bool = True

    # Retrocompatibilidade: lens_enabled ativa ambas as APIs Lens
    lens_enabled: bool = True

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: str | list[str]) -> list[str]:
        """
        Parse allowed_origins from comma-separated string or list.

        Args:
            v: Environment variable value or list.

        Returns:
            List of allowed origins.
        """
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    def get_server_url(self) -> str:
        """
        Retorna a URL completa do servidor.
        """
        return f"http://{self.host}:{self.port}"


settings = Settings()
