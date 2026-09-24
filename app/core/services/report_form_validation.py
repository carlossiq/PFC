"""
Validação dos campos que o usuário digita no formulário do relatório
(referências, assinaturas, destinatário) - rejeita placeholders como
"sasassas"/"sdasdsad"/"diex 2322-1", que iam parar direto no documento
final. Mesmas regras em frontend/src/utils/reportFormValidation.ts.

Só é chamada em /sections/static e /assemble - nunca no /reassemble, que
remonta com o payload já salvo de sessões antigas (que podem ter esses
placeholders e precisam continuar remontáveis).
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

_VOWELS = set("aeiouáéíóúâêôãõàü")
# Referência administrativa: tipo do documento + número + data, ex.:
# "DIEx Nº 115-A3/DCT de 6 de janeiro de 2023" / "Ofício nº 001 - INOVA/IMBEL de 3 de janeiro de 2023".
_ADMIN_REF_RE = re.compile(r"^\S+.*\bn[º°o.]?\s*\S*\d.*\bde\s+\d{1,2}\s+de\s+\w+\s+de\s+\d{4}\b", re.IGNORECASE)
# Referência bibliográfica ABNT: "SOBRENOME, X. ... ano".
_BIBLIO_REF_RE = re.compile(r"^[A-ZÀ-Ý][A-ZÀ-Ý'\- ]+,\s*\S.*\b(1[5-9]|20)\d{2}\b")


def _is_gibberish_word(word: str) -> bool:
    letters = [c for c in word.lower() if c.isalpha()]
    if len(letters) < 5:
        return False
    return len(set(letters)) <= 2 or not (set(letters) & _VOWELS)


def looks_like_placeholder(text: str) -> bool:
    words = text.split()
    return not words or any(_is_gibberish_word(word) for word in words)


def admin_reference_error(ref: str) -> Optional[str]:
    if not _ADMIN_REF_RE.search(ref.strip()) or looks_like_placeholder(ref):
        return (
            f'Referência "{ref}" fora do formato: informe tipo, número e data do documento '
            '(ex.: "DIEx Nº 115-A3/DCT de 6 de janeiro de 2023").'
        )
    return None


def bibliography_error(ref: str) -> Optional[str]:
    if not _BIBLIO_REF_RE.search(ref.strip()) or looks_like_placeholder(ref):
        return (
            f'Referência bibliográfica "{ref}" fora do padrão ABNT: comece por "SOBRENOME, Iniciais." '
            "e inclua o ano."
        )
    return None


def signer_error(role: str, nome: str, posto: str, funcao: str = "") -> Optional[str]:
    nome, posto, funcao = nome.strip(), posto.strip(), funcao.strip()
    if not nome and not posto and not funcao:
        return None  # bloco vazio é filtrado depois (ver _merge_signatures)
    if len(nome.split()) < 2 or looks_like_placeholder(nome):
        return f'{role}: "{nome}" não parece um nome completo.'
    if len(posto) < 2 or looks_like_placeholder(posto):
        return f'{role}: posto/graduação "{posto}" inválido.'
    if not funcao or looks_like_placeholder(funcao):
        return f'{role}: informe a função (ex.: "Chefe da Seção de Informações Tecnológicas").'
    return None


def text_field_error(label: str, value: str, min_words: int = 2) -> Optional[str]:
    if len(value.split()) < min_words or looks_like_placeholder(value):
        return f"{label}: texto inválido."
    return None


def collect_errors(checks: Iterable[Optional[str]]) -> list[str]:
    return [error for error in checks if error]
