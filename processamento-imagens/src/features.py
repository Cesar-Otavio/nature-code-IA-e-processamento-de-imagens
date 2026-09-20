"""Extração das características morfológicas, geométricas e de cor da folha.

Entrada: imagem processada, máscara limpa e o ``ResultadoContorno`` da Fase 6.
Saída: :class:`CaracteristicasFolha`, com os números organizados em blocos.

Duas advertências herdadas de medições anteriores atravessam este módulo:

**R14 — o perímetro digital é enviesado.** A borda em escada é mais longa que a curva
que ela aproxima. Medido: **+5% em bordas curvas**, praticamente constante com a escala,
e **negativo** em bordas alinhadas aos eixos. Como o perímetro entra ao quadrado na
circularidade, **um círculo digital perfeito mede ≈ 0,90, não 1,0**.

**R22 — a área poligonal não é a área raster.** O contorno passa pelos centros dos pixels
de borda e descarta cerca de meio pixel ao longo de todo o perímetro. Medido: de −0,25%
numa folha larga a **−4,13% numa acícula** — o viés depende da forma.

Nenhum dos dois é "corrigido" aqui. Corrigir um viés sistemático sem base teórica sólida
trocaria um erro conhecido por um erro desconhecido. Eles são **medidos, documentados e
reportados**, e a Fase 8 decide limiares sabendo disso.

Unidades: área em px², comprimentos em px, ângulos em graus, e características
adimensionais sem sufixo. **Nunca cm ou mm** — não há objeto de referência de tamanho
conhecido nas imagens.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

import cv2
import numpy as np

from .contours import ResultadoContorno
from .segmentation import FAIXA_VERDE_EXPERIMENTAL, OBJETO, validar_mascara
from .utils import ErroImagem

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

#: Circularidade medida para um círculo digital, na Fase 6.
#:
#: **Não é um fator de correção** — nada é multiplicado por ele. É a referência empírica
#: que substitui o 1,0 teórico: convergiu para 0,8973 com raio 320, e a Fase 8 deve usar
#: este valor, e não 1,0, ao pensar em "quão redondo é redondo".
CIRCULARIDADE_DE_CIRCULO_DIGITAL: float = 0.90

#: Área mínima, em px², abaixo da qual a extração é recusada.
#:
#: **Valor experimental.** Abaixo disso o contorno tem poucos pontos e todas as razões
#: adimensionais ficam dominadas pelo ruído de discretização. A menor folha do conjunto
#: de desenvolvimento tem 20.432 px², três ordens de grandeza acima.
AREA_MINIMA_PX2_EXPERIMENTAL: float = 25.0


def _dividir(numerador: float, denominador: float, casas: int = 6) -> float | None:
    """Divisão segura: devolve ``None`` em vez de NaN, infinito ou exceção.

    Nenhuma característica pode sair silenciosamente como NaN ou infinito — no JSON
    isso viraria valor inválido, e ``0`` seria pior ainda, porque parece um número
    legítimo. ``None`` diz o que de fato aconteceu: não foi possível calcular.
    """
    if denominador == 0 or not math.isfinite(numerador) or not math.isfinite(denominador):
        return None
    resultado = numerador / denominador
    if not math.isfinite(resultado):
        return None
    return round(resultado, casas)


# ---------------------------------------------------------------------------
# Blocos
# ---------------------------------------------------------------------------

@dataclass
class Dimensoes:
    """Medidas lineares e de área. **Todas dependem da escala.**

    Attributes:
        area_contorno_px2: Área do polígono do contorno.
        area_mascara_px2: Contagem de pixels do objeto na máscara.
        diferenca_area_px2: ``area_contorno - area_mascara``.
        diferenca_area_pct: A mesma diferença, em porcentagem da área de máscara.
        perimetro_px: Perímetro do contorno fechado.
        largura_px: Largura da caixa envolvente alinhada aos eixos.
        altura_px: Altura da mesma caixa.
        lado_maior_px: Maior lado da caixa de área mínima.
        lado_menor_px: Menor lado da mesma caixa.
    """

    area_contorno_px2: float
    area_mascara_px2: int
    diferenca_area_px2: float
    diferenca_area_pct: float | None
    perimetro_px: float
    largura_px: int
    altura_px: int
    lado_maior_px: float
    lado_menor_px: float


@dataclass
class Forma:
    """Descritores **adimensionais** — os únicos comparáveis entre imagens.

    Attributes:
        aspect_ratio: ``largura / altura`` da caixa reta. **Sensível a rotação.**
        elongacao: ``lado_maior / lado_menor`` da caixa de área mínima. Sempre ``>= 1``
            e **invariante a rotação**.
        circularidade: ``4πA / P²``. Ver :data:`CIRCULARIDADE_DE_CIRCULO_DIGITAL`.
        solidez: ``area_contorno / area_hull``. Em ``(0, 1]``.
        extent: ``area_contorno / area_bbox_reta``. **Sensível a rotação.**
        extent_rotacionado: O mesmo com a caixa de área mínima. Invariante a rotação.
    """

    aspect_ratio: float | None
    elongacao: float | None
    circularidade: float | None
    solidez: float | None
    extent: float | None
    extent_rotacionado: float | None


@dataclass
class Orientacao:
    """Direção do eixo principal e quão confiável ela é."""

    angulo_graus: float | None
    anisotropia: float
    confiavel: bool


@dataclass
class Convexidade:
    """Convex hull e complexidade de borda.

    Attributes:
        area_hull_px2: Área do envelope convexo.
        perimetro_hull_px: Perímetro do envelope.
        pontos_hull: Número de vértices. **Diagnóstico**, não característica.
        razao_perimetro_hull: ``perimetro / perimetro_hull``. **Experimental.**
    """

    area_hull_px2: float
    perimetro_hull_px: float
    pontos_hull: int
    razao_perimetro_hull: float | None


@dataclass
class Cor:
    """Estatísticas de cor, calculadas **apenas dentro da máscara**.

    O fundo branco nunca entra nas médias.

    Attributes:
        media_rgb: ``(R, G, B)`` médios.
        mediana_rgb: ``(R, G, B)`` medianos — robustos a reflexo especular.
        media_hsv: ``(H, S, V)`` médios. **H é circular; ver a limitação abaixo.**
        mediana_hsv: ``(H, S, V)`` medianos.
        proporcao_verde: Fração dos pixels da folha dentro da faixa de verde.
        pixels_analisados: Quantos pixels entraram nas estatísticas.

    Note:
        **Matiz é uma grandeza circular.** A média aritmética de H é válida apenas
        enquanto os valores não cruzam a fronteira 0/179. No Flavia, o matiz das folhas
        está concentrado entre 43 e 67 — bem longe da fronteira —, então a média é
        segura. Numa folha avermelhada, cujo matiz fica próximo de 0, ela deixaria de
        ser. A **mediana** também é reportada, por ser menos sensível a valores
        extremos.
    """

    media_rgb: tuple[float, float, float]
    mediana_rgb: tuple[float, float, float]
    media_hsv: tuple[float, float, float]
    mediana_hsv: tuple[float, float, float]
    proporcao_verde: float | None
    pixels_analisados: int


@dataclass
class Qualidade:
    """Diagnóstico da extração. **Nada aqui descreve a morfologia da folha.**

    Posição na imagem e distância da borda dependem do enquadramento, não da folha —
    por isso ficam separadas das características de forma.
    """

    centroide_x_px: float
    centroide_y_px: float
    centroide_x_norm: float | None
    centroide_y_norm: float | None
    toca_borda: bool
    distancia_minima_borda_px: int
    numero_contornos: int
    dominancia: float
    orientacao_confiavel: bool


@dataclass
class CaracteristicasFolha:
    """Conjunto completo de características de uma folha.

    Os nomes dos campos são **estáveis** e correspondem ao bloco ``caracteristicas``
    do contrato definido na Fase 1 — serializar com :func:`para_dicionario` produz a
    estrutura que a API devolverá.
    """

    dimensoes: Dimensoes
    forma: Forma
    orientacao: Orientacao
    convexidade: Convexidade
    cor: Cor
    qualidade: Qualidade
    avisos: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Cálculos
# ---------------------------------------------------------------------------

def calcular_circularidade(area: float, perimetro: float) -> float | None:
    """Circularidade: :math:`4\\pi A / P^2`.

    Adimensional. Máximo **teórico** 1,0 para o círculo; máximo **prático** ≈ 0,90 em
    imagem digital, pelo viés do perímetro (R14).

    Decresce conforme a forma se alonga **ou** a borda se torna irregular — as duas
    causas não são distinguíveis por este número sozinho. Uma folha lanceolada lisa e
    uma folha oval serrilhada podem ter circularidade parecida por motivos diferentes.

    Args:
        area: Área, em px².
        perimetro: Perímetro, em px.

    Returns:
        A circularidade, ou ``None`` se o perímetro for zero.
    """
    return _dividir(4.0 * math.pi * area, perimetro ** 2)


def calcular_solidez(area: float, area_hull: float) -> float | None:
    """Solidez: :math:`A / A_{hull}`.

    Adimensional, em ``(0, 1]``. Vale 1 para forma convexa e cai conforme a borda se
    torna recortada ou lobada.

    **É o descritor que captura recorte de borda** — nenhuma outra característica do
    conjunto faz isso. No conjunto de desenvolvimento variou de 0,47 (bordo lobado) a
    0,99 (folha oval lisa).
    """
    return _dividir(area, area_hull)


def calcular_extent(area: float, largura: float, altura: float) -> float | None:
    """Extent: :math:`A / (w \\cdot h)`.

    Fração da caixa envolvente efetivamente ocupada. Adimensional, em ``(0, 1]``.

    Valores de referência: retângulo alinhado = 1,0; círculo = :math:`\\pi/4 ≈ 0,785`.

    **Sensível a rotação** quando calculado sobre a caixa reta: uma folha alongada na
    diagonal tem caixa muito maior que ela, e extent baixo — o que descreve o
    enquadramento, não a forma.
    """
    return _dividir(area, largura * altura)


def calcular_aspect_ratio(largura: float, altura: float) -> float | None:
    """Razão :math:`w/h` da caixa reta.

    Adimensional. Pode ser menor ou maior que 1. **Sensível a rotação** — descreve o
    enquadramento tanto quanto a forma. Para a forma, use :func:`calcular_elongacao`.
    """
    return _dividir(largura, altura)


def calcular_elongacao(lado_maior: float, lado_menor: float) -> float | None:
    """Alongamento: :math:`\\text{lado maior} / \\text{lado menor}` da caixa de área mínima.

    Adimensional e **sempre ``>= 1``** por construção, porque a Fase 6 normaliza qual
    lado é o maior. **Invariante a rotação**, ao contrário do aspect ratio.

    É a medida de alongamento mais adequada ao problema: numa acícula diagonal, a caixa
    reta dá 957×664 (razão 1,4) enquanto a rotacionada dá 1159×58 (razão **20**). A
    segunda descreve a folha; a primeira, o ângulo em que ela foi fotografada.
    """
    return _dividir(lado_maior, lado_menor)


def calcular_razao_perimetro_hull(perimetro: float, perimetro_hull: float) -> float | None:
    """Razão :math:`P / P_{hull}`. **Experimental.**

    Hipótese: mede complexidade de borda — quanto o contorno "passeia" em relação ao
    caminho mais curto que envolve o objeto. Vale ≈ 1 para forma convexa e cresce com
    reentrâncias.

    **Não promovida a essencial**: a medição no conjunto de desenvolvimento precisa
    mostrar que ela não é redundante com a solidez, que captura a mesma ideia por
    área em vez de por comprimento.
    """
    return _dividir(perimetro, perimetro_hull)


def extrair_cor(
    imagem_bgr: np.ndarray,
    mascara: np.ndarray,
    faixa_verde: dict[str, tuple[int, int]] | None = None,
) -> Cor:
    """Estatísticas de cor dentro da máscara.

    Args:
        imagem_bgr: Imagem processada, 3 canais em BGR.
        mascara: Máscara binária do objeto.
        faixa_verde: Faixa usada na proporção de verde. ``None`` usa a da Fase 4.

    Returns:
        O bloco de cor preenchido.

    Raises:
        ErroImagem: ``E004`` se a imagem não tiver 3 canais ou a forma não bater com a
            máscara.
    """
    validar_mascara(mascara)
    if imagem_bgr is None or not isinstance(imagem_bgr, np.ndarray):
        raise ErroImagem("E004", "A imagem precisa ser uma matriz NumPy.")
    if imagem_bgr.ndim != 3 or imagem_bgr.shape[2] != 3:
        raise ErroImagem("E004", "As estatísticas de cor exigem imagem de 3 canais.")
    if imagem_bgr.shape[:2] != mascara.shape:
        raise ErroImagem("E004", "Imagem e máscara têm formas diferentes.")

    dentro = mascara == OBJETO
    quantidade = int(np.count_nonzero(dentro))

    if quantidade == 0:
        zero = (0.0, 0.0, 0.0)
        return Cor(zero, zero, zero, zero, None, 0)

    bgr = imagem_bgr[dentro]
    hsv = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2HSV)[dentro]

    media_bgr = bgr.mean(axis=0)
    mediana_bgr = np.median(bgr, axis=0)
    media_hsv = hsv.mean(axis=0)
    mediana_hsv = np.median(hsv, axis=0)

    limites = faixa_verde if faixa_verde is not None else FAIXA_VERDE_EXPERIMENTAL
    h, s, v = hsv[:, 0], hsv[:, 1], hsv[:, 2]
    verdes = int(np.count_nonzero(
        (h >= limites["h"][0]) & (h <= limites["h"][1])
        & (s >= limites["s"][0]) & (s <= limites["s"][1])
        & (v >= limites["v"][0]) & (v <= limites["v"][1])
    ))

    def arredondar(valores: np.ndarray, inverter: bool) -> tuple[float, float, float]:
        ordem = valores[::-1] if inverter else valores  # BGR -> RGB
        return (round(float(ordem[0]), 2), round(float(ordem[1]), 2), round(float(ordem[2]), 2))

    return Cor(
        media_rgb=arredondar(media_bgr, inverter=True),
        mediana_rgb=arredondar(mediana_bgr, inverter=True),
        media_hsv=arredondar(media_hsv, inverter=False),
        mediana_hsv=arredondar(mediana_hsv, inverter=False),
        proporcao_verde=_dividir(verdes, quantidade),
        pixels_analisados=quantidade,
    )


# ---------------------------------------------------------------------------
# Orquestração
# ---------------------------------------------------------------------------

def extrair_caracteristicas(
    imagem_bgr: np.ndarray,
    mascara: np.ndarray,
    contorno: ResultadoContorno,
    area_minima: float = AREA_MINIMA_PX2_EXPERIMENTAL,
) -> CaracteristicasFolha:
    """Extrai todas as características a partir da geometria da Fase 6.

    **Decisão metodológica: as características adimensionais usam a área do contorno**,
    não a de máscara. A razão é consistência matemática — perímetro, hull e caixas vêm
    todos do contorno, e misturar área raster com perímetro poligonal somaria dois
    vieses diferentes na mesma fração. As duas áreas são reportadas, e a diferença
    entre elas também.

    Args:
        imagem_bgr: Imagem processada, 3 canais.
        mascara: Máscara limpa.
        contorno: Resultado da Fase 6.
        area_minima: Área abaixo da qual a extração é recusada.

    Returns:
        O conjunto completo de características.

    Raises:
        ErroImagem: ``E004`` entrada inválida; ``E011`` objeto pequeno demais para que
            as razões adimensionais tenham significado.
    """
    validar_mascara(mascara)

    area = float(contorno.area_px2)
    if area < area_minima:
        raise ErroImagem(
            "E011",
            f"Objeto pequeno demais para medir: {area:.1f} px², mínimo {area_minima:.0f} px².",
        )

    bbox = contorno.bbox
    rot = contorno.bbox_rotacionada
    largura, altura = int(bbox["largura"]), int(bbox["altura"])
    lado_maior = float(rot["lado_maior"])  # type: ignore[arg-type]
    lado_menor = float(rot["lado_menor"])  # type: ignore[arg-type]

    diferenca = area - contorno.area_mascara_px
    altura_img, largura_img = mascara.shape

    dimensoes = Dimensoes(
        area_contorno_px2=round(area, 4),
        area_mascara_px2=int(contorno.area_mascara_px),
        diferenca_area_px2=round(diferenca, 4),
        diferenca_area_pct=_dividir(diferenca * 100.0, contorno.area_mascara_px, casas=4),
        perimetro_px=round(float(contorno.perimetro_px), 4),
        largura_px=largura,
        altura_px=altura,
        lado_maior_px=round(lado_maior, 4),
        lado_menor_px=round(lado_menor, 4),
    )

    forma = Forma(
        aspect_ratio=calcular_aspect_ratio(largura, altura),
        elongacao=calcular_elongacao(lado_maior, lado_menor),
        circularidade=calcular_circularidade(area, float(contorno.perimetro_px)),
        solidez=calcular_solidez(area, float(contorno.area_hull_px2)),
        extent=calcular_extent(area, largura, altura),
        extent_rotacionado=calcular_extent(area, lado_maior, lado_menor),
    )

    convexidade = Convexidade(
        area_hull_px2=round(float(contorno.area_hull_px2), 4),
        perimetro_hull_px=round(float(contorno.perimetro_hull_px), 4),
        pontos_hull=int(contorno.pontos_hull),
        razao_perimetro_hull=calcular_razao_perimetro_hull(
            float(contorno.perimetro_px), float(contorno.perimetro_hull_px)
        ),
    )

    qualidade = Qualidade(
        centroide_x_px=float(contorno.centroide["x"]),
        centroide_y_px=float(contorno.centroide["y"]),
        centroide_x_norm=_dividir(float(contorno.centroide["x"]), largura_img),
        centroide_y_norm=_dividir(float(contorno.centroide["y"]), altura_img),
        toca_borda=bool(contorno.toca_borda["qualquer"]),
        distancia_minima_borda_px=int(contorno.distancia_minima_borda_px),
        numero_contornos=int(contorno.numero_contornos),
        dominancia=float(contorno.dominancia),
        orientacao_confiavel=bool(contorno.orientacao_confiavel),
    )

    avisos = list(contorno.avisos)
    if forma.solidez is not None and forma.solidez < 0.7:
        avisos.append("solidez_baixa_borda_muito_recortada")
    if forma.elongacao is not None and forma.elongacao > 10:
        avisos.append("objeto_muito_alongado")

    return CaracteristicasFolha(
        dimensoes=dimensoes,
        forma=forma,
        orientacao=Orientacao(
            angulo_graus=contorno.orientacao_graus,
            anisotropia=float(contorno.anisotropia),
            confiavel=bool(contorno.orientacao_confiavel),
        ),
        convexidade=convexidade,
        cor=extrair_cor(imagem_bgr, mascara),
        qualidade=qualidade,
        avisos=avisos,
    )


def para_dicionario(caracteristicas: CaracteristicasFolha) -> dict[str, object]:
    """Serializa para o formato do contrato da Fase 1.

    Garante que nenhum valor seja NaN ou infinito — esses viram ``None``, que no JSON
    é ``null``.
    """
    def limpar(valor: object) -> object:
        if isinstance(valor, float) and not math.isfinite(valor):
            return None
        if isinstance(valor, dict):
            return {chave: limpar(item) for chave, item in valor.items()}
        if isinstance(valor, (list, tuple)):
            return [limpar(item) for item in valor]
        return valor

    return limpar(asdict(caracteristicas))  # type: ignore[return-value]
