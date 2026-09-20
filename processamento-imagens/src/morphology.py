"""Morfologia matemática e limpeza da máscara binária.

Entrada: máscara da segmentação. Saída: máscara limpa.

**Princípio da menor intervenção.** Limpar não é deixar a máscara visualmente mais
lisa — é remover artefato irrelevante sem tocar na geometria real. Uma máscara mais
bonita pode ser matematicamente pior: erosão come pontas, dilatação engrossa bordas, e
ambas alteram perímetro e circularidade, que são medidas do projeto.

Quando duas soluções entregam resultado equivalente, **adota-se a que modifica menos
pixels**.

As operações aqui são primitivas testáveis e independentes. Quais entram no pipeline é
decisão medida, registrada em ``docs/processamento-imagens/05-MORFOLOGIA.md`` — não
consequência de estarem implementadas.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from .segmentation import FUNDO, OBJETO, validar_mascara
from .utils import ErroImagem

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

#: Formas de elemento estruturante disponíveis.
FORMAS_KERNEL: dict[str, int] = {
    "retangular": cv2.MORPH_RECT,
    "eliptico": cv2.MORPH_ELLIPSE,
    "cruz": cv2.MORPH_CROSS,
}

#: Fração da área do componente principal abaixo da qual um componente desconectado
#: é considerado artefato.
#:
#: **Calibrado sobre o conjunto de desenvolvimento**, não arbitrado. Medição em 64
#: imagens: 15 componentes pequenos, de 1 a 74 px, com fração máxima de **0,000355**
#: do principal. O limiar de 0,001 fica ~3× acima do maior artefato observado e
#: ordens de grandeza abaixo de qualquer estrutura foliar real — um lóbulo ou pecíolo
#: destacado teria fração muito maior.
#:
#: Critério **relativo** de propósito: a área do componente principal varia de 21.313
#: a 428.655 px no conjunto, então um limiar absoluto significaria coisas diferentes
#: em imagens diferentes.
FRACAO_COMPONENTE_PEQUENO: float = 0.001

#: Fração da área do componente principal abaixo da qual um buraco interno é
#: considerado defeito de segmentação, e não estrutura real.
#:
#: **Calibrado**: 167 buracos medidos, de 1 a 216 px, fração máxima de 0,001105.
#: O limiar de 0,002 cobre todos os observados com folga de ~2×.
#:
#: **Ressalva importante:** este limiar separa por *tamanho*, e tamanho não distingue
#: com certeza "buraco causado pela segmentação" de "perfuração real na folha". Ver
#: §11 da documentação da fase.
FRACAO_BURACO_PEQUENO: float = 0.002


@dataclass
class ResultadoLimpeza:
    """Máscara limpa com o registro completo do que foi alterado.

    Devolver só a máscara esconderia quanto a limpeza mexeu na geometria — que é
    exatamente o que precisa ser auditável nesta fase.

    Attributes:
        mascara: Máscara após a limpeza.
        mascara_original: Máscara recebida, preservada para comparação.
        operacoes: Operações aplicadas, em ordem.
        parametros: Parâmetros usados.
        metricas: Comparação antes/depois de :func:`comparar_mascaras`.
        avisos: Códigos de alteração suspeita.
    """

    mascara: np.ndarray
    mascara_original: np.ndarray
    operacoes: list[str] = field(default_factory=list)
    parametros: dict[str, object] = field(default_factory=dict)
    metricas: dict[str, object] = field(default_factory=dict)
    avisos: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------

def criar_kernel(tamanho: int = 3, forma: str = "eliptico") -> np.ndarray:
    """Cria o elemento estruturante.

    Args:
        tamanho: Lado do elemento, ímpar e ``>= 3``.
        forma: ``"retangular"``, ``"eliptico"`` ou ``"cruz"``.

    Returns:
        Matriz do elemento estruturante.

    Raises:
        ErroImagem: ``E008`` se o tamanho for par, menor que 3, de tipo errado, ou se
            a forma for desconhecida.
    """
    if isinstance(tamanho, bool) or not isinstance(tamanho, int):
        raise ErroImagem("E008", f"O tamanho do kernel precisa ser inteiro; veio {type(tamanho).__name__}.")
    if tamanho < 3:
        raise ErroImagem("E008", f"O tamanho do kernel precisa ser no mínimo 3; veio {tamanho}.")
    if tamanho % 2 == 0:
        raise ErroImagem("E008", f"O tamanho do kernel precisa ser ímpar; veio {tamanho}.")
    if forma not in FORMAS_KERNEL:
        disponiveis = ", ".join(sorted(FORMAS_KERNEL))
        raise ErroImagem("E008", f"Forma de kernel desconhecida: '{forma}'. Disponíveis: {disponiveis}.")

    return cv2.getStructuringElement(FORMAS_KERNEL[forma], (tamanho, tamanho))


# ---------------------------------------------------------------------------
# Primitivas
# ---------------------------------------------------------------------------

def aplicar_erosao(mascara: np.ndarray, tamanho: int = 3, forma: str = "eliptico") -> np.ndarray:
    """Erosão: encolhe o objeto.

    Mantém um pixel apenas se **toda** a vizinhança definida pelo elemento
    estruturante também for objeto.

    - **reduz** o foreground;
    - **rompe** conexões estreitas;
    - **destrói estruturas finas** — é o risco principal. Uma acícula com poucos
      pixels de largura pode desaparecer inteira.

    **Não usar isolada no pipeline sem evidência.**
    """
    validar_mascara(mascara)
    return cv2.erode(mascara, criar_kernel(tamanho, forma))


def aplicar_dilatacao(mascara: np.ndarray, tamanho: int = 3, forma: str = "eliptico") -> np.ndarray:
    """Dilatação: engorda o objeto.

    Marca um pixel se **alguma** parte da vizinhança for objeto.

    - **aumenta** o foreground;
    - **fecha** pequenos vãos;
    - **engrossa o contorno** — altera perímetro e área, e pode unir objetos
      próximos que deveriam ficar separados.

    **Não usar isolada no pipeline sem evidência.**
    """
    validar_mascara(mascara)
    return cv2.dilate(mascara, criar_kernel(tamanho, forma))


def aplicar_abertura(mascara: np.ndarray, tamanho: int = 3, forma: str = "eliptico") -> np.ndarray:
    """Abertura: erosão seguida de dilatação.

    **Hipótese:** remove pontos pequenos e ruído externo, devolvendo ao objeto
    principal aproximadamente o tamanho que tinha.

    **Risco:** o que a erosão apaga por completo, a dilatação **não traz de volta**.
    Pecíolos, pontas, acículas, serrilhas e lóbulos estreitos podem sumir.
    """
    validar_mascara(mascara)
    return cv2.morphologyEx(mascara, cv2.MORPH_OPEN, criar_kernel(tamanho, forma))


def aplicar_fechamento(mascara: np.ndarray, tamanho: int = 3, forma: str = "eliptico") -> np.ndarray:
    """Fechamento: dilatação seguida de erosão.

    **Hipótese:** preenche descontinuidades pequenas e fecha fissuras na borda.

    **Risco:** une partes que deveriam ficar separadas, preenche concavidades reais,
    e arredonda serrilhas e entalhes entre lóbulos — que são justamente a informação
    morfológica que o projeto quer medir.
    """
    validar_mascara(mascara)
    return cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, criar_kernel(tamanho, forma))


# ---------------------------------------------------------------------------
# Limpeza por componentes
# ---------------------------------------------------------------------------

def remover_componentes_pequenos(
    mascara: np.ndarray,
    fracao_minima: float = FRACAO_COMPONENTE_PEQUENO,
) -> tuple[np.ndarray, list[int]]:
    """Remove componentes desconectados muito menores que o principal.

    Tratada separadamente da abertura de propósito: a abertura remove por **forma**
    — apagando qualquer coisa mais estreita que o elemento estruturante, esteja onde
    estiver, inclusive dentro do objeto. Esta função remove por **tamanho e
    desconexão**, e **não toca em um único pixel do componente principal**.

    O critério é **relativo** à área do maior componente, e não absoluto: no conjunto
    de desenvolvimento o componente principal varia de 21.313 a 428.655 px, de modo
    que um limiar em pixels significaria coisas diferentes em imagens diferentes.

    Esta função **não decide qual objeto é a folha** — isso é da Fase 6. Ela apenas
    usa o maior componente como referência de escala para a limpeza.

    Args:
        mascara: Máscara binária válida.
        fracao_minima: Fração da área do maior componente abaixo da qual remover.

    Returns:
        ``(mascara_limpa, areas_removidas)``.

    Raises:
        ErroImagem: ``E009`` máscara inválida; ``E008`` fração fora de ``(0, 1]``.
    """
    validar_mascara(mascara)
    if isinstance(fracao_minima, bool) or not isinstance(fracao_minima, (int, float)):
        raise ErroImagem("E008", "fracao_minima precisa ser numérica.")
    if not 0 < fracao_minima <= 1:
        raise ErroImagem("E008", f"fracao_minima precisa estar em (0, 1]; veio {fracao_minima}.")

    n_rotulos, rotulos, estatisticas, _centroides = cv2.connectedComponentsWithStats(
        mascara, connectivity=8
    )
    if n_rotulos <= 2:  # fundo + no máximo um componente: nada a remover
        return mascara.copy(), []

    areas = estatisticas[1:, cv2.CC_STAT_AREA]
    area_principal = int(areas.max())
    limite = area_principal * fracao_minima

    limpa = mascara.copy()
    removidas: list[int] = []

    for indice in range(1, n_rotulos):
        area = int(estatisticas[indice, cv2.CC_STAT_AREA])
        if area == area_principal:
            continue
        if area < limite:
            limpa[rotulos == indice] = FUNDO
            removidas.append(area)

    return limpa, sorted(removidas, reverse=True)


def preencher_buracos_pequenos(
    mascara: np.ndarray,
    fracao_maxima: float = FRACAO_BURACO_PEQUENO,
) -> tuple[np.ndarray, list[int]]:
    """Preenche buracos internos pequenos, deixando os grandes intactos.

    Um buraco é uma região de fundo **totalmente cercada** pelo objeto — identificada
    como componente do fundo que não toca nenhuma borda do quadro. Conectividade 4
    para o fundo, complementar à 8 usada no objeto: é o par que evita que fundo e
    objeto sejam considerados conectados ao mesmo tempo em diagonais.

    **Preenchimento seletivo, e não indiscriminado.** Uma folha real pode ter dano,
    perfuração ou recorte, e esses buracos são informação morfológica legítima. Só os
    pequenos, atribuíveis a falha de segmentação, são preenchidos.

    **Limitação honesta:** o critério é o tamanho, e tamanho **não distingue com
    certeza** um buraco de segmentação de uma perfuração real pequena. O limiar foi
    calibrado no conjunto de desenvolvimento, onde os buracos observados vêm de
    reflexo especular.

    Args:
        mascara: Máscara binária válida.
        fracao_maxima: Fração da área do maior componente até a qual preencher.

    Returns:
        ``(mascara_preenchida, areas_preenchidas)``.

    Raises:
        ErroImagem: ``E009`` máscara inválida; ``E008`` fração fora de ``(0, 1]``.
    """
    validar_mascara(mascara)
    if isinstance(fracao_maxima, bool) or not isinstance(fracao_maxima, (int, float)):
        raise ErroImagem("E008", "fracao_maxima precisa ser numérica.")
    if not 0 < fracao_maxima <= 1:
        raise ErroImagem("E008", f"fracao_maxima precisa estar em (0, 1]; veio {fracao_maxima}.")

    n_obj, _rot_obj, stats_obj, _c = cv2.connectedComponentsWithStats(mascara, connectivity=8)
    if n_obj <= 1:  # máscara vazia
        return mascara.copy(), []

    area_principal = int(stats_obj[1:, cv2.CC_STAT_AREA].max())
    limite = area_principal * fracao_maxima

    fundo = cv2.bitwise_not(mascara)
    n_fundo, rotulos_fundo, stats_fundo, _c2 = cv2.connectedComponentsWithStats(fundo, connectivity=4)

    # Rótulos que tocam alguma borda são fundo externo, não buraco.
    externos = set(rotulos_fundo[0, :].tolist())
    externos |= set(rotulos_fundo[-1, :].tolist())
    externos |= set(rotulos_fundo[:, 0].tolist())
    externos |= set(rotulos_fundo[:, -1].tolist())

    preenchida = mascara.copy()
    preenchidos: list[int] = []

    for indice in range(1, n_fundo):
        if indice in externos:
            continue
        area = int(stats_fundo[indice, cv2.CC_STAT_AREA])
        if area < limite:
            preenchida[rotulos_fundo == indice] = OBJETO
            preenchidos.append(area)

    return preenchida, sorted(preenchidos, reverse=True)


# ---------------------------------------------------------------------------
# Comparação
# ---------------------------------------------------------------------------

def comparar_mascaras(antes: np.ndarray, depois: np.ndarray) -> dict[str, object]:
    """Mede **quanto** uma operação alterou a máscara.

    Estas métricas **não medem acerto** — não há ground truth. Elas medem
    intervenção: quanto da máscara original foi mexida. É o instrumento do princípio
    da menor intervenção.

    Args:
        antes: Máscara antes da operação.
        depois: Máscara depois.

    Returns:
        ``area_antes``, ``area_depois``, ``variacao_area_px``,
        ``variacao_area_pct``, ``intersecao_px``, ``uniao_px``, ``iou``,
        ``pixels_removidos``, ``pixels_adicionados``, ``pixels_alterados``.

    Raises:
        ErroImagem: ``E009`` se alguma máscara for inválida ou as formas diferirem.
    """
    validar_mascara(antes)
    validar_mascara(depois, forma_esperada=antes.shape)

    a = antes == OBJETO
    d = depois == OBJETO

    area_antes = int(a.sum())
    area_depois = int(d.sum())
    intersecao = int(np.logical_and(a, d).sum())
    uniao = int(np.logical_or(a, d).sum())
    removidos = int(np.logical_and(a, ~d).sum())
    adicionados = int(np.logical_and(~a, d).sum())

    return {
        "area_antes": area_antes,
        "area_depois": area_depois,
        "variacao_area_px": area_depois - area_antes,
        "variacao_area_pct": round((area_depois - area_antes) / area_antes * 100, 6) if area_antes else 0.0,
        "intersecao_px": intersecao,
        "uniao_px": uniao,
        "iou": round(intersecao / uniao, 6) if uniao else 1.0,
        "pixels_removidos": removidos,
        "pixels_adicionados": adicionados,
        "pixels_alterados": removidos + adicionados,
    }


# ---------------------------------------------------------------------------
# Limpeza
# ---------------------------------------------------------------------------

def limpar_mascara(
    mascara: np.ndarray,
    remover_pequenos: bool = True,
    preencher_buracos: bool = True,
    fracao_componente: float = FRACAO_COMPONENTE_PEQUENO,
    fracao_buraco: float = FRACAO_BURACO_PEQUENO,
    abertura: int | None = None,
    fechamento: int | None = None,
    forma_kernel: str = "eliptico",
) -> ResultadoLimpeza:
    """Aplica a limpeza da máscara e registra tudo o que foi alterado.

    Os padrões refletem a decisão medida desta fase: **remoção de componentes
    pequenos e preenchimento seletivo de buracos, sem abertura nem fechamento.**
    Abertura e fechamento continuam disponíveis por parâmetro, para experimentação —
    mas ficam desligados, porque a medição mostrou que deformam a geometria mais do
    que corrigem.

    Ordem das operações: remoção antes do preenchimento. Remover primeiro evita que
    um artefato desconectado influencie a referência de escala do preenchimento.

    Args:
        mascara: Máscara binária da segmentação.
        remover_pequenos: Remover componentes desconectados pequenos.
        preencher_buracos: Preencher buracos internos pequenos.
        fracao_componente: Limiar relativo de componente pequeno.
        fracao_buraco: Limiar relativo de buraco pequeno.
        abertura: Tamanho do kernel de abertura, ou ``None`` para não aplicar.
        fechamento: Tamanho do kernel de fechamento, ou ``None`` para não aplicar.
        forma_kernel: Forma do elemento estruturante.

    Returns:
        Resultado com máscara limpa, original, operações, parâmetros e métricas.

    Raises:
        ErroImagem: ``E009`` máscara inválida; ``E008`` parâmetro inválido.
    """
    validar_mascara(mascara)
    original = mascara.copy()
    atual = mascara.copy()

    operacoes: list[str] = []
    avisos: list[str] = []
    detalhes: dict[str, object] = {}

    if abertura is not None:
        atual = aplicar_abertura(atual, abertura, forma_kernel)
        operacoes.append(f"abertura_{abertura}")

    if fechamento is not None:
        atual = aplicar_fechamento(atual, fechamento, forma_kernel)
        operacoes.append(f"fechamento_{fechamento}")

    if remover_pequenos:
        atual, removidas = remover_componentes_pequenos(atual, fracao_componente)
        operacoes.append("remover_componentes_pequenos")
        detalhes["componentes_removidos"] = len(removidas)
        detalhes["areas_removidas"] = removidas

    if preencher_buracos:
        atual, preenchidos = preencher_buracos_pequenos(atual, fracao_buraco)
        operacoes.append("preencher_buracos_pequenos")
        detalhes["buracos_preenchidos"] = len(preenchidos)
        detalhes["areas_preenchidas"] = preenchidos

    metricas = comparar_mascaras(original, atual)
    metricas.update(detalhes)

    # Alteração acima do observado no conjunto de desenvolvimento merece atenção.
    if abs(float(metricas["variacao_area_pct"])) > 1.0:
        avisos.append("variacao_area_acima_de_1pct")
    if float(metricas["iou"]) < 0.99:
        avisos.append("iou_abaixo_de_0_99")

    return ResultadoLimpeza(
        mascara=atual,
        mascara_original=original,
        operacoes=operacoes,
        parametros={
            "remover_pequenos": remover_pequenos,
            "preencher_buracos": preencher_buracos,
            "fracao_componente": fracao_componente,
            "fracao_buraco": fracao_buraco,
            "abertura": abertura,
            "fechamento": fechamento,
            "forma_kernel": forma_kernel,
        },
        metricas=metricas,
        avisos=avisos,
    )
