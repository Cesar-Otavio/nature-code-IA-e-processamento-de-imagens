# Fase 10 — Avaliação final congelada nas 96 imagens reservadas

> **Avaliar, não recalibrar.** Esta fase executa o pipeline congelado uma única vez sobre
> o conjunto de avaliação e registra o que aconteceu. Nenhum parâmetro, limiar, regra ou
> fórmula foi alterado — antes, durante ou depois — e os hashes dos arquivos do algoritmo
> provam isso.
>
> **Esta é uma avaliação operacional**, não uma avaliação de acerto: não existe ground
> truth para as categorias geométricas, e o pipeline não identifica espécies. A inspeção
> visual humana dos **12 casos selecionados** (§17) foi **concluída depois da execução**:
> 12/12 revisados, todos considerados visualmente utilizáveis, sem necessidade de correção
> do pipeline. As outras 84 imagens não foram inspecionadas individualmente.

---

## 1. Objetivo

Medir o comportamento técnico do pipeline congelado sobre imagens que ele nunca viu:

- quantas imagens ele processa até o fim, e com que avisos;
- como se distribuem as características e as descrições geométricas;
- quantas descrições caem perto de um limiar;
- quanto tempo leva;
- se o resultado é determinístico.

E, igualmente importante, **descobrir onde as escolhas feitas no desenvolvimento não se
sustentam** — sem corrigi-las.

---

## 2. Princípio de congelamento

A regra vem da Fase 2 (§13):

1. o conjunto de avaliação é executado **uma única vez**, ao final;
2. se algo for ajustado depois de olhar o resultado, **um novo conjunto de avaliação precisa
   ser sorteado** — e isso precisa ser registrado.

A regra 2 é a que protege. Reavaliar no mesmo conjunto depois de ajustar transformaria o
conjunto de avaliação em conjunto de desenvolvimento, silenciosamente.

**Por isso, nada do que está neste documento motivou mudança alguma.** As observações da
§12 e da §13 sobre limiares são registros para trabalho futuro, com conjunto novo.

---

## 3. Commit e tag avaliados

| Item | Valor |
|---|---|
| Branch | `main` |
| Commit | `4b669811006f8fd5b46e515f054c7611b2f2031f` |
| Tag | `fase-9-completa` (aponta para o mesmo commit) |
| Versão do pipeline | `1.0.0` |
| Execução | 21/09/2026, 11:37:58 → 11:38:27 (−03:00) |
| Python | 3.14.3 · OpenCV 5.0.0.93 · NumPy 2.5.3 |

### Estado antes da avaliação

| Suíte | Resultado |
|---|---|
| PDI | **748 passed** — os 746 da Fase 9 + 2 parametrizações de `test_isolamento` que passaram a cobrir o script de avaliação, criado antes para registrar os hashes |
| Legado (camada de IA, integração, diagnóstico, benchmark) | 67 + 46 + 82 + 61 = **256/256** |

### Hashes do algoritmo

SHA-256 de 9 arquivos (`preprocessing`, `segmentation`, `morphology`, `contours`,
`features`, `classification`, `pipeline`, `utils` e `visualizacao`) registrados **antes**
de abrir qualquer imagem de avaliação, e de novo depois. Conferidos contra o conteúdo do
commit: idênticos.

Arquivos: [`hashes-pipeline-antes.txt`](dados-avaliacao/hashes-pipeline-antes.txt),
[`hashes-pipeline-depois.txt`](dados-avaliacao/hashes-pipeline-depois.txt),
[`hashes-pipeline-comparacao.txt`](dados-avaliacao/hashes-pipeline-comparacao.txt) —
**9 de 9 idênticos**.

---

## 4. Conjunto de dados

| Item | Valor |
|---|---|
| Fonte de verdade | `processamento-imagens/dataset/manifesto.csv` (inalterado desde a Fase 4) |
| Entradas no manifesto | 160 |
| Avaliação (`uso = avaliacao`, `aval-v1`) | **96** |
| Desenvolvimento (`dev-v1`) | 64 — **fora** da avaliação |
| Espécies | **32**, com **3 imagens cada** |
| Seleção | aleatória estratificada por espécie, semente `20260919` (Fase 2 §12) |

Validações executadas **antes** de processar, sem abrir imagem alguma:

| Verificação | Resultado |
|---|:---:|
| Total exatamente 96 | ✅ |
| 32 espécies | ✅ |
| 3 imagens por espécie | ✅ |
| Nenhuma imagem de desenvolvimento | ✅ |
| Nenhuma duplicata | ✅ |
| Todos os arquivos existem | ✅ |
| Nenhum caminho em `amostra-flavia` | ✅ |

---

## 5. Protocolo

