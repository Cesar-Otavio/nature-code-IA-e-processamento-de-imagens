"""Seleciona os subconjuntos de desenvolvimento e avaliação do Flavia.

Amostragem **aleatória estratificada por espécie**, com semente fixa, conforme a
política definida em ``docs/processamento-imagens/02-DATASET.md`` §12.

Por que estratificada e com semente:

- **estratificada**, para que todas as 32 espécies apareçam nos dois conjuntos —
  um pipeline validado só em folhas ovais não foi validado;
- **com semente fixa**, para que a seleção seja reproduzível por qualquer pessoa que
  baixe o dataset da fonte oficial;
- **disjunta por construção**, para que o conjunto de avaliação nunca tenha sido
  usado no ajuste de parâmetros.

Uso::

    cd processamento-imagens
    .venv/Scripts/python.exe selecionar_subconjunto.py

Gera ``dataset/manifesto.csv``, que é versionado. As imagens **não** são copiadas
nem versionadas: o manifesto identifica quais arquivos do dataset original foram
usados, e isso basta para reproduzir o experimento.
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

#: Semente da amostragem. Fixa e registrada: trocá-la muda os conjuntos.
SEMENTE = 20260919

#: Imagens por espécie em cada conjunto.
POR_ESPECIE_DESENVOLVIMENTO = 2
POR_ESPECIE_AVALIACAO = 3

#: Faixas de número de arquivo por espécie, conforme a tabela publicada em
#: http://flavia.sourceforge.net/ (consultada em 19/09/2026).
#:
#: O rótulo 13 não existe no dataset original — a numeração vai até 33 e produz
#: 32 espécies. A ausência é do dataset, não um erro de transcrição.
ESPECIES: list[tuple[int, str, str, int, int]] = [
    (1, "Phyllostachys edulis", "Bambu pubescente", 1001, 1059),
    (2, "Aesculus chinensis", "Castanha-da-india chinesa", 1060, 1122),
    (3, "Berberis anhweiensis", "Berberis de Anhui", 1552, 1616),
    (4, "Cercis chinensis", "Olaia chinesa", 1123, 1194),
    (5, "Indigofera tinctoria", "Anil verdadeiro", 1195, 1267),
    (6, "Acer palmatum", "Bordo japones", 1268, 1323),
    (7, "Phoebe nanmu", "Nanmu", 1324, 1385),
    (8, "Kalopanax septemlobus", "Aralia-de-mamona", 1386, 1437),
    (9, "Cinnamomum japonicum", "Canela chinesa", 1497, 1551),
    (10, "Koelreuteria paniculata", "Arvore-da-chuva-dourada", 1438, 1496),
    (11, "Ilex macrocarpa", "Azevinho de fruto grande", 2001, 2050),
    (12, "Pittosporum tobira", "Pitosporo japones", 2051, 2113),
    (14, "Chimonanthus praecox", "Jasmim-de-inverno", 2114, 2165),
    (15, "Cinnamomum camphora", "Canforeira", 2166, 2230),
    (16, "Viburnum awabuki", "Viburno japones", 2231, 2290),
    (17, "Osmanthus fragrans", "Osmanto perfumado", 2291, 2346),
    (18, "Cedrus deodara", "Cedro-do-himalaia", 2347, 2423),
    (19, "Ginkgo biloba", "Ginkgo", 2424, 2485),
    (20, "Lagerstroemia indica", "Resedá", 2486, 2546),
    (21, "Nerium oleander", "Espirradeira", 2547, 2612),
    (22, "Podocarpus macrophyllus", "Pinheiro-budista", 2616, 2675),
    (23, "Prunus serrulata", "Cerejeira japonesa", 3001, 3055),
    (24, "Ligustrum lucidum", "Alfeneiro", 3056, 3110),
    (25, "Toona sinensis", "Toona chinesa", 3111, 3175),
    (26, "Prunus persica", "Pessegueiro", 3176, 3229),
    (27, "Manglietia fordiana", "Manglietia", 3230, 3281),
    (28, "Acer buergerianum", "Bordo tridente", 3282, 3334),
    (29, "Mahonia bealei", "Mahonia", 3335, 3389),
    (30, "Magnolia grandiflora", "Magnolia do sul", 3390, 3446),
    (31, "Populus x canadensis", "Choupo canadense", 3447, 3510),
    (32, "Liriodendron chinense", "Tulipeira chinesa", 3511, 3563),
    (33, "Citrus reticulata", "Tangerina", 3566, 3621),
]


def arquivos_existentes(pasta: Path, inicio: int, fim: int) -> list[str]:
    """Lista os arquivos da faixa que realmente existem no disco.

    As faixas publicadas são nominais: nem todo número dentro do intervalo
    corresponde a um arquivo. Conferir a existência evita montar um manifesto que
    aponta para imagens inexistentes.
    """
    return [f"{n}.jpg" for n in range(inicio, fim + 1) if (pasta / f"{n}.jpg").is_file()]


def main() -> int:
    raiz = Path(__file__).resolve().parent
    pasta = raiz / "dataset" / "dados" / "Leaves"
    destino = raiz / "dataset" / "manifesto.csv"

    if not pasta.is_dir():
        print(f"Dataset não encontrado em {pasta}", file=sys.stderr)
        print("Baixe conforme dataset/README.md antes de executar.", file=sys.stderr)
        return 2

    sorteador = random.Random(SEMENTE)
    linhas: list[dict[str, object]] = []
    total_disponivel = 0
    faltantes: list[str] = []

    for rotulo, cientifico, comum, inicio, fim in ESPECIES:
        disponiveis = arquivos_existentes(pasta, inicio, fim)
        total_disponivel += len(disponiveis)
        necessarias = POR_ESPECIE_DESENVOLVIMENTO + POR_ESPECIE_AVALIACAO

        if len(disponiveis) < necessarias:
            faltantes.append(f"{cientifico}: {len(disponiveis)} de {necessarias}")
            continue

        # sample sobre lista ordenada + semente fixa = seleção reproduzível.
        sorteadas = sorteador.sample(sorted(disponiveis), necessarias)
        desenvolvimento = sorted(sorteadas[:POR_ESPECIE_DESENVOLVIMENTO])
        avaliacao = sorted(sorteadas[POR_ESPECIE_DESENVOLVIMENTO:])

        for arquivo in desenvolvimento:
            linhas.append({
                "arquivo": arquivo, "dataset_origem": "flavia",
                "classe_original": f"{rotulo:02d}-{cientifico}",
                "uso": "desenvolvimento", "subconjunto": "dev-v1",
                "observacao": comum,
            })
        for arquivo in avaliacao:
            linhas.append({
                "arquivo": arquivo, "dataset_origem": "flavia",
                "classe_original": f"{rotulo:02d}-{cientifico}",
                "uso": "avaliacao", "subconjunto": "aval-v1",
                "observacao": comum,
            })

    campos = ["arquivo", "dataset_origem", "classe_original", "uso", "subconjunto", "observacao"]
    with destino.open("w", encoding="utf-8", newline="") as saida:
        escritor = csv.DictWriter(saida, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(sorted(linhas, key=lambda linha: (linha["uso"], linha["classe_original"], linha["arquivo"])))

    dev = sum(1 for linha in linhas if linha["uso"] == "desenvolvimento")
    aval = sum(1 for linha in linhas if linha["uso"] == "avaliacao")
    nomes = [linha["arquivo"] for linha in linhas]

    print(f"semente ................. {SEMENTE}")
    print(f"espécies na tabela ...... {len(ESPECIES)}")
    print(f"imagens no dataset ...... {total_disponivel}")
    print(f"desenvolvimento ......... {dev}")
    print(f"avaliação ............... {aval}")
    print(f"conjuntos disjuntos ..... {len(set(nomes)) == len(nomes)}")
    if faltantes:
        print(f"espécies sem imagens suficientes: {faltantes}")
    print(f"gravado ................. {destino.relative_to(raiz)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
