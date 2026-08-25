# Fase 6 — Benchmark Cloud × Local: protocolo

> **Estado: infraestrutura pronta, benchmark NÃO executado.**
> Nenhum modelo foi baixado, nenhuma geração local foi feita, `config-ia.js` está intacto.
>
> A execução acontece no PC de mesa, seguindo `docs/06b-GUIA-PC-MESA.md`.
>
> Ponto de restauração: tag **`fase-5-completa`** no commit `8a85e29`.

---

## 1. A pergunta da fase

O roteiro do trabalho manda usar o parâmetro `format` com JSON Schema e proíbe pedir JSON
só no texto do prompt. Na Fase 2 ficou medido que **isso não funciona na nuvem**: modelos
`:cloud` são repassados pelo daemon para ollama.com, e a restrição por gramática — que é
aplicada pelo runner local — não chega lá.

Ou seja: o mecanismo correto de saída estruturada só existe rodando o modelo localmente.
A Fase 6 responde se vale a troca, e a que custo.

Três perguntas, nesta ordem:

1. Um modelo pequeno rodando em CPU produz questões de qualidade comparável ao
   `gpt-oss:120b-cloud`?
2. Quanto o JSON Schema melhora a confiabilidade do formato?
3. A latência local é aceitável para uso na apresentação?

---

## 2. Os três braços

Uma variável experimental por comparação. É a lição da Fase 5, onde eu recusei o prompt V2
por tê-lo medido num tópico em que o defeito-alvo não ocorria.

| Braço | Provedor | Modelo | Schema | Isola |
|---|---|---|---|---|
| **A** | cloud | `gpt-oss:120b-cloud` | não (a nuvem ignora) | referência |
| **B** | local | `qwen3.5:4b` | **não** | o **modelo** — prompt idêntico ao A |
| **C** | local | `qwen3.5:4b` | **sim** | o **JSON Schema** — mesmo modelo do B |

**Por que o braço B existe.** Sem ele, comparar Cloud com Local mudaria modelo *e* prompt
ao mesmo tempo: quando `suportaSchema` é `true`, a camada **remove do prompt** o bloco de
instrução de JSON (457 caracteres, medidos), porque o schema passa a garantir o formato.
A comparação ficaria sem causa única.

- **A × B** → mesmo prompt, modelos diferentes. Mede o modelo.
- **B × C** → mesmo modelo, prompt diferindo só no bloco de JSON. Mede o schema.

---

## 3. Integridade da comparação, verificada e não prometida

O script calcula o **SHA-256** do conjunto exato de mensagens enviado ao modelo e compara
os braços A e B, tópico a tópico. **Se divergirem, o benchmark para.** Uma comparação
inválida não continua em silêncio.

Conferência atual, sem usar rede:

```
tópico              | braço A (cloud)  | braço B (local)  | iguais? | braço C (schema)
filo-cordados       | db375a6d56ce20aa | db375a6d56ce20aa |   SIM   | e16eb4ff994e35b2
                    |             9263 |             9263 |        |             8806  (schema tira 457 car.)
filo-artropodes     | cb4a0cf2ab501387 | cb4a0cf2ab501387 |   SIM   | 386ae8402b4332ca
filo-moluscos       | 8138669732d7489c | 8138669732d7489c |   SIM   | 81213474fc62e404
```

```bash
node scripts/benchmark-fase6.js --verificar-prompts
```

O hash não é calculado à parte: o script **intercepta `PromptQuiz.montarMensagens`** dentro
do contexto de execução e registra o hash de cada prompt que realmente saiu, inclusive nas
retentativas. A interceptação vive só em memória — nenhum arquivo do projeto é alterado.

### O que fica idêntico entre os braços

| | Como é garantido |
|---|---|
| Base de conhecimento | `dados/base-conhecimento.js`, intocado desde a Fase 1 |
| Prompt | V4, o mesmo dos 13 tópicos habilitados. `versaoPrompt` fixado em V4 pelo script |
| Validador | `validador-quiz.js` sem alteração, mesmos limiares |
| Tópicos | os mesmos três, com o mesmo `maxQuestoes` |
| Critérios de aprovação | os mesmos — o validador não sabe qual braço está rodando |
| Cache | limpo antes de cada tópico, para a amostra medir o modelo e não o banco |

A única coisa que muda é `CONFIG_IA.provedor` e, entre B e C, `suportaSchema`.

