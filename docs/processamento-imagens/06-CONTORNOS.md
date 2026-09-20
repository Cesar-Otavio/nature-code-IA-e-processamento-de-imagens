# Fase 6 — Contornos e seleção do objeto principal

> **Escopo:** detectar contornos, formalizar a seleção da folha e produzir as grandezas
> geométricas primárias — área, perímetro, caixas envolventes, centroide, orientação e
> convex hull.
>
> **Não implementado:** circularidade, solidez, extent, aspect ratio final, classificação
> morfológica, pipeline, CLI, API, frontend. São da Fase 7.

---

## 1. Objetivo

Transformar a máscara limpa da Fase 5 na **representação geométrica** da folha, e
preparar exatamente os dados de que a Fase 7 vai precisar.

Uma advertência que atravessa toda a fase:

> **O contorno é uma representação digital aproximada da borda real.**
>
> Ele passa pelos **centros dos pixels de borda**, numa grade discreta. Área e perímetro
> medidos aqui estão sujeitos à discretização espacial, com viés **sistemático e
> mensurável** — não aleatório. A §16 quantifica esse viés, que é o risco R14 finalmente
> medido.

---

## 2. `findContours`

Único ponto de detecção: `cv2.findContours(mascara, MODO_RECUPERACAO, METODO_APROXIMACAO)`.

A máscara é validada antes — 2D, `uint8`, binária 0/255 — pela mesma função da Fase 4,
`validar_mascara`.

---

## 3. Modo de recuperação

Comparação no conjunto de desenvolvimento:

| Modo | Contornos (mediana) | Máximo | Imagens com hierarquia |
|---|---:|---:|---:|
| `RETR_EXTERNAL` | 1 | 1 | — |
| `RETR_TREE` | 1 | 1 | **0 / 64** |

> **`RETR_TREE` devolveu exatamente os mesmos contornos que `RETR_EXTERNAL` em 64/64
> imagens.** Não há um único contorno interno a recuperar.

A razão é a Fase 5: o preenchimento seletivo eliminou os **167 buracos** que a
segmentação produzia. A hierarquia que o `RETR_TREE` existiria para representar foi
removida uma fase antes.

**Adotado: `RETR_EXTERNAL`** — mais simples, e suficiente por medição, não por suposição.

Consequência registrada: com `RETR_EXTERNAL`, um buraco interno **não** aparece no
contorno, e a área poligonal o inclui como se fosse objeto. Fixado em teste
(`test_buraco_nao_altera_o_contorno_externo`). No pipeline atual isso é inócuo, porque
não sobram buracos — mas deixa de ser se o preenchimento for desligado.

---

## 4. Aproximação de contorno

| Método | Pontos (mediana) | Mín | Máx | Memória ~ | Diferença de área | Diferença de perímetro |
|---|---:|---:|---:|---:|---|---|
| `CHAIN_APPROX_NONE` | 2.108 | 1.249 | 4.120 | 16,5 KB | — | — |
| **`CHAIN_APPROX_SIMPLE`** | **1.136** | 532 | 2.104 | **8,9 KB** | **0,000000** | **7×10⁻⁶** |

**Redução de 46,1% nos pontos, com geometria idêntica.** A diferença de perímetro é ruído
de ponto flutuante, não perda de informação: `SIMPLE` descarta apenas pontos colineares
intermediários, que não contribuem nem para o comprimento nem para a área.

Tempo praticamente igual (0,65 ms contra 0,68 ms) — a economia é de memória.

**Adotado: `CHAIN_APPROX_SIMPLE`.** A Fase 7 fará medidas geométricas sobre este
contorno, e a decisão foi tomada justamente conferindo que área e perímetro não mudam.

---

## 5. Seleção do objeto principal

### O critério

**Maior área poligonal.** Implementado em `selecionar_contorno_principal()`.

### A hipótese foi testada, não presumida

A Fase 6 exige formalizar *qual objeto representa a folha*, sem assumir cegamente que é o
maior. Validação nas 64 imagens:

