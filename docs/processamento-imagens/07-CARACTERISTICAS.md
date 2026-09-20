# Fase 7 — Extração das características morfológicas

> **Escopo:** produzir os números. Área, perímetro, dimensões, descritores de forma,
> orientação, convexidade e cor — cada um com definição, fórmula, unidade, intervalo,
> interpretação e limitação.
>
> **Não implementado:** classificação morfológica, regras semânticas, nomes de formato,
> pipeline, CLI, API, frontend. São da Fase 8.

---

## 1. Objetivo

Entregar à Fase 8 uma tabela numérica **confiável e interpretável** para cada folha.

Duas advertências herdadas atravessam o módulo inteiro, e estão conectadas na §21:

| Risco | O que é | Efeito |
|---|---|---|
| **R14** | O perímetro digital é enviesado | **+5%** em bordas curvas, constante com a escala |
| **R22** | Área poligonal ≠ área raster | **−0,25% a −4,13%**, conforme a forma |

> **Nenhum dos dois é "corrigido".** Corrigir um viés sistemático sem base teórica sólida
> trocaria um erro conhecido por um erro desconhecido. Eles são medidos, documentados e
> reportados — e a Fase 8 decide limiares sabendo disso.

---

## 2. Contrato de retorno

`CaracteristicasFolha`, em **seis blocos conceituais** mais os avisos:

```
dimensoes     área, perímetro, larguras          → dependem da escala
forma         aspect ratio, elongação,           → adimensionais
              circularidade, solidez, extent
orientacao    ângulo, anisotropia, confiabilidade
convexidade   hull e complexidade de borda
cor           RGB e HSV, dentro da máscara
qualidade     diagnóstico — NÃO é morfologia
avisos        situações que exigem atenção
```

Os nomes dos campos correspondem ao bloco `caracteristicas` definido na Fase 1 e são
**estáveis**: `para_dicionario()` produz exatamente a estrutura que a API devolverá.

### Valores ausentes

Toda característica que não puder ser calculada devolve **`None`** — nunca `NaN`, nunca
infinito, nunca `0`. A função auxiliar `_dividir()` centraliza isso: divisão por zero,
`NaN` ou infinito retornam `None`.

`0` seria pior que `None`, porque parece um número legítimo. Há teste que percorre a
serialização inteira conferindo que nenhum valor não finito escapa.

### Uma correção de nome em relação à Fase 1

A Fase 1 previa `aspect_ratio_rotacionado`. O nome foi trocado para **`elongacao`**,
porque o anterior era ambíguo: numa caixa rotacionada, *qual lado é a "largura"?* A
resposta depende de convenção, e a Fase 6 fixou "lado maior / lado menor" — que é
**alongamento**, não razão de aspecto. O nome novo diz o que o número é.

---

## 3. Área

**Duas áreas, ambas reportadas.** Nunca se apresenta "a área" sem dizer qual.

| Campo | Método | O que é |
|---|---|---|
| `area_contorno_px2` | `cv2.contourArea` | Área do **polígono** do contorno |
| `area_mascara_px2` | Contagem de pixels | Pixels marcados como objeto |
| `diferenca_area_px2` | Diferença absoluta | — |
| `diferenca_area_pct` | Diferença relativa | Em % da área de máscara |

### Distribuição medida — 64 imagens

| | Mín | p25 | Mediana | p75 | Máx |
|---|---:|---:|---:|---:|---:|
| `area_contorno_px2` | 20.432 | 165.422 | **252.430** | 350.793 | 427.570 |
| `area_mascara_px2` | 21.313 | 166.428 | 253.636 | 351.924 | 428.655 |
| **`diferenca_area_pct`** | **−4,131%** | −0,562% | **−0,419%** | −0,326% | −0,253% |

A área poligonal é **sistematicamente menor**, porque o contorno passa pelos centros dos
pixels de borda e descarta cerca de meio pixel ao longo de todo o perímetro.

---

## 4. Qual área alimenta as características

**Decisão: as adimensionais usam `area_contorno_px2`.**

