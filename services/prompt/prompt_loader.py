"""
Prompt loading service for loading prompts from disk.
"""

from pathlib import Path
from typing import Optional

from core.logging import get_logger

logger = get_logger(__name__)


class PromptLoader:
    """
    Carrega prompts do sistema de arquivo.

    Gerencia templates de prompts para diferentes modos de busca
    e casos de uso, permitindo manutenção separada dos prompts.
    """

    # Diretório de prompts (relativo ao raiz do projeto)
    PROMPTS_DIR = Path(__file__).parent.parent.parent / "config" / "prompts"

    # Cache de prompts em memória
    _cache: dict[str, str] = {}

    @staticmethod
    def load_general_system_prompt() -> str:
        """
        Carrega prompt do sistema geral.

        Lê arquivo general_system_prompt.txt que contém instruções
        gerais para o LLM processar requisições de prospecção exploratória.

        Returns:
            Conteúdo do prompt do sistema.

        Raises:
            FileNotFoundError: Se arquivo não existir.
        """
        return PromptLoader._load_prompt("general_system_prompt.txt")

    @staticmethod
    def load_probe_system_prompt() -> str:
        """
        Carrega prompt do sistema para modo probe.

        Lê arquivo probe_system_prompt.txt que contém instruções
        gerais para o LLM processar requisições de prospecção inicial.

        Returns:
            Conteúdo do prompt do sistema.

        Raises:
            FileNotFoundError: Se arquivo não existir.
        """
        return PromptLoader._load_prompt("probe_system_prompt.txt")

    @staticmethod
    def load_refine_topic_system_prompt() -> str:
        """
        Carrega prompt do sistema para refinamento de tópicos.

        Lê arquivo refine_topic_system_prompt.txt que contém instruções
        para o LLM refinar tópicos genéricos em variações mais específicas.

        Returns:
            Conteúdo do prompt do sistema.

        Raises:
            FileNotFoundError: Se arquivo não existir.
        """
        return PromptLoader._load_prompt("refine_topic_system_prompt.txt")

    @staticmethod
    def load_prompt(filename: str) -> str:
        """
        Carrega um prompt customizado pelo nome de arquivo.

        Args:
            filename: Nome do arquivo do prompt.

        Returns:
            Conteúdo do prompt.

        Raises:
            FileNotFoundError: Se arquivo não existir.
        """
        return PromptLoader._load_prompt(filename)

    @staticmethod
    def _load_prompt(filename: str) -> str:
        """
        Carrega prompt interno com cache.

        Args:
            filename: Nome do arquivo.

        Returns:
            Conteúdo do prompt.

        Raises:
            FileNotFoundError: Se arquivo não existir.
        """
        # Verificar cache
        if filename in PromptLoader._cache:
            return PromptLoader._cache[filename]

        # Construir caminho
        prompt_path = PromptLoader.PROMPTS_DIR / filename

        # Verificar existência
        if not prompt_path.exists():
            logger.error(
                f"prompt_file_not_found", filename=filename, path=str(prompt_path)
            )
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        # Carregar de arquivo
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Armazenar em cache
            PromptLoader._cache[filename] = content

            logger.info("prompt_loaded_from_disk", filename=filename)
            return content

        except Exception as exc:
            logger.error(f"failed_to_load_prompt", filename=filename, error=str(exc))
            raise

    @staticmethod
    def clear_cache() -> None:
        """
        Limpa cache de prompts.

        Útil para recarregar prompts atualizados sem reiniciar a aplicação.
        """
        PromptLoader._cache.clear()

    @staticmethod
    def get_cached_prompts() -> dict[str, str]:
        """
        Obtém dicionário de prompts em cache.

        Returns:
            Dicionário com prompts carregados.
        """
        return PromptLoader._cache.copy()