| | |
|---|---|
| Contornos por imagem | **1 em 64/64** |
| Dominância | **1,000000** em todas |
| Seleções ambíguas | **0 / 64** |

> **Registro honesto de escopo.** A seleção acertou 64/64 — mas, com um único contorno em
> cada imagem, **ela não foi exercitada**: não havia escolha a fazer. A validação real do
> critério está nos testes sintéticos (§6), onde há dois objetos de propósito.
>
> Isto é evidência **sobre este dataset após a limpeza da Fase 5**, não verdade universal.
> Uma foto com duas folhas quebraria o critério.

### Critérios alternativos, considerados e não adotados

| Critério | Por que não |
|---|---|
| Proximidade do centro | Puniria folha legitimamente deslocada — e a Fase 1 classificou "folha deslocada" como entrada **aceitável** |
| Não tocar a borda | Nenhuma imagem do conjunto toca; adicionaria regra sem caso de uso |
| Score combinado | Parâmetros novos sem resolver nenhum caso observado |

**Princípio aplicado:** não acrescentar critério que nenhum caso real exige.

### Ambiguidade não é resolvida em silêncio

Quando a razão *área do segundo / área do maior* excede
`RAZAO_AMBIGUIDADE_EXPERIMENTAL = 0,5`, o aviso `selecao_ambigua` é emitido junto com o
resultado.

> **Este limiar é declaradamente experimental.** A maior razão observada no conjunto foi
> **3,55×10⁻⁴** — quatro ordens de grandeza abaixo. Ele não pôde ser calibrado sobre casos
> reais porque o Flavia não contém nenhum. É um aviso para entrada **fora do domínio
> testado**, e está marcado como tal no código.

---

## 6. Múltiplos contornos

O diagnóstico da seleção registra, sempre: `numero_contornos`, `dominancia`,
`razao_segundo_primeiro` e `areas_ordenadas`. **Nada é descartado em silêncio.**

Testes sintéticos cobrem o que o dataset não oferece:

| Cenário | Razão segundo/primeiro | Comportamento |
|---|---:|---|
| Objeto único | — | Sem aviso |
| Objeto dominante + ruído | 0,05 | `multiplos_contornos`, sem ambiguidade |
| Dois objetos comparáveis | 0,90 | **`selecao_ambigua`** |
| Máscara vazia | — | **`E007`** |

---

## 7. Área

Duas medidas, **ambas reportadas**, porque não são a mesma coisa:

| Campo | Método | O que é |
|---|---|---|
| `area_px2` | `cv2.contourArea` | Área do **polígono** definido pelos pontos do contorno |
| `area_mascara_px` | Contagem de pixels | Número de pixels marcados como objeto |

### Diferença medida — 64 imagens

| | Valor |
|---|---|
| Mediana | **−0,419%** |
| Mínimo | **−4,131%** |
| Máximo | −0,253% |
| p5 / p95 | −0,961% / −0,279% |

**A área poligonal é sistematicamente menor**, e a causa é geométrica: o contorno passa
pelos centros dos pixels de borda, descartando aproximadamente meio pixel ao longo de todo
o perímetro.

Os três piores casos:

| Imagem | Diferença | Espécie |
|---|---:|---|
| `2407.jpg` | **−4,131%** | *Cedrus deodara* (acícula) |
| `2400.jpg` | **−3,982%** | *Cedrus deodara* (acícula) |
| `1322.jpg` | −1,085% | *Acer palmatum* (bordo lobado) |

> **O efeito é proporcional à razão perímetro/área.** Uma acícula é quase toda borda:
> perder meio pixel em cada lado custa uma fração enorme da área. Uma folha larga quase
> não sente. **Isso importa para a Fase 7:** qualquer comparação de área entre folhas
> finas e largas carrega esse viés diferencial.

---

## 8. Perímetro

`cv2.arcLength(contorno, True)`, sobre o contorno fechado. Unidade: pixels.

Sensível à discretização de forma **sistemática**, quantificada na §16. Comportamento nos
casos críticos na §19 e §20.

