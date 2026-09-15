"""
Serviço HTTP dedicado de compilação de LaTeX (POST /compile).

Só é chamado sob demanda por POST /report/{session_id}/compile-pdf do
backend principal (app/adapters/driving/http/report_document_router.py) -
nunca automaticamente na montagem do .tex (ver
app/core/services/report_latex_service.py). Roda num container à parte
(latex-compiler/Dockerfile, imagem texlive/texlive) pra não carregar o
toolchain TeX Live completo (~vários GB) na imagem do backend - mesmo
espírito de "serviço de rede dedicado" do MinIO.

Recebe um main.tex + as imagens referenciadas por ele (multipart/form-data),
compila com latexmk num diretório temporário isolado por requisição, e
devolve o PDF final ou o log de erro do LaTeX.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response

app = FastAPI(title="PFC LaTeX Compiler")

_COMPILE_TIMEOUT_SECONDS = 120


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/compile")
async def compile_latex(main_tex: UploadFile, assets: list[UploadFile] = None) -> Response:  # type: ignore[assignment]
    """
    `main_tex`: o arquivo .tex principal (campo obrigatório).
    `assets`: 0+ arquivos adicionais referenciados pelo .tex (imagens dos
    gráficos, etc.) - salvos com o próprio `filename` enviado, no mesmo
    diretório do .tex, pra `\\includegraphics{...}` resolver o caminho
    relativo sem qualquer reescrita.
    """
    work_dir = Path(tempfile.gettempdir()) / f"latex-compile-{uuid.uuid4().hex}"
    work_dir.mkdir(parents=True, exist_ok=False)

    try:
        tex_path = work_dir / "main.tex"
        tex_path.write_bytes(await main_tex.read())

        for asset in assets or []:
            if not asset.filename:
                continue
            asset_path = work_dir / Path(asset.filename).name
            asset_path.write_bytes(await asset.read())

        result = subprocess.run(
            [
                "latexmk",
                "-pdf",
                "-interaction=nonstopmode",
                "-halt-on-error",
                "main.tex",
            ],
            cwd=work_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_COMPILE_TIMEOUT_SECONDS,
        )

        pdf_path = work_dir / "main.pdf"
        if result.returncode != 0 or not pdf_path.exists():
            return JSONResponse(
                status_code=422,
                content={
                    "success": False,
                    "log": (result.stdout or "") + "\n" + (result.stderr or ""),
                },
            )

        return Response(content=pdf_path.read_bytes(), media_type="application/pdf")

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Compilação do LaTeX excedeu o tempo limite.")
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
