"""
Endpoints for capturing/discarding Step1 initial parameters of the prospecting wizard.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.dependencies import get_db_session
from core.logging import get_logger
from db.param_init_models import ParamInit
from schemas.param_init import ParamInitRequest, ParamInitResponse
from schemas.response import SuccessResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/param-init", tags=["param-init"])


@router.post("", response_model=SuccessResponse[ParamInitResponse])
async def create_param_init(
    payload: ParamInitRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[ParamInitResponse]:
    """Cria uma nova tupla PARAM_INIT com os parâmetros iniciais do wizard."""
    row = ParamInit(
        tema=payload.tema,
        descricao=payload.descricao,
        area_estudo=payload.area_estudo,
        keywords=payload.keywords,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    logger.info("param_init_created", param_init_id=row.id)

    return SuccessResponse(data=ParamInitResponse.model_validate(row))


@router.put("/{param_init_id}", response_model=SuccessResponse[ParamInitResponse])
async def update_param_init(
    param_init_id: int,
    payload: ParamInitRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[ParamInitResponse]:
    """Atualiza uma tupla PARAM_INIT existente."""
    row = await session.get(ParamInit, param_init_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Param init row not found")

    row.tema = payload.tema
    row.descricao = payload.descricao
    row.area_estudo = payload.area_estudo
    row.keywords = payload.keywords
    await session.commit()
    await session.refresh(row)

    logger.info("param_init_updated", param_init_id=row.id)

    return SuccessResponse(data=ParamInitResponse.model_validate(row))


async def _delete_param_init(param_init_id: int, session: AsyncSession) -> SuccessResponse[dict]:
    """Apaga uma tupla PARAM_INIT de forma idempotente (não falha se já não existir)."""
    row = await session.get(ParamInit, param_init_id)
    if row is not None:
        await session.delete(row)
        await session.commit()
        logger.info("param_init_deleted", param_init_id=param_init_id)
    else:
        logger.info("param_init_delete_noop_already_gone", param_init_id=param_init_id)

    return SuccessResponse(data={"id": param_init_id, "deleted": True})


@router.delete("/{param_init_id}", response_model=SuccessResponse[dict])
async def delete_param_init(
    param_init_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[dict]:
    """Apaga uma tupla PARAM_INIT (usado no botão Cancelar)."""
    return await _delete_param_init(param_init_id, session)


@router.post("/{param_init_id}/discard", response_model=SuccessResponse[dict])
async def discard_param_init(
    param_init_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[dict]:
    """
    Alias em POST da mesma lógica de delete.

    Existe porque navigator.sendBeacon só consegue enviar POST, usado para
    apagar a tupla quando o usuário fecha/atualiza a aba do navegador.
    """
    return await _delete_param_init(param_init_id, session)
