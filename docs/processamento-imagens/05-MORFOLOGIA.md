# Fase 5 — Morfologia matemática e limpeza da máscara

> **Escopo:** limpar a máscara binária da Fase 4 sem alterar a geometria real da folha.
>
> **Não implementado:** contorno final, área e perímetro definitivos, bounding box,
> convex hull, características, classificação, pipeline, CLI, API, frontend.
>
> **Resultado da fase, antecipado:** abertura e fechamento foram medidos e **não
> adotados**. A limpeza é feita por remoção de componentes desconectados e
> preenchimento seletivo de buracos — operações que alteram **0,0000% do perímetro** e
> deixam **44 das 64 imagens completamente intactas**.

---

## 1. Objetivo

Reduzir ruído e pequenos defeitos **sem** alterar significativamente a geometria da
folha.

A prioridade, em ordem: preservar forma → preservar área → preservar bordas → preservar
estruturas finas → remover só artefato irrelevante.

---

## 2. O princípio da menor intervenção

> **Limpar não é deixar a máscara visualmente mais lisa.**
>
> Uma máscara mais bonita pode ser matematicamente pior: erosão come pontas, dilatação
> engrossa bordas, e ambas alteram perímetro e circularidade — que são exatamente as
> medidas que o projeto pretende extrair na Fase 6.

**Regra adotada:** se duas soluções entregam resultado equivalente, escolhe-se a que
**modifica menos pixels**.

A Fase 4 deixou uma hipótese explícita na mesa: como o HSV já produz máscaras muito
limpas — dominância mínima 0,9996, no máximo 3 componentes, 0 falhas —, *a melhor
decisão desta fase pode ser fazer muito pouco*. Os dados confirmaram a hipótese.

---

## 3. Operações estudadas

| Operação | Implementada | Adotada | Papel |
|---|:---:|:---:|---|
| Erosão | ✅ | ❌ | Primitiva testável |
| Dilatação | ✅ | ❌ | Primitiva testável |
| Abertura | ✅ | ❌ | Medida e recusada |
| Fechamento | ✅ | ❌ | Medida e recusada |
| **Remoção de componentes pequenos** | ✅ | ✅ | **Adotada** |
| **Preenchimento seletivo de buracos** | ✅ | ✅ | **Adotada** |
| Comparação de máscaras | ✅ | — | Instrumento de auditoria |

Abertura e fechamento **continuam disponíveis por parâmetro** em `limpar_mascara()`,
para experimentação futura — mas desligados por padrão, o que está fixado em teste.

---

## 4. Elementos estruturantes

Três formas implementadas, comparadas com abertura 3×3 no conjunto de desenvolvimento:

| Forma | Δ área mediana | **Δ perímetro mediana** | IoU mínimo | Imagens com >1 componente |
|---|---:|---:|---:|---:|
| Retangular | −0,004% | **−0,150%** | 0,99944 | 4 |
| Elíptico | −0,003% | −0,199% | 0,99943 | 7 |
| Cruz | −0,003% | −0,199% | 0,99943 | 7 |

O retangular é ligeiramente melhor nos dois critérios, mas **as três formas deformam o
perímetro** e **nenhuma resolve a fragmentação**: mesmo a melhor deixa 4 imagens com mais
de um componente, contra 12 do ponto de partida.

A comparação acabou se tornando irrelevante para a decisão final, já que abertura e
fechamento não foram adotados. Fica registrada porque a pergunta foi feita e merece
resposta medida.

---

## 5. Kernels

Tamanhos avaliados: **3×3** e **5×5**. Não foram testados 7×7 ou 9×9 no conjunto real,
porque os dados de 3 e 5 já mostravam degradação crescente do perímetro — aumentar o
kernel só pioraria.

O 7×7 aparece em um único teste sintético, para mostrar **quanto** é preciso crescer o
kernel para que a abertura limpe todo o ruído (§13).

---

## 6. Abertura — medida e recusada

