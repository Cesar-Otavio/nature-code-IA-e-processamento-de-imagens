"""Testes das regras determinísticas de classificação morfológica.

Três grupos: as regras sobre valores diretos, as regras sobre formas sintéticas com
geometria conhecida, e as garantias de escopo — que a saída **não** contenha nada que
pareça identificação de espécie ou confiança probabilística.
"""

from __future__ import annotations

import math
from dataclasses import asdict

import cv2
import numpy as np
import pytest

from src.classification import (
    CAMPOS_PROIBIDOS,
    LIMIARES,
    ClassificacaoMorfologica,
    Limiares,
    ResultadoRegra,
    classificar_alongamento,
    classificar_compacidade,
    classificar_complexidade_borda,
    classificar_concavidade,
    classificar_morfologia,
    classificar_orientacao,
    montar_resumo,
)
from src.contours import analisar_contorno
from src.features import extrair_caracteristicas
from src.segmentation import OBJETO


# ---------------------------------------------------------------------------
# Formas sintéticas
# ---------------------------------------------------------------------------

def _cena(mascara: np.ndarray) -> np.ndarray:
    imagem = np.full((*mascara.shape, 3), 250, dtype=np.uint8)
    imagem[mascara == OBJETO] = (40, 140, 60)
    return imagem


def _classificar(mascara: np.ndarray) -> ClassificacaoMorfologica:
    caracteristicas = extrair_caracteristicas(_cena(mascara), mascara, analisar_contorno(mascara))
    return classificar_morfologia(caracteristicas)


