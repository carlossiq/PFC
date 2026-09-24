from types import SimpleNamespace

from app.adapters.driving.http.report_document_router import _bundle_filename
from app.core.services.report_review import referenced_image_files

TEX = (
    "\\documentclass{article}\n"
    "\\newcommand{\\figura}[3][O autor.]{\\includegraphics{#3}}\n"
    "\\begin{document}\n"
    "\\includegraphics[width=4cm]{capa_relatorio.png}\n"
    "\\figura[MADEO, 2019.]{Estágios.\\label{fig:madeo}}{madeo.png}\n"
    "\\quadroimg{Áreas.}{article_top10_heatmap.png}\n"
    "% \\figura{Comentada}{nao_entra.png}\n"
    "\\end{document}\n"
)


def test_referenced_images_ignore_preamble_definitions_and_comments():
    assert referenced_image_files(TEX) == {"capa_relatorio.png", "madeo.png", "article_top10_heatmap.png"}


def test_bundle_filename_uses_reptec_number_and_year():
    row = SimpleNamespace(assemble_payload={"numero": "002", "ano": "2026"})
    assert _bundle_filename(row, 19) == "REPTEC_002_2026.zip"


def test_bundle_filename_falls_back_to_session_and_sanitizes():
    assert _bundle_filename(None, 19) == "relatorio_sessao_19.zip"
    row = SimpleNamespace(assemble_payload={"numero": '0/0"1', "ano": "2026"})
    assert _bundle_filename(row, 7) == "REPTEC_001_2026.zip"
