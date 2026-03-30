"""
Standard API response schemas for consistent response formatting.
"""

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """
    Detalhe de erro estruturado para respostas de erro.

    Proporciona informações padronizadas sobre o que deu errado
    e como o cliente pode corrigir.
    """

    code: str = Field(
        ...,
        description="Código de erro interno",
    )
    message: str = Field(
        ...,
        description="Mensagem de erro legível",
    )
    details: Optional[dict[str, Any]] = Field(
        default=None,
        description="Detalhes adicionais do erro",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "code": "INVALID_INPUT",
                "message": "Theme field is required and must not be empty",
                "details": {"field": "theme", "value": ""},
            }
        }


class SuccessResponse(BaseModel, Generic[T]):
    """
    Resposta padrão de sucesso da API.

    Envolve dados de sucesso com metadados de requisição
    para respostas padronizadas.
    """

    success: bool = Field(
        default=True,
        description="Indicador de sucesso",
    )
    data: Optional[T] = Field(
        default=None,
        description="Dados da resposta",
    )
    message: Optional[str] = Field(
        default=None,
        description="Mensagem informativa opcional",
    )
    run_id: Optional[str] = Field(
        default=None,
        description="Identificador único da requisição",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "success": True,
                "data": {},
                "message": "Operation completed successfully",
                "run_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }


class ErrorResponse(BaseModel):
    """
    Resposta padrão de erro da API.

    Padroniza erros com código HTTP, detalhes estruturados
    e informações de rastreamento de requisição.
    """

    success: bool = Field(
        default=False,
        description="Indicador de falha",
    )
    error: ErrorDetail = Field(
        ...,
        description="Detalhes do erro",
    )
    run_id: Optional[str] = Field(
        default=None,
        description="Identificador único da requisição",
    )
    status_code: int = Field(
        ...,
        description="Código HTTP de status",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": "INVALID_INPUT",
                    "message": "Theme field is required",
                },
                "run_id": "550e8400-e29b-41d4-a716-446655440000",
                "status_code": 400,
            }
        }


class PaginationInfo(BaseModel):
    """
    Informações de paginação para respostas com múltiplos itens.

    Fornece metadados sobre navegação através de conjuntos
    de resultados grandes.
    """

    page: int = Field(
        ge=1,
        description="Número da página atual",
    )
    page_size: int = Field(
        ge=1,
        le=1000,
        description="Tamanho da página",
    )
    total_count: int = Field(
        ge=0,
        description="Número total de itens",
    )
    total_pages: int = Field(
        ge=0,
        description="Número total de páginas",
    )
    has_next: bool = Field(
        default=False,
        description="Se há próxima página",
    )
    has_previous: bool = Field(
        default=False,
        description="Se há página anterior",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 20,
                "total_count": 100,
                "total_pages": 5,
                "has_next": True,
                "has_previous": False,
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Resposta paginada da API.

    Envolve dados paginados com informações de navegação
    para respostas que retornam muitos itens.
    """

    success: bool = Field(
        default=True,
        description="Indicador de sucesso",
    )
    data: list[T] = Field(
        default_factory=list,
        description="Lista de itens da página",
    )
    pagination: PaginationInfo = Field(
        ...,
        description="Informações de paginação",
    )
    run_id: Optional[str] = Field(
        default=None,
        description="Identificador único da requisição",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "success": True,
                "data": [],
                "pagination": {
                    "page": 1,
                    "page_size": 20,
                    "total_count": 100,
                    "total_pages": 5,
                    "has_next": True,
                    "has_previous": False,
                },
                "run_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }


class HealthCheckResponse(BaseModel):
    """
    Resposta de verificação de saúde da aplicação.

    Proporciona status da aplicação e informações básicas
    sobre sua operação.
    """

    status: str = Field(
        default="healthy",
        description="Status de saúde",
    )
    message: str = Field(
        default="Application is running",
        description="Mensagem descritiva",
    )
    run_id: Optional[str] = Field(
        default=None,
        description="Identificador único da requisição",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "status": "healthy",
                "message": "Application is running",
                "run_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }
