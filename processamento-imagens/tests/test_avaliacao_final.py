"""Testes da infraestrutura de avaliação final (Fase 10).

Garantem que o script de avaliação:

- seleciona exatamente as 96 imagens reservadas pelo manifesto, e nada mais;
- é uma casca: chama o pipeline congelado e não reimplementa nem altera nada dele;
- não usa a espécie como entrada, feature ou classificação;
- produz JSON/CSV válidos, sem NaN, e não aborta quando uma imagem falha.

Os testes de ponta a ponta usam imagens **sintéticas** num manifesto temporário —
nenhuma imagem do dataset é aberta aqui.
"""

from __future__ import annotations

import ast
import csv
import json
import math
import re
from pathlib import Path

import cv2
import numpy as np
import pytest

import avaliar_conjunto_final as av

SCRIPT = Path(av.__file__)


# ---------------------------------------------------------------------------
# Seleção pelo manifesto real (sem abrir imagens)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def manifesto_real() -> tuple[list[dict], list[dict]]:
    todas = av.ler_manifesto()
    return todas, av.selecionar_avaliacao(todas)


def test_le_exatamente_96_de_avaliacao(manifesto_real) -> None:
    _todas, avaliacao = manifesto_real
    assert len(avaliacao) == 96
    assert all(linha["uso"] == "avaliacao" for linha in avaliacao)


def test_32_especies_com_3_imagens_cada(manifesto_real) -> None:
    _todas, avaliacao = manifesto_real
    contagem: dict[str, int] = {}
    for linha in avaliacao:
        contagem[linha["classe_original"]] = contagem.get(linha["classe_original"], 0) + 1
    assert len(contagem) == 32
    assert set(contagem.values()) == {3}


def test_desenvolvimento_fica_fora(manifesto_real) -> None:
    todas, avaliacao = manifesto_real
    desenvolvimento = {l["arquivo"] for l in todas if l["uso"] == "desenvolvimento"}
    assert len(desenvolvimento) == 64
    assert not desenvolvimento & {l["arquivo"] for l in avaliacao}


def test_sem_duplicatas_e_sem_amostra(manifesto_real) -> None:
    _todas, avaliacao = manifesto_real
    nomes = [l["arquivo"] for l in avaliacao]
    assert len(nomes) == len(set(nomes))
    for linha in avaliacao:
        caminho = av.caminho_da_imagem(linha)
        assert "amostra" not in str(caminho).lower()
        assert caminho.parent == av.PASTA_IMAGENS


def test_selecao_real_e_valida(manifesto_real) -> None:
    todas, avaliacao = manifesto_real
    assert av.validar_selecao(todas, avaliacao, conferir_arquivos=False) == []


@pytest.mark.skipif(not av.PASTA_IMAGENS.is_dir(), reason="dataset não baixado")
def test_arquivos_de_avaliacao_existem(manifesto_real) -> None:
    todas, avaliacao = manifesto_real
    assert av.validar_selecao(todas, avaliacao, conferir_arquivos=True) == []


# ---------------------------------------------------------------------------
# A validação detecta seleções erradas
# ---------------------------------------------------------------------------

def _linha(arquivo: str, classe: str, uso: str = "avaliacao") -> dict[str, str]:
    return {"arquivo": arquivo, "classe_original": classe, "uso": uso}


def _selecao_valida() -> list[dict[str, str]]:
    return [_linha(f"{e:02d}{i}.jpg", f"{e:02d}-Especie {e}") for e in range(1, 33) for i in range(3)]


def test_validacao_aceita_selecao_bem_formada() -> None:
    selecao = _selecao_valida()
    assert av.validar_selecao(selecao, selecao, conferir_arquivos=False) == []


@pytest.mark.parametrize("defeito", ["falta", "duplicata", "desenvolvimento", "especie_com_2", "amostra"])
def test_validacao_detecta_defeito(defeito: str, tmp_path: Path) -> None:
    selecao = _selecao_valida()
    todas = list(selecao)
    pasta = av.PASTA_IMAGENS

    if defeito == "falta":
        selecao = selecao[:-1]
    elif defeito == "duplicata":
        selecao[1] = dict(selecao[0])
    elif defeito == "desenvolvimento":
        todas = todas + [_linha(selecao[0]["arquivo"], selecao[0]["classe_original"], "desenvolvimento")]
    elif defeito == "especie_com_2":
        selecao[2] = _linha("x.jpg", "02-Especie 2")
    elif defeito == "amostra":
        pasta = tmp_path / "amostra-flavia"

    assert av.validar_selecao(todas, selecao, pasta=pasta, conferir_arquivos=False)


# ---------------------------------------------------------------------------
# Casca: o script não reimplementa nem altera o pipeline
# ---------------------------------------------------------------------------

