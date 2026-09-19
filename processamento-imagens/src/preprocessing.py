"""Pré-processamento: redimensionamento, espaços de cor e redução de ruído.

Todas as operações deste módulo são **determinísticas**: a mesma entrada, com os
mesmos parâmetros, produz sempre exatamente a mesma saída. Não há aleatoriedade,
não há estado global e não há aprendizado.

Convenção de cor: as funções recebem imagem em **BGR**, que é a ordem nativa do
OpenCV. A conversão para RGB existe apenas para exibição e gravação em bibliotecas
que esperam essa ordem.

Nesta fase os filtros são **candidatos em comparação**, não escolhas definitivas.
A decisão entre Gaussiano e mediana sai da Fase 4, medida sobre o conjunto de
desenvolvimento — não desta fase.
"""

from __future__ import annotations

import cv2
import numpy as np

from .utils import ErroImagem

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

#: Lado maior alvo do redimensionamento, em pixels.
#:
#: **Valor experimental, não decisão final.** O Flavia é uniformemente 1600x1200;
#: reduzir para 1024 corta a área em cerca de 60% e, portanto, o custo das operações
#: por pixel. O valor definitivo sai da Fase 4, comparando custo de tempo contra
#: estabilidade das medidas de contorno.
LADO_MAXIMO_PX_EXPERIMENTAL: int = 1024

#: Kernel padrão dos filtros. Ímpar por exigência do OpenCV.
#: Também experimental: o tamanho adequado depende da escala do ruído observado,
#: que só será medido na Fase 4.
KERNEL_PADRAO_EXPERIMENTAL: int = 5

#: Menor kernel que produz algum efeito de suavização.
KERNEL_MINIMO: int = 3


def _validar_imagem(imagem: np.ndarray, nome_do_argumento: str = "imagem") -> None:
    """Confere que o argumento é uma matriz de imagem utilizável.

    Raises:
        ErroImagem: ``E004`` se for ``None``, vazia ou com número de dimensões
            incompatível com uma imagem.
    """
    if imagem is None:
        raise ErroImagem("E004", f"{nome_do_argumento} não pode ser None.")
    if not isinstance(imagem, np.ndarray):
        raise ErroImagem("E004", f"{nome_do_argumento} precisa ser uma matriz NumPy.")
    if imagem.size == 0:
        raise ErroImagem("E004", f"{nome_do_argumento} está vazia.")
    if imagem.ndim not in (2, 3):
        raise ErroImagem(
            "E004", f"{nome_do_argumento} tem {imagem.ndim} dimensões; esperado 2 ou 3."
        )


def _validar_kernel(kernel: int) -> int:
    """Confere que o kernel é ímpar e não menor que o mínimo.

    O OpenCV exige kernel ímpar em ``GaussianBlur`` e ``medianBlur``: sem um pixel
    central definido, não há onde centrar a janela do filtro.

    Args:
        kernel: Lado da janela do filtro, em pixels.

    Returns:
        O próprio kernel, validado.

    Raises:
        ErroImagem: ``E008`` se não for inteiro, for par ou for menor que
            ``KERNEL_MINIMO``.
    """
    if isinstance(kernel, bool) or not isinstance(kernel, int):
        raise ErroImagem("E008", f"O kernel precisa ser um inteiro; veio {type(kernel).__name__}.")
    if kernel < KERNEL_MINIMO:
        raise ErroImagem("E008", f"O kernel precisa ser no mínimo {KERNEL_MINIMO}; veio {kernel}.")
    if kernel % 2 == 0:
        raise ErroImagem("E008", f"O kernel precisa ser ímpar; veio {kernel}.")
    return kernel


# ---------------------------------------------------------------------------
# Redimensionamento
# ---------------------------------------------------------------------------

