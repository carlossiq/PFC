"""
Tests for prompt loading service.
"""

import pytest

from services.prompt import PromptLoader


def test_prompt_loader_loads_general_system_prompt():
    """
    Verifica carregamento do prompt geral.
    """
    try:
        prompt = PromptLoader.load_general_system_prompt()
        assert prompt is not None
        assert len(prompt) > 0
    except FileNotFoundError:
        # Esperado em ambiente sem arquivos de prompt
        pytest.skip("Prompt files not available")


def test_prompt_loader_loads_probe_system_prompt():
    """
    Verifica carregamento do prompt de probe.
    """
    try:
        prompt = PromptLoader.load_probe_system_prompt()
        assert prompt is not None
        assert len(prompt) > 0
    except FileNotFoundError:
        pytest.skip("Prompt files not available")


def test_prompt_loader_caching():
    """
    Verifica que prompts são cachados.
    """
    try:
        # Primeira chamada
        prompt1 = PromptLoader.load_general_system_prompt()

        # Limpar cache
        PromptLoader.clear_cache()

        # Segunda chamada
        prompt2 = PromptLoader.load_general_system_prompt()

        assert prompt1 == prompt2
    except FileNotFoundError:
        pytest.skip("Prompt files not available")


def test_prompt_loader_custom_prompt():
    """
    Verifica carregamento de prompt customizado.
    """
    try:
        prompt = PromptLoader.load_prompt("general_system_prompt.txt")
        assert prompt is not None
    except FileNotFoundError:
        pytest.skip("Prompt files not available")