def _imports(caminho: Path) -> set[str]:
    nomes: set[str] = set()
    for no in ast.walk(ast.parse(caminho.read_text(encoding="utf-8"))):
        if isinstance(no, ast.Import):
            nomes.update(a.name for a in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            nomes.add(no.module)
    return nomes


def test_script_nao_importa_opencv_nem_numpy() -> None:
    importados = {n.split(".")[0] for n in _imports(SCRIPT)}
    assert "cv2" not in importados
    assert "numpy" not in importados


def test_script_usa_somente_o_pipeline_central() -> None:
    internos = {n for n in _imports(SCRIPT) if n.startswith("src")}
    assert internos == {"src.pipeline"}
    assert "processar_folha(" in SCRIPT.read_text(encoding="utf-8")


def _codigo_sem_docstrings(caminho: Path) -> str:
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        corpo = getattr(no, "body", None)
        if isinstance(corpo, list) and corpo and isinstance(corpo[0], ast.Expr) \
                and isinstance(getattr(corpo[0], "value", None), ast.Constant) \
                and isinstance(corpo[0].value.value, str):
            corpo[0] = ast.Pass()
    return ast.unparse(arvore)


def test_script_nao_duplica_parametros_nem_etapas() -> None:
    """Nenhum nome de parâmetro ou função de processamento aparece no código."""
    codigo = _codigo_sem_docstrings(SCRIPT)
    for proibido in ("FAIXA_VERDE", "KERNEL", "LADO_MAXIMO", "Limiares", "LIMIARES",
                     "segmentar_hsv", "limpar_mascara", "analisar_contorno",
                     "extrair_caracteristicas", "classificar_", "GaussianBlur", "inRange",
                     "minAreaRect", "findContours", "limiar"):
        assert proibido not in codigo, f"o script menciona {proibido}"


def test_script_nao_altera_constantes_do_pipeline() -> None:
    codigo = _codigo_sem_docstrings(SCRIPT)
    assert "setattr" not in codigo
    assert not re.search(r"\b(pipeline|src)\.\w+\s*=", codigo)
    for no in ast.walk(ast.parse(codigo)):
        if isinstance(no, (ast.Assign, ast.AugAssign)):
            alvos = no.targets if isinstance(no, ast.Assign) else [no.target]
            for alvo in alvos:
                assert not (isinstance(alvo, ast.Attribute) and isinstance(alvo.value, ast.Name)
                            and alvo.value.id in {"pipeline", "src", "av"})


def test_pipeline_recebe_so_o_caminho(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A espécie nunca é passada ao pipeline."""
    chamadas = []
    monkeypatch.setattr(av, "processar_folha",
                        lambda *a, **k: chamadas.append((a, k)) or {"status": "erro", "erro": {"codigo": "X", "mensagem": ""}})
    av.processar_uma(tmp_path / "1009.jpg")

    (argumentos, nomeados), = chamadas
    assert argumentos == (tmp_path / "1009.jpg",)
    assert nomeados == {"salvar_imagens": False}


# ---------------------------------------------------------------------------
# Estatística
# ---------------------------------------------------------------------------

def test_percentil_linear_igual_ao_numpy() -> None:
    valores = [3.0, 1.0, 4.0, 1.5, 9.0, 2.6, 5.0]
    for p in (0, 5, 25, 50, 75, 95, 100):
        assert av.percentil(valores, p) == pytest.approx(float(np.percentile(valores, p)))


def test_descrever_ignora_none_e_nao_finitos_sem_remover_outlier() -> None:
    resumo = av.descrever([1.0, None, float("nan"), float("inf"), 2.0, 1000.0])
    assert resumo["n"] == 3
    assert resumo["maximo"] == 1000.0  # outlier mantido
    assert all(math.isfinite(v) for k, v in resumo.items() if k != "n")


def test_indices_de_determinismo() -> None:
    indices = av.indices_determinismo(96)
    assert indices[0] == 0 and indices[-1] == 95
    assert len(indices) == 5


# ---------------------------------------------------------------------------
# Ponta a ponta com imagens sintéticas
# ---------------------------------------------------------------------------

@pytest.fixture
def conjunto_sintetico(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Manifesto com 2 'espécies' × 3 imagens: 4 folhas, 1 sem folha, 1 corrompida."""
    pasta = tmp_path / "Leaves"
    pasta.mkdir()

    def folha(nome: str, a: int, b: int, angulo: int) -> None:
        tela = np.full((600, 800, 3), 250, np.uint8)
        cv2.ellipse(tela, (400, 300), (a, b), angulo, 0, 360, (40, 140, 60), -1)
        cv2.imwrite(str(pasta / nome), tela)

    folha("1.png", 250, 100, 10)
    folha("2.png", 200, 180, 40)
    folha("3.png", 300, 40, 70)
    folha("4.png", 150, 90, 0)
    cv2.imwrite(str(pasta / "5.png"), np.full((500, 500, 3), 250, np.uint8))   # E007
    (pasta / "6.jpg").write_text("nao e imagem")                                  # E003

    manifesto = tmp_path / "manifesto.csv"
    with open(manifesto, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["arquivo", "dataset_origem", "classe_original", "uso", "subconjunto", "observacao"])
        for nome, classe in (("1.png", "01-A"), ("2.png", "01-A"), ("3.png", "01-A"),
                             ("4.png", "02-B"), ("5.png", "02-B"), ("6.jpg", "02-B")):
            w.writerow([nome, "sintetico", classe, "avaliacao", "t", ""])
        w.writerow(["7.png", "sintetico", "01-A", "desenvolvimento", "t", ""])

    saida = tmp_path / "saida"
    monkeypatch.setattr(av, "MANIFESTO", manifesto)
    monkeypatch.setattr(av, "PASTA_IMAGENS", pasta)
    monkeypatch.setattr(av, "PASTA_SAIDA", saida)
    monkeypatch.setattr(av, "TOTAL_ESPERADO", 6)
    monkeypatch.setattr(av, "ESPECIES_ESPERADAS", 2)
    return saida


def test_avaliacao_ponta_a_ponta(conjunto_sintetico: Path) -> None:
    assert av.avaliar() == 0

    completos = json.loads((conjunto_sintetico / "fase10-resultados-completos.json").read_text(encoding="utf-8"))
    resumo = json.loads((conjunto_sintetico / "fase10-resumo.json").read_text(encoding="utf-8"))
    linhas = list(csv.DictReader(open(conjunto_sintetico / "fase10-resultados.csv", encoding="utf-8")))

    assert len(completos["resultados"]) == 6
    assert len(linhas) == 6
    assert "7.png" not in {l["arquivo"] for l in linhas}  # desenvolvimento fora

    assert resumo["cobertura"]["erro"] == 2
    assert resumo["erros"]["por_codigo"]["E007"]["imagens"] == ["5.png"]
    assert resumo["erros"]["por_codigo"]["E003"]["imagens"] == ["6.jpg"]
    assert resumo["cobertura"]["taxa_processamento_valido_pct"] == pytest.approx(66.67)
    assert resumo["determinismo"]["todas_identicas"] is True
    assert {c["arquivo"] for c in resumo["inspecao_selecionada"]} >= {"5.png", "6.jpg"}


def test_saidas_sem_nan_e_sem_caminho_absoluto(conjunto_sintetico: Path) -> None:
    av.avaliar()
    for nome in ("fase10-resultados-completos.json", "fase10-resumo.json"):
        texto = (conjunto_sintetico / nome).read_text(encoding="utf-8")
        json.loads(texto, parse_constant=lambda c: pytest.fail(f"{c} em {nome}"))
        assert str(conjunto_sintetico.parent) not in texto
        assert "\\\\" not in texto and ":/" not in texto.replace("://", "")


def test_erro_de_uma_imagem_nao_aborta_o_conjunto(conjunto_sintetico: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original = av.processar_folha

    def explode_na_segunda(caminho, **kwargs):
        if Path(caminho).name == "2.png":
            raise RuntimeError("falha simulada")
        return original(caminho, **kwargs)

    monkeypatch.setattr(av, "processar_folha", explode_na_segunda)
    assert av.avaliar() == 0

    linhas = list(csv.DictReader(open(conjunto_sintetico / "fase10-resultados.csv", encoding="utf-8")))
    assert len(linhas) == 6
    segunda = next(l for l in linhas if l["arquivo"] == "2.png")
    assert segunda["status"] == "erro"
    assert segunda["erro_codigo"] == "EXCECAO_NAO_TRATADA"
    assert "falha simulada" in segunda["erro_mensagem"]


def test_especie_nao_e_feature_nem_classificacao(conjunto_sintetico: Path) -> None:
    av.avaliar()
    linhas = list(csv.DictReader(open(conjunto_sintetico / "fase10-resultados.csv", encoding="utf-8")))
    for linha in linhas:
        for atributo in av.ATRIBUTOS:
            assert linha[f"cat_{atributo}"] in (*av.CATEGORIAS[atributo], "")
    colunas_com_especie = {c for c in linhas[0] if "especie" in c}
    assert colunas_com_especie == {"especie_id", "especie"}

    resumo = json.loads((conjunto_sintetico / "fase10-resumo.json").read_text(encoding="utf-8"))
    texto = json.dumps(resumo).lower()
    for proibido in ("acuracia", "precisao", "recall", "f1", "matriz_confusao", "acerto"):
        assert proibido not in texto


def test_inspecao_limitada_e_sem_duplicatas(conjunto_sintetico: Path) -> None:
    av.avaliar()
    casos = list(csv.DictReader(open(conjunto_sintetico / "fase10-casos-inspecao.csv", encoding="utf-8")))
    nomes = [c["arquivo"] for c in casos]
    assert len(nomes) == len(set(nomes)) <= av.LIMITE_INSPECAO
    assert all(c["inspecao_humana"] == "" for c in casos)  # julgamento é humano


def test_selecao_invalida_nao_executa(conjunto_sintetico: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(av, "TOTAL_ESPERADO", 7)
    assert av.avaliar() == 2
    assert not (conjunto_sintetico / "fase10-resultados.csv").exists()
