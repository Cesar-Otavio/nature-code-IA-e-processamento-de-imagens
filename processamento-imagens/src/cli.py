"""Interface de linha de comando — casca fina sobre o pipeline.

Uso::

    cd processamento-imagens
    python -m src.cli caminho/da/imagem.jpg

**Nenhuma lógica de processamento mora aqui.** Este módulo interpreta argumentos, chama
``pipeline.processar_folha()`` e formata a saída. Há teste estrutural que falha se ele
importar ``cv2`` ou ``numpy`` — a garantia de que a lógica não foi duplicada.

Códigos de saída:

=====  =================================================
  0    Sucesso, com ou sem avisos
  1    Objeto não encontrado (``E007``)
  2    Erro de entrada (``E001``–``E006``)
  3    Erro interno inesperado
=====  =================================================
"""

from __future__ import annotations

import argparse
import json
import sys

from .pipeline import processar_folha

#: Mapeia código de erro de domínio para código de saída do processo.
CODIGOS_DE_SAIDA = {
    "E001": 2, "E002": 2, "E003": 2, "E004": 2, "E005": 2, "E006": 2,
    "E007": 1,
    "E008": 3, "E009": 3, "E010": 3, "E011": 1,
}


def montar_analisador() -> argparse.ArgumentParser:
    """Define os argumentos aceitos."""
    analisador = argparse.ArgumentParser(
        prog="python -m src.cli",
        description="Análise morfológica de folhas por processamento digital de imagens. "
                    "Não utiliza inteligência artificial e não identifica espécies.",
    )
    analisador.add_argument("imagem", help="caminho da imagem a analisar")
    analisador.add_argument("--saida", metavar="DIR", default=None,
                            help="diretório dos resultados (padrão: resultados/execucoes/<id>)")
    analisador.add_argument("--sem-imagens", action="store_true",
                            help="não gerar as imagens intermediárias")
    analisador.add_argument("--json-apenas", action="store_true",
                            help="imprimir somente o JSON, sem resumo legível")
    analisador.add_argument("--verboso", action="store_true",
                            help="detalhar tempos por etapa em stderr")
    return analisador


def _formatar_resumo(resultado: dict) -> str:
    """Monta o resumo legível por pessoas."""
    linhas: list[str] = []
    entrada = resultado["entrada"] or {}
    caracteristicas = resultado["caracteristicas"]
    classificacao = resultado["classificacao"]

    linhas.append("Imagem processada com sucesso")
    linhas.append("")
    linhas.append(f"  arquivo ............ {entrada.get('arquivo')}")
    linhas.append(f"  original ........... {entrada.get('largura_original_px')}x{entrada.get('altura_original_px')}")
    linhas.append(f"  processada ......... {entrada.get('largura_processada_px')}x{entrada.get('altura_processada_px')}")
    linhas.append("")

    dimensoes = caracteristicas["dimensoes"]
    forma = caracteristicas["forma"]
    linhas.append("Medidas")
    linhas.append(f"  área ............... {dimensoes['area_contorno_px2']:,.0f} px²")
    linhas.append(f"  perímetro .......... {dimensoes['perimetro_px']:,.1f} px")
    linhas.append(f"  elongação .......... {forma['elongacao']:.2f}")
    linhas.append(f"  circularidade ...... {forma['circularidade']:.4f}")
    linhas.append(f"  solidez ............ {forma['solidez']:.4f}")
    linhas.append(f"  extent ............. {forma['extent']:.4f}")
    linhas.append("")

    linhas.append("Descrição morfológica")
    for atributo in ("alongamento", "concavidade", "compacidade", "complexidade_borda", "orientacao"):
        linhas.append(f"  {atributo:<19} {classificacao[atributo]['categoria']}")
    linhas.append("")
    linhas.append(f"  {classificacao['resumo']}")

    if resultado["avisos"]:
        linhas.append("")
        linhas.append("Avisos")
        for aviso in resultado["avisos"]:
            linhas.append(f"  - {aviso}")

    if resultado["imagens_intermediarias"]:
        linhas.append("")
        linhas.append(f"  {len(resultado['imagens_intermediarias'])} imagens em: "
                      f"resultados/execucoes/{resultado['id_execucao']}/")

    processamento = resultado["processamento"] or {}
    linhas.append("")
    linhas.append(f"Tempo total: {processamento.get('tempo_total_ms', 0):.1f} ms")

    return "\n".join(linhas)


def main(argumentos: list[str] | None = None) -> int:
    """Executa a CLI.

    Args:
        argumentos: Argumentos de linha de comando. ``None`` usa ``sys.argv``.

    Returns:
        O código de saída do processo.
    """
    opcoes = montar_analisador().parse_args(argumentos)

    try:
        resultado = processar_folha(
            opcoes.imagem,
            salvar_imagens=not opcoes.sem_imagens,
            destino=opcoes.saida,
        )
    except Exception as erro:  # noqa: BLE001 — a CLI não pode vazar rastreamento
        print(f"Erro interno inesperado: {type(erro).__name__}", file=sys.stderr)
        return 3

    if opcoes.json_apenas:
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
    elif resultado["status"] == "erro":
        erro = resultado["erro"]
        print(f"[{erro['codigo']}] {erro['mensagem']}", file=sys.stderr)
    else:
        print(_formatar_resumo(resultado))

    if opcoes.verboso and resultado["processamento"]:
        for etapa, tempo in resultado["processamento"]["tempo_por_etapa_ms"].items():
            print(f"  {etapa:<20} {tempo:>8.3f} ms", file=sys.stderr)

    if resultado["status"] == "erro":
        return CODIGOS_DE_SAIDA.get(resultado["erro"]["codigo"], 3)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
