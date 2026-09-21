# Fase 8 — Regras determinísticas e classificação morfológica

> **Escopo:** traduzir os números da Fase 7 em descrições geométricas legíveis, sem
> esconder de onde veio cada decisão.
>
> **Não implementado:** pipeline, CLI, API, frontend. São da Fase 9.

---

## 1. Objetivo

Produzir uma **descrição morfológica aproximada e transparente** da forma observada.

Cada classificação vem acompanhada dos valores que a motivaram, dos limiares aplicados e
da distância até a fronteira mais próxima. Nenhuma categoria é devolvida sozinha.

---

## 2. Por que isto não é inteligência artificial

| | |
|---|---|
| **Não há modelo** | Nenhum objeto é ajustado a dados |
| **Não há treinamento** | Os limiares foram lidos de uma distribuição e escritos no código por uma pessoa |
| **Não há predição** | Há avaliação de condições `if`/`elif` |
| **Não há probabilidade** | Nenhum número da saída é uma probabilidade calibrada |
| **É reproduzível** | A mesma entrada produz sempre exatamente a mesma saída |
| **É auditável** | Cada decisão reporta features, valores e limiares |

### Vocabulário adotado

| ✅ Usa-se | ❌ Não se usa |
|---|---|
| regra, condição | modelo |
| classificação determinística | aprendizado, treinamento |
| interpretação geométrica | predição, inferência |
| descrição morfológica | inteligência |
| margem ao limiar | confiança, probabilidade, score |

O resumo textual é **composição de mapeamentos fixos** — dicionários que traduzem
categoria em frase. Nenhum modelo de linguagem participa.

---

## 3. Limites do escopo

> **O que esta camada nunca fará:** identificar espécie, gênero ou família; atribuir nome
> científico; diagnosticar doença; substituir avaliação botânica.

Isso é garantido por **teste automatizado**: `test_saida_nao_contem_campo_de_especie_nem_de_confianca`
percorre a saída serializada inteira e falha se encontrar qualquer chave de um conjunto
proibido — `especie`, `genero`, `familia`, `nome_cientifico`, `taxon`, `diagnostico`,
`doenca`, `probabilidade`, `score`, `confianca`, `acuracia`, `predicao`.

Outro teste garante que **nenhuma categoria é um termo botânico** (ovada, lanceolada,
cordiforme, acicular…). As categorias são geométricas por construção.

Todo resultado carrega o aviso fixo:

> *"descrição geométrica automática; não constitui identificação botânica nem taxonômica"*

---

## 4. Atributos classificados

Cinco atributos **independentes**. Uma folha tem várias propriedades ao mesmo tempo, e
reduzir tudo a uma classe única descartaria informação.

| Atributo | Categorias |
|---|---|
| **alongamento** | baixa · moderada · alta · extrema |
| **concavidade** | baixa · moderada · alta · **ambígua** |
| **compacidade** | baixa · moderada · alta |
| **complexidade_borda** | regular · moderada · complexa |
| **orientação** | bem_definida · pouco_definida · indefinida |

Todos podem devolver **`indeterminado`** quando a feature necessária estiver ausente ou
fora do domínio.

---

## 5. Features utilizadas

| Atributo | Feature principal | Feature de apoio |
|---|---|---|
| alongamento | `elongacao` | — |
| concavidade | `solidez` | **`elongacao`** (ver §9) |
| compacidade | `circularidade` | — |
| complexidade_borda | `razao_perimetro_hull` | — |
| orientação | `anisotropia` | `orientacao_graus` (reportado, não decide) |

### Features deliberadamente fora das regras

| Feature | Por que não entra |
|---|---|
| **`aspect_ratio`** (caixa reta) | **Sensível a rotação.** Na acícula `2407` dá 1,68 — descrevendo o ângulo da foto — enquanto a elongação dá 32,59. Usar o aspect ratio faria a classificação depender de como a folha foi posicionada |
| `extent`, `extent_rotacionado` | Correlação de **0,869** entre `extent_rotacionado` e `solidez` (Fase 7). Acrescentar os dois seria contar a mesma evidência duas vezes |
| **Cor (RGB, HSV)** | **Cor não define forma.** Nenhuma regra morfológica pode depender de matiz ou saturação |
| **`proporcao_verde`** | R24: é **circular** com a segmentação — a máscara foi criada com a mesma faixa de verde. Quase constante (0,98–0,9998), não informa nada |
| `pontos_hull` | Diagnóstico; varia com discretização, sem interpretação estável |
| Centroide, distância da borda | Descrevem **posição na imagem**, não morfologia |

