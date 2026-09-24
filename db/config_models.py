"""
Modelos de configuração editável em runtime (settings genéricos, seleção de
API de busca por família, e configs/seleção de provider de IA por call site).

Convenção: valores de "quais providers/códigos existem" (ex: 'gemini',
'ops', 'lens_patent') NÃO são tabelas - são registries Python (ver
app/adapters/driven/llm/provider_registry.py e
services/search/provider_registry.py). Isso é proposital: suportar um novo
provider sempre exige código novo (uma classe adapter), então validar o
código contra um dict em vez de uma FK/CHECK de banco evita migration toda
vez que um provider novo for adicionado - só a instância CONFIGURADA
(model/api_key/base_url, ou qual código está ativo) precisa viver no banco.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column

Base = declarative_base()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AppSetting(Base):
    """
    Um escalar configurável (threshold, top_k, peso, flag booleana...) -
    espelha os campos catalogados em VARIAVEIS_DE_CONFIGURACAO.md. `key` é o
    nome do campo em core/config.py (ex: "term_extraction_score_threshold").

    min_value/max_value/step só são preenchidos para settings numéricos com
    range conhecido - usados pelo front pra desenhar o slider (ver
    RangeSliderInput.tsx); ficam NULL para bool/str.
    """

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "float" | "int" | "bool" | "str"
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    min_value: Mapped[Optional[float]] = mapped_column(Float)
    max_value: Mapped[Optional[float]] = mapped_column(Float)
    step: Mapped[Optional[float]] = mapped_column(Float)
    label: Mapped[Optional[str]] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    # Valor do seed inicial (nunca atualizado por update_value) - mostrado no
    # tooltip como "valor recomendado", independente de quantas vezes o
    # usuário já tenha editado `value` desde então. NULL pra settings
    # secretas (nunca expor o segredo original do .env no tooltip).
    default_value: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class SearchApiSelection(Base):
    """
    Qual provider está ativo por família de busca (patent/scholarly) - no
    máximo 1 ativo por família, garantido por `family` ser PK (não dá pra
    ter duas linhas da mesma família). `active_provider_code` é validado
    contra services.search.provider_registry.SEARCH_PROVIDER_REGISTRY na
    camada de aplicação (não via CHECK de banco - ver docstring do módulo).
    """

    __tablename__ = "search_api_selection"

    family: Mapped[str] = mapped_column(String(20), primary_key=True)  # "patent" | "scholarly"
    active_provider_code: Mapped[str] = mapped_column(String(30), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class LLMProviderConfig(Base):
    """
    Uma instância configurada de provider de IA (ex: "Gemini com o modelo
    gemini-2.0-flash-exp e esta api_key", ou "Ollama no servidor da
    intranet com o modelo gemma4:12b"). Uma única tabela pra todos os
    providers (não uma por provider) - `provider_code` é o discriminador,
    validado contra app.adapters.driven.llm.provider_registry.
    LLM_PROVIDER_REGISTRY. Isso é o que permite adicionar um provider novo
    sem schema novo: só código (uma classe adapter + uma entrada no
    registry), a tabela já aceita qualquer `provider_code`.

    base_url e api_key usam default "" (nunca NULL) de propósito: a
    UniqueConstraint(provider_code, base_url, model) não funcionaria pra
    detectar duplicata se base_url pudesse ser NULL (SQL trata NULL como
    nunca igual a si mesmo em constraints de unicidade).
    """

    __tablename__ = "llm_provider_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_code: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(150), nullable=False)
    api_key: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    base_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (UniqueConstraint("provider_code", "base_url", "model", name="uq_llm_provider_config"),)


class LLMCallSiteBinding(Base):
    """
    Qual LLMProviderConfig cada chamada de IA do programa usa hoje.
    `call_site` é um dos 4 pontos fixos do código (ver
    app/core/services/llm_config_resolver.py::CALL_SITES):
    "theme_candidates", "probe_query", "final_query", "report_writing",
    "report_review".
    """

    __tablename__ = "llm_call_site_bindings"

    call_site: Mapped[str] = mapped_column(String(50), primary_key=True)
    config_id: Mapped[int] = mapped_column(ForeignKey("llm_provider_configs.id"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
