"""
Gera config/cpc_titles.json (código -> título oficial) a partir das listas
oficiais de títulos da CPC (EPO/USPTO) e da IPC (WIPO), usada pra passar ao
LLM o significado REAL de cada classificação no relatório (ver
app/core/services/cpc_titles.py) - sem isso o modelo descrevia os códigos
por conta própria e errava (ex.: "B09B = produção de energia solar").

Só seções, classes e subclasses (ex.: "H", "H10", "H10F"): a busca final
agrega as classificações no nível de subclasse (4 caracteres, ver
ChatService._aggregate_ops_final_items). Os códigos vêm do campo IPC da
OPS, então a lista da IPC completa o que não existir na CPC - a CPC tem
precedência. Códigos extintos nas duas (ex.: H01L, reorganizada em H10)
ficam fora; cpc_titles.py cai no título da classe. Remissões entre
parênteses ("(making or covering furrows ... A01C5/00)") são removidas.

Uso (precisa de internet só aqui, nunca em tempo de execução):
    python scripts/build_cpc_titles.py [CPC_ZIP] [IPC_ZIP]

Cada argumento aceita URL ou caminho local; sem argumento, usa as versões
abaixo. Listas atuais em
https://www.cooperativepatentclassification.org/cpcSchemeAndDefinitions/bulk
e https://www.wipo.int/ipc/itos4ipc/ITSupport_and_download_area/
"""

from __future__ import annotations

import io
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

DEFAULT_CPC_URL = "https://www.cooperativepatentclassification.org/sites/default/files/cpc/bulk/CPCTitleList202608.zip"
DEFAULT_IPC_URL = (
    "https://www.wipo.int/ipc/itos4ipc/ITSupport_and_download_area/20260101/"
    "IPC_scheme_title_list/EN_ipc_title_list_20260101.zip"
)
OUTPUT = Path(__file__).resolve().parents[1] / "config" / "cpc_titles.json"

_CODE_RE = re.compile(r"^[A-HY](\d{2}([A-Z])?)?$")


def _strip_references(title: str) -> str:
    """Remove blocos "(...)" (com aninhamento) e chaves "{...}" do título."""
    out, depth = [], 0
    for ch in title:
        if ch == "(":
            depth += 1
        elif ch == ")" and depth:
            depth -= 1
        elif depth == 0:
            out.append(ch)
    return " ".join("".join(out).replace("{", "").replace("}", "").split()).strip(" ;,")


def build(zip_bytes: bytes) -> dict[str, str]:
    """Aceita os dois formatos: CPC ("código<TAB>nível<TAB>título") e IPC
    ("código<TAB>título") - o título é sempre a última coluna."""
    titles: dict[str, str] = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        for name in sorted(archive.namelist()):
            if not name.endswith(".txt"):
                continue
            for line in archive.read(name).decode("utf-8").splitlines():
                parts = line.split("\t")
                if len(parts) < 2 or not _CODE_RE.match(parts[0]):
                    continue
                titles[parts[0]] = _strip_references(parts[-1])
    return titles


def _read(source: str) -> bytes:
    if source.startswith("http"):
        with urllib.request.urlopen(source, timeout=120) as response:
            return response.read()
    return Path(source).read_bytes()


def main() -> None:
    cpc_source = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CPC_URL
    ipc_source = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_IPC_URL
    titles = build(_read(ipc_source))
    titles.update(build(_read(cpc_source)))  # CPC tem precedência
    payload = {
        "sources": [
            f"CPC {re.sub(r'.*?(\d{6}).*', r'\1', cpc_source)}",
            f"IPC {re.sub(r'.*?(\d{8}).*', r'\1', ipc_source)}",
        ],
        "titles": titles,
    }
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"{len(titles)} títulos gravados em {OUTPUT}")


if __name__ == "__main__":
    main()