---

## 6. Distribuição do conjunto de desenvolvimento

Medida **antes** de qualquer limiar ser proposto. É daqui que eles saem.

### Percentis

| Feature | p5 | p10 | p25 | p50 | p75 | p90 | p95 | mín | máx |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **elongacao** | 1,042 | 1,119 | 1,483 | 2,218 | 3,075 | 6,468 | 7,781 | 1,014 | **32,593** |
| **solidez** | 0,617 | 0,765 | 0,927 | 0,970 | 0,982 | 0,990 | 0,994 | **0,473** | 0,995 |
| **circularidade** | 0,134 | 0,255 | 0,415 | 0,538 | 0,645 | 0,723 | 0,761 | 0,048 | **0,814** |
| **razao_P_hull** | 1,056 | 1,057 | 1,062 | 1,078 | 1,127 | 1,288 | 1,337 | **1,051** | 2,145 |
| **anisotropia** | 0,099 | 0,134 | 0,440 | 0,634 | 0,800 | 0,953 | 0,965 | **0,054** | 0,999 |

### Vales — as descontinuidades que servem de separador natural

| Feature | Maior vale | Largura |
|---|---|---:|
| **solidez** | entre **0,599 e 0,723** | **0,124** |
| **anisotropia** | entre **0,217 e 0,376** | **0,159** |
| elongacao | entre 4,367 e 5,943 | 0,749 |

> **Um vale é uma faixa onde nenhuma folha do conjunto cai.** Um limiar colocado ali não
> corta ninguém ao meio — o que é a melhor justificativa empírica possível para uma
> fronteira.

### Histogramas

```
ELONGAÇÃO                        SOLIDEZ
[1,0 – 1,3)  ############# 13    [0,40 – 0,60)  #### 4
[1,3 – 1,6)  ##### 5             [0,60 – 0,70)  (vazio) 0   ← vale
[1,6 – 2,0)  ##### 5             [0,70 – 0,80)  ##### 5
[2,0 – 2,5)  ################# 17[0,80 – 0,90)  ### 3
[2,5 – 3,0)  ####### 7           [0,90 – 0,95)  ######### 9
[3,0 – 4,0)  ###### 6            [0,95 – 0,98)  ######################## 24
[4,0 – 6,0)  #### 4              [0,98 – 1,01)  ################### 19
[6,0 –   ∞)  ####### 7
```

---

## 7. Derivação dos limiares

Dez limiares, todos centralizados na dataclass `Limiares`. **Nenhum número mágico
espalhado pelo código.**

| Atributo | Limiar | Valor | Origem | Justificativa |
|---|---|---:|---|---|
| **alongamento** | baixa até | **1,5** | p25 ≈ 1,483 | Quartil; separa o grupo de 13 folhas quase equidimensionais |
| | alta a partir de | **3,0** | p75 ≈ 3,075 | Quartil |
| | extrema a partir de | **6,0** | p90 ≈ 6,468 | Decil; isola a cauda de 7 folhas |
| **concavidade** | alta abaixo de | **0,70** | **vale 0,599–0,723** | **Cai dentro do maior vale.** Nenhuma folha do conjunto está perto |
| | baixa a partir de | **0,92** | p20 ≈ 0,913 | Separa a massa concentrada acima de 0,90 |
| **compacidade** | baixa abaixo de | **0,40** | p25 ≈ 0,415 | Quartil |
| | alta a partir de | **0,65** | p75 ≈ 0,645 | Quartil. **Não 0,9** — ver §11 |
| **borda** | moderada a partir de | **1,13** | p75 ≈ 1,127 | Quartil |
| | complexa a partir de | **1,30** | p90 ≈ 1,288 | Decil |
| **orientação** | indefinida abaixo de | **0,05** | Fase 6 | **Não alterado**, conforme a regra |
| | bem definida a partir de | **0,30** | **vale 0,217–0,376** | Cai dentro do vale da anisotropia |

