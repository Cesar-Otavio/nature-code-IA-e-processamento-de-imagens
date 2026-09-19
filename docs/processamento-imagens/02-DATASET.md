# Fase 2 — Seleção, validação e documentação do dataset

> **Estado desta fase: pesquisa e decisão.** Nenhum processamento implementado, nenhuma
> biblioteca instalada, nenhum módulo Python criado.
>
> **Data de todas as verificações: 19 de setembro de 2026.** Cada URL foi aberta e conferida
> nessa data; nenhuma foi reproduzida de memória ou de resultado de busca sem checagem.

---

## 1. Objetivo da fase

Escolher, verificar e documentar o conjunto de imagens que será usado para **desenvolver,
validar e testar** o pipeline de análise morfológica de folhas.

O dataset **não será usado para treinar nada**. Não há aprendizado, não há ajuste de pesos,
não há classificação supervisionada. Seu papel é:

| Uso | Fase |
|---|---|
| Desenvolver e comparar métodos de segmentação clássica | 4 |
| Avaliar robustez do pipeline | 10 |
| Analisar a **distribuição** das características morfológicas | 6 |
| Derivar limiares de classificação determinística, **se os dados suportarem** | 7 |
| Produzir evidências visuais para documentação e apresentação | 10–12 |

---

## 2. Critérios de escolha

Herdados da Fase 1 ([`01-DEFINICAO-PROBLEMA.md`](01-DEFINICAO-PROBLEMA.md) §17), em ordem de
prioridade.

### Prioridade máxima

| # | Critério | Por que pesa tanto |
|---|---|---|
| 1 | Uma folha principal por imagem | O pipeline seleciona o maior contorno; dois objetos comparáveis tornam a escolha ambígua |
| 2 | Folha inteira visível | Área e perímetro de objeto cortado medem outro objeto |
| 3 | Fundo uniforme ou contrastante | **Condição que torna o projeto viável sem IA** |
| 4 | Boa separabilidade folha/fundo | Limiarização clássica depende disso |
| 5 | URL pública e estável | A entrega exige o link, e ele precisa continuar funcionando |
| 6 | Documentação confiável | Rastreabilidade acadêmica |
| 7 | Condições de uso identificáveis | Sem licença conhecida, o uso fica em zona cinzenta |
| 8 | Quantidade suficiente de imagens | Para distribuições, não para treinamento |
| 9 | Variedade de formas | Um pipeline validado só em folhas ovais não foi validado |
| 10 | Variação de tamanho e orientação | Testa invariâncias previstas na Fase 1 §9 |
| 11 | Utilidade para segmentação clássica | Resume os anteriores |

### Critério explicitamente **não** aplicado

> **Número de espécies não é critério de qualidade neste projeto.** O objetivo não é
> classificar espécie. Um dataset de 15 espécies com fundo branco impecável é **superior**,
> para esta finalidade, a um de 185 espécies com cenas naturais.

---

## 3. Metodologia de pesquisa

Para cada candidato, o procedimento foi:

1. localizar a fonte primária (não repositório de terceiro);
2. **abrir a página** e extrair o conteúdo real;
3. registrar mantenedor, origem e documentação;
4. procurar declaração de licença — e, não havendo, **dizer que não há**;
5. verificar quantidade, classes, formato, resolução e fundo;
6. **testar o link de download** por requisição HTTP, conferindo status e tamanho;
7. registrar o artigo associado;
8. registrar a data da verificação.

**Validação final de links** — todos reabertos ao término da fase:

| URL | Status HTTP |
|---|---|
| `http://flavia.sourceforge.net/` | **200** |
| `https://sourceforge.net/projects/flavia/` | **200** |
| Flavia — `Leaves.tar.bz2` (download) | **200**, `Content-Length: 965715159` |
| Flavia — `standardleaves.tar.bz2` (download) | **200** (baixado com sucesso) |
| `https://www.cvl.isy.liu.se/research/datasets/swedish-leaf/` | **200** |
| `https://leafsnap.com/dataset/` | **200** |
| Leafsnap — `leafsnap-dataset.tar` (download) | ❌ **404** |
| `https://github.com/spMohanty/PlantVillage-Dataset` | **200** |
| `https://web.fsktm.um.edu.my/~cschan/downloads_MKLeaf_dataset.html` | ❌ **000** (conexão recusada, 3 tentativas) |

---

## 4. Candidatos avaliados

### 4.1 Flavia Leaf Dataset

