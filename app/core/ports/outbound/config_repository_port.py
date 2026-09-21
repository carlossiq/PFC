from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from app.core.domain.config_types import (
    AppSettingValue,
    LLMCallSiteBindingData,
    LLMProviderConfigData,
    SearchApiSelectionData,
)


@runtime_checkable
class AppSettingsRepositoryPort(Protocol):
    async def list_all(self) -> list[AppSettingValue]: ...

    async def get(self, key: str) -> Optional[AppSettingValue]: ...

    async def update_value(self, key: str, value: str) -> AppSettingValue: ...


@runtime_checkable
class SearchApiSelectionRepositoryPort(Protocol):
    async def list_all(self) -> list[SearchApiSelectionData]: ...

    async def get(self, family: str) -> Optional[SearchApiSelectionData]: ...

    async def set_active(self, family: str, provider_code: str) -> SearchApiSelectionData: ...


@runtime_checkable
class LLMConfigRepositoryPort(Protocol):
    async def list_configs(self) -> list[LLMProviderConfigData]: ...

    async def get_config(self, config_id: int) -> Optional[LLMProviderConfigData]: ...

    async def create_config(self, data: LLMProviderConfigData) -> LLMProviderConfigData: ...

    async def update_config(self, config_id: int, data: LLMProviderConfigData) -> LLMProviderConfigData: ...

    async def delete_config(self, config_id: int) -> None: ...

    async def list_bindings(self) -> list[LLMCallSiteBindingData]: ...

    async def get_binding(self, call_site: str) -> Optional[LLMCallSiteBindingData]: ...

    async def set_binding(self, call_site: str, config_id: int) -> LLMCallSiteBindingData: ...