> **Todos são experimentais e calibrados no conjunto de desenvolvimento do Flavia** — 64
> imagens de folhas isoladas sobre fundo branco. **Não são universais**, e a dataclass é
> substituível por parâmetro, o que há teste verificando.

### Contenção deliberada do número de regras

**Dez limiares, cinco atributos.** Há teste que falha se passarem de doze — um guarda
contra a tentação de acrescentar exceções até as 64 imagens "parecerem certas".

Todos vieram de **quartis ou vales**, jamais de ajuste caso a caso. Nenhuma imagem
específica motivou nenhum limiar.

---

## 8. Alongamento

Usa **`elongacao`** (lado maior / lado menor da caixa de área mínima).

### Por que não o aspect ratio

| Imagem | Caixa reta | `aspect_ratio` | Caixa mínima | **`elongacao`** |
|---|---|---:|---|---:|
| `2407` | 877 × 523 | **1,68** | 1018 × 31 | **32,59** |

O aspect ratio descreve o ângulo da foto; a elongação descreve a folha. É também a única
característica **imune aos dois vieses R14 e R22** — não usa área nem perímetro.

### Distribuição resultante

| Categoria | Imagens | % |
|---|---:|---:|
| moderada | **30** | 46,9% |
| baixa | 17 | 26,6% |
| alta | 10 | 15,6% |
| extrema | 7 | 10,9% |

---

## 9. Concavidade — e a ambiguidade que a regra reconhece

Usa `solidez` **combinada com** `elongacao`. A combinação não é enfeite: resolve um
problema medido.

### O problema (R25)

| Imagem | Elongação | Solidez | Causa real da solidez baixa |
|---|---:|---:|---|
| `1307` | 1,14 | **0,517** | Borda profundamente lobada |
| `2400` | 19,94 | **0,473** | Acícula **curvada** — sem recorte algum |

**Solidez de 0,473 e 0,517 são quase idênticas**, e as causas são completamente
diferentes. O convex hull de um arco é muito maior que o arco, sem que exista qualquer
recorte de borda.

### A regra

```
solidez < 0,70                              → alta concavidade
solidez < 0,92                              → moderada
solidez ≥ 0,92                              → baixa

MAS: se (alta ou moderada) E elongacao ≥ 6,0 → AMBÍGUA
```

Quando a elongação é extrema, a concavidade é declarada **ambígua**, com a explicação por
extenso no campo `observacoes`:

> *"solidez de 0,473 sugeriria borda recortada, mas a elongação de 19,94 indica objeto
> muito alongado — em forma curvada o envelope convexo é naturalmente maior, sem que haja
> recorte. Causa não distinguível apenas por estas medidas."*

> **Rotular a acícula como "recortada" seria uma afirmação falsa produzida por uma regra
> correta demais para o seu próprio bem.** Dizer "não sei distinguir" é o resultado
> honesto.

Há teste que verifica exatamente isso: as duas solidezes quase iguais produzem categorias
**diferentes e corretas** quando a elongação entra na conta.

### Distribuição resultante

| Categoria | Imagens | % |
|---|---:|---:|
| baixa | 49 | 76,6% |
| moderada | 10 | 15,6% |
| alta | 3 | 4,7% |
| **ambígua** | **2** | 3,1% |

As duas ambíguas são exatamente `2400` e `2407` — as acículas.

---

## 10. Compacidade

Usa `circularidade`, com limiares de **0,40** e **0,65**.

---

## 11. Por que o limiar de compacidade não é 0,9

A Fase 6 mediu que um círculo digital perfeito converge para **0,8973** — nunca 1,0 —
porque o perímetro é superestimado em ~5% e entra ao quadrado na fórmula.

| | Valor |
|---|---|
| Circularidade teórica de um círculo | 1,0 |
| **Circularidade medida de um círculo digital** | **≈ 0,90** |
| **Máximo observado nas 64 folhas** | **0,8143** |

