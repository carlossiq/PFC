from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class TextGenerationPort(Protocol):
    """
    Geração de texto livre a partir de um prompt - usado pelo
    ReportWriterService pra redigir cada seção do relatório (Finalidade,
    Introdução, Resultados, ...). Deliberadamente menor que LLMPort
    (process_intake/call_raw_json, voltado a JSON estruturado do fluxo de
    refino de tema/query): aqui a saída é sempre texto solto em português,
    não um schema.
    """

    async def generate(self, prompt: str, system: Optional[str] = None) -> str: ...