| Característica | Área usada | Motivo |
|---|---|---|
| Circularidade | contorno | O perímetro vem do contorno; misturar área raster com perímetro poligonal somaria **dois vieses diferentes** na mesma fração |
| Solidez | contorno | O hull vem do contorno; numerador e denominador precisam da mesma origem |
| Extent | contorno | As caixas vêm do contorno |

O princípio é **consistência de origem**: toda fração usa grandezas medidas do mesmo
objeto geométrico. A área raster continua reportada, e a diferença entre as duas também —
quem preferir a outra convenção tem o número para converter.

> **A decisão não é neutra, e o efeito é diferencial.** Numa acícula a diferença é −4,13%;
> numa folha larga, −0,25%. Comparar circularidade entre folhas finas e largas carrega
> esse viés, que é do método e não da folha.

---

## 5. Perímetro

`perimetro_px`, do contorno fechado da Fase 6.

| Mín | p25 | Mediana | p75 | Máx |
|---:|---:|---:|---:|---:|
| 1.405,2 | 2.289,7 | **2.568,3** | 2.711,9 | **4.818,4** |

**Não é um comprimento físico.** É o comprimento de uma poligonal numa grade discreta,
com viés medido de **+5% em bordas curvas** e **negativo** em bordas alinhadas aos eixos.

O máximo de 4.818,4 px é de uma folha profundamente lobada — quase o dobro da mediana,
com área semelhante.

---

## 6. Dimensões

Todas **dependentes de escala**, portanto **não comparáveis** entre imagens de resoluções
diferentes.

| | Mín | p25 | Mediana | p75 | Máx |
|---|---:|---:|---:|---:|---:|
| `largura_px` | 542 | 783 | 910 | 944 | 980 |
| `altura_px` | 184 | 530 | 644 | 671 | 725 |
| `lado_maior_px` | — | — | — | — | — |
| `lado_menor_px` | — | — | — | — | — |

Os lados da caixa rotacionada também são reportados, e são a base da elongação.

---

## 7. Aspect ratio

$$\text{AR} = \frac{w}{h} \quad \text{(caixa reta)}$$

| | Valor |
|---|---|
| Unidade | adimensional |
| Intervalo | $(0, \infty)$ |
| Medido | mín **1,0070** · mediana **1,4438** · máx **4,1087** |

**Sensível a rotação.** Descreve o enquadramento tanto quanto a forma: a mesma elipse a
0° dá AR > 2,5; a 45°, AR ≈ 1,0.

**Limitação:** pode ser menor ou maior que 1 conforme a folha esteja deitada ou em pé —
duas folhas idênticas fotografadas em ângulos diferentes recebem valores diferentes.

---

## 8. Elongação

$$E = \frac{\text{lado maior}}{\text{lado menor}} \quad \text{(caixa de área mínima)}$$

| | Valor |
|---|---|
| Unidade | adimensional |
| Intervalo | $[1, \infty)$ — **sempre ≥ 1 por construção** |
| Medido | mín **1,0142** · mediana **2,2177** · máx **32,5929** |

**Invariante a rotação**, verificado em teste com a mesma elipse a 0°, 30°, 45°, 60° e 90°.

### A comparação que justifica reportar as duas

| Imagem | Caixa reta | AR | Caixa rotacionada | **Elongação** |
|---|---|---:|---|---:|
| `2407` (acícula) | 877 × 523 | 1,68 | **1018 × 31** | **32,59** |

A caixa reta descreve o ângulo em que a folha foi fotografada; a rotacionada descreve a
folha. **Correlação medida entre as duas: r = 0,064** — praticamente independentes. São
medidas diferentes, e as duas ficam.

---

## 9. Circularidade

$$C = \frac{4\pi A}{P^2}$$

| | Valor |
|---|---|
| Unidade | adimensional |
| Intervalo teórico | $(0, 1]$ |
| **Máximo prático** | **≈ 0,90** — ver abaixo |
| Medido | mín **0,0479** · mediana **0,5381** · máx **0,8143** |

### O teto real não é 1,0

Medido na Fase 6, em círculos sintéticos:

| Raio | Circularidade medida |
|---:|---:|
| 40 | 0,8872 |
| 80 | 0,8886 |
| 160 | 0,8943 |
| **320** | **0,8973** |

