"""
Validação de códigos IPC/CPC gerados pela IA - rede de segurança contra
alucinação de classificação (ver probe_system_prompt.txt/final_system_prompt.md,
regra "não invente CPC/IPC", que sozinha é só confiança no texto do prompt,
sem nenhuma checagem real por trás até este módulo existir).

Dois níveis de checagem, aplicados nessa ordem:
1. Formato: um código IPC/CPC de verdade sempre segue o padrão "LETRA +
   2 dígitos + LETRA + dígitos + barra + dígitos" (ex: "H04W72/00",
   "G06N 3/08") - qualquer coisa fora desse formato é certamente inventada
   ou malformada, e é descartada sempre, mesmo sem lista de referência.
2. Procedência (só quando uma lista de códigos observados na busca probe é
   fornecida - ver ChatService._terms_context_suffix): um código com
   formato válido mas ausente dessa lista também é descartado - a única
   fonte confiável de "esse código existe e é relevante pro tema" é ele
   ter aparecido de verdade nos documentos já encontrados, não o
   conhecimento geral da IA (que já demonstrou inventar números em outros
   contextos deste projeto, ver comparativo qwen vs gemma na geração do
   relatório).
"""

from __future__ import annotations

import re
from typing import Optional

from core.logging import get_logger

logger = get_logger(__name__)

# Ex.: "H04W72/00", "G06N 3/08", "A61B5/0006" - letra (seção A-H), 2
# dígitos (classe), letra (subclasse), 1-4 dígitos (grupo), barra, 2-6
# dígitos (subgrupo) - com ou sem espaço antes da barra, ambos os formatos
# aparecem em fontes reais (Espacenet costuma usar espaço, a IA às vezes não).
_CODE_FORMAT_RE = re.compile(r"^[A-H]\d{2}[A-Z]\s?\d{1,4}/\d{2,6}$", re.IGNORECASE)


def validate_classification_codes(
    codes: list[str],
    allowed_codes: Optional[list[str]] = None,
    field_name: str = "ipc",
) -> list[str]:
    """Filtra `codes` (gerados pela IA), mantendo só os com formato válido
    e, quando `allowed_codes` é fornecida, presentes nela. Cada código
    descartado é logado (nível warning) - dá visibilidade de quanto a IA
    tenta inventar classificação, mesmo sem interromper o pipeline (a
    query segue sem esse código, não com um erro)."""
    if not codes:
        return codes

    allowed_normalized = (
        {c.replace(" ", "").upper() for c in allowed_codes} if allowed_codes else None
    )

    valid: list[str] = []
    for code in codes:
        stripped = (code or "").strip()
        if not stripped:
            continue
        if not _CODE_FORMAT_RE.match(stripped):
            logger.warning("classification_code_rejected_bad_format", field=field_name, code=code)
            continue
        if allowed_normalized is not None and stripped.replace(" ", "").upper() not in allowed_normalized:
            logger.warning("classification_code_rejected_not_in_probe", field=field_name, code=code)
            continue
        valid.append(stripped)
    return valid
