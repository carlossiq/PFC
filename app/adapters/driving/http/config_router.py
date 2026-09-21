"""
CRUD de configuração editável em runtime - ver PLANO_MIGRACAO_CONFIG_BANCO.md.

Sem autenticação por enquanto (risco documentado no plano - projeto à
parte). GET nunca devolve api_key/token/secret em texto puro - ver
AppSettingValue.masked()/LLMProviderConfigData.masked().
"""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.driven.llm.provider_registry import LLM_PROVIDER_REGISTRY
from app.adapters.driven.persistence.config_repository_adapter import (
    AppSettingsRepositoryAdapter,
    LLMConfigRepositoryAdapter,
    SearchApiSelectionRepositoryAdapter,
)
from app.adapters.driving.http.dependencies import get_db_session
from app.core.domain.config_types import LLMProviderConfigData
from app.core.services.llm_config_resolver import CALL_SITES
from app.core.services.report_cover_image import (
    InvalidCoverImageError,
    REPORT_COVER_IMAGE_OBJECT_KEY,
    process_cover_image,
)
from app.core.services.settings_sync_service import SettingsSyncService
from core.logging import get_logger
from schemas.response import SuccessResponse
from services.search.provider_registry import SEARCH_PROVIDER_REGISTRY, is_valid_provider_for_family

logger = get_logger(__name__)

router = APIRouter(prefix="/config", tags=["config"])


def _run_id(request: Request) -> str | None:
    return getattr(request.state, "run_id", None)


def _resolver(request: Request):
    return request.app.state.container["llm_resolver"]


def _storage(request: Request):
    return request.app.state.container["services"]["storage"]


# ------------------------------------------------------------------
# Escalares (app_settings)
# ------------------------------------------------------------------

class UpdateSettingRequest(BaseModel):
    value: str


@router.get("/settings", response_model=SuccessResponse[list[dict[str, Any]]])
async def list_settings(request: Request, session: AsyncSession = Depends(get_db_session)):
    rows = await AppSettingsRepositoryAdapter(session).list_all()
    data = [vars(row.masked()) for row in rows]
    return SuccessResponse(success=True, data=data, run_id=_run_id(request))


# search_year_from/search_year_to não têm um "range" pra slider (ver
# db/config_seed.py) - o único limite real é "não aceitar ano no futuro",
# validado aqui em vez de min_value/max_value.
_YEAR_KEYS_MAX_CURRENT_YEAR = {"search_year_from", "search_year_to"}


def _validate_year(key: str, value: str) -> None:
    if key not in _YEAR_KEYS_MAX_CURRENT_YEAR:
        return
    try:
        year = int(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"'{value}' não é um ano válido.") from exc
    current_year = datetime.now().year
    if year > current_year:
        raise HTTPException(
            status_code=400,
            detail=f"Ano não pode ser maior que o ano atual ({current_year}).",
        )


