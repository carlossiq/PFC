"""
Montagem do .tex do relatório e compilação de PDF sob demanda.

Duas responsabilidades deliberadamente separadas (SRP) - a montagem do .tex
NUNCA compila PDF automaticamente (ver docstring de compile_pdf e o pedido
explícito do usuário: PDF só quando ele decidir, via
POST /report/{session_id}/compile-pdf):
    - `render_and_upload_tex`: renderiza o template Jinja2 (ver
      config/prompts/report_latex_template.py) com os textos/gráficos já
      persistidos, sobe o .tex (+ imagens) pro MinIO.
    - `compile_pdf`: baixa esse .tex + imagens do MinIO, chama o serviço
      HTTP dedicado (latex-compiler/) e sobe o PDF resultante.

Só fala com StoragePort (MinIO) e o latex-compiler via HTTP - nenhum acesso
a ORM/banco aqui (mesmo padrão de report_service.py); o router monta os
dicts de entrada a partir do banco.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.ports.outbound.storage_port import StoragePort
from config.prompts.report_latex_template import render_report_latex
from core.logging import get_logger

logger = get_logger(__name__)


class ReportLatexService:
    def __init__(self, storage: StoragePort, latex_compiler_url: str) -> None:
        self._storage = storage
        self._latex_compiler_url = latex_compiler_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=180)

    @staticmethod
    def _report_prefix(session_id: int) -> str:
        return f"sessions/{session_id}/report"

    @staticmethod
    def _basename(object_key: str) -> str:
        return object_key.rsplit("/", 1)[-1]

    async def render_and_upload_tex(
        self,
        session_id: int,
        context: dict[str, Any],
        chart_object_keys: list[str],
    ) -> dict[str, Any]:
        """Baixa só os PNGs que já existem no MinIO (`chart_object_keys`,
        resolvidos pelo router a partir de SessionChart) - nunca dispara
        geração de gráfico novo. Chaves que falharem no download entram em
        `charts_missing` na resposta, sem interromper a montagem do .tex."""
        image_bytes: dict[str, bytes] = {}
        charts_missing: list[str] = []
        for object_key in chart_object_keys:
            try:
                image_bytes[object_key] = await self._storage.download(object_key)
            except Exception as exc:
                logger.warning("report_latex_chart_download_failed", object_key=object_key, error=str(exc))
                charts_missing.append(object_key)

        tex_content = render_report_latex(context)

        prefix = self._report_prefix(session_id)
        tex_object_key = f"{prefix}/main.tex"
        await self._storage.upload(tex_object_key, tex_content.encode("utf-8"), "text/x-tex")

        image_object_keys: list[str] = []
        for source_key, data in image_bytes.items():
            report_image_key = f"{prefix}/{self._basename(source_key)}"
            await self._storage.upload(report_image_key, data, "image/png")
            image_object_keys.append(report_image_key)

        return {
            "tex_object_key": tex_object_key,
            "tex_content": tex_content,
            "image_object_keys": image_object_keys,
            "charts_missing": charts_missing,
        }

    async def compile_pdf(self, session_id: int, tex_object_key: str, image_object_keys: list[str]) -> dict[str, Any]:
        """Só chamado por POST /report/{session_id}/compile-pdf, nunca
        automaticamente. Falha de compilação não apaga o .tex já persistido
        - devolve `{"success": False, "log": ...}` pro chamador decidir o
        que mostrar ao usuário."""
        tex_bytes = await self._storage.download(tex_object_key)
        files: list[tuple[str, tuple[str, bytes, str]]] = [
            ("main_tex", ("main.tex", tex_bytes, "text/x-tex")),
        ]
        for object_key in image_object_keys:
            data = await self._storage.download(object_key)
            files.append(("assets", (self._basename(object_key), data, "image/png")))

        try:
            response = await self._client.post(f"{self._latex_compiler_url}/compile", files=files)
        except httpx.ConnectError as exc:
            logger.error("latex_compiler_connect_failed", url=self._latex_compiler_url, error=str(exc))
            return {"success": False, "log": f"Não foi possível conectar ao latex-compiler ({self._latex_compiler_url})."}

        if response.status_code != 200:
            log = response.text
            try:
                log = response.json().get("log", log)
            except Exception:
                pass
            return {"success": False, "log": log}

        pdf_object_key = f"{self._report_prefix(session_id)}/main.pdf"
        await self._storage.upload(pdf_object_key, response.content, "application/pdf")
        return {"success": True, "pdf_object_key": pdf_object_key, "pdf_bytes": response.content}

    async def close(self) -> None:
        await self._client.aclose()