Como o perímetro é superestimado em ~5% e entra **ao quadrado**, o efeito é
$1/1{,}05^2 \approx 0{,}907$. **Um círculo perfeito nunca alcança 1,0 em imagem digital.**

> A constante `CIRCULARIDADE_DE_CIRCULO_DIGITAL = 0.90` está no código como **referência
> empírica**, não como fator de correção — nada é multiplicado por ela. Ela existe para
> que a Fase 8 não use 1,0 como "círculo perfeito" ao definir limiares.
>
> Um limiar como `circularidade > 0,9 → arredondada` classificaria **quase nada**: o
> máximo observado nas 64 folhas é 0,8143.

### Uma ambiguidade da própria medida

A circularidade cai tanto por **alongamento** quanto por **irregularidade de borda** — e
o número sozinho não distingue as causas. `1307` (bordo lobado, elongação 1,14) tem
circularidade 0,1161; `2407` (acícula lisa, elongação 32,59) tem 0,0536. Valores
parecidos, motivos opostos. **É preciso ler circularidade junto com elongação e solidez.**

---

## 10. Solidez

$$S = \frac{A}{A_{hull}}$$

| | Valor |
|---|---|
| Unidade | adimensional |
| Intervalo | $(0, 1]$ |
| Medido | mín **0,4733** · mediana **0,9697** · máx **0,9949** |

**É o único descritor do conjunto que captura recorte de borda.** Vale ≈ 1 para forma
convexa e cai conforme a borda se torna lobada ou recortada.

Ao contrário da circularidade, **não** é afetada pelo viés do perímetro: compara duas
áreas, ambas sujeitas ao mesmo viés, que em boa medida se cancela na razão.

Aviso `solidez_baixa_borda_muito_recortada` dispara abaixo de 0,7.

---

## 11. Extent

$$\text{Ext} = \frac{A}{w \cdot h} \quad \text{(caixa reta)}$$

| | Valor |
|---|---|
| Unidade | adimensional |
| Intervalo | $(0, 1]$ |
| Referências | retângulo alinhado = 1,0 · círculo = $\pi/4 ≈ 0{,}785$ |
| Medido | mín **0,0373** · mediana **0,5887** · máx **0,8100** |

**Sensível a rotação**, e fortemente. O mínimo de 0,0373 é da acícula `2400`: a caixa reta
de uma agulha diagonal é enorme comparada à agulha.

---

## 12. Extent rotacionado

$$\text{Ext}_{rot} = \frac{A}{\text{lado maior} \times \text{lado menor}}$$

| | Valor |
|---|---|
| Medido | mín **0,3517** · mediana **0,6733** · máx **0,8158** |

Muito mais estável: a faixa é de 0,35 a 0,82, contra 0,04 a 0,81 do extent reto.

| Imagem | Extent | **Extent rotacionado** |
|---|---:|---:|
| `2400` | 0,0373 | **0,3517** |
| `2407` | 0,0445 | **0,6424** |

**As duas são reportadas.** O extent reto **não** foi substituído automaticamente: ele
continua sendo a definição clássica da literatura, e descartá-lo dificultaria comparação
com outros trabalhos. Mas o rotacionado é o que descreve a forma.

---

## 13. Centroide

$c_x = M_{10}/M_{00}$, $c_y = M_{01}/M_{00}$, em pixels.

Também são reportadas as versões normalizadas pelo tamanho da imagem
(`centroide_x_norm`, `centroide_y_norm`).

> **As coordenadas normalizadas ficam no bloco `qualidade`, não em `forma`.** Elas
> descrevem **posição na imagem**, e não morfologia da folha: uma folha deslocada não é
> uma folha diferente. Classificá-las como característica de forma seria um erro
> conceitual que contaminaria qualquer análise posterior.

---

## 14. Orientação

$$\theta = \frac{1}{2}\arctan\!\left(\frac{2\mu_{11}}{\mu_{20} - \mu_{02}}\right)$$

Em graus, sentido matemático a partir do eixo x. Devolvida como `None` quando a
anisotropia indica que não há eixo dominante.

**Nunca é reportada sozinha:** vem sempre acompanhada de `anisotropia` e `confiavel`.