**Hipótese:** erosão seguida de dilatação remove pontos pequenos e devolve ao objeto
principal aproximadamente o tamanho original.

**Resultado no conjunto de desenvolvimento:**

| Kernel | Imagens com >1 comp. | Δ perímetro mediana | IoU mín | Melhor | **Pior** |
|---|---:|---:|---:|---:|---:|
| Sem morfologia | 12 | — | 1,00000 | 0 | 0 |
| Abertura 3×3 | 7 | −0,199% | 0,99943 | 6 | 0 |
| Abertura 5×5 | **2** | −0,113% | 0,99859 | 9 | **5** |

**Falha dupla.** Com kernel 3 limpa apenas metade dos casos (12 → 7) e já custa perímetro.
Com kernel 5 limpa quase tudo (12 → 2), mas **piora 5 imagens**.

O que a abertura apaga, a dilatação **não traz de volta** — é a assimetria que a torna
perigosa para pecíolos, pontas e lóbulos estreitos.

---

## 7. Fechamento — medido e recusado

**Hipótese:** dilatação seguida de erosão preenche descontinuidades e fissuras.

| Kernel | Imagens com >1 comp. | Δ perímetro mediana | IoU mín |
|---|---:|---:|---:|
| Fechamento 3×3 | 9 | −0,106% | 0,99826 |
| Fechamento 5×5 | 8 | −0,052% | 0,99535 |

**Praticamente não limpa** — 12 → 8 no melhor caso — e mesmo assim reduz o perímetro. O
fechamento não ataca o problema real do conjunto, que é **componente desconectado**, e
não fissura interna.

Risco confirmado em teste sintético: com kernel 7, o fechamento **une dois objetos
separados por 4 px**, transformando dois componentes em um.

---

## 8. Erosão

- **reduz** o foreground;
- **rompe** conexões estreitas;
- **destrói estruturas finas** — o risco principal.

Implementada como primitiva testável. **Não usada isolada no pipeline**, conforme a regra
da fase. Verificado que, em objeto convexo, o que a erosão tira é aproximadamente o que a
dilatação põe — diferença abaixo de 10%.

---

## 9. Dilatação

- **aumenta** o foreground;
- **fecha** pequenos vãos;
- **engrossa o contorno**, alterando área e perímetro, e podendo unir objetos vizinhos.

Também implementada como primitiva, também não usada isolada.

---

## 10. Componentes pequenos

### Distribuição medida — 64 imagens

| | |
|---|---|
| Imagens com mais de 1 componente | **12 / 64** |
| Total de componentes pequenos | **15** |
| Área absoluta | 1 a **74 px** (mediana 5, p95 72) |
| Fração do componente principal | 2,5×10⁻⁶ a **3,55×10⁻⁴** |
| Área do componente principal | 21.313 a 428.655 px |

Os seis maiores:

| Imagem | Área | Fração do principal |
|---|---:|---:|
| `3287.jpg` | 74 px | 0,000355 |
| `3306.jpg` | 71 px | 0,000268 |
| `2233.jpg` | 10 px | 0,000051 |
| `2480.jpg` | 10 px | 0,000027 |
| `2078.jpg` | 8 px | 0,000032 |
| `1101.jpg` | 7 px | 0,000024 |

### Critério relativo, e por quê

O componente principal varia de **21.313 a 428.655 px** no conjunto — um fator de 20. Um
limiar absoluto em pixels significaria coisas muito diferentes nas duas pontas dessa
faixa. O critério é, portanto, **a fração da área do maior componente**.

**Limiar adotado: `FRACAO_COMPONENTE_PEQUENO = 0,001`** — cerca de **3× acima** do maior
artefato observado (0,000355) e ordens de grandeza abaixo de qualquer estrutura foliar
real. Um lóbulo ou pecíolo destacado teria fração muito maior.

### Por que isto não é abertura