```
verificar Git (árvore limpa, HEAD = tag)
  → hashes ANTES
  → testes (748 + 256)
  → validar a seleção pelo manifesto
  → testes da infraestrutura de avaliação com imagens SINTÉTICAS
  → execução única: 96 × processar_folha(caminho, salvar_imagens=False)
  → determinismo: 5 imagens reprocessadas
  → seleção automática de casos para inspeção
  → PNGs desses casos (pasta ignorada) + conferência de que os números não mudam
  → hashes DEPOIS e comparação
  → testes de novo
```

### O script é uma casca

[`processamento-imagens/avaliar_conjunto_final.py`](../../processamento-imagens/avaliar_conjunto_final.py)
lê o manifesto, chama `pipeline.processar_folha()` e agrega. Garantido por teste:

| Garantia | Teste |
|---|---|
| Não importa OpenCV nem NumPy | `test_script_nao_importa_opencv_nem_numpy` |
| O único módulo interno importado é `src.pipeline` | `test_script_usa_somente_o_pipeline_central` |
| Nenhum nome de parâmetro ou etapa (`FAIXA_VERDE`, `KERNEL`, `LIMIARES`, `segmentar_hsv`, `minAreaRect`, …) | `test_script_nao_duplica_parametros_nem_etapas` |
| Nenhuma atribuição a constante do pipeline, nenhum `setattr` | `test_script_nao_altera_constantes_do_pipeline` |
| O pipeline recebe **só o caminho** — a espécie nunca entra | `test_pipeline_recebe_so_o_caminho` |

As estatísticas usam `statistics` da biblioteca padrão; o percentil é interpolação linear,
conferida por teste contra `numpy.percentile`.

### Os testes vieram antes da execução

Como a execução é única, a infraestrutura foi testada **antes**, ponta a ponta, com um
manifesto de imagens sintéticas (4 folhas, 1 sem folha, 1 corrompida). Esses testes
encontraram um defeito do script — caminhos padrão fixados na definição das funções,
imunes à troca da pasta —, corrigido antes de tocar nas 96.

---

## 6. Proteção contra recalibração

| Camada | Mecanismo |
|---|---|
| Algoritmo | 9 hashes SHA-256 antes e depois — **idênticos** |
| Git | O script recusa rodar se algum arquivo congelado diferir do commit (`git diff HEAD`) |
| Código | O script não conhece parâmetro algum (teste estrutural) |
| Execução | Uma única passada; o determinismo reprocessa 5 imagens **sem** mudar nada |
| Visualização | Os PNGs de inspeção foram gerados à parte, e os números conferidos contra a execução principal: **nenhuma divergência** |
| Seleção | Nenhuma imagem removida, nenhuma reprocessada com outro parâmetro, nenhuma máscara editada |

---

## 7. Métricas coletadas

Uma linha por imagem em [`fase10-resultados.csv`](dados-avaliacao/fase10-resultados.csv)
(96 linhas, 54 colunas), e o resultado completo do pipeline de cada imagem em
[`fase10-resultados-completos.json`](dados-avaliacao/fase10-resultados-completos.json):

| Grupo | Campos |
|---|---|
| Identificação | índice, arquivo, espécie (id e nome), conjunto |
| Status | status, código e mensagem de erro |
| Objeto | detectado, nº de contornos, dominância, toca borda, distância à borda, fração de foreground |
| Características | áreas de contorno e de máscara, diferença percentual, perímetro, elongação, circularidade, solidez, extent, extent rotacionado, razão perímetro/hull, anisotropia, orientação confiável, proporção verde |
| Classificação | categoria, `limitrofe` e margem relativa dos 5 atributos; nº de atributos limítrofes |
| Performance | tempo do pipeline, tempo de parede, tempo de cada etapa |
| Avisos | todos, e o número de avisos técnicos |

Agregados em [`fase10-resumo.json`](dados-avaliacao/fase10-resumo.json). Nenhum `NaN` ou
`Infinity` (serialização com `allow_nan=False`), nenhum caminho absoluto.

---

## 8. Taxa de processamento

| Item | Valor |
|---|---:|
| Imagens | 96 |
| Processadas | 96 |
| `sucesso` | 0 |
| `sucesso_com_avisos` | **96** |
| `erro` | **0** |
| **Taxa de processamento válido** | **100 %** |
| Válidas **com** aviso técnico | 65 (67,7 %) |
| Válidas **sem** aviso técnico | 31 (32,3 %) |

> **Por que nenhum `sucesso`?** O pipeline anexa a toda descrição o aviso padrão
> *"descrição geométrica automática; não constitui identificação botânica nem taxonômica"*,
> e o status passa a `sucesso_com_avisos` sempre que há algum aviso. É comportamento do
> contrato congelado, **não alterado**. Por isso a contagem de avisos **técnicos** é
> reportada à parte — ela é a informação útil.

