from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain.config_types import (
    AppSettingValue,
    LLMCallSiteBindingData,
    LLMProviderConfigData,
    SearchApiSelectionData,
)
from db.config_models import (
    AppSetting,
    LLMCallSiteBinding,
    LLMProviderConfig,
    SearchApiSelection,
)


def _setting_to_domain(row: AppSetting) -> AppSettingValue:
    return AppSettingValue(
        key=row.key,
        value=row.value,
        value_type=row.value_type,
        category=row.category,
        is_secret=row.is_secret,
        min_value=row.min_value,
        max_value=row.max_value,
        step=row.step,
        label=row.label,
        description=row.description,
        default_value=row.default_value,
    )


def _llm_config_to_domain(row: LLMProviderConfig) -> LLMProviderConfigData:
    return LLMProviderConfigData(
        id=row.id,
        provider_code=row.provider_code,
        model=row.model,
        api_key=row.api_key,
        base_url=row.base_url,
    )


class AppSettingsRepositoryAdapter:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[AppSettingValue]:
        result = await self._session.execute(select(AppSetting).order_by(AppSetting.category, AppSetting.key))
        return [_setting_to_domain(row) for row in result.scalars().all()]

    async def get(self, key: str) -> Optional[AppSettingValue]:
        row = await self._session.get(AppSetting, key)
        return _setting_to_domain(row) if row else None

    async def update_value(self, key: str, value: str) -> AppSettingValue:
        row = await self._session.get(AppSetting, key)
        if row is None:
            raise KeyError(f"Unknown setting key: {key!r}")
        row.value = value
        await self._session.commit()
        await self._session.refresh(row)
        return _setting_to_domain(row)


class SearchApiSelectionRepositoryAdapter:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[SearchApiSelectionData]:
        result = await self._session.execute(select(SearchApiSelection))
        return [
            SearchApiSelectionData(family=row.family, active_provider_code=row.active_provider_code)
            for row in result.scalars().all()
        ]

    async def get(self, family: str) -> Optional[SearchApiSelectionData]:
        row = await self._session.get(SearchApiSelection, family)
        if row is None:
            return None
        return SearchApiSelectionData(family=row.family, active_provider_code=row.active_provider_code)

    async def set_active(self, family: str, provider_code: str) -> SearchApiSelectionData:
        row = await self._session.get(SearchApiSelection, family)
        if row is None:
            row = SearchApiSelection(family=family, active_provider_code=provider_code)
            self._session.add(row)
        else:
            row.active_provider_code = provider_code
        await self._session.commit()
        await self._session.refresh(row)
        return SearchApiSelectionData(family=row.family, active_provider_code=row.active_provider_code)


class LLMConfigRepositoryAdapter:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_configs(self) -> list[LLMProviderConfigData]:
        result = await self._session.execute(
            select(LLMProviderConfig).order_by(LLMProviderConfig.provider_code, LLMProviderConfig.model)
        )
        return [_llm_config_to_domain(row) for row in result.scalars().all()]

    async def get_config(self, config_id: int) -> Optional[LLMProviderConfigData]:
        row = await self._session.get(LLMProviderConfig, config_id)
        return _llm_config_to_domain(row) if row else None

    async def create_config(self, data: LLMProviderConfigData) -> LLMProviderConfigData:
        row = LLMProviderConfig(
            provider_code=data.provider_code,
            model=data.model,
            api_key=data.api_key,
            base_url=data.base_url,
        )
        self._session.add(row)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ValueError(
                f"Já existe uma config para provider={data.provider_code!r} "
                f"base_url={data.base_url!r} model={data.model!r}"
            ) from exc
        await self._session.refresh(row)
        return _llm_config_to_domain(row)

    async def update_config(self, config_id: int, data: LLMProviderConfigData) -> LLMProviderConfigData:
        row = await self._session.get(LLMProviderConfig, config_id)
        if row is None:
            raise KeyError(f"Unknown LLM provider config id: {config_id}")
        row.provider_code = data.provider_code
        row.model = data.model
        row.api_key = data.api_key
        row.base_url = data.base_url
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ValueError(
                f"Já existe uma config para provider={data.provider_code!r} "
                f"base_url={data.base_url!r} model={data.model!r}"
            ) from exc
        await self._session.refresh(row)
        return _llm_config_to_domain(row)

    async def delete_config(self, config_id: int) -> None:
        row = await self._session.get(LLMProviderConfig, config_id)
        if row is None:
            return
        await self._session.delete(row)
        await self._session.commit()

    async def list_bindings(self) -> list[LLMCallSiteBindingData]:
        result = await self._session.execute(select(LLMCallSiteBinding))
        return [
            LLMCallSiteBindingData(call_site=row.call_site, config_id=row.config_id)
            for row in result.scalars().all()
        ]

    async def get_binding(self, call_site: str) -> Optional[LLMCallSiteBindingData]:
        row = await self._session.get(LLMCallSiteBinding, call_site)
        if row is None:
            return None
        return LLMCallSiteBindingData(call_site=row.call_site, config_id=row.config_id)

    async def set_binding(self, call_site: str, config_id: int) -> LLMCallSiteBindingData:
        row = await self._session.get(LLMCallSiteBinding, call_site)
        if row is None:
            row = LLMCallSiteBinding(call_site=call_site, config_id=config_id)
            self._session.add(row)
        else:
            row.config_id = config_id
        await self._session.commit()
        await self._session.refresh(row)
        return LLMCallSiteBindingData(call_site=row.call_site, config_id=row.config_id)