| | Abertura | Remoção de componentes |
|---|---|---|
| Critério | **forma** — apaga o que for mais estreito que o kernel | **tamanho e desconexão** |
| Alcance | qualquer região, inclusive dentro do objeto | apenas componentes separados |
| Efeito no principal | **corrói a borda** | **não toca um único pixel** |

Fixado em teste: uma linha de 1 px é **destruída** pela abertura 3×3 e **preservada
intacta** pela remoção de componentes.

---

## 11. Preenchimento de buracos

### Método

Um buraco é uma região de fundo **totalmente cercada** pelo objeto — identificada como
componente do fundo que não toca nenhuma borda do quadro. Conectividade **4 para o
fundo**, complementar à **8 usada no objeto**: é o par que evita que fundo e objeto sejam
considerados conectados ao mesmo tempo em diagonais.

### Distribuição medida

| | |
|---|---|
| Imagens com buraco | **14 / 64** |
| Total de buracos | **167** |
| Área | 1 a **216 px** (mediana 4, p75 10, p95 53) |
| Fração do principal | 2,6×10⁻⁶ a **1,105×10⁻³** |

**Os buracos concentram-se em uma imagem.** Dos 167, a grande maioria está em
`2233.jpg` — que é justamente a folha de superfície mais brilhante do conjunto.

### A inspeção que decidiu a questão

O enunciado da fase exige distinguir *"buraco causado pela segmentação"* de *"estrutura
possivelmente real"*. A distinção foi feita **olhando a imagem**, não supondo.

Na comparação `original | máscara | pós-limpeza | diferença` de `2233.jpg`:

- a folha original é **contínua** — não há perfuração, dano ou recorte;
- os buracos da máscara coincidem **exatamente** com as manchas de **reflexo especular**
  na superfície brilhante;
- o reflexo reduz a saturação localmente abaixo do limiar de S, e o pixel cai fora da
  faixa de verde.

> **São defeito de segmentação, não estrutura da folha.** Preenchê-los torna a área
> medida **mais** correta, não menos.

**Limiar adotado: `FRACAO_BURACO_PEQUENO = 0,002`** — cobre todos os 167 observados com
folga de ~2× sobre o maior (0,001105).

### Limitação honesta

O critério é o **tamanho**, e tamanho **não distingue com certeza** um buraco de
segmentação de uma perfuração real pequena. No conjunto de desenvolvimento a inspeção
mostrou que todos vêm de reflexo, mas uma folha com dano de inseto pequeno teria o furo
preenchido indevidamente. Registrado como risco R20.

Verificado em teste que buracos grandes **não** são preenchidos: raios 6, 10 e 60 pixels
(frações 0,0028, 0,0078 e 0,28) são todos preservados.

---

## 12. Métricas de preservação

`comparar_mascaras(antes, depois)` devolve: área antes e depois, variação absoluta e
percentual, interseção, união, **IoU**, pixels removidos, adicionados e alterados.

> Estas métricas **não medem acerto** — não há ground truth. Elas medem **intervenção**:
> quanto da máscara original foi mexida. São o instrumento do princípio da §2.

---

## 13. Testes sintéticos

Formas com propriedades conhecidas por construção: círculo limpo, círculo com ruído
externo, retângulo com buraco, linha fina, objeto serrilhado, dois objetos próximos, dois
distantes, sal e pimenta, componente externo pequeno.

### O contraste que resume a fase

Um círculo com três pontos de ruído (raios 1, 2 e 3):

| Tratamento | Componentes finais | Pixels do objeto principal tocados |
|---|---:|---|
| Abertura 3×3 | 4 — não limpa nada | corrói a borda |
| Abertura 5×5 | 2 | corrói a borda |
| Abertura 7×7 | **1** | **corrói bastante** |
| **Remoção de componentes** | **1** | **zero** |

Para limpar tudo por abertura é preciso kernel 7×7 — que é exatamente o tamanho que
destrói detalhe fino. A remoção de componentes chega ao mesmo resultado **sem tocar no
objeto**.

---

## 14. Linha fina — quando o detalhe desaparece