---

## 15. Anisotropia

$$a = \frac{\lambda_1 - \lambda_2}{\lambda_1 + \lambda_2}$$

Autovalores da covariância dos momentos centrais normalizados.

| | Valor |
|---|---|
| Unidade | adimensional |
| Intervalo | $[0, 1]$ |
| Limiar de confiabilidade | **0,05** (Fase 6, **não alterado**) |
| Medido | mín **0,0540** · mediana **0,6335** · máx **0,9989** |

Vale 0 para objeto isotrópico e tende a 1 para muito alongado. Abaixo do limiar, o ângulo
gira arbitrariamente com o menor detalhe de borda.

**Todas as 64 folhas ficaram acima do limiar** — mas `1177.jpg` está a **0,004** dele.
Ver §23.

---

## 16. Convex hull

| Campo | Medido |
|---|---|
| `area_hull_px2` | — |
| `perimetro_hull_px` | — |
| `pontos_hull` | mín 14 · mediana 63 · máx 120 |
| `razao_perimetro_hull` | mín **1,0507** · mediana 1,0779 · máx **2,1452** |

**`pontos_hull` é diagnóstico, não característica.** O número de vértices depende de
detalhes de discretização da borda e não tem interpretação morfológica estável.

### Razão perímetro/hull — e por que continua experimental

$$R = \frac{P}{P_{hull}}$$

Hipótese: mede complexidade de borda — quanto o contorno "passeia" em relação ao caminho
mais curto que envolve o objeto.

> **Achado desta fase: a referência não é 1,0.** Um círculo digital — perfeitamente
> convexo — dá **1,0507**, não 1,0.
>
> A causa é o R14 entrando **em apenas uma das pontas da fração**: o contorno tem escada
> e é ~5% mais longo que a realidade; o hull é um polígono de vértices, sem escada. O
> viés não se cancela, como acontece na solidez.

Isso a torna **menos interpretável que a solidez**, que mede a mesma ideia por área e cuja
referência é genuinamente 1,0. Ela discrimina — 2,02 na folha lobada contra 1,07 no
círculo — mas permanece **experimental**, e não entra no conjunto essencial.

---

## 17. Cor — RGB

Média e mediana dos pixels **dentro da máscara**. O fundo branco nunca entra, verificado
em teste.

A **mediana** é reportada porque é robusta a reflexo especular: num teste com 2.000 pixels
saturados artificialmente, a mediana do canal verde se manteve em 140,0 enquanto a média
subiu.

---

## 18. Cor — HSV

| Canal | Mín | p25 | Mediana | p75 | Máx |
|---|---:|---:|---:|---:|---:|
| **H** | 47,0 | 51,1 | **52,8** | 54,4 | 59,4 |
| **S** | 98,2 | 145,9 | 171,1 | 194,4 | 250,0 |
| **V** | 72,2 | 136,1 | 153,4 | 168,4 | 220,9 |

O matiz é **notavelmente concentrado**: 32 espécies diferentes, e a média por imagem varia
apenas de 47,0 a 59,4 numa escala de 0 a 179.

### Limitação: matiz é uma grandeza circular

A média aritmética de H só é válida enquanto os valores **não cruzam a fronteira 0/179**.
Uma folha avermelhada teria matiz próximo de 0, e a média de valores como 178 e 2 daria 90
— verde, que é o oposto do correto.

No Flavia isso não ocorre: o matiz está longe da fronteira em todas as 64 imagens. **Mas a
limitação vale para qualquer foto que o usuário envie**, e a mediana é reportada
justamente por ser menos suscetível.

---

## 19. Proporção de verde

Fração dos pixels da folha dentro da faixa HSV da Fase 4.

| Mín | p25 | Mediana | p75 | Máx |
|---:|---:|---:|---:|---:|
| **0,9804** | 0,9969 | **0,9980** | 0,9988 | 0,9998 |

### O viés metodológico, declarado

> **Este número é quase constante — e isso era previsível.**
>
> A máscara foi **criada** selecionando pixels dentro dessa mesma faixa de verde. Medir
> depois quantos pixels da máscara estão na faixa é, em boa medida, **circular**: a
> resposta tende a 1 por construção.
>
> A variação observada (0,9804 a 0,9998) vem apenas do filtro Gaussiano aplicado antes da
> segmentação, que altera levemente alguns pixels de borda.

