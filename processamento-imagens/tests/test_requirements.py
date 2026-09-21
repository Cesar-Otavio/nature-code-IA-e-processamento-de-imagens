"""Arquivos de dependências: a raiz delega ao módulo, sem duplicar versões.

``requirements.txt`` na raiz existe para que ``pip install -r requirements.txt`` funcione
a partir da raiz do repositório. A fonte real das dependências continua sendo
``processamento-imagens/requirements.txt``.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
MODULO = RAIZ / "processamento-imagens"


def _linhas_efetivas(caminho: Path) -> list[str]:
    return [l.strip() for l in caminho.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.strip().startswith("#")]


def test_raiz_delega_ao_modulo_sem_duplicar_versoes() -> None:
    linhas = _linhas_efetivas(RAIZ / "requirements.txt")
    assert linhas == ["-r processamento-imagens/requirements.txt"]


def test_arquivos_referenciados_existem() -> None:
    """Cada ``-r`` resolve relativo ao arquivo que o contém, como faz o pip."""
    for arquivo in (RAIZ / "requirements.txt", MODULO / "requirements-dev.txt"):
        for linha in _linhas_efetivas(arquivo):
            if linha.startswith("-r "):
                assert (arquivo.parent / linha[3:].strip()).is_file(), f"{arquivo.name}: {linha}"


def test_versoes_do_modulo_continuam_fixadas() -> None:
    linhas = _linhas_efetivas(MODULO / "requirements.txt")
    assert linhas == ["numpy==2.5.3", "opencv-python==5.0.0.93", "Flask==3.1.3"]
    assert _linhas_efetivas(MODULO / "requirements-dev.txt") == ["-r requirements.txt", "pytest==9.1.1"]


def test_nenhuma_dependencia_de_ia() -> None:
    proibidas = re.compile(r"torch|tensorflow|keras|sklearn|scikit|transformers|ultralytics|onnx|ollama|openai",
                           re.I)
    for arquivo in (RAIZ / "requirements.txt", MODULO / "requirements.txt", MODULO / "requirements-dev.txt"):
        assert not proibidas.search(arquivo.read_text(encoding="utf-8")), arquivo.name
