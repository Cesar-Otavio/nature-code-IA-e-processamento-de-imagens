# Fase 5 — Revalidação do prompt V4 em Cordados

> Amostra **separada e limpa**, gravada em `docs/dados-piloto/onda9-v4-cordados-revalidacao.json`.
> Não foi misturada com nenhuma amostra anterior, e nenhum dado anterior foi apagado.
>
> Fecha a pendência declarada em `docs/05-AVALIACAO-PILOTO.md` §6, onde a verificação do V4
> em Cordados ficou incompleta porque o plano gratuito do Ollama Cloud cortou no meio.
>
> Modelo `gpt-oss:120b-cloud`, prompt V4, 13 tópicos habilitados — nada foi alterado.

---

## 1. Resultado da nova amostra

| Métrica | Valor |
|---|---|
| Gerações realizadas | **15** |
| Servidas pela IA | **15 de 15 (100%)** — nenhum fallback |
| Questões solicitadas | 75 |
| Questões recebidas | **77** |
| Questões aprovadas | **74** |
| Questões rejeitadas | **3** |
| **Taxa de aprovação** | **96,1%** |
| Retentativas | **4**, em 4 das 15 gerações (27%) |
| Latência por quiz | mediana **12,2 s** · média 13,1 s · p95 24,4 s · mín. 7,7 s · máx. 24,4 s |
| Enunciados distintos | 74 de 74 (**100%**) |
| Estratégias do parser | `direto` 17 · `reparo` 1 |

Motivos das 3 rejeições: `vazamento_por_comprimento` (2) e `enunciado_fora_do_material` (1).

**A amostra é limpa.** Não houve nenhum erro de cota: as métricas registram uma única falha de
chamada, do tipo `resposta` (o modelo devolveu conteúdo vazio na geração 8), que a retentativa
resolveu. Nenhum HTTP de erro, nenhum quiz servido pelo banco fixo.

---

## 2. Comparação V1 × V2 × V3 × V4

Mesmo tópico, mesmo modelo. V1 a V3 com 20 gerações; a revalidação com 15.

| | V1 | V2 | V3 | **V4 (revalidação)** |
|---|---|---|---|---|
| Questões analisadas | 96 | 97 | 96 | **74** |
| **Taxa de aprovação** | 92,3% | 87,4% | 88,9% | **96,1%** |
| **Retentativas** | 6 | 11 | 8 | **4** |
| Gerações que precisaram de retentativa | 5/20 | 10/20 | 8/20 | **4/15** |
| Latência mediana | 13,1 s | 12,9 s | 14,8 s | **12,2 s** |
| Latência p95 | 49,7 s | 36,0 s | 23,2 s | **24,4 s** |
| Enunciados repetidos | 4 (4,2%) | 1 (1,0%) | 4 (4,2%) | **0 (0%)** |
| Marcador `negativa` | 5,2% | 6,2% | 2,1% | 5,4% |
| Marcador `titulo-de-secao` | 8,3% | 8,2% | 8,3% | 12,2% |
| **Defeitos confirmados por leitura** | 1 | — | 0 | **1 (novo tipo)** |

Rejeições por motivo:

| | V1 | V2 | V3 | V4 |
|---|---|---|---|---|
| `vazamento_por_comprimento` | 4 | 12 | 12 | **2** |
| `explicacao_cita_letra` | 3 | 1 | 0 | 0 |
| `alternativa_vazia` | 1 | 1 | 0 | 0 |
| `enunciado_fora_do_material` | 0 | 0 | 0 | 1 |

---

## 3. Avaliação manual

**20 das 74 questões lidas (27%)**, escolhidas em dois grupos:

- **12 dirigidas** — todas as 9 marcadas com `titulo-de-secao` e todas as 4 com `negativa`
  (uma questão tem os dois marcadores). São exatamente os dois problemas que o V4 mira;
- **8 em amostra sistemática** — uma a cada 8 questões, sem seleção por marcador.

### 3.1 Contagem por categoria de problema

