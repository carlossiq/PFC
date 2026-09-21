"""
Sincroniza app_settings (banco) com o singleton `core.config.settings`
(Pydantic, mutável) - ver PLANO_MIGRACAO_CONFIG_BANCO.md § 4.1.

Por que fazer assim em vez de reescrever os ~50 pontos de leitura
(`settings.x` / `getattr(settings, "x", default)`) espalhados pelo código:
o singleton já é lido exatamente desse jeito em todo lugar hoje - carregar
os valores do banco e sobrescrever os atributos do MESMO objeto (`setattr`)
faz esses ~50 pontos de leitura continuarem funcionando sem nenhuma mudança,
e ganharem "hot reload" de graça (editar no front chama `apply_one` aqui,
que atualiza o singleton em memória imediatamente, sem restart).

Limitação aceita: só funciona em single-process (um worker uvicorn) - ver
PLANO_MIGRACAO_CONFIG_BANCO.md § 8.
"""

from __future__ import annotations

from core.config import settings as live_settings
from core.logging import get_logger
from app.core.domain.config_types import AppSettingValue
from app.core.ports.outbound.config_repository_port import AppSettingsRepositoryPort

logger = get_logger(__name__)


class SettingsSyncService:
    def __init__(self, repository: AppSettingsRepositoryPort) -> None:
        self._repository = repository

    async def load_all_into_singleton(self) -> None:
        rows = await self._repository.list_all()
        for row in rows:
            self._apply_to_singleton(row)
        logger.info("settings_sync_loaded", count=len(rows))

    async def update_and_apply(self, key: str, value: str) -> AppSettingValue:
        row = await self._repository.update_value(key, value)
        self._apply_to_singleton(row)
        logger.info("settings_sync_updated", key=key)
        return row

    @staticmethod
    def _apply_to_singleton(row: AppSettingValue) -> None:
        setattr(live_settings, row.key, row.typed_value())