> **100 % de processamento válido significa que o pipeline chegou ao fim com um objeto
> detectado em todas as imagens.** Não significa que o objeto detectado seja a folha
> inteira e só ela: isso é o que a inspeção humana vai dizer (§17).

---

## 9. Erros

**Zero erros.** Nenhum `E007` (sem folha), nenhum `E011` (objeto pequeno demais), nenhum
erro de leitura, nenhuma exceção não tratada.

| Código | Quantidade | % |
|---|---:|---:|
| (todos) | 0 | 0,0 |

---

## 10. Avisos

**Aviso padrão de não identificação botânica:** 96 de 96 — esperado, não técnico.

**Avisos técnicos** (uma imagem pode ter mais de um):

| Aviso | Imagens | % |
|---|---:|---:|
| `atributos proximos de um limiar` | 62 | 64,6 |
| `solidez_baixa_borda_muito_recortada` | 9 | 9,4 |
| `concavidade ambigua` | 3 | 3,1 |
| `objeto_muito_alongado` | 3 | 3,1 |
| `orientacao_nao_confiavel` | 1 | 1,0 |
| `objeto_toca_borda` | **0** | 0,0 |
| `multiplos_contornos` / `selecao_ambigua` | **0** | 0,0 |

- **`solidez_baixa_borda_muito_recortada`:** `1269`, `1282`, `1302` (Acer palmatum),
  `1392`, `1416` (Kalopanax septemlobus), `2370`, `2417` (Cedrus deodara), `3283`, `3317`
  (Acer buergerianum).
- **`concavidade ambigua` e `objeto_muito_alongado`:** as três de Cedrus deodara, `2353`,
  `2370` e `2417` — exatamente o caso da acícula que motivou a regra de ambiguidade na
  Fase 8 (R25).
- **`orientacao_nao_confiavel`:** `1302` (Acer palmatum, anisotropia 0,006).

Todas as imagens tiveram **um único contorno** e dominância 1,0. Nenhuma toca a borda; a
mais próxima, `1416`, fica a **2 px** dela.

---

## 11. Estatísticas das características

Sobre as 96 imagens válidas. **Nenhum outlier removido.**

| Característica | mín | P5 | P25 | mediana | média | P75 | P95 | máx | desvio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Área do contorno (px²) | 20.096 | 95.053 | 180.867 | 273.714 | 251.783 | 333.505 | 383.797 | 413.855 | 97.845 |
| Área da máscara (px²) | 21.037 | 95.982 | 182.090 | 274.970 | 252.807 | 334.727 | 385.003 | 414.919 | 97.873 |
| Perímetro (px) | 1.318 | 1.818 | 2.335 | 2.484 | 2.538 | 2.721 | 3.268 | 4.970 | 534 |
| Elongação | 1,008 | 1,020 | 1,461 | 2,192 | 3,309 | 3,163 | 8,534 | 30,622 | 4,504 |
| Circularidade | 0,045 | 0,110 | 0,390 | 0,521 | 0,507 | 0,625 | 0,777 | 0,830 | 0,184 |
| Solidez | 0,463 | 0,631 | 0,925 | 0,968 | 0,917 | 0,983 | 0,994 | 0,995 | 0,120 |
| Extent | 0,037 | 0,193 | 0,401 | 0,574 | 0,525 | 0,660 | 0,727 | 0,811 | 0,173 |
| Extent rotacionado | 0,350 | 0,504 | 0,634 | 0,669 | 0,663 | 0,714 | 0,777 | 0,825 | 0,085 |
| Razão perímetro/hull | 1,051 | 1,056 | 1,063 | 1,083 | 1,143 | 1,138 | 1,377 | 2,070 | 0,179 |
| Anisotropia | 0,006 | 0,084 | 0,435 | 0,634 | 0,582 | 0,799 | 0,972 | 0,999 | 0,280 |
| Fração de foreground | 0,027 | 0,122 | 0,232 | 0,350 | 0,321 | 0,426 | 0,490 | 0,528 | 0,124 |

Observações factuais:

- **Os extremos são as três acículas de Cedrus deodara** (`2353`, `2370`, `2417`): menor
  área, menor fração de foreground, maior elongação (até 30,6), menor circularidade.
- **Diferença entre área de contorno e de máscara:** entre −4,48 % (`2370`) e +0,71 %
  (`2280`). A maior diferença é justamente a acícula mais fina, onde a borda pesa mais.
- **Razão perímetro/hull mínima 1,051**, confirmando a referência convexa de ≈1,05 medida
  na Fase 6 (R14): nenhuma folha fica abaixo do círculo digital.
- **Circularidade máxima 0,830**, abaixo do teto digital de ≈0,90 — como no
  desenvolvimento (máximo 0,814).

### Comparação descritiva com o desenvolvimento

Os quartis do desenvolvimento vêm da Fase 8 (documentados, não recalculados). **As duas
populações não foram misturadas.**