---

## 9. Bounding box alinhada aos eixos

`cv2.boundingRect` → `{x, y, largura, altura}`.

**Sensível a rotação**, verificado em teste: a mesma elipse (150×60) desenhada a 0° dá
caixa larga; a 45° dá caixa quase quadrada. Ela descreve tanto o **enquadramento** quanto
a forma.

Será a base de `aspect_ratio` e `extent` na Fase 7 — com essa limitação declarada.

---

## 10. Bounding box rotacionada

`cv2.minAreaRect`, com **normalização obrigatória**.

### A limitação do ângulo do OpenCV

O ângulo devolvido depende da versão da biblioteca, e **qual dimensão é chamada de
"largura" muda conforme a orientação encontrada**. O mesmo retângulo físico pode sair como
`(w=100, h=40, ang=0)` ou `(w=40, h=100, ang=90)`.

Usar esse valor diretamente produziria **saltos de 90°** em objetos quase quadrados — e
tornaria o "aspect ratio rotacionado" da Fase 7 instável.

### A convenção fixada aqui

| Campo | Garantia |
|---|---|
| `lado_maior` | **Sempre** o maior dos dois |
| `lado_menor` | **Sempre** o menor |
| `angulo_graus` | Ângulo do **lado maior**, normalizado para `[0, 180)` |
| `largura_bruta`, `altura_bruta`, `angulo_bruto` | Retorno original, preservado para auditoria |

Verificado em teste que os lados são **aproximadamente invariantes a rotação** — variação
abaixo de 12 px entre 0°, 30°, 60° e 90° —, ao contrário da caixa reta.

---

## 11. Centroide

Pelos momentos de imagem:

$$c_x = \frac{M_{10}}{M_{00}}, \qquad c_y = \frac{M_{01}}{M_{00}}$$

`M00 == 0` é tratado como **erro `E010`**, e não como divisão por zero silenciosa. Ocorre
em contorno degenerado — por exemplo, uma linha de dois pontos, sem área.

Verificado contra valores analíticos: círculo centrado, retângulo deslocado e triângulo
(cujo centroide é a média dos vértices).

---

## 12. Orientação

$$\theta = \frac{1}{2}\arctan\!\left(\frac{2\mu_{11}}{\mu_{20} - \mu_{02}}\right)$$

Momentos centrais de segunda ordem, normalizados pela área. Resultado em graus, no sentido
matemático a partir do eixo x.

> **Isto é geometria por momentos, não aprendizado de máquina.** Não há treinamento, não
> há ajuste iterativo, não há dados de exemplo. O resultado é função fechada dos pontos do
> contorno. `sklearn` não é usado — e o teste de isolamento garante que não seja.

---

## 13. Confiabilidade da orientação

O ângulo só tem significado se existir um eixo dominante. Num objeto aproximadamente
circular, os dois eixos têm comprimento semelhante e **o ângulo vira ruído** — gira
arbitrariamente com o menor detalhe de borda.

### A medida adotada: anisotropia

Autovalores da matriz de covariância dos momentos centrais normalizados:

$$a = \frac{\lambda_1 - \lambda_2}{\lambda_1 + \lambda_2}$$

Vale 0 para objeto perfeitamente isotrópico e tende a 1 para muito alongado. **Adimensional
e invariante a escala** — as duas propriedades necessárias para comparar imagens
diferentes.

**Limiar: `ANISOTROPIA_MINIMA_EXPERIMENTAL = 0,05`.** Quando abaixo, `orientacao_graus`
é `None` e o aviso `orientacao_nao_confiavel` é emitido. Não se devolve um número sem
significado.

### Distribuição medida — 64 imagens

| | Valor |
|---|---|
| Mínimo | **0,0540** |
| p25 | 0,4399 |
| Mediana | 0,6335 |
| Máximo | **0,9989** |
| Orientação confiável | **64 / 64** |

As três menores:

