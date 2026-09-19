"""Testes de redimensionamento, espaços de cor e filtros de suavização."""

from __future__ import annotations

import numpy as np
import pytest

from src.preprocessing import (
    KERNEL_MINIMO,
    LADO_MAXIMO_PX_EXPERIMENTAL,
    para_cinza,
    para_hsv,
    para_rgb,
    redimensionar,
    suavizar_gaussiano,
    suavizar_mediana,
)
from src.utils import ErroImagem


# ---------------------------------------------------------------------------
# Redimensionamento
# ---------------------------------------------------------------------------

def test_redimensionamento_preserva_proporcao() -> None:
    entrada = np.zeros((1200, 1600, 3), dtype=np.uint8)
    saida, info = redimensionar(entrada, lado_maximo=800)

    proporcao_original = 1600 / 1200
    proporcao_final = saida.shape[1] / saida.shape[0]

    assert abs(proporcao_original - proporcao_final) < 0.01
    assert max(saida.shape[:2]) == 800
    assert info["redimensionada"] is True


@pytest.mark.parametrize("dimensoes", [(1200, 1600), (1600, 1200), (900, 900), (300, 2000)])
def test_proporcao_preservada_em_varias_formas(dimensoes: tuple[int, int]) -> None:
    altura, largura = dimensoes
    saida, _ = redimensionar(np.zeros((altura, largura, 3), dtype=np.uint8), lado_maximo=512)
    assert abs((largura / altura) - (saida.shape[1] / saida.shape[0])) < 0.02


def test_imagem_menor_nao_e_ampliada_por_padrao() -> None:
    entrada = np.zeros((200, 300, 3), dtype=np.uint8)
    saida, info = redimensionar(entrada, lado_maximo=1024)

    assert saida.shape == entrada.shape
    assert info["redimensionada"] is False
    assert info["fator_escala"] == 1.0


def test_ampliacao_acontece_quando_pedida() -> None:
    entrada = np.zeros((200, 300, 3), dtype=np.uint8)
    saida, info = redimensionar(entrada, lado_maximo=900, ampliar=True)

    assert max(saida.shape[:2]) == 900
    assert info["redimensionada"] is True


def test_info_traz_dimensoes_antes_e_depois() -> None:
    _, info = redimensionar(np.zeros((1200, 1600, 3), dtype=np.uint8), lado_maximo=800)

    assert info["largura_original_px"] == 1600
    assert info["altura_original_px"] == 1200
    assert info["largura_px"] == 800
    assert info["altura_px"] == 600
    assert 0.0 < float(info["fator_escala"]) < 1.0  # type: ignore[arg-type]


def test_redimensionamento_preserva_canais() -> None:
    colorida, _ = redimensionar(np.zeros((800, 800, 3), dtype=np.uint8), lado_maximo=200)
    cinza, _ = redimensionar(np.zeros((800, 800), dtype=np.uint8), lado_maximo=200)

    assert colorida.ndim == 3 and colorida.shape[2] == 3
    assert cinza.ndim == 2


def test_redimensionamento_e_deterministico(imagem_folha_sintetica: np.ndarray) -> None:
    primeira, _ = redimensionar(imagem_folha_sintetica, lado_maximo=256)
    segunda, _ = redimensionar(imagem_folha_sintetica, lado_maximo=256)
    assert np.array_equal(primeira, segunda)


@pytest.mark.parametrize("valor", [0, -100, 3.5, "512", True])
def test_lado_maximo_invalido_gera_E008(valor: object) -> None:
    with pytest.raises(ErroImagem) as capturado:
        redimensionar(np.zeros((200, 300, 3), dtype=np.uint8), lado_maximo=valor)  # type: ignore[arg-type]
    assert capturado.value.codigo == "E008"


def test_imagem_vazia_no_redimensionamento_gera_E004() -> None:
    with pytest.raises(ErroImagem) as capturado:
        redimensionar(np.zeros((0, 0, 3), dtype=np.uint8))
    assert capturado.value.codigo == "E004"