| Estatística | Desenvolvimento (64) | Avaliação (96) |
|---|---:|---:|
| Elongação P25 / P75 / P90 | 1,483 / 3,075 / 6,468 | 1,461 / 3,163 / 5,950 |
| Circularidade P25 / P75 | 0,415 / 0,645 | 0,390 / 0,625 |
| Razão perímetro/hull P75 / P90 | 1,127 / 1,288 | 1,138 / 1,261 |
| Solidez P20 | ≈ 0,92 | 0,896 |

As distribuições são próximas. A avaliação é ligeiramente menos compacta e com solidez um
pouco menor — diferença compatível com amostras de 64 e 96 imagens.

---

## 12. Distribuições das classificações

Nomes das categorias exatamente como o código os produz.

| Alongamento | n | % |
|---|---:|---:|
| `baixa` | 27 | 28,1 |
| `moderada` | 43 | 44,8 |
| `alta` | 16 | 16,7 |
| `extrema` | 10 | 10,4 |
| `indeterminado` | 0 | 0,0 |

| Concavidade | n | % |
|---|---:|---:|
| `baixa` | 73 | 76,0 |
| `moderada` | 13 | 13,5 |
| `alta` | 7 | 7,3 |
| `ambigua` | 3 | 3,1 |
| `indeterminado` | 0 | 0,0 |

| Compacidade | n | % |
|---|---:|---:|
| `baixa` | 25 | 26,0 |
| `moderada` | 50 | 52,1 |
| `alta` | 21 | 21,9 |
| `indeterminado` | 0 | 0,0 |

| Complexidade da borda | n | % |
|---|---:|---:|
| `regular` | 71 | 74,0 |
| `moderada` | 17 | 17,7 |
| `complexa` | 8 | 8,3 |
| `indeterminado` | 0 | 0,0 |

| Orientação | n | % |
|---|---:|---:|
| `bem_definida` | 78 | 81,3 |
| `pouco_definida` | 17 | 17,7 |
| `indefinida` | 1 | 1,0 |
| `indeterminado` | 0 | 0,0 |

**Nenhum atributo ficou `indeterminado`** em nenhuma imagem: todas as métricas vieram
válidas e dentro do domínio.

Não há como dizer se essas proporções estão "certas": são distribuições de descrições
geométricas produzidas por regras fixas, sem referência independente.

### Os "vales" do desenvolvimento não estão vazios na avaliação

Dois limiares da Fase 8 foram colocados em **vales** — faixas onde nenhuma das 64 folhas
de desenvolvimento caía —, com o argumento de que ali o limiar não cortaria nenhuma folha
ao meio. **Na avaliação, esses vales têm folhas:**

| Limiar | Vale no desenvolvimento | Imagens de avaliação dentro do vale |
|---|---|---|
| Concavidade `alta` abaixo de solidez **0,70** | 0,599 – 0,723 | **7**: `3317` 0,605 · `2417` 0,622 · `2370` 0,634 · `3283` 0,647 · `1416` 0,678 · `1392` 0,689 · `1406` 0,711 |
| Orientação `bem_definida` a partir de anisotropia **0,30** | 0,217 – 0,376 | **6**: `1416` 0,224 · `3326` 0,239 · `2024` 0,307 · `3049` 0,329 · `2537` 0,331 · `2488` 0,354 |

Os vales eram, pelo menos em parte, **efeito do tamanho da amostra de desenvolvimento**.
A garantia de "nenhuma folha perto do limiar" não se transfere para imagens novas. Isso
não invalida os limiares — eles continuam separando as distribuições —, mas enfraquece a
justificativa específica dada a eles.

**Nenhum limiar foi alterado.** Um ajuste exigiria um novo conjunto de avaliação.

---

## 13. Casos limítrofes

"Limítrofe" = valor a menos de 5 % (margem relativa) de algum limiar da regra.

| Item | Valor |
|---|---:|
| Imagens com pelo menos um atributo limítrofe | **62 de 96 (64,6 %)** |
| Com 0 / 1 / 2 / 3 / 4 / 5 atributos limítrofes | 34 / 37 / 20 / 5 / 0 / 0 |

| Atributo | Imagens limítrofes |
|---|---:|
| `complexidade_borda` | **35** |
| `concavidade` | 31 |
| `compacidade` | 13 |
| `alongamento` | 11 |
| `orientacao` | 2 |

**`complexidade_borda` é o atributo que mais produz casos limítrofes — e isso já estava
previsto.** A Fase 8 registrou que o limiar de 1,13 "cai no meio da massa" de uma
distribuição muito concentrada. Na avaliação, a mediana da razão é 1,083 e o P75 é 1,138:
o limiar de 1,13 fica exatamente onde as folhas se acumulam. A previsão se confirmou em
dados novos.

A concavidade vem em seguida pelo limiar de 0,92, que também fica numa região densa
(P25 = 0,925).

