"""
Imagem de capa do relatório REPTEC/AGITEC (símbolo/logo) - uma única imagem
GLOBAL (não por sessão), configurável em Configurações > Geral (ver
config_router.py) e persistida no MinIO numa chave fixa (reenviar
sobrescreve o mesmo objeto, mesmo padrão "regenerar não acumula versões" de
SessionChart).

Atualizar a imagem não altera o PDF de relatórios já compilados, mas
qualquer recompilação (POST /report/{id}/compile-pdf) busca sempre a versão
mais recente dessa chave - só a montagem do .tex (POST /assemble) decide se
o bloco da capa existe NO DOCUMENTO (ver report_document_router.py):
sessões montadas antes de qualquer imagem ter sido configurada nunca ganham
o bloco de volta sozinhas (a montagem não roda de novo depois do ponto de
não-retorno), mas isso cobre virtualmente todo relatório na prática, já que
a imagem tende a ser configurada uma vez, no início do uso do sistema.

Padronização de tamanho: o recorte/zoom é feito pelo USUÁRIO no front (ver
frontend/src/components/settings/ImageCropModal.tsx - moldura de proporção
fixa, arraste pra posicionar, slider de zoom), não automaticamente aqui - o
que chega pro backend já é o enquadramento escolhido, no tamanho exato
REPORT_COVER_IMAGE_TARGET_SIZE. `process_cover_image` só reafirma esse
tamanho como rede de segurança (ex.: upload direto na API, sem passar pelo
front) - pra uma imagem já correta, o crop("cover") abaixo não faz nada além
de reencodar pra PNG. O tamanho/proporção alvo (~1:1.414, igual a uma folha
A4) replica o do brasão exibido na capa do REPTEC de referência
(notes/REPTEC_001_2023_TETRA.pdf, pág. 1).
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageOps

from core.logging import get_logger

logger = get_logger(__name__)

REPORT_COVER_IMAGE_OBJECT_KEY = "config/capa_relatorio.png"
REPORT_COVER_IMAGE_FILENAME = "capa_relatorio.png"

REPORT_COVER_IMAGE_TARGET_SIZE = (600, 848)

# Capa padrão do sistema (brasão). Versionada no repositório e enviada ao
# MinIO na subida se ainda não houver capa; "Remover imagem" na tela restaura
# esta mesma imagem (ver restore_default_cover_image).
_DEFAULT_COVER_IMAGE_PATH = Path(__file__).resolve().parents[3] / "config" / "assets" / "brasao_agitec_ia.png"


class InvalidCoverImageError(ValueError):
    """Levantado quando os bytes enviados não são uma imagem decodificável."""


def process_cover_image(raw_bytes: bytes) -> bytes:
    """Rede de segurança, não a UX principal (ver docstring do módulo): o
    front já manda a imagem no enquadramento escolhido pelo usuário, no
    tamanho exato REPORT_COVER_IMAGE_TARGET_SIZE - o crop("cover") aqui só
    entra em ação se algo enviar um tamanho/proporção diferente (upload
    direto na API), e converte pra PNG de qualquer forma."""
    try:
        image = Image.open(io.BytesIO(raw_bytes))
        image.load()
    except Exception as exc:
        raise InvalidCoverImageError("Arquivo enviado não é uma imagem válida.") from exc

    image = image.convert("RGBA") if "A" in image.getbands() else image.convert("RGB")
    fitted = ImageOps.fit(image, REPORT_COVER_IMAGE_TARGET_SIZE, method=Image.LANCZOS)

    buffer = io.BytesIO()
    fitted.save(buffer, format="PNG")
    return buffer.getvalue()


def default_cover_image_bytes() -> bytes:
    """Capa padrão já no formato da capa (PNG, REPORT_COVER_IMAGE_TARGET_SIZE)."""
    return process_cover_image(_DEFAULT_COVER_IMAGE_PATH.read_bytes())


async def ensure_default_cover_image(storage) -> None:
    """Seed automático: envia a capa padrão só se ainda não houver capa no
    MinIO. Nunca sobrescreve uma capa enviada pelo usuário. Melhor-esforço,
    igual às figuras fixas: falha de storage vira aviso, não impede a subida."""
    try:
        await storage.download(REPORT_COVER_IMAGE_OBJECT_KEY)
        return
    except Exception:
        pass
    await storage.upload(REPORT_COVER_IMAGE_OBJECT_KEY, default_cover_image_bytes(), "image/png")
    logger.info("report_cover_image_default_uploaded", object_key=REPORT_COVER_IMAGE_OBJECT_KEY)


async def restore_default_cover_image(storage) -> None:
    """Restaura a capa padrão, substituindo a atual. É o que "Remover imagem"
    faz na tela: apagar de vez faria o seed trazer a capa de volta no próximo
    boot, já que ele só olha se a chave existe."""
    await storage.upload(REPORT_COVER_IMAGE_OBJECT_KEY, default_cover_image_bytes(), "image/png")