**Portanto a proporção de verde NÃO é evidência de que a folha é verde.** Ela é uma
característica descritiva com utilidade limitada neste pipeline. Passaria a ser informativa
se a máscara viesse de outro método — Otsu, por exemplo, que segmenta por intensidade.

A implementação em `extrair_cor` **aceita faixa por parâmetro**, então a medição não
circular é possível quando fizer sentido.

---

## 20. Escala

| Dependentes de escala | Adimensionais |
|---|---|
| `area_contorno_px2`, `area_mascara_px2` | `aspect_ratio`, `elongacao` |
| `perimetro_px` | `circularidade`, `solidez` |
| `largura_px`, `altura_px` | `extent`, `extent_rotacionado` |
| `lado_maior_px`, `lado_menor_px` | `anisotropia`, `razao_perimetro_hull` |
| `area_hull_px2`, `perimetro_hull_px` | `proporcao_verde` |

### Quão estáveis as adimensionais realmente são

Medido com o mesmo círculo em raios 40, 80 e 160:

| Característica | Variação |
|---|---|
| `aspect_ratio`, `elongacao`, `solidez`, `extent` | **< 0,05** — estáveis |
| **`circularidade`** | **deriva de 0,8872 para 0,8943** |

> **A circularidade não é perfeitamente invariante a escala.** Ela cresce com o tamanho do
> objeto, porque o viés do perímetro pesa relativamente mais em objetos pequenos. A deriva
> é pequena (~0,01 entre r=40 e r=320), mas **existe e é sistemática** — há teste que a
> fixa.
>
> É a justificativa retroativa da decisão da Fase 3 de redimensionar todas as imagens para
> um lado maior comum: sem isso, a deriva variaria de imagem para imagem.

**Nada foi normalizado artificialmente para 0–1.** Apenas características com definição
adimensional própria permanecem nessa escala.

---

## 21. Como R14 e R22 afetam cada característica

A conexão pedida explicitamente pelo enunciado.

| Característica | Efeito do **R14** (perímetro +5%) | Efeito do **R22** (área −0,25% a −4,13%) | Resultado |
|---|---|---|---|
| **Circularidade** $4\pi A/P^2$ | **Forte** — $P$ entra ao quadrado | Moderado — $A$ é linear | **Teto em ≈0,90**, e deriva com a escala |
| **Solidez** $A/A_{hull}$ | **Nenhum** — não usa perímetro | **Cancela em boa parte** — as duas áreas têm o mesmo viés | **A mais robusta** |
| **Extent** $A/(wh)$ | Nenhum | Pequeno — só o numerador é afetado | Leve subestimação |
| **Razão P/P_hull** | **Assimétrico** — afeta só o numerador | Nenhum | **Referência vira 1,05**, não 1,0 |
| **Elongação** | Nenhum | Nenhum — usa só as caixas | **Imune aos dois** |

### A leitura prática

> **Solidez e elongação são as características mais confiáveis do conjunto.** A primeira
> porque o viés se cancela na razão de áreas; a segunda porque não usa nem área nem
> perímetro.
>
> **Circularidade é a mais afetada** — e é também a mais usada na literatura. Por isso o
> teto de 0,90 precisa estar visível em qualquer limiar que a Fase 8 defina.

---

## 22. Redundância entre características

Correlação de Pearson entre as oito adimensionais, nas 64 imagens:

| | AR | elong | circ | solidez | extent | ext_rot | P/Ph | aniso |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **aspect_ratio** | 1,000 | 0,064 | 0,037 | 0,298 | 0,261 | 0,190 | −0,256 | 0,427 |
| **elongacao** | 0,064 | 1,000 | −0,578 | −0,227 | −0,681 | −0,152 | −0,179 | 0,528 |
| **circularidade** | 0,037 | −0,578 | 1,000 | 0,623 | **0,846** | 0,630 | −0,439 | −0,320 |
| **solidez** | 0,298 | −0,227 | 0,623 | 1,000 | 0,371 | **0,869** | −0,743 | 0,385 |
| **extent** | 0,261 | −0,681 | **0,846** | 0,371 | 1,000 | 0,416 | −0,093 | −0,514 |
| **extent_rot** | 0,190 | −0,152 | 0,630 | **0,869** | 0,416 | 1,000 | −0,669 | 0,191 |
| **razao_P_hull** | −0,256 | −0,179 | −0,439 | −0,743 | −0,093 | −0,669 | 1,000 | −0,521 |
| **anisotropia** | 0,427 | 0,528 | −0,320 | 0,385 | −0,514 | 0,191 | −0,521 | 1,000 |