Imagens com 3 atributos limítrofes (o máximo observado):

| Arquivo | Espécie | Atributos limítrofes |
|---|---|---|
| `2194` | 15 · Cinnamomum camphora | alongamento, concavidade, compacidade |
| `2458` | 19 · Ginkgo biloba | concavidade, compacidade, complexidade_borda |
| `3026` | 23 · Prunus serrulata | concavidade, compacidade, complexidade_borda |
| `3494` | 31 · Populus × canadensis | concavidade, compacidade, complexidade_borda |
| `3617` | 33 · Citrus reticulata | alongamento, concavidade, complexidade_borda |

> Uma proporção de 64,6 % de imagens com algum atributo limítrofe é alta. Ela diz que a
> **descrição textual** de muitas folhas mudaria com uma pequena variação de medida. Os
> **números** continuam sendo o resultado principal; a categoria é uma leitura deles.

---

## 14. Análise descritiva por espécie

**A espécie é só um agrupamento.** Não há métrica de acerto de espécie, porque o pipeline
não identifica espécies. Colunas: imagens no conjunto · processadas · com aviso técnico ·
com erro · medianas de elongação, circularidade, solidez e razão perímetro/hull.

| ID | Espécie | Img | Proc. | Aviso | Erro | Elong. | Circ. | Solidez | Razão |
|---:|---|:-:|:-:|:-:|:-:|---:|---:|---:|---:|
| 01 | Phyllostachys edulis | 3 | 3 | 2 | 0 | 7,041 | 0,279 | 0,952 | 1,060 |
| 02 | Aesculus chinensis | 3 | 3 | 3 | 0 | 2,478 | 0,558 | 0,968 | 1,101 |
| 03 | Berberis anhweiensis | 3 | 3 | 3 | 0 | 2,957 | 0,527 | 0,974 | 1,093 |
| 04 | Cercis chinensis | 3 | 3 | 2 | 0 | 1,090 | 0,787 | 0,965 | 1,072 |
| 05 | Indigofera tinctoria | 3 | 3 | 0 | 0 | 2,187 | 0,714 | 0,994 | 1,057 |
| 06 | Acer palmatum | 3 | 3 | 3 | 0 | 1,088 | 0,107 | 0,468 | 2,013 |
| 07 | Phoebe nanmu | 3 | 3 | 0 | 0 | 3,336 | 0,470 | 0,971 | 1,059 |
| 08 | Kalopanax septemlobus | 3 | 3 | 3 | 0 | 1,168 | 0,332 | 0,689 | 1,381 |
| 09 | Cinnamomum japonicum | 3 | 3 | 1 | 0 | 2,855 | 0,515 | 0,977 | 1,063 |
| 10 | Koelreuteria paniculata | 3 | 3 | 3 | 0 | 1,760 | 0,430 | 0,932 | 1,278 |
| 11 | Ilex macrocarpa | 3 | 3 | 2 | 0 | 1,180 | 0,731 | 0,982 | 1,071 |
| 12 | Pittosporum tobira | 3 | 3 | 1 | 0 | 2,132 | 0,612 | 0,980 | 1,066 |
| 14 | Chimonanthus praecox | 3 | 3 | 2 | 0 | 2,036 | 0,669 | 0,981 | 1,063 |
| 15 | Cinnamomum camphora | 3 | 3 | 3 | 0 | 1,625 | 0,622 | 0,958 | 1,067 |
| 16 | Viburnum awabuki | 3 | 3 | 2 | 0 | 2,652 | 0,534 | 0,983 | 1,086 |
| 17 | Osmanthus fragrans | 3 | 3 | 3 | 0 | 2,243 | 0,582 | 0,969 | 1,107 |
| 18 | Cedrus deodara | 3 | 3 | 3 | 0 | 28,282 | 0,070 | 0,634 | 1,084 |
| 19 | Ginkgo biloba | 3 | 3 | 3 | 0 | 1,709 | 0,614 | 0,924 | 1,109 |
| 20 | Lagerstroemia indica | 3 | 3 | 1 | 0 | 1,470 | 0,820 | 0,994 | 1,064 |
| 21 | Nerium oleander | 3 | 3 | 2 | 0 | 5,786 | 0,311 | 0,988 | 1,059 |
| 22 | Podocarpus macrophyllus | 3 | 3 | 0 | 0 | 8,361 | 0,236 | 0,974 | 1,070 |
| 23 | Prunus serrulata | 3 | 3 | 3 | 0 | 1,690 | 0,471 | 0,909 | 1,228 |
| 24 | Ligustrum lucidum | 3 | 3 | 1 | 0 | 2,039 | 0,701 | 0,988 | 1,056 |
| 25 | Toona sinensis | 3 | 3 | 3 | 0 | 3,545 | 0,367 | 0,904 | 1,093 |
| 26 | Prunus persica | 3 | 3 | 1 | 0 | 3,591 | 0,432 | 0,974 | 1,070 |
| 27 | Manglietia fordiana | 3 | 3 | 0 | 0 | 3,851 | 0,455 | 0,994 | 1,053 |
| 28 | Acer buergerianum | 3 | 3 | 2 | 0 | 1,115 | 0,352 | 0,647 | 1,246 |
| 29 | Mahonia bealei | 3 | 3 | 3 | 0 | 1,397 | 0,539 | 0,842 | 1,176 |
| 30 | Magnolia grandiflora | 3 | 3 | 2 | 0 | 2,441 | 0,621 | 0,991 | 1,057 |
| 31 | Populus × canadensis | 3 | 3 | 3 | 0 | 1,022 | 0,715 | 0,972 | 1,100 |
| 32 | Liriodendron chinense | 3 | 3 | 2 | 0 | 1,064 | 0,582 | 0,863 | 1,192 |
| 33 | Citrus reticulata | 3 | 3 | 3 | 0 | 2,696 | 0,497 | 0,942 | 1,111 |

