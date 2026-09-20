"""Testes das estratégias de segmentação.

As imagens são sintéticas e têm resposta conhecida: sabe-se exatamente onde está o
objeto porque ele foi desenhado. Isso permite verificar a segmentação contra a
verdade, e não contra a expectativa de quem escreveu o código.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from src.preprocessing import para_cinza, suavizar_gaussiano, suavizar_mediana
from src.segmentation import (
    FAIXA_VERDE_EXPERIMENTAL,
    FUNDO,
    OBJETO,
    ResultadoSegmentacao,
    analisar_mascara,
    garantir_polaridade,
    segmentar_adaptativo,
    segmentar_combinado,
    segmentar_hsv,
    segmentar_otsu,
    toca_borda,
    validar_mascara,
)
from src.utils import ErroImagem


# ---------------------------------------------------------------------------
# Cenas sintéticas
# ---------------------------------------------------------------------------

def _folha_verde_sobre_branco(largura: int = 600, altura: int = 400) -> np.ndarray:
    """Elipse verde centrada sobre fundo branco — a condição do Flavia."""
    tela = np.full((altura, largura, 3), 250, dtype=np.uint8)
    cv2.ellipse(tela, (largura // 2, altura // 2), (160, 70), 20, 0, 360, (40, 140, 60), -1)
    return tela


def _objeto_escuro_sobre_branco() -> np.ndarray:
    tela = np.full((400, 600, 3), 245, dtype=np.uint8)
    cv2.ellipse(tela, (300, 200), (150, 60), 0, 0, 360, (30, 30, 30), -1)
    return tela


def _objeto_claro_sobre_fundo_escuro() -> np.ndarray:
    tela = np.full((400, 600, 3), 20, dtype=np.uint8)
    cv2.ellipse(tela, (300, 200), (150, 60), 0, 0, 360, (230, 230, 230), -1)
    return tela


def _folha_tocando_borda() -> np.ndarray:
    tela = np.full((400, 600, 3), 250, dtype=np.uint8)
    cv2.ellipse(tela, (560, 200), (160, 70), 0, 0, 360, (40, 140, 60), -1)
    return tela


def _duas_folhas() -> np.ndarray:
    tela = np.full((400, 600, 3), 250, dtype=np.uint8)
    cv2.ellipse(tela, (170, 200), (90, 45), 0, 0, 360, (40, 140, 60), -1)
    cv2.ellipse(tela, (430, 200), (85, 42), 0, 0, 360, (40, 140, 60), -1)
    return tela


def _folha_com_gradiente_de_iluminacao() -> np.ndarray:
    """Folha verde sobre fundo cujo brilho cai da esquerda para a direita."""
    altura, largura = 400, 600
    rampa = np.linspace(255, 140, largura, dtype=np.uint8)
    tela = cv2.merge([np.tile(rampa, (altura, 1))] * 3)
    cv2.ellipse(tela, (300, 200), (160, 70), 0, 0, 360, (40, 140, 60), -1)
    return tela


def _folha_com_sombra() -> np.ndarray:
    """Folha verde com uma sombra cinza projetada ao lado."""
    tela = np.full((400, 600, 3), 250, dtype=np.uint8)
    cv2.ellipse(tela, (330, 230), (165, 75), 15, 0, 360, (150, 150, 150), -1)  # sombra
    cv2.ellipse(tela, (300, 200), (160, 70), 15, 0, 360, (40, 140, 60), -1)    # folha
    return tela


def _folha_com_ruido() -> np.ndarray:
    gerador = np.random.default_rng(20260919)
    tela = _folha_verde_sobre_branco()
    mascara = gerador.random(tela.shape[:2])
    tela[mascara < 0.01] = 0
    tela[mascara > 0.99] = 255
    return tela


# ---------------------------------------------------------------------------
# validar_mascara
# ---------------------------------------------------------------------------

def test_mascara_binaria_valida_e_aceita() -> None:
    mascara = np.zeros((100, 100), dtype=np.uint8)
    mascara[20:60, 20:60] = OBJETO
    assert validar_mascara(mascara) is mascara


def test_mascara_com_tres_dimensoes_e_recusada() -> None:
    with pytest.raises(ErroImagem) as capturado:
        validar_mascara(np.zeros((100, 100, 3), dtype=np.uint8))
    assert capturado.value.codigo == "E009"


def test_mascara_de_dtype_errado_e_recusada() -> None:
    with pytest.raises(ErroImagem) as capturado:
        validar_mascara(np.zeros((100, 100), dtype=np.float32))
    assert capturado.value.codigo == "E009"


def test_mascara_com_valor_intermediario_e_recusada() -> None:
    mascara = np.zeros((100, 100), dtype=np.uint8)
    mascara[10, 10] = 128
    with pytest.raises(ErroImagem) as capturado:
        validar_mascara(mascara)
    assert capturado.value.codigo == "E009"


def test_mascara_vazia_e_recusada() -> None:
    with pytest.raises(ErroImagem) as capturado:
        validar_mascara(np.zeros((0, 0), dtype=np.uint8))
    assert capturado.value.codigo == "E009"


def test_forma_diferente_da_esperada_e_recusada() -> None:
    with pytest.raises(ErroImagem) as capturado:
        validar_mascara(np.zeros((50, 50), dtype=np.uint8), forma_esperada=(100, 100))
    assert capturado.value.codigo == "E009"


def test_mascara_toda_preta_ou_toda_branca_e_valida() -> None:
    """Degenerada não é inválida: é um resultado ruim, detectado pelas métricas."""
    assert validar_mascara(np.zeros((50, 50), dtype=np.uint8)) is not None
    assert validar_mascara(np.full((50, 50), OBJETO, dtype=np.uint8)) is not None


# ---------------------------------------------------------------------------
# toca_borda e analisar_mascara
# ---------------------------------------------------------------------------

def test_objeto_central_nao_toca_borda() -> None:
    mascara = np.zeros((200, 200), dtype=np.uint8)
    mascara[50:150, 50:150] = OBJETO
    assert toca_borda(mascara) is False


@pytest.mark.parametrize("fatia", ["topo", "base", "esquerda", "direita"])
def test_objeto_em_cada_borda_e_detectado(fatia: str) -> None:
    mascara = np.zeros((200, 200), dtype=np.uint8)
    if fatia == "topo":
        mascara[0:20, 80:120] = OBJETO
    elif fatia == "base":
        mascara[180:200, 80:120] = OBJETO
    elif fatia == "esquerda":
        mascara[80:120, 0:20] = OBJETO
    else:
        mascara[80:120, 180:200] = OBJETO
    assert toca_borda(mascara) is True


def test_metricas_de_mascara_conhecida() -> None:
    """Quadrado de 100x100 numa tela de 200x200: fração exata de 0,25."""
    mascara = np.zeros((200, 200), dtype=np.uint8)
    mascara[50:150, 50:150] = OBJETO

    metricas = analisar_mascara(mascara)

    assert abs(float(metricas["fracao_foreground"]) - 0.25) < 1e-6
    assert metricas["n_componentes"] == 1
    assert metricas["area_maior_componente_px"] == 10000
    assert abs(float(metricas["dominancia_maior_componente"]) - 1.0) < 1e-6
    assert metricas["toca_borda"] is False
    assert metricas["bbox_preliminar"] == {"x": 50, "y": 50, "largura": 100, "altura": 100}


def test_metricas_contam_componentes_separados() -> None:
    mascara = np.zeros((200, 200), dtype=np.uint8)
    mascara[20:60, 20:60] = OBJETO
    mascara[120:140, 120:140] = OBJETO

    metricas = analisar_mascara(mascara)

    assert metricas["n_componentes"] == 2
    assert metricas["area_maior_componente_px"] == 1600
    # 1600 de um total de 1600 + 400 = 2000
    assert abs(float(metricas["dominancia_maior_componente"]) - 0.8) < 1e-6


def test_metricas_de_mascara_vazia() -> None:
    metricas = analisar_mascara(np.zeros((100, 100), dtype=np.uint8))
    assert metricas["fracao_foreground"] == 0.0
    assert metricas["n_componentes"] == 0
    assert metricas["bbox_preliminar"] is None


# ---------------------------------------------------------------------------
# Polaridade
# ---------------------------------------------------------------------------

def test_polaridade_correta_nao_inverte() -> None:
    """Objeto no centro, borda limpa: nada a corrigir."""
    mascara = np.zeros((200, 200), dtype=np.uint8)
    mascara[60:140, 60:140] = OBJETO

    saida, invertida = garantir_polaridade(mascara)

    assert invertida is False
    assert np.array_equal(saida, mascara)


def test_polaridade_invertida_e_corrigida() -> None:
    """Fundo marcado como objeto: a borda denuncia e a máscara é invertida."""
    mascara = np.full((200, 200), OBJETO, dtype=np.uint8)
    mascara[60:140, 60:140] = FUNDO

    saida, invertida = garantir_polaridade(mascara)

    assert invertida is True
    assert int(saida[100, 100]) == OBJETO
    assert int(saida[5, 5]) == FUNDO


def test_borda_supera_ocupacao_em_objeto_grande() -> None:
    """O caso que separa os dois critérios.

    Objeto central ocupando 64% da imagem, com borda limpa. Pelo critério de
    ocupação seria invertido por engano; pelo critério de borda, não.
    """
    mascara = np.zeros((200, 200), dtype=np.uint8)
    mascara[20:180, 20:180] = OBJETO  # 160x160 = 64% de 200x200

    _, por_borda = garantir_polaridade(mascara, metodo="borda")
    _, por_ocupacao = garantir_polaridade(mascara, metodo="ocupacao")

    assert por_borda is False
    assert por_ocupacao is True


def test_metodo_de_polaridade_desconhecido_e_recusado() -> None:
    with pytest.raises(ErroImagem) as capturado:
        garantir_polaridade(np.zeros((50, 50), dtype=np.uint8), metodo="magia")
    assert capturado.value.codigo == "E008"


@pytest.mark.parametrize("espessura", [0, -1, 2.5, "5"])
def test_espessura_de_borda_invalida_e_recusada(espessura: object) -> None:
    mascara = np.zeros((50, 50), dtype=np.uint8)
    with pytest.raises(ErroImagem) as capturado:
        garantir_polaridade(mascara, espessura_borda=espessura)  # type: ignore[arg-type]
    assert capturado.value.codigo == "E008"


# ---------------------------------------------------------------------------
# Otsu
# ---------------------------------------------------------------------------

def test_otsu_encontra_objeto_escuro_sobre_branco() -> None:
    """Caso do Flavia — e o que exige inversão.

    ``THRESH_BINARY`` marca como 255 o que está **acima** do limiar, ou seja, o
    fundo branco. A correção de polaridade percebe isso pela borda e inverte.
    """
    resultado = segmentar_otsu(para_cinza(_objeto_escuro_sobre_branco()))

    validar_mascara(resultado.mascara)
    assert resultado.estrategia == "otsu"
    assert int(resultado.mascara[200, 300]) == OBJETO   # centro do objeto
    assert int(resultado.mascara[10, 10]) == FUNDO      # canto = fundo
    assert 0.05 < float(resultado.metricas["fracao_foreground"]) < 0.5
    assert resultado.parametros["invertida"] is True


def test_otsu_encontra_objeto_claro_sobre_fundo_escuro() -> None:
    """Caso oposto — e que **não** exige inversão.

    Aqui ``THRESH_BINARY`` já marca o objeto claro como 255. O par com o teste
    anterior mostra que a polaridade é decidida pela cena, e não fixada no código:
    o mesmo método produz ``invertida=True`` num caso e ``False`` no outro, com o
    objeto sempre acabando como 255.
    """
    resultado = segmentar_otsu(para_cinza(_objeto_claro_sobre_fundo_escuro()))

    assert int(resultado.mascara[200, 300]) == OBJETO
    assert int(resultado.mascara[10, 10]) == FUNDO
    assert resultado.parametros["invertida"] is False


def test_otsu_registra_o_limiar_escolhido() -> None:
    resultado = segmentar_otsu(para_cinza(_folha_verde_sobre_branco()))
    limiar = float(resultado.parametros["limiar_otsu"])
    assert 0.0 < limiar < 255.0


def test_otsu_recusa_imagem_de_tres_canais() -> None:
    with pytest.raises(ErroImagem) as capturado:
        segmentar_otsu(_folha_verde_sobre_branco())
    assert capturado.value.codigo == "E004"


def test_otsu_recusa_imagem_vazia() -> None:
    with pytest.raises(ErroImagem) as capturado:
        segmentar_otsu(np.zeros((0, 0), dtype=np.uint8))
    assert capturado.value.codigo == "E004"


def test_otsu_recusa_float() -> None:
    with pytest.raises(ErroImagem) as capturado:
        segmentar_otsu(np.zeros((100, 100), dtype=np.float32))
    assert capturado.value.codigo == "E004"


def test_otsu_e_deterministico() -> None:
    cinza = para_cinza(_folha_verde_sobre_branco())
    assert np.array_equal(segmentar_otsu(cinza).mascara, segmentar_otsu(cinza).mascara)


# ---------------------------------------------------------------------------
# HSV
# ---------------------------------------------------------------------------

def test_hsv_encontra_folha_verde() -> None:
    resultado = segmentar_hsv(_folha_verde_sobre_branco())

    validar_mascara(resultado.mascara)
    assert resultado.estrategia == "hsv"
    assert int(resultado.mascara[200, 300]) == OBJETO
    assert int(resultado.mascara[10, 10]) == FUNDO


def test_hsv_ignora_objeto_cinza() -> None:
    """A hipótese central do método: o que não é colorido não entra."""
    resultado = segmentar_hsv(_objeto_escuro_sobre_branco())
    assert float(resultado.metricas["fracao_foreground"]) < 0.01


def test_hsv_descarta_sombra_cinza() -> None:
    """A vantagem prevista sobre Otsu, verificada.

    Sombra é escura mas não é saturada — Otsu a inclui, o HSV não.
    """
    cena = _folha_com_sombra()
    fracao_otsu = float(segmentar_otsu(para_cinza(cena)).metricas["fracao_foreground"])
    fracao_hsv = float(segmentar_hsv(cena).metricas["fracao_foreground"])

    assert fracao_hsv < fracao_otsu


def test_hsv_registra_a_faixa_usada() -> None:
    resultado = segmentar_hsv(_folha_verde_sobre_branco())
    faixa = resultado.parametros["faixa"]
    assert set(faixa) == {"h", "s", "v"}  # type: ignore[arg-type]


def test_hsv_aceita_faixa_personalizada() -> None:
    faixa = {"h": (0, 179), "s": (0, 255), "v": (0, 255)}
    resultado = segmentar_hsv(_folha_verde_sobre_branco(), faixa=faixa)
    # Faixa que cobre tudo marca a imagem inteira.
    assert float(resultado.metricas["fracao_foreground"]) > 0.99


@pytest.mark.parametrize(
    "faixa",
    [
        {"h": (10, 5), "s": (0, 255), "v": (0, 255)},   # min > max
        {"s": (0, 255), "v": (0, 255)},                  # canal ausente
        {"h": ("a", 5), "s": (0, 255), "v": (0, 255)},   # tipo errado
    ],
)
def test_faixa_hsv_malformada_e_recusada(faixa: dict) -> None:
    with pytest.raises(ErroImagem) as capturado:
        segmentar_hsv(_folha_verde_sobre_branco(), faixa=faixa)
    assert capturado.value.codigo == "E008"


def test_hsv_recusa_imagem_de_um_canal() -> None:
    with pytest.raises(ErroImagem) as capturado:
        segmentar_hsv(np.zeros((100, 100), dtype=np.uint8))
    assert capturado.value.codigo == "E004"


def test_hsv_e_deterministico() -> None:
    cena = _folha_verde_sobre_branco()
    assert np.array_equal(segmentar_hsv(cena).mascara, segmentar_hsv(cena).mascara)


def test_faixa_experimental_cobre_o_verde_de_folha() -> None:
    """A faixa calibrada precisa aceitar um verde de folha típico."""
    verde = np.zeros((10, 10, 3), dtype=np.uint8)
    verde[:, :] = (40, 140, 60)
    hsv = cv2.cvtColor(verde, cv2.COLOR_BGR2HSV)
    h, s, v = (int(x) for x in hsv[5, 5])

    assert FAIXA_VERDE_EXPERIMENTAL["h"][0] <= h <= FAIXA_VERDE_EXPERIMENTAL["h"][1]
    assert FAIXA_VERDE_EXPERIMENTAL["s"][0] <= s <= FAIXA_VERDE_EXPERIMENTAL["s"][1]
    assert FAIXA_VERDE_EXPERIMENTAL["v"][0] <= v <= FAIXA_VERDE_EXPERIMENTAL["v"][1]


# ---------------------------------------------------------------------------
# Adaptativo
# ---------------------------------------------------------------------------

def test_adaptativo_produz_mascara_valida() -> None:
    resultado = segmentar_adaptativo(para_cinza(_folha_verde_sobre_branco()))
    validar_mascara(resultado.mascara)
    assert resultado.estrategia == "adaptativo"


@pytest.mark.parametrize("bloco", [2, 4, 1, 0, -3, 3.0, "51"])
def test_bloco_invalido_e_recusado(bloco: object) -> None:
    with pytest.raises(ErroImagem) as capturado:
        segmentar_adaptativo(para_cinza(_folha_verde_sobre_branco()), bloco=bloco)  # type: ignore[arg-type]
    assert capturado.value.codigo == "E008"


def test_adaptativo_recusa_tres_canais() -> None:
    with pytest.raises(ErroImagem) as capturado:
        segmentar_adaptativo(_folha_verde_sobre_branco())
    assert capturado.value.codigo == "E004"


def test_adaptativo_e_deterministico() -> None:
    cinza = para_cinza(_folha_verde_sobre_branco())
    assert np.array_equal(
        segmentar_adaptativo(cinza).mascara, segmentar_adaptativo(cinza).mascara
    )


def test_adaptativo_aceita_blocos_diferentes() -> None:
    """Blocos válidos produzem máscaras válidas, de tamanhos distintos.

    A hipótese de que o adaptativo fragmenta em região uniforme **não se confirmou
    em cena sintética** — que é limpa demais para diferenciá-lo de Otsu. A avaliação
    real está na comparação sobre o conjunto de desenvolvimento, em
    ``docs/processamento-imagens/04-SEGMENTACAO.md``.
    """
    cinza = para_cinza(_folha_verde_sobre_branco())

    for bloco in (11, 31, 51):
        resultado = segmentar_adaptativo(cinza, bloco=bloco)
        validar_mascara(resultado.mascara)
        assert resultado.parametros["bloco"] == bloco


# ---------------------------------------------------------------------------
# Combinação
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("modo", ["uniao", "intersecao"])
def test_combinado_produz_mascara_valida(modo: str) -> None:
    cena = _folha_verde_sobre_branco()
    resultado = segmentar_combinado(cena, para_cinza(cena), modo=modo)

    validar_mascara(resultado.mascara)
    assert resultado.estrategia == f"combinado_{modo}"


def test_uniao_contem_intersecao() -> None:
    """Propriedade lógica: A∩B ⊆ A∪B, sempre."""
    cena = _folha_com_sombra()
    cinza = para_cinza(cena)

    uniao = segmentar_combinado(cena, cinza, modo="uniao").mascara
    intersecao = segmentar_combinado(cena, cinza, modo="intersecao").mascara

    assert np.all(intersecao[uniao == FUNDO] == FUNDO)
    assert np.count_nonzero(uniao) >= np.count_nonzero(intersecao)


def test_modo_de_combinacao_desconhecido_e_recusado() -> None:
    cena = _folha_verde_sobre_branco()
    with pytest.raises(ErroImagem) as capturado:
        segmentar_combinado(cena, para_cinza(cena), modo="xor")
    assert capturado.value.codigo == "E008"


def test_combinado_recusa_formas_incompativeis() -> None:
    cena = _folha_verde_sobre_branco()
    cinza_menor = para_cinza(_folha_verde_sobre_branco(300, 200))
    with pytest.raises(ErroImagem) as capturado:
        segmentar_combinado(cena, cinza_menor, modo="uniao")
    assert capturado.value.codigo == "E008"


# ---------------------------------------------------------------------------
# Cenas difíceis
# ---------------------------------------------------------------------------

def test_folha_tocando_borda_e_sinalizada() -> None:
    resultado = segmentar_hsv(_folha_tocando_borda())
    assert resultado.metricas["toca_borda"] is True


def test_duas_folhas_produzem_dois_componentes() -> None:
    resultado = segmentar_hsv(_duas_folhas())
    assert int(resultado.metricas["n_componentes"]) == 2
    # Nenhuma domina: a maior fica longe de 100% do foreground.
    assert float(resultado.metricas["dominancia_maior_componente"]) < 0.8


def test_hsv_resiste_a_gradiente_de_iluminacao() -> None:
    """Matiz é estável sob variação de brilho — a razão de usar HSV."""
    resultado = segmentar_hsv(_folha_com_gradiente_de_iluminacao())
    assert int(resultado.mascara[200, 300]) == OBJETO
    assert float(resultado.metricas["dominancia_maior_componente"]) > 0.9


def test_ruido_impulsivo_fragmenta_otsu() -> None:
    """Sem filtro, o ruído vira componente — motivo de existir a etapa de filtro."""
    cinza_limpa = para_cinza(_folha_verde_sobre_branco())
    cinza_ruidosa = para_cinza(_folha_com_ruido())

    limpa = int(segmentar_otsu(cinza_limpa).metricas["n_componentes"])
    ruidosa = int(segmentar_otsu(cinza_ruidosa).metricas["n_componentes"])

    assert ruidosa > limpa * 10


def test_hsv_e_praticamente_imune_a_ruido_preto_e_branco() -> None:
    """Achado desta fase, não previsto no planejamento.

    Ruído impulsivo é preto ou branco puro — saturação zero. Como o HSV seleciona
    por matiz **e** saturação mínima, esses pixels caem fora da faixa e simplesmente
    não entram na máscara. Otsu, que decide só por intensidade, os inclui todos.

    Medido nesta cena: Otsu produz mais de mil componentes; o HSV, um.
    """
    cena = _folha_com_ruido()

    componentes_hsv = int(segmentar_hsv(cena).metricas["n_componentes"])
    componentes_otsu = int(segmentar_otsu(para_cinza(cena)).metricas["n_componentes"])

    assert componentes_hsv <= 2
    assert componentes_otsu > 100


@pytest.mark.parametrize("filtro", [suavizar_gaussiano, suavizar_mediana])
def test_filtro_reduz_fragmentacao_causada_por_ruido(filtro) -> None:
    """Sobre Otsu, que é quem sofre com o ruído (ver teste anterior)."""
    cena = _folha_com_ruido()

    sem_filtro = int(segmentar_otsu(para_cinza(cena)).metricas["n_componentes"])
    com_filtro = int(segmentar_otsu(para_cinza(filtro(cena, 5))).metricas["n_componentes"])

    assert com_filtro < sem_filtro


# ---------------------------------------------------------------------------
# Contrato de retorno
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("estrategia", ["otsu", "hsv", "adaptativo", "combinado"])
def test_todas_as_estrategias_devolvem_o_contrato(estrategia: str) -> None:
    cena = _folha_verde_sobre_branco()
    cinza = para_cinza(cena)

    if estrategia == "otsu":
        resultado = segmentar_otsu(cinza)
    elif estrategia == "hsv":
        resultado = segmentar_hsv(cena)
    elif estrategia == "adaptativo":
        resultado = segmentar_adaptativo(cinza)
    else:
        resultado = segmentar_combinado(cena, cinza)

    assert isinstance(resultado, ResultadoSegmentacao)
    assert isinstance(resultado.estrategia, str) and resultado.estrategia
    assert isinstance(resultado.parametros, dict) and resultado.parametros
    assert isinstance(resultado.avisos, list)
    validar_mascara(resultado.mascara, forma_esperada=cena.shape[:2])

    for chave in (
        "fracao_foreground",
        "n_componentes",
        "dominancia_maior_componente",
        "toca_borda",
        "bbox_preliminar",
    ):
        assert chave in resultado.metricas


@pytest.mark.parametrize("estrategia", ["otsu", "hsv", "adaptativo"])
def test_mascara_tem_a_forma_da_entrada(estrategia: str) -> None:
    cena = _folha_verde_sobre_branco(521, 337)  # dimensões ímpares, de propósito
    cinza = para_cinza(cena)

    if estrategia == "otsu":
        mascara = segmentar_otsu(cinza).mascara
    elif estrategia == "hsv":
        mascara = segmentar_hsv(cena).mascara
    else:
        mascara = segmentar_adaptativo(cinza).mascara

    assert mascara.shape == (337, 521)
