"""Testes da infraestrutura da avaliação de robustez com fotos externas (Fase 11).

Todas as imagens aqui são **sintéticas**, geradas em ``tmp_path``. Elas validam só a
infraestrutura — manifesto, erros, serialização — e **não** são fotos externas: nenhum
resultado destes testes entra na documentação científica da Fase 11.
"""

from __future__ import annotations

import ast
import csv
import json
import re
from pathlib import Path

import cv2
import numpy as np
import pytest

import avaliar_fotos_externas as ext

SCRIPT = Path(ext.__file__)
CABECALHO = "id,arquivo,fundo,iluminacao,posicao,distancia,formato,observacao\n"


# ---------------------------------------------------------------------------
# Ambiente isolado
# ---------------------------------------------------------------------------

@pytest.fixture
def ambiente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    pastas = {
        "fotos": tmp_path / "fotos-externas",
        "imagens": tmp_path / "fotos-externas" / "imagens",
        "saida": tmp_path / "dados-robustez",
        "visual": tmp_path / "robustez-fase11",
    }
    pastas["imagens"].mkdir(parents=True)
    pastas["manifesto"] = pastas["fotos"] / "manifesto.csv"
    pastas["manifesto"].write_text(CABECALHO, encoding="utf-8")
    monkeypatch.setattr(ext, "MANIFESTO", pastas["manifesto"])
    monkeypatch.setattr(ext, "PASTA_IMAGENS", pastas["imagens"])
    monkeypatch.setattr(ext, "PASTA_SAIDA", pastas["saida"])
    monkeypatch.setattr(ext, "PASTA_VISUAL", pastas["visual"])
    return pastas


def _folha(caminho: Path, a: int = 220, b: int = 90) -> None:
    tela = np.full((600, 800, 3), 250, np.uint8)
    cv2.ellipse(tela, (400, 300), (a, b), 20, 0, 360, (40, 140, 60), -1)
    cv2.imwrite(str(caminho), tela)


def _manifesto(ambiente: dict[str, Path], *linhas: str) -> None:
    ambiente["manifesto"].write_text(CABECALHO + "".join(l + "\n" for l in linhas), encoding="utf-8")


def _linha(id_: str, arquivo: str, formato: str = "JPG", fundo: str = "claro") -> str:
    return f"{id_},{arquivo},{fundo},natural,centralizada,media,{formato},"


# ---------------------------------------------------------------------------
# Sem fotos: encerramento controlado
# ---------------------------------------------------------------------------

def test_manifesto_vazio_encerra_sem_erro(ambiente, capsys: pytest.CaptureFixture) -> None:
    assert ext.main([]) == 0
    saida = capsys.readouterr().out
    assert "Nenhuma foto externa disponível" in saida
    assert "fotos-externas/imagens/" in saida
    assert not ambiente["saida"].exists()  # nenhum resultado gerado


def test_manifesto_ausente_encerra_sem_erro(ambiente, capsys: pytest.CaptureFixture) -> None:
    ambiente["manifesto"].unlink()
    assert ext.main([]) == 0
    assert "Nenhuma foto externa disponível" in capsys.readouterr().out


def test_manifesto_preenchido_sem_imagens_encerra_sem_erro(ambiente, capsys: pytest.CaptureFixture) -> None:
    _manifesto(ambiente, _linha("EXT001", "folha-01.jpg"))
    assert ext.main([]) == 0
    assert "Nenhuma foto externa disponível" in capsys.readouterr().out


def test_verificar_e_inspecao_sem_fotos(ambiente, capsys: pytest.CaptureFixture) -> None:
    assert ext.main(["verificar"]) == 0
    assert ext.main(["inspecao"]) == 0
    assert "Traceback" not in capsys.readouterr().out


def test_manifesto_versionado_tem_so_o_cabecalho() -> None:
    """O modelo real não contém dados inventados."""
    linhas = (ext.RAIZ_MODULO / "fotos-externas" / "manifesto.csv").read_text(encoding="utf-8").splitlines()
    assert linhas == [CABECALHO.strip()]


def test_pasta_de_imagens_real_nao_tem_fotos_versionadas() -> None:
    pasta = ext.RAIZ_MODULO / "fotos-externas" / "imagens"
    assert (pasta / ".gitkeep").is_file()


# ---------------------------------------------------------------------------
# Validação do manifesto
# ---------------------------------------------------------------------------