| | |
|---|---|
| **Fonte oficial** | http://flavia.sourceforge.net/ |
| **Projeto** | https://sourceforge.net/projects/flavia/ |
| **Download** | `https://sourceforge.net/projects/flavia/files/Leaf%20Image%20Dataset/1.0/Leaves.tar.bz2/download` |
| **Subconjunto pequeno** | `https://sourceforge.net/projects/flavia/files/Standard%20Leaf%20Images/0.1/standardleaves.tar.bz2/download` |
| **Mantenedor** | Projeto Flavia, hospedado no SourceForge |
| **Origem do material** | Campus da Universidade de Nanjing e Arboreto Sun Yat-Sen, China; plantas comuns do Delta do Yangtzé |
| **Imagens** | **1.907** |
| **Espécies** | **32** (50 a 77 imagens por espécie) |
| **Formato** | JPEG |
| **Resolução** | **1600 × 1200** — confirmada por inspeção direta dos arquivos |
| **Fundo** | **Branco, uniforme** — confirmado visualmente |
| **Pecíolo** | Removido na maioria dos casos: as imagens contêm o limbo |
| **Tamanho** | 965,7 MB (`Content-Length: 965715159`, verificado) |
| **Cadastro** | Não exigido |
| **Ground truth** | ❌ Não há máscaras nem contornos anotados |
| **Licença** | Projeto declarado no SourceForge como **"GNU General Public License version 2.0 (GPLv2)"** |
| **Artigo** | Stephen Gang Wu et al., *A Leaf Recognition Algorithm for Plant Classification Using Probabilistic Neural Network*, IEEE 7th International Symposium on Signal Processing and Information Technology (ISSPIT), dezembro de 2007 |

> **Ressalva sobre a licença.** O campo GPLv2 no SourceForge descreve **o projeto** (que
> inclui o software de reconhecimento). Não localizei uma declaração de licença específica e
> separada para o conjunto de imagens. O uso aqui é estritamente acadêmico, sem
> redistribuição — o que se mantém dentro de qualquer leitura razoável dos termos.

### 4.2 Swedish Leaf Dataset

| | |
|---|---|
| **Fonte oficial** | https://www.cvl.isy.liu.se/research/datasets/swedish-leaf/ |
| **Mantenedor** | Computer Vision Laboratory, Linköping University |
| **Imagens** | **1.125** (75 por espécie) |
| **Espécies** | **15** árvores suecas |
| **Formato** | **TIFF** |
| **Fundo** | Uniforme (imagens digitalizadas em scanner) |
| **Tamanho** | **~4,1 GB** — 15 arquivos, de 71 MB a 659 MB cada |
| **Acesso** | Download por classe (`leaf1.zip` … `leaf15.zip`) |
| **Ground truth** | ❌ Não documentado |
| **Licença** | ⚠️ **"Licença explícita não localizada na fonte consultada."** Há apenas requisito de citação |
| **Artigo** | Oskar J. O. Söderkvist, *Computer vision classification of leaves from Swedish trees*, Dissertação de Mestrado, Linköping University, 2001 |

### 4.3 Leafsnap

| | |
|---|---|
| **Fonte oficial** | https://leafsnap.com/dataset/ |
| **Imagens** | 23.147 de laboratório + 7.719 de campo = **30.866** |
| **Espécies** | **185** (nordeste dos EUA) |
| **Origem** | Laboratório: folhas prensadas da coleção Smithsonian, iluminação controlada. Campo: fotos de celular em ambiente externo |
| **Ground truth** | ✅ **Sim** — segmentações geradas automaticamente acompanham as imagens |
| **Download** | `https://leafsnap.com/static/dataset/leafsnap-dataset.tar` — 977 MB, versão 1.0, atualizado em 11/07/2014 |
| **Status do download** | ❌ **404 Not Found** — verificado duas vezes, com e sem redirecionamento |
| **Licença** | "Licença explícita não localizada na fonte consultada." Liberado "para promover pesquisa", com exigência de citação |
| **Artigo** | Kumar et al., *Leafsnap: A Computer Vision System for Automatic Plant Species Identification*, ECCV 2012 |

> **Achado da verificação.** A página do dataset carrega normalmente (HTTP 200) e descreve o
> arquivo, mas **o arquivo em si não está no endereço publicado**. Sem o link oficial
> funcionando, usar o Leafsnap exigiria recorrer a espelhos de terceiros — o que
> comprometeria justamente a rastreabilidade que o projeto exige.

### 4.4 PlantVillage