### Único par acima de 0,85

**`solidez` × `extent_rotacionado`: r = 0,869.**

Faz sentido: ambas medem "quanto do envelope a folha preenche" — uma contra o hull
convexo, outra contra o retângulo mínimo.

**Decisão: manter as duas, com `solidez` como primária.** Justificativa:

1. r = 0,869 é forte, mas **não é equivalência** — restam ~25% de variância independente;
2. **solidez é mais interpretável**: o hull é o envelope natural da forma, e sua
   referência é genuinamente 1,0;
3. solidez é **imune ao R14** (§21); o extent rotacionado herda um resíduo pela área;
4. o extent rotacionado captura alongamento que o hull não vê — uma folha lisa mas muito
   alongada tem solidez alta e extent rotacionado menor.

### O que a tabela também revela

**`aspect_ratio` × `elongacao`: r = 0,064.** Praticamente independentes — a confirmação
numérica de que medem coisas diferentes e que reportar as duas não é redundância.

**`circularidade` × `extent`: r = 0,846**, logo abaixo do limiar. Ambas caem com
alongamento, o que explica a correlação sem torná-las intercambiáveis.

---

## 23. Casos extremos e outliers

**Nenhum outlier foi removido.** Todos representam morfologia real.

### Acículas — `2400` e `2407`

| | `2400` | `2407` |
|---|---:|---:|
| Área do contorno | 23.692 px² | 20.432 px² |
| Perímetro | 2.492,8 px | 2.188,5 px |
| **Elongação** | **19,94** | **32,59** |
| Circularidade | **0,0479** | 0,0536 |
| **Solidez** | **0,4733** | 0,7738 |
| Extent | 0,0373 | 0,0445 |
| Extent rotacionado | 0,3517 | 0,6424 |
| Anisotropia | 0,9965 | **0,9989** |

Elongação de 32,59 e anisotropia de 0,9989 — os extremos do conjunto nas duas medidas, e
uma descrição fiel do que uma acícula é.

> **A diferença de solidez entre as duas é reveladora: 0,47 contra 0,77.** Ambas são
> acículas, mas `2400` está **curvada**, e o hull de um arco é muito maior que o arco.
> A solidez está capturando curvatura, não recorte de borda — uma ambiguidade da medida
> que vale registrar para a Fase 8.

### Folhas lobadas — `1307` e `3287`

| | `1307` | `3287` |
|---|---:|---:|
| Perímetro | **4.694,9 px** | 2.982,2 px |
| Elongação | 1,14 | 1,11 |
| **Circularidade** | **0,1161** | 0,2925 |
| **Solidez** | **0,5166** | 0,5988 |
| **Razão P/P_hull** | **2,021** | 1,342 |
| Anisotropia | 0,1346 | 0,1997 |

Elongação ≈ 1 — folhas quase tão largas quanto altas — mas circularidade baixíssima e
solidez em torno de 0,5. **É exatamente a assinatura de borda profundamente recortada**, e
a combinação `elongação ≈ 1` + `solidez baixa` a separa sem ambiguidade de uma acícula,
que tem circularidade igualmente baixa por motivo oposto.

`1307` tem a maior razão P/P_hull do conjunto (2,021): o contorno é o dobro do caminho
convexo.

### Baixa anisotropia — `1177`

| | Valor |
|---|---|
| **Anisotropia** | **0,0540** — a menor do conjunto |
| Limiar de confiabilidade | 0,05 |
| Margem | **0,004** |
| Circularidade | 0,7972 — a segunda maior |
| Solidez | 0,9713 |
| Elongação | 1,04 |