Medido com linhas de espessura exata:

| Espessura | Abertura 3×3 | Abertura 5×5 | Fechamento | **Remoção de comp.** |
|---|---|---|---|---|
| 1 px | ❌ **destruída** | ❌ destruída | ✅ preservada | ✅ **intacta** |
| 2 px | ❌ **destruída** | ❌ destruída | ✅ preservada | ✅ **intacta** |
| 3 px | ✅ sobrevive | ❌ **destruída** | ✅ preservada | ✅ **intacta** |
| 5 px | ✅ sobrevive | ✅ sobrevive | ✅ preservada | ✅ **intacta** |

A regra é direta: com elemento estruturante *n*×*n*, a erosão exige *n* pixels de largura
para manter o pixel central. **Abertura 3×3 apaga até 2 px; 5×5 apaga até 3 px.**

É o mecanismo exato pelo qual pecíolos, pontas de lóbulo e acículas desapareceriam.

---

## 15. Serrilhas

Serrilha sintética, dentes triangulares na borda. O efeito **depende da escala do detalhe
em relação ao kernel** — e essa dependência é o achado:

| Serrilha | Perímetro original | Abertura 5×5 | Fechamento 5×5 |
|---|---:|---:|---:|
| **Fina** — 40 dentes de 3 px | 899,4 | **864,5** (−3,9%) | **867,1** (−3,6%) |
| Média — 30 dentes de 4 px | 899,4 | 873,4 (−2,9%) | 875,4 (−2,7%) |
| Grossa — 12 dentes de 8 px | 879,5 | 878,4 (−0,1%) | 879,5 (0,0%) |

Serrilha grossa resiste; **serrilha fina perde quase 4% do perímetro**. Registrar os dois
lados evita a conclusão simplista de que "morfologia sempre destrói borda" — ela destrói
**o detalhe da escala do kernel**, que é precisamente o detalhe morfológico interessante.

A remoção de componentes não altera o perímetro da serrilha em nenhuma escala.

---

## 16. Conjunto de desenvolvimento

As mesmas **64 imagens** da Fase 4 (2 por espécie × 32), semente `20260919`.

> **As 96 imagens de avaliação não foram abertas em nenhum momento desta fase.**

---

## 17. Comparação das estratégias

Sete candidatas, com `sem morfologia` como linha de base obrigatória.

| Estratégia | Δ área med | Δ área pior | IoU med | **IoU mín** | **Δ perím med** | **comp>1** | Melhor | Neutro | **Pior** | ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **A** sem morfologia | 0,000 | 0,000 | 1,00000 | 1,00000 | 0,000 | **12** | 0 | 64 | 0 | 0,1 |
| **B** abertura 3 | −0,003 | −0,057 | 0,99997 | 0,99943 | −0,199 | 7 | 6 | 58 | 0 | 7,1 |
| **B** abertura 5 | −0,011 | −0,141 | 0,99989 | 0,99859 | −0,113 | 2 | 9 | 50 | **5** | 7,4 |
| **C** fechamento 3 | 0,002 | 0,000 | 0,99997 | 0,99826 | −0,106 | 9 | 5 | 59 | 0 | 7,0 |
| **C** fechamento 5 | 0,009 | 0,000 | 0,99991 | 0,99535 | −0,052 | 8 | 5 | 59 | 0 | 7,3 |
| **D** abertura→fechamento 3 | −0,001 | −0,036 | 0,99995 | 0,99822 | **−0,302** | 7 | 6 | 58 | 0 | 14,2 |
| **E** fechamento→abertura 3 | 0,000 | −0,009 | 0,99995 | 0,99817 | **−0,302** | 7 | 6 | 58 | 0 | 14,1 |
| **F** remover componentes | 0,000 | −0,036 | 1,00000 | **0,99965** | **0,000** | **0** | 12 | 52 | **0** | 10,6 |
| **G** remover + preencher | 0,000 | −0,036 | 1,00000 | 0,99313 | **0,000** | **0** | **19** | 44 | 1 | 26,0 |