O rótulo 13 não existe no Flavia (Fase 2). Todas as 32 espécies tiveram as 3 imagens
processadas.

**Observação descritiva:** as medianas separam grupos geométricos esperados pela forma
das folhas — lobadas (Acer palmatum, Kalopanax, Acer buergerianum) com solidez baixa e
razão alta; aciculares e lanceoladas (Cedrus, Podocarpus, Phyllostachys, Nerium) com
elongação alta. Isso é coerência interna das medidas, **não** reconhecimento de espécie.

---

## 15. Performance

Execução **sem** imagens intermediárias. A visualização não entra nestes números.

| Medida | Valor |
|---|---:|
| **Tempo total das 96 imagens** | **27,1 s** |

| Por imagem (ms) | média | mediana | P95 | mín | máx |
|---|---:|---:|---:|---:|---:|
| Tempo de parede (inclui leitura do arquivo) | 282,2 | 284,7 | 326,9 | 201,2 | 367,9 |
| Tempo do pipeline (sem leitura) | 237,2 | 240,9 | 276,5 | 167,1 | 309,8 |

| Etapa (ms) | média | mediana | P95 | mín | máx |
|---|---:|---:|---:|---:|---:|
| Redimensionamento | 7,78 | 5,43 | 14,24 | 4,92 | 23,80 |
| Suavização | 1,56 | 1,45 | 2,20 | 1,15 | 3,62 |
| Segmentação | 29,43 | 28,43 | 34,69 | 26,38 | 51,18 |
| Limpeza | 80,18 | 78,61 | 87,77 | 74,24 | 127,24 |
| Contornos | 21,09 | 20,79 | 22,51 | 19,93 | 23,99 |
| Características | 96,97 | 100,06 | 130,35 | 38,08 | 134,76 |
| Classificação | 0,10 | 0,10 | 0,12 | 0,09 | 0,14 |

**Limpeza e características** somam ~75 % do tempo do pipeline. A classificação é
desprezível.

> Os tempos são ~40 % maiores que os medidos na Fase 9 (mediana de 167 ms sem imagens,
> em 24 imagens de desenvolvimento). A máquina e a carga do sistema variam entre as
> execuções, e as imagens são outras; a diferença não foi investigada. Menos de 0,4 s por
> imagem continua adequado ao uso educacional.

---

## 16. Determinismo

Cinco imagens escolhidas pela **posição** — primeira, três intermediárias e última —
reprocessadas sem nenhuma mudança:

| Índice | Arquivo | status | objeto | características | classificação | erro |
|---:|---|:-:|:-:|:-:|:-:|:-:|
| 0 | `1009` | ✅ | ✅ | ✅ | ✅ | ✅ |
| 24 | `1497` | ✅ | ✅ | ✅ | ✅ | ✅ |
| 48 | `2353` | ✅ | ✅ | ✅ | ✅ | ✅ |
| 71 | `3150` | ✅ | ✅ | ✅ | ✅ | ✅ |
| 95 | `3617` | ✅ | ✅ | ✅ | ✅ | ✅ |

**5 de 5 idênticas.** Além disso, as 12 imagens de inspeção foram reprocessadas **com**
geração de imagens intermediárias, e `objeto`, `caracteristicas` e `classificacao` saíram
idênticos aos da execução principal — mais 12 confirmações.

---

## 17. Casos selecionados para inspeção

Selecionados **automaticamente, por critérios objetivos**, sem julgamento de qualidade.
Arquivo: [`fase10-casos-inspecao.csv`](dados-avaliacao/fase10-casos-inspecao.csv), com as
colunas `inspecao_humana` e `observacao` para a equipe preencher com o protocolo da Fase 2
§15 (correta · aceitável · falha).

