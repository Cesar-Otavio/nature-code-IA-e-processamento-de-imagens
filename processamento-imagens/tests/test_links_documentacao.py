"""Links locais da documentação: nenhum aponta para arquivo ou âncora inexistente.

Varre todos os ``.md`` versionáveis do repositório (README raiz, ``docs/`` e
``processamento-imagens/``). URLs externas **não** são verificadas — não há acesso à rede
nos testes.

Âncoras (``arquivo.md#secao``) são conferidas com a regra de geração do GitHub: minúsculas,
pontuação removida, espaços viram hífens, acentos preservados, títulos repetidos recebem
sufixo ``-1``, ``-2``…
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
IGNORAR = (".venv", "dataset/dados", "resultados/", ".pytest_cache", "node_modules", "fotos-externas/imagens")

LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
TITULO = re.compile(r"^#{1,6}\s+(.*)$", re.M)
BLOCO_DE_CODIGO = re.compile(r"```.*?```", re.S)


def _documentos() -> list[Path]:
    return sorted(p for p in RAIZ.rglob("*.md") if not any(i in p.as_posix() for i in IGNORAR))


def _slug(titulo: str) -> str:
    texto = titulo.replace("`", "").strip().lower()
    texto = re.sub(r"[^\w\- ]", "", texto)
    return texto.replace(" ", "-")


def ancoras(caminho: Path) -> set[str]:
    texto = BLOCO_DE_CODIGO.sub("", caminho.read_text(encoding="utf-8"))
    vistas: dict[str, int] = {}
    resultado: set[str] = set()
    for titulo in TITULO.findall(texto):
        base = _slug(titulo)
        n = vistas.get(base, 0)
        resultado.add(base if n == 0 else f"{base}-{n}")
        vistas[base] = n + 1
    return resultado


def links_quebrados(caminho: Path) -> tuple[list[str], int]:
    """Devolve (problemas, quantidade de links locais conferidos)."""
    texto = BLOCO_DE_CODIGO.sub("", caminho.read_text(encoding="utf-8"))
    problemas: list[str] = []
    conferidos = 0
    for alvo in LINK.findall(texto):
        if re.match(r"^[a-zA-Z][a-zA-Z+.-]*:", alvo):  # http:, https:, mailto:
            continue
        conferidos += 1
        arquivo, _, ancora = alvo.partition("#")
        destino = (caminho.parent / arquivo).resolve() if arquivo else caminho.resolve()
        if not destino.exists():
            problemas.append(f"{alvo} → arquivo inexistente")
        elif ancora and destino.suffix == ".md" and ancora not in ancoras(destino):
            problemas.append(f"{alvo} → âncora inexistente")
    return problemas, conferidos


DOCUMENTOS = _documentos()


@pytest.mark.parametrize("documento", DOCUMENTOS, ids=[p.relative_to(RAIZ).as_posix() for p in DOCUMENTOS])
def test_links_locais_existem(documento: Path) -> None:
    problemas, _ = links_quebrados(documento)
    assert not problemas, f"{documento.relative_to(RAIZ)}:\n  " + "\n  ".join(problemas)


def test_a_varredura_confere_links_de_verdade() -> None:
    """Evita um 'zero problemas' por não ter encontrado link nenhum."""
    total = sum(links_quebrados(p)[1] for p in DOCUMENTOS)
    assert len(DOCUMENTOS) >= 30
    assert total >= 200


def test_documentos_da_entrega_estao_na_varredura() -> None:
    nomes = {p.relative_to(RAIZ).as_posix() for p in DOCUMENTOS}
    for obrigatorio in ("README.md", "docs/DOCUMENTACAO-FINAL-IA-PDI.md", "docs/CHECKLIST-ENTREGA-FINAL.md",
                        "docs/TESTES-MANUAIS-FINAIS.md", "docs/ROTEIRO-DEMO.md", "docs/REQUISITOS-PROFESSOR.md"):
        assert obrigatorio in nomes


def test_detector_acusa_arquivo_e_ancora_quebrados(tmp_path: Path) -> None:
    (tmp_path / "alvo.md").write_text("# Seção Única\n\n## 2. Navegador\n", encoding="utf-8")
    doc = tmp_path / "doc.md"
    doc.write_text(
        "[ok](alvo.md) [ok](alvo.md#2-navegador) [ok](alvo.md#seção-única) [ext](https://x.y/z)\n"
        "[quebrado](nao-existe.md) [âncora](alvo.md#3-inexistente)\n"
        "```\n[ignorado em código](sumiu.md)\n```\n",
        encoding="utf-8",
    )
    problemas, conferidos = links_quebrados(doc)
    assert conferidos == 5
    assert len(problemas) == 2
    assert any("nao-existe.md" in p for p in problemas)
    assert any("3-inexistente" in p for p in problemas)


def test_nenhum_caminho_pessoal_na_documentacao() -> None:
    padrao = re.compile(r"[A-Za-z]:[\\/]Users[\\/]|/home/[a-z]|\\Users\\", re.I)
    ocorrencias = [p.relative_to(RAIZ).as_posix() for p in DOCUMENTOS if padrao.search(p.read_text(encoding="utf-8"))]
    assert not ocorrencias, f"caminho pessoal em: {ocorrencias}"