### Leitura

**As operações morfológicas fracassam nos dois lados.** Nenhuma delas elimina a
fragmentação — a melhor (abertura 5×5) ainda deixa 2 imagens, e ao custo de **5 imagens
pioradas**. E todas cobram perímetro: as combinações D e E, que são as mais "completas",
são também as que mais deformam (**−0,302%**).

**F e G zeram a fragmentação com perímetro intocado.** Δ perímetro = **0,000** — não
aproximadamente zero: exatamente zero, em todas as 64 imagens.

O protocolo classificou G com 19 "melhor" contra 12 de F, porque G também corrige os
buracos. O único "pior" de G é `2233.jpg`, cujo IoU cai para 0,99313 — e a §11 mostrou
que essa queda é **a correção de um defeito**, não uma degradação.

---

## 18. Casos críticos

### Acículas — o teste de estresse obrigatório

| Imagem | Operação | Área | Δ área | Comprimento | Δ compr. | Perímetro | Δ perím. |
|---|---|---:|---:|---:|---:|---:|---:|
| **2400** | sem morfologia | 24.674 | — | 1158,8 | — | 2492,8 | — |
| | abertura 3×3 | 24.660 | −0,057% | 1158,8 | 0,000% | 2484,6 | **−0,329%** |
| | abertura 5×5 | 24.641 | −0,134% | 1158,6 | −0,022% | 2490,0 | −0,113% |
| | **adotada (G)** | **24.674** | **0,000%** | **1158,8** | **0,000%** | **2492,8** | **0,000%** |
| **2407** | sem morfologia | 21.313 | — | 1018,1 | — | 2188,5 | — |
| | abertura 3×3 | 21.312 | −0,005% | 1018,1 | 0,000% | 2188,0 | −0,027% |
| | abertura 5×5 | 21.290 | −0,108% | 1017,3 | −0,084% | 2187,1 | −0,065% |
| | **adotada (G)** | **21.313** | **0,000%** | **1018,1** | **0,000%** | **2188,5** | **0,000%** |

**Integridade do objeto:** 1 componente antes e depois, em ambos os casos. A acícula não
foi destruída por nenhuma operação — as acículas do Flavia têm ~20 px de largura, acima
do limite de sobrevivência da §14 —, mas **só a estratégia adotada as preserva
exatamente**.

### Demais casos

| Caso | Imagem | Abertura 5×5 | **Adotada (G)** |
|---|---|---|---|
| **Folha lobada** | `1307` | **−2,398% de perímetro**, −0,503% de comprimento | **0,000%** |
| **Folha serrilhada** | `1491` | −0,587% de perímetro | **0,000%** |
| **Folha larga** | `2497` | −0,032% de perímetro | **0,000%** |
| **Reflexo** | `3430` | 3 → 1 comp., **−0,997% de perímetro** | 3 → 1 comp., **0,000%** |
| **Reflexo + buracos** | `2233` | 2 → 1 comp., −0,549% | 2 → 1 comp., 0,000% · **+0,692% de área** (167 buracos) |
| **Artefato externo** | `3287` | **não remove** (2 comp.) | 2 → 1 comp., −0,036% de área |
| **Artefato externo** | `3306` | **não remove** (3 comp.), −0,957% de perímetro | 3 → 1 comp., −0,025% |

**O caso mais revelador é `1307`**, a folha lobada: a abertura 5×5 custa **2,4% do
perímetro**. Perder 2,4% do perímetro de uma folha lobada é destruir exatamente a
informação morfológica que a Fase 6 pretende medir.

**E `3287`/`3306` mostram o outro lado:** a abertura **nem sequer remove** os artefatos
que motivariam usá-la — e ainda assim cobra perímetro.

### Pecíolo marrom (achado da Fase 4)

