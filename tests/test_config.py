"""
Tests for configuration loading.
"""

from core.config import settings


def test_config_loads_from_env():
    """
    Verifica que configuração carrega corretamente.
    """
    assert settings.app_name is not None
    assert settings.app_version is not None
    assert settings.host is not None
    assert settings.port > 0


def test_config_has_required_fields():
    """
    Verifica campos obrigatórios de config.
    """
    required_fields = [
        "app_name",
        "environment",
        "host",
        "port",
        "api_prefix",
    ]

    for field in required_fields:
        assert hasattr(settings, field)


def test_config_defaults():
    """
    Verifica valores padrão de configuração.
    """
    assert settings.port == 8000
    assert settings.host == "0.0.0.0"
    assert settings.api_prefix == "/api/v1"
    assert isinstance(settings.allowed_origins, list)
