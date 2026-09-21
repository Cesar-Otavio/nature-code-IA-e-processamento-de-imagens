"""Testes da interface de linha de comando."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from src.cli import CODIGOS_DE_SAIDA, main, montar_analisador


@pytest.fixture
def folha(tmp_path: Path) -> Path:
    tela = np.full((700, 900, 3), 250, dtype=np.uint8)
    cv2.ellipse(tela, (450, 350), (280, 110), 25, 0, 360, (40, 140, 60), -1)
    destino = tmp_path / "folha.png"
    cv2.imwrite(str(destino), tela)
    return destino


@pytest.fixture
def vazia(tmp_path: Path) -> Path:
    destino = tmp_path / "vazia.png"
    cv2.imwrite(str(destino), np.full((400, 400, 3), 250, dtype=np.uint8))
    return destino


# ---------------------------------------------------------------------------
# Casca fina — a garantia estrutural
# ---------------------------------------------------------------------------

def _imports_de(caminho: Path) -> set[str]:
    arvore = ast.parse(caminho.read_text(encoding="utf-8"), filename=str(caminho))
    encontrados: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for alias in no.names:
                encontrados.add(alias.name.split(".")[0])
        elif isinstance(no, ast.ImportFrom) and no.module:
            encontrados.add(no.module.split(".")[0])
    return encontrados


def test_cli_nao_importa_opencv_nem_numpy() -> None:
    """Se a CLI precisasse de cv2, haveria lógica duplicada nela."""
    caminho = Path(__file__).resolve().parent.parent / "src" / "cli.py"
    importados = _imports_de(caminho)

    assert "cv2" not in importados
    assert "numpy" not in importados


def test_cli_importa_apenas_o_pipeline() -> None:
    caminho = Path(__file__).resolve().parent.parent / "src" / "cli.py"
    texto = caminho.read_text(encoding="utf-8")

    for modulo in ("segmentation", "morphology", "contours", "features", "classification"):
        assert f"from .{modulo}" not in texto, f"cli.py importa {modulo} diretamente"
    assert "from .pipeline import" in texto


def test_cli_nao_importa_flask() -> None:
    caminho = Path(__file__).resolve().parent.parent / "src" / "cli.py"
    assert "flask" not in _imports_de(caminho)


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------

def test_imagem_valida_retorna_zero(folha: Path, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    codigo = main([str(folha), "--saida", str(tmp_path / "saida")])

    assert codigo == 0
    saida = capsys.readouterr().out
    assert "Imagem processada com sucesso" in saida
    assert "área" in saida
    assert "Descrição morfológica" in saida


def test_arquivo_inexistente_retorna_dois(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    codigo = main([str(tmp_path / "nao-existe.jpg")])

    assert codigo == 2
    assert "E001" in capsys.readouterr().err


def test_arquivo_invalido_retorna_dois(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    destino = tmp_path / "falso.jpg"
    destino.write_text("nao e imagem", encoding="utf-8")

    assert main([str(destino)]) == 2
    assert "E003" in capsys.readouterr().err


def test_sem_objeto_retorna_um(vazia: Path, capsys: pytest.CaptureFixture) -> None:
    """Erro de processamento, não de entrada — código diferente."""
    assert main([str(vazia), "--sem-imagens"]) == 1
    assert "E007" in capsys.readouterr().err


def test_json_apenas_produz_json_valido(folha: Path, capsys: pytest.CaptureFixture) -> None:
    codigo = main([str(folha), "--json-apenas", "--sem-imagens"])
    saida = capsys.readouterr().out

    assert codigo == 0
    dados = json.loads(saida)
    assert dados["status"] in ("sucesso", "sucesso_com_avisos")
    assert "caracteristicas" in dados


def test_json_apenas_nao_mistura_texto(folha: Path, capsys: pytest.CaptureFixture) -> None:
    """Para uso em script, a saída precisa ser JSON puro."""
    main([str(folha), "--json-apenas", "--sem-imagens"])
    saida = capsys.readouterr().out.strip()

    assert saida.startswith("{")
    assert saida.endswith("}")
    assert "Imagem processada" not in saida


def test_sem_imagens_nao_grava_nada(folha: Path, tmp_path: Path) -> None:
    destino = tmp_path / "nao-deve-existir"
    main([str(folha), "--sem-imagens", "--saida", str(destino)])
    assert not destino.exists()


def test_com_imagens_grava_oito(folha: Path, tmp_path: Path) -> None:
    destino = tmp_path / "saida"
    main([str(folha), "--saida", str(destino)])

    assert destino.is_dir()
    assert len(list(destino.glob("*.png"))) == 8


def test_verboso_detalha_tempos(folha: Path, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    main([str(folha), "--verboso", "--sem-imagens"])
    erro = capsys.readouterr().err

    assert "segmentacao" in erro
    assert "ms" in erro


def test_erro_vai_para_stderr(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """stdout fica livre para o JSON; erros vão para stderr."""
    main([str(tmp_path / "x.jpg")])
    capturado = capsys.readouterr()

    assert capturado.out == ""
    assert "E001" in capturado.err


def test_erro_nao_expoe_rastreamento(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    main([str(tmp_path / "x.jpg")])
    assert "Traceback" not in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Argumentos e códigos
# ---------------------------------------------------------------------------

def test_analisador_tem_as_flags_previstas() -> None:
    acoes = {acao.dest for acao in montar_analisador()._actions}
    assert {"imagem", "saida", "sem_imagens", "json_apenas", "verboso"} <= acoes


def test_mapa_de_codigos_de_saida() -> None:
    """O contrato de exit codes da Fase 1."""
    assert CODIGOS_DE_SAIDA["E001"] == 2
    assert CODIGOS_DE_SAIDA["E002"] == 2
    assert CODIGOS_DE_SAIDA["E003"] == 2
    assert CODIGOS_DE_SAIDA["E007"] == 1
    assert CODIGOS_DE_SAIDA["E008"] == 3


def test_descricao_declara_que_nao_usa_ia() -> None:
    descricao = montar_analisador().description or ""
    assert "não utiliza inteligência artificial" in descricao.lower()
    assert "não identifica espécies" in descricao.lower()


def test_avisos_aparecem_no_resumo(folha: Path, capsys: pytest.CaptureFixture) -> None:
    main([str(folha), "--sem-imagens"])
    saida = capsys.readouterr().out
    assert "Avisos" in saida or "avisos" in saida