`2497.jpg` perde parte do pecíolo na segmentação, por ele não ser verde. **A morfologia
não corrige isso** — o pecíolo não está na máscara para ser preservado. Continua
registrado como limitação da segmentação (R18), não desta fase, e **não foi resolvido
alterando parâmetros da Fase 4**, conforme a regra §30 do enunciado.

---

## 19. Estratégia escolhida

> ## 🌿 **G — remoção de componentes pequenos + preenchimento seletivo de buracos**
> Sem abertura. Sem fechamento. Sem erosão ou dilatação isoladas.

### Resultado no conjunto de desenvolvimento

| Métrica | Valor |
|---|---|
| Variação de área | mediana **0,0000%** · mín −0,0355% · máx **+0,6922%** |
| IoU | mediana **1,00000** · mín 0,99313 |
| **Variação de perímetro** | mediana **0,0000%** · **máximo absoluto 0,0000%** |
| Pixels alterados | mediana **0** · máx 1.353 |
| **Imagens com alteração zero** | **44 / 64** |
| Imagens restantes com >1 componente | **0 / 64** |
| Componentes removidos | 15 |
| Buracos preenchidos | 167 |

### Justificativa

1. **Resolve o problema por completo.** 12 imagens fragmentadas → 0. Nenhuma operação
   morfológica chegou perto.
2. **Não toca o perímetro.** 0,0000% em todas as 64 imagens — contra até −2,4% da
   abertura em folha lobada.
3. **Preserva estrutura fina por construção.** O critério é tamanho e desconexão, não
   espessura: uma linha de 1 px sobrevive intacta.
4. **Menor intervenção.** Em **44 de 64 imagens não altera um único pixel**. Quando
   altera, a mediana é 0,0000% de área.
5. **O preenchimento corrige defeito verificado.** Os 167 buracos foram inspecionados e
   coincidem com reflexo especular numa folha comprovadamente contínua.
6. **Limiares calibrados, não arbitrados**, com margem documentada sobre a distribuição
   real.

### E por que abertura e fechamento ficaram de fora

Não por preferência estética, mas porque **falham nos dois objetivos ao mesmo tempo**:
não limpam (a melhor deixa 2 de 12, e em 2 casos nem remove o artefato) e degradam
(perímetro até −2,4%). Uma operação que não resolve o problema e ainda custa geometria
não tem defesa possível neste contexto.

Elas continuam implementadas, testadas e acessíveis por parâmetro — se um dataset futuro
apresentar máscaras realmente ruidosas, a ferramenta está pronta.

---

## 20. Parâmetros finais da fase

| Parâmetro | Valor | Origem |
|---|---|---|
| `FRACAO_COMPONENTE_PEQUENO` | **0,001** | Calibrado: 3× acima do maior artefato (0,000355) |
| `FRACAO_BURACO_PEQUENO` | **0,002** | Calibrado: 2× acima do maior buraco (0,001105) |
| `remover_pequenos` | **True** | Decisão medida |
| `preencher_buracos` | **True** | Decisão medida |
| `abertura` | **None** | Recusada por evidência |
| `fechamento` | **None** | Recusada por evidência |
| `forma_kernel` | `"eliptico"` | Só relevante se abertura/fechamento forem ligados |
| Conectividade do objeto | 8 | Padrão para foreground |
| Conectividade do fundo | 4 | Complementar, para detecção de buracos |
| Avisos | `variacao_area > 1%`, `IoU < 0,99` | Acima do observado no dev set |

---

## 21. Performance

Máscaras de 1024×768, 64 imagens.

| Operação | Mediana | Mín | Máx |
|---|---:|---:|---:|
| Erosão 3×3 | 7,12 ms | 6,74 | 9,52 |
| Dilatação 3×3 | 7,05 ms | 6,72 | 9,29 |
| Abertura 3×3 | 7,17 ms | 6,86 | 11,10 |
| Abertura 5×5 | 7,79 ms | 7,22 | 11,85 |
| Fechamento 3×3 | 7,43 ms | 6,88 | 10,39 |
| `remover_componentes_pequenos` | 11,26 ms | 10,40 | 14,56 |
| `preencher_buracos_pequenos` | 16,72 ms | 15,79 | 49,21 |
| **`limpar_mascara` (adotada)** | **59,00 ms** | 55,95 | 90,14 |

