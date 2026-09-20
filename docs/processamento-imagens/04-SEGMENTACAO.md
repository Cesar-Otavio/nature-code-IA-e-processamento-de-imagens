# Fase 4 — Segmentação da folha

> **Escopo:** separar a folha do fundo, produzindo uma máscara binária. Comparação de
> estratégias clássicas sobre o conjunto de desenvolvimento, sem nenhuma operação
> morfológica aplicada ao resultado oficial.
>
> **Não implementado nesta fase:** morfologia definitiva, contorno final,
> características, classificação, pipeline, CLI, API, frontend.

---

## 1. Objetivo

Escolher, com evidência medida, a estratégia de segmentação que vai alimentar as fases
de morfologia e contornos.

O objetivo **não é máscara perfeita.** É uma máscara consistente o bastante para que a
Fase 5 trabalhe em cima dela. Artefato pequeno é problema da morfologia; folha perdida
ou objeto errado é problema da segmentação.

---

## 2. O problema

Dada uma imagem pré-processada, decidir para cada pixel: **folha** (255) ou **fundo** (0).

Três dificuldades, todas presentes no Flavia:

| Dificuldade | Manifestação |
|---|---|
| **Polaridade desconhecida** | Nenhuma limiarização sabe qual dos dois grupos é o objeto |
| **Sombra e reflexo** | Sombra é escura como a folha; reflexo é claro como o fundo |
| **Artefatos de captura** | Resíduos bege e pontos escuros no fundo, observados na Fase 2 |

---

## 3. Estratégias implementadas

Cada uma com hipótese declarada **antes** da medição.

| Estratégia | Hipótese | Ponto fraco previsto |
|---|---|---|
| **Otsu** | O histograma de intensidade tem dois modos separados; Otsu acha o limiar sem ninguém escolher valor | Decide por intensidade — sombra também é escura |
| **HSV** | A folha é verde, e o matiz é estável sob variação de brilho; fundo branco tem saturação ≈0 | Folha seca ou avermelhada fica fora da faixa |
| **Adaptativo** | Sob iluminação irregular nenhum limiar global serve; comparar com a vizinhança resolve | Em região grande e uniforme não há referência local |
| **Combinado (união)** | Folha é o que é escuro **ou** verde; recupera o que um método perde | Soma os falsos positivos dos dois |
| **Combinado (interseção)** | Folha é o que é escuro **e** verde; elimina sombra e reflexo | Perde o que qualquer um dos dois perder |

Otsu é a **linha de base honesta**: não tem parâmetro de cor para ajustar, então as
outras precisam se justificar contra ele.

---

## 4. Conjunto de desenvolvimento

| | |
|---|---|
| Origem | Flavia completo — 1.907 imagens baixadas da fonte oficial |
| Seleção | Aleatória **estratificada por espécie** |
| Semente | **`20260919`** |
| Desenvolvimento | **64 imagens** (2 por espécie × 32) |
| Avaliação | 96 imagens (3 por espécie) — **não tocado nesta fase** |
| Disjunção | Verificada por construção: `True` |

Gerado por `selecionar_subconjunto.py`, versionado, com a tabela de faixas
espécie→arquivo publicada em http://flavia.sourceforge.net/ (consultada em 19/09/2026).

**Validação cruzada da tabela:** a soma das faixas cobriu exatamente **1.907** arquivos
existentes — o mesmo número que a literatura atribui ao dataset. Se a transcrição
tivesse erro, a contagem não fecharia.

O manifesto `dataset/manifesto.csv` é versionado; as imagens, não.

---

## 5. Metodologia

```
1. baixar o dataset completo
2. sortear dev (64) e avaliação (96), disjuntos, semente fixa
3. medir a distribuição real de H, S, V nos pixels de folha  ← evidência, não chute
4. derivar faixas candidatas dos percentis medidos
5. comparar as faixas entre si no conjunto de desenvolvimento
6. comparar as 5 estratégias × 3 filtros = 15 combinações
7. inspecionar visualmente as 64 máscaras da melhor combinação
8. classificar por protocolo definido antes da inspeção
```

**O conjunto de avaliação não foi aberto em nenhuma etapa.**

---

## 6. Distribuição de cor medida