def _circulo(raio: int = 120, lado: int = 400) -> np.ndarray:
    m = np.zeros((lado, lado), dtype=np.uint8)
    cv2.circle(m, (lado // 2, lado // 2), raio, OBJETO, -1)
    return m


def _retangulo(largura: int, altura: int, lado: int = 500) -> np.ndarray:
    m = np.zeros((lado, lado), dtype=np.uint8)
    x, y = (lado - largura) // 2, (lado - altura) // 2
    cv2.rectangle(m, (x, y), (x + largura - 1, y + altura - 1), OBJETO, -1)
    return m


def _elipse(a: int, b: int, angulo: int = 0, lado: int = 500) -> np.ndarray:
    m = np.zeros((lado, lado), dtype=np.uint8)
    cv2.ellipse(m, (lado // 2, lado // 2), (a, b), angulo, 0, 360, OBJETO, -1)
    return m


def _estrela(pontas: int = 7, raio_ext: int = 180, raio_int: int = 65, lado: int = 500) -> np.ndarray:
    """Côncava por construção — imita folha profundamente lobada."""
    m = np.zeros((lado, lado), dtype=np.uint8)
    centro = lado // 2
    pontos = []
    for i in range(pontas * 2):
        raio = raio_ext if i % 2 == 0 else raio_int
        angulo = math.pi * i / pontas
        pontos.append([int(centro + raio * math.cos(angulo)), int(centro + raio * math.sin(angulo))])
    cv2.fillPoly(m, [np.array(pontos)], OBJETO)
    return m


def _arco_alongado(lado: int = 600) -> np.ndarray:
    """Objeto muito alongado **e curvado** — solidez baixa sem recorte algum.

    Reprodução sintética da acícula ``2400``, que a Fase 7 mediu com elongação 19,94 e
    solidez 0,47. Os parâmetros foram escolhidos por medição: este arco dá **elongação
    8,00 e solidez 0,42**, caindo nas mesmas faixas do caso real.
    """
    m = np.zeros((lado, lado), dtype=np.uint8)
    cv2.ellipse(m, (lado // 2, lado // 2), (280, 280), 0, 250, 290, OBJETO, thickness=8)
    return m


# ---------------------------------------------------------------------------
# Alongamento
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "elongacao,esperado",
    [(1.0, "baixa"), (1.2, "baixa"), (1.49, "baixa"),
     (1.5, "moderada"), (2.2, "moderada"), (2.99, "moderada"),
     (3.0, "alta"), (4.5, "alta"), (5.99, "alta"),
     (6.0, "extrema"), (20.0, "extrema"), (32.6, "extrema")],
)
def test_faixas_de_alongamento(elongacao: float, esperado: str) -> None:
    assert classificar_alongamento(elongacao).categoria == esperado


@pytest.mark.parametrize("limiar", [LIMIARES.elongacao_baixa, LIMIARES.elongacao_alta, LIMIARES.elongacao_extrema])
def test_fronteiras_de_alongamento_sao_inclusivas_acima(limiar: float) -> None:
    """O valor exatamente no limiar pertence à faixa **superior**."""
    abaixo = classificar_alongamento(limiar - 0.01).categoria
    exato = classificar_alongamento(limiar).categoria
    assert abaixo != exato


def test_valor_no_limiar_e_limitrofe() -> None:
    resultado = classificar_alongamento(LIMIARES.elongacao_alta + 0.01)
    assert resultado.limitrofe is True
    assert resultado.margem_relativa is not None and resultado.margem_relativa < 0.05


def test_valor_longe_do_limiar_nao_e_limitrofe() -> None:
    assert classificar_alongamento(2.2).limitrofe is False


@pytest.mark.parametrize("valor", [None, float("nan"), float("inf"), 0.0, -3.0, 0.5])
def test_alongamento_invalido_fica_indeterminado(valor: object) -> None:
    resultado = classificar_alongamento(valor)  # type: ignore[arg-type]
    assert resultado.categoria == "indeterminado"
    assert resultado.observacoes


# ---------------------------------------------------------------------------
# Concavidade — e a ambiguidade do R25
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "solidez,esperado",
    [(0.99, "baixa"), (0.95, "baixa"), (0.92, "baixa"),
     (0.91, "moderada"), (0.80, "moderada"), (0.70, "moderada"),
     (0.69, "alta"), (0.52, "alta"), (0.30, "alta")],
)
def test_faixas_de_concavidade(solidez: float, esperado: str) -> None:
    """Com elongação moderada, a solidez decide sozinha."""
    assert classificar_concavidade(solidez, elongacao=1.5).categoria == esperado


def test_solidez_baixa_com_elongacao_extrema_e_ambigua() -> None:
    """A regra central da fase: não rotular acícula curvada como recortada.

    Reproduz `2400`: solidez 0,47 e elongação 19,94.
    """
    resultado = classificar_concavidade(solidez=0.4733, elongacao=19.94)

    assert resultado.categoria == "ambigua"
    assert resultado.observacoes
    assert "curvad" in resultado.observacoes[0] or "alongado" in resultado.observacoes[0]


def test_solidez_baixa_com_elongacao_baixa_e_alta_concavidade() -> None:
    """Reproduz `1307`: solidez 0,52 e elongação 1,14 — aí é recorte mesmo."""
    resultado = classificar_concavidade(solidez=0.5166, elongacao=1.14)

    assert resultado.categoria == "alta"
    assert resultado.observacoes == []


def test_as_duas_solidez_quase_iguais_dao_categorias_diferentes() -> None:
    """A prova de que a combinação resolve a ambiguidade.

    0,4733 e 0,5166 são quase idênticas. Sozinhas dariam a mesma resposta; com a
    elongação, dão respostas corretas e diferentes.
    """
    acicula = classificar_concavidade(0.4733, elongacao=19.94)
    lobada = classificar_concavidade(0.5166, elongacao=1.14)

    assert acicula.categoria == "ambigua"
    assert lobada.categoria == "alta"


def test_solidez_alta_com_elongacao_extrema_nao_e_ambigua() -> None:
    """A ressalva só se aplica quando a solidez é de fato baixa."""
    assert classificar_concavidade(0.98, elongacao=20.0).categoria == "baixa"


@pytest.mark.parametrize("valor", [None, float("nan"), float("inf"), -0.5, 1.5])
def test_concavidade_invalida_fica_indeterminada(valor: object) -> None:
    assert classificar_concavidade(valor, elongacao=2.0).categoria == "indeterminado"  # type: ignore[arg-type]


def test_concavidade_sem_elongacao_ainda_classifica() -> None:
    """Elongação ausente não impede a regra — só remove a ressalva."""
    resultado = classificar_concavidade(0.50, elongacao=None)
    assert resultado.categoria == "alta"


# ---------------------------------------------------------------------------
# Compacidade
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "circularidade,esperado",
    [(0.05, "baixa"), (0.30, "baixa"), (0.39, "baixa"),
     (0.40, "moderada"), (0.54, "moderada"), (0.64, "moderada"),
     (0.65, "alta"), (0.81, "alta")],
)
def test_faixas_de_compacidade(circularidade: float, esperado: str) -> None:
    assert classificar_compacidade(circularidade).categoria == esperado


def test_limiar_de_compacidade_respeita_o_teto_digital() -> None:
    """R14 explícito na regra: o limiar de "alta" não pode ser 0,9.

    O máximo observado nas 64 folhas é 0,8143. Um limiar de 0,9 classificaria nenhuma
    folha como compacta.
    """
    assert LIMIARES.circularidade_alta < 0.90
    assert classificar_compacidade(0.8143).categoria == "alta"


def test_compacidade_traz_a_ressalva_do_teto_digital() -> None:
    assert any("0,90" in obs or "teto" in obs for obs in classificar_compacidade(0.5).observacoes)


@pytest.mark.parametrize("valor", [None, float("nan"), -0.1, 1.2])
def test_compacidade_invalida_fica_indeterminada(valor: object) -> None:
    assert classificar_compacidade(valor).categoria == "indeterminado"  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Complexidade de borda
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "razao,esperado",
    [(1.05, "regular"), (1.10, "regular"), (1.12, "regular"),
     (1.13, "moderada"), (1.25, "moderada"),
     (1.30, "complexa"), (2.02, "complexa")],
)
def test_faixas_de_complexidade(razao: float, esperado: str) -> None:
    assert classificar_complexidade_borda(razao).categoria == esperado


def test_complexidade_declara_que_e_experimental() -> None:
    observacoes = classificar_complexidade_borda(1.10).observacoes
    assert any("experimental" in obs for obs in observacoes)
    assert any("1,05" in obs for obs in observacoes)


@pytest.mark.parametrize("valor", [None, float("nan"), 0.5, -1.0])
def test_complexidade_invalida_fica_indeterminada(valor: object) -> None:
    assert classificar_complexidade_borda(valor).categoria == "indeterminado"  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Orientação
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "anisotropia,esperado",
    [(0.01, "indefinida"), (0.049, "indefinida"),
     (0.05, "pouco_definida"), (0.15, "pouco_definida"), (0.29, "pouco_definida"),
     (0.30, "bem_definida"), (0.63, "bem_definida"), (0.99, "bem_definida")],
)
def test_faixas_de_orientacao(anisotropia: float, esperado: str) -> None:
    assert classificar_orientacao(45.0, anisotropia).categoria == esperado


def test_caso_1177_fica_pouco_definida() -> None:
    """`1177` tem anisotropia 0,0540 — acima do limiar de confiabilidade por 0,004.

    A categoria captura a fragilidade, e a observação a explica.
    """
    resultado = classificar_orientacao(78.3, 0.0540)

    assert resultado.categoria == "pouco_definida"
    assert resultado.observacoes
    assert "fraco" in resultado.observacoes[0]


def test_margem_relativa_exagera_a_folga_em_limiar_pequeno() -> None:
    """Limitação conhecida da margem relativa, registrada em teste.

    `1177` está a **0,004 em valor absoluto** do limiar de 0,05 — intuitivamente
    limítrofe. Mas 0,004 são **8% de 0,05**, acima do critério de 5%, e por isso o
    caso **não** é marcado como limítrofe.

    A margem relativa é adequada para limiares de magnitude comparável entre si
    (elongação 1,5/3,0/6,0), e **exagera a folga quando o limiar é pequeno em valor
    absoluto**. Está documentado em vez de contornado com uma exceção ad hoc — que
    seria um limiar a mais para ajustar.
    """
    resultado = classificar_orientacao(78.3, 0.0540)

    assert resultado.margem_relativa == pytest.approx(0.08, abs=0.001)
    assert resultado.limitrofe is False
    assert abs(0.0540 - LIMIARES.anisotropia_minima) < 0.005  # absoluto: é limítrofe


def test_orientacao_nao_classifica_direcao() -> None:
    """O ângulo é pose, não forma — a categoria nunca descreve direção."""
    for angulo in (0.0, 45.0, 90.0, 135.0, 179.0):
        categoria = classificar_orientacao(angulo, 0.8).categoria
        assert categoria == "bem_definida"
        for palavra in ("horizontal", "vertical", "diagonal"):
            assert palavra not in categoria


def test_angulo_e_reportado_mas_nao_decide() -> None:
    resultado = classificar_orientacao(78.3, 0.8)
    assert resultado.valores["angulo_graus"] == 78.3
    assert "anisotropia" in resultado.features_usadas


def test_orientacao_com_angulo_none_ainda_classifica() -> None:
    """Quando a Fase 6 devolve `None`, a anisotropia ainda decide a categoria."""
    assert classificar_orientacao(None, 0.02).categoria == "indefinida"


@pytest.mark.parametrize("valor", [None, float("nan"), -0.1, 1.5])
def test_orientacao_com_anisotropia_invalida(valor: object) -> None:
    assert classificar_orientacao(45.0, valor).categoria == "indeterminado"  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Formas sintéticas — geometria conhecida
# ---------------------------------------------------------------------------

def test_circulo() -> None:
    c = _classificar(_circulo(raio=120))

    assert c.alongamento.categoria == "baixa"
    assert c.concavidade.categoria == "baixa"
    assert c.compacidade.categoria == "alta"
    assert c.orientacao.categoria == "indefinida"


def test_retangulo_2_para_1() -> None:
    c = _classificar(_retangulo(300, 150))
    assert c.alongamento.categoria == "moderada"
    assert c.concavidade.categoria == "baixa"


def test_retangulo_5_para_1() -> None:
    c = _classificar(_retangulo(400, 80))
    assert c.alongamento.categoria == "alta"
    assert c.concavidade.categoria == "baixa"


def test_elipse_alongada() -> None:
    c = _classificar(_elipse(200, 40))
    assert c.alongamento.categoria in ("alta", "extrema")
    assert c.orientacao.categoria == "bem_definida"


def test_estrela_tem_concavidade_alta_e_borda_complexa() -> None:
    c = _classificar(_estrela())

    assert c.concavidade.categoria == "alta"
    assert c.complexidade_borda.categoria == "complexa"
    assert c.compacidade.categoria == "baixa"


def test_arco_alongado_e_caso_ambiguo() -> None:
    """A forma sintética que reproduz a acícula curvada.

    Elongação extrema **e** solidez baixa — a regra deve reconhecer a ambiguidade em
    vez de afirmar recorte.
    """
    c = _classificar(_arco_alongado())

    assert c.alongamento.categoria == "extrema"
    assert c.concavidade.categoria == "ambigua"
    assert any("ambigua" in aviso for aviso in c.avisos)


def test_objeto_quase_circular() -> None:
    c = _classificar(_elipse(150, 145))
    assert c.alongamento.categoria == "baixa"
    assert c.orientacao.categoria in ("indefinida", "pouco_definida")


# ---------------------------------------------------------------------------
# Contrato e auditabilidade
# ---------------------------------------------------------------------------

def test_toda_regra_e_auditavel() -> None:
    c = _classificar(_elipse(200, 60))

    for regra in (c.alongamento, c.concavidade, c.compacidade, c.complexidade_borda, c.orientacao):
        assert isinstance(regra, ResultadoRegra)
        assert regra.atributo
        assert regra.categoria
        assert regra.features_usadas, f"{regra.atributo} não declara as features usadas"
        assert regra.valores, f"{regra.atributo} não reporta os valores observados"
        if regra.categoria != "indeterminado":
            assert regra.limiares_aplicados, f"{regra.atributo} não reporta os limiares"


def test_nunca_retorna_apenas_a_categoria() -> None:
    """A exigência central: categoria sempre vem com evidência."""
    regra = classificar_alongamento(4.8)

    assert regra.categoria == "alta"
    assert regra.valores["elongacao"] == 4.8
    assert regra.limiares_aplicados["alta_a_partir_de"] == LIMIARES.elongacao_alta


def test_resumo_e_montado_das_categorias() -> None:
    c = _classificar(_elipse(200, 50))

    assert isinstance(c.resumo, str)
    assert c.resumo.endswith(".")
    assert "Folha" in c.resumo


def test_resumo_muda_quando_a_categoria_muda() -> None:
    """Prova que o texto é composição de regras, não geração."""
    a = montar_resumo(
        classificar_alongamento(1.1), classificar_concavidade(0.99, 1.1),
        classificar_compacidade(0.70), classificar_orientacao(0.0, 0.01),
    )
    b = montar_resumo(
        classificar_alongamento(20.0), classificar_concavidade(0.99, 20.0),
        classificar_compacidade(0.10), classificar_orientacao(45.0, 0.99),
    )
    assert a != b


def test_aviso_de_nao_identificacao_sempre_presente() -> None:
    c = _classificar(_circulo())
    assert any("nao constitui identificacao botanica" in aviso for aviso in c.avisos)


def test_determinismo() -> None:
    mascara = _elipse(200, 60, 30)
    assert asdict(_classificar(mascara)) == asdict(_classificar(mascara))


def test_limiares_sao_configuraveis() -> None:
    """Os limiares não estão espalhados como números mágicos."""
    frouxos = Limiares(elongacao_baixa=10.0, elongacao_alta=20.0, elongacao_extrema=30.0)
    assert classificar_alongamento(5.0, frouxos).categoria == "baixa"
    assert classificar_alongamento(5.0, LIMIARES).categoria == "alta"


# ---------------------------------------------------------------------------
# Escopo — o que a saída NÃO pode conter
# ---------------------------------------------------------------------------

def _achatar(objeto: object, prefixo: str = "") -> list[str]:
    """Todas as chaves de um dicionário aninhado."""
    chaves: list[str] = []
    if isinstance(objeto, dict):
        for chave, valor in objeto.items():
            chaves.append(str(chave).lower())
            chaves.extend(_achatar(valor, prefixo))
    elif isinstance(objeto, (list, tuple)):
        for item in objeto:
            chaves.extend(_achatar(item, prefixo))
    return chaves


def test_saida_nao_contem_campo_de_especie_nem_de_confianca() -> None:
    """Isolamento semântico: a saída não pode parecer identificação nem probabilidade."""
    dados = asdict(_classificar(_elipse(200, 60)))
    chaves = set(_achatar(dados))

    proibidos = chaves & CAMPOS_PROIBIDOS
    assert not proibidos, f"campos proibidos na saída: {sorted(proibidos)}"


def test_nenhuma_categoria_e_nome_botanico() -> None:
    """As categorias são geométricas, não taxonômicas."""
    termos = {"ovada", "lanceolada", "cordiforme", "eliptica", "acicular", "obovada",
              "espatulada", "reniforme", "sagitada", "peltada"}
    c = _classificar(_elipse(200, 60))

    for regra in (c.alongamento, c.concavidade, c.compacidade, c.complexidade_borda, c.orientacao):
        assert regra.categoria.lower() not in termos


def test_resumo_nao_promete_identificacao() -> None:
    resumo = _classificar(_elipse(200, 60)).resumo.lower()
    for termo in ("especie", "espécie", "genero", "gênero", "planta é", "identificad"):
        assert termo not in resumo


def test_margem_nao_e_confianca() -> None:
    """`margem_relativa` é distância ao limiar, e o nome do campo diz isso."""
    regra = classificar_alongamento(4.8)

    assert regra.margem_relativa is not None
    assert not hasattr(regra, "confianca")
    assert not hasattr(regra, "probabilidade")
    assert not hasattr(regra, "score")


def test_numero_de_regras_e_pequeno() -> None:
    """Cinco atributos, poucos limiares — sem superajuste às 64 imagens."""
    limiares = asdict(LIMIARES)
    assert len(limiares) <= 12, f"{len(limiares)} limiares é sinal de superajuste"