| Imagem | Anisotropia | Espécie |
|---|---:|---|
| `1177.jpg` | **0,0540** | *Cercis chinensis* (folha cordada, quase circular) |
| `1322.jpg` | 0,0706 | *Acer palmatum* |
| `1134.jpg` | 0,0854 | *Cercis chinensis* |

> **`1177.jpg` está a 0,004 do limiar.** Na inspeção visual, o eixo principal aparece
> **vertical** numa folha que parece mais larga que alta — exatamente a instabilidade que
> o indicador existe para sinalizar. Ela passou no critério, mas por pouco.
>
> **Consequência para a Fase 7:** a orientação dessa folha não deve ser usada como
> característica confiável, ainda que o campo venha preenchido. O valor de `anisotropia`
> precisa acompanhar o ângulo em qualquer análise.

---

## 14. Convex hull

`cv2.convexHull` → hull, área, perímetro e número de vértices.

### Distribuição — 64 imagens

| | Valor |
|---|---|
| `area / area_hull` (prévia de solidez) | mediana **0,9697** · mín **0,4733** · máx 0,9949 |
| Pontos do hull | mediana 63 · mín 14 · máx 120 |

A razão mínima de 0,4733 é de uma folha profundamente lobada: **menos da metade** do seu
envelope convexo é folha. É o descritor que vai distinguir borda lisa de borda recortada
na Fase 7.

Verificado em teste: hull de forma convexa tem área igual à do contorno; hull de quadrado
tem exatamente 4 vértices; perímetro do hull é **menor** que o do contorno côncavo.

---

## 15. Toca-borda e distância

### Detecção por lado

`{topo, base, esquerda, direita, qualquer}`, verificada sobre os **pontos do contorno** —
não sobre a caixa envolvente, que poderia acusar toque por causa de um ponto distante.

**Resultado: 0/64 imagens tocam qualquer borda.**

### Distância mínima da borda

| | Valor |
|---|---|
| Mínimo | **14 px** |
| p5 | 17 px |
| Mediana | 34 px |
| Máximo | 184 px |

Nenhuma folha chega perto de ser cortada. **Não é característica morfológica** — depende
do enquadramento, não da folha —, e por isso fica fora do que a Fase 7 vai medir.

---

## 16. Perímetro digital — o R14 medido

O risco aberto desde a Fase 1, finalmente quantificado.

### Círculo — perímetro teórico $2\pi r$

| Raio | Erro de área | **Erro de perímetro** | **Circularidade medida** |
|---:|---:|---:|---:|
| 10 | −8,33% | **+4,95%** | 0,8323 |
| 20 | −4,51% | +4,95% | 0,8670 |
| 40 | −2,28% | +4,95% | 0,8872 |
| 80 | −1,25% | +5,41% | 0,8886 |
| 160 | −0,62% | +5,41% | 0,8943 |
| 320 | −0,29% | **+5,41%** | **0,8973** |

### Os dois achados centrais

**1. O erro de perímetro não decai com a escala.** Ao contrário do erro de área, que cai
de −8,33% para −0,29%, o erro de perímetro fica **praticamente constante em ~5%**. Aumentar
a resolução **não** resolve.

A razão é geométrica: a borda em escada tem comprimento proporcional ao perímetro real, não
a um termo de ordem menor. Ampliar a figura multiplica escada e arco na mesma proporção.

**2. A circularidade de um círculo digital converge para ~0,90 — não para 1,0.**

Como $C = 4\pi A / P^2$ e o perímetro é superestimado em ~5%, o efeito entra **ao
quadrado**: $1/1{,}05^2 \approx 0{,}907$. Mesmo com raio 320 a circularidade medida é
**0,8973**.

> ### Consequência direta para a Fase 7
>
> **Nenhum limiar de circularidade pode usar 1,0 como referência de "círculo perfeito".**
> A referência empírica é **≈ 0,90**. Um limiar do tipo `circularidade > 0,9 → arredondada`
> classificaria quase nada, porque quase nada alcança esse valor no mundo digital.

### Quadrado — perímetro teórico $4L$

