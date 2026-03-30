"""
Structured logging configuration module.
"""

import json
import logging
import sys
from typing import Any

import structlog

from core.config import settings


def configure_logging() -> None:
    """
    Configura logging estruturado com structlog para toda a aplicação.

    Define formatadores, handlers e configurações para produção.
    """
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
            structlog.processors.JSONRenderer(),
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
