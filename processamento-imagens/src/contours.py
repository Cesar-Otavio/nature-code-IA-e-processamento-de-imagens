"""Detecção de contornos, seleção do objeto principal e geometria básica.

Entrada: máscara limpa da Fase 5. Saída: a representação geométrica da folha —
contorno, área, perímetro, caixas envolventes, centroide, orientação e convex hull.

> **O contorno é uma representação digital aproximada da borda real.** Ele passa pelos
> centros dos pixels de borda, numa grade discreta. Área e perímetro medidos aqui estão
> sujeitos à discretização espacial, com viés **sistemático e mensurável** — não
> aleatório. Ver ``docs/processamento-imagens/06-CONTORNOS.md`` §16.

Esta fase **não calcula características derivadas** — circularidade, solidez, extent e
aspect ratio são da Fase 7. Aqui só se produzem as grandezas primárias de que elas
precisam.

Unidades: área em px², perímetro e posições em px, ângulos em graus. Nunca cm ou mm —
não há objeto de referência de tamanho conhecido nas imagens.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import cv2
import numpy as np

from .segmentation import OBJETO, validar_mascara
from .utils import ErroImagem

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

#: Modo de recuperação de contornos.
#:
#: **RETR_EXTERNAL**, escolhido por medição: no conjunto de desenvolvimento,
#: ``RETR_TREE`` devolveu exatamente os mesmos contornos em **64/64** imagens, sem
#: nenhuma hierarquia interna. A razão é a Fase 5 — o preenchimento de buracos
#: eliminou as 167 cavidades que existiam. Usar TREE seria pagar por hierarquia
#: inexistente.
MODO_RECUPERACAO: int = cv2.RETR_EXTERNAL

#: Método de aproximação do contorno.
#:
#: **CHAIN_APPROX_SIMPLE**, escolhido por medição: reduz os pontos em **46,1%**
#: (mediana de 2.108 para 1.136) com diferença **nula** em área e da ordem de 1e-6 em
#: perímetro — ruído de ponto flutuante. Metade da memória, zero perda geométrica.
METODO_APROXIMACAO: int = cv2.CHAIN_APPROX_SIMPLE

#: Razão área-do-segundo / área-do-maior acima da qual a escolha do objeto principal
#: é considerada **ambígua**.
#:
#: **Valor experimental.** No conjunto de desenvolvimento a maior razão observada foi
#: 3,55×10⁻⁴ — quatro ordens de grandeza abaixo deste limiar. Ele existe para o caso
#: de duas folhas na mesma imagem, que o Flavia não contém: é um aviso para entrada
#: fora do domínio testado, não um critério calibrado sobre casos reais.
RAZAO_AMBIGUIDADE_EXPERIMENTAL: float = 0.5

#: Anisotropia abaixo da qual a orientação é considerada não confiável.
#:
#: **Valor experimental.** Um objeto com eixos principais de comprimento semelhante
#: não tem direção dominante, e o ângulo calculado passa a ser ruído. Ver
#: :func:`calcular_orientacao`.
ANISOTROPIA_MINIMA_EXPERIMENTAL: float = 0.05


@dataclass
class ResultadoContorno:
    """Representação geométrica do objeto principal.

    Todas as grandezas em pixels; ângulos em graus.

    Attributes:
        contorno: Pontos do contorno selecionado, no formato do OpenCV.
        area_px2: Área poligonal, por ``cv2.contourArea``.
        area_mascara_px: Contagem de pixels da máscara — **não é igual** à poligonal.
        perimetro_px: Perímetro do contorno fechado.
        bbox: Caixa envolvente alinhada aos eixos.
        bbox_rotacionada: Caixa de área mínima, com ângulo normalizado.
        centroide: Centro de massa, pelos momentos.
        orientacao_graus: Ângulo do eixo principal, ou ``None`` se não confiável.
        anisotropia: Quanto o objeto é alongado, em ``[0, 1]``.
        orientacao_confiavel: Se a orientação tem significado.
        hull: Pontos do convex hull.
        area_hull_px2: Área do hull.
        perimetro_hull_px: Perímetro do hull.
        pontos_hull: Número de vértices do hull.
        toca_borda: Detalhamento por lado e agregado.
        distancia_minima_borda_px: Menor distância do contorno às bordas do quadro.
        numero_contornos: Quantos contornos a máscara continha.
        dominancia: Área do principal / área total de todos os contornos.
        avisos: Códigos de situação suspeita.
    """

    contorno: np.ndarray
    area_px2: float
    area_mascara_px: int
    perimetro_px: float
    bbox: dict[str, int]
    bbox_rotacionada: dict[str, object]
    centroide: dict[str, float]
    orientacao_graus: float | None
    anisotropia: float
    orientacao_confiavel: bool
    hull: np.ndarray
    area_hull_px2: float
    perimetro_hull_px: float
    pontos_hull: int
    toca_borda: dict[str, bool]
    distancia_minima_borda_px: int
    numero_contornos: int
    dominancia: float
    avisos: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Detecção e seleção
# ---------------------------------------------------------------------------

def detectar_contornos(mascara: np.ndarray) -> list[np.ndarray]:
    """Extrai os contornos externos da máscara.

    Args:
        mascara: Máscara binária válida.

    Returns:
        Lista de contornos, possivelmente vazia.

    Raises:
        ErroImagem: ``E009`` se a máscara for inválida.
    """
    validar_mascara(mascara)
    contornos, _hierarquia = cv2.findContours(mascara, MODO_RECUPERACAO, METODO_APROXIMACAO)
    return list(contornos)


def selecionar_contorno_principal(
    contornos: list[np.ndarray],
    razao_ambiguidade: float = RAZAO_AMBIGUIDADE_EXPERIMENTAL,
) -> tuple[np.ndarray, dict[str, object]]:
    """Escolhe o contorno que representa a folha.

    **Critério: maior área poligonal.** A hipótese de que "o maior contorno é a folha"
    foi testada, e não presumida: vale em 64/64 imagens do conjunto de desenvolvimento
    — mas isso é evidência **sobre este dataset**, não verdade universal. O Flavia tem
    uma folha isolada por imagem; uma foto com duas folhas quebraria o critério.

    Critérios alternativos — proximidade do centro, não tocar a borda — foram
    considerados e **não adotados**: acrescentariam parâmetros sem resolver nenhum caso
    observado, e proximidade do centro puniria folhas legitimamente deslocadas.

    Quando o segundo maior contorno tem área comparável ao primeiro, a escolha **não é
    feita em silêncio**: o aviso ``selecao_ambigua`` é emitido.

    Args:
        contornos: Contornos detectados.
        razao_ambiguidade: Razão segundo/primeiro acima da qual avisar.

    Returns:
        ``(contorno, diagnostico)``. O diagnóstico traz ``indice``, ``area``,
        ``numero_contornos``, ``dominancia``, ``razao_segundo_primeiro``,
        ``areas_ordenadas`` e ``avisos``.

    Raises:
        ErroImagem: ``E007`` se não houver contorno; ``E008`` se a razão for inválida.
    """
    if isinstance(razao_ambiguidade, bool) or not isinstance(razao_ambiguidade, (int, float)):
        raise ErroImagem("E008", "razao_ambiguidade precisa ser numérica.")
    if not 0 < razao_ambiguidade <= 1:
        raise ErroImagem("E008", f"razao_ambiguidade precisa estar em (0, 1]; veio {razao_ambiguidade}.")

    if not contornos:
        raise ErroImagem(
            "E007",
            "Nenhuma folha foi detectada. Verifique o contraste com o fundo.",
        )

    areas = [float(cv2.contourArea(c)) for c in contornos]
    indice = int(np.argmax(areas))
    area_principal = areas[indice]

    if area_principal <= 0:
        raise ErroImagem("E007", "Nenhum contorno com área utilizável foi encontrado.")

    area_total = float(sum(areas))
    ordenadas = sorted(areas, reverse=True)
    razao = (ordenadas[1] / ordenadas[0]) if len(ordenadas) > 1 and ordenadas[0] > 0 else 0.0

    avisos: list[str] = []
    if razao > razao_ambiguidade:
        avisos.append("selecao_ambigua")
    if len(contornos) > 1:
        avisos.append("multiplos_contornos")

    diagnostico: dict[str, object] = {
        "indice": indice,
        "area": area_principal,
        "numero_contornos": len(contornos),
        "dominancia": round(area_principal / area_total, 6) if area_total else 1.0,
        "razao_segundo_primeiro": round(razao, 6),
        "areas_ordenadas": [round(a, 2) for a in ordenadas],
        "avisos": avisos,
    }

    return contornos[indice], diagnostico


# ---------------------------------------------------------------------------
# Geometria
# ---------------------------------------------------------------------------

def calcular_centroide(contorno: np.ndarray) -> dict[str, float]:
    """Centro de massa, pelos momentos de imagem.

    .. math:: c_x = M_{10}/M_{00}, \\qquad c_y = M_{01}/M_{00}

    Args:
        contorno: Contorno do objeto.

    Returns:
        ``{"x": ..., "y": ...}`` em pixels.

    Raises:
        ErroImagem: ``E010`` se ``M00 == 0`` — contorno degenerado, sem área.
    """
    momentos = cv2.moments(contorno)
    if momentos["m00"] == 0:
        raise ErroImagem("E010", "Contorno sem área: o centroide é indefinido.")
    return {
        "x": round(momentos["m10"] / momentos["m00"], 4),
        "y": round(momentos["m01"] / momentos["m00"], 4),
    }


def calcular_orientacao(contorno: np.ndarray) -> tuple[float | None, float, bool]:
    """Ângulo do eixo principal, pelos momentos centrais de segunda ordem.

    .. math:: \\theta = \\tfrac{1}{2}\\arctan\\!\\left(\\frac{2\\mu_{11}}{\\mu_{20}-\\mu_{02}}\\right)

    **Confiabilidade.** O ângulo só tem significado se existir um eixo dominante. Num
    objeto aproximadamente circular os dois eixos têm comprimento semelhante e o ângulo
    vira ruído — gira arbitrariamente com o menor detalhe de borda.

    A medida usada é a **anisotropia**, derivada dos autovalores da matriz de
    covariância dos momentos centrais normalizados:

    .. math:: a = \\frac{\\lambda_1 - \\lambda_2}{\\lambda_1 + \\lambda_2}

    Vale 0 para um objeto perfeitamente isotrópico e tende a 1 para um objeto muito
    alongado. É adimensional e invariante a escala — as duas propriedades necessárias
    para comparar imagens diferentes.

    Isto é geometria por momentos, **não aprendizado de máquina**: não há treinamento,
    não há ajuste, e o resultado é função fechada dos pontos do contorno.

    Args:
        contorno: Contorno do objeto.

    Returns:
        ``(angulo_graus, anisotropia, confiavel)``. O ângulo é ``None`` quando não
        confiável, medido no sentido matemático a partir do eixo x.

    Raises:
        ErroImagem: ``E010`` se o contorno não tiver área.
    """
    momentos = cv2.moments(contorno)
    if momentos["m00"] == 0:
        raise ErroImagem("E010", "Contorno sem área: a orientação é indefinida.")

    # Momentos centrais normalizados pela área formam a matriz de covariância.
    mu20 = momentos["mu20"] / momentos["m00"]
    mu02 = momentos["mu02"] / momentos["m00"]
    mu11 = momentos["mu11"] / momentos["m00"]

    # Autovalores da matriz [[mu20, mu11], [mu11, mu02]].
    traco = mu20 + mu02
    discriminante = math.sqrt(max(0.0, (mu20 - mu02) ** 2 + 4.0 * mu11 ** 2))
    lambda1 = (traco + discriminante) / 2.0
    lambda2 = (traco - discriminante) / 2.0

    anisotropia = ((lambda1 - lambda2) / (lambda1 + lambda2)) if (lambda1 + lambda2) > 0 else 0.0
    anisotropia = round(max(0.0, min(1.0, anisotropia)), 6)

    confiavel = anisotropia >= ANISOTROPIA_MINIMA_EXPERIMENTAL
    if not confiavel:
        return None, anisotropia, False

    # O fator 1/2 vem da periodicidade de pi do eixo principal.
    angulo = 0.5 * math.atan2(2.0 * mu11, mu20 - mu02)
    return round(math.degrees(angulo), 4), anisotropia, True


def calcular_bbox(contorno: np.ndarray) -> dict[str, int]:
    """Caixa envolvente alinhada aos eixos.

    **Sensível a rotação**: gira com o objeto, então descreve o enquadramento tanto
    quanto a forma. A caixa rotacionada de :func:`calcular_bbox_rotacionada` é a que
    descreve a forma.

    Returns:
        ``{"x", "y", "largura", "altura"}`` em pixels.
    """
    x, y, largura, altura = cv2.boundingRect(contorno)
    return {"x": int(x), "y": int(y), "largura": int(largura), "altura": int(altura)}


def calcular_bbox_rotacionada(contorno: np.ndarray) -> dict[str, object]:
    """Caixa envolvente de área mínima, com ângulo normalizado.

    **Limitação do ângulo do OpenCV, e por que ele é normalizado aqui.**
    ``cv2.minAreaRect`` devolve o ângulo num intervalo que depende da versão da
    biblioteca, e qual dimensão é chamada de "largura" muda conforme a orientação
    encontrada. O mesmo retângulo físico pode sair como ``(w=100, h=40, ang=0)`` ou
    ``(w=40, h=100, ang=90)``.

    Usar esse ângulo diretamente produziria saltos de 90° em objetos quase quadrados.
    Aqui a convenção é fixada: **``lado_maior`` é sempre o maior**, ``lado_menor``
    sempre o menor, e ``angulo_graus`` é o ângulo do **lado maior**, normalizado para
    ``[0, 180)``.

    Returns:
        ``{"centro_x", "centro_y", "lado_maior", "lado_menor", "angulo_graus",
        "largura_bruta", "altura_bruta", "angulo_bruto"}``. Os campos ``_bruto``
        guardam o retorno original, para auditoria.
    """
    (centro_x, centro_y), (largura, altura), angulo_bruto = cv2.minAreaRect(contorno)

    lado_maior = max(largura, altura)
    lado_menor = min(largura, altura)

    # Se a altura for o lado maior, o ângulo do lado maior está a 90° do devolvido.
    angulo = angulo_bruto if largura >= altura else angulo_bruto + 90.0
    angulo = angulo % 180.0

    return {
        "centro_x": round(float(centro_x), 4),
        "centro_y": round(float(centro_y), 4),
        "lado_maior": round(float(lado_maior), 4),
        "lado_menor": round(float(lado_menor), 4),
        "angulo_graus": round(float(angulo), 4),
        "largura_bruta": round(float(largura), 4),
        "altura_bruta": round(float(altura), 4),
        "angulo_bruto": round(float(angulo_bruto), 4),
    }


def calcular_hull(contorno: np.ndarray) -> tuple[np.ndarray, float, float, int]:
    """Convex hull do contorno.

    O menor polígono convexo que contém o objeto. Na Fase 7 servirá de base para a
    solidez, que distingue borda lisa de borda recortada.

    Returns:
        ``(hull, area, perimetro, numero_de_pontos)``.
    """
    hull = cv2.convexHull(contorno)
    return hull, float(cv2.contourArea(hull)), float(cv2.arcLength(hull, True)), int(len(hull))


def detectar_toca_borda(contorno: np.ndarray, forma: tuple[int, int]) -> dict[str, bool]:
    """Verifica se o contorno encosta em cada borda do quadro.

    A verificação usa os **pontos do contorno**, e não a caixa envolvente: a caixa
    poderia tocar a borda por causa de um ponto distante, enquanto o objeto não toca.

    Args:
        contorno: Contorno do objeto.
        forma: ``(altura, largura)`` da imagem.

    Returns:
        ``{"topo", "base", "esquerda", "direita", "qualquer"}``.
    """
    altura, largura = forma
    pontos = contorno.reshape(-1, 2)
    xs, ys = pontos[:, 0], pontos[:, 1]

    toques = {
        "topo": bool(np.any(ys <= 0)),
        "base": bool(np.any(ys >= altura - 1)),
        "esquerda": bool(np.any(xs <= 0)),
        "direita": bool(np.any(xs >= largura - 1)),
    }
    toques["qualquer"] = any(toques.values())
    return toques


def calcular_distancia_minima_borda(contorno: np.ndarray, forma: tuple[int, int]) -> int:
    """Menor distância entre o contorno e qualquer borda do quadro, em pixels.

    Sinal de diagnóstico — indica quão perto o objeto esteve de ser cortado.
    **Não é característica morfológica**: depende do enquadramento, não da folha.
    """
    altura, largura = forma
    pontos = contorno.reshape(-1, 2)
    xs, ys = pontos[:, 0], pontos[:, 1]

    return int(min(
        int(xs.min()),
        int(ys.min()),
        int(largura - 1 - xs.max()),
        int(altura - 1 - ys.max()),
    ))


# ---------------------------------------------------------------------------
# Orquestração
# ---------------------------------------------------------------------------

def analisar_contorno(
    mascara: np.ndarray,
    razao_ambiguidade: float = RAZAO_AMBIGUIDADE_EXPERIMENTAL,
) -> ResultadoContorno:
    """Extrai toda a geometria do objeto principal de uma máscara.

    Args:
        mascara: Máscara binária limpa.
        razao_ambiguidade: Limiar de aviso para seleção ambígua.

    Returns:
        A representação geométrica completa.

    Raises:
        ErroImagem: ``E009`` máscara inválida; ``E007`` nenhum objeto detectado;
            ``E010`` contorno degenerado.
    """
    validar_mascara(mascara)

    contornos = detectar_contornos(mascara)
    contorno, diagnostico = selecionar_contorno_principal(contornos, razao_ambiguidade)

    area = float(cv2.contourArea(contorno))
    perimetro = float(cv2.arcLength(contorno, True))
    centroide = calcular_centroide(contorno)
    orientacao, anisotropia, confiavel = calcular_orientacao(contorno)
    hull, area_hull, perimetro_hull, pontos_hull = calcular_hull(contorno)
    toques = detectar_toca_borda(contorno, mascara.shape)

    avisos = list(diagnostico["avisos"])  # type: ignore[arg-type]
    if toques["qualquer"]:
        avisos.append("objeto_toca_borda")
    if not confiavel:
        avisos.append("orientacao_nao_confiavel")

    return ResultadoContorno(
        contorno=contorno,
        area_px2=round(area, 4),
        area_mascara_px=int(np.count_nonzero(mascara == OBJETO)),
        perimetro_px=round(perimetro, 4),
        bbox=calcular_bbox(contorno),
        bbox_rotacionada=calcular_bbox_rotacionada(contorno),
        centroide=centroide,
        orientacao_graus=orientacao,
        anisotropia=anisotropia,
        orientacao_confiavel=confiavel,
        hull=hull,
        area_hull_px2=round(area_hull, 4),
        perimetro_hull_px=round(perimetro_hull, 4),
        pontos_hull=pontos_hull,
        toca_borda=toques,
        distancia_minima_borda_px=calcular_distancia_minima_borda(contorno, mascara.shape),
        numero_contornos=int(diagnostico["numero_contornos"]),  # type: ignore[arg-type]
        dominancia=float(diagnostico["dominancia"]),  # type: ignore[arg-type]
        avisos=avisos,
    )
