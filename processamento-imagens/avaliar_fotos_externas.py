"""Avaliação de robustez com fotos externas — Fase 11.

Executa o pipeline **congelado** (tag ``fase-9-completa``) sobre fotografias reais tiradas
pela equipe, fora do ambiente controlado do Flavia, e registra o comportamento — sem
ajustar nada.

**Esta é uma casca de avaliação**, como a da Fase 10: não segmenta, não limpa máscara, não
extrai característica e não classifica. Cada foto passa por ``pipeline.processar_folha()``.
Há teste estrutural que falha se este arquivo importar OpenCV, NumPy ou um módulo interno
de processamento.

**Nenhuma recalibração.** Se o pipeline falhar em fundo real, isso é o resultado:
"a segmentação HSV calibrada para o Flavia apresentou baixa robustez em fundos naturais"
— e não um motivo para mudar a faixa HSV.

**Nenhum julgamento visual automático.** O script mede; dizer se a folha foi bem
segmentada é da inspeção humana, em ``fase11-inspecao.csv``, que ele cria com as colunas
de julgamento **vazias** e nunca sobrescreve depois de preenchida.

Reaproveita, por importação, os hashes e a estatística do script da Fase 10
(``avaliar_conjunto_final.py``), sem modificá-lo.

Uso, a partir de ``processamento-imagens/``::

    .venv/Scripts/python.exe avaliar_fotos_externas.py              # avaliar
    .venv/Scripts/python.exe avaliar_fotos_externas.py verificar    # só valida o manifesto
    .venv/Scripts/python.exe avaliar_fotos_externas.py inspecao     # resume a revisão humana
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
from pathlib import Path, PurePosixPath, PureWindowsPath

from src.pipeline import VERSAO_PIPELINE, processar_folha

import avaliar_conjunto_final as fase10

RAIZ_MODULO = Path(__file__).resolve().parent
RAIZ_REPOSITORIO = RAIZ_MODULO.parent
PASTA_FOTOS = RAIZ_MODULO / "fotos-externas"
MANIFESTO = PASTA_FOTOS / "manifesto.csv"
PASTA_IMAGENS = PASTA_FOTOS / "imagens"
PASTA_SAIDA = RAIZ_REPOSITORIO / "docs" / "processamento-imagens" / "dados-robustez"
#: Imagens intermediárias de TODAS as fotos (conjunto pequeno, inspeção humana).
#: Dentro de ``resultados/``, ignorado pelo Git.
PASTA_VISUAL = RAIZ_MODULO / "resultados" / "robustez-fase11"
#: Referência do checkpoint congelado: os hashes registrados antes da Fase 10.
HASHES_REFERENCIA = fase10.PASTA_SAIDA / "hashes-pipeline-antes.txt"
RESUMO_FASE10 = fase10.PASTA_SAIDA / "fase10-resumo.json"

CAMPOS_MANIFESTO = ("id", "arquivo", "fundo", "iluminacao", "posicao", "distancia", "formato", "observacao")
PADRAO_ID = re.compile(r"^EXT\d{3}$")
EXTENSOES = {".jpg": "JPG", ".jpeg": "JPG", ".png": "PNG"}

#: Vocabulário controlado das condições de captura (protocolo da Fase 11).
CONDICOES = {
    "fundo": ("claro", "escuro", "colorido", "irregular"),
    "iluminacao": ("natural", "artificial", "sombra", "desigual"),
    "posicao": ("centralizada", "inclinada", "proxima_borda", "deslocada"),
    "distancia": ("grande", "media", "pequena"),
}
FORMATOS = ("JPG", "JPEG", "PNG")

ATRIBUTOS = fase10.ATRIBUTOS
AVISO_PADRAO = fase10.AVISO_PADRAO

MENSAGEM_SEM_FOTOS = (
    "Nenhuma foto externa disponível para avaliação.\n"
    "Adicione as imagens em fotos-externas/imagens/ e preencha o manifesto.csv."
)

#: Colunas preenchidas **somente** pela equipe, na revisão visual.
COLUNAS_HUMANAS = (
    "folha_principal_segmentada", "mascara_visual_adequada", "contorno_visual_adequado",
    "resultado_util", "problema_principal", "observacao_humana",
)
VALORES_JULGAMENTO = ("sim", "parcial", "nao")
PROBLEMAS = (
    "fundo confundido com folha", "folha parcialmente perdida", "sombra incorporada",
    "objeto secundario incorporado", "folha fragmentada", "folha nao detectada",
    "contorno inadequado", "recorte pela borda", "cor fora da faixa", "resultado adequado",
    "outro",
)


# ---------------------------------------------------------------------------
# Manifesto
# ---------------------------------------------------------------------------

def ler_manifesto(caminho: Path | None = None) -> list[dict[str, str]]:
    """Linhas do manifesto; linhas totalmente vazias são ignoradas."""
    caminho = caminho or MANIFESTO
    if not caminho.is_file():
        return []
    with open(caminho, encoding="utf-8-sig", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    return [{k: (v or "").strip() for k, v in l.items() if k} for l in linhas
            if any((v or "").strip() for v in l.values() if isinstance(v, str))]


def _nome_simples(nome: str) -> str | None:
    """O motivo pelo qual ``nome`` não é um nome de arquivo simples, ou ``None``."""
    if not nome:
        return "arquivo vazio"
    if PurePosixPath(nome).is_absolute() or PureWindowsPath(nome).is_absolute() \
            or PureWindowsPath(nome).drive or nome.startswith(("/", "\\")):
        return "caminho absoluto não permitido"
    if ".." in re.split(r"[\\/]", nome):
        return "'..' não permitido"
    if "/" in nome or "\\" in nome:
        return "o arquivo deve estar diretamente em imagens/, sem subpastas"
    return None


def validar_manifesto(
    linhas: list[dict[str, str]], pasta: Path | None = None
) -> tuple[list[dict[str, str]], list[dict[str, object]]]:
    """Separa as entradas válidas das inválidas. **Não abre imagem alguma.**

    Uma entrada inválida é registrada e não é processada; as demais seguem.
    """
    pasta = (pasta or PASTA_IMAGENS).resolve()
    validas: list[dict[str, str]] = []
    invalidas: list[dict[str, object]] = []

    contagem_ids: dict[str, int] = {}
    contagem_arquivos: dict[str, int] = {}
    for linha in linhas:
        contagem_ids[linha.get("id", "")] = contagem_ids.get(linha.get("id", ""), 0) + 1
        chave = linha.get("arquivo", "").lower()
        contagem_arquivos[chave] = contagem_arquivos.get(chave, 0) + 1

    for numero, linha in enumerate(linhas, start=2):  # linha 1 é o cabeçalho
        problemas: list[str] = []
        identificador = linha.get("id", "")
        nome = linha.get("arquivo", "")

        if not PADRAO_ID.match(identificador):
            problemas.append(f"id '{identificador}' fora do padrão EXT000")
        elif contagem_ids[identificador] > 1:
            problemas.append(f"id duplicado: {identificador}")

        motivo = _nome_simples(nome)
        if motivo:
            problemas.append(motivo)
        else:
            if contagem_arquivos[nome.lower()] > 1:
                problemas.append(f"arquivo duplicado: {nome}")
            extensao = Path(nome).suffix.lower()
            if extensao not in EXTENSOES:
                problemas.append(f"extensão não aceita: '{extensao}' (aceitas: .jpg, .jpeg, .png)")
            else:
                formato = linha.get("formato", "").upper()
                if formato and EXTENSOES[extensao] != ("JPG" if formato == "JPEG" else formato):
                    problemas.append(f"formato '{formato}' não corresponde à extensão '{extensao}'")
            caminho = (pasta / nome).resolve()
            if caminho.parent != pasta:
                problemas.append("arquivo fora da pasta imagens/")
            elif not caminho.is_file():
                problemas.append(f"arquivo não encontrado em imagens/: {nome}")

        for campo, permitidos in CONDICOES.items():
            valor = linha.get(campo, "")
            if valor not in permitidos:
                problemas.append(f"{campo} '{valor}' inválido (use: {', '.join(permitidos)})")
        if linha.get("formato", "").upper() not in FORMATOS:
            problemas.append(f"formato '{linha.get('formato', '')}' inválido (use: JPG, JPEG, PNG)")

        if problemas:
            invalidas.append({"linha_manifesto": numero, "id": identificador, "arquivo": nome,
                              "problemas": problemas})
        else:
            validas.append(linha)

    return validas, invalidas


def fotos_na_pasta(pasta: Path | None = None) -> list[str]:
    pasta = pasta or PASTA_IMAGENS
    if not pasta.is_dir():
        return []
    return sorted(p.name for p in pasta.iterdir() if p.is_file() and p.suffix.lower() in EXTENSOES)


# ---------------------------------------------------------------------------
# Hashes do pipeline congelado (mecanismo da Fase 10, reaproveitado)
# ---------------------------------------------------------------------------

def conferir_congelamento() -> dict[str, object]:
    """Compara os arquivos do algoritmo com o checkpoint congelado."""
    atuais = fase10.hashes_congelados()
    referencia = fase10.ler_hashes(HASHES_REFERENCIA) if HASHES_REFERENCIA.is_file() else {}
    comparacao = {nome: {"referencia": referencia.get(nome), "atual": valor,
                         "identico": referencia.get(nome) == valor}
                  for nome, valor in atuais.items()}
    git = fase10.estado_git()
    return {
        "referencia": "docs/processamento-imagens/dados-avaliacao/hashes-pipeline-antes.txt",
        "referencia_encontrada": bool(referencia),
        "arquivos": comparacao,
        "todos_identicos": bool(referencia) and all(c["identico"] for c in comparacao.values()),
        "arquivos_congelados_alterados_no_git": git["arquivos_congelados_alterados"],
        "commit": git["commit"],
        "momento": fase10.agora(),
    }


def _gravar_hashes(momento: str, conferencia: dict[str, object]) -> None:
    linhas = [f"# Hashes do pipeline congelado — {momento} da avaliação externa (Fase 11)",
              f"# commit: {conferencia['commit']}",
              f"# data/hora: {conferencia['momento']}",
              f"# referência: {conferencia['referencia']}",
              "arquivo;hash_referencia;hash_atual;IDENTICO"]
    for nome, c in conferencia["arquivos"].items():  # type: ignore[union-attr]
        linhas.append(f"{nome};{c['referencia']};{c['atual']};{'SIM' if c['identico'] else 'NAO'}")
    linhas.append(f"# todos idênticos: {'SIM' if conferencia['todos_identicos'] else 'NAO'}")
    (PASTA_SAIDA / f"hashes-pipeline-{momento}.txt").write_text(
        "\n".join(linhas) + "\n", encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# Resultado por foto
# ---------------------------------------------------------------------------

_pegar = fase10._pegar


def processar_foto(caminho: Path, destino: Path | None) -> tuple[dict, float]:
    """Chama o pipeline congelado. Exceção vira erro registrado; o lote continua."""
    inicio = time.perf_counter()
    try:
        resultado = processar_folha(caminho, salvar_imagens=destino is not None, destino=destino)
    except Exception as erro:  # noqa: BLE001 — registrar, nunca esconder
        resultado = {
            "status": "erro", "objeto": None, "caracteristicas": None, "classificacao": None,
            "avisos": [], "processamento": None, "imagens_intermediarias": {},
            "erro": {"codigo": "EXCECAO_NAO_TRATADA", "mensagem": f"{type(erro).__name__}: {erro}"},
        }
    return resultado, (time.perf_counter() - inicio) * 1000.0


def linha_da_foto(entrada: dict[str, str], resultado: dict, tempo_parede_ms: float) -> dict:
    """Achata o resultado do pipeline. Não calcula nada."""
    erro = resultado.get("erro") or {}
    obj = resultado.get("objeto") or {}
    car = resultado.get("caracteristicas") or {}
    cla = resultado.get("classificacao") or {}
    ent = resultado.get("entrada") or {}
    avisos = resultado.get("avisos") or []

    linha = {
        "id": entrada["id"], "arquivo": entrada["arquivo"],
        "fundo": entrada["fundo"], "iluminacao": entrada["iluminacao"],
        "posicao": entrada["posicao"], "distancia": entrada["distancia"],
        "formato": entrada["formato"].upper(),
        "status": resultado.get("status"),
        "erro_codigo": erro.get("codigo"), "erro_mensagem": erro.get("mensagem"),
        "largura_original_px": ent.get("largura_original_px"),
        "altura_original_px": ent.get("altura_original_px"),
        "tinha_canal_alfa": ent.get("tinha_canal_alfa"),
        "detectado": obj.get("detectado", False),
        "fracao_foreground": obj.get("fracao_foreground"),
        "numero_contornos": obj.get("numero_contornos"),
        "dominancia": obj.get("dominancia"),
        "toca_borda": _pegar(obj, "toca_borda", "qualquer"),
        "distancia_minima_borda_px": obj.get("distancia_minima_borda_px"),
        "area_contorno_px2": _pegar(car, "dimensoes", "area_contorno_px2"),
        "elongacao": _pegar(car, "forma", "elongacao"),
        "circularidade": _pegar(car, "forma", "circularidade"),
        "solidez": _pegar(car, "forma", "solidez"),
        "razao_perimetro_hull": _pegar(car, "convexidade", "razao_perimetro_hull"),
        "anisotropia": _pegar(car, "orientacao", "anisotropia"),
        "orientacao_confiavel": _pegar(car, "orientacao", "confiavel"),
        "proporcao_verde": _pegar(car, "cor", "proporcao_verde"),
    }
    for atributo in ATRIBUTOS:
        regra = cla.get(atributo) or {}
        linha[f"cat_{atributo}"] = regra.get("categoria")
        linha[f"limitrofe_{atributo}"] = regra.get("limitrofe")
    linha["n_limitrofes"] = sum(1 for a in ATRIBUTOS if linha[f"limitrofe_{a}"])
    linha["tempo_pipeline_ms"] = _pegar(resultado, "processamento", "tempo_total_ms")
    linha["tempo_parede_ms"] = round(tempo_parede_ms, 3)
    tecnicos = [a for a in avisos if a != AVISO_PADRAO]
    linha["n_avisos_tecnicos"] = len(tecnicos)
    linha["avisos"] = " | ".join(avisos)
    return linha


# ---------------------------------------------------------------------------
# Agregação
# ---------------------------------------------------------------------------

def resumir(linhas: list[dict], invalidas: list[dict]) -> dict:
    total = len(linhas) + len(invalidas)
    validas = [l for l in linhas if l["status"] in ("sucesso", "sucesso_com_avisos")]
    erros = [l for l in linhas if l["status"] == "erro"]

    cobertura = {
        "entradas_no_manifesto": total,
        "entradas_invalidas_nao_processadas": len(invalidas),
        "processadas": len(linhas),
        "sucesso_operacional": len(validas),
        "erro": len(erros),
        "taxa_processamento_pct": round(100.0 * len(validas) / len(linhas), 2) if linhas else None,
        "com_aviso_tecnico": sum(1 for l in validas if l["n_avisos_tecnicos"] > 0),
        "observacao": ("sucesso operacional = o pipeline chegou ao fim com um objeto medido; "
                       "não diz se o objeto é a folha — isso é da inspeção humana"),
    }

    por_codigo: dict[str, dict] = {}
    for l in erros:
        d = por_codigo.setdefault(l["erro_codigo"], {"quantidade": 0, "ids": []})
        d["quantidade"] += 1
        d["ids"].append(l["id"])

    avisos: dict[str, dict] = {}
    for l in linhas:
        for a in (l["avisos"].split(" | ") if l["avisos"] else []):
            if a == AVISO_PADRAO:
                continue
            d = avisos.setdefault(fase10._chave_aviso(a), {"quantidade": 0, "ids": []})
            d["quantidade"] += 1
            d["ids"].append(l["id"])

    por_condicao: dict[str, dict] = {}
    for campo, valores in CONDICOES.items():
        por_condicao[campo] = {}
        for valor in valores:
            grupo = [l for l in linhas if l[campo] == valor]
            por_condicao[campo][valor] = {
                "fotos": len(grupo),
                "sucesso_operacional": sum(1 for l in grupo if l["status"] != "erro"),
                "erro": sum(1 for l in grupo if l["status"] == "erro"),
                "com_aviso_tecnico": sum(1 for l in grupo if l["n_avisos_tecnicos"] > 0),
                "ids": [l["id"] for l in grupo],
            }

    return {
        "cobertura": cobertura,
        "erros": {"total": len(erros), "por_codigo": por_codigo},
        "entradas_invalidas": invalidas,
        "avisos_tecnicos": avisos,
        "caracteristicas": {f: fase10.descrever([l[f] for l in validas])
                            for f in ("fracao_foreground", "elongacao", "circularidade", "solidez",
                                      "razao_perimetro_hull", "anisotropia")},
        "classificacoes": {a: _contar([l[f"cat_{a}"] for l in validas]) for a in ATRIBUTOS},
        "por_condicao": por_condicao,
        "performance": {
            "tempo_parede_ms": fase10.descrever([l["tempo_parede_ms"] for l in linhas]),
            "tempo_pipeline_ms": fase10.descrever([l["tempo_pipeline_ms"] for l in validas]),
            "observacao": ("inclui a geração das 8 imagens intermediárias de cada foto; "
                           "não é diretamente comparável ao tempo da Fase 10, que foi sem imagens"),
        },
        "comparacao_fase10": comparar_com_fase10(linhas),
    }


def _contar(valores: list[object]) -> dict[str, int]:
    saida: dict[str, int] = {}
    for v in valores:
        saida[str(v)] = saida.get(str(v), 0) + 1
    return saida


def comparar_com_fase10(linhas: list[dict]) -> dict[str, object]:
    """Lado a lado, **sem conclusão automática**: as duas populações não são misturadas."""
    fase10_resumo = (json.loads(RESUMO_FASE10.read_text(encoding="utf-8"))
                     if RESUMO_FASE10.is_file() else None)
    validas = [l for l in linhas if l["status"] != "erro"]
    externo = {
        "condicao": "fotos reais, fundo e iluminação não controlados",
        "imagens": len(linhas),
        "taxa_processamento_pct": round(100.0 * len(validas) / len(linhas), 2) if linhas else None,
        "com_aviso_tecnico": sum(1 for l in validas if l["n_avisos_tecnicos"] > 0),
        "tempo_parede_mediana_ms": fase10.descrever([l["tempo_parede_ms"] for l in linhas]).get("mediana"),
        "inspecao_humana": "ver fase11-inspecao-resumo.json, após a revisão",
    }
    flavia = None
    if fase10_resumo:
        flavia = {
            "condicao": "Flavia, fundo branco controlado",
            "imagens": fase10_resumo["cobertura"]["total_imagens"],
            "taxa_processamento_pct": fase10_resumo["cobertura"]["taxa_processamento_valido_pct"],
            "com_aviso_tecnico": fase10_resumo["cobertura"]["validas_com_aviso_tecnico"],
            "tempo_parede_mediana_ms": fase10_resumo["performance"]["tempo_parede_por_imagem_ms"]["mediana"],
            "inspecao_humana": "pendente (Fase 10)",
        }
    return {"flavia_fase10": flavia, "fotos_externas_fase11": externo,
            "conclusao": None,
            "observacao": "a comparação é descritiva; a conclusão é escrita por pessoas, após a inspeção"}


def resumir_inspecao(caminho: Path | None = None) -> dict[str, object]:
    """Resume a revisão **humana** já preenchida. Valores fora do vocabulário são apontados."""
    caminho = caminho or (PASTA_SAIDA / "fase11-inspecao.csv")
    linhas = list(csv.DictReader(open(caminho, encoding="utf-8-sig")))
    julgamentos = ("folha_principal_segmentada", "mascara_visual_adequada",
                   "contorno_visual_adequado", "resultado_util")
    resumo: dict[str, object] = {"fotos": len(linhas), "revisadas": 0, "valores_invalidos": []}
    for coluna in julgamentos:
        resumo[coluna] = {v: 0 for v in (*VALORES_JULGAMENTO, "nao_preenchido")}
    resumo["problema_principal"] = {p: 0 for p in (*PROBLEMAS, "nao_preenchido")}
    for l in linhas:
        if any(l.get(c, "").strip() for c in COLUNAS_HUMANAS):
            resumo["revisadas"] += 1  # type: ignore[operator]
        for coluna in julgamentos:
            valor = l.get(coluna, "").strip().lower() or "nao_preenchido"
            if valor not in resumo[coluna]:  # type: ignore[operator]
                resumo["valores_invalidos"].append({"id": l["id"], "coluna": coluna, "valor": valor})  # type: ignore[union-attr]
                continue
            resumo[coluna][valor] += 1  # type: ignore[index]
        problema = l.get("problema_principal", "").strip().lower() or "nao_preenchido"
        if problema in resumo["problema_principal"]:  # type: ignore[operator]
            resumo["problema_principal"][problema] += 1  # type: ignore[index]
        else:
            resumo["valores_invalidos"].append({"id": l["id"], "coluna": "problema_principal", "valor": problema})  # type: ignore[union-attr]
    return resumo


def inspecao_ja_preenchida(caminho: Path | None = None) -> bool:
    caminho = caminho or (PASTA_SAIDA / "fase11-inspecao.csv")
    if not caminho.is_file():
        return False
    return any(any(l.get(c, "").strip() for c in COLUNAS_HUMANAS)
               for l in csv.DictReader(open(caminho, encoding="utf-8-sig")))


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------

def _json(dados: object, destino: Path) -> None:
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                       encoding="utf-8", newline="\n")


def _csv(linhas: list[dict], colunas: list[str], destino: Path) -> None:
    with open(destino, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(linhas)


def avaliar() -> int:
    linhas_manifesto = ler_manifesto()
    if not linhas_manifesto or not fotos_na_pasta():
        print(MENSAGEM_SEM_FOTOS)
        return 0

    if inspecao_ja_preenchida():
        print("fase11-inspecao.csv já tem revisão humana preenchida — a avaliação NÃO foi "
              "executada de novo, para não sobrescrever o julgamento da equipe.")
        return 5

    validas, invalidas = validar_manifesto(linhas_manifesto)
    for inv in invalidas:
        print(f"  entrada inválida (linha {inv['linha_manifesto']}, {inv['id'] or 'sem id'}): "
              + "; ".join(inv["problemas"]))  # type: ignore[arg-type]
    if not validas:
        print("Nenhuma entrada válida no manifesto — nada foi processado.")
        return 2

    antes = conferir_congelamento()
    if not antes["todos_identicos"] or antes["arquivos_congelados_alterados_no_git"]:
        print("O pipeline não está idêntico ao checkpoint congelado — avaliação NÃO executada.")
        return 3
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    _gravar_hashes("antes", antes)

    inicio = fase10.agora()
    resultados, linhas = [], []
    for entrada in validas:
        destino = PASTA_VISUAL / entrada["id"]
        resultado, tempo = processar_foto(PASTA_IMAGENS / entrada["arquivo"], destino)
        resultados.append(resultado)
        linhas.append(linha_da_foto(entrada, resultado, tempo))
        print(f"  {entrada['id']}  {entrada['arquivo']:<24} {resultado['status']}")

    depois = conferir_congelamento()
    _gravar_hashes("depois", depois)

    metadados = {
        "fase": 11, "descricao": "robustez com fotos externas — pipeline congelado",
        "commit": antes["commit"], "tag_congelada": fase10.TAG_AVALIADA,
        "versao_pipeline": VERSAO_PIPELINE, "inicio": inicio, "fim": fase10.agora(),
        "manifesto": "processamento-imagens/fotos-externas/manifesto.csv",
        "pasta_imagens": "processamento-imagens/fotos-externas/imagens (não versionada)",
        "imagens_intermediarias": "processamento-imagens/resultados/robustez-fase11/<id>/ (não versionada)",
        "hashes_identicos_antes": antes["todos_identicos"],
        "hashes_identicos_depois": depois["todos_identicos"],
    }
    resumo = resumir(linhas, invalidas)

    _json({"metadados": metadados,
           "resultados": [{"linha": l, "resultado": r} for l, r in zip(linhas, resultados)],
           "entradas_invalidas": invalidas},
          PASTA_SAIDA / "fase11-resultados-completos.json")
    _csv(linhas, list(linhas[0]), PASTA_SAIDA / "fase11-resultados.csv")
    _json({"metadados": metadados, **resumo}, PASTA_SAIDA / "fase11-resumo.json")
    _csv([{"id": l["id"], "arquivo": l["arquivo"], **{c: "" for c in COLUNAS_HUMANAS}} for l in linhas],
         ["id", "arquivo", *COLUNAS_HUMANAS], PASTA_SAIDA / "fase11-inspecao.csv")

    c = resumo["cobertura"]
    print(f"\n{c['processadas']} fotos processadas · sucesso operacional {c['sucesso_operacional']} · "
          f"erros {c['erro']} · inválidas {c['entradas_invalidas_nao_processadas']} · "
          f"hashes {'idênticos' if depois['todos_identicos'] else 'DIVERGENTES'}")
    print("Próximo passo: revisar as imagens em resultados/robustez-fase11/ e preencher "
          "docs/processamento-imagens/dados-robustez/fase11-inspecao.csv")
    return 0 if depois["todos_identicos"] else 4


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        return avaliar()
    if argv == ["verificar"]:
        linhas = ler_manifesto()
        if not linhas or not fotos_na_pasta():
            print(MENSAGEM_SEM_FOTOS)
            return 0
        validas, invalidas = validar_manifesto(linhas)
        print(f"{len(linhas)} entradas · {len(validas)} válidas · {len(invalidas)} inválidas")
        for inv in invalidas:
            print(f"  linha {inv['linha_manifesto']} ({inv['id'] or 'sem id'}): " + "; ".join(inv["problemas"]))  # type: ignore[arg-type]
        return 0 if not invalidas else 2
    if argv == ["inspecao"]:
        caminho = PASTA_SAIDA / "fase11-inspecao.csv"
        if not caminho.is_file():
            print("fase11-inspecao.csv ainda não existe — execute a avaliação primeiro.")
            return 0
        resumo = resumir_inspecao(caminho)
        _json(resumo, PASTA_SAIDA / "fase11-inspecao-resumo.json")
        print(f"{resumo['revisadas']} de {resumo['fotos']} fotos com revisão humana; "
              f"valores inválidos: {len(resumo['valores_invalidos'])}")  # type: ignore[arg-type]
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