| | |
|---|---|
| **Fonte oficial** | https://github.com/spMohanty/PlantVillage-Dataset |
| **Imagens** | **54.306** |
| **Classes** | 38 (14 culturas × condições sadia/doente, 26 doenças) |
| **Variantes** | Colorida, escala de cinza e **segmentada** |
| **Resolução** | 256 × 256 px |
| **Fundo** | Uniforme |
| **Finalidade** | **Diagnóstico de doenças em folhas de cultivo** |
| **Licença** | ⚠️ Não declarada no README do repositório oficial. Fontes de terceiros mencionam CC0 1.0, **o que não foi possível confirmar na fonte primária** |
| **Artigo** | Mohanty, Hughes & Salathé, *Using deep learning for image-based plant disease detection*, Frontiers in Plant Science, v. 7, 2016. DOI: 10.3389/fpls.2016.01419 |

### 4.5 MalayaKew (MK) Leaf Dataset

| | |
|---|---|
| **Fonte oficial** | `https://web.fsktm.um.edu.my/~cschan/downloads_MKLeaf_dataset.html` |
| **Status** | ❌ **Conexão recusada — 3 tentativas independentes**, em momentos distintos (`ECONNREFUSED 103.18.2.145:443`, depois `status=000`) |
| **Fonte alternativa** | `http://cs-chan.com/dataset.html` — **certificado TLS expirado** |
| **Origem** | Royal Botanic Gardens, Kew, Inglaterra |
| **Espécies** | 44 |
| **Estrutura** | D1 (folhas inteiras, primeiro plano extraído em HSV) e D2 (recortes 256×256) |
| **Licença** | ❌ **Não verificável** — a fonte não pôde ser aberta |
| **Artigo** | Lee, Chan et al., *Deep-Plant: Plant Identification with Convolutional Neural Networks*, 2015 |

> **Conclusão da verificação.** Nenhuma das duas fontes oficiais respondeu. Um dataset cuja
> origem não pode ser aberta não atende ao critério de rastreabilidade, e **não entra na
> comparação final**.

---

## 5. Análise visual

### Metodologia — e por que ela é real e não descritiva

Para não concluir adequação apenas por descrição textual, **baixei o subconjunto pequeno do
Flavia** — `standardleaves.tar.bz2`, **17,2 MB**, uma imagem representativa por espécie — e
inspecionei as imagens diretamente.

| | |
|---|---|
| Arquivo | `standardleaves.tar.bz2` (17.237.308 bytes) |
| Conteúdo | **32 arquivos JPEG**, um por espécie |
| Destino | Diretório temporário **fora do repositório** |
| Versionado? | ❌ **Nada foi copiado para o projeto** |
| Resolução conferida | **32/32 em 1600 × 1200** |

### Condições observadas

| Aspecto | Observação direta |
|---|---|
| **Fundo** | Branco, uniforme, com separação folha/fundo muito alta. **A premissa central do projeto se confirma** |
| **Uma folha por imagem** | ✅ Em todas as amostras inspecionadas |
| **Folha inteira** | ✅ Na maioria. **Um caso observado com a folha tocando a borda** |
| **Orientação** | **Variada** — folhas em diagonal, sem alinhamento padronizado. Excelente para testar invariância a rotação |
| **Escala** | **Muito variada** — de folhas ocupando quase todo o quadro a acículas finíssimas |
| **Pecíolo** | Ausente na maioria; presente e curto em algumas |
| **Iluminação** | Uniforme, com **sombra suave** sob a folha em alguns casos |
| **Reflexo** | **Presente** em folhas de superfície brilhante — reflexo especular visível |
| **Ruído** | **Pequenos artefatos bege/amarelados** no fundo, próximos à folha, em algumas imagens — resíduos do processo de captura |
| **Objetos extras** | Pontos escuros isolados no fundo, de poucos pixels |
| **Compressão** | JPEG, sem artefatos visíveis relevantes |

### Três casos que resumem o dataset

| Caso | Arquivo | O que representa |
|---|---|---|
| 🟢 **Fácil** | `1.jpg` | Folha lanceolada em diagonal, fundo branco limpo, contraste altíssimo. Pequenos artefatos bege próximos à borda — que a **abertura morfológica** deve remover |
| 🟠 **Médio/difícil** | `16.jpg` | Folha grande e brilhante, com **reflexo especular**, **sombra suave** no fundo e **tocando a borda superior direita**. Aciona os avisos `A001` e `A008` previstos na Fase 1 |
| 🔴 **Extremo** | `18.jpg` | **Acícula de conífera**: extremamente fina e alongada. Área minúscula, aspect ratio altíssimo, poucos pixels de largura. É o pior caso para o perímetro digital (risco R14) |

