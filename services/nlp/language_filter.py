"""
Filtro de idioma para descartar abstracts em idioma diferente do inglês.

Usado na busca (probe e final, tanto OPS quanto Scopus) antes de repassar os
resultados pra extração de termos / geração da query final - um abstract em
outro idioma pode levar a IA a "traduzir errado" termos técnicos na hora de
montar a busca final.
"""
from typing import Optional

from langdetect import detect, LangDetectException

from core.logging import get_logger

logger = get_logger(__name__)

# langdetect não é confiável em textos muito curtos - abaixo disso, não
# arriscamos um veredito (não descarta por essa razão sozinha).
_MIN_TEXT_LENGTH = 20


def is_non_english_abstract(text: Optional[str]) -> bool:
    """
    True se o texto for detectado com confiança como um idioma diferente do
    inglês. Abstracts vazios ou curtos demais pra detecção confiável
    retornam False (não é motivo de descarte por si só - só quando há
    abstract e ele está claramente em outro idioma).
    """
    cleaned = (text or "").strip()
    if len(cleaned) < _MIN_TEXT_LENGTH:
        return False

    try:
        return detect(cleaned) != "en"
    except LangDetectException:
        return False


def filter_english_abstracts(items: list[dict], abstract_key: str = "abstract") -> list[dict]:
    """
    Filtra uma lista de itens (dicts com um campo de abstract), descartando
    os que têm abstract confiavelmente não-inglês. Itens sem abstract (ou
    com abstract curto demais pra detectar) são mantidos.
    """
    filtered = [item for item in items if not is_non_english_abstract(item.get(abstract_key))]

    discarded = len(items) - len(filtered)
    if discarded:
        logger.info("non_english_abstracts_discarded", discarded=discarded, kept=len(filtered))

    return filtered