def test_lado_maximo_padrao_e_o_experimental() -> None:
    entrada = np.zeros((1200, 1600, 3), dtype=np.uint8)
    saida, _ = redimensionar(entrada)
    assert max(saida.shape[:2]) == LADO_MAXIMO_PX_EXPERIMENTAL


# ---------------------------------------------------------------------------
# Espaços de cor
# ---------------------------------------------------------------------------

def test_bgr_para_rgb_troca_os_canais_extremos() -> None:
    tela = np.zeros((10, 10, 3), dtype=np.uint8)
    tela[:, :] = (255, 0, 0)  # BGR: azul puro

    rgb = para_rgb(tela)
    r, g, b = rgb[5, 5]

    assert (int(r), int(g), int(b)) == (0, 0, 255)
    assert rgb.shape == tela.shape


def test_rgb_e_involutivo() -> None:
    """Converter duas vezes devolve o original."""
    original = np.zeros((10, 10, 3), dtype=np.uint8)
    original[:, :] = (30, 90, 200)
    assert np.array_equal(para_rgb(para_rgb(original)), original)


def test_grayscale_tem_um_canal(imagem_folha_sintetica: np.ndarray) -> None:
    cinza = para_cinza(imagem_folha_sintetica)

    assert cinza.ndim == 2
    assert cinza.shape == imagem_folha_sintetica.shape[:2]
    assert cinza.dtype == np.uint8


def test_grayscale_de_branco_e_255_e_de_preto_e_0() -> None:
    branco = np.full((10, 10, 3), 255, dtype=np.uint8)
    preto = np.zeros((10, 10, 3), dtype=np.uint8)

    assert int(para_cinza(branco)[5, 5]) == 255
    assert int(para_cinza(preto)[5, 5]) == 0


def test_grayscale_pondera_mais_o_verde() -> None:
    """A conversão segue a sensibilidade do olho: verde pesa mais que azul."""
    verde = np.zeros((10, 10, 3), dtype=np.uint8)
    verde[:, :] = (0, 255, 0)
    azul = np.zeros((10, 10, 3), dtype=np.uint8)
    azul[:, :] = (255, 0, 0)

    assert int(para_cinza(verde)[5, 5]) > int(para_cinza(azul)[5, 5])


def test_hsv_tem_tres_canais(imagem_folha_sintetica: np.ndarray) -> None:
    hsv = para_hsv(imagem_folha_sintetica)
    assert hsv.shape == imagem_folha_sintetica.shape
    assert hsv.dtype == np.uint8


def test_hsv_respeita_os_intervalos_do_opencv(imagem_folha_sintetica: np.ndarray) -> None:
    """No OpenCV, H vai de 0 a 179 — e não de 0 a 359."""
    hsv = para_hsv(imagem_folha_sintetica)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

    assert 0 <= int(h.min()) and int(h.max()) <= 179
    assert 0 <= int(s.min()) and int(s.max()) <= 255
    assert 0 <= int(v.min()) and int(v.max()) <= 255


def test_hsv_isola_matiz_da_iluminacao() -> None:
    """Dois verdes de brilho diferente mantêm o mesmo matiz."""
    claro = np.zeros((10, 10, 3), dtype=np.uint8)
    claro[:, :] = (0, 200, 0)
    escuro = np.zeros((10, 10, 3), dtype=np.uint8)
    escuro[:, :] = (0, 80, 0)

    h_claro = int(para_hsv(claro)[5, 5, 0])
    h_escuro = int(para_hsv(escuro)[5, 5, 0])
    v_claro = int(para_hsv(claro)[5, 5, 2])
    v_escuro = int(para_hsv(escuro)[5, 5, 2])

    assert h_claro == h_escuro
    assert v_claro > v_escuro