Para medir a cor da folha sem já assumir que ela é verde, a região foi delimitada por
**Otsu** — que decide por intensidade, não por cor. Só então H, S e V foram medidos
dentro dessa região.

**16.220.932 pixels de folha**, nas 64 imagens de desenvolvimento:

| Canal | p1 | p5 | p25 | **mediana** | p75 | p95 | p99 |
|---|---:|---:|---:|---:|---:|---:|---:|
| **H** (0–179) | 43 | 46 | 50 | **53** | 55 | 60 | 67 |
| **S** (0–255) | 82 | 112 | 148 | **173** | 201 | 253 | 255 |
| **V** (0–255) | 51 | 93 | 133 | **152** | 173 | 213 | 233 |

Mediana de H **por imagem**: mínimo 46, mediana 53, máximo 60. Nenhuma das 64 imagens
tem mediana de matiz fora de [25, 95].

> O matiz é **notavelmente concentrado**: 98% dos pixels de folha estão entre H=43 e
> H=67, em 32 espécies diferentes. Confirma, com amostra de verdade, o sinal observado
> em três imagens na Fase 3.

---

## 7. Calibração da faixa HSV — um achado contraintuitivo

Quatro faixas candidatas, derivadas dos percentis, comparadas no conjunto de
desenvolvimento:

| Faixa | frac med | comp med | **comp máx** | **domin mín** | IoU vs Otsu |
|---|---:|---:|---:|---:|---:|
| **A** justa, p1–p99 (H 43–67, S≥82, V≥51) | 0,311 | 1 | **409** | 0,9462 | 0,9880 |
| **B** margem 50% (H 30–80, S≥50, V≥40) | 0,321 | 1 | 159 | 0,9853 | 0,9843 |
| **C** ampla (H 25–95, S≥40, V≥20) | 0,323 | 1 | **3** | **0,9996** | 0,9816 |
| **D** H largo, S alto (H 25–95, S≥70) | 0,320 | 1 | 83 | 0,9898 | 0,9876 |

### A faixa mais justa é a pior

Parece errado, e não é. A faixa A foi derivada **dos próprios percentis dos pixels de
folha** — deveria ser a mais precisa. Ela fragmenta a máscara em até **409
componentes**, contra 3 da faixa ampla.

**Por quê.** A faixa justa recorta pixels *de dentro* da folha. Nervuras, bordas,
regiões com brilho especular e áreas em sombra têm matiz ou saturação ligeiramente
deslocados — e caem fora de um intervalo apertado, abrindo buracos e cortando a máscara
em pedaços.

**E por que a ampla não traz o fundo junto.** Porque quem separa folha de fundo branco
**não é o matiz — é a saturação mínima**. O fundo do Flavia tem S≈0. Ampliar a faixa de
H não aproxima o fundo do critério; apenas para de recortar o interior da folha.

> **O papel de cada canal, medido:**
> `S_min` separa objeto de fundo. A faixa de `H` exclui objetos coloridos que não sejam
> verdes. Confundir os dois papéis leva a apertar o parâmetro errado.

A comparação D confirma: subir `S_min` de 40 para 70 piora (comp máx de 3 para 83),
porque começa a recortar regiões menos saturadas da própria folha.

**Faixa adotada: C** — `H ∈ [25, 95]`, `S ≥ 40`, `V ≥ 20`.

---

## 8. Comparação das estratégias

15 combinações (5 estratégias × 3 tratamentos de ruído), 64 imagens cada.

| Estratégia | Filtro | frac med | frac máx | comp med | **comp máx** | **domin med** | **domin mín** | borda | ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| otsu | sem | 0,317 | 0,529 | 3 | 470 | 1,0000 | 0,9949 | 0 | 28,5 |
| otsu | gauss | 0,317 | 0,530 | 1 | 66 | 1,0000 | 0,9981 | 0 | 28,3 |
| otsu | mediana | 0,317 | 0,529 | 1 | 35 | 1,0000 | 0,9976 | 0 | 29,6 |
| **hsv** | sem | 0,322 | 0,545 | 1 | 18 | 1,0000 | 0,9996 | 0 | 20,8 |
| **hsv** | **gauss** | **0,323** | 0,545 | **1** | **3** | **1,0000** | **0,9996** | **0** | **23,0** |
| hsv | mediana | 0,322 | 0,545 | 1 | 12 | 1,0000 | 0,9996 | 0 | 27,2 |
| adaptativo | sem | 0,107 | 0,228 | 3454 | 7931 | 0,4794 | 0,1207 | 13 | 57,3 |
| adaptativo | gauss | 0,086 | 0,210 | 922 | 2148 | 0,5742 | 0,1569 | 11 | 51,4 |
| adaptativo | mediana | 0,079 | 0,201 | 648 | 1389 | 0,5992 | 0,1716 | 12 | 52,1 |
| união | gauss | 0,323 | 0,545 | 1 | 5 | 1,0000 | 0,9996 | 0 | 66,0 |
| interseção | gauss | 0,317 | 0,530 | 1 | 66 | 1,0000 | 0,9981 | 0 | 66,2 |

