"""Verifica que o módulo de PDI não usa Inteligência Artificial.

A regra da disciplina — *sem IA, sem aprendizado de máquina* — é verificada por
execução, não por promessa de documentação. É o mesmo princípio que a Fase 6 da
etapa de IA adotou ao comparar hashes de prompt em vez de afirmar que eram iguais.

A varredura é sintática e deliberadamente conservadora: detecta violações óbvias,
não prova ausência semântica. Uma violação detectada aqui é certamente real; a
ausência de detecção não é prova formal — apenas evidência forte.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

RAIZ_MODULO = Path(__file__).resolve().parent.parent
RAIZ_PROJETO = RAIZ_MODULO.parent

#: Bibliotecas de aprendizado de máquina e visão por IA.
BIBLIOTECAS_PROIBIDAS = frozenset({
    "torch", "torchvision", "tensorflow", "keras", "jax", "flax",
    "sklearn", "scikit_learn", "xgboost", "lightgbm", "catboost",
    "ultralytics", "yolo", "yolov5", "yolov8",
    "transformers", "huggingface_hub", "timm", "onnx", "onnxruntime",
    "openai", "anthropic", "ollama", "langchain", "llama_cpp",
    "mediapipe", "dlib", "caffe", "mxnet", "paddle", "paddlepaddle",
})

#: Termos que denunciam uso de IA mesmo sem import — inclusive o módulo de redes
#: neurais do próprio OpenCV, que é a violação mais fácil de cometer sem perceber.
TERMOS_PROIBIDOS = (
    r"cv2\.dnn",
    r"\bdnn_superres\b",
    r"readNetFrom\w*",
    r"\bscript/ia\b",
    r"\bconfig-ia\b",
    r"\bprompt-quiz\b",
    r"\bservico-quiz\b",
    r"localhost:11434",
    r"\bapi/chat\b",
)

#: Clientes HTTP: o módulo não deve chamar serviço externo de reconhecimento.
CLIENTES_HTTP = frozenset({"requests", "httpx", "urllib3", "aiohttp"})


def _arquivos_python() -> list[Path]:
    """Todos os .py do módulo, exceto o ambiente virtual."""
    return [
        caminho
        for caminho in RAIZ_MODULO.rglob("*.py")
        if ".venv" not in caminho.parts and "__pycache__" not in caminho.parts
    ]


def _codigo_sem_docstrings(caminho: Path) -> str:
    """Devolve o texto do arquivo com as docstrings removidas.

    A varredura por termos proibidos deve olhar **código**, não documentação: uma
    docstring que diz "este módulo não importa ``script/ia``" é o oposto de uma
    violação, e reprová-la forçaria a piorar a documentação para agradar o teste.

    Comentários e strings comuns **permanecem** no texto analisado — só as
    docstrings de módulo, classe e função são retiradas.
    """
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    arvore = ast.parse("\n".join(linhas), filename=str(caminho))

    a_remover: set[int] = set()
    for no in ast.walk(arvore):
        if not isinstance(no, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        corpo = getattr(no, "body", [])
        if not corpo:
            continue
        primeiro = corpo[0]
        if (
            isinstance(primeiro, ast.Expr)
            and isinstance(primeiro.value, ast.Constant)
            and isinstance(primeiro.value.value, str)
        ):
            fim = primeiro.end_lineno or primeiro.lineno
            a_remover.update(range(primeiro.lineno, fim + 1))

    return "\n".join(linha for numero, linha in enumerate(linhas, 1) if numero not in a_remover)


def _imports_de(caminho: Path) -> set[str]:
    """Extrai os módulos de topo importados, por análise da árvore sintática.

    Usar ``ast`` em vez de expressão regular evita falso positivo em comentário,
    docstring ou string literal — como as listas deste próprio arquivo.
    """
    arvore = ast.parse(caminho.read_text(encoding="utf-8"), filename=str(caminho))
    encontrados: set[str] = set()

    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for alias in no.names:
                encontrados.add(alias.name.split(".")[0].lower())
        elif isinstance(no, ast.ImportFrom) and no.module:
            encontrados.add(no.module.split(".")[0].lower())

    return encontrados


def test_ha_arquivos_python_para_verificar() -> None:
    """Guarda contra a suíte passar por não encontrar nada."""
    assert len(_arquivos_python()) >= 3


@pytest.mark.parametrize("caminho", _arquivos_python(), ids=lambda p: p.name)
def test_nenhum_import_de_biblioteca_de_ia(caminho: Path) -> None:
    proibidos = _imports_de(caminho) & BIBLIOTECAS_PROIBIDAS
    assert not proibidos, f"{caminho.name} importa biblioteca de IA: {sorted(proibidos)}"


@pytest.mark.parametrize("caminho", _arquivos_python(), ids=lambda p: p.name)
def test_nenhum_cliente_http_externo(caminho: Path) -> None:
    """O módulo é offline: não chama API externa de reconhecimento visual."""
    clientes = _imports_de(caminho) & CLIENTES_HTTP
    assert not clientes, f"{caminho.name} importa cliente HTTP: {sorted(clientes)}"


def test_nenhum_termo_proibido_no_codigo() -> None:
    """Varre o código por marcas de IA, incluindo cv2.dnn.

    Este próprio arquivo é pulado: ele contém os termos por definição. Docstrings
    são excluídas da varredura — ver ``_codigo_sem_docstrings``.
    """
    violacoes: list[str] = []

    for caminho in _arquivos_python():
        if caminho.name == "test_isolamento.py":
            continue
        texto = _codigo_sem_docstrings(caminho)
        for padrao in TERMOS_PROIBIDOS:
            if re.search(padrao, texto, flags=re.IGNORECASE):
                violacoes.append(f"{caminho.name}: {padrao}")

    assert not violacoes, f"Termos proibidos encontrados: {violacoes}"


def test_modulo_nao_referencia_a_camada_de_ia_do_site() -> None:
    """Nenhum caminho relativo alcança script/ia/."""
    violacoes: list[str] = []

    for caminho in _arquivos_python():
        if caminho.name == "test_isolamento.py":
            continue
        if re.search(r"script[/\\]ia", _codigo_sem_docstrings(caminho), flags=re.IGNORECASE):
            violacoes.append(caminho.name)

    assert not violacoes, f"Referência à camada de IA em: {violacoes}"


def test_camada_de_ia_do_site_nao_referencia_o_modulo_de_pdi() -> None:
    """A independência vale nos dois sentidos.

    A camada de IA não pode importar, chamar ou mencionar o módulo de PDI.
    """
    pasta_ia = RAIZ_PROJETO / "script" / "ia"
    if not pasta_ia.is_dir():
        pytest.skip("camada de IA não encontrada neste checkout")

    violacoes: list[str] = []
    for arquivo in pasta_ia.glob("*.js"):
        texto = arquivo.read_text(encoding="utf-8")
        if re.search(r"processamento[-_]imagens|opencv|\bcv2\b", texto, flags=re.IGNORECASE):
            violacoes.append(arquivo.name)

    assert not violacoes, f"A camada de IA referencia o módulo de PDI em: {violacoes}"


def test_a_varredura_ainda_detecta_violacao_real(tmp_path: Path) -> None:
    """Prova que excluir docstrings não cegou o detector.

    Sem este teste, ``_codigo_sem_docstrings`` poderia ter afrouxado a verificação
    sem que ninguém percebesse — o detector passaria a aprovar tudo.
    """
    violador = tmp_path / "violador.py"
    violador.write_text(
        '"""Docstring inocente, sem termo nenhum."""\n'
        "import torch\n"
        "modelo = cv2.dnn.readNetFromONNX('rede.onnx')\n"
        "resposta = 'localhost:11434'\n",
        encoding="utf-8",
    )

    codigo = _codigo_sem_docstrings(violador)

    assert "torch" in _imports_de(violador)
    assert re.search(r"cv2\.dnn", codigo)
    assert re.search(r"readNetFrom\w*", codigo)
    assert re.search(r"localhost:11434", codigo)


def test_a_varredura_ignora_termo_apenas_em_docstring(tmp_path: Path) -> None:
    """E prova o outro lado: documentação que cita o termo não é violação."""
    documentado = tmp_path / "documentado.py"
    documentado.write_text(
        '"""Este módulo não importa script/ia nem usa cv2.dnn."""\n'
        "valor = 42\n",
        encoding="utf-8",
    )

    codigo = _codigo_sem_docstrings(documentado)

    assert "script/ia" not in codigo
    assert "cv2.dnn" not in codigo
    assert "valor = 42" in codigo


def test_dependencias_instaladas_nao_incluem_biblioteca_de_ia() -> None:
    """Confere o ambiente de verdade, não apenas o código.

    Uma biblioteca de IA instalada no ambiente é um risco mesmo sem import: ela
    acabaria no ``requirements.txt`` gerado por congelamento.
    """
    import importlib.metadata as metadata

    instalados = {dist.metadata["Name"].lower().replace("-", "_") for dist in metadata.distributions() if dist.metadata["Name"]}
    proibidos = instalados & BIBLIOTECAS_PROIBIDAS

    assert not proibidos, f"Bibliotecas de IA no ambiente: {sorted(proibidos)}"