@pytest.mark.parametrize("conversao", [para_rgb, para_cinza, para_hsv])
def test_conversoes_recusam_imagem_de_um_canal(conversao) -> None:
    with pytest.raises(ErroImagem) as capturado:
        conversao(np.zeros((100, 100), dtype=np.uint8))
    assert capturado.value.codigo == "E004"


@pytest.mark.parametrize("conversao", [para_rgb, para_cinza, para_hsv])
def test_conversoes_recusam_imagem_vazia(conversao) -> None:
    with pytest.raises(ErroImagem) as capturado:
        conversao(np.zeros((0, 0, 3), dtype=np.uint8))
    assert capturado.value.codigo == "E004"


@pytest.mark.parametrize("conversao", [para_rgb, para_cinza, para_hsv])
def test_conversoes_sao_deterministicas(conversao, imagem_folha_sintetica: np.ndarray) -> None:
    assert np.array_equal(conversao(imagem_folha_sintetica), conversao(imagem_folha_sintetica))


# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------

def test_gaussiano_preserva_forma_e_tipo(imagem_folha_sintetica: np.ndarray) -> None:
    saida = suavizar_gaussiano(imagem_folha_sintetica, kernel=5)
    assert saida.shape == imagem_folha_sintetica.shape
    assert saida.dtype == imagem_folha_sintetica.dtype


def test_mediana_preserva_forma_e_tipo(imagem_folha_sintetica: np.ndarray) -> None:
    saida = suavizar_mediana(imagem_folha_sintetica, kernel=5)
    assert saida.shape == imagem_folha_sintetica.shape
    assert saida.dtype == imagem_folha_sintetica.dtype


def test_gaussiano_reduz_variacao_local(imagem_sal_e_pimenta: np.ndarray) -> None:
    antes = float(np.std(imagem_sal_e_pimenta.astype(np.float64)))
    depois = float(np.std(suavizar_gaussiano(imagem_sal_e_pimenta, kernel=5).astype(np.float64)))
    assert depois < antes


def test_mediana_remove_ruido_impulsivo(imagem_sal_e_pimenta: np.ndarray) -> None:
    """A mediana descarta extremos em vez de os diluir — o ruído some."""
    filtrada = suavizar_mediana(imagem_sal_e_pimenta, kernel=5)

    extremos_antes = int(np.sum((imagem_sal_e_pimenta == 0) | (imagem_sal_e_pimenta == 255)))
    extremos_depois = int(np.sum((filtrada == 0) | (filtrada == 255)))

    assert extremos_antes > 0
    assert extremos_depois < extremos_antes * 0.1


def test_mediana_supera_gaussiano_contra_sal_e_pimenta(imagem_sal_e_pimenta: np.ndarray) -> None:
    """Comparação factual entre os dois candidatos, sem eleger vencedor geral.

    Mede apenas este caso: ruído impulsivo. A escolha do filtro do pipeline é da
    Fase 4, sobre imagens reais.
    """
    alvo = 128.0
    erro_gauss = float(np.mean(np.abs(suavizar_gaussiano(imagem_sal_e_pimenta, 5).astype(np.float64) - alvo)))
    erro_mediana = float(np.mean(np.abs(suavizar_mediana(imagem_sal_e_pimenta, 5).astype(np.float64) - alvo)))

    assert erro_mediana < erro_gauss


def test_filtros_funcionam_em_um_canal() -> None:
    cinza = np.full((100, 100), 128, dtype=np.uint8)
    assert suavizar_gaussiano(cinza, 3).shape == cinza.shape
    assert suavizar_mediana(cinza, 3).shape == cinza.shape


def test_filtros_sao_deterministicos(imagem_folha_sintetica: np.ndarray) -> None:
    assert np.array_equal(
        suavizar_gaussiano(imagem_folha_sintetica, 5), suavizar_gaussiano(imagem_folha_sintetica, 5)
    )
    assert np.array_equal(
        suavizar_mediana(imagem_folha_sintetica, 5), suavizar_mediana(imagem_folha_sintetica, 5)
    )