### Leitura

**HSV + Gaussiano vence em todos os indicadores relevantes.** Máximo de 3 componentes
contra 66 do Otsu; dominância mínima 0,9996 contra 0,9981; e ainda é mais rápido.

**Otsu é sólido, mas inferior.** Sem filtro chega a 470 componentes. Com Gaussiano cai
para 66 — ainda 22× pior que o HSV.

**Adaptativo falha por completo.** Fração mediana de 0,079–0,107 quando a real é ~0,32:
**perde cerca de 70% da folha**. Até 7.931 componentes. Dominância de 0,12. E acusa 11
a 13 imagens tocando a borda, quando **nenhuma toca**. O ponto fraco previsto na §3 se
confirmou com margem enorme.

**As combinações não agregam nada.** União ≡ HSV e interseção ≡ Otsu, com o **triplo do
custo** (66 ms contra 23 ms). O motivo é estrutural e vale registrar: neste dataset a
máscara de Otsu está **contida** na de HSV, então `A∪B = B` e `A∩B = A`. Combinar duas
máscaras aninhadas não produz informação nova.

---

## 9. Polaridade

Nenhuma limiarização sabe qual lado é o objeto. `THRESH_BINARY` marca como 255 o que
está **acima** do limiar — que no Flavia é o fundo branco, não a folha.

Dois critérios implementados e testados:

| Critério | Premissa | Falha quando |
|---|---|---|
| **`borda`** (padrão) | A moldura do quadro é fundo | O objeto toca a borda em toda a volta |
| `ocupacao` | O objeto ocupa menos da metade | O objeto é maior que o fundo |

**O caso que separa os dois**, verificado por teste: objeto central ocupando 64% da
imagem, com borda limpa. Pelo critério de ocupação seria invertido por engano; pelo de
borda, não. Daí `borda` ser o padrão.

Dois testes pareados fixam o comportamento: objeto escuro sobre branco →
`invertida=True`; objeto claro sobre escuro → `invertida=False`. **Em ambos o objeto
termina como 255.** A polaridade é decidida pela cena, não fixada no código.

> **Correção registrada.** A primeira versão do teste esperava `invertida=True` também
> no caso claro-sobre-escuro. O código estava certo e o teste, errado: com
> `THRESH_BINARY`, o objeto claro já sai como 255. O teste foi corrigido e a explicação
> ficou na docstring — é justamente o que ele deve documentar.

---

## 10. Filtros

| Filtro | comp máx (Otsu) | comp máx (HSV) |
|---|---:|---:|
| sem filtro | 470 | 18 |
| **Gaussiano** | 66 | **3** |
| mediana | 35 | 12 |

**Gaussiano escolhido**, por qualidade de máscara — não por velocidade. Ele dá o melhor
resultado com HSV (3 contra 12 da mediana). A diferença de tempo entre os dois é de
4 ms e **não pesou na decisão**.

Curiosamente a mediana é melhor **com Otsu** (35 contra 66), mas isso é irrelevante:
Otsu não é a estratégia escolhida.

### Um achado dos testes sintéticos

Com ruído impulsivo preto-e-branco, **Otsu produz 1.943 componentes e o HSV produz 1**.

Ruído impulsivo é preto ou branco puro — **saturação zero**. Como o HSV exige matiz na
faixa *e* saturação mínima, esses pixels simplesmente não entram. Otsu, decidindo só por
intensidade, inclui todos.

Não estava previsto no planejamento, e é uma vantagem estrutural do HSV neste tipo de
cena. Está fixado em `test_hsv_e_praticamente_imune_a_ruido_preto_e_branco`.

