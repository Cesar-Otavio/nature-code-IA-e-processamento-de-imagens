# Dataset — Flavia Leaf Dataset

> **As imagens não estão neste repositório e nunca estarão.**
> Este diretório contém apenas a documentação e o manifesto de rastreabilidade. As 1.907
> imagens (965,7 MB) são obtidas por download da fonte oficial, seguindo as instruções
> abaixo.

---

## Identificação

| | |
|---|---|
| **Nome** | Flavia Leaf Dataset |
| **Fonte oficial** | http://flavia.sourceforge.net/ |
| **Projeto** | https://sourceforge.net/projects/flavia/ |
| **Origem do material** | Campus da Universidade de Nanjing e Arboreto Sun Yat-Sen, Nanquim, China — plantas comuns do Delta do Yangtzé |
| **Imagens** | 1.907 |
| **Espécies** | 32 (50 a 77 imagens por espécie) |
| **Formato** | JPEG |
| **Resolução** | 1600 × 1200 px |
| **Fundo** | Branco, uniforme |
| **Tamanho do pacote** | 965,7 MB (`Leaves.tar.bz2`) |
| **Cadastro** | Não exigido |
| **Verificado em** | 19 de setembro de 2026 — HTTP 200, `Content-Length: 965715159` |

---

## Como obter

### Dataset completo — necessário para desenvolvimento e avaliação

```bash
cd processamento-imagens/dataset
mkdir -p dados && cd dados

curl -L -o Leaves.tar.bz2 \
  "https://sourceforge.net/projects/flavia/files/Leaf%20Image%20Dataset/1.0/Leaves.tar.bz2/download"

tar -xjf Leaves.tar.bz2
```

### Subconjunto pequeno — 32 imagens, 17,2 MB

Uma imagem representativa por espécie. Útil para verificação rápida, sem baixar quase 1 GB:

```bash
curl -L -o standardleaves.tar.bz2 \
  "https://sourceforge.net/projects/flavia/files/Standard%20Leaf%20Images/0.1/standardleaves.tar.bz2/download"

tar -xjf standardleaves.tar.bz2
```

---

## Onde colocar e estrutura esperada

```
processamento-imagens/dataset/
├── README.md          ← este arquivo (versionado)
├── manifesto.csv      ← quais imagens foram usadas (versionado)
└── dados/             ← IGNORADO PELO GIT
    ├── Leaves.tar.bz2
    └── Leaves/
        ├── 1001.jpg
        ├── 1002.jpg
        └── ...        1.907 arquivos
```

O diretório `dados/` é coberto pela regra `processamento-imagens/dataset/*` do
[`.gitignore`](../../.gitignore) da raiz. **Confira com `git status` após o download**: nada
de `dados/` deve aparecer.

---

## Política de não versionamento

**O dataset completo não entra no repositório**, mesmo que a licença permitisse.

| Motivo | |
|---|---|
| **Tamanho** | O repositório já carrega 120 MB em `images/`. Acrescentar 965 MB inviabilizaria clone e histórico |
| **Redistribuição** | Material de terceiros não é redistribuído por este projeto |
| **Reprodutibilidade** | O link oficial mais o `manifesto.csv` reconstroem exatamente o experimento, sem copiar imagem alguma |

O que **é** versionado: este README, o `manifesto.csv`, o script de seleção e poucas imagens
de autoria própria em `../exemplos/`.

---

## Licença e condições de uso

> **Declaração honesta, conforme verificado em 19/09/2026.**

O projeto Flavia está registrado no SourceForge sob **"GNU General Public License version
2.0 (GPLv2)"**. Essa declaração cobre **o projeto**, que inclui o software de reconhecimento
de folhas.

**Não foi localizada uma declaração de licença específica e separada para o conjunto de
imagens.**

O uso neste trabalho é:

- estritamente **acadêmico**;
- **sem redistribuição** de qualquer imagem;
- **com citação** do artigo original;
- limitado a **análise** das imagens obtidas na fonte oficial.

Esse uso se mantém dentro de qualquer leitura razoável dos termos declarados. Caso a equipe
precise de garantia formal para publicação, o caminho é contatar os autores.

### Citação obrigatória

> Stephen Gang Wu, Forrest Sheng Bao, Eric You Xu, Yu-Xuan Wang, Yi-Fan Chang, Qiao-Liang
> Xiang. **A Leaf Recognition Algorithm for Plant Classification Using Probabilistic Neural
> Network.** IEEE 7th International Symposium on Signal Processing and Information Technology
> (ISSPIT), dezembro de 2007.

---

## Finalidade acadêmica neste projeto

Disciplina de **Processamento de Imagens e Sinais** — análise morfológica de folhas por
processamento digital clássico.

> **O dataset NÃO é usado para treinar nada.** Não há rede neural, aprendizado de máquina,
> modelo pré-treinado ou classificação supervisionada. As imagens servem para desenvolver e
> avaliar algoritmos **determinísticos** de segmentação e medição.

As classes de espécie do dataset são preservadas no manifesto apenas para **garantir
diversidade morfológica** e **estratificar a amostragem**. Elas não são usadas como alvo de
classificação, e o projeto **não promete identificar espécies**.

---

## Observações sobre as imagens

Registradas por inspeção visual direta do subconjunto de 32 imagens, em 19/09/2026.

| Aspecto | Observação |
|---|---|
| **Fundo** | Branco e uniforme; separabilidade folha/fundo muito alta |
| **Orientação** | Variada, frequentemente diagonal — sem alinhamento padronizado |
| **Escala** | Muito variada, de folhas que quase preenchem o quadro a acículas finíssimas |
| **Pecíolo** | Ausente na maioria; curto e presente em algumas |
| **Artefatos** | Pequenos resíduos bege/amarelados no fundo, próximos à folha, em parte das imagens |
| **Sombra** | Suave, sob a folha, em alguns casos |
| **Reflexo** | Especular em folhas de superfície brilhante |
| **Borda do quadro** | **Há casos em que a folha toca a borda** |

### Consequências para o pipeline

1. A **abertura morfológica** é necessária: os artefatos de fundo serão capturados pela
   limiarização e precisam ser removidos antes da seleção do contorno.
2. O aviso de "objeto toca a borda" tem **caso real** no dataset.
3. Acículas muito finas são o caso mais severo para o perímetro digital — poucos pixels de
   largura produzem razão perímetro/área muito desfavorável.

### Limitação principal, dita com clareza

> O Flavia é um dataset de **laboratório**. Fundo branco, folha isolada, luz uniforme e
> câmera fixa representam o **melhor caso**.
>
> Um pipeline que funcione perfeitamente aqui demonstra que **os algoritmos estão corretos**
> — não que funcionará numa foto tirada com celular sobre a grama.

---

## Documentação relacionada

| Documento | Conteúdo |
|---|---|
| [`docs/processamento-imagens/02-DATASET.md`](../../docs/processamento-imagens/02-DATASET.md) | Comparação completa dos candidatos, justificativa da escolha e protocolo de avaliação |
| [`docs/processamento-imagens/01-DEFINICAO-PROBLEMA.md`](../../docs/processamento-imagens/01-DEFINICAO-PROBLEMA.md) | Contratos de entrada e saída, características e fórmulas |
| `manifesto.csv` | Quais imagens participaram de cada conjunto |
