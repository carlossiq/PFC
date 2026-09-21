from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class AppSettingValue:
    key: str
    value: str
    value_type: str  # "float" | "int" | "bool" | "str"
    category: str
    is_secret: bool
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    label: Optional[str] = None
    description: Optional[str] = None
    # Valor do seed inicial (não muda com update_value) - "valor
    # recomendado" mostrado no tooltip do front. Sempre None pra settings
    # secretas (ver db/config_seed.py - nunca guardamos o segredo original
    # do .env aqui).
    default_value: Optional[str] = None

    def typed_value(self) -> object:
        if self.value_type == "float":
            return float(self.value)
        if self.value_type == "int":
            return int(self.value)
        if self.value_type == "bool":
            return self.value.lower() in ("true", "1", "yes")
        return self.value

    def masked(self) -> "AppSettingValue":
        if not self.is_secret or not self.value:
            return self
        masked_value = f"...{self.value[-4:]}" if len(self.value) > 4 else "****"
        return AppSettingValue(
            key=self.key,
            value=masked_value,
            value_type=self.value_type,
            category=self.category,
            is_secret=self.is_secret,
            min_value=self.min_value,
            max_value=self.max_value,
            step=self.step,
            label=self.label,
            description=self.description,
            default_value=self.default_value,
        )


@dataclass
class SearchApiSelectionData:
    family: str  # "patent" | "scholarly"
    active_provider_code: str


@dataclass
class LLMProviderConfigData:
    id: Optional[int]
    provider_code: str
    model: str
    api_key: str
    base_url: str

    def masked(self) -> "LLMProviderConfigData":
        masked_key = f"...{self.api_key[-4:]}" if len(self.api_key) > 4 else ("****" if self.api_key else "")
        return LLMProviderConfigData(
            id=self.id,
            provider_code=self.provider_code,
            model=self.model,
            api_key=masked_key,
            base_url=self.base_url,
        )


@dataclass
class LLMCallSiteBindingData:
    call_site: str
    config_id: int
