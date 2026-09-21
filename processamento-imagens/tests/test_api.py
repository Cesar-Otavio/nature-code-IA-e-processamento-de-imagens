"""Testes da API Flask, pelo cliente de teste — nenhum servidor real é iniciado."""

from __future__ import annotations

import ast
import io
from pathlib import Path

import cv2
import numpy as np
import pytest

from src import api as modulo_api
from src import pipeline
from src.api import ORIGENS_PERMITIDAS, TAMANHO_MAXIMO_BYTES, criar_app


@pytest.fixture
def cliente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Cliente isolado: as execuções vão para um diretório temporário."""
    pasta = tmp_path / "execucoes"
    monkeypatch.setattr(pipeline, "PASTA_EXECUCOES", pasta)
    monkeypatch.setattr(modulo_api, "PASTA_EXECUCOES", pasta)
    app = criar_app()
    app.config["TESTING"] = True
    return app.test_client()


def _png_de_folha() -> bytes:
    tela = np.full((700, 900, 3), 250, dtype=np.uint8)
    cv2.ellipse(tela, (450, 350), (280, 110), 25, 0, 360, (40, 140, 60), -1)
    return cv2.imencode(".png", tela)[1].tobytes()


def _enviar(cliente, dados: bytes, nome: str = "folha.png", campo: str = "imagem", origem: str | None = None):
    cabecalhos = {"Origin": origem} if origem else {}
    return cliente.post(
        "/api/processar-folha",
        data={campo: (io.BytesIO(dados), nome)},
        content_type="multipart/form-data",
        headers=cabecalhos,
    )


# ---------------------------------------------------------------------------
# Casca fina
# ---------------------------------------------------------------------------

def _imports(caminho: Path) -> set[str]:
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    nomes: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes.update(alias.name.split(".")[0] for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            nomes.add(no.module.split(".")[0])
    return nomes


def test_api_nao_contem_logica_de_processamento() -> None:
    caminho = Path(__file__).resolve().parent.parent / "src" / "api.py"
    texto = caminho.read_text(encoding="utf-8")

    assert "cv2" not in _imports(caminho)
    assert "numpy" not in _imports(caminho)
    for modulo in ("segmentation", "morphology", "contours", "features", "classification", "preprocessing"):
        assert f"from .{modulo}" not in texto, f"api.py importa {modulo} diretamente"
    assert "from .pipeline import" in texto


def test_pipeline_e_nucleo_nao_importam_flask() -> None:
    """A camada de processamento não sabe que existe uma API."""
    raiz = Path(__file__).resolve().parent.parent / "src"
    for nome in ("pipeline.py", "segmentation.py", "morphology.py", "contours.py",
                 "features.py", "classification.py", "preprocessing.py", "utils.py", "visualizacao.py"):
        assert "flask" not in _imports(raiz / nome), f"{nome} importa Flask"


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

def test_health(cliente) -> None:
    resposta = cliente.get("/health")
    dados = resposta.get_json()

    assert resposta.status_code == 200
    assert dados["status"] == "ok"
    assert dados["servico"] == "nature-code-pdi"
    assert dados["usa_ia"] is False
    assert "versao" in dados


# ---------------------------------------------------------------------------
# /api/processar-folha
# ---------------------------------------------------------------------------

def test_upload_valido(cliente) -> None:
    resposta = _enviar(cliente, _png_de_folha())
    dados = resposta.get_json()

    assert resposta.status_code == 200
    assert dados["status"] in ("sucesso", "sucesso_com_avisos")
    assert dados["caracteristicas"]["forma"]["elongacao"] > 1
    assert len(dados["imagens_intermediarias"]) == 8


def test_imagens_viram_urls_da_api(cliente) -> None:
    dados = _enviar(cliente, _png_de_folha()).get_json()
    identificador = dados["id_execucao"]

    for url in dados["imagens_intermediarias"].values():
        assert url.startswith(f"/api/resultado/{identificador}/")


def test_imagem_intermediaria_e_servida(cliente) -> None:
    dados = _enviar(cliente, _png_de_folha()).get_json()
    url = dados["imagens_intermediarias"]["07-final"]

    resposta = cliente.get(url)
    assert resposta.status_code == 200
    assert resposta.mimetype == "image/png"
    assert resposta.data[:8] == b"\x89PNG\r\n\x1a\n"


def test_campo_ausente(cliente) -> None:
    resposta = _enviar(cliente, _png_de_folha(), campo="arquivo")
    assert resposta.status_code == 400
    assert resposta.get_json()["erro"]["codigo"] == "E002"


def test_extensao_invalida(cliente) -> None:
    resposta = _enviar(cliente, b"conteudo", nome="documento.txt")
    assert resposta.status_code == 400
    assert resposta.get_json()["erro"]["codigo"] == "E002"


def test_conteudo_invalido_com_extensao_valida(cliente) -> None:
    resposta = _enviar(cliente, b"isto nao e uma imagem", nome="falso.jpg")
    assert resposta.status_code == 400
    assert resposta.get_json()["erro"]["codigo"] == "E003"


def test_imagem_sem_folha_retorna_422(cliente) -> None:
    vazia = cv2.imencode(".png", np.full((400, 400, 3), 250, dtype=np.uint8))[1].tobytes()
    resposta = _enviar(cliente, vazia)
    assert resposta.status_code == 422
    assert resposta.get_json()["erro"]["codigo"] == "E007"


def test_payload_grande_retorna_413(cliente) -> None:
    grande = b"\x00" * (TAMANHO_MAXIMO_BYTES + 1024)
    resposta = _enviar(cliente, grande, nome="grande.png")
    assert resposta.status_code == 413
    assert resposta.get_json()["erro"]["codigo"] == "E006"


def test_nome_malicioso_nao_determina_caminho(cliente) -> None:
    resposta = _enviar(cliente, _png_de_folha(), nome="../../../etc/folha.png")
    dados = resposta.get_json()

    assert resposta.status_code == 200
    assert "/" not in dados["entrada"]["arquivo"]
    assert ".." not in dados["entrada"]["arquivo"]


def test_nome_temporario_nao_vaza_no_erro(cliente) -> None:
    """Defeito encontrado no teste manual da Fase 9.

    Em resposta de erro, `entrada.arquivo` expunha o nome do arquivo temporário
    interno (`nature-code-pdi-<uuid>.jpg`) em vez do nome enviado.
    """
    dados = _enviar(cliente, b"nao e imagem", nome="minha-folha.jpg").get_json()

    assert dados["status"] == "erro"
    assert dados["entrada"]["arquivo"] == "minha-folha.jpg"
    assert "nature-code-pdi" not in str(dados)


def test_upload_original_nao_e_mantido(cliente, tmp_path: Path) -> None:
    import tempfile
    antes = set(Path(tempfile.gettempdir()).glob("nature-code-pdi-*"))
    _enviar(cliente, _png_de_folha())
    depois = set(Path(tempfile.gettempdir()).glob("nature-code-pdi-*"))
    assert depois == antes


def test_erro_nao_expoe_rastreamento(cliente) -> None:
    texto = _enviar(cliente, b"lixo", nome="x.jpg").get_data(as_text=True)
    assert "Traceback" not in texto
    assert 'File "' not in texto


# ---------------------------------------------------------------------------
# Resultados e travessia de caminho
# ---------------------------------------------------------------------------

def test_resultado_inexistente(cliente) -> None:
    resposta = cliente.get("/api/resultado/naoexiste/07-final.png")
    assert resposta.status_code == 404


@pytest.mark.parametrize("caminho", [
    "/api/resultado/../../api.py",
    "/api/resultado/..%2F..%2Fsrc/api.py",
    "/api/resultado/abc/..%2F..%2F..%2Fsrc%2Fapi.py",
    "/api/resultado/abc/..%5C..%5Csrc%5Capi.py",
    "/api/resultado/..%5C..%5C/api.py",
])
def test_path_traversal_bloqueado(cliente, caminho: str) -> None:
    resposta = cliente.get(caminho)
    assert resposta.status_code == 404
    assert b"def criar_app" not in resposta.data


def test_so_serve_png(cliente) -> None:
    dados = _enviar(cliente, _png_de_folha()).get_json()
    resposta = cliente.get(f"/api/resultado/{dados['id_execucao']}/resultado.json")
    assert resposta.status_code == 404


# ---------------------------------------------------------------------------
# Segurança — reprodução automatizada das verificações manuais da revisão
# ---------------------------------------------------------------------------

def test_upload_de_13_mb_retorna_413_com_mensagem() -> None:
    """Verificação manual: arquivo de 13 MB → HTTP 413, E006, mensagem exata."""
    cliente = criar_app().test_client()
    treze_mb = b"\x00" * (13 * 1024 * 1024)
    resposta = _enviar(cliente, treze_mb, nome="grande.jpg")
    dados = resposta.get_json()

    assert resposta.status_code == 413
    assert dados["erro"]["codigo"] == "E006"
    assert dados["erro"]["mensagem"] == "Arquivo muito grande. Máximo: 12 MB."


def test_upload_logo_abaixo_do_limite_nao_e_barrado_pelo_tamanho(cliente) -> None:
    """O limite barra só o que passa dele: 11 MB de lixo chega ao pipeline (E003), não ao 413."""
    resposta = _enviar(cliente, b"\x00" * (11 * 1024 * 1024), nome="quase.jpg")
    assert resposta.status_code == 400
    assert resposta.get_json()["erro"]["codigo"] == "E003"


def _execucao_real(cliente) -> str:
    return _enviar(cliente, _png_de_folha()).get_json()["id_execucao"]


@pytest.mark.parametrize("sufixo", [
    "..%2F..%2Fsrc%2Fapi.py",          # a tentativa manual, literal
    "..%2F..%2F..%2Fsrc%2Fapi.py",
    "../../src/api.py",                 # ../ cru
    "..%5C..%5Csrc%5Capi.py",           # barra invertida codificada
    "%2E%2E%2F%2E%2E%2Fsrc%2Fapi.py",   # pontos também codificados
    "..",
    "%2E%2E",
])
def test_path_traversal_a_partir_de_execucao_real(cliente, sufixo: str) -> None:
    """Verificação manual: /api/resultado/<uuid>/..%2F..%2Fsrc%2Fapi.py → 404, E404, nada exposto."""
    identificador = _execucao_real(cliente)
    resposta = cliente.get(f"/api/resultado/{identificador}/{sufixo}")

    assert resposta.status_code == 404
    assert b"def criar_app" not in resposta.data
    assert b"import" not in resposta.data
    if resposta.is_json:
        assert resposta.get_json()["erro"]["codigo"] == "E404"


def test_png_fora_da_execucao_nao_e_servido(cliente, tmp_path: Path) -> None:
    """Um PNG real, fora da pasta da execução, não é alcançável pela rota."""
    pasta = modulo_api.PASTA_EXECUCOES
    identificador = _execucao_real(cliente)

    fora = pasta.parent / "segredo.png"
    fora.write_bytes(cv2.imencode(".png", np.zeros((5, 5, 3), np.uint8))[1].tobytes())
    na_raiz = pasta / "raiz.png"
    na_raiz.write_bytes(fora.read_bytes())

    for caminho in (
        f"/api/resultado/{identificador}/..%2F..%2Fsegredo.png",
        f"/api/resultado/{identificador}/..%2Fraiz.png",
        f"/api/resultado/..%2F/segredo.png",
        "/api/resultado/../segredo.png",
        f"/api/resultado/{identificador}/../raiz.png",
    ):
        # O Werkzeug pode responder 308 para fundir barras duplas ("..%2F/" vira "..//");
        # o que importa é a resposta final, depois de seguir o redirecionamento.
        resposta = cliente.get(caminho, follow_redirects=True)
        assert resposta.status_code == 404, caminho
        assert resposta.data[:8] != b"\x89PNG\r\n\x1a\n", caminho


def test_arquivo_nao_png_dentro_da_execucao_nao_e_servido(cliente) -> None:
    """Mesmo existindo dentro da pasta da execução, só PNG é servido."""
    identificador = _execucao_real(cliente)
    pasta = modulo_api.PASTA_EXECUCOES / identificador
    (pasta / "notas.txt").write_text("conteudo interno")
    (pasta / "dados.json").write_text("{}")

    for nome in ("notas.txt", "dados.json"):
        resposta = cliente.get(f"/api/resultado/{identificador}/{nome}")
        assert resposta.status_code == 404
        assert b"conteudo interno" not in resposta.data
        assert resposta.get_json()["erro"]["codigo"] == "E404"


# ---------------------------------------------------------------------------
# Temporários e TTL
# ---------------------------------------------------------------------------

def _temporarios() -> set[Path]:
    import tempfile
    return set(Path(tempfile.gettempdir()).glob("nature-code-pdi-*"))


def test_upload_temporario_removido_quando_o_pipeline_rejeita(cliente) -> None:
    antes = _temporarios()
    resposta = _enviar(cliente, b"nao e imagem", nome="falso.jpg")
    assert resposta.status_code == 400
    assert _temporarios() == antes


def test_upload_temporario_removido_quando_nao_ha_folha(cliente) -> None:
    antes = _temporarios()
    vazia = cv2.imencode(".png", np.full((400, 400, 3), 250, dtype=np.uint8))[1].tobytes()
    assert _enviar(cliente, vazia).status_code == 422
    assert _temporarios() == antes


def test_upload_temporario_removido_quando_o_pipeline_explode(
    cliente, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exceção inesperada dentro do pipeline: temporário apagado e 500 sem rastreamento."""
    vistos: list[Path] = []

    def explodir(caminho, **_kwargs):
        vistos.append(Path(caminho))
        assert Path(caminho).exists()  # o temporário existia durante o processamento
        raise RuntimeError("falha interna simulada")

    monkeypatch.setattr(modulo_api, "processar_folha", explodir)
    antes = _temporarios()
    resposta = _enviar(cliente, _png_de_folha())

    assert resposta.status_code == 500
    assert resposta.get_json()["erro"]["codigo"] == "E500"
    assert b"falha interna simulada" not in resposta.data
    assert b"Traceback" not in resposta.data
    assert vistos and not vistos[0].exists()
    assert _temporarios() == antes