A estratégia adotada é **~8× mais cara** que uma abertura. Isso **não pesou na decisão**,
conforme a regra da fase: performance não decide contra uma operação que preserva melhor
a geometria.

Vale notar que os 59 ms excedem a soma das duas operações (28 ms) porque `limpar_mascara`
também executa `comparar_mascaras` e a análise de componentes para preencher o contrato
de auditoria. Esse custo é de instrumentação, não de processamento — e pode ser reduzido
no pipeline final se for necessário.

---

## 22. Limitações

| # | Limitação |
|---|---|
| 1 | **Tamanho não distingue buraco real de defeito.** No dev set a inspeção mostrou que todos vêm de reflexo, mas um dano pequeno de inseto seria preenchido indevidamente |
| 2 | **Limiares calibrados em 64 imagens de laboratório**, com fundo branco. Máscaras mais ruidosas — foto de celular sobre fundo texturizado — poderiam exigir outra configuração |
| 3 | **A decisão de recusar abertura/fechamento vale para este dataset.** Em máscaras genuinamente ruidosas a conclusão poderia se inverter |
| 4 | **Kernels 7×7 e maiores não foram testados no conjunto real** — a tendência medida em 3 e 5 tornava isso improdutivo |
| 5 | **A remoção usa o maior componente como referência de escala**, o que pressupõe que ele é a folha. Em imagem com dois objetos de tamanho comparável a referência seria ambígua — mas a **seleção do objeto é da Fase 6** |
| 6 | **O pecíolo perdido na segmentação não é recuperável aqui** |
| 7 | **`limpar_mascara` custa 59 ms**, dominados por instrumentação de auditoria |

---

## 23. Riscos atualizados

| # | Risco | Estado | Nota |
|---|---|---|---|
| **R7** | Limiares arbitrários | 🟢 **Mitigado** | Ambos calibrados sobre distribuição medida, com margem declarada |
| **R14** | Perímetro digital distorce circularidade | 🟠 Aberto | Fase 6. **Mas a decisão desta fase o reduz**: a limpeza não altera o perímetro |
| **R18** | Pecíolo não verde descartado | 🟠 Aberto | Não resolvido aqui, por regra; segue para a Fase 6 |
| **R19** | Faixa calibrada só em folha verde sadia | 🟠 Aberto | Inalterado |
| **R20** 🆕 | **Preenchimento pode fechar perfuração real** | 🟡 Novo | O critério é tamanho; no dev set não ocorreu, mas é possível |
| **R21** 🆕 | **A limpeza pressupõe que o maior componente é a folha** | 🟡 Novo | Referência de escala apenas; a seleção do objeto é da Fase 6 |

---

## 24. Próxima fase

**Fase 6 — Contornos e características.**

| # | Ação |
|---|---|
| 1 | Implementar `contours.py`: detecção e **seleção formal do objeto principal** |
| 2 | Implementar `features.py` com as características classificadas como essenciais na Fase 1 |
| 3 | **Enfrentar o risco R14**: medir o desvio do perímetro digital em círculos sintéticos de vários raios, **antes** de fixar tolerância |
| 4 | Calcular área, perímetro, bounding box reta e rotacionada, centroide, convex hull |
| 5 | Derivar aspect ratio, circularidade, solidez e extent |
| 6 | Medir a distribuição de cada característica no conjunto de desenvolvimento |
| 7 | **Declarar o efeito do pecíolo** (R18) na documentação de perímetro e solidez |
| 8 | Documentar em `06-CARACTERISTICAS.md` |

O conjunto de avaliação continua fechado.

---

*Fase 5 concluída em 20 de setembro de 2026, sobre o commit `6dfffa0`. 307 testes do
módulo e 256 asserções legadas, todos passando.*
