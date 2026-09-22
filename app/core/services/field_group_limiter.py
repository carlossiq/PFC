"""
Achata o número de grupos de conceito em TITLE/ABSTRACT para o teto
permitido pela variante da busca final (ver FIELD GUIDELINES em
final_system_prompt.md) - rede de segurança estrutural para o mesmo tipo
de problema que classification_code_validator.py resolve para CPC/IPC:
um modelo pequeno (ex: gemma3:4b) segue a tabela de contagem de grupos do
prompt de forma inconsistente (confirmado ao vivo: pedida no máximo 2
grupos no ABSTRACT para a variante GENERIC, o modelo devolveu 3), e cada
grupo extra vira mais um AND - o que reduz drasticamente o recall de uma
busca que deveria ser "ampla" (ver BaseQueryBuilder._title_abstract_operator
e a seção BOOLEAN STRUCTURE do prompt).

Em vez de rejeitar/descartar termos, os grupos excedentes são fundidos num
único grupo OR final - preserva 100% dos termos gerados pela IA, só ajusta
a estrutura booleana para o nível de restrição que a variante pede.

Além do teto de grupos, também força group_operator="AND" entre os grupos
que sobrarem (quando há mais de um) - confirmado ao vivo que, mesmo com a
contagem de grupos dentro do limite, o modelo às vezes escolhe
group_operator="OR" pra satisfazer "0-1 AND total" da variante GENERIC de
forma literal, só que isso quebra a exigência de que os conceitos CORE
coexistam no mesmo documento (ver CONCEPT PRIORITY/CORE LOGIC do prompt) -
title="military communication" OR title="trunked radio" casa qualquer
patente que mencione só "military communication" (ex: uma patente
farmacêutica citando prior art militar), sem nenhuma relação com rádio
troncalizado. A "amplitude" de uma variante GENERIC deve vir de menos
grupos/mais termos por grupo (ver FIELD GUIDELINES), nunca de tornar os
conceitos opcionais entre si.
"""

from __future__ import annotations

import dataclasses

# O tipo real de llm_response em ChatService (retorno de
# LLMPort.process_intake) é o dataclass de domínio app.core.domain.types -
# schemas.llm.LLMOutput só entra depois, na conversão feita por
# app/adapters/driven/query_builders/_converters.py::response_to_output.
# Usar schemas.llm aqui (pydantic, com .model_copy()) parecia funcionar em
# teste unitário isolado mas quebrava em runtime real (AttributeError:
# 'TextualQuery' object has no attribute 'model_copy'), silenciosamente
# tratado como "sem efeito" só por coincidência de timing de reload - por
# isso a confirmação final foi testar contra o dataclass de verdade.
from app.core.domain.types import LLMResponse, TermGroup, TextualQuery

# Espelha a tabela "FIELD GUIDELINES" de config/prompts/final_system_prompt.md -
# se a tabela mudar lá, mude aqui também.
_MAX_GROUPS_BY_VARIANT: dict[str, dict[str, int]] = {
    "specific": {"title": 3, "abstract": 4},
    "balanced": {"title": 2, "abstract": 3},
    "generic": {"title": 2, "abstract": 2},
}


def enforce_group_limit(field: TextualQuery, max_groups: int) -> TextualQuery:
    """Funde grupos excedentes de `field` num único grupo OR final, até
    respeitar `max_groups`, e força group_operator="AND" entre os grupos
    restantes (quando há mais de um) - ver docstring do módulo. Não mexe em
    field.groups[i].operator (o operador DENTRO de cada grupo, entre os
    termos/sinônimos), só no operador ENTRE grupos (entre conceitos)."""
    groups = field.groups
    if max_groups > 0 and len(groups) > max_groups:
        kept = groups[: max_groups - 1]
        overflow = groups[max_groups - 1 :]

        merged_terms: list[str] = []
        for group in overflow:
            for term in group.terms:
                if term not in merged_terms:
                    merged_terms.append(term)

        groups = [*kept, TermGroup(operator="OR", terms=merged_terms)]

    group_operator = "AND" if len(groups) > 1 else field.group_operator
    if groups is field.groups and group_operator == field.group_operator:
        return field
    return dataclasses.replace(field, groups=groups, group_operator=group_operator)


def enforce_final_query_group_limits(llm_response: LLMResponse, variant: str) -> None:
    """Aplica enforce_group_limit em TITLE/ABSTRACT de `llm_response`
    in-place, conforme o teto de `variant` (specific/balanced/generic - ver
    _MAX_GROUPS_BY_VARIANT). Sem efeito para variantes desconhecidas (a
    busca probe não tem variant e nunca chama esta função)."""
    limits = _MAX_GROUPS_BY_VARIANT.get(variant)
    if not limits:
        return

    llm_response.title = enforce_group_limit(llm_response.title, limits.get("title", 99))
    llm_response.abstract = enforce_group_limit(llm_response.abstract, limits.get("abstract", 99))