---

## 4. Tópicos

Os três da Fase 5, cobrindo a faixa de volume de conteúdo, todos já habilitados e com
dados de nuvem para comparação:

| Tópico | Caracteres | `maxQuestoes` | Papel |
|---|---:|---:|---|
| `filo-cordados` | 4.675 | 5 | Referência das Fases 1 a 5 |
| `filo-artropodes` | 1.032 | 2 | Onde ocorreu o defeito de título de seção |
| `filo-moluscos` | 645 | 1 | Menor tópico com 100% de entrega |

---

## 5. Dimensionamento: por que N não está definido

Não sei quanto tempo o `qwen3.5:4b` leva em CPU, e não vou estimar. O protocolo é medir
antes:

**Etapa 1 — sondagem.** 3 gerações em `filo-cordados`, braço B.

```bash
node scripts/benchmark-fase6.js --sondagem --modelo-local qwen3.5:4b
```

**Etapa 2 — bateria, dimensionada pela latência medida:**

| Mediana da sondagem | N por tópico | Tempo estimado por braço local |
|---|---:|---|
| até 60 s | 10 | ~1 h |
| 60 a 150 s | 6 | ~1 h 15 |
| acima de 150 s | 3 | ~40 min |

O braço A (nuvem) roda com o **mesmo N**, no mesmo dia, para que a comparação não seja
contaminada por variação do serviço entre datas.

### Modelo local: candidato e reserva

| | Tamanho | RAM estimada em execução | Situação |
|---|---|---|---|
| `qwen3.5:4b` | 3,4 GB | ~4,2 a 4,7 GB | **Candidato principal** |
| `qwen3.5:2b` | 1,9 GB | ~2,6 a 3,0 GB | Reserva, se o 4b for inviável |

A escolha final sai da sondagem, não daqui. No PC de mesa — 32 GB de RAM — o 4b tem folga
larga; a reserva existe caso a latência, e não a memória, inviabilize.

O modelo é parâmetro de linha de comando (`--modelo-local`), **não** está escrito no
`config-ia.js`. Trocar de candidato é trocar um argumento.

---

## 6. Métricas coletadas

Todas saem da instrumentação existente, sem alterar a camada.

| Métrica | Como é obtida |
|---|---|
| **Latência** | Relógio de parede por quiz — mediana, p95, mín., máx. Também a latência informada pelo cliente, separada do tempo de validação |
| **Taxa de aprovação** | aprovadas ÷ recebidas, pelo validador atual |
| **Retentativas** | total e quantas gerações precisaram de segunda tentativa |
| **JSON válido de primeira** | a primeira tentativa usou a estratégia `direto` do parser, sem `recorte` nem `reparo`. **É a métrica central do braço C** |
| **Taxa de entrega** | gerações servidas por IA ÷ total. Mede utilidade prática |
| **Motivos de rejeição** | contados por motivo do validador |
| **Motivos de fallback** | quando a cascata cai para cache ou quiz fixo |
| **Fidelidade** | `conceito_fora_do_material` e `enunciado_fora_do_material` do validador, mais os marcadores de triagem |
| **Diversidade** | enunciados distintos ÷ total |
| **Máquina** | CPUs e RAM são gravados na amostra, para as execuções em PCs diferentes serem comparáveis |

---

## 7. Avaliação de qualidade

O protocolo da Fase 5, sem mudanças — porque foi ele que encontrou os dois defeitos que o
validador aprovou.

### 7.1 Triagem automática

`scripts/comparar-benchmark.js` marca candidatos a problema. Marcador **não é defeito
confirmado**, e ausência de marcador **não é atestado de qualidade**:

| Marcador | O que aponta |
|---|---|
| `negativa` | enunciado com NÃO / EXCETO / INCORRETA / FALSA |
| `titulo-de-secao` | enunciado apoiado num título estrutural de seção |
| `alucinacao` | a alternativa correta mal aparece no material |
| `distrator-vazio` | distrator sem relação lexical com o material |
| `distrator-literal` | distrator reproduz trecho inteiro do material |
| **`termo-inedito`** | **novo na Fase 6** — ver §7.3 |

### 7.2 Leitura manual

Para cada braço:

- **todas** as questões marcadas em `negativa` e `titulo-de-secao` — os dois problemas que
  as regras do prompt V4 miram;