def test_api_limpa_execucoes_antigas_antes_de_processar(cliente) -> None:
    """A limpeza por idade roda a cada requisição de processamento."""
    import os
    import time

    pasta = modulo_api.PASTA_EXECUCOES
    antiga = pasta / ("c" * 32)
    antiga.mkdir(parents=True)
    (antiga / "07-final.png").write_bytes(b"x")
    velho = time.time() - 25 * 3600
    os.utime(antiga, (velho, velho))

    dados = _enviar(cliente, _png_de_folha()).get_json()

    assert not antiga.exists()
    assert (pasta / dados["id_execucao"]).is_dir()  # a nova execução foi preservada


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

def test_cors_libera_origem_local(cliente) -> None:
    resposta = cliente.get("/health", headers={"Origin": "http://localhost:8000"})
    assert resposta.headers.get("Access-Control-Allow-Origin") == "http://localhost:8000"


def test_cors_recusa_origem_externa(cliente) -> None:
    resposta = cliente.get("/health", headers={"Origin": "https://site-malicioso.example"})
    assert "Access-Control-Allow-Origin" not in resposta.headers


def test_cors_nao_usa_curinga() -> None:
    assert "*" not in ORIGENS_PERMITIDAS


def test_preflight(cliente) -> None:
    resposta = cliente.open("/api/processar-folha", method="OPTIONS",
                            headers={"Origin": "http://127.0.0.1:8000"})
    assert resposta.status_code == 204
    assert "POST" in resposta.headers.get("Access-Control-Allow-Methods", "")


# ---------------------------------------------------------------------------
# Configuração de segurança
# ---------------------------------------------------------------------------

def test_escuta_apenas_local() -> None:
    assert modulo_api.HOST_PADRAO == "127.0.0.1"


def test_debug_desligado() -> None:
    assert criar_app().debug is False


def test_limite_de_upload_configurado() -> None:
    assert criar_app().config["MAX_CONTENT_LENGTH"] == TAMANHO_MAXIMO_BYTES


# ---------------------------------------------------------------------------
# Consistência CLI × API
# ---------------------------------------------------------------------------

def test_cli_e_api_produzem_o_mesmo_resultado(cliente, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """A mesma imagem pelos dois caminhos: características e classificação idênticas."""
    import json

    from src.cli import main

    dados = _png_de_folha()
    arquivo = tmp_path / "folha.png"
    arquivo.write_bytes(dados)

    main([str(arquivo), "--json-apenas", "--sem-imagens"])
    pela_cli = json.loads(capsys.readouterr().out)
    pela_api = _enviar(cliente, dados).get_json()

    assert pela_cli["caracteristicas"] == pela_api["caracteristicas"]
    assert pela_cli["classificacao"] == pela_api["classificacao"]
    assert pela_cli["objeto"] == pela_api["objeto"]