---

## 11. Métricas de triagem

Implementadas em `analisar_mascara()`. **Não são medida de acerto** — não há ground
truth no Flavia. Apontam máscaras suspeitas, que merecem ser olhadas.

| Métrica | O que revela |
|---|---|
| `fracao_foreground` | Máscara quase vazia ou dominando o quadro |
| `n_componentes` | Fragmentação |
| `dominancia_maior_componente` | Quanto do objeto está no maior pedaço |
| `toca_borda` | Objeto provavelmente cortado |
| `bbox_preliminar` | Caixa envolvente do maior componente |

### Distribuição observada — HSV + Gaussiano, 64 imagens

| Métrica | p5 | mediana | p95 | mín | máx |
|---|---:|---:|---:|---:|---:|
| `fracao_foreground` | 0,119 | **0,323** | 0,513 | 0,027 | 0,545 |
| `dominancia` | 1,0000 | **1,0000** | — | **0,9996** | 1,0000 |
| `n_componentes` | — | **1** | — | 1 | **3** |
| `toca_borda` | — | — | — | **0 imagens** | — |

### Limiares de suspeita — experimentais, derivados desta distribuição

| Aviso | Critério | Justificativa |
|---|---|---|
| `foreground_quase_vazio` | `fracao < 0,02` | Abaixo do mínimo observado (0,027) |
| `foreground_domina` | `fracao > 0,60` | Acima do máximo observado (0,545) |
| `muitos_componentes` | `n_componentes > 5` | Acima do máximo observado (3) |
| `pouco_dominante` | `dominancia < 0,99` | Abaixo do mínimo observado (0,9996) |
| `toca_borda` | verdadeiro | Nenhuma imagem do dev set toca |

**Todos marcados como experimentais.** Foram calibrados no conjunto de desenvolvimento e
ainda não foram validados contra o de avaliação.

---

## 12. Protocolo de classificação manual

Critérios fixados **antes** de olhar as máscaras.

| Categoria | Critério |
|---|---|
| 🟢 **Correta** | A máscara cobre a folha inteira; a borda acompanha o contorno real; sem buraco interno relevante; **um único componente**; sem inclusão de fundo, sombra ou artefato |
| 🟡 **Aceitável** | A folha está essencialmente correta, com desvio pequeno e localizado — artefato isolado ou pequena falha de borda —, **sem comprometer a geometria principal**. As medidas continuam utilizáveis, com ressalva |
| 🔴 **Falha** | Objeto errado selecionado · parte significativa da folha perdida · sombra ou fundo incorporados · máscara fragmentada · nenhum objeto detectado |

Inspeção feita em quatro mosaicos de 16 imagens, com contorno desenhado sobre a
original, mais pares `original | máscara` em tamanho cheio para os casos apontados pela
triagem.

---

## 13. Resultado no conjunto de desenvolvimento

### HSV + Gaussiano

| Categoria | Imagens | Proporção |
|---|---:|---:|
| 🟢 Correta | **52** | 81,3% |
| 🟡 Aceitável | **12** | 18,8% |
| 🔴 **Falha** | **0** | **0%** |

As 12 "aceitáveis" são as que têm mais de um componente. **Todos os artefatos são
minúsculos:**

| Imagem | Componentes | Área fora do maior |
|---|---:|---|
| `3287.jpg` | 2 | ~74 px (0,035%) |
| `3306.jpg` | 3 | ~72 px (0,027%) |
| `2233.jpg` | 2 | ~10 px |
| `2078.jpg` | 3 | ~11 px |
| demais (8) | 2 | 3 a 10 px |

O maior artefato do conjunto tem **74 pixels** numa folha de ~145.000. Uma abertura
morfológica de kernel pequeno os elimina — que é exatamente o trabalho da Fase 5.

### Otsu + Gaussiano, para comparação

22 das 64 imagens com mais de um componente, e os artefatos são **uma ordem de grandeza
maiores**: `3430.jpg` com **65 componentes** e ~687 px fora do maior; `3436.jpg` com 64
componentes.

Essas duas são justamente as folhas **mais brilhantes** do conjunto. O reflexo especular
cria manchas claras que Otsu classifica como fundo, abrindo buracos na máscara. **No HSV
as duas saem com 1 componente** — o brilho reduz a saturação mas não muda o matiz o
bastante para sair da faixa.

