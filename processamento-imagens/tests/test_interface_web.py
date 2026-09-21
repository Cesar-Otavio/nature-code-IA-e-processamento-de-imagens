"""Testes da integração web: navegação, caminhos e comportamento do JavaScript.

Três grupos:

1. **Navegação estática** — o botão em ``plantas.html`` existe, os ``href``/``src`` da
   página nova apontam para arquivos reais, nada depende de ``file://``.
2. **Validação de respostas** — ``validacao-pdi.js`` executado no Node.
3. **Comportamento da interface** — ``analise-folha.js`` executado no Node com DOM
   simulado (``tests/js/interface_pdi.js``): API fora do ar, JSON inválido, erro da
   API, URL maliciosa, tempo esgotado, troca de imagem, liberação dos ``blob:``.

Os grupos 2 e 3 precisam do Node, que o projeto já usa nas suítes da camada de IA.
Sem Node, são pulados — e o pulo aparece no relatório do pytest.

**Nada disto substitui abrir a página num navegador de verdade.**
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

from src import api as modulo_api
from src import pipeline
from src.api import criar_app

RAIZ = Path(__file__).resolve().parents[2]
MODULOS = RAIZ / "pages" / "modulos"
PAGINA = MODULOS / "analise-folha.html"
PLANTAS = MODULOS / "plantas.html"
PASTA_PDI = RAIZ / "script" / "pdi"
HARNESS = Path(__file__).resolve().parent / "js" / "interface_pdi.js"

NODE = shutil.which("node")
precisa_node = pytest.mark.skipif(NODE is None, reason="Node.js não encontrado")


class _Coletor(HTMLParser):
    """Coleta links, scripts e ids — ignorando o que está dentro de comentários."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []  # (tag, url)
        self.scripts: list[str] = []
        self.ids: set[str] = set()
        self.ancoras: list[tuple[str, str]] = []  # (href, texto)
        self._ancora: str | None = None
        self._texto: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        if "id" in a:
            self.ids.add(a["id"])
        for chave in ("href", "src"):
            if chave in a:
                self.links.append((tag, a[chave]))
        if tag == "script" and "src" in a:
            self.scripts.append(a["src"])
        if tag == "a":
            self._ancora, self._texto = a.get("href", ""), []

    def handle_data(self, data: str) -> None:
        if self._ancora is not None:
            self._texto.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._ancora is not None:
            self.ancoras.append((self._ancora, " ".join("".join(self._texto).split())))
            self._ancora = None


def _coletar(caminho: Path) -> _Coletor:
    coletor = _Coletor()
    coletor.feed(caminho.read_text(encoding="utf-8"))
    return coletor


def _local(url: str) -> bool:
    return not re.match(r"^(https?:)?//", url) and not url.startswith(("#", "data:", "mailto:"))


# ---------------------------------------------------------------------------
# 1. Navegação estática
# ---------------------------------------------------------------------------

def test_plantas_tem_link_visivel_para_a_ferramenta() -> None:
    ancoras = _coletar(PLANTAS).ancoras
    alvo = [(href, txt) for href, txt in ancoras if href.endswith("analise-folha.html")]

    assert alvo, "plantas.html não tem âncora para analise-folha.html (fora de comentário)"
    href, texto = alvo[0]
    assert "Análise Morfológica de Folhas" in texto
    assert (PLANTAS.parent / href).resolve() == PAGINA.resolve()


def test_pagina_volta_para_plantas() -> None:
    ancoras = _coletar(PAGINA).ancoras
    voltar = [href for href, txt in ancoras if txt.upper() == "VOLTAR"]

    assert voltar
    assert (PAGINA.parent / voltar[0]).resolve() == PLANTAS.resolve()


@pytest.mark.parametrize("pagina", [PAGINA, PLANTAS], ids=["analise-folha", "plantas"])
def test_todo_recurso_local_existe(pagina: Path) -> None:
    """Cada href/src relativo resolve para um arquivo real a partir de pages/modulos/."""
    faltando = []
    for tag, url in _coletar(pagina).links:
        if not _local(url):
            continue
        destino = (pagina.parent / url.split("#")[0].split("?")[0]).resolve()
        if not destino.exists():
            faltando.append(f"<{tag}> {url}")
    assert not faltando, f"recursos inexistentes em {pagina.name}: {faltando}"


