"""Testes de validação de entrada e leitura de imagem."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.utils import (
    EXTENSOES_SUPORTADAS,
    Cronometro,
    ErroImagem,
    garantir_diretorio,
    ler_imagem,
    nome_seguro,
    validar_caminho,
    validar_dimensoes,
    validar_extensao,
)


# ---------------------------------------------------------------------------
# validar_caminho
# ---------------------------------------------------------------------------

def test_caminho_valido_e_aceito(arquivo_png_valido: Path) -> None:
    assert validar_caminho(arquivo_png_valido) == arquivo_png_valido


def test_arquivo_inexistente_gera_E001(tmp_path: Path) -> None:
    with pytest.raises(ErroImagem) as capturado:
        validar_caminho(tmp_path / "nao-existe.png")
    assert capturado.value.codigo == "E001"


def test_diretorio_em_vez_de_arquivo_gera_E001(tmp_path: Path) -> None:
    with pytest.raises(ErroImagem) as capturado:
        validar_caminho(tmp_path)
    assert capturado.value.codigo == "E001"


# ---------------------------------------------------------------------------
# validar_extensao
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("extensao", sorted(EXTENSOES_SUPORTADAS))
def test_extensoes_suportadas_sao_aceitas(extensao: str) -> None:
    assert validar_extensao(f"folha{extensao}") == extensao


def test_extensao_aceita_maiusculas() -> None:
    assert validar_extensao("FOLHA.JPG") == ".jpg"


@pytest.mark.parametrize("nome", ["doc.txt", "vetor.svg", "animado.gif", "sem_extensao"])
def test_extensao_nao_suportada_gera_E002(nome: str) -> None:
    with pytest.raises(ErroImagem) as capturado:
        validar_extensao(nome)
    assert capturado.value.codigo == "E002"


# ---------------------------------------------------------------------------
# validar_dimensoes
# ---------------------------------------------------------------------------

def test_dimensoes_validas_retornam_largura_e_altura() -> None:
    assert validar_dimensoes(np.zeros((200, 300, 3), dtype=np.uint8)) == (300, 200)


def test_matriz_vazia_gera_E004() -> None:
    with pytest.raises(ErroImagem) as capturado:
        validar_dimensoes(np.zeros((0, 0, 3), dtype=np.uint8))
    assert capturado.value.codigo == "E004"


def test_matriz_none_gera_E004() -> None:
    with pytest.raises(ErroImagem) as capturado:
        validar_dimensoes(None)  # type: ignore[arg-type]
    assert capturado.value.codigo == "E004"


def test_resolucao_abaixo_do_minimo_gera_E005() -> None:
    with pytest.raises(ErroImagem) as capturado:
        validar_dimensoes(np.zeros((20, 20, 3), dtype=np.uint8))
    assert capturado.value.codigo == "E005"


def test_lado_minimo_e_configuravel() -> None:
    # A mesma imagem que falha com o padrão passa com um mínimo menor.
    assert validar_dimensoes(np.zeros((20, 20, 3), dtype=np.uint8), lado_minimo=10) == (20, 20)


# ---------------------------------------------------------------------------
# ler_imagem
# ---------------------------------------------------------------------------

def test_le_png_valido(arquivo_png_valido: Path) -> None:
    imagem, meta = ler_imagem(arquivo_png_valido)
    assert imagem.shape == (400, 600, 3)
    assert meta["formato"] == "PNG"
    assert meta["largura_original_px"] == 600
    assert meta["altura_original_px"] == 400
    assert meta["canais"] == 3
    assert int(meta["bytes"]) > 0  # type: ignore[call-overload]


def test_le_jpg_valido(arquivo_jpg_valido: Path) -> None:
    imagem, meta = ler_imagem(arquivo_jpg_valido)
    assert imagem.shape == (400, 600, 3)
    assert meta["formato"] == "JPG"


def test_extensao_valida_com_conteudo_invalido_gera_E003(arquivo_jpg_falso: Path) -> None:
    """O caso central: extensão correta não prova que o arquivo é imagem."""
    with pytest.raises(ErroImagem) as capturado:
        ler_imagem(arquivo_jpg_falso)
    assert capturado.value.codigo == "E003"


def test_arquivo_vazio_gera_E004(arquivo_vazio: Path) -> None:
    with pytest.raises(ErroImagem) as capturado:
        ler_imagem(arquivo_vazio)
    assert capturado.value.codigo == "E004"


def test_extensao_invalida_gera_E002(arquivo_extensao_invalida: Path) -> None:
    with pytest.raises(ErroImagem) as capturado:
        ler_imagem(arquivo_extensao_invalida)
    assert capturado.value.codigo == "E002"


def test_imagem_minuscula_gera_E005(imagem_minuscula: Path) -> None:
    with pytest.raises(ErroImagem) as capturado:
        ler_imagem(imagem_minuscula)
    assert capturado.value.codigo == "E005"


def test_leitura_devolve_bgr(tmp_path: Path) -> None:
    """Confirma a convenção: o OpenCV lê em BGR, não em RGB."""
    import cv2

    destino = tmp_path / "azul.png"
    tela = np.zeros((100, 100, 3), dtype=np.uint8)
    tela[:, :] = (255, 0, 0)  # BGR puro: azul
    cv2.imwrite(str(destino), tela)

    imagem, _ = ler_imagem(destino)
    b, g, r = imagem[50, 50]
    assert (int(b), int(g), int(r)) == (255, 0, 0)


def test_leitura_e_deterministica(arquivo_png_valido: Path) -> None:
    primeira, _ = ler_imagem(arquivo_png_valido)
    segunda, _ = ler_imagem(arquivo_png_valido)
    assert np.array_equal(primeira, segunda)


# ---------------------------------------------------------------------------
# Erro de domínio
# ---------------------------------------------------------------------------

def test_erro_carrega_codigo_e_mensagem() -> None:
    erro = ErroImagem("E001", "Arquivo não encontrado.")
    assert erro.codigo == "E001"
    assert erro.mensagem == "Arquivo não encontrado."
    assert "E001" in str(erro)


def test_mensagem_nao_expoe_rastreamento(tmp_path: Path) -> None:
    """A mensagem de domínio é para pessoas, não para depuração."""
    with pytest.raises(ErroImagem) as capturado:
        validar_caminho(tmp_path / "ausente.png")
    texto = capturado.value.mensagem
    assert "Traceback" not in texto
    assert "File \"" not in texto


# ---------------------------------------------------------------------------
# nome_seguro
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("folha.jpg", "folha.jpg"),
        ("../../etc/passwd", "passwd"),
        ("C:\\Windows\\system32\\cmd.exe", "cmd.exe"),
        ("foto com espaço.png", "foto_com_espa_o.png"),
        ("...oculto", "oculto"),
        ("", "arquivo"),
        ("///", "arquivo"),
    ],
)
def test_nome_seguro(entrada: str, esperado: str) -> None:
    assert nome_seguro(entrada) == esperado


def test_nome_seguro_remove_diretorios() -> None:
    assert "/" not in nome_seguro("a/b/c/d.png")
    assert "\\" not in nome_seguro("a\\b\\c\\d.png")


# ---------------------------------------------------------------------------
# Apoio
# ---------------------------------------------------------------------------

def test_garantir_diretorio_cria_e_e_idempotente(tmp_path: Path) -> None:
    alvo = tmp_path / "a" / "b" / "c"
    assert garantir_diretorio(alvo).is_dir()
    assert garantir_diretorio(alvo).is_dir()


def test_cronometro_mede_tempo_nao_negativo() -> None:
    with Cronometro() as cronometro:
        sum(range(1000))
    assert cronometro.ms >= 0.0