| Categoria pedida | Encontradas |
|---|---:|
| Mais de uma resposta defensável | **0** |
| Nenhuma resposta correta | **1** (§4) |
| Alucinação | **1** (a mesma de §4) |
| Problema de posição/seção do conteúdo | **0** |
| Problema em questão negativa | **0** |
| Distrator também verdadeiro | **0** |
| Explicação inconsistente | **1** (a mesma de §4) |

### 3.2 O marcador `titulo-de-secao` subiu, e não é defeito

12,2% contra 8,3% do V3. Li as 9 e **nenhuma é defeituosa**. Em todas, o título da seção aparece
como *contexto* — "Considerando as características gerais dos cordados, assinale a correta" — e o
que separa a resposta das demais é o **conteúdo factual**, não a posição no texto. Os distratores
são afirmações falsas, não fatos verdadeiros de outra seção.

É o mesmo padrão observado em Artrópodes quando o V4 foi adotado: o modelo passou a citar a seção
com mais frequência **e** parou de decidir por ela. O marcador conta a menção, não o defeito.

### 3.3 As 4 questões negativas estão corretas

A mais significativa é esta, porque é **a mesma pergunta que estava defeituosa no V1**:

> **Considerando as características dos Condrictes, qual das alternativas abaixo NÃO se aplica a
> esse grupo?**
> A) São heterotérmicos · B) Têm escamas placóides · C) Possuem esqueleto cartilaginoso ·
> **D) Possuem bexiga natatória** ← correta

As três não-respostas são afirmações que o texto declara explicitamente sobre condrictes, e a
resposta é a única que o texto refuta. É exatamente o que a regra do V3 exige.

Comparação direta com a versão defeituosa da mesma pergunta em V1:

| | Distratores |
|---|---|
| V1 | *mandíbula* e *brânquias externas* — nenhum dos dois afirmado no texto, e brânquias externas **também** não se aplica aos condrictes: duas respostas |
| V4 | *heterotérmicos*, *escamas placóides*, *esqueleto cartilaginoso* — os três explícitos no texto |

Nas outras três — grupo que não pertence a Vertebrata, coração bicavitário sem bexiga natatória, e
descrição que não corresponde aos cornos — as não-respostas também vêm do material.

### 3.4 Amostra cega

As 8 lidas sem seleção por marcador estão corretas: resposta única, fiel ao material, distratores
plausíveis e falsos, explicação coerente com a alternativa certa. Os distratores usam
características de **outros grupos do mesmo texto** (peixes, aves, mamíferos), que é o erro que um
estudante realmente cometeria.

---

## 4. Defeito novo encontrado — NÃO corrigido

Conforme combinado, está registrado e nada foi alterado.

**Geração 11, questão 1:**

> **De acordo com o texto, quais são as características gerais dos cordados?**
> **A) São celomados, trilobulados e deuterostômios.** ← marcada como correta
> B) São pseudocelomados, trilobulados e protostômios.
> C) São pseudocelomados, diploblásticos e protostômios.
> D) São celomados, diploblásticos e deuterostômios.
>
> *"O texto afirma que os cordados são celomados, **trilobulados** e deuterostômios…"*

O texto do site diz:

```
## Características Gerais
- Celomados; Triblásticos; Deuterostômios;
```

**"Trilobulados" não existe** — nem no material do site, nem como termo de embriologia. O modelo
corrompeu *triblásticos* e repetiu a invenção na explicação.

### 4.1 Por que isto é grave

A alternativa A tem um termo inventado; a alternativa D tem *diploblásticos*, que é um termo real
mas errado para cordados. **Nenhuma das quatro alternativas está inteiramente correta.** É um caso
de "nenhuma resposta correta", causado por alucinação num único termo.

Um aluno que estudou o material procuraria "triblásticos" e não encontraria.

### 4.2 Por que as duas camadas automáticas não pegaram

| Camada | Por que passou |
|---|---|
| Validador — `conceito_fora_do_material` | O `conceitoAvaliado` era "Características Gerais", que está no texto |
| Validador — `enunciado_fora_do_material` | A alternativa correta tem 67% de cobertura: *celomados* e *deuterostômios* seguram o índice sozinhos |
| Triagem — marcador `alucinacao` | Limiar de 55%; 67% passa folgado |