> Um limiar de `circularidade > 0,9 → compacta` classificaria **nenhuma folha**. Um de
> 0,95 não classificaria nem o próprio círculo.

O limiar de **0,65** é o p75 observado. Há teste que falha se `circularidade_alta` for
maior ou igual a 0,90, fixando a lição do R14 na própria regra.

Toda classificação de compacidade carrega a ressalva:

> *"a circularidade tem teto digital de aproximadamente 0,90 (R14); os limiares refletem a
> distribuição observada, não o valor teórico de 1,0"*

### Distribuição resultante

| Categoria | Imagens | % |
|---|---:|---:|
| moderada | 36 | 56,2% |
| baixa | 14 | 21,9% |
| alta | 14 | 21,9% |

---

## 12. Complexidade de borda

Usa `razao_perimetro_hull`, **declaradamente experimental**.

### Duas ressalvas, ambas medidas

**1. A referência não é 1,0.** Um círculo digital — perfeitamente convexo — dá **1,0507**.
O viés do perímetro (R14) afeta o **numerador** e não o denominador: o contorno tem
escada, o hull é um polígono de vértices.

**2. Poder discriminante fraco.** A distribuição é muito concentrada (p25 = 1,062,
p75 = 1,127), e o limiar de 1,13 cai **no meio da massa**. Consequência medida:
**31 das 64 imagens ficam limítrofes** neste atributo — quase metade.

> Isso é um argumento forte para **não promover a métrica a essencial**. A solidez mede a
> mesma ideia por área, é imune ao R14, e tem um vale natural onde colocar o limiar.

Toda classificação carrega a ressalva de que a métrica é experimental e que a referência é
1,05.

### Distribuição resultante

| Categoria | Imagens | % |
|---|---:|---:|
| regular | 50 | 78,1% |
| moderada | 8 | 12,5% |
| complexa | 6 | 9,4% |

---

## 13. Orientação

Classifica **quão definido** é o eixo — **nunca a direção**.

> O ângulo descreve a **pose na imagem**, não a forma da folha. "Horizontal", "vertical" e
> "diagonal" são propriedades do enquadramento: a mesma folha fotografada girada teria
> outro ângulo e continuaria sendo a mesma folha.

Há teste que verifica que a categoria nunca contém essas palavras, para cinco ângulos
diferentes.

O ângulo é **reportado** em `valores`, sempre acompanhado da anisotropia — nunca sozinho.

| Categoria | Anisotropia | Imagens |
|---|---|---:|
| bem_definida | ≥ 0,30 | **52** (81,2%) |
| pouco_definida | 0,05 – 0,30 | **12** (18,8%) |
| indefinida | < 0,05 | 0 |

O limiar de 0,05 é o da Fase 6 e **não foi alterado**, conforme a regra da fase.

---

## 14. Zonas intermediárias e margem ao limiar

### Zonas

Cada atributo tem **três ou quatro faixas**, não uma decisão binária. A faixa do meio *é*
a zona cinzenta: `moderada`, `pouco_definida`, `intermediária`.

### Margem relativa

Cada resultado traz `margem_relativa` — a distância ao limiar mais próximo, em fração do
próprio limiar.

> **Não é confiança nem probabilidade.** Um valor de 3,01 contra um limiar de 3,00 dá
> margem 0,003: caso limítrofe, não "alta certeza". O nome do campo diz o que ele é, e há
> teste que verifica que não existem campos `confianca`, `probabilidade` ou `score`.

Abaixo de 5%, o caso é marcado `limitrofe` e entra nos avisos.

### Uma limitação da margem relativa, registrada

`1177.jpg` tem anisotropia **0,0540** contra o limiar de 0,05 — **0,004 de distância
absoluta**, intuitivamente limítrofe. Mas 0,004 são **8% de 0,05**, acima do critério de
5%, e o caso **não** é marcado como limítrofe.

> A margem relativa funciona bem para limiares de magnitude comparável (1,5 / 3,0 / 6,0) e
> **exagera a folga quando o limiar é pequeno em valor absoluto**.
>
> Isso foi **documentado em teste em vez de contornado com uma exceção**: acrescentar um
> critério absoluto só para este caso seria mais um limiar a calibrar, com uma única
> observação para sustentá-lo.