### O que a inspeção mudou no planejamento

Três consequências concretas, que **não viriam de uma leitura da descrição do dataset**:

1. **A abertura morfológica não é opcional.** Os artefatos bege no fundo serão capturados
   pela limiarização e precisam ser removidos antes da seleção de contorno.
2. **Os avisos `A001` e `A008` têm caso real no dataset** — não são hipóteses. O critério de
   "toca a borda" será exercitado de verdade.
3. **O caso da acícula é o teste mais duro do risco R14.** Um objeto com poucos pixels de
   largura tem razão perímetro/área péssima, e a circularidade medida será muito distante do
   valor geométrico. É a imagem que deve constar da documentação de limitações.

---

## 6. Matriz comparativa

Escala descritiva: **Excelente · Boa · Média · Ruim · Inadequada**. Não foi criado score
numérico — uma soma de pesos arbitrários daria aparência de objetividade a um julgamento que
é qualitativo.

| Critério | **Flavia** | **Swedish Leaf** | **Leafsnap** | **PlantVillage** | **MalayaKew** |
|---|---|---|---|---|---|
| **Fonte** | SourceForge | CVL / Linköping | leafsnap.com | GitHub oficial | Univ. Malaya |
| **URL ativa** | ✅ 200 | ✅ 200 | ⚠️ página 200 | ✅ 200 | ❌ **000** |
| **Download ativo** | ✅ **200, 965,7 MB** | ✅ por classe | ❌ **404** | ✅ | ❌ |
| **Imagens** | 1.907 | 1.125 | 30.866 | 54.306 | ~2.800 (D1) |
| **Classes** | 32 espécies | 15 espécies | 185 espécies | 38 (doenças) | 44 espécies |
| **Fundo** | **Excelente** (branco) | **Excelente** (scanner) | Boa (lab) / Ruim (campo) | Boa | Boa |
| **Uma folha por imagem** | **Excelente** | **Excelente** | Boa (lab) | **Excelente** | **Excelente** |
| **Folha inteira** | **Boa** | **Excelente** | Boa | Média (recortada) | Boa |
| **Iluminação** | Boa | **Excelente** | Média | Boa | Boa |
| **Variação de forma/escala** | **Excelente** | Boa | **Excelente** | Ruim | Boa |
| **Licença** | **GPLv2** (projeto) | ⚠️ não localizada | ⚠️ não localizada | ⚠️ não confirmada | ❌ não verificável |
| **Acesso** | Direto, sem cadastro | Direto | **Quebrado** | Direto | **Indisponível** |
| **Tamanho** | 965,7 MB | **~4,1 GB** | 977 MB | ~2 GB | — |
| **Formato** | JPEG | **TIFF** | JPEG | JPEG 256px | JPEG |
| **Ground truth** | ❌ | ❌ | ✅ **sim** | ✅ variante segmentada | ✅ D1 |
| **Facilidade de segmentação clássica** | **Excelente** | **Excelente** | Média | Boa | Boa |
| **Adequação ao projeto** | **Excelente** | **Boa** | **Ruim** | **Inadequada** | **Inadequada** |
| **Limitação principal** | Sem ground truth; condições de laboratório | 4,1 GB em TIFF; licença não localizada | **Download quebrado** | Focado em doença, 256px, sem variação de forma | **Fonte inacessível** |

---

## 7. Dataset escolhido

> # 🌿 Dataset selecionado: **Flavia Leaf Dataset**
>
> **Fonte oficial:** http://flavia.sourceforge.net/
> **Download:** `https://sourceforge.net/projects/flavia/files/Leaf%20Image%20Dataset/1.0/Leaves.tar.bz2/download`
> **Verificado em:** 19 de setembro de 2026 — HTTP 200, 965.715.159 bytes

### Justificativa, ponto a ponto

| Requisito | Como o Flavia atende |
|---|---|
| **Compatível com segmentação clássica** | Fundo branco uniforme e folha verde produzem a maior separabilidade possível em intensidade e em matiz. **Confirmado por inspeção visual direta**, não por descrição |
| **Adequado à análise morfológica** | Uma folha inteira por imagem, limbo isolado, sem sobreposição. É exatamente a entrada "ideal" definida na Fase 1 §4 |
| **Fonte rastreável** | Site oficial ativo, projeto no SourceForge com licença declarada, artigo publicado em conferência IEEE |
| **Volume suficiente** | 1.907 imagens — muito além do necessário para distribuições e avaliação, sem ser inviável de manusear |
| **Diversidade suficiente** | 32 espécies com formas genuinamente distintas: lanceoladas, ovais, aciculares, lobadas. **Variação de escala e orientação confirmada visualmente** |
| **Condições adequadas ao escopo** | Resolução uniforme (1600×1200), JPEG, sem cadastro, download direto e verificado |