| # | Arquivo | Espécie | Motivo |
|---:|---|---|---|
| 1 | `2370` | 18 · Cedrus deodara | maior elongação; menor circularidade |
| 2 | `2353` | 18 · Cedrus deodara | maior elongação; menor circularidade |
| 3 | `2417` | 18 · Cedrus deodara | maior elongação; menor circularidade |
| 4 | `1302` | 06 · Acer palmatum | menor solidez; maior razão perímetro/hull |
| 5 | `1282` | 06 · Acer palmatum | menor solidez; maior razão perímetro/hull |
| 6 | `1269` | 06 · Acer palmatum | menor solidez; maior razão perímetro/hull |
| 7 | `2194` | 15 · Cinnamomum camphora | mais atributos limítrofes |
| 8 | `2458` | 19 · Ginkgo biloba | mais atributos limítrofes |
| 9 | `3026` | 23 · Prunus serrulata | mais atributos limítrofes |
| 10 | `1052` | 01 · Phyllostachys edulis | controle sem aviso técnico |
| 11 | `1191` | 04 · Cercis chinensis | controle sem aviso técnico |
| 12 | `1195` | 05 · Indigofera tinctoria | controle sem aviso técnico |

Os critérios "todos os erros" e "toca a borda" não selecionaram nenhuma imagem, porque não
houve caso.

Os PNGs das 8 etapas desses 12 casos estão em `processamento-imagens/resultados/inspecao-fase10/`
(19 MB, **ignorado pelo Git**). Para regenerá-los:

```bash
cd processamento-imagens
.venv/Scripts/python.exe avaliar_conjunto_final.py inspecao
```

**Sugestões adicionais**, não incluídas na seleção automática e listadas aqui só como
observação: `1416` (a 2 px da borda; solidez no vale de 0,70) e `1406`/`1392` (solidez
perto de 0,70).

### Status da inspeção humana

| Item | Estado |
|---|---|
| Casos revisados | **12/12** |
| Resultado | **Todos considerados visualmente utilizáveis** |
| Correção do pipeline | **Nenhuma necessária, nenhuma feita** — hashes inalterados |
| Reprocessamento | Nenhum; os números desta fase são os da execução única |
| Registro por caso | [`fase10-casos-inspecao.csv`](dados-avaliacao/fase10-casos-inspecao.csv): **12 × `correta`** — folha principal segmentada, máscara e contorno adequados |

Observações registradas no CSV:

| Caso | Observação |
|---|---|
| `1302` | Orientação pouco/não confiável é coerente com a geometria quase simétrica da folha; não é erro de segmentação |
| `3026` | A caixa mínima rotacionada pode ultrapassar visualmente a imagem — comportamento conhecido do `minAreaRect` (R33); não é falha de segmentação |
| `2370`, `2353`, `2417` | Casos extremamente alongados; a geometria observada é coerente |

> **Alcance:** a inspeção cobriu os 12 casos selecionados, não as 96 imagens. Ela reforça,
> mas não prova, que o processamento válido das outras 84 corresponde a segmentações
> corretas.

---

## 18. Limitações

| # | Limitação |
|---|---|
| 1 | **Sem ground truth.** Não há máscaras de referência nem categorias de referência; nada aqui mede acerto |
| 2 | **Inspeção visual só dos 12 casos selecionados** (12/12 utilizáveis). Nas outras 84, "processamento válido" = objeto detectado e medido, não segmentação conferida |
| 3 | `sucesso` puro nunca ocorre, pelo desenho do contrato (§8) |
| 4 | 64,6 % das imagens têm algum atributo limítrofe; a descrição textual é sensível perto dos limiares |
| 5 | Os vales que justificavam dois limiares não se confirmaram na avaliação (§12) |
| 6 | O determinismo foi verificado na mesma máquina e na mesma versão de bibliotecas; outra versão do OpenCV pode mudar valores |
| 7 | Os tempos dependem da máquina e da carga (§15) |
| 8 | 3 imagens por espécie: estatísticas por espécie são descritivas, sem poder de generalização |

---

## 19. Ameaças à validade