def test_scripts_do_pdi_carregam_na_ordem_certa() -> None:
    scripts = [Path(s).name for s in _coletar(PAGINA).scripts if "/pdi/" in s]
    assert scripts == ["config-pdi.js", "validacao-pdi.js", "analise-folha.js"]


def test_todo_id_usado_pelo_js_existe_na_pagina() -> None:
    codigo = (PASTA_PDI / "analise-folha.js").read_text(encoding="utf-8")
    usados = set(re.findall(r'\$\(\s*"([\w-]+)"\s*\)', codigo))
    usados |= set(re.findall(r'"(img-(?:original|mascara|final))"', codigo))

    ausentes = usados - _coletar(PAGINA).ids
    assert not ausentes, f"ids usados no JS e ausentes no HTML: {sorted(ausentes)}"


def test_cada_imagem_de_etapa_tem_aviso_de_indisponivel() -> None:
    html = PAGINA.read_text(encoding="utf-8")
    for id_img in ("img-original", "img-mascara", "img-final"):
        trecho = html[html.index(f'id="{id_img}"'):]
        trecho = trecho[:trecho.index("</figure>")]
        assert 'class="img-indisponivel"' in trecho


def test_nada_depende_de_file_protocol() -> None:
    arquivos = [PAGINA, PLANTAS, *PASTA_PDI.glob("*.js")]
    for arquivo in arquivos:
        assert "file://" not in arquivo.read_text(encoding="utf-8"), arquivo.name


def test_api_configurada_em_endereco_local() -> None:
    config = (PASTA_PDI / "config-pdi.js").read_text(encoding="utf-8")
    url = re.search(r'urlBase:\s*"([^"]+)"', config).group(1)
    assert re.fullmatch(r"http://(127\.0\.0\.1|localhost):\d+", url)


def test_origem_do_http_server_esta_no_cors() -> None:
    """O site servido por `python -m http.server 8000` é uma origem aceita pela API."""
    assert "http://localhost:8000" in modulo_api.ORIGENS_PERMITIDAS
    assert "http://127.0.0.1:8000" in modulo_api.ORIGENS_PERMITIDAS