def test_manifesto_valido(ambiente) -> None:
    _folha(ambiente["imagens"] / "a.jpg")
    _folha(ambiente["imagens"] / "b.png")
    _manifesto(ambiente, _linha("EXT001", "a.jpg"), _linha("EXT002", "b.png", "PNG"))
    validas, invalidas = ext.validar_manifesto(ext.ler_manifesto())
    assert [v["id"] for v in validas] == ["EXT001", "EXT002"]
    assert invalidas == []


def _problemas(ambiente, *linhas: str) -> list[str]:
    _manifesto(ambiente, *linhas)
    _validas, invalidas = ext.validar_manifesto(ext.ler_manifesto())
    return [p for inv in invalidas for p in inv["problemas"]]


def test_id_duplicado(ambiente) -> None:
    _folha(ambiente["imagens"] / "a.jpg")
    _folha(ambiente["imagens"] / "b.jpg")
    assert any("id duplicado" in p for p in _problemas(ambiente, _linha("EXT001", "a.jpg"), _linha("EXT001", "b.jpg")))


def test_arquivo_duplicado_ignorando_maiusculas(ambiente) -> None:
    _folha(ambiente["imagens"] / "a.jpg")
    assert any("arquivo duplicado" in p
               for p in _problemas(ambiente, _linha("EXT001", "a.jpg"), _linha("EXT002", "A.JPG")))


def test_arquivo_inexistente(ambiente) -> None:
    _folha(ambiente["imagens"] / "outra.jpg")
    assert any("não encontrado" in p for p in _problemas(ambiente, _linha("EXT001", "sumiu.jpg")))


@pytest.mark.parametrize("arquivo", ["folha.gif", "folha.bmp", "folha.txt", "folha", "folha.jpg.exe"])
def test_extensao_invalida(ambiente, arquivo: str) -> None:
    (ambiente["imagens"] / arquivo).write_bytes(b"x")
    assert any("extensão" in p for p in _problemas(ambiente, _linha("EXT001", arquivo)))


@pytest.mark.parametrize("arquivo", [
    "../segredo.jpg", "..\\segredo.jpg", "sub/../../segredo.jpg", "..", "imagens/../../x.jpg",
])
def test_path_traversal_recusado(ambiente, arquivo: str) -> None:
    fora = ambiente["fotos"].parent / "segredo.jpg"
    _folha(fora)
    _folha(ambiente["imagens"] / "real.jpg")
    _manifesto(ambiente, _linha("EXT001", arquivo), _linha("EXT002", "real.jpg"))
    validas, invalidas = ext.validar_manifesto(ext.ler_manifesto())
    assert [v["id"] for v in validas] == ["EXT002"]
    assert invalidas and invalidas[0]["id"] == "EXT001"


@pytest.mark.parametrize("arquivo", ["C:\\fotos\\x.jpg", "C:/fotos/x.jpg", "/etc/x.jpg", "\\\\servidor\\x.jpg", "D:x.jpg"])
def test_caminho_absoluto_recusado(ambiente, arquivo: str) -> None:
    assert any("absoluto" in p for p in _problemas(ambiente, _linha("EXT001", arquivo)))


def test_link_simbolico_para_fora_recusado(ambiente) -> None:
    """Nome simples, mas o arquivo real está fora de imagens/: só a conferência do caminho
    resolvido pega esse caso."""
    fora = ambiente["fotos"].parent / "segredo.jpg"
    _folha(fora)
    link = ambiente["imagens"] / "atalho.jpg"
    try:
        link.symlink_to(fora)
    except OSError:
        pytest.skip("o sistema não permitiu criar link simbólico")
    assert any("fora da pasta" in p for p in _problemas(ambiente, _linha("EXT001", "atalho.jpg")))


