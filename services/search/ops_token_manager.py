"""
Gerenciador centralizado de token OAuth2 do OPS.

Mantém um token compartilhado em memória, evitando renovações desnecessárias
e garantindo que todas as requisições usem o mesmo token válido.
Similar a um store global (como Zustand no frontend).
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional

import httpx

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


class OPSToken:
    """Representa um token OAuth2 do OPS com informações de expiração."""

    def __init__(self, access_token: str, expires_in: int) -> None:
        """
        Inicializa com token de acesso.

        Args:
            access_token: Token de acesso OAuth2.
            expires_in: Duração em segundos.
        """
        self.access_token = access_token
        self.expires_in = expires_in
        self.created_at = datetime.utcnow()
        self.expiration_time = self.created_at + timedelta(seconds=expires_in)

    def is_expired(self) -> bool:
        """Verifica se token está expirado com margem de 60 segundos."""
        return datetime.utcnow() >= (self.expiration_time - timedelta(seconds=60))

    def to_dict(self) -> dict:
        """Retorna dict com informações do token."""
        return {
            "access_token": self.access_token,
            "expires_in": self.expires_in,
            "created_at": self.created_at.isoformat(),
            "expiration_time": self.expiration_time.isoformat(),
        }


class OPSTokenManager:
    """
    Gerenciador centralizado de token OAuth2 do OPS.

    Mantém um token compartilhado em memória, evitando renovações desnecessárias.
    Thread-safe com lock assíncrono para requisições simultâneas.
    """

    _instance: Optional["OPSTokenManager"] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __new__(cls) -> "OPSTokenManager":
        """Padrão Singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Inicializa gerenciador de token (apenas uma vez)."""
        if self._initialized:
            return

        self.token: Optional[OPSToken] = None
        self.consumer_key = settings.ops_consumer_key
        self.consumer_secret = settings.ops_consumer_secret
        self.async_client = httpx.AsyncClient()
        self._OPS_TOKEN_URL = "https://ops.epo.org/auth/accesstoken"
        self._last_error: str = ""
        self._initialized = True

        logger.info("ops_token_manager_initialized")

    async def get_valid_token(self) -> Optional[str]:
        """
        Obtém um token válido, renovando se necessário.

        Usa lock assíncrono para evitar requisições simultâneas de renovação.

        Returns:
            Token de acesso válido ou None se falhar.
        """
        # Verificação rápida sem lock
        if self.token and not self.token.is_expired():
            return self.token.access_token

        # Renovar sob lock para evitar race conditions
        async with self._lock:
            # Double-check após adquirir lock
            if self.token and not self.token.is_expired():
                return self.token.access_token

            # Renovar token
            success, error_msg = await self._refresh_token()
            if success and self.token:
                self._last_error = ""
                return self.token.access_token
            else:
                self._last_error = error_msg
                logger.error(
                    "ops_token_manager_token_unavailable",
                    reason=error_msg,
                )

        return None

    async def _refresh_token(self) -> tuple[bool, str]:
        """
        Obtém novo token OAuth2 do OPS.

        Returns:
            Tupla (sucesso, mensagem_erro). Se sucesso, mensagem_erro é "OK".
        """
        try:
            # Validar credenciais
            if not self.consumer_key or not self.consumer_secret:
                error_msg = "Missing OPS credentials (consumer_key or consumer_secret not set)"
                logger.error(
                    "ops_token_missing_credentials",
                    has_consumer_key=bool(self.consumer_key),
                    has_consumer_secret=bool(self.consumer_secret),
                )
                return False, error_msg

            logger.info(
                "ops_token_refresh_requested",
                url=self._OPS_TOKEN_URL,
            )

            response = await self.async_client.post(
                self._OPS_TOKEN_URL,
                auth=(self.consumer_key, self.consumer_secret),
                data={"grant_type": "client_credentials"},
                timeout=30,
            )

            response.raise_for_status()
            data = response.json()

            if "access_token" in data:
                access_token = data["access_token"]
                expires_in = int(data.get("expires_in", 3600))

                self.token = OPSToken(access_token, expires_in)

                logger.info(
                    "ops_token_refreshed",
                    expires_at=self.token.expiration_time.isoformat(),
                    token_type=data.get("token_type"),
                )
                return True, "OK"
            else:
                error_msg = f"No access_token in response: {data}"
                logger.error("ops_token_refresh_no_token", response=data)
                return False, error_msg

        except httpx.TimeoutException as exc:
            error_msg = f"Timeout connecting to OPS auth server (30s) - check network connectivity"
            logger.error(
                "ops_token_refresh_timeout",
                error=error_msg,
                url=self._OPS_TOKEN_URL,
            )
            return False, error_msg

        except httpx.HTTPStatusError as exc:
            error_msg = f"OPS auth server returned HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            logger.error(
                "ops_token_refresh_http_error",
                status_code=exc.response.status_code,
                response=exc.response.text[:200],
                url=self._OPS_TOKEN_URL,
            )
            return False, error_msg

        except httpx.ConnectError as exc:
            error_msg = f"Failed to connect to OPS auth server - check if ops.epo.org is accessible"
            logger.error(
                "ops_token_refresh_connect_error",
                error=str(exc),
                url=self._OPS_TOKEN_URL,
            )
            return False, error_msg

        except Exception as exc:
            error_msg = str(exc) if str(exc) else f"{type(exc).__name__}: unknown error"
            logger.error(
                "ops_token_refresh_failed",
                error=error_msg,
                error_type=type(exc).__name__,
                url=self._OPS_TOKEN_URL,
            )
            return False, error_msg

    async def close(self) -> None:
        """Fecha cliente HTTP."""
        await self.async_client.aclose()


# Singleton global
ops_token_manager = OPSTokenManager()
