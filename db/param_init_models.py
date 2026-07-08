"""
Database model for capturing the prospecting wizard's initial parameters (Step1).
"""

from typing import Optional

from sqlalchemy import JSON, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column

Base = declarative_base()


class ParamInit(Base):
    """Parâmetros iniciais capturados na tela Step1 do wizard de prospecção."""

    __tablename__ = "param_init"

    id: Mapped[int] = mapped_column(primary_key=True)
    tema: Mapped[str] = mapped_column(String(500), nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(Text)
    keywords: Mapped[Optional[list[str]]] = mapped_column(JSON)
    area_estudo: Mapped[Optional[str]] = mapped_column(String(500))
