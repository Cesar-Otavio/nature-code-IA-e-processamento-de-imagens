"""Testes das características morfológicas.

As formas sintéticas têm valores **conhecidos analiticamente** — área, perímetro,
aspect ratio, extent e solidez de um retângulo ou de um círculo são calculáveis a
mão. As tolerâncias vêm das medições de discretização da Fase 6, não de ajuste
posterior.
"""

from __future__ import annotations

import math

import cv2
import numpy as np
import pytest

from src.contours import analisar_contorno
from src.features import (
    AREA_MINIMA_PX2_EXPERIMENTAL,
    CIRCULARIDADE_DE_CIRCULO_DIGITAL,
    CaracteristicasFolha,
    _dividir,
    calcular_aspect_ratio,
    calcular_circularidade,
    calcular_elongacao,
    calcular_extent,
    calcular_razao_perimetro_hull,
    calcular_solidez,
    extrair_caracteristicas,
    extrair_cor,
    para_dicionario,
)
from src.segmentation import OBJETO
from src.utils import ErroImagem


# ---------------------------------------------------------------------------
# Cenas sintéticas: máscara + imagem colorida correspondente
# ---------------------------------------------------------------------------

def _cena(mascara: np.ndarray, cor_bgr: tuple[int, int, int] = (40, 140, 60)) -> np.ndarray:
    """Imagem branca com o objeto pintado na cor indicada."""
    imagem = np.full((*mascara.shape, 3), 250, dtype=np.uint8)
    imagem[mascara == OBJETO] = cor_bgr
    return imagem