---

## 15. Casos ambíguos e indeterminados

| Situação | Resposta |
|---|---|
| Feature ausente (`None`) | `indeterminado` + motivo |
| `NaN` ou infinito | `indeterminado` + motivo |
| Fora do domínio (elongação < 1, solidez > 1) | `indeterminado` + motivo |
| Solidez baixa **e** elongação extrema | **`ambigua`** + explicação |
| Perto de um limiar | Categoria + `limitrofe = True` |

**Nenhuma regra levanta exceção.** Feature ruim produz `indeterminado`, não travamento.

---

## 16. Regras finais

```
ALONGAMENTO        elongacao <1,5 → baixa · <3,0 → moderada · <6,0 → alta · ≥6,0 → extrema

CONCAVIDADE        solidez ≥0,92 → baixa · ≥0,70 → moderada · <0,70 → alta
                   SE (alta|moderada) E elongacao ≥6,0 → ambigua

COMPACIDADE        circularidade <0,40 → baixa · <0,65 → moderada · ≥0,65 → alta

BORDA              razao_P_hull <1,13 → regular · <1,30 → moderada · ≥1,30 → complexa

ORIENTAÇÃO         anisotropia <0,05 → indefinida · <0,30 → pouco_definida · ≥0,30 → bem_definida
```

**Cinco regras, dez limiares, uma condição combinada.**

---

## 17. Testes sintéticos

| Forma | Alongamento | Concavidade | Compacidade | Orientação |
|---|---|---|---|---|
| Círculo | baixa | baixa | **alta** | **indefinida** |
| Retângulo 2:1 | moderada | baixa | — | — |
| Retângulo 5:1 | **alta** | baixa | — | — |
| Elipse alongada | alta/extrema | — | — | bem_definida |
| **Estrela** | — | **alta** | baixa | — |
| **Arco alongado** | **extrema** | **ambígua** | — | — |
| Quase circular | baixa | — | — | indefinida/pouco_definida |

O **arco alongado** é a reprodução sintética da acícula curvada: parâmetros escolhidos por
medição para dar elongação 8,00 e solidez 0,42, caindo nas mesmas faixas do caso real.

### Testes de fronteira

Para cada limiar: valor **abaixo**, **exatamente no limiar** e **acima**. Verifica-se que
o valor exatamente no limiar pertence à faixa superior, e que a mudança de categoria
ocorre onde deveria.

---

## 18. Casos reais

| Imagem | Elong | Solidez | Circ | Aniso | Classificação |
|---|---:|---:|---:|---:|---|
| **`2400`** acícula curvada | 19,94 | 0,473 | 0,048 | 0,997 | extrema · **ambígua** · baixa · regular · bem_definida |
| **`2407`** acícula | 32,59 | 0,774 | 0,054 | 0,999 | extrema · **ambígua** · baixa · regular · bem_definida |
| **`1307`** bordo lobado | 1,14 | 0,517 | 0,116 | 0,135 | baixa · **alta** · baixa · **complexa** · pouco_definida |
| **`3287`** bordo lobado | 1,11 | 0,599 | 0,293 | 0,200 | baixa · **alta** · baixa · **complexa** · pouco_definida |
| **`1177`** cordada | 1,04 | 0,971 | 0,797 | **0,054** | baixa · baixa · **alta** · regular · **pouco_definida** |
| **`2497`** oval larga | 1,41 | 0,993 | 0,814 | 0,377 | baixa · baixa · alta · regular · bem_definida |
| **`1491`** serrilhada | 2,25 | 0,945 | 0,425 | 0,625 | moderada · baixa · moderada · moderada · bem_definida |
| `3452` lobada rasa | 1,01 | 0,933 | 0,621 | 0,114 | baixa · baixa · moderada · moderada · pouco_definida |

### Acículas

Ambas caem em `extrema` + `ambigua`, exatamente como projetado. A observação explica que a
solidez baixa pode vir de curvatura e não de recorte.

### Lobadas