| Lado | Erro de área | **Erro de perímetro** | Circularidade |
|---:|---:|---:|---:|
| 10 | −19,00% | **−10,00%** | 0,7854 |
| 40 | −4,94% | −2,50% | 0,7854 |
| 160 | −1,25% | −0,62% | 0,7854 |
| 320 | −0,62% | **−0,31%** | **0,7854** |

**O sinal do erro se inverte.** Num quadrado alinhado aos eixos não há escada, e o contorno
pelos centros dos pixels **encurta** cada lado em cerca de 1 px.

E a circularidade dá **exatamente $\pi/4 \approx 0{,}7854$ em todas as escalas** — o valor
analítico. Os erros de área e perímetro se cancelam.

> Esse cancelamento é a prova mais forte de que **o viés é determinístico, não ruído**.
> Ele depende da forma e da orientação, e pode ser previsto — o que permite discuti-lo em
> vez de ignorá-lo.

### Quadrado rotacionado 45°

| Lado | Erro de perímetro |
|---:|---:|
| 40 | +1,13% |
| 80 | +0,06% |
| 160 | +0,41% |

Erro pequeno: a diagonal a 45° é a direção que a grade de pixels representa melhor, depois
dos eixos.

---

## 17. Escala

Resumo do comportamento com o tamanho do objeto:

| Grandeza | Com o aumento da escala |
|---|---|
| Erro de **área** | **Decai** — de −8,33% (r=10) para −0,29% (r=320) |
| Erro de **perímetro** | **Não decai** — fica em ~5% no círculo |
| **Circularidade** | Converge para ~0,90, **nunca** para 1,0 |

**Implicação prática:** objetos pequenos têm área subestimada **e** circularidade
enviesada. Comparar circularidade entre uma folha que ocupa 3% do quadro e outra que ocupa
50% carrega um viés que não é da folha — é da amostragem.

É também a justificativa retroativa da decisão da Fase 3 de **redimensionar todas as
imagens para um lado maior comum**: sem isso, o viés variaria de imagem para imagem.

---

## 18. Testes sintéticos

Formas com propriedades conhecidas: círculo, quadrado, retângulo, elipse, triângulo, linha
grossa, objeto rotacionado, objeto tocando cada uma das quatro bordas, múltiplos objetos,
objeto com buraco e forma serrilhada.

**As tolerâncias foram medidas antes de serem fixadas** — os valores da §16 vieram primeiro,
os testes depois. Nenhuma tolerância foi afrouxada até o teste passar.

---

## 19. Acículas

O caso extremo do conjunto.

| | `2400.jpg` | `2407.jpg` |
|---|---:|---:|
| Área poligonal | 23.692 px² | 20.432 px² |
| Área da máscara | 24.674 px | 21.313 px |
| **Diferença** | **−3,98%** | **−4,13%** |
| Perímetro | 2.492,8 px | 2.188,5 px |
| Bbox reta | 957 × 664 | 877 × 523 |
| **Bbox rotacionada** | **1159 × 58** @ 34,8° | **1018 × 31** @ 31,3° |
| Centroide | (536, 350) | (527, 414) |
| Orientação | 34,78° | 31,64° |
| **Anisotropia** | **0,997** | **0,999** |
| Área do hull | 50.052 px² | 26.406 px² |
| Toca borda | Não | Não |

**Três observações.**

A **bbox rotacionada captura a forma com precisão** — 1159×58 descreve a acícula; a caixa
reta (957×664) descreve só o enquadramento diagonal. É a demonstração mais clara de por que
as duas caixas são reportadas.

A **anisotropia é praticamente máxima** (0,997 e 0,999), e a orientação é o dado mais
confiável do conjunto inteiro.

E a **diferença entre área poligonal e de máscara é a maior do conjunto** — ~4%, contra
mediana de −0,42%. Consequência direta da razão perímetro/área extrema: a acícula é quase
toda borda.

---

## 20. Folhas lobadas e serrilhadas

