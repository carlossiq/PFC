"""
Token cost calculator for different LLM models.

Provides standardized cost calculations for various providers.
"""

from typing import Optional, Tuple

from core.logging import get_logger

logger = get_logger(__name__)

# Pricing as of 2024 (in USD per 1M tokens)
PRICING = {
    "gemini": {
        "gemini-1.5-pro": {"input": 0.075, "output": 0.30},
        "gemini-1.5-flash": {"input": 0.0375, "output": 0.15},
        "gemini-pro": {"input": 0.0005, "output": 0.0015},
    },
    "gpt-4": {
        "gpt-4-turbo": {"input": 10.0, "output": 30.0},
        "gpt-4": {"input": 30.0, "output": 60.0},
        "gpt-4-32k": {"input": 60.0, "output": 120.0},
    },
    "claude": {
        "claude-3-opus": {"input": 15.0, "output": 75.0},
        "claude-3-sonnet": {"input": 3.0, "output": 15.0},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
        "claude-2.1": {"input": 8.0, "output": 24.0},
    },
    "mistral": {
        "mistral-large": {"input": 8.0, "output": 24.0},
        "mistral-medium": {"input": 2.7, "output": 8.1},
        "mistral-small": {"input": 0.14, "output": 0.42},
    },
}


def get_model_pricing(model: str, variant: Optional[str] = None) -> Optional[dict[str, float]]:
    """
    Get pricing for a specific model.

    Args:
        model: Model name (gemini, gpt-4, claude, mistral)
        variant: Model variant (e.g., gemini-1.5-pro, gpt-4-turbo)

    Returns:
        Dict with 'input' and 'output' keys in USD per 1M tokens, or None if not found
    """
    if model not in PRICING:
        logger.warning("unknown_model_pricing", model=model)
        return None

    # If variant provided, try to find exact match
    if variant and variant in PRICING[model]:
        return PRICING[model][variant]

    # Otherwise return first available variant
    if PRICING[model]:
        first_variant = next(iter(PRICING[model].values()))
        logger.warning(
            "model_variant_not_found",
            model=model,
            requested_variant=variant,
            using_variant=next(iter(PRICING[model].keys())),
        )
        return first_variant

    return None


def calculate_token_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    variant: Optional[str] = None,
) -> Tuple[float, float, float]:
    """
    Calculate cost for token usage.

    Args:
        model: Model name (gemini, gpt-4, claude, mistral)
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        variant: Model variant (optional)

    Returns:
        Tuple of (input_cost_usd, output_cost_usd, total_cost_usd)
    """
    pricing = get_model_pricing(model, variant)

    if not pricing:
        logger.error(
            "no_pricing_found",
            model=model,
            variant=variant,
        )
        return 0.0, 0.0, 0.0

    # Pricing is per 1M tokens
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    total_cost = input_cost + output_cost

    return input_cost, output_cost, total_cost


def format_cost(cost_usd: float) -> str:
    """
    Format cost as readable string.

    Args:
        cost_usd: Cost in USD

    Returns:
        Formatted cost string
    """
    if cost_usd < 0.0001:
        return f"${cost_usd:.6f}"
    elif cost_usd < 0.01:
        return f"${cost_usd:.4f}"
    else:
        return f"${cost_usd:.2f}"


def format_tokens(token_count: int) -> str:
    """
    Format token count as readable string.

    Args:
        token_count: Number of tokens

    Returns:
        Formatted token count
    """
    if token_count >= 1_000_000:
        return f"{token_count / 1_000_000:.1f}M"
    elif token_count >= 1_000:
        return f"{token_count / 1_000:.1f}K"
    else:
        return str(token_count)