### Um argumento adicional, de método

O Flavia foi o **único candidato cujo conteúdo pôde ser inspecionado nesta fase**, graças ao
subconjunto de 17,2 MB. Os outros teriam exigido baixar entre 1 e 4 GB — ou nem isso
resolveria, nos dois casos com fonte quebrada. Poder verificar a premissa central do projeto
(*"o fundo permite segmentação sem IA"*) **olhando as imagens** é, por si só, uma vantagem
prática sobre confiar na descrição.

### Por que cada um dos demais foi descartado

| Dataset | Motivo do descarte |
|---|---|
| **Swedish Leaf** | **Não é inadequado — é pior nesta aplicação.** 4,1 GB em TIFF por 1.125 imagens é um custo desproporcional; a licença não foi localizada; e as 15 espécies oferecem menos variação de forma que as 32 do Flavia. É o **segundo colocado legítimo** |
| **Leafsnap** | **Download oficial retorna 404**, verificado duas vezes. Tem o atrativo real de possuir ground truth, mas usar espelho de terceiro destruiria a rastreabilidade exigida pela entrega |
| **PlantVillage** | **Finalidade incompatível.** É um dataset de diagnóstico de doença, com recortes de 256×256 que frequentemente não contêm a folha inteira e com variação de forma baixa. As 54 mil imagens são irrelevantes — o volume aqui não é critério. A licença não pôde ser confirmada na fonte primária |
| **MalayaKew** | **Fonte inacessível.** Conexão recusada em 3 tentativas na página oficial, certificado expirado na alternativa. Sem fonte verificável, não há como documentar origem nem licença |

### Limitações que permanecem

Declaradas agora, para constarem também dos slides e da documentação final:

| # | Limitação | Consequência |
|---|---|---|
| 1 | **Sem ground truth** | A qualidade da segmentação não pode ser medida por IoU ou Dice. Exige protocolo de inspeção manual (§12) |
| 2 | **Condições de laboratório** | Fundo branco controlado **não representa** uma foto de celular sobre grama ou mesa de madeira |
| 3 | **Viés geográfico** | Plantas do Delta do Yangtzé, China. Não representa a flora brasileira |
| 4 | **Pecíolo removido** | A literatura difere quanto a incluí-lo; perímetro e solidez mudam conforme a escolha |
| 5 | **Uma única fonte de captura** | Mesma câmera, mesmo enquadramento, mesma iluminação — o pipeline pode se adaptar a essas condições sem que se perceba |
| 6 | **Sem casos de falha naturais** | Quase não há imagens ruins; testar robustez exigirá degradação sintética ou material próprio |

### Em que cenários este dataset **não** representa o mundo real

O ponto mais importante desta seção, e que precisa ser dito na apresentação:

> Um pipeline que funcione perfeitamente no Flavia **não demonstra** que funcionará numa foto
> feita pelo usuário. O Flavia é o **melhor caso**: fundo branco, folha isolada, luz
> uniforme, câmera fixa. Ele valida a **correção dos algoritmos**, não a robustez em campo.

Cenários não cobertos: fundo texturizado ou verde · luz natural com sombra dura · folha ainda
presa à planta · várias folhas sobrepostas · perspectiva e curvatura · desfoque de movimento ·
folha seca, avermelhada ou variegada.

---

## 8. Dataset secundário

**Decisão: não adotar um segundo dataset público.**

A pergunta correta não é "seria interessante ter mais dados?", e sim "o que exatamente o
Flavia não testa, e qual conjunto testaria isso?". A resposta é: **condições reais de
captura** — e nenhum candidato verificado oferece isso de forma acessível.

| Candidato a secundário | Por que não resolve |
|---|---|
| Leafsnap (imagens de campo) | Seria a escolha natural — imagens de celular em ambiente externo. **Mas o download está 404** |
| PlantVillage | Também é laboratório; não acrescenta condição nova |
| Swedish Leaf | Também é fundo uniforme; acrescenta 4,1 GB e nenhuma condição nova |

### Proposta alternativa, mais adequada e de custo baixo

**Um conjunto próprio pequeno, fotografado pelos integrantes**, apenas para teste de
robustez — não para desenvolvimento nem para a avaliação principal.

