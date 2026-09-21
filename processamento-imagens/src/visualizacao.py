"""Geração das imagens intermediárias de diagnóstico.

Separado do pipeline de propósito: desenhar é apresentação, medir é processamento.
**Nada aqui influencia número algum** — as cores e anotações existem para quem olha, e
o resultado numérico é idêntico com ou sem elas.

Legenda fixa das visualizações:

=========  ==========================  ============
Cor        Elemento                    BGR
=========  ==========================  ============
Verde      Contorno principal          (0, 255, 0)
Magenta    Convex hull                 (255, 0, 255)
Azul       Bounding box alinhada       (255, 0, 0)
Amarelo    Bounding box rotacionada    (0, 255, 255)
Vermelho   Centroide                   (0, 0, 255)
Ciano      Eixo principal              (255, 255, 0)
=========  ==========================  ============

Nota: a caixa rotacionada de área mínima pode ultrapassar a borda da imagem quando a
folha é grande no quadro. O desenho mostra só a parte visível; o cálculo não muda.
"""

from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

from .contours import ResultadoContorno
from .preprocessing import para_cinza, para_hsv
from .utils import garantir_diretorio

#: Cores da legenda, em BGR.
CORES = {
    "contorno": (0, 255, 0),
    "hull": (255, 0, 255),
    "bbox": (255, 0, 0),
    "bbox_rotacionada": (0, 255, 255),
    "centroide": (0, 0, 255),
    "eixo": (255, 255, 0),
}

#: Ordem e nomes dos arquivos gerados.
ETAPAS = (
    "00-original",
    "01-cinza",
    "02-hsv-matiz",
    "03-suavizada",
    "04-mascara",
    "05-mascara-limpa",
    "06-contorno",
    "07-final",
)


def segmento_visivel(
    inicio: tuple[float, float],
    fim: tuple[float, float],
    largura: int,
    altura: int,
) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """Recorta um segmento aos limites da imagem, **só para desenhar**.

    A caixa rotacionada de área mínima de uma folha grande tem, legitimamente, cantos
    fora do quadro — o retângulo girado que envolve um objeto quase do tamanho da imagem
    precisa ultrapassá-la (medido na Fase 9: ``2497`` excede 77 px, ``1101`` 50 px).

    Mover os vértices para dentro (``clip`` dos pontos) **deformaria** o retângulo e
    desenharia uma caixa que não existe. Recortar cada **segmento** mantém exatamente a
    parte visível da caixa verdadeira, com coordenadas sempre válidas.

    Returns:
        Os extremos inteiros do trecho visível, dentro de ``[0, largura-1] x [0, altura-1]``,
        ou ``None`` se o segmento estiver inteiramente fora da imagem.
    """
    p1 = (int(round(inicio[0])), int(round(inicio[1])))
    p2 = (int(round(fim[0])), int(round(fim[1])))
    visivel, a, b = cv2.clipLine((0, 0, largura, altura), p1, p2)
    if not visivel:
        return None
    return (int(a[0]), int(a[1])), (int(b[0]), int(b[1]))


def _desenhar_segmento(imagem: np.ndarray, inicio, fim, cor, espessura: int) -> None:
    altura, largura = imagem.shape[:2]
    trecho = segmento_visivel(inicio, fim, largura, altura)
    if trecho is not None:
        cv2.line(imagem, trecho[0], trecho[1], cor, espessura)


def anotar_resultado(
    imagem_bgr: np.ndarray,
    contorno: ResultadoContorno,
    texto: list[str] | None = None,
) -> np.ndarray:
    """Desenha a geometria completa sobre a imagem.

    Args:
        imagem_bgr: Imagem processada.
        contorno: Geometria da Fase 6.
        texto: Linhas a escrever no canto superior esquerdo.

    Returns:
        Uma **cópia** anotada. A imagem original não é modificada.
    """
    saida = imagem_bgr.copy()

    cv2.drawContours(saida, [contorno.contorno], -1, CORES["contorno"], 3)
    cv2.polylines(saida, [contorno.hull], True, CORES["hull"], 2)

    caixa = contorno.bbox
    cv2.rectangle(
        saida,
        (caixa["x"], caixa["y"]),
        (caixa["x"] + caixa["largura"], caixa["y"] + caixa["altura"]),
        CORES["bbox"], 2,
    )

    rot = contorno.bbox_rotacionada
    pontos = cv2.boxPoints((
        (float(rot["centro_x"]), float(rot["centro_y"])),      # type: ignore[arg-type]
        (float(rot["largura_bruta"]), float(rot["altura_bruta"])),  # type: ignore[arg-type]
        float(rot["angulo_bruto"]),                             # type: ignore[arg-type]
    ))
    # Segmento a segmento, recortado ao quadro: a caixa pode exceder a imagem.
    for indice in range(4):
        _desenhar_segmento(
            saida, tuple(pontos[indice]), tuple(pontos[(indice + 1) % 4]),
            CORES["bbox_rotacionada"], 2,
        )

    centro_x = int(contorno.centroide["x"])
    centro_y = int(contorno.centroide["y"])
    cv2.circle(saida, (centro_x, centro_y), 8, CORES["centroide"], -1)

    if contorno.orientacao_confiavel and contorno.orientacao_graus is not None:
        metade = float(rot["lado_maior"]) / 2.0  # type: ignore[arg-type]
        angulo = math.radians(contorno.orientacao_graus)
        _desenhar_segmento(
            saida,
            (centro_x - metade * math.cos(angulo), centro_y + metade * math.sin(angulo)),
            (centro_x + metade * math.cos(angulo), centro_y - metade * math.sin(angulo)),
            CORES["eixo"], 3,
        )

    for indice, linha in enumerate(texto or []):
        posicao = (14, 38 + indice * 34)
        cv2.putText(saida, linha, posicao, cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 5)
        cv2.putText(saida, linha, posicao, cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)

    return saida


def gravar_etapas(
    destino: str | Path,
    redimensionada: np.ndarray,
    suavizada: np.ndarray,
    mascara_bruta: np.ndarray,
    mascara_limpa: np.ndarray,
    contorno: ResultadoContorno,
    texto: list[str] | None = None,
) -> dict[str, str]:
    """Grava as oito imagens intermediárias.

    Args:
        destino: Diretório de saída, criado se não existir.
        redimensionada: Imagem após redimensionamento.
        suavizada: Após o filtro Gaussiano.
        mascara_bruta: Máscara da segmentação, antes da limpeza.
        mascara_limpa: Máscara após a limpeza morfológica.
        contorno: Geometria da Fase 6.
        texto: Linhas a escrever na imagem final.

    Returns:
        ``{nome_da_etapa: nome_do_arquivo}``. **Somente nomes de arquivo** — nunca
        caminhos absolutos, que vazariam a estrutura de diretórios da máquina.
    """
    pasta = garantir_diretorio(destino)

    cinza = para_cinza(redimensionada)
    matiz = para_hsv(redimensionada)[:, :, 0]

    imagens = {
        "00-original": redimensionada,
        "01-cinza": cinza,
        "02-hsv-matiz": matiz,
        "03-suavizada": suavizada,
        "04-mascara": mascara_bruta,
        "05-mascara-limpa": mascara_limpa,
        "06-contorno": cv2.drawContours(redimensionada.copy(), [contorno.contorno], -1, CORES["contorno"], 3),
        "07-final": anotar_resultado(redimensionada, contorno, texto),
    }

    gravados: dict[str, str] = {}
    for etapa in ETAPAS:
        nome = f"{etapa}.png"
        cv2.imwrite(str(pasta / nome), imagens[etapa])
        gravados[etapa] = nome

    return gravados
