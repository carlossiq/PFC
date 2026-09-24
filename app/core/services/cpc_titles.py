"""
Significado oficial das classificações CPC/IPC usadas no relatório -
config/cpc_titles.json é gerado por scripts/build_cpc_titles.py a partir
das listas oficiais (EPO/USPTO e WIPO). O LLM recebe esses títulos prontos
e é proibido de descrever os códigos por conta própria (ver
report_prompts._informacoes_tecnologicas_prompt).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_TITLES_FILE = Path(__file__).resolve().parents[3] / "config" / "cpc_titles.json"


@lru_cache(maxsize=1)
def _titles() -> dict[str, str]:
    try:
        return json.loads(_TITLES_FILE.read_text(encoding="utf-8"))["titles"]
    except (OSError, ValueError, KeyError):
        return {}


def describe_code(code: str) -> str:
    """Título oficial de um código de subclasse (ex.: "H02S"). Subclasses
    extintas nas versões vigentes (ex.: "H01L", reorganizada na classe H10)
    caem no título da classe, com a ressalva explícita - nunca um título
    inventado."""
    titles = _titles()
    code = code.strip().upper()
    if code in titles:
        return titles[code]
    class_code = code[:3]
    if class_code in titles:
        return (
            f"subclasse ausente da versão vigente da CPC/IPC; pertence à classe {class_code} "
            f"({titles[class_code]}) - descreva apenas pela classe"
        )
    return "código não encontrado na tabela oficial - não descreva o significado"


def describe_codes(codes: list[str]) -> list[tuple[str, str]]:
    return [(code, describe_code(code)) for code in codes]
