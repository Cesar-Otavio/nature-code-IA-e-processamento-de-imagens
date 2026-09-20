"""Testes de contornos, seleção do objeto principal e geometria.

As formas sintéticas têm área, perímetro e orientação **conhecidos analiticamente**, o
que permite verificar as fórmulas contra a matemática. As tolerâncias usadas foram
**medidas antes de serem fixadas** — ver ``docs/processamento-imagens/06-CONTORNOS.md``
§16 — e não escolhidas até o teste passar.
"""

from __future__ import annotations

import math

import cv2
import numpy as np
import pytest

from src.contours import (
    METODO_APROXIMACAO,
    MODO_RECUPERACAO,
    ResultadoContorno,
    analisar_contorno,
    calcular_bbox,
    calcular_bbox_rotacionada,
    calcular_centroide,
    calcular_distancia_minima_borda,
    calcular_hull,
    calcular_orientacao,
    detectar_contornos,
    detectar_toca_borda,
    selecionar_contorno_principal,
)
from src.segmentation import OBJETO, validar_mascara
from src.utils import ErroImagem


# ---------------------------------------------------------------------------
# Formas sintéticas
# ---------------------------------------------------------------------------

def _circulo(raio: int = 80, lado: int = 400) -> np.ndarray:
    m = np.zeros((lado, lado), dtype=np.uint8)
    cv2.circle(m, (lado // 2, lado // 2), raio, OBJETO, -1)
    return m


def _quadrado(lado_obj: int = 160, lado: int = 400) -> np.ndarray:
    m = np.zeros((lado, lado), dtype=np.uint8)
    canto = (lado - lado_obj) // 2
    cv2.rectangle(m, (canto, canto), (canto + lado_obj - 1, canto + lado_obj - 1), OBJETO, -1)
    return m


def _retangulo(largura: int = 200, altura: int = 80, lado: int = 400) -> np.ndarray:
    m = np.zeros((lado, lado), dtype=np.uint8)
    x, y = (lado - largura) // 2, (lado - altura) // 2
    cv2.rectangle(m, (x, y), (x + largura - 1, y + altura - 1), OBJETO, -1)
    return m


def _elipse(a: int = 150, b: int = 60, angulo: int = 0, lado: int = 400) -> np.ndarray:
    m = np.zeros((lado, lado), dtype=np.uint8)
    cv2.ellipse(m, (lado // 2, lado // 2), (a, b), angulo, 0, 360, OBJETO, -1)
    return m


def _triangulo(lado: int = 400) -> np.ndarray:
    m = np.zeros((lado, lado), dtype=np.uint8)
    cv2.fillPoly(m, [np.array([[200, 80], [320, 300], [80, 300]])], OBJETO)
    return m


def _linha_grossa(espessura: int = 20, lado: int = 400) -> np.ndarray:
    m = np.zeros((lado, lado), dtype=np.uint8)
    m[200 - espessura // 2:200 + espessura // 2, 50:350] = OBJETO
    return m


def _objeto_tocando_borda(qual: str = "direita") -> np.ndarray:
    m = np.zeros((300, 400), dtype=np.uint8)
    if qual == "direita":
        cv2.rectangle(m, (250, 100), (399, 200), OBJETO, -1)
    elif qual == "esquerda":
        cv2.rectangle(m, (0, 100), (150, 200), OBJETO, -1)
    elif qual == "topo":
        cv2.rectangle(m, (150, 0), (250, 150), OBJETO, -1)
    else:
        cv2.rectangle(m, (150, 150), (250, 299), OBJETO, -1)
    return m


def _dois_objetos(area_menor_relativa: float) -> np.ndarray:
    """Dois retângulos; o segundo com área relativa controlada."""
    m = np.zeros((400, 600), dtype=np.uint8)
    cv2.rectangle(m, (50, 150), (250, 250), OBJETO, -1)  # 200x100 = 20.000
    lado = int(math.sqrt(20000 * area_menor_relativa))
    cv2.rectangle(m, (400, 180), (400 + lado, 180 + lado), OBJETO, -1)
    return m


def _objeto_com_buraco() -> np.ndarray:
    m = np.zeros((400, 400), dtype=np.uint8)
    cv2.rectangle(m, (100, 100), (300, 300), OBJETO, -1)
    cv2.circle(m, (200, 200), 40, 0, -1)
    return m


def _serrilhado(n_dentes: int = 20, altura: int = 6) -> np.ndarray:
    m = np.zeros((300, 400), dtype=np.uint8)
    cv2.rectangle(m, (50, 150), (350, 250), OBJETO, -1)
    largura = 300 // n_dentes
    for i in range(n_dentes):
        x = 50 + i * largura
        cv2.fillPoly(m, [np.array([[x, 150], [x + largura // 2, 150 - altura], [x + largura, 150]])], OBJETO)
    return m


def _principal(mascara: np.ndarray) -> np.ndarray:
    return selecionar_contorno_principal(detectar_contornos(mascara))[0]


# ---------------------------------------------------------------------------
# Configuração escolhida
# ---------------------------------------------------------------------------

def test_configuracao_adotada() -> None:
    """Fixa as escolhas medidas da fase."""
    assert MODO_RECUPERACAO == cv2.RETR_EXTERNAL
    assert METODO_APROXIMACAO == cv2.CHAIN_APPROX_SIMPLE


def test_simple_e_none_dao_a_mesma_geometria() -> None:
    """A justificativa de usar SIMPLE: menos pontos, geometria idêntica."""
    m = _elipse(a=150, b=60, angulo=30)

    cn, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    maior_n = max(cn, key=cv2.contourArea)
    maior_s = max(cs, key=cv2.contourArea)

    assert len(maior_s) < len(maior_n)
    assert cv2.contourArea(maior_s) == pytest.approx(cv2.contourArea(maior_n), abs=1e-6)
    assert cv2.arcLength(maior_s, True) == pytest.approx(cv2.arcLength(maior_n, True), abs=1e-4)


# ---------------------------------------------------------------------------
# Detecção e seleção
# ---------------------------------------------------------------------------

def test_detecta_um_contorno() -> None:
    assert len(detectar_contornos(_circulo())) == 1


def test_detecta_dois_contornos() -> None:
    assert len(detectar_contornos(_dois_objetos(0.3))) == 2


def test_mascara_vazia_nao_tem_contorno() -> None:
    assert detectar_contornos(np.zeros((100, 100), dtype=np.uint8)) == []


def test_selecao_em_mascara_vazia_gera_E007() -> None:
    with pytest.raises(ErroImagem) as capturado:
        selecionar_contorno_principal([])
    assert capturado.value.codigo == "E007"


def test_seleciona_o_maior_de_dois() -> None:
    contorno, diagnostico = selecionar_contorno_principal(detectar_contornos(_dois_objetos(0.1)))

    assert cv2.contourArea(contorno) == pytest.approx(20000, rel=0.02)
    assert diagnostico["numero_contornos"] == 2
    assert float(diagnostico["dominancia"]) > 0.85  # type: ignore[arg-type]


def test_objeto_muito_maior_nao_e_ambiguo() -> None:
    _, diagnostico = selecionar_contorno_principal(detectar_contornos(_dois_objetos(0.05)))
    assert "selecao_ambigua" not in diagnostico["avisos"]  # type: ignore[operator]


def test_objetos_de_tamanho_parecido_sao_ambiguos() -> None:
    """Não escolher em silêncio quando a escolha é duvidosa."""
    _, diagnostico = selecionar_contorno_principal(detectar_contornos(_dois_objetos(0.9)))

    assert "selecao_ambigua" in diagnostico["avisos"]  # type: ignore[operator]
    assert float(diagnostico["razao_segundo_primeiro"]) > 0.5  # type: ignore[arg-type]


def test_ruido_pequeno_nao_dispara_ambiguidade() -> None:
    m = _circulo(raio=100)
    cv2.circle(m, (370, 370), 3, OBJETO, -1)
    _, diagnostico = selecionar_contorno_principal(detectar_contornos(m))

    assert "selecao_ambigua" not in diagnostico["avisos"]  # type: ignore[operator]
    assert "multiplos_contornos" in diagnostico["avisos"]  # type: ignore[operator]


@pytest.mark.parametrize("razao", [0, -0.5, 1.5, "0.5", True])
def test_razao_de_ambiguidade_invalida(razao: object) -> None:
    with pytest.raises(ErroImagem) as capturado:
        selecionar_contorno_principal(detectar_contornos(_circulo()), razao_ambiguidade=razao)  # type: ignore[arg-type]
    assert capturado.value.codigo == "E008"


# ---------------------------------------------------------------------------
# Área — teórica vs digital
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raio,tolerancia_pct", [(40, 3.0), (80, 2.0), (160, 1.0)])
def test_area_de_circulo_converge_com_a_escala(raio: int, tolerancia_pct: float) -> None:
    """O erro de área **decai** com o tamanho — medido: −2,28% em r=40, −0,62% em r=160."""
    lado = raio * 3
    area_teorica = math.pi * raio ** 2
    area = cv2.contourArea(_principal(_circulo(raio, lado)))

    assert abs(area - area_teorica) / area_teorica * 100 < tolerancia_pct


def test_area_de_quadrado() -> None:
    """Medido: −1,25% em L=160. O contorno passa pelos centros dos pixels de borda."""
    area = cv2.contourArea(_principal(_quadrado(160)))
    assert abs(area - 160 ** 2) / 160 ** 2 * 100 < 2.0


def test_area_poligonal_e_menor_que_a_contagem_de_pixels() -> None:
    """Diferença sistemática, não aleatória — o contorno corta meio pixel na borda."""
    m = _circulo(raio=100)
    area_contorno = cv2.contourArea(_principal(m))
    area_pixels = int(np.count_nonzero(m))

    assert area_contorno < area_pixels
    assert (area_pixels - area_contorno) / area_pixels < 0.02


# ---------------------------------------------------------------------------
# Perímetro digital — o R14 quantificado
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raio", [20, 40, 80, 160])
def test_perimetro_de_circulo_e_superestimado(raio: int) -> None:
    """A borda em escada é mais longa que o arco que ela aproxima.

    Medido: erro entre **+4,95% e +5,41%**, aproximadamente **constante com a escala**
    — ao contrário do erro de área, que decai.
    """
    perimetro_teorico = 2 * math.pi * raio
    perimetro = cv2.arcLength(_principal(_circulo(raio, raio * 3)), True)
    erro_pct = (perimetro - perimetro_teorico) / perimetro_teorico * 100

    assert 4.0 < erro_pct < 6.5


@pytest.mark.parametrize("lado_obj", [40, 80, 160, 320])
def test_perimetro_de_quadrado_e_subestimado(lado_obj: int) -> None:
    """Sinal **oposto** ao do círculo.

    Num quadrado alinhado aos eixos não há escada, e o contorno pelos centros dos
    pixels encurta cada lado. Medido: −2,50% em L=40, −0,31% em L=320.
    """
    perimetro_teorico = 4 * lado_obj
    perimetro = cv2.arcLength(_principal(_quadrado(lado_obj, lado_obj * 2)), True)
    erro_pct = (perimetro - perimetro_teorico) / perimetro_teorico * 100

    assert -3.0 < erro_pct < 0.0


def test_circularidade_de_circulo_digital_nao_chega_a_um() -> None:
    """A consequência prática do R14, fixada em teste.

    Como o perímetro é superestimado em ~5% e entra ao quadrado, a circularidade de um
    círculo perfeito converge para ~0,90 — **não para 1,0**. Qualquer limiar definido
    na Fase 7 precisa levar isso em conta.
    """
    for raio in (80, 160, 320):
        contorno = _principal(_circulo(raio, raio * 3))
        area = cv2.contourArea(contorno)
        perimetro = cv2.arcLength(contorno, True)
        circularidade = 4 * math.pi * area / perimetro ** 2

        assert 0.85 < circularidade < 0.92


def test_circularidade_de_quadrado_e_estavel_em_toda_escala() -> None:
    """Medido: exatamente π/4 ≈ 0,7854 de L=10 a L=320.

    Os erros de área e perímetro se cancelam — o que mostra que o viés não é ruído,
    e sim consequência determinística da discretização.
    """
    valores = []
    for lado_obj in (40, 80, 160, 320):
        contorno = _principal(_quadrado(lado_obj, lado_obj * 2))
        area = cv2.contourArea(contorno)
        perimetro = cv2.arcLength(contorno, True)
        valores.append(4 * math.pi * area / perimetro ** 2)

    for valor in valores:
        assert valor == pytest.approx(math.pi / 4, abs=0.01)


# ---------------------------------------------------------------------------
# Bounding box
# ---------------------------------------------------------------------------

def test_bbox_de_retangulo() -> None:
    bbox = calcular_bbox(_principal(_retangulo(200, 80)))
    assert bbox["largura"] == 200
    assert bbox["altura"] == 80


def test_bbox_de_quadrado_e_quadrada() -> None:
    bbox = calcular_bbox(_principal(_quadrado(160)))
    assert bbox["largura"] == bbox["altura"] == 160


def test_bbox_muda_com_rotacao() -> None:
    """A caixa reta descreve o enquadramento, não a forma."""
    sem_rotacao = calcular_bbox(_principal(_elipse(150, 60, 0)))
    com_rotacao = calcular_bbox(_principal(_elipse(150, 60, 45)))

    assert sem_rotacao["largura"] > sem_rotacao["altura"]
    assert abs(com_rotacao["largura"] - com_rotacao["altura"]) < 10


# ---------------------------------------------------------------------------
# Bounding box rotacionada
# ---------------------------------------------------------------------------

def test_bbox_rotacionada_de_retangulo() -> None:
    caixa = calcular_bbox_rotacionada(_principal(_retangulo(200, 80)))
    assert caixa["lado_maior"] == pytest.approx(200, abs=3)
    assert caixa["lado_menor"] == pytest.approx(80, abs=3)


def test_lado_maior_e_sempre_o_maior() -> None:
    """A normalização que resolve a ambiguidade do OpenCV."""
    for angulo in (0, 15, 30, 45, 60, 75, 90, 120, 150):
        caixa = calcular_bbox_rotacionada(_principal(_elipse(150, 60, angulo)))
        assert caixa["lado_maior"] >= caixa["lado_menor"]  # type: ignore[operator]


def test_lados_da_bbox_rotacionada_sao_invariantes_a_rotacao() -> None:
    """Ao contrário da caixa reta, os lados da rotacionada descrevem a forma."""
    medidas = [calcular_bbox_rotacionada(_principal(_elipse(150, 60, a))) for a in (0, 30, 60, 90)]
    maiores = [float(m["lado_maior"]) for m in medidas]  # type: ignore[arg-type]
    menores = [float(m["lado_menor"]) for m in medidas]  # type: ignore[arg-type]

    assert max(maiores) - min(maiores) < 12
    assert max(menores) - min(menores) < 12


def test_angulo_normalizado_fica_em_0_180() -> None:
    for angulo in (0, 30, 45, 90, 135, 170):
        caixa = calcular_bbox_rotacionada(_principal(_elipse(150, 60, angulo)))
        assert 0 <= float(caixa["angulo_graus"]) < 180  # type: ignore[arg-type]


def test_bbox_rotacionada_guarda_o_retorno_bruto() -> None:
    """Auditabilidade: o valor original do OpenCV fica registrado."""
    caixa = calcular_bbox_rotacionada(_principal(_retangulo(200, 80)))
    for chave in ("largura_bruta", "altura_bruta", "angulo_bruto"):
        assert chave in caixa


# ---------------------------------------------------------------------------
# Centroide
# ---------------------------------------------------------------------------

def test_centroide_de_forma_centrada() -> None:
    centroide = calcular_centroide(_principal(_circulo(raio=80, lado=400)))
    assert centroide["x"] == pytest.approx(200, abs=1.5)
    assert centroide["y"] == pytest.approx(200, abs=1.5)


def test_centroide_de_retangulo_deslocado() -> None:
    m = np.zeros((400, 400), dtype=np.uint8)
    cv2.rectangle(m, (50, 100), (150, 200), OBJETO, -1)
    centroide = calcular_centroide(_principal(m))

    assert centroide["x"] == pytest.approx(100, abs=1.5)
    assert centroide["y"] == pytest.approx(150, abs=1.5)


def test_centroide_de_triangulo() -> None:
    """Centroide de triângulo = média dos vértices."""
    centroide = calcular_centroide(_principal(_triangulo()))
    assert centroide["x"] == pytest.approx((200 + 320 + 80) / 3, abs=3)
    assert centroide["y"] == pytest.approx((80 + 300 + 300) / 3, abs=4)


def test_centroide_de_contorno_degenerado_gera_E010() -> None:
    with pytest.raises(ErroImagem) as capturado:
        calcular_centroide(np.array([[[10, 10]], [[10, 20]]], dtype=np.int32))
    assert capturado.value.codigo == "E010"


# ---------------------------------------------------------------------------
# Orientação
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("angulo_desenhado", [0, 30, 60, 90, 135])
def test_orientacao_de_elipse(angulo_desenhado: int) -> None:
    """O eixo maior é detectado, a menos da periodicidade de 180°."""
    angulo, anisotropia, confiavel = calcular_orientacao(_principal(_elipse(150, 50, angulo_desenhado)))

    assert confiavel
    assert anisotropia > 0.5

    # O OpenCV desenha o ângulo em sentido horário na tela; a fórmula devolve o
    # sentido matemático. A comparação é feita módulo 180, aceitando os dois sinais.
    diferenca = min(
        abs((angulo - angulo_desenhado) % 180),
        abs((angulo + angulo_desenhado) % 180),
        180 - abs((angulo - angulo_desenhado) % 180),
        180 - abs((angulo + angulo_desenhado) % 180),
    )
    assert diferenca < 8


def test_orientacao_de_circulo_nao_e_confiavel() -> None:
    """Sem eixo dominante, o ângulo é ruído — e o código diz isso."""
    angulo, anisotropia, confiavel = calcular_orientacao(_principal(_circulo(raio=120)))

    assert not confiavel
    assert angulo is None
    assert anisotropia < 0.05


def test_orientacao_de_quadrado_nao_e_confiavel() -> None:
    _, anisotropia, confiavel = calcular_orientacao(_principal(_quadrado(160)))
    assert not confiavel
    assert anisotropia < 0.05


def test_anisotropia_cresce_com_o_alongamento() -> None:
    valores = [calcular_orientacao(_principal(_elipse(a, 50)))[1] for a in (55, 80, 120, 200)]
    assert valores == sorted(valores)
    assert valores[0] < 0.3 < valores[-1]


def test_anisotropia_esta_no_intervalo_unitario() -> None:
    for forma in (_circulo(), _quadrado(), _elipse(200, 30), _linha_grossa(), _triangulo()):
        _, anisotropia, _ = calcular_orientacao(_principal(forma))
        assert 0.0 <= anisotropia <= 1.0


def test_orientacao_de_contorno_degenerado_gera_E010() -> None:
    with pytest.raises(ErroImagem) as capturado:
        calcular_orientacao(np.array([[[10, 10]], [[10, 20]]], dtype=np.int32))
    assert capturado.value.codigo == "E010"


# ---------------------------------------------------------------------------
# Convex hull
# ---------------------------------------------------------------------------

def test_hull_de_forma_convexa_tem_area_igual() -> None:
    contorno = _principal(_circulo(raio=100))
    _, area_hull, _, _ = calcular_hull(contorno)
    assert area_hull == pytest.approx(cv2.contourArea(contorno), rel=0.01)


def test_hull_de_forma_concava_e_maior() -> None:
    contorno = _principal(_serrilhado(n_dentes=6, altura=30))
    _, area_hull, _, _ = calcular_hull(contorno)
    assert area_hull > cv2.contourArea(contorno)


def test_hull_de_quadrado_tem_quatro_vertices() -> None:
    _, _, _, pontos = calcular_hull(_principal(_quadrado(160)))
    assert pontos == 4


def test_perimetro_do_hull_nao_supera_o_do_contorno_concavo() -> None:
    """O hull corta as reentrâncias: caminho mais curto."""
    contorno = _principal(_serrilhado(n_dentes=20, altura=10))
    _, _, perimetro_hull, _ = calcular_hull(contorno)
    assert perimetro_hull < cv2.arcLength(contorno, True)


# ---------------------------------------------------------------------------
# Toca-borda
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("qual", ["topo", "base", "esquerda", "direita"])
def test_deteccao_por_lado(qual: str) -> None:
    m = _objeto_tocando_borda(qual)
    toques = detectar_toca_borda(_principal(m), m.shape)

    assert toques[qual] is True
    assert toques["qualquer"] is True


def test_objeto_central_nao_toca_borda() -> None:
    m = _circulo(raio=80, lado=400)
    toques = detectar_toca_borda(_principal(m), m.shape)

    assert toques["qualquer"] is False
    assert not any(toques[lado] for lado in ("topo", "base", "esquerda", "direita"))


def test_distancia_minima_da_borda() -> None:
    m = np.zeros((400, 400), dtype=np.uint8)
    cv2.rectangle(m, (30, 60), (300, 350), OBJETO, -1)
    assert calcular_distancia_minima_borda(_principal(m), m.shape) == 30


def test_distancia_e_zero_quando_toca() -> None:
    m = _objeto_tocando_borda("direita")
    assert calcular_distancia_minima_borda(_principal(m), m.shape) == 0


# ---------------------------------------------------------------------------
# analisar_contorno
# ---------------------------------------------------------------------------

def test_contrato_completo() -> None:
    resultado = analisar_contorno(_elipse(150, 60, 30))

    assert isinstance(resultado, ResultadoContorno)
    assert resultado.area_px2 > 0
    assert resultado.area_mascara_px > 0
    assert resultado.perimetro_px > 0
    assert set(resultado.bbox) == {"x", "y", "largura", "altura"}
    assert "lado_maior" in resultado.bbox_rotacionada
    assert set(resultado.centroide) == {"x", "y"}
    assert resultado.orientacao_confiavel is True
    assert resultado.area_hull_px2 > 0
    assert resultado.pontos_hull >= 3
    assert "qualquer" in resultado.toca_borda
    assert resultado.numero_contornos == 1
    assert isinstance(resultado.avisos, list)


def test_area_de_mascara_e_de_contorno_sao_reportadas_separadamente() -> None:
    """As duas medidas de área não são iguais — e ambas ficam registradas."""
    resultado = analisar_contorno(_circulo(raio=100))
    assert resultado.area_px2 != float(resultado.area_mascara_px)
    assert resultado.area_px2 < resultado.area_mascara_px


def test_avisos_de_borda_e_orientacao() -> None:
    resultado = analisar_contorno(_objeto_tocando_borda("direita"))
    assert "objeto_toca_borda" in resultado.avisos

    circulo = analisar_contorno(_circulo(raio=120))
    assert "orientacao_nao_confiavel" in circulo.avisos
    assert circulo.orientacao_graus is None


def test_mascara_vazia_gera_E007() -> None:
    with pytest.raises(ErroImagem) as capturado:
        analisar_contorno(np.zeros((200, 200), dtype=np.uint8))
    assert capturado.value.codigo == "E007"


def test_mascara_invalida_gera_E009() -> None:
    with pytest.raises(ErroImagem) as capturado:
        analisar_contorno(np.zeros((200, 200, 3), dtype=np.uint8))
    assert capturado.value.codigo == "E009"


def test_buraco_nao_altera_o_contorno_externo() -> None:
    """RETR_EXTERNAL ignora a cavidade — a área poligonal inclui o buraco."""
    com_buraco = analisar_contorno(_objeto_com_buraco())
    assert com_buraco.numero_contornos == 1
    assert com_buraco.area_px2 > com_buraco.area_mascara_px


def test_determinismo() -> None:
    m = _elipse(150, 60, 30)
    a, b = analisar_contorno(m), analisar_contorno(m)

    assert a.area_px2 == b.area_px2
    assert a.perimetro_px == b.perimetro_px
    assert a.centroide == b.centroide
    assert a.orientacao_graus == b.orientacao_graus
    assert np.array_equal(a.contorno, b.contorno)


def test_invariancia_a_translacao() -> None:
    """Área, perímetro e orientação não dependem de onde o objeto está."""
    base = np.zeros((500, 500), dtype=np.uint8)
    cv2.ellipse(base, (150, 150), (120, 50), 25, 0, 360, OBJETO, -1)
    deslocado = np.zeros((500, 500), dtype=np.uint8)
    cv2.ellipse(deslocado, (330, 330), (120, 50), 25, 0, 360, OBJETO, -1)

    a, b = analisar_contorno(base), analisar_contorno(deslocado)

    assert a.area_px2 == pytest.approx(b.area_px2, rel=0.01)
    assert a.perimetro_px == pytest.approx(b.perimetro_px, rel=0.01)
    assert a.orientacao_graus == pytest.approx(b.orientacao_graus, abs=2)  # type: ignore[arg-type]
    assert a.centroide != b.centroide  # o centroide, esse sim, muda
