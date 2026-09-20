"""Testes das operações morfológicas e da limpeza da máscara.

As formas sintéticas têm propriedades conhecidas por construção: sabe-se exatamente
quantos pixels de largura tem uma linha, quantos dentes tem uma serrilha e qual a área
de um retângulo. Isso permite medir **numericamente** quando uma operação destrói
detalhe — em vez de julgar por aparência.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from src.morphology import (
    FRACAO_BURACO_PEQUENO,
    FRACAO_COMPONENTE_PEQUENO,
    ResultadoLimpeza,
    aplicar_abertura,
    aplicar_dilatacao,
    aplicar_erosao,
    aplicar_fechamento,
    comparar_mascaras,
    criar_kernel,
    limpar_mascara,
    preencher_buracos_pequenos,
    remover_componentes_pequenos,
)
from src.segmentation import FUNDO, OBJETO, analisar_mascara, validar_mascara
from src.utils import ErroImagem


# ---------------------------------------------------------------------------
# Máscaras sintéticas
# ---------------------------------------------------------------------------

def _circulo(raio: int = 80, lado: int = 400) -> np.ndarray:
    m = np.zeros((lado, lado), dtype=np.uint8)
    cv2.circle(m, (lado // 2, lado // 2), raio, OBJETO, -1)
    return m


def _circulo_com_ruido_externo() -> np.ndarray:
    """Círculo de raio 100 (31.417 px) com três pontos de ruído de raios 1, 2 e 3.

    O maior ponto tem 29 px, ou 0,00092 do principal — abaixo do limiar de 0,001,
    portanto removível pelo critério de componentes.
    """
    m = _circulo(raio=100)
    cv2.circle(m, (40, 40), 2, OBJETO, -1)
    cv2.circle(m, (360, 50), 3, OBJETO, -1)
    cv2.circle(m, (50, 350), 1, OBJETO, -1)
    return m


def _retangulo_com_buraco(raio: int = 4) -> np.ndarray:
    """Retângulo 200×200 (40.401 px) com buraco central.

    Raio 4 → ~49 px → 0,0012 do objeto, **abaixo** do limiar de 0,002: preenchível.
    """
    m = np.zeros((400, 400), dtype=np.uint8)
    cv2.rectangle(m, (100, 100), (300, 300), OBJETO, -1)
    cv2.circle(m, (200, 200), raio, FUNDO, -1)
    return m


def _linha_fina(espessura: int, comprimento: int = 300) -> np.ndarray:
    """Linha horizontal com espessura exata, em pixels."""
    m = np.zeros((200, 400), dtype=np.uint8)
    topo = 100 - espessura // 2
    m[topo:topo + espessura, 50:50 + comprimento] = OBJETO
    return m


def _objeto_serrilhado(n_dentes: int = 40, altura_dente: int = 3) -> np.ndarray:
    """Retângulo com dentes triangulares na borda superior.

    O padrão é **serrilha fina** — 40 dentes de 3 px —, que é a escala em que a
    morfologia de kernel 5 efetivamente deforma a borda. Dentes grossos resistem;
    ver ``test_serrilha_grossa_resiste``.
    """
    m = np.zeros((300, 400), dtype=np.uint8)
    cv2.rectangle(m, (50, 150), (350, 250), OBJETO, -1)
    largura = 300 // n_dentes
    for i in range(n_dentes):
        x = 50 + i * largura
        triangulo = np.array([[x, 150], [x + largura // 2, 150 - altura_dente], [x + largura, 150]])
        cv2.fillPoly(m, [triangulo], OBJETO)
    return m


def _dois_objetos(separacao: int) -> np.ndarray:
    m = np.zeros((300, 400), dtype=np.uint8)
    cv2.rectangle(m, (100, 100), (180, 200), OBJETO, -1)
    cv2.rectangle(m, (180 + separacao, 100), (260 + separacao, 200), OBJETO, -1)
    return m


def _sal_e_pimenta() -> np.ndarray:
    gerador = np.random.default_rng(20260920)
    m = _circulo()
    ruido = gerador.random(m.shape)
    m[ruido < 0.005] = OBJETO
    return m


def _componente_externo_pequeno(raio_ponto: int = 3) -> np.ndarray:
    """Círculo de raio 100 (31.417 px) com um ponto externo.

    Raio 3 → 29 px → 0,00092 do principal, **abaixo** do limiar de 0,001: removível.
    Raio 4 → 49 px → 0,00156, **acima**: preservado. O par demonstra que o limiar
    tem efeito, e não aprova tudo.
    """
    m = _circulo(raio=100)
    cv2.circle(m, (350, 350), raio_ponto, OBJETO, -1)
    return m


def _perimetro(mascara: np.ndarray) -> float:
    """Perímetro do maior contorno. Diagnóstico apenas — não é característica final."""
    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return max((cv2.arcLength(c, True) for c in contornos), default=0.0)


# ---------------------------------------------------------------------------
# Kernel
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("forma", ["retangular", "eliptico", "cruz"])
@pytest.mark.parametrize("tamanho", [3, 5, 7])
def test_kernel_valido(forma: str, tamanho: int) -> None:
    kernel = criar_kernel(tamanho, forma)
    assert kernel.shape == (tamanho, tamanho)
    assert kernel.dtype == np.uint8


def test_formas_de_kernel_sao_diferentes() -> None:
    """Retangular preenche tudo; cruz e elipse, não."""
    retangular = criar_kernel(5, "retangular")
    eliptico = criar_kernel(5, "eliptico")
    cruz = criar_kernel(5, "cruz")

    assert int(retangular.sum()) == 25
    assert int(cruz.sum()) < int(eliptico.sum()) < int(retangular.sum())


@pytest.mark.parametrize("tamanho", [2, 4, 1, 0, -3, 3.0, "5", True])
def test_tamanho_de_kernel_invalido(tamanho: object) -> None:
    with pytest.raises(ErroImagem) as capturado:
        criar_kernel(tamanho)  # type: ignore[arg-type]
    assert capturado.value.codigo == "E008"


def test_forma_de_kernel_desconhecida() -> None:
    with pytest.raises(ErroImagem) as capturado:
        criar_kernel(3, "hexagonal")
    assert capturado.value.codigo == "E008"


# ---------------------------------------------------------------------------
# Primitivas
# ---------------------------------------------------------------------------

def test_erosao_reduz_area() -> None:
    antes = _circulo()
    depois = aplicar_erosao(antes, 3)
    assert int(depois.sum()) < int(antes.sum())
    validar_mascara(depois)


def test_dilatacao_aumenta_area() -> None:
    antes = _circulo()
    depois = aplicar_dilatacao(antes, 3)
    assert int(depois.sum()) > int(antes.sum())
    validar_mascara(depois)


def test_erosao_e_dilatacao_sao_duais_em_area() -> None:
    """A erosão tira aproximadamente o que a dilatação põe, num objeto convexo."""
    base = _circulo(raio=100)
    perdido = int(base.sum()) - int(aplicar_erosao(base, 3).sum())
    ganho = int(aplicar_dilatacao(base, 3).sum()) - int(base.sum())
    assert abs(perdido - ganho) / max(perdido, ganho) < 0.10


def test_abertura_remove_ruido_externo_conforme_o_kernel() -> None:
    """A abertura remove ruído **por tamanho do elemento estruturante**.

    Medido: o círculo tem 3 pontos de ruído com raios 1, 2 e 3. Abertura 3×3 não
    remove nenhum; 5×5 remove dois; só 7×7 remove todos. Ou seja, para limpar por
    abertura é preciso um kernel grande — que é exatamente o que destrói detalhe fino
    (ver testes de linha e serrilha).
    """
    com_ruido = _circulo_com_ruido_externo()
    assert int(analisar_mascara(com_ruido)["n_componentes"]) == 4

    assert int(analisar_mascara(aplicar_abertura(com_ruido, 3))["n_componentes"]) == 4
    assert int(analisar_mascara(aplicar_abertura(com_ruido, 5))["n_componentes"]) == 2
    assert int(analisar_mascara(aplicar_abertura(com_ruido, 7))["n_componentes"]) == 1


def test_remocao_de_componentes_limpa_o_mesmo_ruido_sem_kernel() -> None:
    """O contraste que decide a fase.

    O mesmo ruído que exige abertura 7×7 é removido pela remoção de componentes
    **sem tocar em nenhum pixel do objeto principal**.
    """
    com_ruido = _circulo_com_ruido_externo()
    limpa, removidas = remover_componentes_pequenos(com_ruido)

    assert int(analisar_mascara(limpa)["n_componentes"]) == 1
    assert len(removidas) == 3

    assert np.array_equal(limpa, _circulo(raio=100))


def test_fechamento_fecha_fissura() -> None:
    m = _circulo(raio=100)
    m[200, 100:300] = FUNDO  # corta o círculo ao meio com 1 px
    fechada = aplicar_fechamento(m, 5)
    assert int(fechada.sum()) > int(m.sum())


@pytest.mark.parametrize("operacao", [aplicar_erosao, aplicar_dilatacao, aplicar_abertura, aplicar_fechamento])
def test_primitivas_preservam_forma_e_dtype(operacao) -> None:
    saida = operacao(_circulo(), 3)
    assert saida.shape == (400, 400)
    assert saida.dtype == np.uint8
    validar_mascara(saida)


@pytest.mark.parametrize("operacao", [aplicar_erosao, aplicar_dilatacao, aplicar_abertura, aplicar_fechamento])
def test_primitivas_sao_deterministicas(operacao) -> None:
    base = _circulo()
    assert np.array_equal(operacao(base, 5), operacao(base, 5))


@pytest.mark.parametrize("operacao", [aplicar_erosao, aplicar_dilatacao, aplicar_abertura, aplicar_fechamento])
def test_primitivas_recusam_mascara_invalida(operacao) -> None:
    with pytest.raises(ErroImagem) as capturado:
        operacao(np.zeros((100, 100, 3), dtype=np.uint8), 3)
    assert capturado.value.codigo == "E009"


# ---------------------------------------------------------------------------
# Linha fina — quando o detalhe desaparece
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("espessura", [1, 2, 3, 5])
def test_abertura_3_destroi_linhas_de_ate_2px(espessura: int) -> None:
    """Mede numericamente o limite de sobrevivência sob abertura 3×3.

    Com elemento estruturante elíptico 3×3, a erosão exige 3 px de largura para
    manter o pixel central. Linhas de 1 e 2 px são **apagadas por completo**; de 3 px
    para cima sobrevivem.
    """
    linha = _linha_fina(espessura)
    area_antes = int(np.count_nonzero(linha))
    area_depois = int(np.count_nonzero(aplicar_abertura(linha, 3)))

    if espessura <= 2:
        assert area_depois == 0, f"linha de {espessura} px deveria ser destruída"
    else:
        assert area_depois > 0, f"linha de {espessura} px não deveria sumir"
        assert area_depois / area_antes > 0.5


@pytest.mark.parametrize("espessura", [1, 2, 3, 5])
def test_abertura_5_destroi_linhas_de_ate_3px(espessura: int) -> None:
    """Abertura 5×5 é mais agressiva: elimina até 3 px, e ainda corrói a de 5."""
    linha = _linha_fina(espessura)
    area_depois = int(np.count_nonzero(aplicar_abertura(linha, 5)))

    if espessura <= 3:
        assert area_depois == 0, f"abertura 5x5 deveria destruir linha de {espessura} px"
    else:
        assert area_depois > 0


def test_fechamento_preserva_linha_fina() -> None:
    """O fechamento não destrói estrutura fina — só a engorda ou mantém."""
    for espessura in (1, 2, 3, 5):
        linha = _linha_fina(espessura)
        depois = aplicar_fechamento(linha, 5)
        assert int(np.count_nonzero(depois)) >= int(np.count_nonzero(linha))


def test_remover_componentes_preserva_linha_fina() -> None:
    """A diferença central entre remover componentes e abrir.

    A abertura apaga a linha de 1 px porque ela é **estreita**. A remoção de
    componentes a mantém intacta, porque ela é o **maior** componente — o critério é
    tamanho e desconexão, não espessura.
    """
    linha = _linha_fina(1)
    limpa, removidas = remover_componentes_pequenos(linha)

    assert np.array_equal(limpa, linha)
    assert removidas == []
    assert int(np.count_nonzero(aplicar_abertura(linha, 3))) == 0


# ---------------------------------------------------------------------------
# Serrilha
# ---------------------------------------------------------------------------

def test_abertura_e_fechamento_deformam_serrilha_fina() -> None:
    """Os dentes da borda são informação morfológica — e as duas operações os atacam.

    A abertura corta as pontas; o fechamento preenche os vales. Ambas reduzem o
    perímetro, que é a medida mais sensível à borda.

    Medido em serrilha fina (40 dentes de 3 px): o perímetro cai de ~899 para ~865
    com abertura 5×5 e ~867 com fechamento 5×5 — cerca de **4% de perda**, numa
    característica que o projeto pretende medir.
    """
    serrilhado = _objeto_serrilhado(n_dentes=40, altura_dente=3)
    perimetro_original = _perimetro(serrilhado)

    p_abertura = _perimetro(aplicar_abertura(serrilhado, 5))
    p_fechamento = _perimetro(aplicar_fechamento(serrilhado, 5))

    assert p_abertura < perimetro_original * 0.99
    assert p_fechamento < perimetro_original * 0.99


def test_serrilha_grossa_resiste() -> None:
    """A deformação depende da escala do detalhe em relação ao kernel.

    Dentes de 8 px praticamente não são afetados por kernel 5 — o que mostra que o
    risco não é universal, e sim proporcional. Registrar isso evita a conclusão
    simplista de que "morfologia sempre destrói borda".
    """
    grossa = _objeto_serrilhado(n_dentes=12, altura_dente=8)
    original = _perimetro(grossa)

    assert _perimetro(aplicar_abertura(grossa, 5)) > original * 0.99
    assert _perimetro(aplicar_fechamento(grossa, 5)) >= original * 0.99


def test_remover_componentes_nao_toca_a_serrilha() -> None:
    serrilhado = _objeto_serrilhado()
    limpa, _ = remover_componentes_pequenos(serrilhado)

    assert np.array_equal(limpa, serrilhado)
    assert _perimetro(limpa) == _perimetro(serrilhado)


def test_fechamento_une_objetos_proximos() -> None:
    """O risco do fechamento: junta o que deveria ficar separado."""
    proximos = _dois_objetos(separacao=4)
    assert int(analisar_mascara(proximos)["n_componentes"]) == 2
    assert int(analisar_mascara(aplicar_fechamento(proximos, 7))["n_componentes"]) == 1


def test_fechamento_nao_une_objetos_distantes() -> None:
    distantes = _dois_objetos(separacao=40)
    assert int(analisar_mascara(aplicar_fechamento(distantes, 7))["n_componentes"]) == 2


# ---------------------------------------------------------------------------
# Remoção de componentes
# ---------------------------------------------------------------------------

def test_remove_componente_externo_pequeno() -> None:
    m = _componente_externo_pequeno(raio_ponto=3)  # 29 px = 0,00092 do principal
    assert int(analisar_mascara(m)["n_componentes"]) == 2

    limpa, removidas = remover_componentes_pequenos(m)

    assert int(analisar_mascara(limpa)["n_componentes"]) == 1
    assert len(removidas) == 1


def test_componente_acima_do_limiar_e_preservado() -> None:
    """O limiar tem efeito nos dois sentidos — não aprova tudo.

    Raio 4 dá 49 px = 0,00156 do principal, acima do limiar de 0,001: fica.
    """
    m = _componente_externo_pequeno(raio_ponto=4)
    limpa, removidas = remover_componentes_pequenos(m)

    assert removidas == []
    assert np.array_equal(limpa, m)


def test_remocao_nao_altera_o_componente_principal() -> None:
    """A garantia mais importante desta função."""
    m = _componente_externo_pequeno()
    limpa, _ = remover_componentes_pequenos(m)

    n, rotulos, estatisticas, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    indice_maior = int(np.argmax(estatisticas[1:, cv2.CC_STAT_AREA])) + 1
    principal = (rotulos == indice_maior)

    assert np.array_equal(limpa[principal], m[principal])


def test_remocao_preserva_componente_grande() -> None:
    """Dois objetos de tamanho comparável: nenhum é artefato."""
    m = _dois_objetos(separacao=60)
    limpa, removidas = remover_componentes_pequenos(m)

    assert removidas == []
    assert np.array_equal(limpa, m)


def test_remocao_remove_ruido_salt_and_pepper() -> None:
    m = _sal_e_pimenta()
    antes = int(analisar_mascara(m)["n_componentes"])
    limpa, removidas = remover_componentes_pequenos(m)

    assert antes > 50
    assert int(analisar_mascara(limpa)["n_componentes"]) == 1
    assert len(removidas) == antes - 1


def test_remocao_em_mascara_de_um_componente_nao_faz_nada() -> None:
    m = _circulo()
    limpa, removidas = remover_componentes_pequenos(m)
    assert np.array_equal(limpa, m)
    assert removidas == []


@pytest.mark.parametrize("fracao", [0, -0.1, 1.5, "0.001", True])
def test_fracao_de_componente_invalida(fracao: object) -> None:
    with pytest.raises(ErroImagem) as capturado:
        remover_componentes_pequenos(_circulo(), fracao_minima=fracao)  # type: ignore[arg-type]
    assert capturado.value.codigo == "E008"


def test_remocao_e_deterministica() -> None:
    m = _sal_e_pimenta()
    assert np.array_equal(remover_componentes_pequenos(m)[0], remover_componentes_pequenos(m)[0])


# ---------------------------------------------------------------------------
# Preenchimento de buracos
# ---------------------------------------------------------------------------

def test_preenche_buraco_pequeno() -> None:
    m = _retangulo_com_buraco(raio=4)  # 49 px = 0,0012 do objeto
    area_antes = int(np.count_nonzero(m))

    preenchida, preenchidos = preencher_buracos_pequenos(m)

    assert len(preenchidos) == 1
    assert int(np.count_nonzero(preenchida)) - area_antes == preenchidos[0]
    assert preenchidos[0] == pytest.approx(49, abs=10)


@pytest.mark.parametrize("raio,deve_preencher", [(4, True), (6, False), (10, False), (60, False)])
def test_preenchimento_e_seletivo_por_tamanho(raio: int, deve_preencher: bool) -> None:
    """Preenchimento **seletivo**: um recorte grande pode ser estrutura real.

    Medido: raio 4 → 0,0012 (preenche); raio 6 → 0,0028; raio 10 → 0,0078;
    raio 60 → 0,28 (todos acima do limiar de 0,002, portanto preservados).
    """
    m = _retangulo_com_buraco(raio=raio)
    preenchida, preenchidos = preencher_buracos_pequenos(m)

    if deve_preencher:
        assert len(preenchidos) == 1
    else:
        assert preenchidos == []
        assert np.array_equal(preenchida, m)


def test_nao_preenche_concavidade_aberta() -> None:
    """Uma reentrância que toca a borda não é buraco — é forma."""
    m = np.zeros((300, 300), dtype=np.uint8)
    cv2.rectangle(m, (50, 50), (250, 250), OBJETO, -1)
    cv2.rectangle(m, (130, 150), (170, 260), FUNDO, -1)  # entalhe aberto na base

    preenchida, preenchidos = preencher_buracos_pequenos(m)

    assert preenchidos == []
    assert np.array_equal(preenchida, m)


def test_preenchimento_nunca_remove_pixel() -> None:
    m = _retangulo_com_buraco()
    preenchida, _ = preencher_buracos_pequenos(m)
    assert np.all(preenchida[m == OBJETO] == OBJETO)


def test_preenchimento_em_mascara_sem_buraco_nao_faz_nada() -> None:
    m = _circulo()
    preenchida, preenchidos = preencher_buracos_pequenos(m)
    assert preenchidos == []
    assert np.array_equal(preenchida, m)


def test_preenchimento_em_mascara_vazia() -> None:
    vazia = np.zeros((100, 100), dtype=np.uint8)
    preenchida, preenchidos = preencher_buracos_pequenos(vazia)
    assert preenchidos == []
    assert np.array_equal(preenchida, vazia)


@pytest.mark.parametrize("fracao", [0, -0.5, 2.0, "0.002"])
def test_fracao_de_buraco_invalida(fracao: object) -> None:
    with pytest.raises(ErroImagem) as capturado:
        preencher_buracos_pequenos(_circulo(), fracao_maxima=fracao)  # type: ignore[arg-type]
    assert capturado.value.codigo == "E008"


# ---------------------------------------------------------------------------
# comparar_mascaras
# ---------------------------------------------------------------------------

def test_comparacao_de_mascaras_identicas() -> None:
    m = _circulo()
    metricas = comparar_mascaras(m, m)

    assert metricas["iou"] == 1.0
    assert metricas["variacao_area_px"] == 0
    assert metricas["pixels_removidos"] == 0
    assert metricas["pixels_adicionados"] == 0


def test_comparacao_detecta_remocao() -> None:
    antes = _componente_externo_pequeno()
    depois, _ = remover_componentes_pequenos(antes)
    metricas = comparar_mascaras(antes, depois)

    assert metricas["pixels_removidos"] > 0
    assert metricas["pixels_adicionados"] == 0
    assert int(metricas["variacao_area_px"]) < 0  # type: ignore[arg-type]


def test_comparacao_detecta_adicao() -> None:
    antes = _retangulo_com_buraco()
    depois, _ = preencher_buracos_pequenos(antes)
    metricas = comparar_mascaras(antes, depois)

    assert metricas["pixels_adicionados"] > 0
    assert metricas["pixels_removidos"] == 0


def test_comparacao_recusa_formas_diferentes() -> None:
    with pytest.raises(ErroImagem) as capturado:
        comparar_mascaras(_circulo(lado=400), _circulo(lado=300))
    assert capturado.value.codigo == "E009"


def test_iou_de_mascaras_disjuntas_e_zero() -> None:
    a = np.zeros((200, 200), dtype=np.uint8)
    a[10:50, 10:50] = OBJETO
    b = np.zeros((200, 200), dtype=np.uint8)
    b[150:190, 150:190] = OBJETO

    assert comparar_mascaras(a, b)["iou"] == 0.0


# ---------------------------------------------------------------------------
# limpar_mascara
# ---------------------------------------------------------------------------

def test_limpeza_devolve_contrato_completo() -> None:
    resultado = limpar_mascara(_componente_externo_pequeno())

    assert isinstance(resultado, ResultadoLimpeza)
    validar_mascara(resultado.mascara)
    validar_mascara(resultado.mascara_original)
    assert resultado.operacoes
    assert resultado.parametros
    assert isinstance(resultado.avisos, list)

    for chave in ("area_antes", "area_depois", "variacao_area_pct", "iou",
                  "pixels_removidos", "pixels_adicionados", "intersecao_px", "uniao_px"):
        assert chave in resultado.metricas


def test_limpeza_padrao_nao_aplica_abertura_nem_fechamento() -> None:
    """A decisão medida desta fase, fixada em teste."""
    resultado = limpar_mascara(_circulo())

    assert not any("abertura" in op for op in resultado.operacoes)
    assert not any("fechamento" in op for op in resultado.operacoes)
    assert resultado.parametros["abertura"] is None
    assert resultado.parametros["fechamento"] is None


def test_limpeza_padrao_preserva_linha_de_1px() -> None:
    """A configuração adotada não destrói estrutura fina — ao contrário da abertura."""
    linha = _linha_fina(1)
    resultado = limpar_mascara(linha)

    assert np.array_equal(resultado.mascara, linha)
    assert resultado.metricas["pixels_alterados"] == 0


def test_limpeza_preserva_original() -> None:
    entrada = _componente_externo_pequeno()
    copia = entrada.copy()
    resultado = limpar_mascara(entrada)

    assert np.array_equal(resultado.mascara_original, copia)
    assert np.array_equal(entrada, copia)  # não mutou o argumento


def test_limpeza_remove_e_preenche() -> None:
    m = _componente_externo_pequeno(raio_ponto=3)
    cv2.circle(m, (200, 200), 4, FUNDO, -1)  # buraco de ~49 px no círculo de 31.417

    resultado = limpar_mascara(m)

    assert int(resultado.metricas["componentes_removidos"]) >= 1  # type: ignore[arg-type]
    assert int(resultado.metricas["buracos_preenchidos"]) >= 1  # type: ignore[arg-type]
    assert int(resultado.metricas["pixels_removidos"]) > 0  # type: ignore[arg-type]
    assert int(resultado.metricas["pixels_adicionados"]) > 0  # type: ignore[arg-type]


def test_limpeza_com_abertura_opcional() -> None:
    resultado = limpar_mascara(_circulo_com_ruido_externo(), abertura=5)
    assert "abertura_5" in resultado.operacoes


def test_limpeza_e_deterministica() -> None:
    m = _componente_externo_pequeno()
    assert np.array_equal(limpar_mascara(m).mascara, limpar_mascara(m).mascara)


def test_limpeza_em_mascara_ja_limpa_nao_altera_nada() -> None:
    """Menor intervenção: sem artefato, zero pixels tocados."""
    resultado = limpar_mascara(_circulo())

    assert resultado.metricas["pixels_alterados"] == 0
    assert resultado.metricas["iou"] == 1.0
    assert resultado.avisos == []


def test_limpeza_recusa_mascara_invalida() -> None:
    with pytest.raises(ErroImagem) as capturado:
        limpar_mascara(np.zeros((100, 100), dtype=np.float32))
    assert capturado.value.codigo == "E009"


def test_avisos_disparam_em_alteracao_grande() -> None:
    """Abertura agressiva num objeto pequeno deve acender os avisos."""
    resultado = limpar_mascara(_circulo(raio=20), abertura=7)

    assert abs(float(resultado.metricas["variacao_area_pct"])) > 0
    if float(resultado.metricas["iou"]) < 0.99:
        assert "iou_abaixo_de_0_99" in resultado.avisos


# ---------------------------------------------------------------------------
# Limiares calibrados
# ---------------------------------------------------------------------------

def test_limiares_estao_acima_do_maior_artefato_medido() -> None:
    """Fixa a calibração: os limiares cobrem o que foi observado no dev set.

    Maior componente pequeno medido: 0,000355 do principal.
    Maior buraco medido: 0,001105 do principal.
    """
    assert FRACAO_COMPONENTE_PEQUENO > 0.000355
    assert FRACAO_BURACO_PEQUENO > 0.001105


def test_limiares_sao_conservadores() -> None:
    """E ficam ordens de grandeza abaixo de qualquer estrutura foliar real."""
    assert FRACAO_COMPONENTE_PEQUENO < 0.01
    assert FRACAO_BURACO_PEQUENO < 0.01
