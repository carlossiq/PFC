"""
Figuras fixas da Metodologia do relatório REPTEC/AGITEC (5.3 - estágios do
ciclo de vida e curva logística, ver notes/REPTEC_001_2023_TETRA.pdf, Figuras
2 e 3) - iguais em TODO relatório, nunca geradas pelo sistema nem pela IA.

Os PNGs versionados em config/report_assets/ são a fonte; no MinIO ficam em
chaves GLOBAIS (não por sessão, mesmo padrão da imagem de capa em
report_cover_image.py), enviadas uma vez na inicialização do app
(`ensure_static_figures_uploaded`) e baixadas em toda compilação de PDF.
"""

from __future__ import annotations

from pathlib import Path

from app.core.ports.outbound.storage_port import StoragePort
from core.logging import get_logger

logger = get_logger(__name__)

_ASSETS_DIR = Path(__file__).resolve().parents[3] / "config" / "report_assets"

# filename (o mesmo usado no \includegraphics do template) -> chave no MinIO
REPORT_STATIC_FIGURES: dict[str, str] = {
    "madeo.png": "config/report_figures/madeo.png",
    "kucharavy.png": "config/report_figures/kucharavy.png",
}


async def ensure_static_figures_uploaded(storage: StoragePort) -> None:
    """Sobe cada figura que ainda não existe no MinIO - StoragePort não tem
    `exists()`, então checa tentando baixar (mesmo padrão de
    _cover_image_exists). Nunca sobrescreve o que já está lá."""
    for filename, object_key in REPORT_STATIC_FIGURES.items():
        try:
            await storage.download(object_key)
            continue
        except Exception:
            pass
        source = _ASSETS_DIR / filename
        if not source.exists():
            logger.warning("report_static_figure_source_missing", path=str(source))
            continue
        await storage.upload(object_key, source.read_bytes(), "image/png")
        logger.info("report_static_figure_uploaded", object_key=object_key)