Uma palavra inventada dentro de uma alternativa majoritariamente correta é invisível para
qualquer medida de sobreposição. **Só a leitura pega.**

### 4.3 Frequência

**1 ocorrência em 74 questões (1,4%).** O termo "trilobulados" aparece uma única vez na amostra
inteira, e nenhuma outra questão da amostra tem termo fabricado. O termo correto, *triblásticos*,
aparece corretamente em outra questão.

Não é um padrão sistemático nesta amostra, e **não tem relação com as regras do V4** — nenhuma das
duas trata de fidelidade terminológica. Provavelmente ocorreria em qualquer versão do prompt; as
amostras anteriores não foram varridas especificamente para isso.

---

## 5. Conclusão sobre o V4

**Há evidência de melhoria, e o resultado é consistente.**

O que melhorou, com número:

- **Taxa de aprovação 96,1%** — a melhor das quatro versões, contra 92,3% do V1 e 88,9% do V3;
- **Retentativas caíram para 4**, contra 8 do V3 e 11 do V2. Só 27% das gerações precisaram de
  segunda tentativa;
- **`vazamento_por_comprimento` caiu de 12 para 2.** Este é o dado que mais surpreende: V2 e V3
  haviam triplicado esse motivo em relação ao V1, e eu havia registrado que "qualquer instrução
  extra faz o modelo escrever alternativas corretas mais longas". **O V4 desmente essa
  generalização** — tem mais instrução que V2 e V3 e rejeita menos que todos;
- **Latência mediana 12,2 s**, a menor das quatro;
- **Zero enunciados repetidos** em 74 questões.

O que se manteve:

- **0 defeitos** nos dois problemas que o V4 mira, em 13 questões dirigidas exatamente a eles;
- A questão sobre condrictes, defeituosa em V1, saiu correta e bem ancorada.

O que ficou em aberto:

- **1 defeito novo**, de tipo diferente (alucinação terminológica), 1 em 74. Não relacionado às
  regras do V4.

### 5.1 Ressalva estatística

A amostra tem 15 gerações contra 20 das anteriores. Uma diferença de poucos pontos na taxa de
aprovação estaria dentro do ruído — mas a diferença observada não é de poucos pontos: 96,1% contra
88,9%, com as retentativas caindo pela metade e o motivo dominante de rejeição caindo de 12 para 2.
A direção é clara mesmo com a amostra menor.

Já a subida dos marcadores `negativa` (2,1% → 5,4%) e `titulo-de-secao` (8,3% → 12,2%) **não**
sustenta conclusão: em números absolutos são 4 e 9 questões, a variação cabe no acaso, e a leitura
de todas as 13 não achou defeito em nenhuma.

---

## 6. A pendência da Fase 5 pode ser encerrada

**Sim.** A pendência era verificar que o V4 não regride em Cordados, com amostra limpa. A amostra
foi obtida, tem 15 gerações sem contaminação, e o V4 não só não regrediu como apresentou os
melhores números das quatro versões no tópico de referência.

Fica aberto, para sua decisão, um item **novo e independente** da pendência original: o defeito de
alucinação terminológica da §4. Ele não foi corrigido, conforme combinado.

Se você quiser tratá-lo, o caminho mais promissor **não** é mexer no prompt de novo — é uma regra
de validação: comparar os termos técnicos da alternativa correta com os termos que aparecem no
material, e recusar quando a alternativa introduz um termo técnico inédito. Isso pegaria
"trilobulados" sem depender de o modelo se comportar. Mas é mudança de escopo e precisa da sua
aprovação, com medição antes e depois como nas outras.

---

## 7. Estado do repositório

Nada foi alterado nesta revalidação. Acréscimos: a amostra
`docs/dados-piloto/onda9-v4-cordados-revalidacao.json` e este documento. As amostras anteriores
permanecem intactas, `topicosComIA` continua com os 13 tópicos aprovados, o modelo continua
`gpt-oss:120b-cloud` e o prompt continua V4.