| | |
|---|---|
| **Volume sugerido** | 10 a 15 imagens |
| **Composição** | Folhas sobre papel branco (caso controlado) · sobre mesa de madeira (fundo texturizado) · sobre grama (**fundo verde — pior caso**) · com sombra dura · folha cortada pelo enquadramento · duas folhas na mesma foto |
| **Licença** | **Totalmente sob controle da equipe** — sem qualquer incerteza |
| **Versionamento** | Podem ir para `exemplos/`, por serem poucas e de autoria própria |
| **Valor** | Testa exatamente o caso de uso real: o usuário enviando uma foto pela página |

Isso entrega o benefício de um dataset secundário — testar generalização — **sem baixar
gigabytes e sem herdar incerteza de licença**. Fica como proposta para a Fase 10.

---

## 9. Política de download

| Regra | |
|---|---|
| Download completo (965,7 MB) | **Ainda não realizado.** Ocorrerá na Fase 3, após sua revisão |
| Baixado nesta fase | Apenas `standardleaves.tar.bz2` (17,2 MB, 32 imagens), em diretório temporário fora do repositório |
| Destino local do dataset | `processamento-imagens/dataset/dados/` |
| Reconstrução | Por download da URL oficial, documentado em `dataset/README.md` |

---

## 10. Política de Git — confirmada

> **O dataset completo NÃO será versionado.** A regra vale mesmo com licença permissiva:
> o repositório já carrega 120 MB em `images/`, e acrescentar 965 MB seria irresponsável.

| Item | Versionado? |
|---|:---:|
| `docs/processamento-imagens/02-DATASET.md` | ✅ |
| `processamento-imagens/dataset/README.md` | ✅ |
| `processamento-imagens/dataset/manifesto.csv` | ✅ |
| Script de seleção do subconjunto | ✅ (Fase 3) |
| Poucas imagens próprias em `exemplos/` | ✅ |
| Resultados escolhidos como evidência | ✅ |
| **As 1.907 imagens do Flavia** | ❌ **Nunca** |
| `Leaves.tar.bz2` | ❌ |

### Verificação do `.gitignore`

A regra existente cobre a estrutura escolhida:

```
processamento-imagens/dataset/*
!processamento-imagens/dataset/README.md
!processamento-imagens/dataset/manifesto.csv
!processamento-imagens/dataset/amostras.txt
!processamento-imagens/dataset/.gitkeep
```

`dataset/*` ignora todo o conteúdo, **incluindo o subdiretório `dados/`**, e as quatro
exceções liberam exatamente os arquivos de rastreabilidade. `*.tar.bz2` é coberto por
`*.tar`? **Não** — e por isso foi verificado separadamente (§16).

---

## 11. Estrutura e manifesto

### Estrutura local

```
processamento-imagens/dataset/
├── README.md          ✅ versionado — origem, link, como obter
├── manifesto.csv      ✅ versionado — quais imagens foram usadas
└── dados/             ❌ ignorado pelo Git
    └── Leaves/        1.907 JPEG, obtidos por download
```

### Formato do manifesto

```csv
arquivo,dataset_origem,classe_original,uso,subconjunto,observacao
```

| Campo | Conteúdo |
|---|---|
| `arquivo` | Nome do arquivo no dataset original (ex.: `1001.jpg`) |
| `dataset_origem` | `flavia` ou `proprio` |
| `classe_original` | Identificador da espécie conforme o dataset |
| `uso` | `desenvolvimento` · `avaliacao` · `robustez` · `demonstracao` |
| `subconjunto` | Rótulo do lote de seleção (ex.: `dev-v1`, `aval-v1`) |
| `observacao` | Campo livre — ex.: "folha toca a borda", "acícula" |

> **Nenhuma linha foi criada.** O manifesto será gerado pelo script de seleção da Fase 3, a
> partir do dataset real. Inventar linhas agora produziria um arquivo que não corresponde a
> nada.

**O manifesto é o que torna a avaliação reproduzível sem redistribuir imagem alguma:** quem
baixar o dataset pela URL oficial pode reexecutar exatamente sobre as mesmas imagens.

---

## 12. Estratégia de subconjunto

### O problema a evitar

Selecionar manualmente as imagens "que funcionam" produziria uma avaliação que mede a
habilidade de escolher imagens, não a qualidade do pipeline. **Cherry-picking é o modo mais
fácil de produzir um resultado bonito e inútil.**

### Método proposto — reproduzível

| Parâmetro | Valor |
|---|---|
| **Método** | Amostragem aleatória **estratificada por espécie** |
| **Semente** | **Fixa: `20260919`**, registrada no script e no manifesto |
| **Estratificação** | Todas as **32 espécies** representadas em ambos os conjuntos |
| **Implementação** | Script versionado, executável por qualquer pessoa |
| **Saída** | `manifesto.csv`, versionado |

