"""Validação de entrada, leitura de imagem e utilidades de apoio.

Responsabilidade única: transformar um caminho de arquivo em uma matriz de imagem
confiável — ou falhar com um erro nomeado, nunca com uma exceção crua vinda da
biblioteca.

Os códigos de erro seguem o contrato da Fase 1
(``docs/processamento-imagens/01-DEFINICAO-PROBLEMA.md`` §11).

Convenção de cor: o OpenCV lê imagens em **BGR**, não em RGB. Toda função deste
pacote que recebe ou devolve imagem colorida trabalha em BGR, salvo quando o nome
disser o contrário (ver ``preprocessing.para_rgb``).
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

#: Extensões aceitas. A extensão é o primeiro filtro, nunca o último: o arquivo só
#: é aceito se também **decodificar** como imagem (ver ``ler_imagem``).
EXTENSOES_SUPORTADAS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".bmp"})

#: Menor lado aceitável, em pixels.
#:
#: **Valor experimental, não decisão final.** Escolhido como piso de sanidade: abaixo
#: disso não há contorno com pixels suficientes para que perímetro e circularidade
#: signifiquem algo. O valor definitivo sai da Fase 4, medindo a degradação dos
#: descritores em imagens progressivamente reduzidas.
LADO_MINIMO_PX_EXPERIMENTAL: int = 64


class ErroImagem(Exception):
    """Erro de domínio do módulo, com código estável.

    Existe para que a camada que chama receba um código tratável em vez de uma
    exceção da biblioteca. A mensagem é destinada a uma pessoa e **nunca** contém
    rastreamento técnico.

    Attributes:
        codigo: Código do contrato da Fase 1 (``E001``..``E007``).
        mensagem: Texto em português, acionável.
    """

    def __init__(self, codigo: str, mensagem: str) -> None:
        super().__init__(f"[{codigo}] {mensagem}")
        self.codigo = codigo
        self.mensagem = mensagem


def validar_caminho(caminho: str | Path) -> Path:
    """Confere que o caminho aponta para um arquivo existente e legível.

    Args:
        caminho: Caminho do arquivo de imagem.

    Returns:
        O caminho resolvido.

    Raises:
        ErroImagem: ``E001`` se não existir, não for arquivo ou não for legível.
    """
    alvo = Path(caminho)

    if not alvo.exists():
        raise ErroImagem("E001", f"Arquivo não encontrado: {alvo}")
    if not alvo.is_file():
        raise ErroImagem("E001", f"O caminho não é um arquivo: {alvo}")
    if not os.access(alvo, os.R_OK):
        raise ErroImagem("E001", f"Sem permissão de leitura: {alvo}")

    return alvo


def validar_extensao(caminho: str | Path) -> str:
    """Confere que a extensão está entre as suportadas.

    Primeiro filtro apenas: uma extensão correta não garante que o conteúdo seja
    uma imagem. Quem decide isso é ``ler_imagem``.

    Args:
        caminho: Caminho do arquivo.

    Returns:
        A extensão em minúsculas, com ponto (ex.: ``".jpg"``).

    Raises:
        ErroImagem: ``E002`` se a extensão não for suportada.
    """
    extensao = Path(caminho).suffix.lower()

    if extensao not in EXTENSOES_SUPORTADAS:
        aceitas = ", ".join(sorted(e.lstrip(".").upper() for e in EXTENSOES_SUPORTADAS))
        raise ErroImagem(
            "E002",
            f"Formato não suportado: '{extensao or "sem extensão"}'. Aceitos: {aceitas}.",
        )

    return extensao


def validar_dimensoes(imagem: np.ndarray, lado_minimo: int = LADO_MINIMO_PX_EXPERIMENTAL) -> tuple[int, int]:
    """Confere que a matriz tem dimensões utilizáveis.

    Args:
        imagem: Matriz da imagem.
        lado_minimo: Menor lado aceitável, em pixels.

    Returns:
        ``(largura, altura)`` em pixels.

    Raises:
        ErroImagem: ``E004`` se a matriz for vazia ou tiver dimensão nula;
            ``E005`` se algum lado for menor que ``lado_minimo``.
    """
    if imagem is None or imagem.size == 0:
        raise ErroImagem("E004", "A imagem está vazia.")
    if imagem.ndim not in (2, 3):
        raise ErroImagem("E004", f"Matriz com {imagem.ndim} dimensões não é uma imagem.")

    altura, largura = imagem.shape[:2]

    if altura == 0 or largura == 0:
        raise ErroImagem("E004", "A imagem está vazia.")
    if min(altura, largura) < lado_minimo:
        raise ErroImagem(
            "E005",
            f"Resolução muito baixa: {largura}x{altura}. "
            f"O menor lado precisa ter ao menos {lado_minimo} px.",
        )

    return largura, altura


def ler_imagem(
    caminho: str | Path,
    lado_minimo: int = LADO_MINIMO_PX_EXPERIMENTAL,
) -> tuple[np.ndarray, dict[str, object]]:
    """Lê uma imagem do disco, validando caminho, extensão, conteúdo e dimensões.

    Ponto de entrada único de leitura do módulo. A imagem devolvida está em **BGR**,
    que é a ordem de canais nativa do OpenCV.

    Args:
        caminho: Caminho do arquivo de imagem.
        lado_minimo: Menor lado aceitável, em pixels.

    Returns:
        Uma tupla ``(imagem, metadados)``. Os metadados trazem ``arquivo``,
        ``formato``, ``largura_original_px``, ``altura_original_px``, ``canais`` e
        ``bytes``.

    Raises:
        ErroImagem: ``E001`` caminho inválido; ``E002`` extensão não suportada;
            ``E003`` conteúdo não decodifica como imagem; ``E004`` imagem vazia;
            ``E005`` resolução abaixo do mínimo.
    """
    alvo = validar_caminho(caminho)
    extensao = validar_extensao(alvo)

    # imdecode em vez de imread: imread devolve None tanto para arquivo ausente
    # quanto para conteúdo inválido, e não lida com caminhos não-ASCII no Windows.
    try:
        bruto = np.fromfile(str(alvo), dtype=np.uint8)
    except OSError as erro:
        raise ErroImagem("E001", f"Não foi possível ler o arquivo: {alvo}") from erro

    if bruto.size == 0:
        raise ErroImagem("E004", "O arquivo está vazio.")

    imagem = cv2.imdecode(bruto, cv2.IMREAD_COLOR)

    if imagem is None:
        raise ErroImagem(
            "E003",
            "O arquivo não pôde ser lido como imagem. Pode estar corrompido "
            "ou não ser realmente uma imagem.",
        )

    largura, altura = validar_dimensoes(imagem, lado_minimo)

    metadados: dict[str, object] = {
        "arquivo": alvo.name,
        "formato": extensao.lstrip(".").upper(),
        "largura_original_px": largura,
        "altura_original_px": altura,
        "canais": imagem.shape[2] if imagem.ndim == 3 else 1,
        "bytes": int(bruto.size),
    }

    return imagem, metadados


def nome_seguro(nome: str) -> str:
    """Reduz um nome de arquivo a caracteres seguros para o sistema de arquivos.

    Usado para que um nome vindo de fora nunca determine o caminho de gravação.
    Remove diretórios, troca o que não for alfanumérico por ``_`` e evita nome vazio.

    Args:
        nome: Nome de arquivo recebido.

    Returns:
        Nome saneado, sempre não vazio.
    """
    base = Path(str(nome).replace("\\", "/")).name
    limpo = re.sub(r"[^A-Za-z0-9._-]", "_", base).lstrip(".")
    limpo = re.sub(r"_{2,}", "_", limpo)
    return limpo or "arquivo"


def garantir_diretorio(caminho: str | Path) -> Path:
    """Cria o diretório se ainda não existir.

    Args:
        caminho: Caminho do diretório.

    Returns:
        O caminho criado ou já existente.
    """
    destino = Path(caminho)
    destino.mkdir(parents=True, exist_ok=True)
    return destino


class Cronometro:
    """Mede o tempo de uma etapa, em milissegundos.

    Usa ``perf_counter``, que é monotônico. Serve para registrar ordem de grandeza,
    não para medição de precisão.

    Example:
        >>> with Cronometro() as c:
        ...     pass
        >>> c.ms >= 0.0
        True
    """

    def __init__(self) -> None:
        self.ms: float = 0.0
        self._inicio: float = 0.0

    def __enter__(self) -> "Cronometro":
        self._inicio = time.perf_counter()
        return self

    def __exit__(self, *_excecao: object) -> None:
        self.ms = (time.perf_counter() - self._inicio) * 1000.0