def redimensionar(
    imagem: np.ndarray,
    lado_maximo: int = LADO_MAXIMO_PX_EXPERIMENTAL,
    ampliar: bool = False,
) -> tuple[np.ndarray, dict[str, object]]:
    """Redimensiona preservando a proporção original.

    Por padrão **não amplia**: uma imagem já menor que ``lado_maximo`` é devolvida
    inalterada. Ampliar não cria informação — apenas interpola — e inflaria
    artificialmente as medidas de área e perímetro.

    A interpolação é escolhida conforme o sentido da mudança: ``INTER_AREA`` para
    reduzir, que faz média dos pixels da região e evita serrilhado, e
    ``INTER_LINEAR`` para ampliar.

    Args:
        imagem: Imagem de entrada, em qualquer número de canais.
        lado_maximo: Tamanho alvo do maior lado, em pixels.
        ampliar: Se ``True``, amplia imagens menores que ``lado_maximo``.

    Returns:
        ``(imagem_redimensionada, info)``, em que ``info`` traz
        ``largura_original_px``, ``altura_original_px``, ``largura_px``,
        ``altura_px``, ``fator_escala`` e ``redimensionada``.

    Raises:
        ErroImagem: ``E004`` se a imagem for inválida; ``E008`` se ``lado_maximo``
            não for um inteiro positivo.
    """
    _validar_imagem(imagem)

    if isinstance(lado_maximo, bool) or not isinstance(lado_maximo, int) or lado_maximo <= 0:
        raise ErroImagem("E008", f"lado_maximo precisa ser um inteiro positivo; veio {lado_maximo}.")

    altura, largura = imagem.shape[:2]
    maior_lado = max(altura, largura)
    fator = lado_maximo / maior_lado

    if fator >= 1.0 and not ampliar:
        return imagem, {
            "largura_original_px": largura,
            "altura_original_px": altura,
            "largura_px": largura,
            "altura_px": altura,
            "fator_escala": 1.0,
            "redimensionada": False,
        }

    # max(1, ...) evita dimensão zero em imagens de proporção muito extrema.
    nova_largura = max(1, int(round(largura * fator)))
    nova_altura = max(1, int(round(altura * fator)))

    interpolacao = cv2.INTER_AREA if fator < 1.0 else cv2.INTER_LINEAR
    saida = cv2.resize(imagem, (nova_largura, nova_altura), interpolation=interpolacao)

    return saida, {
        "largura_original_px": largura,
        "altura_original_px": altura,
        "largura_px": nova_largura,
        "altura_px": nova_altura,
        "fator_escala": round(fator, 6),
        "redimensionada": True,
    }


# ---------------------------------------------------------------------------
# Espaços de cor
# ---------------------------------------------------------------------------

def para_rgb(imagem_bgr: np.ndarray) -> np.ndarray:
    """Converte de BGR para RGB.

    Finalidade: exibição e gravação em bibliotecas que esperam RGB. **Não** é usada
    no processamento — a ordem dos canais não altera nenhuma medida geométrica.

    Args:
        imagem_bgr: Imagem de 3 canais em BGR.

    Returns:
        Imagem de 3 canais em RGB, mesma forma, ``uint8``, cada canal em ``0..255``.

    Raises:
        ErroImagem: ``E004`` se a imagem não tiver exatamente 3 canais.
    """
    _validar_imagem(imagem_bgr)
    if imagem_bgr.ndim != 3 or imagem_bgr.shape[2] != 3:
        raise ErroImagem("E004", "A conversão para RGB exige uma imagem de 3 canais.")
    return cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2RGB)


def para_cinza(imagem_bgr: np.ndarray) -> np.ndarray:
    """Converte de BGR para escala de cinza.

    Finalidade: base da limiarização por intensidade — Otsu e limiar adaptativo
    operam sobre um único canal. É o caminho mais direto de segmentação quando o
    fundo é claro e o objeto escuro, como no Flavia.

    A conversão é uma média ponderada dos canais, com peso maior no verde, seguindo
    a sensibilidade do olho humano.

    Args:
        imagem_bgr: Imagem de 3 canais em BGR.

    Returns:
        Imagem de 1 canal, ``uint8``, valores em ``0..255``.

    Raises:
        ErroImagem: ``E004`` se a imagem não tiver exatamente 3 canais.
    """
    _validar_imagem(imagem_bgr)
    if imagem_bgr.ndim != 3 or imagem_bgr.shape[2] != 3:
        raise ErroImagem("E004", "A conversão para cinza exige uma imagem de 3 canais.")
    return cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2GRAY)


