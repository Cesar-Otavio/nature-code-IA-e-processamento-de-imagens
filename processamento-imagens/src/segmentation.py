"""Segmentação da folha: separação entre objeto e fundo por métodos clássicos.

Entrada: imagem pré-processada. Saída: máscara binária em que a folha vale 255 e o
fundo vale 0.

Todas as estratégias são **determinísticas** e baseadas em processamento digital
clássico — limiarização por intensidade, faixa em espaço de cor e limiar adaptativo.
Não há aprendizado, não há modelo treinado, não há ``cv2.dnn``.

Cada estratégia devolve um :class:`ResultadoSegmentacao`, e não apenas a matriz: a
máscara sozinha esconderia qual método a produziu, com quais parâmetros e quão
suspeita ela é. Essa informação é necessária para comparar estratégias e para
diagnosticar falhas.

**Nesta fase nenhuma operação morfológica é aplicada ao resultado oficial.** Limpar
a máscara é trabalho da Fase 5; aqui as estratégias são comparadas em estado bruto,
para que a comparação meça a segmentação e não a limpeza posterior.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from .utils import ErroImagem

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

#: Valores da máscara binária. O OpenCV trata qualquer não-zero como verdadeiro,
#: mas fixar 0/255 torna a máscara visualizável e comparável sem ambiguidade.
FUNDO: int = 0
OBJETO: int = 255

#: Espessura, em pixels, da faixa de borda usada para decidir a polaridade.
#: Ver :func:`garantir_polaridade`.
ESPESSURA_BORDA_PX: int = 5

#: Faixa de verde em HSV (OpenCV: H em 0..179, S e V em 0..255).
#:
#: **Calibrada sobre o conjunto de desenvolvimento**, não copiada de tutorial.
#:
#: Distribuição medida em 16.220.932 pixels de folha, nas 64 imagens de
#: desenvolvimento:
#:
#: =======  ====  ====  ========  ====  ====
#: canal      p1    p5   mediana   p95   p99
#: =======  ====  ====  ========  ====  ====
#: H          43    46        53    60    67
#: S          82   112       173   253   255
#: V          51    93       152   213   233
#: =======  ====  ====  ========  ====  ====
#:
#: **Achado contraintuitivo, medido:** a faixa *justa* (H 43–67, dos próprios
#: percentis) é **pior** que a ampla. Ela recorta pixels de dentro da folha — bordas,
#: nervuras e áreas com brilho têm matiz ligeiramente deslocado —, fragmentando a
#: máscara em até **409 componentes**, contra **3** da faixa ampla. Quem separa a
#: folha do fundo branco é a **saturação mínima**, não o matiz: o fundo tem S≈0. A
#: faixa de H serve para excluir objetos coloridos que não sejam verdes.
#:
#: Comparação registrada em ``docs/processamento-imagens/04-SEGMENTACAO.md`` §7.
#:
#: Uma folha seca, avermelhada ou variegada fica legitimamente fora desta faixa — é
#: limitação conhecida do método, não defeito da implementação.
FAIXA_VERDE_EXPERIMENTAL: dict[str, tuple[int, int]] = {
    "h": (25, 95),
    "s": (40, 255),
    "v": (20, 255),
}


@dataclass
class ResultadoSegmentacao:
    """Máscara binária acompanhada da procedência e do diagnóstico.

    Attributes:
        mascara: Matriz 2D ``uint8`` com valores ``0`` e ``255``.
        estrategia: Nome do método que a produziu.
        parametros: Parâmetros efetivamente usados, para reprodução.
        metricas: Indicadores de triagem de :func:`analisar_mascara`.
        avisos: Códigos de máscara suspeita. Lista vazia não prova acerto.
    """

    mascara: np.ndarray
    estrategia: str
    parametros: dict[str, object] = field(default_factory=dict)
    metricas: dict[str, object] = field(default_factory=dict)
    avisos: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Validação e análise de máscara
# ---------------------------------------------------------------------------

def validar_mascara(mascara: np.ndarray, forma_esperada: tuple[int, int] | None = None) -> np.ndarray:
    """Confere que a matriz é uma máscara binária utilizável.

    Args:
        mascara: Matriz a validar.
        forma_esperada: ``(altura, largura)`` que a máscara deve ter. Quando ``None``,
            a forma não é conferida.

    Returns:
        A própria máscara, validada.

    Raises:
        ErroImagem: ``E009`` se não for ``uint8``, não for 2D, contiver valor
            diferente de 0 e 255, estiver vazia ou tiver forma diferente da esperada.
    """
    if mascara is None or not isinstance(mascara, np.ndarray):
        raise ErroImagem("E009", "A máscara precisa ser uma matriz NumPy.")
    if mascara.size == 0:
        raise ErroImagem("E009", "A máscara está vazia.")
    if mascara.ndim != 2:
        raise ErroImagem("E009", f"A máscara precisa ser 2D; veio com {mascara.ndim} dimensões.")
    if mascara.dtype != np.uint8:
        raise ErroImagem("E009", f"A máscara precisa ser uint8; veio {mascara.dtype}.")

    valores = np.unique(mascara)
    if not np.all(np.isin(valores, (FUNDO, OBJETO))):
        fora = [int(v) for v in valores if v not in (FUNDO, OBJETO)][:5]
        raise ErroImagem("E009", f"A máscara só pode conter 0 e 255; encontrados {fora}.")

    if forma_esperada is not None and mascara.shape != forma_esperada:
        raise ErroImagem(
            "E009", f"Forma da máscara {mascara.shape} difere da esperada {forma_esperada}."
        )

    return mascara


def toca_borda(mascara: np.ndarray) -> bool:
    """Informa se algum pixel de objeto encosta na borda do quadro.

    Objeto que toca a borda provavelmente está cortado, e então área e perímetro
    medem um objeto diferente do real.
    """
    validar_mascara(mascara)
    return bool(
        np.any(mascara[0, :] == OBJETO)
        or np.any(mascara[-1, :] == OBJETO)
        or np.any(mascara[:, 0] == OBJETO)
        or np.any(mascara[:, -1] == OBJETO)
    )


def analisar_mascara(mascara: np.ndarray) -> dict[str, object]:
    """Calcula indicadores de triagem da máscara.

    Estes números **não são medida de acerto** — não há ground truth no Flavia. Eles
    apontam máscaras suspeitas, que merecem ser olhadas. Uma máscara sem nenhum
    indicador ruim ainda pode estar errada.

    Args:
        mascara: Máscara binária válida.

    Returns:
        Dicionário com ``fracao_foreground``, ``n_componentes``,
        ``dominancia_maior_componente``, ``area_maior_componente_px``,
        ``toca_borda`` e ``bbox_preliminar``.
    """
    validar_mascara(mascara)

    altura, largura = mascara.shape
    total_px = altura * largura
    foreground_px = int(np.count_nonzero(mascara))

    # Rótulo 0 é o fundo; os componentes do objeto começam em 1.
    n_rotulos, _rotulos, estatisticas, _centroides = cv2.connectedComponentsWithStats(
        mascara, connectivity=8
    )
    n_componentes = max(0, n_rotulos - 1)

    if n_componentes == 0:
        return {
            "fracao_foreground": 0.0,
            "n_componentes": 0,
            "area_maior_componente_px": 0,
            "dominancia_maior_componente": 0.0,
            "toca_borda": False,
            "bbox_preliminar": None,
        }

    areas = estatisticas[1:, cv2.CC_STAT_AREA]
    indice_maior = int(np.argmax(areas)) + 1
    area_maior = int(estatisticas[indice_maior, cv2.CC_STAT_AREA])

    return {
        "fracao_foreground": round(foreground_px / total_px, 6),
        "n_componentes": n_componentes,
        "area_maior_componente_px": area_maior,
        "dominancia_maior_componente": round(area_maior / foreground_px, 6) if foreground_px else 0.0,
        "toca_borda": toca_borda(mascara),
        "bbox_preliminar": {
            "x": int(estatisticas[indice_maior, cv2.CC_STAT_LEFT]),
            "y": int(estatisticas[indice_maior, cv2.CC_STAT_TOP]),
            "largura": int(estatisticas[indice_maior, cv2.CC_STAT_WIDTH]),
            "altura": int(estatisticas[indice_maior, cv2.CC_STAT_HEIGHT]),
        },
    }


# ---------------------------------------------------------------------------
# Polaridade
# ---------------------------------------------------------------------------

def garantir_polaridade(
    mascara: np.ndarray,
    metodo: str = "borda",
    espessura_borda: int = ESPESSURA_BORDA_PX,
) -> tuple[np.ndarray, bool]:
    """Decide se a máscara precisa ser invertida e a inverte quando necessário.

    Nenhuma limiarização sabe qual lado é o objeto. Otsu separa a imagem em dois
    grupos, mas qual grupo é a folha depende da cena: no Flavia a folha é escura
    sobre fundo claro, numa foto noturna poderia ser o contrário. Assumir uma
    polaridade fixa faria o método funcionar por acaso.

    Dois critérios, ambos testados:

    ``"borda"``
        Assume que a **moldura do quadro é fundo**. Se a maioria dos pixels na faixa
        de borda estiver marcada como objeto, a máscara está invertida. É o critério
        padrão por ser robusto ao tamanho do objeto: funciona tanto para uma folha
        pequena quanto para uma que ocupe 80% do quadro.

    ``"ocupacao"``
        Assume que o **objeto ocupa menos da metade** da imagem. Mais simples, mas
        falha quando o objeto é realmente maior que o fundo.

    Args:
        mascara: Máscara binária válida.
        metodo: ``"borda"`` ou ``"ocupacao"``.
        espessura_borda: Largura da faixa de borda, em pixels, para ``"borda"``.

    Returns:
        ``(mascara, foi_invertida)``.

    Raises:
        ErroImagem: ``E009`` máscara inválida; ``E008`` método desconhecido ou
            espessura inválida.
    """
    validar_mascara(mascara)

    if metodo not in ("borda", "ocupacao"):
        raise ErroImagem("E008", f"Método de polaridade desconhecido: '{metodo}'.")

    if metodo == "ocupacao":
        precisa_inverter = np.count_nonzero(mascara) > (mascara.size / 2)
    else:
        if isinstance(espessura_borda, bool) or not isinstance(espessura_borda, int) or espessura_borda < 1:
            raise ErroImagem("E008", f"espessura_borda precisa ser inteiro >= 1; veio {espessura_borda}.")

        altura, largura = mascara.shape
        faixa = max(1, min(espessura_borda, altura // 2, largura // 2))

        moldura = np.concatenate([
            mascara[:faixa, :].ravel(),
            mascara[-faixa:, :].ravel(),
            mascara[:, :faixa].ravel(),
            mascara[:, -faixa:].ravel(),
        ])
        precisa_inverter = np.count_nonzero(moldura) > (moldura.size / 2)

    if precisa_inverter:
        return cv2.bitwise_not(mascara), True
    return mascara, False


# ---------------------------------------------------------------------------
# Estratégias
# ---------------------------------------------------------------------------

def segmentar_otsu(
    imagem_cinza: np.ndarray,
    metodo_polaridade: str = "borda",
) -> ResultadoSegmentacao:
    """Limiarização global pelo método de Otsu.

    **Hipótese:** o histograma de intensidade tem dois modos bem separados — folha
    escura e fundo claro —, e Otsu encontra o limiar que maximiza a variância entre
    eles sem que ninguém precise escolher um valor.

    É a estratégia de referência: não tem parâmetro para ajustar, o que a torna a
    linha de base honesta contra a qual as outras precisam se justificar.

    **Ponto fraco previsto:** Otsu decide por intensidade, e sombra também é escura.
    Uma sombra projetada no fundo tende a ser incorporada ao objeto.

    Args:
        imagem_cinza: Imagem de 1 canal, ``uint8``.
        metodo_polaridade: Critério de :func:`garantir_polaridade`.

    Returns:
        Resultado com a máscara e o limiar escolhido por Otsu.

    Raises:
        ErroImagem: ``E004`` se a imagem não for de canal único.
    """
    if imagem_cinza is None or not isinstance(imagem_cinza, np.ndarray):
        raise ErroImagem("E004", "A imagem precisa ser uma matriz NumPy.")
    if imagem_cinza.size == 0:
        raise ErroImagem("E004", "A imagem está vazia.")
    if imagem_cinza.ndim != 2:
        raise ErroImagem("E004", "Otsu exige imagem de 1 canal (escala de cinza).")
    if imagem_cinza.dtype != np.uint8:
        raise ErroImagem("E004", f"Otsu exige uint8; veio {imagem_cinza.dtype}.")

    limiar, bruta = cv2.threshold(imagem_cinza, 0, OBJETO, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mascara, invertida = garantir_polaridade(bruta, metodo=metodo_polaridade)

    return ResultadoSegmentacao(
        mascara=mascara,
        estrategia="otsu",
        parametros={
            "limiar_otsu": float(limiar),
            "metodo_polaridade": metodo_polaridade,
            "invertida": invertida,
        },
        metricas=analisar_mascara(mascara),
    )


def segmentar_hsv(
    imagem_bgr: np.ndarray,
    faixa: dict[str, tuple[int, int]] | None = None,
) -> ResultadoSegmentacao:
    """Segmentação por faixa de cor em HSV.

    **Hipótese:** a folha é verde, e o matiz do verde é aproximadamente estável
    mesmo quando o brilho varia — porque o HSV separa matiz de iluminação, coisa que
    o RGB não faz. Um fundo branco tem saturação baixa e cai fora da faixa.

    **Vantagem prevista sobre Otsu:** sombra no fundo continua sendo cinza — escura,
    porém sem saturação —, então não entra na máscara.

    **Ponto fraco previsto:** folha seca, avermelhada ou variegada fica fora da
    faixa de verde. É limitação do método, não defeito da implementação.

    Args:
        imagem_bgr: Imagem de 3 canais em BGR.
        faixa: Limites ``{"h": (min, max), "s": (...), "v": (...)}``. Quando ``None``,
            usa :data:`FAIXA_VERDE_EXPERIMENTAL`.

    Returns:
        Resultado com a máscara e a faixa usada.

    Raises:
        ErroImagem: ``E004`` imagem inválida; ``E008`` faixa malformada.
    """
    if imagem_bgr is None or not isinstance(imagem_bgr, np.ndarray):
        raise ErroImagem("E004", "A imagem precisa ser uma matriz NumPy.")
    if imagem_bgr.size == 0:
        raise ErroImagem("E004", "A imagem está vazia.")
    if imagem_bgr.ndim != 3 or imagem_bgr.shape[2] != 3:
        raise ErroImagem("E004", "A segmentação por HSV exige imagem de 3 canais.")

    limites = faixa if faixa is not None else FAIXA_VERDE_EXPERIMENTAL
    for canal in ("h", "s", "v"):
        if canal not in limites:
            raise ErroImagem("E008", f"A faixa precisa conter o canal '{canal}'.")
        minimo, maximo = limites[canal]
        if not isinstance(minimo, int) or not isinstance(maximo, int) or minimo > maximo:
            raise ErroImagem("E008", f"Faixa inválida no canal '{canal}': {limites[canal]}.")

    hsv = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2HSV)
    inferior = np.array([limites["h"][0], limites["s"][0], limites["v"][0]], dtype=np.uint8)
    superior = np.array([limites["h"][1], limites["s"][1], limites["v"][1]], dtype=np.uint8)

    mascara = cv2.inRange(hsv, inferior, superior)

    # inRange já devolve 0/255, e o objeto é o que está DENTRO da faixa: não há
    # ambiguidade de polaridade aqui, ao contrário de Otsu.
    return ResultadoSegmentacao(
        mascara=mascara,
        estrategia="hsv",
        parametros={"faixa": {k: tuple(v) for k, v in limites.items()}},
        metricas=analisar_mascara(mascara),
    )


def segmentar_adaptativo(
    imagem_cinza: np.ndarray,
    bloco: int = 51,
    constante: int = 5,
    metodo_polaridade: str = "borda",
) -> ResultadoSegmentacao:
    """Limiarização adaptativa: um limiar por vizinhança, não um global.

    **Hipótese:** quando a iluminação varia ao longo do quadro, nenhum limiar global
    serve — o que é escuro de um lado pode ser claro do outro. O limiar adaptativo
    compara cada pixel com a média da sua vizinhança.

    **Ponto fraco previsto:** em regiões grandes e uniformes, como o interior da
    folha e o fundo liso, a comparação local não tem referência e o método produz
    ruído. É exatamente a condição do Flavia.

    Args:
        imagem_cinza: Imagem de 1 canal, ``uint8``.
        bloco: Lado da vizinhança, ímpar e ``>= 3``.
        constante: Subtraída da média local.
        metodo_polaridade: Critério de :func:`garantir_polaridade`.

    Returns:
        Resultado com a máscara e os parâmetros usados.

    Raises:
        ErroImagem: ``E004`` imagem inválida; ``E008`` bloco inválido.
    """
    if imagem_cinza is None or not isinstance(imagem_cinza, np.ndarray):
        raise ErroImagem("E004", "A imagem precisa ser uma matriz NumPy.")
    if imagem_cinza.size == 0:
        raise ErroImagem("E004", "A imagem está vazia.")
    if imagem_cinza.ndim != 2:
        raise ErroImagem("E004", "O limiar adaptativo exige imagem de 1 canal.")
    if isinstance(bloco, bool) or not isinstance(bloco, int) or bloco < 3 or bloco % 2 == 0:
        raise ErroImagem("E008", f"bloco precisa ser inteiro ímpar >= 3; veio {bloco}.")

    bruta = cv2.adaptiveThreshold(
        imagem_cinza, OBJETO, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, bloco, constante
    )
    mascara, invertida = garantir_polaridade(bruta, metodo=metodo_polaridade)

    return ResultadoSegmentacao(
        mascara=mascara,
        estrategia="adaptativo",
        parametros={
            "bloco": bloco,
            "constante": constante,
            "metodo_polaridade": metodo_polaridade,
            "invertida": invertida,
        },
        metricas=analisar_mascara(mascara),
    )


def segmentar_combinado(
    imagem_bgr: np.ndarray,
    imagem_cinza: np.ndarray,
    modo: str = "uniao",
    faixa: dict[str, tuple[int, int]] | None = None,
) -> ResultadoSegmentacao:
    """Combina as máscaras de Otsu e HSV por operação lógica.

    **Hipótese da interseção (``"intersecao"``):** um pixel só é folha se for escuro
    *e* verde. Deveria eliminar sombra — escura mas sem saturação — e reflexo —
    verde mas claro. Custo: qualquer região que um dos métodos perca é perdida no
    resultado.

    **Hipótese da união (``"uniao"``):** um pixel é folha se for escuro *ou* verde.
    Deveria recuperar partes que um método isolado perde, como o brilho especular
    que o HSV descarta. Custo: soma os falsos positivos dos dois.

    Args:
        imagem_bgr: Imagem de 3 canais em BGR.
        imagem_cinza: A mesma imagem em 1 canal.
        modo: ``"uniao"`` ou ``"intersecao"``.
        faixa: Faixa HSV; ``None`` usa a experimental.

    Returns:
        Resultado com a máscara combinada.

    Raises:
        ErroImagem: ``E008`` modo desconhecido ou formas incompatíveis.
    """
    if modo not in ("uniao", "intersecao"):
        raise ErroImagem("E008", f"Modo de combinação desconhecido: '{modo}'.")

    resultado_otsu = segmentar_otsu(imagem_cinza)
    resultado_hsv = segmentar_hsv(imagem_bgr, faixa=faixa)

    if resultado_otsu.mascara.shape != resultado_hsv.mascara.shape:
        raise ErroImagem("E008", "As imagens colorida e em cinza têm formas diferentes.")

    operacao = cv2.bitwise_or if modo == "uniao" else cv2.bitwise_and
    mascara = operacao(resultado_otsu.mascara, resultado_hsv.mascara)

    return ResultadoSegmentacao(
        mascara=mascara,
        estrategia=f"combinado_{modo}",
        parametros={
            "modo": modo,
            "limiar_otsu": resultado_otsu.parametros["limiar_otsu"],
            "faixa": resultado_hsv.parametros["faixa"],
        },
        metricas=analisar_mascara(mascara),
    )