def _js_sem_comentarios(codigo: str) -> str:
    codigo = re.sub(r"/\*.*?\*/", "", codigo, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", codigo)


@pytest.mark.parametrize("arquivo", sorted(p.name for p in PASTA_PDI.glob("*.js")))
def test_js_do_pdi_nao_injeta_html(arquivo: str) -> None:
    codigo = _js_sem_comentarios((PASTA_PDI / arquivo).read_text(encoding="utf-8"))
    for proibido in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("):
        assert proibido not in codigo, f"{arquivo} usa {proibido}"


def test_js_nao_mostra_detalhe_tecnico_ao_usuario() -> None:
    """Mensagem de exceção e stack vão para o console, nunca para a tela."""
    codigo = _js_sem_comentarios((PASTA_PDI / "analise-folha.js").read_text(encoding="utf-8"))
    for chamada in re.findall(r"mostrarErro\(([^;]*)\);", codigo, flags=re.S):
        assert "erro.message" not in chamada and ".stack" not in chamada


# ---------------------------------------------------------------------------
# 2 e 3. JavaScript executado no Node
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def resposta_real(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Resposta verdadeira da API (cliente de teste) para alimentar a interface."""
    import cv2
    import numpy as np

    pasta = tmp_path_factory.mktemp("execucoes")
    original = pipeline.PASTA_EXECUCOES, modulo_api.PASTA_EXECUCOES
    pipeline.PASTA_EXECUCOES = modulo_api.PASTA_EXECUCOES = pasta
    try:
        tela = np.full((700, 900, 3), 250, dtype=np.uint8)
        cv2.ellipse(tela, (450, 350), (280, 110), 25, 0, 360, (40, 140, 60), -1)
        import io
        dados = cv2.imencode(".png", tela)[1].tobytes()
        cliente = criar_app().test_client()
        corpo = cliente.post(
            "/api/processar-folha",
            data={"imagem": (io.BytesIO(dados), "folha.png")},
            content_type="multipart/form-data",
        ).get_json()
    finally:
        pipeline.PASTA_EXECUCOES, modulo_api.PASTA_EXECUCOES = original

    assert corpo["status"] in ("sucesso", "sucesso_com_avisos")
    destino = tmp_path_factory.mktemp("resposta") / "resposta.json"
    destino.write_text(json.dumps(corpo), encoding="utf-8")
    return destino


def _node(script: str) -> object:
    saida = subprocess.run([NODE, "-e", script], capture_output=True, text=True, timeout=60, check=True)
    return json.loads(saida.stdout)


@precisa_node
def test_validacao_aceita_a_resposta_real_da_api(resposta_real: Path) -> None:
    """O validador do JS e o contrato do Python concordam."""
    caminho_js = json.dumps(str(PASTA_PDI / "validacao-pdi.js"))
    caminho_json = json.dumps(str(resposta_real))
    problemas = _node(
        f"const V=require({caminho_js});const fs=require('fs');"
        f"console.log(JSON.stringify(V.problemasDaResposta(JSON.parse(fs.readFileSync({caminho_json},'utf-8')))));"
    )
    assert problemas == []


@precisa_node
def test_validacao_de_url_de_imagem() -> None:
    hexa = "a" * 32
    casos = {
        f"/api/resultado/{hexa}/07-final.png": True,
        f"/api/resultado/{hexa}/05-mascara-limpa.png": True,
        "https://site-malicioso.example/x.png": False,
        f"//site-malicioso.example/api/resultado/{hexa}/07-final.png": False,
        "/api/resultado/../../src/api.py": False,
        f"/api/resultado/{hexa}/..%2F..%2Fsrc%2Fapi.py": False,
        f"/api/resultado/{hexa}/07-final.jpg": False,
        "/api/resultado/naoehex/07-final.png": False,
        f"/api/resultado/{hexa}/07-final.png?x=1": False,
        "javascript:alert(1)": False,
        "": False,
    }
    caminho_js = json.dumps(str(PASTA_PDI / "validacao-pdi.js"))
    entradas = json.dumps(list(casos) + [None, 123])
    resultados = _node(
        f"const V=require({caminho_js});"
        f"console.log(JSON.stringify({entradas}.map(c=>V.urlDeImagemSegura(c,'http://127.0.0.1:5000'))));"
    )
    for (caminho, aceita), resultado in zip(casos.items(), resultados):
        assert (resultado is not None) == aceita, caminho
        if aceita:
            assert resultado == "http://127.0.0.1:5000" + caminho
    assert resultados[-2:] == [None, None]


@precisa_node
def test_validacao_recusa_formatos_inesperados() -> None:
    caminho_js = json.dumps(str(PASTA_PDI / "validacao-pdi.js"))
    formatos = [None, [], {}, {"status": "x"}, {"status": "erro"}, {"status": "erro", "erro": {}},
                {"status": "sucesso"}, {"status": "sucesso", "caracteristicas": {}, "classificacao": {}}]
    resultados = _node(
        f"const V=require({caminho_js});"
        f"console.log(JSON.stringify({json.dumps(formatos)}.map(f=>V.problemasDaResposta(f).length)));"
    )
    assert all(n > 0 for n in resultados), resultados


CENARIOS = [
    "api_offline",
    "json_invalido",
    "json_formato_inesperado",
    "erro_da_api_e_nova_tentativa",
    "sucesso_com_resposta_real",
    "url_de_imagem_maliciosa",
    "imagem_que_falha_ao_carregar",
    "tempo_esgotado",
    "troca_de_imagem_durante_analise",
    "preview_e_revoke",
]


@precisa_node
@pytest.mark.parametrize("cenario", CENARIOS)
def test_comportamento_da_interface(cenario: str, resposta_real: Path) -> None:
    saida = subprocess.run(
        [NODE, str(HARNESS), str(RAIZ), cenario, str(resposta_real)],
        capture_output=True, text=True, timeout=60,
    )
    assert saida.returncode == 0, saida.stderr
    resultado = json.loads(saida.stdout.strip().splitlines()[-1])
    assert resultado["ok"], "\n".join(resultado["falhas"])
