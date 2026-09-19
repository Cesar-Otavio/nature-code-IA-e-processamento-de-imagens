"""Fixtures compartilhadas: imagens sintéticas e arquivos temporários.

As imagens são geradas por NumPy e OpenCV, não lidas do disco. Isso permite testar
as operações contra formas de propriedades **conhecidas analiticamente**, sem
depender do dataset — a mesma estratégia que as suítes da etapa de IA usam ao
executar o código real num DOM dublado.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

#: Semente fixa: os testes precisam ser determinísticos, inclusive os que usam ruído.
SEMENTE = 20260919


@pytest.fixture
def imagem_preta() -> np.ndarray:
    """Imagem BGR 200x300 inteiramente preta."""
    return np.zeros((200, 300, 3), dtype=np.uint8)


@pytest.fixture
def imagem_branca() -> np.ndarray:
    """Imagem BGR 200x300 inteiramente branca."""
    return np.full((200, 300, 3), 255, dtype=np.uint8)


@pytest.fixture
def imagem_gradiente() -> np.ndarray:
    """Imagem BGR 200x300 com gradiente horizontal de 0 a 255."""
    linha = np.linspace(0, 255, 300, dtype=np.uint8)
    canal = np.tile(linha, (200, 1))
    return cv2.merge([canal, canal, canal])


@pytest.fixture
def imagem_circulo() -> np.ndarray:
    """Círculo branco de raio 60 no centro de um fundo preto 400x400 (BGR)."""
    tela = np.zeros((400, 400, 3), dtype=np.uint8)
    cv2.circle(tela, (200, 200), 60, (255, 255, 255), thickness=-1)
    return tela


@pytest.fixture
def imagem_retangulo() -> np.ndarray:
    """Retângulo branco 120x60 sobre fundo preto 400x400 (BGR)."""
    tela = np.zeros((400, 400, 3), dtype=np.uint8)
    cv2.rectangle(tela, (100, 150), (220, 210), (255, 255, 255), thickness=-1)
    return tela


@pytest.fixture
def imagem_folha_sintetica() -> np.ndarray:
    """Elipse verde sobre fundo branco — imita a condição do Flavia.

    Serve para exercitar o caminho completo de pré-processamento com uma imagem
    que tem a mesma estrutura do dataset (objeto colorido sobre fundo claro), sem
    depender do download.
    """
    tela = np.full((400, 600, 3), 255, dtype=np.uint8)
    cv2.ellipse(tela, (300, 200), (180, 70), 25, 0, 360, (40, 140, 60), thickness=-1)
    return tela


@pytest.fixture
def imagem_sal_e_pimenta() -> np.ndarray:
    """Imagem cinza uniforme com 5% de pixels em ruído impulsivo.

    Usa semente fixa: o teste precisa ser reproduzível.
    """
    gerador = np.random.default_rng(SEMENTE)
    tela = np.full((200, 300, 3), 128, dtype=np.uint8)
    mascara = gerador.random((200, 300))
    tela[mascara < 0.025] = 0
    tela[mascara > 0.975] = 255
    return tela


@pytest.fixture
def arquivo_png_valido(tmp_path: Path, imagem_folha_sintetica: np.ndarray) -> Path:
    """Grava a folha sintética como PNG num diretório temporário."""
    destino = tmp_path / "folha.png"
    cv2.imwrite(str(destino), imagem_folha_sintetica)
    return destino


@pytest.fixture
def arquivo_jpg_valido(tmp_path: Path, imagem_folha_sintetica: np.ndarray) -> Path:
    """Grava a folha sintética como JPEG num diretório temporário."""
    destino = tmp_path / "folha.jpg"
    cv2.imwrite(str(destino), imagem_folha_sintetica)
    return destino


@pytest.fixture
def arquivo_jpg_falso(tmp_path: Path) -> Path:
    """Arquivo com extensão .jpg mas conteúdo de texto.

    É o caso que prova que validar a extensão não basta.
    """
    destino = tmp_path / "impostor.jpg"
    destino.write_text("isto nao e uma imagem, e apenas texto\n", encoding="utf-8")
    return destino


@pytest.fixture
def arquivo_vazio(tmp_path: Path) -> Path:
    """Arquivo .png com zero bytes."""
    destino = tmp_path / "vazio.png"
    destino.write_bytes(b"")
    return destino


@pytest.fixture
def arquivo_extensao_invalida(tmp_path: Path) -> Path:
    """Arquivo de texto com extensão não suportada."""
    destino = tmp_path / "documento.txt"
    destino.write_text("texto", encoding="utf-8")
    return destino


@pytest.fixture
def imagem_minuscula(tmp_path: Path) -> Path:
    """Imagem PNG 20x20 — abaixo do lado mínimo."""
    destino = tmp_path / "minuscula.png"
    cv2.imwrite(str(destino), np.full((20, 20, 3), 128, dtype=np.uint8))
    return destino