| | `1307` (bordo lobado) | `3287` (bordo lobado) | `1491` (serrilhada) |
|---|---:|---:|---:|
| Área | 203.570 px² | 206.984 px² | 246.090 px² |
| Perímetro | **4.694,9 px** | 2.982,2 px | 2.696,8 px |
| Área do hull | 394.095 px² | 345.660 px² | 260.301 px² |
| **Área / hull** | **0,517** | 0,599 | 0,945 |
| Anisotropia | **0,135** | 0,200 | 0,625 |

**O contorno não simplifica demais.** `1307` tem perímetro de 4.694,9 px para área de
203.570 px² — quase o dobro do perímetro de `1491`, que tem *mais* área. Cada lóbulo e cada
entalhe está no contorno, e a inspeção visual confirma que o traçado acompanha as pontas.

Foi isso que a decisão da Fase 5 preservou: a abertura 5×5 custava **−2,4% do perímetro**
justamente nesta folha.

**A razão área/hull separa os três casos com clareza** — 0,517 e 0,599 para as lobadas,
0,945 para a serrilhada. É a prévia mais promissora para a Fase 7.

**Mas atenção à anisotropia baixa das lobadas** (0,135 e 0,200): uma folha lobada tende à
simetria radial, o que torna o eixo principal pouco definido mesmo estando acima do limiar.

---

## 21. Pecíolo

R18, aberto desde a Fase 4: a segmentação por HSV descarta pecíolo marrom, por não ser
verde.

**Não houve tentativa de recuperá-lo nesta fase**, conforme a regra §31 do enunciado — e
nenhum parâmetro das fases anteriores foi alterado.

Impacto geométrico registrado, em `2497.jpg`:

| Grandeza | Efeito da ausência do pecíolo |
|---|---|
| **Área** | Subestimada pelo tanto que o pecíolo ocuparia |
| **Perímetro** | Alterado — o contorno fecha rente à base em vez de seguir o cabo |
| **Bbox** | Encurtada no eixo do pecíolo |
| **Centroide** | Deslocado para longe da base |
| **Orientação** | Afetada, porque o pecíolo prolonga o eixo principal |
| **Hull** | Menor |

> Parte da literatura de morfologia foliar mede **com** pecíolo, parte **sem**. O projeto
> mede sem — por consequência do método, não por escolha deliberada. **Isso precisa
> constar da documentação de área, perímetro e solidez na Fase 7.**

---

## 22. Conjunto de desenvolvimento

As mesmas **64 imagens** (2 por espécie × 32), semente `20260919`.

| Verificação | Resultado |
|---|---|
| Contorno principal correto | **64 / 64** |
| Ambíguo | **0** |
| Incorreto | **0** |
| Contornos por imagem | 1 em todas |
| Dominância | 1,000000 |
| Toca borda | 0 / 64 |
| Orientação confiável | 64 / 64 |

Confirmado visualmente em 8 casos representativos, com contorno, ambas as caixas,
centroide, eixo principal e hull sobrepostos à imagem original.

> **As 96 imagens de avaliação não foram abertas.**

---

## 23. Visualizações

Geradas em `resultados/temporarios/contornos/` — **diretório ignorado pelo Git**.

Legenda, apenas para depuração visual (não faz parte do processamento numérico):

| Cor | Elemento |
|---|---|
| 🟢 Verde | Contorno principal |
| 🔵 Azul | Bounding box alinhada aos eixos |
| 🟡 Amarelo | Bounding box rotacionada |
| 🟣 Magenta | Convex hull |
| 🔴 Vermelho | Centroide |
| 🩵 Ciano | Eixo principal |

---

## 24. Performance

64 imagens, máscaras de 1024×768.

| Etapa | Mediana | Mín | Máx |
|---|---:|---:|---:|
| `findContours` | **7,99 ms** | 7,73 | 12,29 |
| Seleção do principal | 0,08 ms | 0,06 | 0,14 |
| Convex hull | 0,15 ms | 0,08 | 0,49 |
| Momentos (centroide + orientação) | 0,08 ms | 0,07 | 0,19 |
| **`analisar_contorno` completo** | **14,87 ms** | 14,46 | 20,99 |