`1307` e `3287` recebem **`baixa` alongamento + `alta` concavidade + `complexa` borda** —
a assinatura que as separa sem ambiguidade das acículas, que têm circularidade igualmente
baixa por motivo oposto.

### Baixa anisotropia

`1177` recebe `pouco_definida`, com a observação de que o eixo é fraco. A Fase 6 já havia
observado visualmente que o eixo aparece vertical numa folha mais larga que alta.

---

## 19. Protocolo de inspeção manual

Critérios definidos **antes** de olhar os resultados.

| Categoria | Critério |
|---|---|
| **Coerente** | Todas as cinco categorias correspondem ao que a inspeção geométrica da imagem mostra |
| **Parcialmente coerente** | A maioria corresponde, mas ao menos uma é defensável e imprecisa — ou conservadora demais |
| **Incoerente** | Ao menos uma categoria contradiz o que a imagem mostra |

> **Esta inspeção verifica coerência geométrica, não verdade botânica.** Não há ground
> truth morfológico, e opinião visual **não** é convertida em verdade taxonômica.

Amostra: **12 imagens**, incluindo extremos (acículas, lobadas), medianas e casos
limítrofes, com contorno e convex hull sobrepostos.

---

## 20. Resultado da inspeção

| | Casos | % |
|---|---:|---:|
| 🟢 **Coerente** | **10** | 83,3% |
| 🟡 **Parcialmente coerente** | **2** | 16,7% |
| 🔴 **Incoerente** | **0** | **0%** |

### Os dois parciais, e o que ensinam

**`2407` — a regra foi conservadora demais.** Esta acícula é praticamente **reta**, e a
solidez de 0,774 vem de curvatura mínima. A regra a marcou `ambigua` porque a elongação é
extrema, mas aqui não há nem recorte nem curvatura relevante — `baixa` seria mais preciso.

> A ressalva do R25 é aplicada a **toda** folha de elongação extrema com solidez abaixo de
> 0,92, inclusive quando a solidez não é de fato baixa. É conservadorismo, não erro — mas
> custa precisão em um dos dois casos.

**`3452` — lóbulos rasos não atingem o limiar.** A folha tem entalhes visíveis, e o convex
hull mostra as concavidades, mas a solidez de 0,9334 fica acima de 0,92 e a concavidade
sai como `baixa`. O limiar de 0,92 está no meio de uma região densa da distribuição —
diferente do de 0,70, que cai num vale.

Nenhum dos dois motivou ajuste de limiar. **Ajustar um limiar para acomodar um caso
observado é exatamente o superajuste manual que a Fase 2 definiu como risco.**

---

## 21. Cobertura

| | Valor |
|---|---|
| Atributos determinados | **320 / 320 (100%)** |
| Atributos indeterminados | **0** |
| Concavidade ambígua | 2 / 64 |
| Imagens com ao menos um limítrofe | **45 / 64** |

### Limítrofes por atributo

| Atributo | Casos limítrofes |
|---|---:|
| **complexidade_borda** | **31 / 64** |
| concavidade | 20 / 64 |
| compacidade | 13 / 64 |
| alongamento | 8 / 64 |
| orientação | 0 / 64 |

> **Os 31 limítrofes da complexidade de borda são o achado mais importante desta seção.**
> Quase metade das folhas fica perto de uma fronteira nesse atributo — consequência direta
> da distribuição muito concentrada (p25 = 1,062, p75 = 1,127). É a confirmação empírica
> de que a métrica tem **poder discriminante fraco**, e de que mantê-la como experimental
> foi a decisão certa.

### Sobre "acurácia"

> **Nenhuma acurácia é reportada, e não poderia ser.** Não existe ground truth morfológico
> — não há rótulo verdadeiro contra o qual comparar. Dizer "95% de acerto" exigiria uma
> verdade que o dataset não fornece.
>
> O que se mede é **cobertura, distribuição, consistência, casos limítrofes e coerência
> visual protocolada**.

---

## 22. Performance

| Etapa | Mediana | Mín | Máx |
|---|---:|---:|---:|
| **Classificação (5 regras)** | **0,037 ms** | 0,033 | 0,123 |
| Extração de características (Fase 7) | 70,17 ms | — | — |
| Segmentação + limpeza (Fases 4–5) | ~82 ms | — | — |