def test_imagem_uniforme_nao_muda_com_filtro() -> None:
    """Sem variação local não há o que suavizar (exceto na borda, aqui replicada)."""
    uniforme = np.full((100, 100, 3), 200, dtype=np.uint8)
    assert np.array_equal(suavizar_mediana(uniforme, 5), uniforme)


# ---------------------------------------------------------------------------
# Validação de kernel
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filtro", [suavizar_gaussiano, suavizar_mediana])
@pytest.mark.parametrize("kernel", [2, 4, 6, 10])
def test_kernel_par_e_rejeitado(filtro, kernel: int, imagem_folha_sintetica: np.ndarray) -> None:
    with pytest.raises(ErroImagem) as capturado:
        filtro(imagem_folha_sintetica, kernel=kernel)
    assert capturado.value.codigo == "E008"


@pytest.mark.parametrize("filtro", [suavizar_gaussiano, suavizar_mediana])
@pytest.mark.parametrize("kernel", [0, 1, -3])
def test_kernel_abaixo_do_minimo_e_rejeitado(filtro, kernel: int, imagem_folha_sintetica: np.ndarray) -> None:
    with pytest.raises(ErroImagem) as capturado:
        filtro(imagem_folha_sintetica, kernel=kernel)
    assert capturado.value.codigo == "E008"


@pytest.mark.parametrize("filtro", [suavizar_gaussiano, suavizar_mediana])
@pytest.mark.parametrize("kernel", [3.0, "5", None, True])
def test_kernel_de_tipo_errado_e_rejeitado(filtro, kernel: object, imagem_folha_sintetica: np.ndarray) -> None:
    with pytest.raises(ErroImagem) as capturado:
        filtro(imagem_folha_sintetica, kernel=kernel)  # type: ignore[arg-type]
    assert capturado.value.codigo == "E008"


@pytest.mark.parametrize("filtro", [suavizar_gaussiano, suavizar_mediana])
def test_kernel_minimo_e_aceito(filtro, imagem_folha_sintetica: np.ndarray) -> None:
    assert filtro(imagem_folha_sintetica, kernel=KERNEL_MINIMO).shape == imagem_folha_sintetica.shape


@pytest.mark.parametrize("filtro", [suavizar_gaussiano, suavizar_mediana])
def test_filtros_recusam_imagem_vazia(filtro) -> None:
    with pytest.raises(ErroImagem) as capturado:
        filtro(np.zeros((0, 0, 3), dtype=np.uint8), kernel=3)
    assert capturado.value.codigo == "E004"


@pytest.mark.parametrize("filtro", [suavizar_gaussiano, suavizar_mediana])
def test_filtros_recusam_none(filtro) -> None:
    with pytest.raises(ErroImagem) as capturado:
        filtro(None, kernel=3)  # type: ignore[arg-type]
    assert capturado.value.codigo == "E004"


# ---------------------------------------------------------------------------
# Encadeamento
# ---------------------------------------------------------------------------

def test_pipeline_de_preprocessamento_encadeia(imagem_folha_sintetica: np.ndarray) -> None:
    """Percorre a sequência prevista sem segmentar nada."""
    redimensionada, info = redimensionar(imagem_folha_sintetica, lado_maximo=300)
    cinza = para_cinza(redimensionada)
    hsv = para_hsv(redimensionada)
    suavizada = suavizar_gaussiano(cinza, kernel=5)

    assert max(redimensionada.shape[:2]) == 300
    assert cinza.ndim == 2
    assert hsv.shape == redimensionada.shape
    assert suavizada.shape == cinza.shape
    assert info["redimensionada"] is True


def test_encadeamento_completo_e_deterministico(imagem_folha_sintetica: np.ndarray) -> None:
    def executar() -> np.ndarray:
        redimensionada, _ = redimensionar(imagem_folha_sintetica, lado_maximo=256)
        return suavizar_mediana(para_cinza(redimensionada), kernel=5)

    assert np.array_equal(executar(), executar())
