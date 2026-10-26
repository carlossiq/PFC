"""
Verifica o setup do banco a partir do zero (passo 4 do README).

Roda as migrations e a inicialização duas vezes contra o banco de DATABASE_URL
e confere o estado final: head do Alembic aplicado e uma linha em app_settings
por entrada do seed. A segunda rodada prova que nada duplica.

Uso (na raiz do projeto, com a venv ativa):
    python scripts/verify_fresh_setup.py

Aplica migrations e grava o seed no banco apontado: use um banco de teste ou vazio.
"""

import subprocess
import sys
from pathlib import Path

import psycopg2
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.config import settings  # noqa: E402
from db.config_seed import _SETTINGS_SEED  # noqa: E402


def _run(args: list[str]) -> None:
    result = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise SystemExit(f"[FALHA] {' '.join(args)}")
    print(f"[OK] {' '.join(args)}")


def _sync_url() -> str:
    # psycopg2 não aceita o driver asyncpg da DATABASE_URL usada pelo app.
    return settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def main() -> None:
    for _ in range(2):
        _run(["-m", "alembic", "upgrade", "head"])
        _run(["-m", "db.init_db"])

    head = ScriptDirectory(str(ROOT / "alembic")).get_current_head()
    with psycopg2.connect(_sync_url()) as conn, conn.cursor() as cur:
        cur.execute("SELECT version_num FROM alembic_version")
        applied = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM app_settings")
        seeded = cur.fetchone()[0]

    expected = len(_SETTINGS_SEED)
    if applied != head:
        raise SystemExit(f"[FALHA] alembic em {applied}, esperado {head}")
    if seeded != expected:
        raise SystemExit(f"[FALHA] app_settings com {seeded} linhas, esperado {expected}")
    print(f"[OK] alembic em {head}, app_settings com {seeded} linhas (sem duplicar)")


if __name__ == "__main__":
    main()
