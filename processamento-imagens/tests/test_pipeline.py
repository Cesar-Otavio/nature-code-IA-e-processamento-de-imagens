"""Testes ponta a ponta do pipeline e do contrato JSON."""

from __future__ import annotations

import json
import math
from pathlib import Path

import cv2
import numpy as np
import pytest

from src.pipeline import (
    VERSAO_PIPELINE,
    _serializar,
    limpar_execucoes_antigas,
    processar_folha,
    processar_matriz,
)
from src.segmentation import OBJETO
from src.utils import ler_imagem, normalizar_canais

BLOCOS = {
    "status", "versao_pipeline", "id_execucao", "entrada", "processamento",
    "objeto", "caracteristicas", "classificacao", "avisos", "erro",
    "imagens_intermediarias",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def folha_sintetica(tmp_path: Path) -> Path:
    """Elipse verde sobre fundo branco — reproduz a condição do Flavia."""
    tela = np.full((700, 900, 3), 250, dtype=np.uint8)
    cv2.ellipse(tela, (450, 350), (280, 110), 25, 0, 360, (40, 140, 60), -1)
    destino = tmp_path / "folha.png"
    cv2.imwrite(str(destino), tela)
    return destino


@pytest.fixture
def folha_sem_objeto(tmp_path: Path) -> Path:
    destino = tmp_path / "vazia.png"
    cv2.imwrite(str(destino), np.full((400, 400, 3), 250, dtype=np.uint8))
    return destino


@pytest.fixture
def arquivo_corrompido(tmp_path: Path) -> Path:
    destino = tmp_path / "falso.jpg"
    destino.write_text("isto nao e uma imagem", encoding="utf-8")
    return destino


# ---------------------------------------------------------------------------
# Contrato
# ---------------------------------------------------------------------------

def test_contrato_tem_todos_os_blocos(folha_sintetica: Path, tmp_path: Path) -> None:
    resultado = processar_folha(folha_sintetica, destino=tmp_path / "saida")
    assert set(resultado) == BLOCOS


def test_contrato_de_erro_tem_os_mesmos_blocos(tmp_path: Path) -> None:
    """Sucesso e erro têm a mesma forma — consumidores não precisam de dois formatos."""
    resultado = processar_folha(tmp_path / "inexistente.jpg")

    assert set(resultado) == BLOCOS
    assert resultado["status"] == "erro"
    assert resultado["caracteristicas"] is None
    assert resultado["erro"]["codigo"] == "E001"  # type: ignore[index]


@pytest.mark.parametrize("status", ["sucesso", "sucesso_com_avisos", "erro"])
def test_status_e_um_dos_tres(status: str, folha_sintetica: Path, tmp_path: Path) -> None:
    resultado = processar_folha(folha_sintetica, destino=tmp_path / "s")
    assert resultado["status"] in ("sucesso", "sucesso_com_avisos", "erro")


def test_blocos_internos(folha_sintetica: Path, tmp_path: Path) -> None:
    resultado = processar_folha(folha_sintetica, destino=tmp_path / "s")

    assert set(resultado["entrada"]) >= {  # type: ignore[arg-type]
        "arquivo", "formato", "largura_original_px", "altura_original_px",
        "largura_processada_px", "altura_processada_px", "bytes",
    }
    assert set(resultado["processamento"]) >= {  # type: ignore[arg-type]
        "etapas", "parametros", "tempo_total_ms", "tempo_por_etapa_ms",
    }
    assert set(resultado["objeto"]) >= {  # type: ignore[arg-type]
        "detectado", "numero_contornos", "dominancia", "bbox", "bbox_rotacionada",
        "centroide", "toca_borda", "orientacao_graus", "orientacao_confiavel",
    }
    assert set(resultado["caracteristicas"]) == {  # type: ignore[arg-type]
        "dimensoes", "forma", "orientacao", "convexidade", "cor", "qualidade", "avisos",
    }
    assert set(resultado["classificacao"]) >= {  # type: ignore[arg-type]
        "alongamento", "concavidade", "compacidade", "complexidade_borda",
        "orientacao", "resumo", "avisos",
    }


def test_nomes_de_caracteristicas_sao_os_da_fase_7(folha_sintetica: Path, tmp_path: Path) -> None:
    """A API não pode inventar uma segunda nomenclatura."""
    caracteristicas = processar_folha(folha_sintetica, destino=tmp_path / "s")["caracteristicas"]

    for campo in ("area_contorno_px2", "area_mascara_px2", "perimetro_px"):
        assert campo in caracteristicas["dimensoes"]  # type: ignore[index]
    for campo in ("elongacao", "circularidade", "solidez", "extent", "extent_rotacionado"):
        assert campo in caracteristicas["forma"]  # type: ignore[index]


def test_versao_do_pipeline_e_reportada(folha_sintetica: Path, tmp_path: Path) -> None:
    assert processar_folha(folha_sintetica, destino=tmp_path / "s")["versao_pipeline"] == VERSAO_PIPELINE


def test_caminho_absoluto_nao_vaza(folha_sintetica: Path, tmp_path: Path) -> None:
    """O JSON público não expõe a estrutura de diretórios da máquina."""
    resultado = processar_folha(folha_sintetica, destino=tmp_path / "s")
    texto = json.dumps(resultado, ensure_ascii=False)

    assert str(tmp_path) not in texto
    assert resultado["entrada"]["arquivo"] == "folha.png"  # type: ignore[index]
    for nome in resultado["imagens_intermediarias"].values():  # type: ignore[union-attr]
        assert "/" not in nome and "\\" not in nome


# ---------------------------------------------------------------------------
# Serialização
# ---------------------------------------------------------------------------

def test_json_e_valido_e_sem_nan(folha_sintetica: Path, tmp_path: Path) -> None:
    resultado = processar_folha(folha_sintetica, destino=tmp_path / "s")
    texto = json.dumps(resultado, ensure_ascii=False, allow_nan=False)

    assert "NaN" not in texto
    assert "Infinity" not in texto
    assert json.loads(texto) == resultado


def test_serializador_converte_tipos_numpy() -> None:
    assert _serializar(np.int64(42)) == 42
    assert _serializar(np.float64(1.5)) == 1.5
    assert _serializar(np.bool_(True)) is True
    assert isinstance(_serializar(np.int32(7)), int)


def test_serializador_transforma_nao_finitos_em_none() -> None:
    assert _serializar(float("nan")) is None
    assert _serializar(float("inf")) is None
    assert _serializar(np.float64("nan")) is None


def test_serializador_descarta_arrays() -> None:
    """Matriz de imagem nunca pode chegar ao JSON."""
    assert _serializar(np.zeros((10, 10, 3), dtype=np.uint8)) is None


def test_nenhum_array_no_resultado(folha_sintetica: Path, tmp_path: Path) -> None:
    resultado = processar_folha(folha_sintetica, destino=tmp_path / "s")

    def conferir(valor: object) -> None:
        assert not isinstance(valor, np.ndarray)
        if isinstance(valor, dict):
            for item in valor.values():
                conferir(item)
        elif isinstance(valor, list):
            for item in valor:
                conferir(item)

    conferir(resultado)


# ---------------------------------------------------------------------------
# Imagens intermediárias
# ---------------------------------------------------------------------------

def test_gera_oito_imagens(folha_sintetica: Path, tmp_path: Path) -> None:
    saida = tmp_path / "execucao"
    resultado = processar_folha(folha_sintetica, salvar_imagens=True, destino=saida)

    assert len(resultado["imagens_intermediarias"]) == 8  # type: ignore[arg-type]
    for nome in resultado["imagens_intermediarias"].values():  # type: ignore[union-attr]
        assert (saida / nome).is_file()


def test_modo_sem_imagens(folha_sintetica: Path, tmp_path: Path) -> None:
    saida = tmp_path / "sem"
    resultado = processar_folha(folha_sintetica, salvar_imagens=False, destino=saida)

    assert resultado["imagens_intermediarias"] == {}
    assert not saida.exists()


def test_resultado_numerico_identico_com_e_sem_imagens(folha_sintetica: Path, tmp_path: Path) -> None:
    """Visualização é apresentação: não pode influenciar número algum."""
    com = processar_folha(folha_sintetica, salvar_imagens=True, destino=tmp_path / "a")
    sem = processar_folha(folha_sintetica, salvar_imagens=False)

    assert com["caracteristicas"] == sem["caracteristicas"]
    assert com["classificacao"] == sem["classificacao"]
    assert com["objeto"] == sem["objeto"]


# ---------------------------------------------------------------------------
# Erros
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("caso,codigo", [("inexistente", "E001"), ("corrompido", "E003")])
def test_erros_de_entrada(caso: str, codigo: str, arquivo_corrompido: Path, tmp_path: Path) -> None:
    caminho = tmp_path / "nao-existe.jpg" if caso == "inexistente" else arquivo_corrompido
    resultado = processar_folha(caminho)

    assert resultado["status"] == "erro"
    assert resultado["erro"]["codigo"] == codigo  # type: ignore[index]


def test_extensao_invalida(tmp_path: Path) -> None:
    destino = tmp_path / "documento.txt"
    destino.write_text("texto", encoding="utf-8")

    assert processar_folha(destino)["erro"]["codigo"] == "E002"  # type: ignore[index]


def test_imagem_sem_objeto(folha_sem_objeto: Path) -> None:
    resultado = processar_folha(folha_sem_objeto, salvar_imagens=False)

    assert resultado["status"] == "erro"
    assert resultado["erro"]["codigo"] == "E007"  # type: ignore[index]


def test_erro_nao_expoe_rastreamento(tmp_path: Path) -> None:
    mensagem = processar_folha(tmp_path / "x.jpg")["erro"]["mensagem"]  # type: ignore[index]
    assert "Traceback" not in mensagem
    assert 'File "' not in mensagem


# ---------------------------------------------------------------------------
# R16 — EXIF e canal alfa
# ---------------------------------------------------------------------------

def test_png_com_alfa_e_composto_sobre_branco(tmp_path: Path) -> None:
    """R16: um pixel transparente não pode virar preto.

    Sem o tratamento, a região transparente manteria a cor sob o alfa — normalmente
    preto — e a segmentação veria um fundo escuro onde deveria haver fundo claro.
    """
    rgba = np.zeros((400, 500, 4), dtype=np.uint8)
    rgba[:, :, :3] = (0, 0, 0)     # preto sob o alfa
    rgba[:, :, 3] = 0              # tudo transparente
    cv2.ellipse(rgba, (250, 200), (150, 70), 0, 0, 360, (40, 140, 60, 255), -1)

    destino = tmp_path / "alfa.png"
    cv2.imwrite(str(destino), rgba)

    imagem, metadados = ler_imagem(destino)

    assert metadados["tinha_canal_alfa"] is True
    assert imagem.shape[2] == 3
    canto = tuple(int(x) for x in imagem[10, 10])
    assert canto == (255, 255, 255), "região transparente deveria virar branca"


def test_png_com_alfa_percorre_o_pipeline(tmp_path: Path) -> None:
    rgba = np.zeros((500, 600, 4), dtype=np.uint8)
    rgba[:, :, 3] = 0
    cv2.ellipse(rgba, (300, 250), (200, 90), 20, 0, 360, (40, 140, 60, 255), -1)
    destino = tmp_path / "folha-alfa.png"
    cv2.imwrite(str(destino), rgba)

    resultado = processar_folha(destino, salvar_imagens=False)

    assert resultado["status"] in ("sucesso", "sucesso_com_avisos")
    assert resultado["entrada"]["tinha_canal_alfa"] is True  # type: ignore[index]


def test_normalizar_canais_trata_os_tres_casos() -> None:
    cinza = np.full((50, 50), 128, dtype=np.uint8)
    bgr = np.full((50, 50, 3), 128, dtype=np.uint8)
    bgra = np.full((50, 50, 4), 128, dtype=np.uint8)

    assert normalizar_canais(cinza)[0].shape == (50, 50, 3)
    assert normalizar_canais(bgr)[0].shape == (50, 50, 3)
    assert normalizar_canais(bgra)[0].shape == (50, 50, 3)
    assert normalizar_canais(bgra)[1] is True
    assert normalizar_canais(bgr)[1] is False


def test_orientacao_exif_e_aplicada(tmp_path: Path) -> None:
    """R16: o OpenCV já aplica a rotação EXIF — verificado, não suposto.

    Um JPEG retrato (200×100) com ``Orientation=6`` é decodificado como paisagem
    (100×200).
    """
    import struct

    tela = np.full((200, 100, 3), 250, dtype=np.uint8)
    cv2.ellipse(tela, (50, 100), (30, 70), 0, 0, 360, (40, 140, 60), -1)
    _ok, buffer = cv2.imencode(".jpg", tela)
    base = bytes(buffer)

    exif = (b"Exif\x00\x00II\x2a\x00\x08\x00\x00\x00\x01\x00\x12\x01\x03\x00"
            b"\x01\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00")
    app1 = b"\xff\xe1" + struct.pack(">H", len(exif) + 2) + exif

    sem = tmp_path / "sem-exif.jpg"
    com = tmp_path / "com-exif.jpg"
    sem.write_bytes(base)
    com.write_bytes(base[:2] + app1 + base[2:])

    imagem_sem, _ = ler_imagem(sem)
    imagem_com, _ = ler_imagem(com)

    assert imagem_sem.shape[:2] == (200, 100)
    assert imagem_com.shape[:2] == (100, 200)


@pytest.mark.parametrize("dimensoes", [(900, 700), (700, 900)])
def test_retrato_e_paisagem(dimensoes: tuple[int, int], tmp_path: Path) -> None:
    largura, altura = dimensoes
    tela = np.full((altura, largura, 3), 250, dtype=np.uint8)
    cv2.ellipse(tela, (largura // 2, altura // 2), (largura // 4, altura // 5), 15, 0, 360, (40, 140, 60), -1)
    destino = tmp_path / f"{largura}x{altura}.png"
    cv2.imwrite(str(destino), tela)

    assert processar_folha(destino, salvar_imagens=False)["status"] in ("sucesso", "sucesso_com_avisos")


# ---------------------------------------------------------------------------
# Determinismo e limpeza
# ---------------------------------------------------------------------------

def test_determinismo(folha_sintetica: Path) -> None:
    """Campos variáveis (id, tempos) à parte, o resultado é idêntico."""
    a = processar_folha(folha_sintetica, salvar_imagens=False)
    b = processar_folha(folha_sintetica, salvar_imagens=False)

    assert a["caracteristicas"] == b["caracteristicas"]
    assert a["classificacao"] == b["classificacao"]
    assert a["objeto"] == b["objeto"]
    assert a["id_execucao"] != b["id_execucao"]


def test_id_de_execucao_e_hexadecimal(folha_sintetica: Path) -> None:
    identificador = processar_folha(folha_sintetica, salvar_imagens=False)["id_execucao"]
    assert isinstance(identificador, str)
    assert len(identificador) == 32
    assert all(c in "0123456789abcdef" for c in identificador)


def test_id_pode_ser_fornecido(folha_sintetica: Path, tmp_path: Path) -> None:
    resultado = processar_folha(folha_sintetica, salvar_imagens=False, id_execucao="abc123")
    assert resultado["id_execucao"] == "abc123"


def test_processar_matriz_aceita_ndarray() -> None:
    """A camada interna evita duplicação entre CLI e API."""
    tela = np.full((500, 700, 3), 250, dtype=np.uint8)
    cv2.ellipse(tela, (350, 250), (200, 90), 0, 0, 360, (40, 140, 60), -1)

    resultado = processar_matriz(tela, {"arquivo": "memoria.png", "formato": "PNG"}, salvar_imagens=False)
    assert resultado["status"] in ("sucesso", "sucesso_com_avisos")


def test_limpeza_de_execucoes_antigas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import os
    import time

    from src import pipeline

    pasta = tmp_path / "execucoes"
    pasta.mkdir()
    antiga = pasta / "antiga"
    nova = pasta / "nova"
    antiga.mkdir()
    nova.mkdir()
    (antiga / "x.png").write_bytes(b"x")

    velho = time.time() - 48 * 3600
    os.utime(antiga, (velho, velho))

    monkeypatch.setattr(pipeline, "PASTA_EXECUCOES", pasta)

    assert pipeline.limpar_execucoes_antigas(24.0) == 1
    assert not antiga.exists()
    assert nova.exists()


def _pasta_com_execucoes(tmp_path: Path) -> tuple[Path, Path, Path]:
    import os
    import time

    pasta = tmp_path / "execucoes"
    antiga, recente = pasta / ("a" * 32), pasta / ("b" * 32)
    for p in (antiga, recente):
        p.mkdir(parents=True)
        (p / "07-final.png").write_bytes(b"x")
    velho = time.time() - 25 * 3600
    os.utime(antiga, (velho, velho))
    return pasta, antiga, recente


def test_limpeza_e_idempotente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Reproduz a verificação manual: 1 removido na primeira chamada, 0 nas seguintes."""
    from src import pipeline

    pasta, antiga, recente = _pasta_com_execucoes(tmp_path)
    monkeypatch.setattr(pipeline, "PASTA_EXECUCOES", pasta)

    assert pipeline.limpar_execucoes_antigas(24.0) == 1
    assert pipeline.limpar_execucoes_antigas(24.0) == 0
    assert pipeline.limpar_execucoes_antigas(24.0) == 0
    assert not antiga.exists()
    assert (recente / "07-final.png").exists()


def test_limpeza_ignora_arquivos_soltos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Só diretórios de execução são candidatos; um arquivo na raiz não é tocado."""
    import os
    import time

    from src import pipeline

    pasta, _antiga, _recente = _pasta_com_execucoes(tmp_path)
    solto = pasta / "nota.txt"
    solto.write_text("x")
    velho = time.time() - 48 * 3600
    os.utime(solto, (velho, velho))
    monkeypatch.setattr(pipeline, "PASTA_EXECUCOES", pasta)

    pipeline.limpar_execucoes_antigas(24.0)
    assert solto.exists()


def test_limpeza_nao_conta_o_que_nao_conseguiu_remover(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Com arquivo travado, a pasta fica — e não pode ser contada como removida."""
    import shutil

    from src import pipeline

    pasta, antiga, _recente = _pasta_com_execucoes(tmp_path)
    monkeypatch.setattr(pipeline, "PASTA_EXECUCOES", pasta)
    monkeypatch.setattr(shutil, "rmtree", lambda *a, **k: None)  # simula falha silenciosa

    assert pipeline.limpar_execucoes_antigas(24.0) == 0
    assert antiga.exists()


def test_limpeza_em_pasta_inexistente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from src import pipeline
    monkeypatch.setattr(pipeline, "PASTA_EXECUCOES", tmp_path / "nao-existe")
    assert pipeline.limpar_execucoes_antigas() == 0


# ---------------------------------------------------------------------------
# Parâmetros preservados
# ---------------------------------------------------------------------------

def test_parametros_das_fases_anteriores_nao_mudaram(folha_sintetica: Path, tmp_path: Path) -> None:
    """Nenhuma recalibração silenciosa nesta fase."""
    parametros = processar_folha(folha_sintetica, destino=tmp_path / "s")["processamento"]["parametros"]  # type: ignore[index]

    assert parametros["kernel_gaussiano"] == 5
    assert parametros["lado_maximo_px"] == 1024
    assert parametros["faixa_hsv"]["h"] == [25, 95]
    assert parametros["faixa_hsv"]["s"] == [40, 255]
    assert parametros["faixa_hsv"]["v"] == [20, 255]


def test_etapas_sao_reportadas_em_ordem(folha_sintetica: Path, tmp_path: Path) -> None:
    etapas = processar_folha(folha_sintetica, destino=tmp_path / "s")["processamento"]["etapas"]  # type: ignore[index]

    assert etapas[0] == "validacao"
    assert "segmentacao" in etapas
    assert etapas[-1] == "classificacao"


def test_tempos_sao_reportados(folha_sintetica: Path, tmp_path: Path) -> None:
    processamento = processar_folha(folha_sintetica, destino=tmp_path / "s")["processamento"]

    assert processamento["tempo_total_ms"] > 0  # type: ignore[index]
    for etapa in ("segmentacao", "contornos", "caracteristicas", "classificacao"):
        assert etapa in processamento["tempo_por_etapa_ms"]  # type: ignore[index]


def test_avisos_nao_sao_duplicados(folha_sintetica: Path, tmp_path: Path) -> None:
    avisos = processar_folha(folha_sintetica, destino=tmp_path / "s")["avisos"]
    assert len(avisos) == len(set(avisos))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Visualização da caixa rotacionada que excede o quadro (Fase 9, correção)
#
# Observado em `2497` e `1101`: a caixa de área mínima de uma folha grande tem
# cantos fora da imagem. É geometria correta; só o DESENHO é recortado.
# ---------------------------------------------------------------------------

def _folha_grande_girada() -> np.ndarray:
    """Folha que não toca a borda, mas cuja caixa rotacionada excede o quadro."""
    tela = np.full((768, 1024, 3), 250, dtype=np.uint8)
    cv2.ellipse(tela, (512, 384), (470, 250), 30, 0, 360, (40, 140, 60), -1)
    return tela


def test_segmento_visivel_recorta_ao_quadro() -> None:
    from src.visualizacao import segmento_visivel

    # Aresta real da caixa de `2497`: começa fora pela esquerda e termina fora por cima.
    trecho = segmento_visivel((-26.4, 250.8), (811.0, -67.1), 1024, 768)
    assert trecho is not None
    for x, y in trecho:
        assert 0 <= x <= 1023 and 0 <= y <= 767

    assert segmento_visivel((-50, -50), (-10, -80), 1024, 768) is None      # todo fora
    assert segmento_visivel((10, 20), (300, 400), 1024, 768) == ((10, 20), (300, 400))  # todo dentro


def test_caixa_que_excede_o_quadro_e_desenhada_so_dentro(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nenhuma coordenada desenhada fica fora da imagem."""
    from src import visualizacao

    tela = _folha_grande_girada()
    chamadas: list[tuple] = []
    original = visualizacao.cv2.line

    def espiao(imagem, p1, p2, *args, **kwargs):
        chamadas.append((imagem.shape[:2], p1, p2))
        return original(imagem, p1, p2, *args, **kwargs)

    monkeypatch.setattr(visualizacao.cv2, "line", espiao)
    resultado = processar_matriz(tela, {"arquivo": "grande.png", "formato": "PNG"},
                                 salvar_imagens=True, destino=tmp_path / "exec")

    # Pré-condição: a caixa verdadeira excede mesmo o quadro.
    rot = resultado["objeto"]["bbox_rotacionada"]
    pontos = cv2.boxPoints(((rot["centro_x"], rot["centro_y"]),
                            (rot["largura_bruta"], rot["altura_bruta"]), rot["angulo_bruto"]))
    assert pontos.min() < 0 or pontos[:, 0].max() > 1023 or pontos[:, 1].max() > 767
    assert resultado["objeto"]["toca_borda"]["qualquer"] is False

    assert len(chamadas) >= 4  # as arestas visíveis da caixa (e o eixo)
    for (altura, largura), p1, p2 in chamadas:
        for x, y in (p1, p2):
            assert isinstance(x, int) and isinstance(y, int)
            assert 0 <= x <= largura - 1 and 0 <= y <= altura - 1, (p1, p2)

    assert (tmp_path / "exec" / "07-final.png").is_file()


def test_recorte_do_desenho_nao_muda_nenhum_numero(tmp_path: Path) -> None:
    """A caixa continua sendo o minAreaRect do contorno, com ou sem imagens geradas."""
    tela = _folha_grande_girada()
    metadados = {"arquivo": "grande.png", "formato": "PNG"}

    com = processar_matriz(tela, metadados, salvar_imagens=True, destino=tmp_path / "exec")
    sem = processar_matriz(tela, metadados, salvar_imagens=False)

    for bloco in ("objeto", "caracteristicas", "classificacao"):
        assert com[bloco] == sem[bloco]

    mascara = np.zeros(tela.shape[:2], np.uint8)
    cv2.ellipse(mascara, (512, 384), (470, 250), 30, 0, 360, 255, -1)
    contorno = max(cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0],
                   key=cv2.contourArea)
    (_cx, _cy), (lado_a, lado_b), _ang = cv2.minAreaRect(contorno)
    rot = com["objeto"]["bbox_rotacionada"]
    assert rot["lado_maior"] == pytest.approx(max(lado_a, lado_b), rel=0.02)
    assert rot["lado_menor"] == pytest.approx(min(lado_a, lado_b), rel=0.02)
