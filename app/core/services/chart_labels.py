"""
Rótulos dos gráficos de ranking (top depositantes/instituições) - nomes
muito longos (ex.: "HUANENG CLEAN ENERGY RESEARCH INSTITUTE OF CHINA
HUANENG GROUP CO LTD") empurram o eixo e espremem as barras. Só o RÓTULO
desenhado é abreviado - o nome completo continua nos dados (resumo numérico
que vai pro texto do relatório, ver report_lifecycle.top_summary).

Ordem: abreviações padronizadas (estilo ISO 4 / ABNT) -> remoção de
preposições/artigos -> corte na última palavra inteira com "…".
"""

from __future__ import annotations

import re

MAX_LABEL_LENGTH = 45

# palavra (minúscula) -> abreviação. Inglês (OPS/Scopus) e português.
_ABBREVIATIONS: dict[str, str] = {
    # inglês
    "university": "Univ.",
    "universities": "Univs.",
    "institute": "Inst.",
    "institutes": "Insts.",
    "institution": "Inst.",
    "technology": "Technol.",
    "technologies": "Technol.",
    "technological": "Technol.",
    "corporation": "Corp.",
    "company": "Co.",
    "limited": "Ltd.",
    "incorporated": "Inc.",
    "laboratory": "Lab.",
    "laboratories": "Labs.",
    "national": "Natl.",
    "research": "Res.",
    "department": "Dept.",
    "international": "Intl.",
    "engineering": "Eng.",
    "science": "Sci.",
    "sciences": "Sci.",
    "scientific": "Sci.",
    "academy": "Acad.",
    "association": "Assoc.",
    "development": "Dev.",
    "industrial": "Ind.",
    "industry": "Ind.",
    "industries": "Ind.",
    "electronics": "Electron.",
    "electronic": "Electron.",
    "electric": "Elec.",
    "electrical": "Elec.",
    "manufacturing": "Mfg.",
    "center": "Ctr.",
    "centre": "Ctr.",
    "government": "Govt.",
    "information": "Inf.",
    "communication": "Commun.",
    "communications": "Commun.",
    "aerospace": "Aerosp.",
    "aeronautics": "Aeronaut.",
    "aeronautical": "Aeronaut.",
    "astronautics": "Astronaut.",
    "automation": "Autom.",
    "college": "Coll.",
    "school": "Sch.",
    "systems": "Syst.",
    "system": "Syst.",
    "management": "Mgmt.",
    "applied": "Appl.",
    "advanced": "Adv.",
    "agricultural": "Agric.",
    "medical": "Med.",
    "chemical": "Chem.",
    "mechanical": "Mech.",
    "polytechnic": "Polytech.",
    "foundation": "Found.",
    "hospital": "Hosp.",
    "federal": "Fed.",
    # português
    "universidade": "Univ.",
    "instituto": "Inst.",
    "tecnologia": "Tecnol.",
    "tecnológico": "Tecnol.",
    "tecnológica": "Tecnol.",
    "nacional": "Nac.",
    "pesquisa": "Pesq.",
    "pesquisas": "Pesq.",
    "departamento": "Depto.",
    "engenharia": "Eng.",
    "ciências": "Ciênc.",
    "ciência": "Ciênc.",
    "empresa": "Emp.",
    "brasileira": "Bras.",
    "brasileiro": "Bras.",
    "laboratório": "Lab.",
    "fundação": "Fund.",
}

_STOPWORDS = {"of", "the", "and", "for", "de", "da", "do", "das", "dos", "e", "a", "o"}

_WORD_RE = re.compile(r"[^\W\d_]+(?:[-'][^\W\d_]+)*", re.UNICODE)


def _match_case(original: str, replacement: str) -> str:
    """Nomes da OPS vêm em MAIÚSCULAS - a abreviação acompanha."""
    return replacement.upper() if original.isupper() and len(original) > 1 else replacement


def _abbreviate_words(name: str) -> str:
    def replace(match: re.Match[str]) -> str:
        word = match.group(0)
        abbreviation = _ABBREVIATIONS.get(word.lower())
        return _match_case(word, abbreviation) if abbreviation else word

    abbreviated = _WORD_RE.sub(replace, name)
    # "Co.," / "Ltd.." etc. - pontuação duplicada deixada pela troca.
    return re.sub(r"\.{2,}", ".", abbreviated)


def _drop_stopwords(name: str) -> str:
    words = name.split()
    kept = [w for i, w in enumerate(words) if i == 0 or w.lower().strip(",.") not in _STOPWORDS]
    return " ".join(kept)


def _truncate(name: str, max_length: int) -> str:
    if len(name) <= max_length:
        return name
    cut = name[: max_length - 1]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,;-.") + "…"


def abbreviate_label(name: str, max_length: int = MAX_LABEL_LENGTH) -> str:
    """Nome com até `max_length` caracteres - intacto se já couber."""
    name = " ".join(str(name).split())
    if len(name) <= max_length:
        return name
    for step in (_abbreviate_words, _drop_stopwords):
        name = step(name)
        if len(name) <= max_length:
            return name
    return _truncate(name, max_length)


def abbreviate_labels(names: list[str], max_length: int = MAX_LABEL_LENGTH) -> list[str]:
    """Abrevia cada nome mantendo os rótulos DISTINTOS entre si - dois nomes
    diferentes que ficassem iguais depois de abreviados seriam fundidos numa
    barra só pelo matplotlib (mesmo rótulo no eixo categórico)."""
    labels: list[str] = []
    seen: dict[str, int] = {}
    for name in names:
        label = abbreviate_label(name, max_length)
        if label in seen:
            seen[label] += 1
            suffix = f" ({seen[label]})"
            label = _truncate(label, max_length - len(suffix)) + suffix
        else:
            seen[label] = 1
        labels.append(label)
    return labels