- **todas** as marcadas em `termo-inedito`;
- **amostra cega sistemática**, uma a cada N, sem seleção por marcador.

A classificação usa as mesmas nove categorias da Fase 5: mais de uma resposta defensável,
nenhuma resposta correta, distrator também verdadeiro, ambiguidade, dependência de seção,
alucinação, explicação inconsistente, questão negativa mal formada e distrator artificial.

### 7.3 Detector de termo técnico inédito

Criado nesta fase para o defeito registrado na Fase 5: *"alucinação ou corrupção de termo
técnico parcialmente mascarada pela sobreposição lexical"* — o caso em que o modelo
escreveu **"trilobulados"** onde o material diz **"triblásticos"**.

Aquele caso passou por três camadas sem ser notado: pelo validador, porque a alternativa
tinha 67% de cobertura (as outras palavras seguravam o índice); pelo marcador `alucinacao`,
cujo limiar é 55%; e pela leitura, até eu comparar palavra a palavra.

O detector extrai da **alternativa correta** as palavras com 8 ou mais letras que não sejam
advérbios em *-mente*, gerúndios ou palavras comuns, e verifica por radical se aparecem no
material. Só a alternativa correta é analisada — um distrator pode e deve trazer termo de
fora, porque ele é uma afirmação falsa.

**Calibragem contra a amostra real da Fase 5** (74 questões da revalidação do V4):

| | Resultado |
|---|---|
| Questões marcadas | **4 de 74 (5,4%)** |
| Encontrou o defeito conhecido | ✅ `trilobulados` |
| Encontrou um caso que a leitura manual perdeu | ✅ `triploblasticos` |
| Ruído | `flutuabilidade`, `representantes` |

O achado de `triploblasticos` é o que justifica o detector: é sinônimo legítimo de
*triblásticos* em embriologia, mas **não é o termo do material**. Não chega a ser erro
factual como "trilobulados", e ainda assim entrega ao aluno uma palavra que ele não vai
encontrar estudando. Minha leitura manual das 20 questões não pegou.

---

## 8. Onde os resultados são gravados

**`docs/dados-benchmark/`** — pasta nova, separada de `docs/dados-piloto/`.

| Braço | Arquivo |
|---|---|
| Sondagem | `fase6-sondagem-<modelo>.json` |
| A | `fase6-braco-A-gpt-oss-120b-cloud.json` |
| B | `fase6-braco-B-qwen3-5-4b.json` |
| C | `fase6-braco-C-qwen3-5-4b.json` |

Cada arquivo guarda o texto integral de todas as questões geradas, os hashes de prompt, as
latências por geração e a configuração da máquina.

### Salvaguardas, todas com teste automatizado

| Salvaguarda | Teste |
|---|---|
| Gravação só em `docs/dados-benchmark/` | recusa caminho fora da pasta |
| Nunca sobrescreve resultado existente | exige `--forcar` explícito |
| `config-ia.js` não é alterado | SHA-256 conferido antes e depois de cada braço |
| Dados da Fase 5 intocados | os 9 arquivos são fotografados por hash e conferidos ao fim |
| Prompts A e B idênticos | comparação de hash aborta a execução se divergir |

---

## 9. Testes da infraestrutura

```bash
node scripts/testar-benchmark.js      # 61 asserções, sem modelo e sem rede
```

**61 passaram, 0 falharam.** Os testes rodam o benchmark inteiro contra um daemon dublado,
incluindo os caminhos de falha: modelo não registrado, daemon fora do ar e resposta sem
JSON. Isso permitiu validar a infraestrutura antes de baixar 3,4 GB de modelo e antes de
levar qualquer coisa para o PC de mesa.

---

## 10. O que fica fora desta preparação

1. **A escolha final do modelo** — sai da sondagem no PC de mesa.
2. **O `think: false`.** O `qwen3.5` é um modelo com raciocínio, e tokens de pensamento
   podem multiplicar a latência em CPU. Desligá-lo exigiria acrescentar um parâmetro ao
   `cliente-ollama.js`. **Não foi feito de propósito**: a primeira sondagem mede o
   comportamento real com a configuração atual, e a decisão vem depois, com o número.
3. **O uso da GPU.** A GTX 1650 tem 4 GB de VRAM e o Ollama pode ou não usá-la. O guia
   manda verificar e **registrar o que acontecer**, sem mexer em driver para forçar.
4. **A execução.** Nada foi gerado.