def _circulo(raio: int = 100, lado: int = 400) -> np.ndarray:
    m = np.zeros((lado, lado), dtype=np.uint8)
    cv2.circle(m, (lado // 2, lado // 2), raio, OBJETO, -1)
    return m


def _quadrado(lado_obj: int = 200, lado: int = 400) -> np.ndarray:
    m = np.zeros((lado, lado), dtype=np.uint8)
    canto = (lado - lado_obj) // 2
    cv2.rectangle(m, (canto, canto), (canto + lado_obj - 1, canto + lado_obj - 1), OBJETO, -1)
    return m


def _retangulo(largura: int = 240, altura: int = 80, lado: int = 400) -> np.ndarray:
    m = np.zeros((lado, lado), dtype=np.uint8)
    x, y = (lado - largura) // 2, (lado - altura) // 2
    cv2.rectangle(m, (x, y), (x + largura - 1, y + altura - 1), OBJETO, -1)
    return m


def _elipse(a: int = 150, b: int = 50, angulo: int = 0, lado: int = 400) -> np.ndarray:
    m = np.zeros((lado, lado), dtype=np.uint8)
    cv2.ellipse(m, (lado // 2, lado // 2), (a, b), angulo, 0, 360, OBJETO, -1)
    return m


def _estrela(pontas: int = 6, raio_ext: int = 150, raio_int: int = 60, lado: int = 400) -> np.ndarray:
    """Forma fortemente côncava — solidez baixa por construção."""
    m = np.zeros((lado, lado), dtype=np.uint8)
    centro = lado // 2
    pontos = []
    for i in range(pontas * 2):
        raio = raio_ext if i % 2 == 0 else raio_int
        angulo = math.pi * i / pontas
        pontos.append([int(centro + raio * math.cos(angulo)), int(centro + raio * math.sin(angulo))])
    cv2.fillPoly(m, [np.array(pontos)], OBJETO)
    return m


def _serrilhado(n_dentes: int = 30, altura: int = 6, lado: int = 400) -> np.ndarray:
    m = np.zeros((lado, lado), dtype=np.uint8)
    cv2.rectangle(m, (50, 150), (350, 250), OBJETO, -1)
    largura = 300 // n_dentes
    for i in range(n_dentes):
        x = 50 + i * largura
        cv2.fillPoly(m, [np.array([[x, 150], [x + largura // 2, 150 - altura], [x + largura, 150]])], OBJETO)
    return m


def _extrair(mascara: np.ndarray, cor_bgr: tuple[int, int, int] = (40, 140, 60)) -> CaracteristicasFolha:
    return extrair_caracteristicas(_cena(mascara, cor_bgr), mascara, analisar_contorno(mascara))


# ---------------------------------------------------------------------------
# Divisão segura
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("numerador,denominador", [(1.0, 0.0), (0.0, 0.0), (float("inf"), 2.0), (1.0, float("nan"))])
def test_divisao_segura_devolve_none(numerador: float, denominador: float) -> None:
    """Nenhuma característica pode sair como NaN, infinito ou zero enganoso."""
    assert _dividir(numerador, denominador) is None


def test_divisao_normal() -> None:
    assert _dividir(10.0, 4.0) == 2.5


# ---------------------------------------------------------------------------
# Fórmulas isoladas
# ---------------------------------------------------------------------------

def test_circularidade_de_circulo_teorico() -> None:
    """Com valores exatos, a fórmula dá 1,0 — o viés vem da discretização, não dela."""
    raio = 100.0
    assert calcular_circularidade(math.pi * raio ** 2, 2 * math.pi * raio) == pytest.approx(1.0, abs=1e-6)


def test_circularidade_de_quadrado_teorico() -> None:
    lado = 100.0
    assert calcular_circularidade(lado ** 2, 4 * lado) == pytest.approx(math.pi / 4, abs=1e-6)


def test_solidez_de_forma_convexa_e_um() -> None:
    assert calcular_solidez(1000.0, 1000.0) == 1.0


def test_extent_de_retangulo_e_um() -> None:
    assert calcular_extent(200.0 * 100.0, 200.0, 100.0) == 1.0


def test_extent_de_circulo_e_pi_sobre_4() -> None:
    raio = 50.0
    assert calcular_extent(math.pi * raio ** 2, 2 * raio, 2 * raio) == pytest.approx(math.pi / 4, abs=1e-4)


def test_elongacao_e_sempre_maior_ou_igual_a_um() -> None:
    assert calcular_elongacao(200.0, 50.0) == 4.0
    assert calcular_elongacao(100.0, 100.0) == 1.0


@pytest.mark.parametrize(
    "funcao,argumentos",
    [
        (calcular_circularidade, (100.0, 0.0)),
        (calcular_solidez, (100.0, 0.0)),
        (calcular_extent, (100.0, 0.0, 10.0)),
        (calcular_aspect_ratio, (100.0, 0.0)),
        (calcular_elongacao, (100.0, 0.0)),
        (calcular_razao_perimetro_hull, (100.0, 0.0)),
    ],
)
def test_formulas_com_denominador_zero(funcao, argumentos) -> None:
    assert funcao(*argumentos) is None


# ---------------------------------------------------------------------------
# Círculo
# ---------------------------------------------------------------------------

def test_circulo_tem_aspect_ratio_e_elongacao_proximos_de_um() -> None:
    f = _extrair(_circulo(raio=100)).forma
    assert f.aspect_ratio == pytest.approx(1.0, abs=0.02)
    assert f.elongacao == pytest.approx(1.0, abs=0.05)


def test_circulo_tem_solidez_proxima_de_um() -> None:
    assert _extrair(_circulo(raio=100)).forma.solidez == pytest.approx(1.0, abs=0.02)


def test_circulo_tem_extent_proximo_de_pi_sobre_quatro() -> None:
    assert _extrair(_circulo(raio=100)).forma.extent == pytest.approx(math.pi / 4, abs=0.02)


@pytest.mark.parametrize("raio", [40, 80, 160])
def test_circularidade_digital_nao_alcanca_um(raio: int) -> None:
    """A consequência do R14, agora no nível das características.

    Medido na Fase 6: converge para ~0,897. Este teste fixa que o código **não
    corrige** esse viés artificialmente.
    """
    circularidade = _extrair(_circulo(raio=raio, lado=raio * 3)).forma.circularidade

    assert circularidade is not None
    assert 0.85 < circularidade < 0.92
    assert circularidade < 1.0


def test_constante_de_referencia_bate_com_o_medido() -> None:
    medido = _extrair(_circulo(raio=160, lado=480)).forma.circularidade
    assert medido == pytest.approx(CIRCULARIDADE_DE_CIRCULO_DIGITAL, abs=0.03)


def test_circulo_tem_orientacao_nao_confiavel() -> None:
    o = _extrair(_circulo(raio=120)).orientacao
    assert o.confiavel is False
    assert o.angulo_graus is None
    assert o.anisotropia < 0.05


# ---------------------------------------------------------------------------
# Quadrado e retângulo
# ---------------------------------------------------------------------------

def test_quadrado_tem_extent_proximo_de_um() -> None:
    assert _extrair(_quadrado(200)).forma.extent == pytest.approx(1.0, abs=0.02)


def test_quadrado_tem_circularidade_proxima_de_pi_sobre_quatro() -> None:
    """Medido na Fase 6: exatamente π/4 em toda escala — os vieses se cancelam."""
    assert _extrair(_quadrado(200)).forma.circularidade == pytest.approx(math.pi / 4, abs=0.02)


def test_retangulo_tem_valores_conhecidos() -> None:
    c = _extrair(_retangulo(240, 80))

    assert c.dimensoes.largura_px == 240
    assert c.dimensoes.altura_px == 80
    assert c.dimensoes.area_contorno_px2 == pytest.approx(240 * 80, rel=0.02)
    assert c.dimensoes.perimetro_px == pytest.approx(2 * (240 + 80), rel=0.02)
    assert c.forma.aspect_ratio == pytest.approx(3.0, rel=0.02)
    assert c.forma.elongacao == pytest.approx(3.0, rel=0.05)
    assert c.forma.extent == pytest.approx(1.0, abs=0.02)
    assert c.forma.solidez == pytest.approx(1.0, abs=0.02)


def test_retangulo_vertical_tem_aspect_ratio_menor_que_um() -> None:
    """Aspect ratio distingue orientação; elongação, não."""
    c = _extrair(_retangulo(80, 240))
    assert c.forma.aspect_ratio == pytest.approx(1 / 3, rel=0.05)
    assert c.forma.elongacao == pytest.approx(3.0, rel=0.05)


# ---------------------------------------------------------------------------
# Aspect ratio vs elongação
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("angulo", [0, 30, 45, 60, 90])
def test_elongacao_e_invariante_a_rotacao(angulo: int) -> None:
    """A diferença que justifica reportar as duas medidas."""
    assert _extrair(_elipse(150, 50, angulo)).forma.elongacao == pytest.approx(3.0, rel=0.12)


def test_aspect_ratio_varia_com_a_rotacao() -> None:
    horizontal = _extrair(_elipse(150, 50, 0)).forma.aspect_ratio
    diagonal = _extrair(_elipse(150, 50, 45)).forma.aspect_ratio

    assert horizontal is not None and diagonal is not None
    assert horizontal > 2.5
    assert diagonal == pytest.approx(1.0, abs=0.15)


def test_extent_rotacionado_e_mais_estavel_que_extent() -> None:
    """Numa forma diagonal, a caixa reta é muito maior que o objeto."""
    reto = [_extrair(_elipse(150, 50, a)).forma.extent for a in (0, 45)]
    rotacionado = [_extrair(_elipse(150, 50, a)).forma.extent_rotacionado for a in (0, 45)]

    assert abs(rotacionado[0] - rotacionado[1]) < abs(reto[0] - reto[1])  # type: ignore[operator]


# ---------------------------------------------------------------------------
# Formas côncavas
# ---------------------------------------------------------------------------

def test_estrela_tem_solidez_baixa() -> None:
    f = _extrair(_estrela()).forma
    assert f.solidez is not None
    assert f.solidez < 0.6


def test_estrela_tem_circularidade_baixa() -> None:
    assert _extrair(_estrela()).forma.circularidade < 0.5  # type: ignore[operator]


def test_estrela_dispara_aviso_de_solidez_baixa() -> None:
    assert "solidez_baixa_borda_muito_recortada" in _extrair(_estrela()).avisos


def test_estrela_tem_razao_perimetro_hull_alta() -> None:
    razao = _extrair(_estrela()).convexidade.razao_perimetro_hull
    assert razao is not None and razao > 1.35


def test_razao_perimetro_hull_nao_vale_um_em_forma_convexa() -> None:
    """Achado desta fase, e a razão de a métrica continuar experimental.

    A referência intuitiva seria 1,0 para forma convexa — mas um círculo digital dá
    **≈ 1,05**. O contorno em escada é ~5% mais longo que a realidade (R14), enquanto
    o hull é um polígono de vértices que **não** tem escada. O viés do R14 entra numa
    das pontas da fração e não na outra.

    Consequência: a métrica não tem referência natural em 1,0, o que a torna menos
    interpretável que a solidez — que compara áreas, ambas sujeitas ao mesmo viés.
    """
    razao = _extrair(_circulo(raio=100)).convexidade.razao_perimetro_hull

    assert razao is not None
    assert 1.0 < razao < 1.10


def test_razao_perimetro_hull_separa_convexo_de_concavo() -> None:
    """Ainda assim discrimina — só não a partir de 1,0."""
    convexo = _extrair(_circulo(raio=100)).convexidade.razao_perimetro_hull
    concavo = _extrair(_estrela()).convexidade.razao_perimetro_hull

    assert concavo > convexo * 1.25  # type: ignore[operator]


def test_serrilha_aumenta_perimetro_sem_mudar_muito_area() -> None:
    """Assinatura da serrilha: perímetro sobe, área quase não muda, circularidade cai."""
    liso = np.zeros((400, 400), dtype=np.uint8)
    cv2.rectangle(liso, (50, 150), (350, 250), OBJETO, -1)

    c_liso = _extrair(liso)
    c_serra = _extrair(_serrilhado(n_dentes=30, altura=6))

    assert c_serra.dimensoes.perimetro_px > c_liso.dimensoes.perimetro_px
    assert c_serra.dimensoes.area_contorno_px2 == pytest.approx(c_liso.dimensoes.area_contorno_px2, rel=0.10)
    assert c_serra.forma.circularidade < c_liso.forma.circularidade  # type: ignore[operator]
    assert c_serra.convexidade.area_hull_px2 == pytest.approx(c_liso.convexidade.area_hull_px2, rel=0.10)


# ---------------------------------------------------------------------------
# Elipse: orientação e anisotropia
# ---------------------------------------------------------------------------

def test_elipse_tem_orientacao_confiavel() -> None:
    o = _extrair(_elipse(150, 50, 30)).orientacao
    assert o.confiavel is True
    assert o.angulo_graus is not None
    assert o.anisotropia > 0.5


def test_anisotropia_cresce_com_o_alongamento() -> None:
    valores = [_extrair(_elipse(a, 50)).orientacao.anisotropia for a in (55, 90, 150)]
    assert valores == sorted(valores)


def test_elipse_tem_centroide_no_centro() -> None:
    q = _extrair(_elipse(150, 50, 0, lado=400)).qualidade
    assert q.centroide_x_px == pytest.approx(200, abs=2)
    assert q.centroide_y_px == pytest.approx(200, abs=2)
    assert q.centroide_x_norm == pytest.approx(0.5, abs=0.01)


# ---------------------------------------------------------------------------
# Escala
# ---------------------------------------------------------------------------

def test_dimensoes_dependem_da_escala() -> None:
    pequeno = _extrair(_circulo(raio=50, lado=200)).dimensoes
    grande = _extrair(_circulo(raio=100, lado=400)).dimensoes

    assert grande.area_contorno_px2 > pequeno.area_contorno_px2 * 3
    assert grande.perimetro_px > pequeno.perimetro_px * 1.8


@pytest.mark.parametrize("caracteristica", ["aspect_ratio", "elongacao", "solidez", "extent"])
def test_adimensionais_sao_estaveis_com_a_escala(caracteristica: str) -> None:
    """As adimensionais são as únicas comparáveis entre imagens."""
    valores = [
        getattr(_extrair(_circulo(raio=r, lado=r * 4)).forma, caracteristica)
        for r in (40, 80, 160)
    ]
    assert max(valores) - min(valores) < 0.05


def test_circularidade_tem_leve_deriva_com_a_escala() -> None:
    """Honestidade: a circularidade **não** é perfeitamente invariante.

    Medido na Fase 6: 0,8872 em r=40 e 0,8973 em r=320. A deriva é pequena, mas
    existe — e vem do viés do perímetro, não da forma.
    """
    valores = [_extrair(_circulo(raio=r, lado=r * 4)).forma.circularidade for r in (40, 160)]
    assert valores[1] > valores[0]  # type: ignore[operator]
    assert abs(valores[1] - valores[0]) < 0.03  # type: ignore[operator]


# ---------------------------------------------------------------------------
# Cor
# ---------------------------------------------------------------------------

def test_cor_usa_apenas_pixels_da_mascara() -> None:
    """O fundo branco nunca entra na média."""
    mascara = _circulo(raio=100)
    cor = extrair_cor(_cena(mascara, (40, 140, 60)), mascara)

    assert cor.media_rgb == pytest.approx((60.0, 140.0, 40.0), abs=1.0)
    assert cor.pixels_analisados == int(np.count_nonzero(mascara))
    assert cor.pixels_analisados < mascara.size  # nem toda a imagem


def test_mediana_de_cor_resiste_a_reflexo() -> None:
    """A mediana é robusta ao brilho especular; a média, não."""
    mascara = _circulo(raio=100)
    imagem = _cena(mascara, (40, 140, 60))
    pontos = np.argwhere(mascara == OBJETO)[:2000]
    for y, x in pontos:
        imagem[y, x] = (255, 255, 255)  # reflexo

    cor = extrair_cor(imagem, mascara)

    assert cor.mediana_rgb[1] == pytest.approx(140.0, abs=2.0)
    assert cor.media_rgb[1] > cor.mediana_rgb[1]


def test_proporcao_de_verde_alta_em_objeto_verde() -> None:
    mascara = _circulo(raio=100)
    proporcao = extrair_cor(_cena(mascara, (40, 140, 60)), mascara).proporcao_verde
    assert proporcao is not None and proporcao > 0.95


def test_proporcao_de_verde_baixa_em_objeto_cinza() -> None:
    mascara = _circulo(raio=100)
    proporcao = extrair_cor(_cena(mascara, (128, 128, 128)), mascara).proporcao_verde
    assert proporcao is not None and proporcao < 0.05


def test_cor_com_mascara_vazia() -> None:
    vazia = np.zeros((100, 100), dtype=np.uint8)
    cor = extrair_cor(np.full((100, 100, 3), 250, dtype=np.uint8), vazia)

    assert cor.pixels_analisados == 0
    assert cor.proporcao_verde is None


def test_cor_recusa_imagem_de_um_canal() -> None:
    mascara = _circulo()
    with pytest.raises(ErroImagem) as capturado:
        extrair_cor(np.zeros(mascara.shape, dtype=np.uint8), mascara)
    assert capturado.value.codigo == "E004"


def test_cor_recusa_formas_incompativeis() -> None:
    mascara = _circulo(lado=400)
    with pytest.raises(ErroImagem) as capturado:
        extrair_cor(np.full((300, 300, 3), 250, dtype=np.uint8), mascara)
    assert capturado.value.codigo == "E004"


# ---------------------------------------------------------------------------
# Contrato
# ---------------------------------------------------------------------------

def test_contrato_completo() -> None:
    c = _extrair(_elipse(150, 60, 30))

    assert isinstance(c, CaracteristicasFolha)
    assert c.dimensoes.area_contorno_px2 > 0
    assert c.dimensoes.area_mascara_px2 > 0
    assert c.forma.circularidade is not None
    assert c.orientacao.anisotropia >= 0
    assert c.convexidade.area_hull_px2 > 0
    assert c.cor.pixels_analisados > 0
    assert c.qualidade.numero_contornos == 1
    assert isinstance(c.avisos, list)


def test_as_duas_areas_sao_reportadas_separadamente() -> None:
    """R22 explícito no contrato: nunca uma "área" sem dizer qual."""
    d = _extrair(_circulo(raio=100)).dimensoes

    assert d.area_contorno_px2 != float(d.area_mascara_px2)
    assert d.area_contorno_px2 < d.area_mascara_px2
    assert d.diferenca_area_px2 < 0
    assert d.diferenca_area_pct is not None and -5 < d.diferenca_area_pct < 0


def test_serializacao_sem_nan_nem_infinito() -> None:
    dados = para_dicionario(_extrair(_elipse(150, 60, 30)))

    def conferir(valor: object) -> None:
        if isinstance(valor, float):
            assert math.isfinite(valor)
        elif isinstance(valor, dict):
            for item in valor.values():
                conferir(item)
        elif isinstance(valor, list):
            for item in valor:
                conferir(item)

    conferir(dados)
    assert set(dados) == {"dimensoes", "forma", "orientacao", "convexidade", "cor", "qualidade", "avisos"}


def test_nomes_do_contrato_sao_estaveis() -> None:
    """Os nomes viajam para o JSON da API — mudá-los depois é caro."""
    dados = para_dicionario(_extrair(_circulo(raio=100)))

    for campo in ("area_contorno_px2", "area_mascara_px2", "perimetro_px", "largura_px", "altura_px"):
        assert campo in dados["dimensoes"]  # type: ignore[operator]
    for campo in ("aspect_ratio", "elongacao", "circularidade", "solidez", "extent", "extent_rotacionado"):
        assert campo in dados["forma"]  # type: ignore[operator]


def test_objeto_pequeno_demais_gera_E011() -> None:
    minusculo = np.zeros((100, 100), dtype=np.uint8)
    cv2.circle(minusculo, (50, 50), 2, OBJETO, -1)

    with pytest.raises(ErroImagem) as capturado:
        extrair_caracteristicas(_cena(minusculo), minusculo, analisar_contorno(minusculo))
    assert capturado.value.codigo == "E011"


def test_area_minima_e_configuravel() -> None:
    pequeno = np.zeros((100, 100), dtype=np.uint8)
    cv2.circle(pequeno, (50, 50), 3, OBJETO, -1)

    c = extrair_caracteristicas(_cena(pequeno), pequeno, analisar_contorno(pequeno), area_minima=1.0)
    assert c.dimensoes.area_contorno_px2 > 0


def test_aviso_de_objeto_muito_alongado() -> None:
    fino = np.zeros((400, 400), dtype=np.uint8)
    fino[198:202, 20:380] = OBJETO
    assert "objeto_muito_alongado" in _extrair(fino).avisos


def test_determinismo() -> None:
    mascara = _elipse(150, 60, 30)
    assert para_dicionario(_extrair(mascara)) == para_dicionario(_extrair(mascara))


def test_invariancia_a_translacao() -> None:
    base = np.zeros((500, 500), dtype=np.uint8)
    cv2.ellipse(base, (150, 150), (120, 50), 25, 0, 360, OBJETO, -1)
    deslocada = np.zeros((500, 500), dtype=np.uint8)
    cv2.ellipse(deslocada, (330, 330), (120, 50), 25, 0, 360, OBJETO, -1)

    a, b = _extrair(base).forma, _extrair(deslocada).forma

    for campo in ("elongacao", "circularidade", "solidez", "extent_rotacionado"):
        assert getattr(a, campo) == pytest.approx(getattr(b, campo), rel=0.03)


def test_constantes_experimentais_estao_declaradas() -> None:
    assert 0.85 < CIRCULARIDADE_DE_CIRCULO_DIGITAL < 0.95
    assert AREA_MINIMA_PX2_EXPERIMENTAL > 0