> Folha cordada, quase tão larga quanto alta. Passou no critério de confiabilidade **por
> 0,004**. A inspeção visual da Fase 6 mostrou o eixo principal **vertical** numa folha
> que parece mais larga que alta.
>
> **Recomendação para a Fase 8:** nenhuma regra deve usar `orientacao_graus` sem consultar
> `anisotropia` junto. O campo vem preenchido, mas o valor é frágil.

---

## 24. Conjunto de desenvolvimento

As mesmas **64 imagens**, semente `20260919`.

> **As 96 imagens de avaliação não foram abertas.** Confirmado programaticamente: o
> script de extração filtra por `uso == "desenvolvimento"` e verifica os dois tamanhos.

Extração bem-sucedida em **64/64**, sem exceção e sem valor ausente.

---

## 25. Tabela de referência das características

| Característica | Fórmula | Unidade | Intervalo | Interpretação | Limitação |
|---|---|---|---|---|---|
| `area_contorno_px2` | `contourArea` | px² | > 0 | Tamanho do polígono | Depende da escala; −0,25% a −4,13% vs raster |
| `area_mascara_px2` | contagem | px² | > 0 | Tamanho em pixels | Depende da escala |
| `perimetro_px` | `arcLength` | px | > 0 | Comprimento da borda | **+5% em curvas (R14)** |
| `largura_px`, `altura_px` | `boundingRect` | px | > 0 | Caixa reta | Muda com rotação |
| `lado_maior/menor_px` | `minAreaRect` | px | > 0 | Caixa mínima | Depende da escala |
| `aspect_ratio` | $w/h$ | — | $(0,\infty)$ | Largo vs alto | **Sensível a rotação** |
| **`elongacao`** | $\ell_{maior}/\ell_{menor}$ | — | $[1,\infty)$ | Quão alongada | **Imune a R14 e R22** |
| **`circularidade`** | $4\pi A/P^2$ | — | $(0,1]$ | Quão próxima de círculo | **Teto real ≈0,90**; ambígua entre alongamento e recorte |
| **`solidez`** | $A/A_{hull}$ | — | $(0,1]$ | Recorte de borda | Também captura curvatura |
| `extent` | $A/(wh)$ | — | $(0,1]$ | Preenchimento da caixa | **Sensível a rotação** |
| `extent_rotacionado` | $A/(\ell_M\ell_m)$ | — | $(0,1]$ | Idem, invariante | r=0,869 com solidez |
| `centroide_*_px` | momentos | px | — | Centro de massa | Posição, não forma |
| `orientacao_graus` | momentos | ° | $[-90,90]$ | Eixo principal | **`None` se anisotropia < 0,05** |
| `anisotropia` | $(\lambda_1-\lambda_2)/(\lambda_1+\lambda_2)$ | — | $[0,1]$ | Quão definido é o eixo | — |
| `area_hull_px2` | `convexHull` | px² | > 0 | Envelope convexo | Depende da escala |
| `razao_perimetro_hull` | $P/P_{hull}$ | — | $[1,\infty)$ | Complexidade de borda | **Referência 1,05, não 1,0** — experimental |
| `media_rgb`, `mediana_rgb` | média/mediana | 0–255 | — | Cor | Depende da iluminação |
| `media_hsv`, `mediana_hsv` | média/mediana | H 0–179 | — | Cor | **H é circular** |
| `proporcao_verde` | fração na faixa | — | $[0,1]$ | Descritiva | **Circular com a segmentação** |

### Características descartadas, e por quê

| Descartada | Motivo |
|---|---|
| **Compacidade** $P^2/(4\pi A)$ | **Inverso exato da circularidade** — o mesmo número apresentado duas vezes. Decidido na Fase 1 |
| Textura | Sem hipótese formulada sobre o que revelaria |
| Contagem de bordas | Varia com limiar e ruído; não é descritor interpretável |
| Hu Moments, descritores de Fourier, embeddings | Fora do escopo; os dois últimos ampliariam o escopo sem pergunta que os justifique |

---

## 26. Performance

64 imagens, 1024×768.