### Tamanhos propostos

| Conjunto | Por espécie | Total | Finalidade |
|---|---:|---:|---|
| **Desenvolvimento** | 2 | **64** | Ajustar segmentação, filtros, operações morfológicas, limiares |
| **Avaliação** | 3 | **96** | Medir o resultado final — **tocado uma única vez** |
| | | **160** | Disjuntos por construção |

**Justificativa dos números:** 96 imagens é um conjunto que uma pessoa consegue inspecionar
visualmente uma a uma em tempo razoável — requisito incontornável, já que não há ground truth
(§13). E 2 por espécie no desenvolvimento cobre as 32 formas sem oferecer material suficiente
para superajuste confortável.

Os números podem ser ajustados na Fase 3; **a semente e a estratificação não**.

---

## 13. Desenvolvimento × avaliação, e o overfitting manual

### O risco, nomeado

> **Mesmo sem aprendizado de máquina, existe superajuste.**
>
> Ajustar repetidamente limiares, tamanhos de kernel e parâmetros de filtro **olhando sempre
> para as mesmas imagens** produz um pipeline adaptado àquelas imagens. Não há gradiente nem
> pesos — mas há um otimizador: **a pessoa que ajusta**. O resultado é o mesmo: desempenho
> excelente no conjunto visto e desconhecido fora dele.

Este projeto já tem um precedente documentado do mesmo gênero: na Fase 5 da etapa de IA, uma
regra de prompt foi avaliada num tópico onde o defeito-alvo tinha taxa-base zero, e a
conclusão foi tirada de um experimento que não podia produzi-la. **O erro não foi de código;
foi de desenho experimental.**

### Regra metodológica adotada

```
                 conjunto de desenvolvimento  ≠  conjunto de avaliação
                          (64 imagens)              (96 imagens)
                                │                        │
                    olhado quantas vezes         tocado UMA vez,
                        for preciso              no fim da Fase 10
```

| Regra | |
|---|---|
| 1 | Todo ajuste de parâmetro é feito **exclusivamente** sobre o conjunto de desenvolvimento |
| 2 | O conjunto de avaliação é executado **uma única vez**, ao final |
| 3 | Se o resultado da avaliação for ruim e algo for ajustado, **um novo conjunto de avaliação deve ser sorteado** — e isso precisa ser registrado |
| 4 | Os dois conjuntos são **disjuntos por construção**, garantido pelo script |
| 5 | A regra 3 vale mesmo quando for tentador ignorá-la |

A regra 3 é a que realmente protege. Reavaliar no mesmo conjunto após um ajuste transforma o
conjunto de avaliação em conjunto de desenvolvimento — silenciosamente.

---

## 14. Ground truth

### Disponibilidade nos candidatos

| Dataset | Ground truth | Situação |
|---|---|---|
| **Flavia** (escolhido) | ❌ Nenhum | — |
| Leafsnap | ✅ Segmentações automáticas | Download 404 |
| PlantVillage | ✅ Variante segmentada | Dataset inadequado por outros motivos |
| MalayaKew | ✅ D1 com primeiro plano extraído | Fonte inacessível |
| Swedish Leaf | ❌ Não documentado | — |

### Decisão, e o raciocínio

O Leafsnap tem ground truth e isso é uma vantagem real — permitiria IoU e Dice, métricas
objetivas. Mas:

1. **o download oficial está quebrado**, e a rastreabilidade é requisito da entrega;
2. suas segmentações são **geradas automaticamente**, não anotadas por humano — seriam
   referência aproximada, não verdade;
3. e, sobretudo: **não se troca o objetivo do projeto para poder usar uma métrica.**

> Escolher um dataset pior para a análise morfológica só porque ele permite calcular IoU
> seria deixar a métrica determinar o problema. A decisão correta é manter o dataset adequado
> e **definir um protocolo de avaliação honesto para a ausência de ground truth**.

---

## 15. Métricas de segmentação sem ground truth

### Protocolo de inspeção manual

Sem máscaras de referência, a avaliação é **humana, mas protocolada** — com critério definido
**antes** de olhar os resultados, para que a classificação não se acomode ao que se vê.