`findContours` domina — 8 dos 15 ms. Seleção, hull e momentos somados custam **0,31 ms**,
2% do total. Nenhuma otimização é necessária, e nenhuma foi feita.

---

## 25. Limitações

| # | Limitação |
|---|---|
| 1 | **A seleção do objeto não foi exercitada nas imagens reais** — havia sempre um único contorno. A validação do critério está nos testes sintéticos |
| 2 | **O limiar de ambiguidade (0,5) não foi calibrado sobre casos reais**, porque o dataset não contém nenhum |
| 3 | **A área poligonal é sistematicamente menor que a contagem de pixels**, e a diferença varia com a forma: −0,25% em folha larga, −4,13% em acícula |
| 4 | **O perímetro é superestimado em ~5% em bordas curvas** e subestimado em bordas alinhadas aos eixos. O viés depende da forma |
| 5 | **A circularidade de um círculo digital é ~0,90, não 1,0** |
| 6 | **A orientação é frágil perto do limiar de anisotropia** — `1177.jpg` está a 0,004 dele |
| 7 | **`RETR_EXTERNAL` ignora buracos**, e a área poligonal os inclui como objeto. Inócuo hoje, porque a Fase 5 os preenche |
| 8 | **O pecíolo continua ausente** (R18), afetando seis grandezas |
| 9 | **Os ângulos da bbox rotacionada e dos momentos podem divergir** em objetos pouco anisotrópicos — medem coisas diferentes: envelope mínimo contra distribuição de massa |

---

## 26. Riscos atualizados

| # | Risco | Estado | Nota |
|---|---|---|---|
| **R14** | Perímetro digital distorce circularidade | 🟢 **MEDIDO e quantificado** | ~+5% em curvas, constante com a escala; circularidade de círculo ≈ 0,90. A Fase 7 tem o número de que precisa |
| **R18** | Pecíolo não verde descartado | 🟠 Aberto | Impacto geométrico documentado na §21 |
| **R19** | Faixa calibrada só em folha verde sadia | 🟠 Aberto | Inalterado |
| **R20** | Preenchimento pode fechar perfuração real | 🟡 Aberto | Inalterado |
| **R21** | Limpeza pressupõe maior componente = folha | 🟢 **Formalizado** | A seleção agora é explícita, com diagnóstico e aviso de ambiguidade |
| **R22** 🆕 | **Área poligonal ≠ área de máscara, com viés dependente da forma** | 🟠 Novo | −0,25% a −4,13%. Afeta comparação entre folhas finas e largas |
| **R23** 🆕 | **Orientação instável perto do limiar de anisotropia** | 🟡 Novo | `1177.jpg` a 0,004 do limiar, com eixo visivelmente duvidoso |

---

## 27. Próxima fase

**Fase 7 — Características morfológicas e classificação por regras.**

| # | Ação |
|---|---|
| 1 | Implementar `features.py` com as características essenciais da Fase 1 |
| 2 | **Usar ≈0,90 como referência de círculo**, não 1,0 — consequência direta da §16 |
| 3 | Decidir qual área usar — poligonal ou de máscara — e **declarar a escolha**, dado o viés da §7 |
| 4 | Calcular aspect ratio nas duas caixas, e reportar ambos |
| 5 | Exigir que `anisotropia` acompanhe qualquer uso de orientação |
| 6 | Medir a distribuição de cada característica nas 64 imagens |
| 7 | **Só então** avaliar se há separação que sustente classificação por regras |
| 8 | Declarar o efeito do pecíolo em área, perímetro e solidez |
| 9 | Documentar em `07-CARACTERISTICAS.md` |

O conjunto de avaliação continua fechado.

---

*Fase 6 concluída em 20 de setembro de 2026, sobre o commit `744553c`. 382 testes do
módulo e 256 asserções legadas, todos passando.*