A camada de regras custa **0,05% do pipeline** — cerca de **1.900× mais barata** que a
extração de características. É aritmética sobre meia dúzia de números; não há o que
otimizar.

---

## 23. Limitações

| # | Limitação |
|---|---|
| 1 | **Limiares calibrados em 64 imagens de laboratório**, folhas isoladas sobre fundo branco. Não são universais |
| 2 | **A ressalva de ambiguidade é conservadora**: aplica-se a toda folha de elongação extrema com solidez < 0,92, mesmo quando a solidez não é de fato baixa (`2407`) |
| 3 | **O limiar de concavidade em 0,92 cai numa região densa** — 20 casos limítrofes. Só o de 0,70 tem vale natural |
| 4 | **A complexidade de borda discrimina mal** — 31 de 64 limítrofes |
| 5 | **A margem relativa exagera a folga em limiares pequenos** (§14) |
| 6 | **Não há ground truth morfológico**; a validação é coerência visual protocolada |
| 7 | **A inspeção manual cobriu 12 de 64 imagens** |
| 8 | **Nenhuma categoria é botânica**, por decisão — o que limita a comparação com a literatura |
| 9 | **As categorias são discretas**: duas folhas próximas de um limiar recebem rótulos diferentes apesar de serem quase idênticas |

---

## 24. Riscos atualizados

| # | Risco | Estado | Nota |
|---|---|---|---|
| **R25** | Solidez confunde recorte com curvatura | 🟢 **Tratado** | A regra combinada devolve `ambigua` em vez de afirmar recorte |
| **R14** | Perímetro digital | 🟢 **Incorporado às regras** | Limiar de compacidade em 0,65, não 0,9; teste fixa isso |
| **R24** | Proporção de verde circular | 🟢 **Contornado** | Excluída das regras morfológicas |
| **R23** | Orientação instável perto do limiar | 🟢 **Tratado** | `1177` sai como `pouco_definida`, com observação |
| **R18** | Pecíolo ausente | 🟠 Aberto | Afeta as features que alimentam as regras |
| **R19** | Faixa calibrada em folha verde sadia | 🟠 Aberto | Inalterado |
| **R20** | Preenchimento pode fechar perfuração real | 🟡 Aberto | Inalterado |
| **R27** 🆕 | **Descrição geométrica pode ser lida como classificação botânica** | 🟠 Novo | Mitigado por vocabulário neutro, aviso fixo em todo resultado e dois testes de escopo. **Mas o risco é de leitura humana**, e precisa ser reforçado na apresentação |
| **R28** 🆕 | **A ressalva de ambiguidade é conservadora demais** | 🟡 Novo | `2407` marcada ambígua sem necessidade |
| **R29** 🆕 | **Complexidade de borda tem poder discriminante fraco** | 🟡 Novo | 31/64 limítrofes; continua experimental |

---

## 25. Próxima fase

**Fase 9 — Pipeline completo, CLI e API.**

| # | Ação |
|---|---|
| 1 | Criar `pipeline.py` unindo as Fases 3 a 8 num ponto de entrada único |
| 2 | Produzir o JSON do contrato da Fase 1, com o bloco `classificacao` desta fase |
| 3 | Criar `cli.py` como **casca fina** — sem importar `cv2` nem `numpy` |
| 4 | Criar `api.py` em Flask, também casca fina, com as 13 medidas de segurança da Fase 1 |
| 5 | Gerar as 8 imagens intermediárias previstas |
| 6 | Testar que CLI e API produzem **o mesmo resultado** para a mesma imagem |
| 7 | **Resolver o R12** — a invocação com o diretório de nome hifenizado |
| 8 | Criar o `requirements.txt` definitivo |
| 9 | Documentar em `09-PIPELINE.md` |

O conjunto de avaliação **continua fechado** — será aberto apenas na fase de avaliação
final, uma única vez.

---

*Fase 8 concluída em 20 de setembro de 2026, sobre o commit `a8a20d3`. 563 testes do
módulo e 256 asserções legadas, todos passando.*