| Ameaça | Efeito |
|---|---|
| **O Flavia tem fundo branco e controlado** | A segmentação HSV foi calibrada para essa condição. O resultado **não** se estende a fotos com fundo complexo |
| **Avaliação e desenvolvimento vêm do mesmo dataset** | Mesma câmera, mesmo fundo, mesmo enquadramento. A avaliação reservada protege contra ajuste caso a caso, não contra viés do dataset |
| **A avaliação mede o comportamento técnico do pipeline**, não a generalização para qualquer fotografia | 100 % de processamento válido aqui não prediz o desempenho com fotos de celular |
| **Não há ground truth independente** para as categorias geométricas | As distribuições da §12 descrevem o que as regras produzem, não se está certo |
| **As regras são heurísticas determinísticas** | Limiares derivados de quartis e vales de 64 imagens (Fase 8) |
| **Medidas em pixels** | Sem objeto de referência, não há conversão para unidade física; área e perímetro dependem da resolução e do enquadramento |
| **Sem calibração física** | A mesma folha fotografada a outra distância dá outros valores absolutos |
| **A cor depende da iluminação** | As características de cor não são comparáveis entre condições de captura |
| **`proporcao_verde` tem viés circular** | É medida sobre a máscara que a própria faixa verde definiu; valores próximos de 1 são esperados por construção (mínimo observado 0,981) |
| **O perímetro digital tem viés conhecido (R14)** | Superestima ~5 %; afeta circularidade e razão perímetro/hull (referência convexa ≈1,05, não 1,0) |
| **`minAreaRect` pode divergir do eixo principal** | A elongação vem da caixa de área mínima, que em folhas pouco alongadas pode se alinhar a uma aresta do envelope convexo (R33, Fase 9) |
| **A avaliação externa com fotos reais é outra etapa** | Nenhuma foto fora do Flavia foi usada aqui; a Fase 11 ([`11-ROBUSTEZ-FOTOS-EXTERNAS.md`](11-ROBUSTEZ-FOTOS-EXTERNAS.md)) mostrou baixa robustez visual fora do Flavia |

---

## 20. Conclusão

Sobre as 96 imagens reservadas, com o pipeline congelado em `fase-9-completa`:

- **96 de 96 processadas até o fim, 0 erros**, um único contorno em todas, nenhuma tocando
  a borda;
- 65 com algum aviso técnico, principalmente proximidade de limiar;
- distribuições de características **próximas** às do desenvolvimento;
- **resultado determinístico** (5 + 12 reprocessamentos idênticos);
- **~0,28 s por imagem**, 27 s para o conjunto inteiro;
- **algoritmo inalterado**, provado por 9 hashes idênticos antes e depois.

Duas descobertas que só uma avaliação reservada podia fazer:

1. **Os vales do desenvolvimento não se sustentaram**: 7 e 6 imagens de avaliação caem nas
   faixas que estavam vazias no desenvolvimento.
2. **A fragilidade do limiar de complexidade da borda, prevista na Fase 8, se confirmou**:
   é o atributo com mais casos limítrofes (35).

Nenhuma das duas motivou ajuste. Ambas ficam registradas para trabalho futuro, que
precisaria de um novo conjunto de avaliação.

O que esta fase **não** estabelece sozinha: se as segmentações estão corretas. A inspeção
humana dos 12 casos selecionados, feita depois, considerou **todos os 12 utilizáveis**, sem
necessidade de correção do pipeline.

---

## 21. Próximos passos

1. ~~Inspeção humana dos 12 casos selecionados~~ — **concluída**: 12/12 utilizáveis.
   Julgamento por caso em `fase10-casos-inspecao.csv` (12 × `correta`); inspecionar as 96
   continua opcional.
2. ~~Validação manual da interface no navegador~~ — **concluída**
   ([`TESTES-MANUAIS-FINAIS.md`](../TESTES-MANUAIS-FINAIS.md)).
3. ~~Avaliação externa com fotos reais~~ — **executada na Fase 11**.
4. Se, depois disso, algum limiar ou parâmetro for revisto: **sortear um novo conjunto de
   avaliação** e registrar a revisão, conforme a Fase 2 §13.
5. Documentação final e README raiz.

---

## Arquivos desta fase

| Arquivo | Conteúdo |
|---|---|
| `processamento-imagens/avaliar_conjunto_final.py` | Script de avaliação (casca) |
| `processamento-imagens/tests/test_avaliacao_final.py` | 26 testes da infraestrutura |
| `docs/processamento-imagens/dados-avaliacao/hashes-pipeline-antes.txt` | Hashes antes |
| `docs/processamento-imagens/dados-avaliacao/hashes-pipeline-depois.txt` | Hashes depois |
| `docs/processamento-imagens/dados-avaliacao/hashes-pipeline-comparacao.txt` | Comparação: 9 × `SIM` |
| `docs/processamento-imagens/dados-avaliacao/fase10-resultados-completos.json` | Metadados + resultado completo de cada imagem (~1 MB) |
| `docs/processamento-imagens/dados-avaliacao/fase10-resultados.csv` | 96 linhas, 54 colunas |
| `docs/processamento-imagens/dados-avaliacao/fase10-resumo.json` | Agregados |
| `docs/processamento-imagens/dados-avaliacao/fase10-casos-inspecao.csv` | 12 casos, inspecionados: 12 × `correta` (§17) |

**Testes ao final:** PDI **776 passed** (748 + 26 da infraestrutura + 2 parametrizações de
isolamento que passaram a cobrir o arquivo de teste novo); legado **256/256**.