---

## 14. Casos difíceis

| Caso | Imagem | Condição | Resultado HSV + gauss |
|---|---|---|---|
| **Acícula estreita** | `2400`, `2407` | Objeto finíssimo; fração 0,027 e 0,031 — as menores do conjunto | 🟢 **Correta.** Contorno completo, 1 componente. A triagem as apontou por fração baixa; a inspeção mostrou que **fração baixa ≠ falha**: o objeto é pequeno de verdade |
| **Reflexo especular forte** | `3430`, `3436` | Folhas brilhantes | 🟢 **Correta** no HSV (1 componente). **Otsu falha**: 65 e 64 componentes |
| **Folha larga** | `2497` | Maior fração do conjunto (0,545) | 🟡 **Aceitável.** Máscara quase perfeita, mas o **pecíolo marrom foi parcialmente perdido** — está fora da faixa de verde |
| **Folha alongada** | `1007`, `2562`, `2620` | Razão comprimento/largura alta | 🟢 **Correta** |
| **Caso fácil** | `1101`, `2047` | Folha oval, fundo limpo | 🟢 **Correta** |
| **Borda lobada** | `1307`, `1322`, `3287` | Bordo japonês, lobos profundos e pontas finas | 🟢 **Correta.** O contorno acompanha cada lóbulo |
| **Borda espinhosa** | `3363`, `3373` | Mahonia | 🟢 **Correta** |
| **Forma peculiar** | `2480`, `2485` (ginkgo), `3525` (tulipeira) | Leque com borda ondulada; forma truncada | 🟢 **Correta** |

### O pecíolo — limitação real, encontrada por inspeção

Em folhas cujo pecíolo é marrom ou bege, a segmentação por HSV **o descarta**, porque
ele não é verde. Visível em `2497.jpg`.

Consequência: **perímetro e solidez mudam** conforme o pecíolo entre ou não na máscara.
Não é defeito da implementação — é o método fazendo exatamente o que foi pedido. Precisa
ser **declarado** na documentação das características (Fase 6), porque parte da
literatura de morfologia foliar mede com pecíolo e parte sem.

---

## 15. Estratégia escolhida

> ## 🌿 **HSV + filtro Gaussiano (kernel 5)**
> Faixa `H ∈ [25, 95]`, `S ≥ 40`, `V ≥ 20`

### Evidência que sustenta a escolha

| Critério | HSV+gauss | Otsu+gauss | Adaptativo+gauss |
|---|---:|---:|---:|
| Máximo de componentes | **3** | 66 | 2.148 |
| Dominância mínima | **0,9996** | 0,9981 | 0,1569 |
| Imagens com >1 componente | **12/64** | 22/64 | 64/64 |
| Maior artefato | **74 px** | 687 px | — |
| Falhas na inspeção | **0/64** | — | — |
| Fração mediana | 0,323 | 0,317 | 0,086 ❌ |
| Falsos "toca borda" | **0** | 0 | 11 |
| Tempo mediano | **23,0 ms** | 28,3 ms | 51,4 ms |

Vence em **todos** os critérios de qualidade, e também em tempo — o que aqui é apenas
conveniente, não argumento.

### Razões estruturais, além dos números

1. **Separa por cor, não por brilho.** Sombra e reflexo alteram a intensidade sem
   alterar muito o matiz. É o que faz `3430` e `3436` funcionarem.
2. **Imune a ruído impulsivo**, por exigir saturação mínima (§10).
3. **Resiste a gradiente de iluminação**, verificado em cena sintética.

---

## 16. Fallback

**Nenhum fallback será implementado nesta fase.**

A cascata `HSV → se suspeita → Otsu` foi considerada e **descartada por falta de
evidência de benefício**:

1. **Não houve caso em que o HSV falhasse** e o Otsu acertasse — 0 falhas em 64;
2. **Otsu é pior onde o HSV é fraco**: nas folhas brilhantes, o HSV dá 1 componente e o
   Otsu dá 65;
3. **As máscaras são aninhadas** (Otsu ⊆ HSV neste dataset), então o fallback trocaria a
   máscara maior por uma menor — perderia informação, não recuperaria;
