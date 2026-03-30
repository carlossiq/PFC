"""
Configuration module for application settings management.
"""

from typing import Optional

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
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"

    class Config:
        """Configuração do Pydantic."""

        env_file: str = ".env"
        env_file_encoding: str = "utf-8"
        case_sensitive: bool = False

    def get_server_url(self) -> str:
        """
        Retorna a URL completa do servidor.
        """
        return f"http://{self.host}:{self.port}"


settings = Settings()