def para_hsv(imagem_bgr: np.ndarray) -> np.ndarray:
    """Converte de BGR para HSV.

    Finalidade: separar **matiz** de **iluminação**. Uma folha verde mantém o matiz
    aproximadamente constante mesmo quando a luz varia, o que torna o HSV candidato
    natural à segmentação por cor — e é o espaço onde a proporção de pixels verdes
    será calculada.

    Intervalos no OpenCV para imagem ``uint8``, que **não** são os convencionais:

    ===========  ==========  ============================================
    Canal        Intervalo   Observação
    ===========  ==========  ============================================
    H (matiz)    0..179      metade do ângulo em graus, para caber em 8 bits
    S (satur.)   0..255      convencionalmente 0..100%
    V (valor)    0..255      convencionalmente 0..100%
    ===========  ==========  ============================================

    Args:
        imagem_bgr: Imagem de 3 canais em BGR.

    Returns:
        Imagem de 3 canais em HSV, ``uint8``.

    Raises:
        ErroImagem: ``E004`` se a imagem não tiver exatamente 3 canais.
    """
    _validar_imagem(imagem_bgr)
    if imagem_bgr.ndim != 3 or imagem_bgr.shape[2] != 3:
        raise ErroImagem("E004", "A conversão para HSV exige uma imagem de 3 canais.")
    return cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2HSV)


# ---------------------------------------------------------------------------
# Redução de ruído — candidatos em comparação
# ---------------------------------------------------------------------------

def suavizar_gaussiano(
    imagem: np.ndarray,
    kernel: int = KERNEL_PADRAO_EXPERIMENTAL,
    sigma: float = 0.0,
) -> np.ndarray:
    """Aplica filtro Gaussiano.

    Efeito: atenua ruído de alta frequência fazendo a média ponderada da vizinhança,
    com peso decrescente conforme a distância ao centro.

    Custo: **suaviza as bordas junto com o ruído**. Kernel grande demais arredonda o
    contorno da folha e altera perímetro e circularidade — exatamente as medidas que
    o projeto quer preservar. É a razão de o tamanho do kernel ser decidido por
    medição, e não por hábito.

    Args:
        imagem: Imagem de 1 ou 3 canais.
        kernel: Lado da janela, ímpar e ``>= 3``.
        sigma: Desvio padrão. Com ``0.0``, o OpenCV o deriva do kernel.

    Returns:
        Imagem suavizada, mesma forma e tipo da entrada.

    Raises:
        ErroImagem: ``E004`` imagem inválida; ``E008`` kernel inválido.
    """
    _validar_imagem(imagem)
    _validar_kernel(kernel)
    return cv2.GaussianBlur(imagem, (kernel, kernel), sigma)


def suavizar_mediana(
    imagem: np.ndarray,
    kernel: int = KERNEL_PADRAO_EXPERIMENTAL,
) -> np.ndarray:
    """Aplica filtro de mediana.

    Efeito: substitui cada pixel pela mediana da vizinhança. Como a mediana descarta
    valores extremos em vez de os diluir, é muito eficaz contra **ruído impulsivo**
    (sal e pimenta) — o tipo que os pequenos artefatos escuros do fundo do Flavia
    produzem.

    Preserva bordas melhor que a média, porque não mistura os dois lados de uma
    transição. Em compensação é mais caro: exige ordenar a vizinhança de cada pixel.

    Args:
        imagem: Imagem de 1 ou 3 canais.
        kernel: Lado da janela, ímpar e ``>= 3``.

    Returns:
        Imagem filtrada, mesma forma e tipo da entrada.

    Raises:
        ErroImagem: ``E004`` imagem inválida; ``E008`` kernel inválido.
    """
    _validar_imagem(imagem)
    _validar_kernel(kernel)
    return cv2.medianBlur(imagem, kernel)
