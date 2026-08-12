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
    llm_anthropic_model: str = "claude-3-5-sonnet-20241022"

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
    probe_api: str = "lens_patent"
    probe_api_ext: str = ""  # Vazio por padrão, habilitar no .env se necessário
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
    # Score threshold: mínimo para retornar termos (0.0-1.0)
    # Aumentar → menos termos, só os melhores (ex: 0.50)
    # Diminuir → mais termos, incluindo contexto (ex: 0.15)
    # Ajustado para all-mpnet-base-v2 (modelo para patentes)
    term_extraction_score_threshold: float = 0.35

    # MMR Lambda: balanço entre relevância e diversidade (0.0-1.0)
    # 1.0 = 100% relevância, 0% diversidade (pode ter termos muito similares)
    # 0.5 = 50% relevância, 50% diversidade (balanço)
    # 0.0 = 0% relevância, 100% diversidade (máxima diversidade)
    # Default 0.55: prioriza relevância (55%) mantendo diversidade (45%)
    # Aumentar para 0.80+ se preferir termos mais relevantes que diversos
    # Diminuir para 0.30 se preferir máxima diversidade
    term_extraction_mmr_lambda: float = 0.45

    # MMR Similarity Threshold: filtra termos muito similares (0.0-1.0)
    # 1.0 = pula termos 100% similares (aceita tudo que não é idêntico)
    # 0.5 = pula termos >50% similares (padrão: rejeita duplicatas próximas)
    # 0.3 = pula termos >30% similares (muito restritivo)
    # Default 0.5: bom balanço, remove duplicatas sem perder termos relacionados
    # Aumentar para 0.70 se quiser agrupar termos relacionados
    # Diminuir para 0.30 se quiser máxima diversidade
    term_extraction_mmr_similarity_threshold: float = 0.5

    # Overlap Threshold: filtra termos com alta sobreposição de palavras (0.0-1.0)
    # Usa word overlap ratio: shared_words / min(term_a_words, term_b_words)
    # 1.0 = remove apenas termos idênticos
    # 0.75 = remove termos com >75% palavras iguais
    # 0.67 = remove termos com >67% palavras iguais (padrão: bom balanço)
    # 0.50 = remove termos com >50% palavras iguais (muito restritivo)
    # Default 0.67: mantém diversidade removendo apenas termos muito similares
    # Aumentar para 0.80 se quiser aceitar mais termos similares
    # Diminuir para 0.50 se quiser máxima diversidade
    term_extraction_overlap_threshold: float = 0.66

    # N-gram Size-Based Score Adjustments
    # Aplicadas em _get_score_adjustments() do term_extraction.py
    term_extraction_unigram_penalty: float = -0.4  # Penalidade para 1-grams
    term_extraction_bigram_bonus: float = 0.0  # Bônus/penalidade para 2-grams
    term_extraction_trigram_bonus: float = 0.25  # Bônus para 3-grams

    # Bad POS Pattern Penalties (applied when bad pattern detected)
    term_extraction_bad_bigram_penalty: float = (
        -0.8
    )  # Penalidade para 2-grams com padrão ruim
    term_extraction_bad_trigram_penalty: float = (
        -0.8
    )  # Penalidade para 3-grams com padrão ruim

    # Report Configuration
    report_output_dir: str = "gerados"

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
