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
    database_url: str = "sqlite:///./app.db"

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
    llm_qwen3_api_key: Optional[str] = None
    llm_qwen3_model: str = "qwen-max"

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
    relevance_threshold: float = 0.5

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
