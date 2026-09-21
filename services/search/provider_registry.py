"""
Registry de providers de busca suportados por família (patent/scholarly) -
mesmo espírito de app/adapters/driven/llm/provider_registry.py: um dict
Python, não uma tabela de banco, porque suportar uma API nova sempre exige
um adapter + query builder novos (código), não só dado. `SearchApiSelection`
(db/config_models.py) guarda só qual código está ATIVO por família; a lista
de códigos válidos pra cada família vem daqui - usado tanto pra validar a
escrita (não deixar selecionar um código que não existe) quanto pro front
listar as opções do seletor.

Extensão: uma API nova pro patente (ex: "uspto") = 1 entrada nova em
SEARCH_PROVIDER_REGISTRY["patent"] + construir o adapter/query builder dela
em app/container.py::_build_search_pair - sem tocar em SearchApiSelection,
endpoints ou frontend.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchProviderSpec:
    code: str
    display_name: str
    family: str  # "patent" | "scholarly"


SEARCH_PROVIDER_REGISTRY: dict[str, dict[str, SearchProviderSpec]] = {
    "patent": {
        "ops": SearchProviderSpec(code="ops", display_name="OPS (European Patent Office)", family="patent"),
        "lens_patent": SearchProviderSpec(code="lens_patent", display_name="Lens Patent", family="patent"),
    },
    "scholarly": {
        "scopus": SearchProviderSpec(code="scopus", display_name="Scopus (Elsevier)", family="scholarly"),
        "lens_scholarly": SearchProviderSpec(code="lens_scholarly", display_name="Lens Scholarly", family="scholarly"),
    },
}


def is_valid_provider_for_family(family: str, provider_code: str) -> bool:
    return provider_code in SEARCH_PROVIDER_REGISTRY.get(family, {})


def list_providers_for_family(family: str) -> list[SearchProviderSpec]:
    return list(SEARCH_PROVIDER_REGISTRY.get(family, {}).values())