4. Acrescentaria caminho de código não exercitado.

> Cascata sem evidência é complexidade disfarçada de robustez.

**Quando reconsiderar:** o ponto fraco declarado do HSV é folha **não verde** — seca,
avermelhada ou variegada. O Flavia não tem esses casos. Se aparecerem no conjunto
próprio de robustez proposto na Fase 2, o fallback passa a ter justificativa. A decisão
fica registrada como reavaliável, não como encerrada.

---

## 17. Parâmetros experimentais

| Parâmetro | Valor | Origem |
|---|---|---|
| `FAIXA_VERDE_EXPERIMENTAL` | H [25,95], S [40,255], V [20,255] | **Calibrada** — §7, 4 candidatas comparadas |
| Filtro | Gaussiano, kernel 5 | **Escolhido** — §10, por qualidade de máscara |
| `ESPESSURA_BORDA_PX` | 5 | Experimental, não comparado com alternativas |
| `bloco` adaptativo | 51 | Irrelevante — estratégia descartada |
| Limiares de suspeita | §11 | Experimentais, calibrados só no dev set |

---

## 18. Limitações

| # | Limitação |
|---|---|
| 1 | **Validado apenas em condição de laboratório.** Fundo branco uniforme é o melhor caso; nada aqui demonstra desempenho em foto de celular sobre grama |
| 2 | **A faixa de verde exclui folha não verde**, por construção. Seca, avermelhada ou variegada ficaria de fora |
| 3 | **O pecíolo não verde é descartado** (§14), o que altera perímetro e solidez |
| 4 | **Sem ground truth**, a avaliação é inspeção protocolada, não IoU |
| 5 | **64 imagens.** Suficiente para escolher entre estratégias; insuficiente para afirmar taxa de acerto |
| 6 | **Os limiares de suspeita não foram validados** fora do conjunto onde foram calibrados |
| 7 | **Nenhuma máscara foi limpa.** Os números são de máscara bruta — a Fase 5 deve melhorá-los |
| 8 | **Adaptativo descartado com um só par de parâmetros.** Outro `bloco` poderia ir melhor; mas com fração mediana de 0,086 contra 0,32, a distância torna a reavaliação pouco promissora |

---

## 19. Riscos atualizados

| # | Risco | Estado | Nota |
|---|---|---|---|
| **R6** | Segmentação depende de contraste | 🟢 **Resolvido para o Flavia** | 0 falhas em 64; dominância mínima 0,9996 |
| **R7** | Limiares arbitrários | 🟢 **Mitigado** | Faixa HSV calibrada em 16,2 M de pixels e 4 candidatas comparadas; limiares de suspeita derivados da distribuição |
| **R3** | Tamanho do repositório | 🟢 **Validado** | 1,1 GB de imagens no disco, **0 bytes no Git** |
| **R14** | Perímetro digital | 🟠 Aberto | Fase 6 |
| **R16** | Alfa e EXIF | 🟡 Aberto | Não afeta o Flavia |
| **R18** 🆕 | **Pecíolo não verde é descartado** | 🟡 Novo | §14. Declarar na documentação das características |
| **R19** 🆕 | **Faixa calibrada só em folha verde e sadia** | 🟠 Novo | O dataset não tem folha seca ou variegada; o método não foi exposto a esse caso |

---

## 20. Próxima fase

**Fase 5 — Morfologia.**

| # | Ação |
|---|---|
| 1 | Implementar `morphology.py`: abertura, fechamento, preenchimento de buracos |
| 2 | **Alvo concreto:** eliminar os artefatos de 3 a 74 px das 12 imagens "aceitáveis" |
| 3 | Comparar tamanhos de kernel no conjunto de desenvolvimento |
| 4 | Medir se a abertura leva 12/64 para 0/64 com mais de um componente |
| 5 | **Verificar que a morfologia não distorce o contorno** — kernel grande arredonda a borda e altera perímetro e circularidade |
| 6 | Registrar par antes/depois de cada operação, como evidência visual |
| 7 | Documentar em `05-MORFOLOGIA.md` |

O conjunto de avaliação continua fechado.

---

*Fase 4 concluída em 19 de setembro de 2026, sobre o commit `0f65ae3`. 209 testes do
módulo e 256 asserções legadas, todos passando.*