| Categoria | Critério |
|---|---|
| 🟢 **Correta** | A máscara cobre a folha inteira; a borda acompanha o contorno real; sem buracos internos relevantes; sem inclusão de fundo, sombra ou artefato |
| 🟡 **Aceitável** | A folha está essencialmente correta, com desvios pequenos e localizados: borda levemente erodida ou dilatada, pequeno artefato incluído, pequena falha interna. **As medidas continuam utilizáveis, com ressalva** |
| 🔴 **Falha** | Objeto errado selecionado · parte significativa da folha perdida · sombra ou fundo incorporados · máscara fragmentada · nenhum objeto detectado |

### O que será reportado

| Item |
|---|
| Proporção em cada categoria, sobre as 96 imagens de avaliação |
| **Causas das falhas, agrupadas e contadas** |
| Tempo médio de processamento por imagem |
| Distribuição de cada característica (média, mediana, desvio, mínimo, máximo) |
| As imagens que falharam, **mostradas** — não apenas contadas |

### Medidas auxiliares, automáticas

Sem substituir a inspeção, alguns indicadores podem ser calculados e usados como triagem:

| Indicador | O que sugere |
|---|---|
| Fração da imagem ocupada pelo objeto | Valor extremo sugere falha |
| Nº de componentes conectados após morfologia | Muitos sugerem máscara fragmentada |
| Objeto toca a borda | Provável corte |
| Solidez muito baixa | Possível inclusão de artefato distante |

> **Nenhuma meta percentual é declarada.** A proporção obtida será medida e reportada, seja
> qual for. Anunciar um alvo antes do primeiro experimento inverteria a ordem entre hipótese
> e resultado.

---

## 16. Verificação do `.gitignore`

A regra `*.tar` **não** cobre `.tar.bz2` — verificado. Mas as demais regras já protegem o
caso concreto:

| Caminho | Ignorado? | Por qual regra |
|---|:---:|---|
| `processamento-imagens/dataset/dados/` | ✅ | `processamento-imagens/dataset/*` |
| `processamento-imagens/dataset/Leaves.tar.bz2` | ✅ | `processamento-imagens/dataset/*` |
| `processamento-imagens/dataset/README.md` | ❌ (versionado) | exceção `!` |
| `processamento-imagens/dataset/manifesto.csv` | ❌ (versionado) | exceção `!` |
| `Leaves.tar.bz2` na raiz do projeto | ⚠️ **não coberto** | — |

**Conclusão:** como o download será feito dentro de `dataset/`, a proteção é suficiente.
Nenhuma alteração ao `.gitignore` foi necessária nesta fase. Caso, na Fase 3, o arquivo
compactado chegue a existir fora de `dataset/`, acrescenta-se `*.bz2` — mas antecipar isso
seria acrescentar regra sem caso de uso.

---

## 17. Plano para a próxima fase

**Fase 3 — Pré-processamento**, após sua revisão:

| # | Ação |
|---|---|
| 1 | Criar `.venv` e instalar apenas `opencv-python`, `numpy` e `pytest` |
| 2 | Baixar o Flavia (965,7 MB) para `dataset/dados/`, **fora do Git** |
| 3 | Escrever o script de seleção estratificada com semente `20260919` |
| 4 | Gerar `manifesto.csv` com os conjuntos de 64 e 96 imagens |
| 5 | Implementar `utils.py` (validação e E/S) e `preprocessing.py` |
| 6 | Comparar redimensionamento, espaços de cor e filtros **no conjunto de desenvolvimento** |
| 7 | Definir, com medição, a resolução mínima e o lado de redimensionamento — pendências da Fase 1 |
| 8 | Documentar em `03-PRE-PROCESSAMENTO.md` |
| 9 | Rodar as 256 asserções de regressão |

---

## 18. Pendências e incertezas reais

| # | Pendência | Natureza |
|---|---|---|
| 1 | **Licença do Flavia** | O SourceForge declara GPLv2 **para o projeto**. Não localizei declaração separada para o conjunto de imagens. Uso acadêmico sem redistribuição permanece seguro, mas a incerteza está registrada |
| 2 | **R12 — hífen no nome do diretório** | Continua aberto desde a Fase 1. Bloqueia a Fase 8, não a Fase 3 |
| 3 | **Conjunto próprio de robustez** | Proposto na §8, depende de decisão e de alguém fotografar as folhas |
| 4 | **Tamanhos de 64 e 96** | Propostos com justificativa; ajustáveis na Fase 3 |
| 5 | **Leafsnap poderia voltar** | O 404 pode ser temporário. Se a fonte voltar, o ground truth passa a ser uma opção — mas não se deve esperar por isso |

---

*Fase 2 concluída em 19 de setembro de 2026, sobre o commit `04c6567`. Todas as URLs citadas
foram abertas e verificadas nessa data.*