@router.put("/settings/{key}", response_model=SuccessResponse[dict[str, Any]])
async def update_setting(
    key: str,
    payload: UpdateSettingRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    _validate_year(key, payload.value)
    try:
        service = SettingsSyncService(AppSettingsRepositoryAdapter(session))
        row = await service.update_and_apply(key, payload.value)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SuccessResponse(success=True, data=vars(row.masked()), run_id=_run_id(request))


# ------------------------------------------------------------------
# Seleção de API de busca (search_api_selection)
# ------------------------------------------------------------------

class UpdateSearchApiRequest(BaseModel):
    active_provider_code: str


@router.get("/search-apis", response_model=SuccessResponse[dict[str, Any]])
async def list_search_apis(request: Request, session: AsyncSession = Depends(get_db_session)):
    repo = SearchApiSelectionRepositoryAdapter(session)
    selections = {s.family: s.active_provider_code for s in await repo.list_all()}
    options = {
        family: [{"code": spec.code, "display_name": spec.display_name} for spec in specs.values()]
        for family, specs in SEARCH_PROVIDER_REGISTRY.items()
    }
    return SuccessResponse(
        success=True,
        data={"selections": selections, "options": options},
        run_id=_run_id(request),
    )


@router.put("/search-apis/{family}", response_model=SuccessResponse[dict[str, Any]])
async def update_search_api(
    family: str,
    payload: UpdateSearchApiRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    if not is_valid_provider_for_family(family, payload.active_provider_code):
        raise HTTPException(
            status_code=400,
            detail=f"'{payload.active_provider_code}' não é uma API válida para a família '{family}'.",
        )
    row = await SearchApiSelectionRepositoryAdapter(session).set_active(family, payload.active_provider_code)
    logger.info(
        "search_api_selection_updated_restart_required",
        family=family,
        active_provider_code=payload.active_provider_code,
    )
    return SuccessResponse(
        success=True,
        data={"family": row.family, "active_provider_code": row.active_provider_code},
        message="Reinicie o backend para essa mudança valer (a API de busca é montada no boot).",
        run_id=_run_id(request),
    )


# ------------------------------------------------------------------
# Providers/configs de IA (llm_provider_configs)
# ------------------------------------------------------------------

class LLMConfigRequest(BaseModel):
    provider_code: str
    model: str
    api_key: str = ""
    base_url: str = ""


@router.get("/llm/providers", response_model=SuccessResponse[dict[str, Any]])
async def list_llm_providers(request: Request):
    data = {
        code: {
            "display_name": spec.display_name,
            "requires_api_key": spec.requires_api_key,
            "requires_base_url": spec.requires_base_url,
        }
        for code, spec in LLM_PROVIDER_REGISTRY.items()
    }
    return SuccessResponse(success=True, data=data, run_id=_run_id(request))


@router.get("/llm/configs", response_model=SuccessResponse[list[dict[str, Any]]])
async def list_llm_configs(request: Request, session: AsyncSession = Depends(get_db_session)):
    rows = await LLMConfigRepositoryAdapter(session).list_configs()
    return SuccessResponse(success=True, data=[vars(row.masked()) for row in rows], run_id=_run_id(request))


@router.post("/llm/configs", response_model=SuccessResponse[dict[str, Any]])
async def create_llm_config(
    payload: LLMConfigRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    if payload.provider_code not in LLM_PROVIDER_REGISTRY:
        raise HTTPException(status_code=400, detail=f"provider_code desconhecido: {payload.provider_code!r}")
    try:
        row = await LLMConfigRepositoryAdapter(session).create_config(
            LLMProviderConfigData(
                id=None,
                provider_code=payload.provider_code,
                model=payload.model,
                api_key=payload.api_key,
                base_url=payload.base_url,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return SuccessResponse(success=True, data=vars(row.masked()), run_id=_run_id(request))


@router.put("/llm/configs/{config_id}", response_model=SuccessResponse[dict[str, Any]])
async def update_llm_config(
    config_id: int,
    payload: LLMConfigRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    if payload.provider_code not in LLM_PROVIDER_REGISTRY:
        raise HTTPException(status_code=400, detail=f"provider_code desconhecido: {payload.provider_code!r}")
    try:
        row = await LLMConfigRepositoryAdapter(session).update_config(
            config_id,
            LLMProviderConfigData(
                id=config_id,
                provider_code=payload.provider_code,
                model=payload.model,
                api_key=payload.api_key,
                base_url=payload.base_url,
            ),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    # Configs editadas podem ser usadas por algum call site já cacheado no
    # resolver - invalida tudo (barato: só reconstrói no próximo uso de
    # cada call site, não agora).
    _resolver(request).invalidate_all()
    return SuccessResponse(success=True, data=vars(row.masked()), run_id=_run_id(request))


@router.delete("/llm/configs/{config_id}", response_model=SuccessResponse[dict[str, Any]])
async def delete_llm_config(
    config_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    await LLMConfigRepositoryAdapter(session).delete_config(config_id)
    _resolver(request).invalidate_all()
    return SuccessResponse(success=True, data={"deleted": config_id}, run_id=_run_id(request))


# ------------------------------------------------------------------
# Seleção de IA por call site (llm_call_site_bindings)
# ------------------------------------------------------------------

class UpdateCallSiteRequest(BaseModel):
    config_id: int


@router.get("/llm/call-sites", response_model=SuccessResponse[dict[str, Any]])
async def list_call_sites(request: Request, session: AsyncSession = Depends(get_db_session)):
    repo = LLMConfigRepositoryAdapter(session)
    bindings = {b.call_site: b.config_id for b in await repo.list_bindings()}
    configs = [vars(c.masked()) for c in await repo.list_configs()]
    return SuccessResponse(
        success=True,
        data={"call_sites": list(CALL_SITES), "bindings": bindings, "configs": configs},
        run_id=_run_id(request),
    )


@router.put("/llm/call-sites/{call_site}", response_model=SuccessResponse[dict[str, Any]])
async def update_call_site(
    call_site: str,
    payload: UpdateCallSiteRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    if call_site not in CALL_SITES:
        raise HTTPException(status_code=404, detail=f"call_site desconhecido: {call_site!r}")

    repo = LLMConfigRepositoryAdapter(session)
    config = await repo.get_config(payload.config_id)
    if config is None:
        raise HTTPException(status_code=404, detail=f"LLMProviderConfig {payload.config_id} não existe.")

    row = await repo.set_binding(call_site, payload.config_id)
    _resolver(request).invalidate(call_site)
    return SuccessResponse(
        success=True,
        data={"call_site": row.call_site, "config_id": row.config_id},
        run_id=_run_id(request),
    )


# ------------------------------------------------------------------
# Imagem de capa do relatório (símbolo/logo, ver
# app/core/services/report_cover_image.py) - uma única imagem GLOBAL,
# persistida no MinIO numa chave fixa. Atualizar aqui não altera PDFs já
# compilados, mas qualquer recompilação (POST /report/{id}/compile-pdf)
# passa a usar a nova imagem.
# ------------------------------------------------------------------

class ReportCoverImageResponse(BaseModel):
    has_image: bool
    image_base64: Optional[str] = None


async def _cover_image_response(request: Request) -> ReportCoverImageResponse:
    try:
        png_bytes = await _storage(request).download(REPORT_COVER_IMAGE_OBJECT_KEY)
    except Exception:
        return ReportCoverImageResponse(has_image=False)
    return ReportCoverImageResponse(has_image=True, image_base64=base64.b64encode(png_bytes).decode("ascii"))


@router.get("/report-cover-image", response_model=SuccessResponse[ReportCoverImageResponse])
async def get_report_cover_image(request: Request):
    return SuccessResponse(success=True, data=await _cover_image_response(request), run_id=_run_id(request))


@router.post("/report-cover-image", response_model=SuccessResponse[ReportCoverImageResponse])
async def upload_report_cover_image(request: Request, file: UploadFile = File(...)):
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    try:
        processed = process_cover_image(raw_bytes)
    except InvalidCoverImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await _storage(request).upload(REPORT_COVER_IMAGE_OBJECT_KEY, processed, "image/png")
    logger.info("report_cover_image_updated")
    return SuccessResponse(
        success=True,
        data=ReportCoverImageResponse(has_image=True, image_base64=base64.b64encode(processed).decode("ascii")),
        run_id=_run_id(request),
    )


@router.delete("/report-cover-image", response_model=SuccessResponse[ReportCoverImageResponse])
async def delete_report_cover_image(request: Request):
    try:
        await _storage(request).delete(REPORT_COVER_IMAGE_OBJECT_KEY)
    except Exception as exc:
        logger.warning("report_cover_image_delete_failed error=%s", exc)
    return SuccessResponse(success=True, data=ReportCoverImageResponse(has_image=False), run_id=_run_id(request))
