"""
Structured logging configuration module.
"""

import json
import logging
import sys
from typing import Any

import structlog

from core.config import settings


# Bibliotecas de terceiros que logam em INFO por padrão e não agregam nada
# pertinente ao dia a dia (uma linha por request HTTP interno, por query SQL
# etc.) - subidas pra WARNING sempre, independente de settings.log_level.
# `sqlalchemy.engine` aqui é só defesa extra: o principal motivo dela logar
# em INFO é `echo=True` no engine (ver db/session.py), que já é False por
# padrão (settings.sql_echo) - mas SQLAlchemy reafirma o nível pra INFO
# sempre que echo=True em qualquer lugar (inclusive scripts/testes), então
# vale silenciar aqui como rede de segurança.
_NOISY_THIRD_PARTY_LOGGERS = (
    "sqlalchemy.engine",
    "sqlalchemy.pool",
    "httpx",
    "httpcore",
)


def configure_logging() -> None:
    """
    Configura logging estruturado com structlog para toda a aplicação.

    Em desenvolvimento, renderiza em texto legível (uma linha por evento,
    "evento  chave=valor") em vez de JSON puro - muito mais fácil de
    acompanhar o log de inicialização/requests a olho. Produção continua em
    JSON (uma linha por evento, mas parseável por ferramenta de agregação de
    log).
    """
    is_dev = settings.environment != "production"
    renderer = structlog.dev.ConsoleRenderer() if is_dev else structlog.processors.JSONRenderer()

    # Configurar structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            renderer,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configurar logging stdlib
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=settings.log_level,
    )

    for logger_name in _NOISY_THIRD_PARTY_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Obtém um logger estruturado para um módulo específico.

    Args:
        name: Nome do módulo para identificar na origem do log.

    Returns:
        Instância de BoundLogger configurada.
    """
    return structlog.get_logger(name)


class StructuredLogger:
    """
    Wrapper para facilitar logging estruturado com contexto adicional.
    """

    def __init__(self, name: str) -> None:
        """
        Inicializa o logger estruturado.

        Args:
            name: Nome do módulo.
        """
        self.logger = get_logger(name)

    def info(self, message: str, **context: Any) -> None:
        """
        Log em nível INFO com contexto estruturado.

        Args:
            message: Mensagem principal do log.
            **context: Dados contextuais adicionais.
        """
        self.logger.info(message, **context)

    def error(self, message: str, **context: Any) -> None:
        """
        Log em nível ERROR com contexto estruturado.

        Args:
            message: Mensagem principal do log.
            **context: Dados contextuais adicionais.
        """
        self.logger.error(message, **context)

    def warning(self, message: str, **context: Any) -> None:
        """
        Log em nível WARNING com contexto estruturado.

        Args:
            message: Mensagem principal do log.
            **context: Dados contextuais adicionais.
        """
        self.logger.warning(message, **context)

    def debug(self, message: str, **context: Any) -> None:
        """
        Log em nível DEBUG com contexto estruturado.

        Args:
            message: Mensagem principal do log.
            **context: Dados contextuais adicionais.
        """
        self.logger.debug(message, **context)