def test_caminho_resolvido_fora_de_imagens_recusado(ambiente, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mesmo caso do link simbólico, sem depender de permissão do sistema: o nome é simples,
    mas a resolução do caminho aponta para fora de imagens/."""
    fora = ambiente["fotos"].parent / "segredo.jpg"
    _folha(fora)
    _folha(ambiente["imagens"] / "atalho.jpg")
    resolver = Path.resolve
    monkeypatch.setattr(Path, "resolve",
                        lambda self, strict=False: fora if self.name == "atalho.jpg" else resolver(self, strict))
    assert any("fora da pasta" in p for p in _problemas(ambiente, _linha("EXT001", "atalho.jpg")))


def test_subpasta_recusada(ambiente) -> None:
    (ambiente["imagens"] / "sub").mkdir()
    _folha(ambiente["imagens"] / "sub" / "a.jpg")
    assert any("subpastas" in p for p in _problemas(ambiente, _linha("EXT001", "sub/a.jpg")))


def test_id_fora_do_padrao(ambiente) -> None:
    _folha(ambiente["imagens"] / "a.jpg")
    assert any("padrão" in p for p in _problemas(ambiente, _linha("E1", "a.jpg")))


def test_condicao_fora_do_vocabulario(ambiente) -> None:
    _folha(ambiente["imagens"] / "a.jpg")
    assert any("fundo" in p for p in _problemas(ambiente, _linha("EXT001", "a.jpg", fundo="verde")))


def test_formato_incompativel_com_extensao(ambiente) -> None:
    _folha(ambiente["imagens"] / "a.jpg")
    assert any("não corresponde" in p for p in _problemas(ambiente, _linha("EXT001", "a.jpg", formato="PNG")))


def test_jpeg_aceito_como_jpg(ambiente) -> None:
    _folha(ambiente["imagens"] / "a.jpeg")
    _manifesto(ambiente, _linha("EXT001", "a.jpeg", formato="JPEG"))
    validas, invalidas = ext.validar_manifesto(ext.ler_manifesto())
    assert len(validas) == 1 and invalidas == []


# ---------------------------------------------------------------------------
# Casca: só o pipeline central
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
    raizes = {n.split(".")[0] for n in _imports(SCRIPT)}
    assert "cv2" not in raizes and "numpy" not in raizes


def test_script_usa_somente_o_pipeline_central() -> None:
    internos = {n for n in _imports(SCRIPT) if n.startswith("src")}
    assert internos == {"src.pipeline"}
    # O único outro módulo do projeto é o da Fase 10, reaproveitado só para hashes e estatística.
    assert "avaliar_conjunto_final" in _imports(SCRIPT)


def _codigo_sem_docstrings(caminho: Path) -> str:
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        corpo = getattr(no, "body", None)
        if isinstance(corpo, list) and corpo and isinstance(corpo[0], ast.Expr) \
                and isinstance(getattr(corpo[0], "value", None), ast.Constant) \
                and isinstance(corpo[0].value.value, str):
            corpo[0] = ast.Pass()
    return ast.unparse(arvore)


def test_nenhuma_constante_de_segmentacao_nem_regra_duplicada() -> None:
    codigo = _codigo_sem_docstrings(SCRIPT)
    for proibido in ("FAIXA_VERDE", "KERNEL", "LADO_MAXIMO", "Limiares", "LIMIARES", "limiar",
                     "segmentar_hsv", "limpar_mascara", "analisar_contorno", "extrair_caracteristicas",
                     "classificar_", "GaussianBlur", "inRange", "minAreaRect", "findContours",
                     "cvtColor", "morphologyEx"):
        assert proibido not in codigo, f"o script menciona {proibido}"
    # Nenhum número que pareça faixa HSV ou limiar de regra.
    assert not re.search(r"\b(25|95|0\.92|0\.70|1\.13|1\.30|0\.65|0\.40)\b", codigo)


def test_script_nao_altera_constantes_do_pipeline() -> None:
    codigo = _codigo_sem_docstrings(SCRIPT)
    assert "setattr" not in codigo
    for no in ast.walk(ast.parse(codigo)):
        if isinstance(no, (ast.Assign, ast.AugAssign)):
            alvos = no.targets if isinstance(no, ast.Assign) else [no.target]
            for alvo in alvos:
                assert not (isinstance(alvo, ast.Attribute) and isinstance(alvo.value, ast.Name)
                            and alvo.value.id in {"pipeline", "src", "fase10"})


def test_pipeline_central_e_chamado(ambiente, monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas = []
    original = ext.processar_folha
    monkeypatch.setattr(ext, "processar_folha", lambda c, **k: chamadas.append((Path(c), k)) or original(c, **k))
    _folha(ambiente["imagens"] / "a.jpg")
    _manifesto(ambiente, _linha("EXT001", "a.jpg"))
    assert ext.main([]) == 0

    (caminho, nomeados), = chamadas
    assert caminho == ambiente["imagens"] / "a.jpg"
    assert nomeados["salvar_imagens"] is True           # todas as fotos geram imagens
    assert nomeados["destino"] == ambiente["visual"] / "EXT001"


# ---------------------------------------------------------------------------
# Execução ponta a ponta (imagens sintéticas — não são fotos externas)
# ---------------------------------------------------------------------------

@pytest.fixture
def lote(ambiente) -> dict[str, Path]:
    _folha(ambiente["imagens"] / "folha-01.jpg")
    _folha(ambiente["imagens"] / "folha-02.png", 150, 140)
    cv2.imwrite(str(ambiente["imagens"] / "vazia.jpg"), np.full((400, 400, 3), 250, np.uint8))  # E007
    (ambiente["imagens"] / "corrompida.jpg").write_text("nao e imagem")                          # E003
    _manifesto(ambiente,
               _linha("EXT001", "folha-01.jpg"),
               _linha("EXT002", "folha-02.png", "PNG", fundo="escuro"),
               _linha("EXT003", "vazia.jpg", fundo="colorido"),
               _linha("EXT004", "corrompida.jpg", fundo="irregular"),
               _linha("EXT005", "../fora.jpg"))                                                 # inválida
    return ambiente


def test_lote_gera_todas_as_saidas(lote) -> None:
    assert ext.main([]) == 0
    for nome in ("fase11-resultados-completos.json", "fase11-resultados.csv", "fase11-resumo.json",
                 "fase11-inspecao.csv", "hashes-pipeline-antes.txt", "hashes-pipeline-depois.txt"):
        assert (lote["saida"] / nome).is_file(), nome


def test_json_valido_sem_nan(lote) -> None:
    ext.main([])
    for nome in ("fase11-resultados-completos.json", "fase11-resumo.json"):
        texto = (lote["saida"] / nome).read_text(encoding="utf-8")
        json.loads(texto, parse_constant=lambda c: pytest.fail(f"{c} em {nome}"))


def test_csv_valido_com_uma_linha_por_foto_processada(lote) -> None:
    ext.main([])
    linhas = list(csv.DictReader(open(lote["saida"] / "fase11-resultados.csv", encoding="utf-8")))
    assert [l["id"] for l in linhas] == ["EXT001", "EXT002", "EXT003", "EXT004"]
    for campo in ("fundo", "iluminacao", "posicao", "distancia", "status", "erro_codigo", "avisos",
                  "detectado", "fracao_foreground", "numero_contornos", "toca_borda", "elongacao",
                  "circularidade", "solidez", "razao_perimetro_hull", "anisotropia",
                  "cat_alongamento", "cat_concavidade", "cat_compacidade", "cat_complexidade_borda",
                  "cat_orientacao", "tempo_parede_ms"):
        assert campo in linhas[0]


def test_foto_com_erro_nao_interrompe_o_lote(lote) -> None:
    ext.main([])
    resumo = json.loads((lote["saida"] / "fase11-resumo.json").read_text(encoding="utf-8"))
    assert resumo["cobertura"]["processadas"] == 4
    assert resumo["cobertura"]["sucesso_operacional"] == 2
    assert resumo["erros"]["por_codigo"]["E007"]["ids"] == ["EXT003"]
    assert resumo["erros"]["por_codigo"]["E003"]["ids"] == ["EXT004"]


def test_excecao_inesperada_nao_interrompe_o_lote(lote, monkeypatch: pytest.MonkeyPatch) -> None:
    original = ext.processar_folha

    def explodir_na_primeira(caminho, **k):
        if Path(caminho).name == "folha-01.jpg":
            raise RuntimeError("falha simulada")
        return original(caminho, **k)

    monkeypatch.setattr(ext, "processar_folha", explodir_na_primeira)
    assert ext.main([]) == 0
    linhas = {l["id"]: l for l in csv.DictReader(open(lote["saida"] / "fase11-resultados.csv", encoding="utf-8"))}
    assert linhas["EXT001"]["erro_codigo"] == "EXCECAO_NAO_TRATADA"
    assert linhas["EXT002"]["status"].startswith("sucesso")


def test_foto_valida_gera_resultado_e_imagens(lote) -> None:
    ext.main([])
    linhas = {l["id"]: l for l in csv.DictReader(open(lote["saida"] / "fase11-resultados.csv", encoding="utf-8"))}
    assert linhas["EXT001"]["status"].startswith("sucesso")
    assert float(linhas["EXT001"]["elongacao"]) > 1
    assert len(list((lote["visual"] / "EXT001").glob("*.png"))) == 8


def test_entrada_invalida_registrada_e_nao_processada(lote) -> None:
    ext.main([])
    completos = json.loads((lote["saida"] / "fase11-resultados-completos.json").read_text(encoding="utf-8"))
    assert [i["id"] for i in completos["entradas_invalidas"]] == ["EXT005"]
    assert "EXT005" not in {r["linha"]["id"] for r in completos["resultados"]}


def test_saida_sem_caminho_absoluto(lote) -> None:
    ext.main([])
    raiz = str(lote["fotos"].parent)
    for arquivo in lote["saida"].iterdir():
        texto = arquivo.read_text(encoding="utf-8")
        assert raiz not in texto and raiz.replace("\\", "/") not in texto, arquivo.name
        assert not re.search(r"[A-Za-z]:[\\/]", texto), arquivo.name


def test_inspecao_humana_nasce_vazia(lote) -> None:
    ext.main([])
    linhas = list(csv.DictReader(open(lote["saida"] / "fase11-inspecao.csv", encoding="utf-8")))
    assert list(linhas[0]) == ["id", "arquivo", *ext.COLUNAS_HUMANAS]
    assert all(l[c] == "" for l in linhas for c in ext.COLUNAS_HUMANAS)


def test_inspecao_preenchida_nunca_e_sobrescrita(lote, capsys: pytest.CaptureFixture) -> None:
    ext.main([])
    caminho = lote["saida"] / "fase11-inspecao.csv"
    texto = caminho.read_text(encoding="utf-8").replace("EXT001,folha-01.jpg,,", "EXT001,folha-01.jpg,sim,", 1)
    caminho.write_text(texto, encoding="utf-8")

    assert ext.main([]) == 5
    assert caminho.read_text(encoding="utf-8") == texto
    assert "não sobrescrever" in capsys.readouterr().out


def test_resumo_da_inspecao_humana(lote) -> None:
    ext.main([])
    caminho = lote["saida"] / "fase11-inspecao.csv"
    linhas = list(csv.DictReader(open(caminho, encoding="utf-8")))
    linhas[0].update(folha_principal_segmentada="sim", resultado_util="sim", problema_principal="resultado adequado")
    linhas[1].update(folha_principal_segmentada="parcial", problema_principal="sombra incorporada")
    linhas[2].update(folha_principal_segmentada="talvez")  # valor fora do vocabulário
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)

    resumo = ext.resumir_inspecao(caminho)
    assert resumo["revisadas"] == 3
    assert resumo["folha_principal_segmentada"]["sim"] == 1
    assert resumo["folha_principal_segmentada"]["parcial"] == 1
    assert resumo["problema_principal"]["sombra incorporada"] == 1
    assert resumo["valores_invalidos"] == [{"id": "EXT003", "coluna": "folha_principal_segmentada", "valor": "talvez"}]


def test_resumo_por_condicao_e_comparacao_sem_conclusao(lote) -> None:
    ext.main([])
    resumo = json.loads((lote["saida"] / "fase11-resumo.json").read_text(encoding="utf-8"))
    assert resumo["por_condicao"]["fundo"]["escuro"]["ids"] == ["EXT002"]
    assert resumo["por_condicao"]["fundo"]["colorido"]["erro"] == 1
    assert resumo["comparacao_fase10"]["conclusao"] is None
    texto = json.dumps(resumo).lower()
    for proibido in ("acuracia", "precisao", "recall", "\"f1", "acerto", "reconhec"):
        assert proibido not in texto


def test_hashes_conferidos_antes_e_depois(lote) -> None:
    ext.main([])
    for momento in ("antes", "depois"):
        texto = (lote["saida"] / f"hashes-pipeline-{momento}.txt").read_text(encoding="utf-8")
        assert "# todos idênticos: SIM" in texto
        assert texto.count(";SIM") == len(ext.fase10.ARQUIVOS_CONGELADOS)


def test_pipeline_diferente_do_congelado_nao_executa(lote, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    falsa = tmp_path / "referencia.txt"
    falsa.write_text("src/pipeline.py  " + "0" * 64 + "\n", encoding="utf-8")
    monkeypatch.setattr(ext, "HASHES_REFERENCIA", falsa)
    assert ext.main([]) == 3
    assert not (lote["saida"] / "fase11-resultados.csv").exists()


def test_verificar_aponta_entradas_invalidas(lote, capsys: pytest.CaptureFixture) -> None:
    assert ext.main(["verificar"]) == 2
    saida = capsys.readouterr().out
    assert "5 entradas" in saida and "1 inválidas" in saida and "EXT005" in saida
