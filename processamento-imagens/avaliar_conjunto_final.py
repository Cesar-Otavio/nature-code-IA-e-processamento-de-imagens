"""Avaliação final congelada — Fase 10.

Executa o pipeline **congelado** (tag ``fase-9-completa``) sobre as 96 imagens de
avaliação do manifesto, uma única vez, e registra os resultados sem ajustar nada.

**Esta é uma casca de avaliação.** Não segmenta, não limpa máscara, não extrai
característica, não classifica e não conhece nenhum parâmetro do pipeline: cada imagem
passa por ``pipeline.processar_folha()``, exatamente como na CLI e na API. Há teste
estrutural que falha se este arquivo importar OpenCV, NumPy ou qualquer módulo interno
de processamento.

**Avaliar, não recalibrar.** Os resultados daqui não podem alimentar mudança alguma em
HSV, Gaussiano, morfologia, contornos, features, limiares ou regras
(``docs/processamento-imagens/02-DATASET.md`` §13).

**A espécie não é alvo.** Ela vem do manifesto e serve só para agrupar a descrição dos
resultados. Nunca é passada ao pipeline — que recebe apenas o caminho da imagem — e não
existe métrica de acerto de espécie.

**Nenhum julgamento visual automático.** O script mede e seleciona casos por critérios
objetivos; dizer se uma segmentação está correta é tarefa da inspeção humana
(``02-DATASET.md`` §15).

Uso, a partir de ``processamento-imagens/``::

    .venv/Scripts/python.exe avaliar_conjunto_final.py hashes antes
    .venv/Scripts/python.exe avaliar_conjunto_final.py verificar
    .venv/Scripts/python.exe avaliar_conjunto_final.py avaliar
    .venv/Scripts/python.exe avaliar_conjunto_final.py inspecao
    .venv/Scripts/python.exe avaliar_conjunto_final.py hashes depois
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from src.pipeline import VERSAO_PIPELINE, processar_folha

RAIZ_MODULO = Path(__file__).resolve().parent
RAIZ_REPOSITORIO = RAIZ_MODULO.parent
MANIFESTO = RAIZ_MODULO / "dataset" / "manifesto.csv"
PASTA_IMAGENS = RAIZ_MODULO / "dataset" / "dados" / "Leaves"
PASTA_SAIDA = RAIZ_REPOSITORIO / "docs" / "processamento-imagens" / "dados-avaliacao"
#: PNGs da inspeção qualitativa. Dentro de ``resultados/``, ignorado pelo Git.
PASTA_INSPECAO = RAIZ_MODULO / "resultados" / "inspecao-fase10"

TAG_AVALIADA = "fase-9-completa"

#: Protocolo da Fase 2 (§12): 32 espécies × 3 imagens.
TOTAL_ESPERADO = 96
ESPECIES_ESPERADAS = 32
POR_ESPECIE = 3

#: Arquivos que definem o algoritmo. Os hashes antes e depois precisam coincidir.
ARQUIVOS_CONGELADOS = (
    "src/preprocessing.py",
    "src/segmentation.py",
    "src/morphology.py",
    "src/contours.py",
    "src/features.py",
    "src/classification.py",
    "src/pipeline.py",
    "src/utils.py",
    "src/visualizacao.py",
)

ATRIBUTOS = ("alongamento", "concavidade", "compacidade", "complexidade_borda", "orientacao")

#: Categorias exatamente como o código as produz — não renomeadas.
CATEGORIAS = {
    "alongamento": ("baixa", "moderada", "alta", "extrema", "indeterminado"),
    "concavidade": ("baixa", "moderada", "alta", "ambigua", "indeterminado"),
    "compacidade": ("baixa", "moderada", "alta", "indeterminado"),
    "complexidade_borda": ("regular", "moderada", "complexa", "indeterminado"),
    "orientacao": ("bem_definida", "pouco_definida", "indefinida", "indeterminado"),
}

ETAPAS = ("redimensionamento", "suavizacao", "segmentacao", "limpeza",
          "contornos", "caracteristicas", "classificacao")

FEATURES_ESTATISTICAS = (
    "area_contorno_px2", "area_mascara_px2", "perimetro_px", "elongacao", "circularidade",
    "solidez", "extent", "extent_rotacionado", "razao_perimetro_hull", "anisotropia",
    "fracao_foreground",
)

#: Aviso anexado a toda descrição bem-sucedida. Não é aviso técnico.
AVISO_PADRAO = "descricao geometrica automatica; nao constitui identificacao botanica nem taxonomica"

#: Posições das imagens reprocessadas no teste de determinismo: primeira, três
#: intermediárias distribuídas e última.
FRACOES_DETERMINISMO = (0.0, 0.25, 0.5, 0.75, 1.0)

LIMITE_INSPECAO = 20


# ---------------------------------------------------------------------------
# Manifesto
# ---------------------------------------------------------------------------

def ler_manifesto(caminho: Path | None = None) -> list[dict[str, str]]:
    with open(caminho or MANIFESTO, encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def selecionar_avaliacao(linhas: list[dict[str, str]]) -> list[dict[str, str]]:
    """As entradas marcadas ``uso = avaliacao``, na ordem do manifesto."""
    return [linha for linha in linhas if linha["uso"] == "avaliacao"]


def especie_de(linha: dict[str, str]) -> tuple[str, str]:
    """``"01-Phyllostachys edulis"`` → ``("01", "Phyllostachys edulis")``."""
    identificador, _, nome = linha["classe_original"].partition("-")
    return identificador, nome


def caminho_da_imagem(linha: dict[str, str], pasta: Path | None = None) -> Path:
    return (pasta or PASTA_IMAGENS) / linha["arquivo"]


def validar_selecao(
    todas: list[dict[str, str]],
    avaliacao: list[dict[str, str]],
    pasta: Path | None = None,
    conferir_arquivos: bool = True,
) -> list[str]:
    """Problemas da seleção. Lista vazia = pode avaliar. **Não abre imagem alguma.**"""
    problemas: list[str] = []

    if len(avaliacao) != TOTAL_ESPERADO:
        problemas.append(f"total de avaliação {len(avaliacao)}, esperado {TOTAL_ESPERADO}")

    nomes = [linha["arquivo"] for linha in avaliacao]
    repetidos = sorted({n for n in nomes if nomes.count(n) > 1})
    if repetidos:
        problemas.append(f"arquivos duplicados: {repetidos}")

    desenvolvimento = {linha["arquivo"] for linha in todas if linha["uso"] == "desenvolvimento"}
    misturados = sorted(set(nomes) & desenvolvimento)
    if misturados:
        problemas.append(f"imagens de desenvolvimento na avaliação: {misturados}")

    if any(linha["uso"] != "avaliacao" for linha in avaliacao):
        problemas.append("entrada com uso diferente de 'avaliacao'")

    por_especie: dict[str, int] = {}
    for linha in avaliacao:
        por_especie[linha["classe_original"]] = por_especie.get(linha["classe_original"], 0) + 1
    if len(por_especie) != ESPECIES_ESPERADAS:
        problemas.append(f"{len(por_especie)} espécies, esperadas {ESPECIES_ESPERADAS}")
    fora = {k: v for k, v in por_especie.items() if v != POR_ESPECIE}
    if fora:
        problemas.append(f"espécies fora de {POR_ESPECIE} imagens: {fora}")

    for linha in avaliacao:
        caminho = caminho_da_imagem(linha, pasta)
        if "amostra" in str(caminho).lower():
            problemas.append(f"caminho aponta para amostra: {linha['arquivo']}")
        if conferir_arquivos and not caminho.is_file():
            problemas.append(f"arquivo ausente: {linha['arquivo']}")

    return problemas


# ---------------------------------------------------------------------------
# Hashes e Git
# ---------------------------------------------------------------------------

def sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def hashes_congelados(raiz: Path | None = None) -> dict[str, str]:
    return {nome: sha256((raiz or RAIZ_MODULO) / nome) for nome in ARQUIVOS_CONGELADOS}


def _git(*argumentos: str) -> str:
    try:
        saida = subprocess.run(["git", *argumentos], cwd=RAIZ_REPOSITORIO,
                               capture_output=True, text=True, check=True)
        return saida.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def estado_git() -> dict[str, object]:
    caminhos = [f"processamento-imagens/{nome}" for nome in ARQUIVOS_CONGELADOS]
    return {
        "commit": _git("rev-parse", "HEAD"),
        "commit_curto": _git("rev-parse", "--short", "HEAD"),
        "tag": TAG_AVALIADA,
        "commit_da_tag": _git("rev-list", "-n", "1", TAG_AVALIADA),
        "arquivos_congelados_alterados": [c for c in _git("diff", "--name-only", "HEAD", "--", *caminhos).splitlines() if c],
    }


def agora() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def escrever_hashes(momento: str) -> Path:
    git = estado_git()
    hashes = hashes_congelados()
    linhas = [
        f"# Hashes SHA-256 do pipeline congelado — {momento} da avaliação (Fase 10)",
        f"# commit: {git['commit']}",
        f"# tag: {git['tag']} -> {git['commit_da_tag']}",
        f"# data/hora: {agora()}",
        f"# arquivos congelados alterados em relação ao commit: {git['arquivos_congelados_alterados'] or 'nenhum'}",
        "#",
        "# caminho (relativo a processamento-imagens/)  sha256",
    ]
    linhas += [f"{nome}  {valor}" for nome, valor in hashes.items()]
    destino = PASTA_SAIDA / f"hashes-pipeline-{momento}.txt"
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8", newline="\n")
    return destino


def ler_hashes(caminho: Path) -> dict[str, str]:
    resultado = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if linha and not linha.startswith("#"):
            nome, valor = linha.split()
            resultado[nome] = valor
    return resultado


def comparar_hashes() -> tuple[Path, bool]:
    antes = ler_hashes(PASTA_SAIDA / "hashes-pipeline-antes.txt")
    depois = ler_hashes(PASTA_SAIDA / "hashes-pipeline-depois.txt")
    linhas = ["# Comparação dos hashes do pipeline congelado, antes × depois da avaliação",
              "arquivo;hash_antes;hash_depois;IDENTICO"]
    todos = True
    for nome in ARQUIVOS_CONGELADOS:
        igual = antes.get(nome) == depois.get(nome) and antes.get(nome) is not None
        todos &= igual
        linhas.append(f"{nome};{antes.get(nome)};{depois.get(nome)};{'SIM' if igual else 'NAO'}")
    linhas.append(f"# todos idênticos: {'SIM' if todos else 'NAO'}")
    destino = PASTA_SAIDA / "hashes-pipeline-comparacao.txt"
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8", newline="\n")
    return destino, todos


# ---------------------------------------------------------------------------
# Uma linha por imagem
# ---------------------------------------------------------------------------

def _pegar(dados: object, *chaves: str) -> object:
    for chave in chaves:
        if not isinstance(dados, dict):
            return None
        dados = dados.get(chave)
    return dados


def linha_da_imagem(indice: int, entrada: dict[str, str], resultado: dict, tempo_parede_ms: float) -> dict:
    """Achata o resultado do pipeline numa linha tabular. Não calcula feature alguma."""
    especie_id, especie = especie_de(entrada)
    erro = resultado.get("erro") or {}
    car = resultado.get("caracteristicas") or {}
    obj = resultado.get("objeto") or {}
    cla = resultado.get("classificacao") or {}
    avisos = resultado.get("avisos") or []

    linha = {
        "indice": indice,
        "arquivo": entrada["arquivo"],
        "especie_id": especie_id,
        "especie": especie,
        "conjunto": entrada["uso"],
        "status": resultado.get("status"),
        "erro_codigo": erro.get("codigo"),
        "erro_mensagem": erro.get("mensagem"),
        "detectado": obj.get("detectado", False),
        "numero_contornos": obj.get("numero_contornos"),
        "dominancia": obj.get("dominancia"),
        "toca_borda": _pegar(obj, "toca_borda", "qualquer"),
        "distancia_minima_borda_px": obj.get("distancia_minima_borda_px"),
        "fracao_foreground": obj.get("fracao_foreground"),
        "area_contorno_px2": _pegar(car, "dimensoes", "area_contorno_px2"),
        "area_mascara_px2": _pegar(car, "dimensoes", "area_mascara_px2"),
        "diferenca_area_pct": _pegar(car, "dimensoes", "diferenca_area_pct"),
        "perimetro_px": _pegar(car, "dimensoes", "perimetro_px"),
        "elongacao": _pegar(car, "forma", "elongacao"),
        "circularidade": _pegar(car, "forma", "circularidade"),
        "solidez": _pegar(car, "forma", "solidez"),
        "extent": _pegar(car, "forma", "extent"),
        "extent_rotacionado": _pegar(car, "forma", "extent_rotacionado"),
        "razao_perimetro_hull": _pegar(car, "convexidade", "razao_perimetro_hull"),
        "anisotropia": _pegar(car, "orientacao", "anisotropia"),
        "orientacao_confiavel": _pegar(car, "orientacao", "confiavel"),
        "proporcao_verde": _pegar(car, "cor", "proporcao_verde"),
    }
    for atributo in ATRIBUTOS:
        regra = cla.get(atributo) or {}
        linha[f"cat_{atributo}"] = regra.get("categoria")
        linha[f"limitrofe_{atributo}"] = regra.get("limitrofe")
        linha[f"margem_{atributo}"] = regra.get("margem_relativa")
    linha["n_limitrofes"] = sum(1 for a in ATRIBUTOS if linha[f"limitrofe_{a}"])

    tempos = _pegar(resultado, "processamento", "tempo_por_etapa_ms") or {}
    linha["tempo_pipeline_ms"] = _pegar(resultado, "processamento", "tempo_total_ms")
    linha["tempo_parede_ms"] = round(tempo_parede_ms, 3)
    for etapa in ETAPAS:
        linha[f"tempo_{etapa}_ms"] = tempos.get(etapa)

    tecnicos = [a for a in avisos if a != AVISO_PADRAO]
    linha["n_avisos_tecnicos"] = len(tecnicos)
    linha["avisos"] = " | ".join(avisos)
    return linha


def processar_uma(caminho: Path) -> tuple[dict, float]:
    """Chama o pipeline congelado. Qualquer exceção vira resultado de erro — uma imagem
    problemática não pode abortar a avaliação das outras."""
    inicio = time.perf_counter()
    try:
        resultado = processar_folha(caminho, salvar_imagens=False)
    except Exception as erro:  # noqa: BLE001 — registrar, nunca esconder
        resultado = {
            "status": "erro", "objeto": None, "caracteristicas": None, "classificacao": None,
            "avisos": [], "processamento": None,
            "erro": {"codigo": "EXCECAO_NAO_TRATADA", "mensagem": f"{type(erro).__name__}: {erro}"},
        }
    return resultado, (time.perf_counter() - inicio) * 1000.0


# ---------------------------------------------------------------------------
# Estatística — Python puro, sem NumPy
# ---------------------------------------------------------------------------

def percentil(valores: list[float], p: float) -> float:
    """Percentil com interpolação linear entre vizinhos (método 'linear' do NumPy)."""
    ordenados = sorted(valores)
    posicao = (len(ordenados) - 1) * p / 100.0
    baixo = math.floor(posicao)
    alto = min(baixo + 1, len(ordenados) - 1)
    return ordenados[baixo] + (ordenados[alto] - ordenados[baixo]) * (posicao - baixo)


def descrever(valores: list[object]) -> dict[str, object]:
    """Resumo de uma variável. **Nenhum outlier é removido.**"""
    numeros = [float(v) for v in valores if isinstance(v, (int, float)) and not isinstance(v, bool)
               and math.isfinite(float(v))]
    if not numeros:
        return {"n": 0}
    return {
        "n": len(numeros),
        "minimo": round(min(numeros), 6),
        "p5": round(percentil(numeros, 5), 6),
        "p25": round(percentil(numeros, 25), 6),
        "mediana": round(statistics.median(numeros), 6),
        "media": round(statistics.fmean(numeros), 6),
        "p75": round(percentil(numeros, 75), 6),
        "p95": round(percentil(numeros, 95), 6),
        "maximo": round(max(numeros), 6),
        "desvio_padrao": round(statistics.stdev(numeros), 6) if len(numeros) > 1 else 0.0,
    }


def _contagem(itens: list[str], total: int) -> dict[str, dict[str, object]]:
    saida: dict[str, dict[str, object]] = {}
    for item in itens:
        saida.setdefault(item, {"quantidade": 0})
        saida[item]["quantidade"] += 1  # type: ignore[operator]
    for dados in saida.values():
        dados["percentual"] = round(100.0 * dados["quantidade"] / total, 2) if total else 0.0  # type: ignore[operator]
    return dict(sorted(saida.items(), key=lambda kv: (-kv[1]["quantidade"], kv[0])))  # type: ignore[index]


def _chave_aviso(aviso: str) -> str:
    """Avisos com parte variável ("atributos proximos de um limiar: X, Y") agrupados."""
    return aviso.split(":")[0].strip()


def resumir(linhas: list[dict]) -> dict:
    total = len(linhas)
    validas = [l for l in linhas if l["status"] in ("sucesso", "sucesso_com_avisos")]
    erros = [l for l in linhas if l["status"] == "erro"]

    cobertura = {
        "total_imagens": total,
        "processadas": total,
        "sucesso": sum(1 for l in linhas if l["status"] == "sucesso"),
        "sucesso_com_avisos": sum(1 for l in linhas if l["status"] == "sucesso_com_avisos"),
        "erro": len(erros),
        "taxa_processamento_valido_pct": round(100.0 * len(validas) / total, 2) if total else 0.0,
        "validas_com_aviso_tecnico": sum(1 for l in validas if l["n_avisos_tecnicos"] > 0),
        "validas_sem_aviso_tecnico": sum(1 for l in validas if l["n_avisos_tecnicos"] == 0),
        "observacao": ("o status 'sucesso_com_avisos' inclui o aviso padrão de não "
                       "identificação botânica, anexado a toda descrição; por isso a contagem "
                       "de avisos técnicos é reportada à parte"),
    }

    por_codigo: dict[str, dict] = {}
    for l in erros:
        dados = por_codigo.setdefault(l["erro_codigo"], {"quantidade": 0, "imagens": []})
        dados["quantidade"] += 1
        dados["imagens"].append(l["arquivo"])
    for dados in por_codigo.values():
        dados["percentual"] = round(100.0 * dados["quantidade"] / total, 2)

    todos_avisos = [a for l in linhas for a in (l["avisos"].split(" | ") if l["avisos"] else [])]
    tecnicos = [a for a in todos_avisos if a != AVISO_PADRAO]
    avisos = {
        "aviso_padrao_nao_identificacao": {"texto": AVISO_PADRAO,
                                           "imagens": sum(1 for a in todos_avisos if a == AVISO_PADRAO)},
        "tecnicos_agrupados": _contagem([_chave_aviso(a) for a in tecnicos], total),
        "tecnicos_texto_exato": _contagem(tecnicos, total),
        "imagens_por_aviso_tecnico": {},
    }
    for l in linhas:
        for a in (l["avisos"].split(" | ") if l["avisos"] else []):
            if a != AVISO_PADRAO:
                avisos["imagens_por_aviso_tecnico"].setdefault(_chave_aviso(a), []).append(l["arquivo"])

    estatisticas = {f: descrever([l[f] for l in validas]) for f in FEATURES_ESTATISTICAS}

    distribuicoes = {}
    for atributo in ATRIBUTOS:
        observadas = [l[f"cat_{atributo}"] for l in validas]
        contagem = {c: {"quantidade": 0, "percentual": 0.0} for c in CATEGORIAS[atributo]}
        for c in observadas:
            contagem.setdefault(c, {"quantidade": 0, "percentual": 0.0})["quantidade"] += 1
        for dados in contagem.values():
            dados["percentual"] = round(100.0 * dados["quantidade"] / len(validas), 2) if validas else 0.0
        distribuicoes[atributo] = contagem

    com_limitrofe = [l for l in validas if l["n_limitrofes"] > 0]
    limitrofes = {
        "imagens_com_pelo_menos_um": len(com_limitrofe),
        "percentual": round(100.0 * len(com_limitrofe) / len(validas), 2) if validas else 0.0,
        "por_atributo": {a: sum(1 for l in validas if l[f"limitrofe_{a}"]) for a in ATRIBUTOS},
        "distribuicao_do_numero_por_imagem": {str(n): sum(1 for l in validas if l["n_limitrofes"] == n)
                                               for n in range(len(ATRIBUTOS) + 1)},
        "principais_casos": [
            {"arquivo": l["arquivo"], "especie_id": l["especie_id"], "n_limitrofes": l["n_limitrofes"],
             "atributos": [a for a in ATRIBUTOS if l[f"limitrofe_{a}"]],
             "margens": {a: l[f"margem_{a}"] for a in ATRIBUTOS if l[f"limitrofe_{a}"]}}
            for l in sorted(com_limitrofe, key=lambda l: (-l["n_limitrofes"], l["indice"]))[:10]
        ],
    }

    especies: dict[str, dict] = {}
    for l in linhas:
        dados = especies.setdefault(l["especie_id"], {"especie": l["especie"], "linhas": []})
        dados["linhas"].append(l)
    por_especie = {}
    for identificador, dados in sorted(especies.items()):
        grupo = dados["linhas"]
        ok = [l for l in grupo if l["status"] != "erro"]
        por_especie[identificador] = {
            "especie": dados["especie"],
            "imagens_previstas": POR_ESPECIE,
            "imagens_no_conjunto": len(grupo),
            "processadas_validas": len(ok),
            "com_aviso_tecnico": sum(1 for l in ok if l["n_avisos_tecnicos"] > 0),
            "com_erro": len(grupo) - len(ok),
            "arquivos": [l["arquivo"] for l in grupo],
            "mediana_elongacao": _mediana([l["elongacao"] for l in ok]),
            "mediana_circularidade": _mediana([l["circularidade"] for l in ok]),
            "mediana_solidez": _mediana([l["solidez"] for l in ok]),
            "mediana_razao_perimetro_hull": _mediana([l["razao_perimetro_hull"] for l in ok]),
        }

    performance = {
        "tempo_parede_por_imagem_ms": descrever([l["tempo_parede_ms"] for l in linhas]),
        "tempo_pipeline_por_imagem_ms": descrever([l["tempo_pipeline_ms"] for l in validas]),
        "por_etapa_ms": {e: descrever([l[f"tempo_{e}_ms"] for l in validas]) for e in ETAPAS},
        "observacao": ("execução sem imagens intermediárias (salvar_imagens=False): "
                       "'visualizacao' não entra. tempo_parede inclui leitura do arquivo, "
                       "que o pipeline não cronometra"),
    }

    return {"cobertura": cobertura, "erros": {"total": len(erros), "por_codigo": por_codigo},
            "avisos": avisos, "estatisticas_features": estatisticas,
            "distribuicoes_classificacao": distribuicoes, "limitrofes": limitrofes,
            "por_especie": por_especie, "performance": performance}


def _mediana(valores: list[object]) -> float | None:
    numeros = [float(v) for v in valores if isinstance(v, (int, float)) and not isinstance(v, bool)]
    return round(statistics.median(numeros), 6) if numeros else None


# ---------------------------------------------------------------------------
# Determinismo e seleção para inspeção
# ---------------------------------------------------------------------------

def indices_determinismo(total: int) -> list[int]:
    return sorted({round((total - 1) * f) for f in FRACOES_DETERMINISMO})


def verificar_determinismo(avaliacao: list[dict[str, str]], resultados: list[dict]) -> dict:
    casos = []
    for indice in indices_determinismo(len(avaliacao)):
        novo, _ = processar_uma(caminho_da_imagem(avaliacao[indice]))
        original = resultados[indice]
        identicos = {bloco: novo.get(bloco) == original.get(bloco)
                     for bloco in ("status", "objeto", "caracteristicas", "classificacao", "erro")}
        casos.append({"indice": indice, "arquivo": avaliacao[indice]["arquivo"],
                      "identico": all(identicos.values()), "blocos": identicos})
    return {"imagens": len(casos), "todas_identicas": all(c["identico"] for c in casos), "casos": casos}


def selecionar_para_inspecao(linhas: list[dict]) -> list[dict]:
    """Casos para revisão humana, por critérios **objetivos** e deterministas.

    Não julga resultado algum: só aponta extremos, erros, limítrofes e controles sem aviso.
    """
    validas = [l for l in linhas if l["status"] != "erro"]
    escolhidos: dict[str, list[str]] = {}

    def adicionar(grupo: list[dict], motivo: str, quantos: int) -> None:
        for l in grupo[:quantos]:
            escolhidos.setdefault(l["arquivo"], []).append(motivo)

    def ordenar(chave: str, maior: bool) -> list[dict]:
        com_valor = [l for l in validas if isinstance(l[chave], (int, float))]
        return sorted(com_valor, key=lambda l: ((-l[chave]) if maior else l[chave], l["indice"]))

    adicionar([l for l in linhas if l["status"] == "erro"], "erro", len(linhas))
    adicionar(ordenar("elongacao", True), "maior elongacao", 3)
    adicionar(ordenar("solidez", False), "menor solidez", 3)
    adicionar(ordenar("razao_perimetro_hull", True), "maior razao perimetro/hull", 3)
    adicionar(ordenar("circularidade", False), "menor circularidade", 3)
    adicionar(sorted([l for l in validas if l["n_limitrofes"] > 0],
                     key=lambda l: (-l["n_limitrofes"], l["indice"])), "mais atributos limitrofes", 3)
    adicionar([l for l in validas if l["toca_borda"]], "toca a borda", 3)
    adicionar(sorted([l for l in validas if l["n_avisos_tecnicos"] == 0], key=lambda l: l["indice"]),
              "controle sem aviso tecnico", 3)

    por_arquivo = {l["arquivo"]: l for l in linhas}
    casos = [{"arquivo": a, "indice": por_arquivo[a]["indice"], "especie_id": por_arquivo[a]["especie_id"],
              "motivos": "; ".join(m)} for a, m in escolhidos.items()]
    return casos[:LIMITE_INSPECAO]


# ---------------------------------------------------------------------------
# Saída
# ---------------------------------------------------------------------------

def _json(dados: object, destino: Path) -> None:
    # allow_nan=False: NaN ou Infinity levantam erro em vez de irem para o arquivo.
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                       encoding="utf-8", newline="\n")


def _csv(linhas: list[dict], destino: Path) -> None:
    with open(destino, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0]), lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(linhas)


def avaliar() -> int:
    todas = ler_manifesto()
    avaliacao = selecionar_avaliacao(todas)
    problemas = validar_selecao(todas, avaliacao)
    if problemas:
        print("Seleção inválida — avaliação NÃO executada:", *problemas, sep="\n  ")
        return 2

    git = estado_git()
    if git["arquivos_congelados_alterados"]:
        print("Arquivos congelados alterados — avaliação NÃO executada:", git["arquivos_congelados_alterados"])
        return 3

    inicio_execucao = agora()
    resultados, linhas = [], []
    relogio = time.perf_counter()
    for indice, entrada in enumerate(avaliacao):
        resultado, tempo = processar_uma(caminho_da_imagem(entrada))
        resultados.append(resultado)
        linhas.append(linha_da_imagem(indice, entrada, resultado, tempo))
        print(f"  [{indice + 1:2d}/{len(avaliacao)}] {entrada['arquivo']:<9} {resultado['status']}")
    tempo_total_s = time.perf_counter() - relogio

    resumo = resumir(linhas)
    resumo["performance"]["tempo_total_96_s"] = round(tempo_total_s, 3)
    resumo["determinismo"] = verificar_determinismo(avaliacao, resultados)
    casos = selecionar_para_inspecao(linhas)
    resumo["inspecao_selecionada"] = casos

    metadados = {
        "fase": 10, "descricao": "avaliação final congelada nas imagens reservadas",
        "commit": git["commit"], "tag": git["tag"], "commit_da_tag": git["commit_da_tag"],
        "versao_pipeline": VERSAO_PIPELINE, "inicio": inicio_execucao, "fim": agora(),
        "total_esperado": TOTAL_ESPERADO, "total_processado": len(linhas),
        "salvar_imagens": False, "manifesto": "processamento-imagens/dataset/manifesto.csv",
        "pasta_imagens": "processamento-imagens/dataset/dados/Leaves (não versionada)",
        "python": sys.version.split()[0],
    }

    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    _json({"metadados": metadados,
           "resultados": [{"linha": l, "resultado": r} for l, r in zip(linhas, resultados)]},
          PASTA_SAIDA / "fase10-resultados-completos.json")
    _csv(linhas, PASTA_SAIDA / "fase10-resultados.csv")
    _json({"metadados": metadados, **resumo}, PASTA_SAIDA / "fase10-resumo.json")
    _csv([{**c, "inspecao_humana": "", "observacao": ""} for c in casos],
         PASTA_SAIDA / "fase10-casos-inspecao.csv")

    print(f"\n{len(linhas)} imagens em {tempo_total_s:.1f} s · "
          f"válidas {resumo['cobertura']['taxa_processamento_valido_pct']}% · "
          f"erros {resumo['erros']['total']} · determinismo "
          f"{'OK' if resumo['determinismo']['todas_identicas'] else 'DIVERGENTE'}")
    return 0


def gerar_inspecao() -> int:
    """Gera os PNGs dos casos selecionados em pasta ignorada, e confere que os números
    batem com a execução principal — a visualização não altera nenhuma métrica."""
    casos = list(csv.DictReader(open(PASTA_SAIDA / "fase10-casos-inspecao.csv", encoding="utf-8")))
    completos = json.loads((PASTA_SAIDA / "fase10-resultados-completos.json").read_text(encoding="utf-8"))
    por_arquivo = {item["linha"]["arquivo"]: item["resultado"] for item in completos["resultados"]}
    divergentes = []
    for caso in casos:
        destino = PASTA_INSPECAO / Path(caso["arquivo"]).stem
        novo = processar_folha(PASTA_IMAGENS / caso["arquivo"], salvar_imagens=True, destino=destino)
        original = por_arquivo[caso["arquivo"]]
        if any(novo.get(b) != original.get(b) for b in ("objeto", "caracteristicas", "classificacao")):
            divergentes.append(caso["arquivo"])
        print(f"  {caso['arquivo']:<9} -> {destino.relative_to(RAIZ_MODULO)}")
    print(f"{len(casos)} casos; divergências numéricas: {divergentes or 'nenhuma'}")
    return 1 if divergentes else 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["hashes"] and argv[1:2] in (["antes"], ["depois"]):
        print(escrever_hashes(argv[1]).relative_to(RAIZ_REPOSITORIO))
        if argv[1] == "depois":
            destino, iguais = comparar_hashes()
            print(destino.relative_to(RAIZ_REPOSITORIO), "- todos idênticos:", "SIM" if iguais else "NAO")
            return 0 if iguais else 4
        return 0
    if argv == ["verificar"]:
        todas = ler_manifesto()
        avaliacao = selecionar_avaliacao(todas)
        problemas = validar_selecao(todas, avaliacao)
        especies = {linha["classe_original"] for linha in avaliacao}
        print(f"manifesto: {len(todas)} entradas · avaliação: {len(avaliacao)} · espécies: {len(especies)}")
        print("seleção válida" if not problemas else "PROBLEMAS:\n  " + "\n  ".join(problemas))
        return 0 if not problemas else 2
    if argv == ["avaliar"]:
        return avaliar()
    if argv == ["inspecao"]:
        return gerar_inspecao()
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