| Etapa | Mediana | Mín | Máx |
|---|---:|---:|---:|
| Geometria (Fase 6) | 15,01 ms | 14,53 | 17,12 |
| **Cor** | **63,70 ms** | 19,79 | 100,96 |
| **Extração completa** | **70,17 ms** | 26,35 | 112,22 |

**A cor domina** — 64 dos 70 ms. A causa é o `cvtColor` da imagem inteira para HSV antes
de filtrar pela máscara. Converter só os pixels da máscara reduziria o custo, mas exigiria
reorganizar o array; **não foi otimizado**, porque 70 ms por imagem não é gargalo para o
uso previsto.

---

## 27. Limitações

| # | Limitação |
|---|---|
| 1 | **Circularidade tem teto em ≈0,90**, não 1,0, e deriva levemente com a escala |
| 2 | **Circularidade é ambígua** entre alongamento e recorte de borda |
| 3 | **Solidez também captura curvatura**, não só recorte — visível nas duas acículas (0,47 vs 0,77) |
| 4 | **Proporção de verde é circular** com a segmentação; quase constante por construção |
| 5 | **Média de H é válida só porque o matiz não cruza 0/179** neste dataset |
| 6 | **Razão P/P_hull tem referência em 1,05**, o que reduz sua interpretabilidade |
| 7 | **A escolha da área do contorno** introduz viés diferencial: −0,25% em folha larga, −4,13% em acícula |
| 8 | **Orientação frágil perto do limiar** — `1177` a 0,004 dele |
| 9 | **64 imagens de laboratório.** As distribuições valem para este conjunto, não para folhas em geral |
| 10 | **Cor depende de iluminação e balanço de branco**, não normalizados |
| 11 | **O pecíolo ausente** (R18) afeta área, perímetro, solidez e orientação |

---

## 28. Riscos atualizados

| # | Risco | Estado | Nota |
|---|---|---|---|
| **R14** | Perímetro digital | 🟢 **Medido e propagado** | §21 mostra o efeito em cada característica; teto de 0,90 fixado em teste |
| **R22** | Área poligonal ≠ raster | 🟢 **Medido e declarado** | As duas áreas são reportadas; escolha justificada na §4 |
| **R18** | Pecíolo ausente | 🟠 Aberto | Impacto declarado; não resolvido, por regra |
| **R19** | Faixa calibrada em folha verde sadia | 🟠 Aberto | Inalterado |
| **R20** | Preenchimento pode fechar perfuração real | 🟡 Aberto | Inalterado |
| **R23** | Orientação instável perto do limiar | 🟡 Aberto | `1177` a 0,004; recomendação explícita para a Fase 8 |
| **R24** 🆕 | **Proporção de verde é circular com a segmentação** | 🟡 Novo | Quase constante (0,98–0,9998); não é evidência de nada |
| **R25** 🆕 | **Solidez confunde recorte com curvatura** | 🟡 Novo | Acícula curvada dá 0,47; acícula reta, 0,77 |
| **R26** 🆕 | **Média de matiz quebra se a folha não for verde** | 🟡 Novo | H circular; vale para upload do usuário, não para o Flavia |

---

## 29. Próxima fase

**Fase 8 — Classificação morfológica por regras determinísticas.**

| # | Ação |
|---|---|
| 1 | Partir das distribuições da §3 a §19, **não de valores da literatura** |
| 2 | **Usar 0,90 como referência de círculo**, nunca 1,0 |
| 3 | **Combinar elongação + solidez** para separar alongado de recortado — a circularidade sozinha confunde os dois |
| 4 | **Exigir `anisotropia` junto de `orientacao_graus`** em qualquer regra |
| 5 | Verificar se a distribuição **sustenta** separação em classes — `null` é resultado aceitável |
| 6 | Se houver classes, derivar limiares do conjunto de desenvolvimento e registrar a amostra |
| 7 | Tratar casos de fronteira com aviso, não com certeza fabricada |
| 8 | Documentar em `08-CLASSIFICACAO.md` |

O conjunto de avaliação continua fechado.

---

*Fase 7 concluída em 20 de setembro de 2026, sobre o commit `060fff7`. 455 testes do
módulo e 256 asserções legadas, todos passando.*
