# Fase 6 — Resultado das sondagens locais

> **Escopo desta execução: duas sondagens do Braço B.** A bateria completa A/B/C **não foi
> executada**. Este documento registra o que foi medido, e é explícito sobre o que
> continua sem resposta experimental.

Fonte primária: `docs/dados-benchmark/fase6-sondagem-qwen3-5-4b.json` e
`docs/dados-benchmark/fase6-sondagem-qwen3-5-2b.json`. Todo número aqui foi lido desses
arquivos ou calculado a partir deles, e pode ser reconferido com
`node scripts/comparar-benchmark.js`.

---

## 1. Objetivo da Fase 6

A Fase 6 existe por causa de uma limitação medida na Fase 2: **nenhum modelo `:cloud`
respeita o parâmetro `format` com JSON Schema.** O daemon repassa a requisição para a
ollama.com, e a restrição por gramática — que é aplicada pelo runner local — não chega lá.
O mecanismo correto de saída estruturada só existe rodando o modelo na própria máquina.

A fase foi desenhada para responder três perguntas, nesta ordem
([`06-BENCHMARK-LOCAL.md`](06-BENCHMARK-LOCAL.md) §1):

1. Um modelo pequeno em CPU produz questões de qualidade comparável ao `gpt-oss:120b-cloud`?
2. Quanto o JSON Schema melhora a confiabilidade do formato?
3. A latência local é aceitável para uso na apresentação?

**Esta execução responde apenas a terceira**, e mesmo assim de forma restrita: os dados
coletados são suficientes para a **decisão de viabilidade prevista pelo protocolo**,
**no hardware e na configuração testados**, e não autorizam generalização além disso. As
duas primeiras continuam em aberto.

---

## 2. Escopo realmente executado

| Braço | Descrição | Executado? |
|---|---|---|
| **A** | Cloud, `gpt-oss:120b-cloud`, sem schema | **Não** |
| **B** | Local, sem schema | **Sim — apenas sondagem**, em dois modelos |
| **C** | Local, com JSON Schema | **Não** |

Duas sondagens, 3 gerações cada, todas no tópico `filo-cordados`:

| Sondagem | Arquivo | Data (UTC) |
|---|---|---|
| `qwen3.5:4b` | `fase6-sondagem-qwen3-5-4b.json` | 2026-09-10, 02:26 → 02:52 |
| `qwen3.5:2b` | `fase6-sondagem-qwen3-5-2b.json` | 2026-09-18, 02:32 → 02:48 |

**O que esta execução não permite afirmar:**

- não há comparação experimental **A × B** — o braço da nuvem não foi rodado nesta bateria;
- não há comparação experimental **B × C** — o braço com schema não foi rodado;
- **não se pode concluir nada sobre o efeito do JSON Schema**, que era a pergunta central
  da fase;
- **o benchmark completo da Fase 6 não foi concluído.**

O que se pode concluir é a **viabilidade prática dos dois modelos locais testados, nesta
máquina e nesta configuração**. Nada além disso.

---

## 3. Ambiente da sondagem

Os dois JSONs registram exatamente o mesmo ambiente no campo `maquina`:

| | Valor registrado |
|---|---|
| Plataforma | `win32` |
| Node.js | `v24.21.0` |
| CPUs lógicas | 12 |
| Memória total | 15,7 GB |

> **Atenção — este não é o ambiente originalmente planejado.**
> O [`06b-GUIA-PC-MESA.md`](06b-GUIA-PC-MESA.md) foi escrito para um PC de mesa com
> **Ryzen 7 5800X, 32 GB de RAM e GTX 1650**. A execução ocorreu em uma máquina com
> **12 CPUs lógicas e 15,7 GB de RAM** — praticamente metade da memória prevista.
> **Nenhum resultado deste documento pode ser atribuído à GTX 1650 ou ao Ryzen 7 5800X.**

O campo `maquina` grava plataforma, versão do Node, número de CPUs lógicas e memória
total. **Não grava modelo de processador nem presença de GPU.** O passo 19 do guia manda
conferir a coluna `PROCESSOR` do `ollama ps` para saber se houve aceleração por GPU; esse
registro **não consta nos arquivos**, então este documento não afirma nada sobre uso de
GPU nesta execução.

---

## 4. Metodologia

A sondagem é o primeiro estágio do protocolo, e existe justamente para dimensionar a
bateria antes de gastar horas nela ([`06-BENCHMARK-LOCAL.md`](06-BENCHMARK-LOCAL.md) §5):

```bash
node scripts/benchmark-fase6.js --sondagem --modelo-local qwen3.5:4b
node scripts/benchmark-fase6.js --sondagem --modelo-local qwen3.5:2b --rotulo fase6-sondagem-qwen3-5-2b
```

Parâmetros idênticos nas duas execuções, todos lidos dos JSONs:

| | Valor |
|---|---|
| Braço | B — Local sem schema |
| Provedor | `local` |
| `schemaEnviado` | `false` |
| Versão do prompt | **V4** |
| Tópico | `filo-cordados` (4.675 caracteres, `maxQuestoes` = 5) |
| Gerações por tópico | 3 |
| Questões por geração | 5 |

**Integridade do prompt, verificada.** O script calcula o SHA-256 do conjunto exato de
mensagens enviado ao modelo. As duas sondagens registram **o mesmo hash**:

```
db375a6d56ce20aafe239e2e7bfe218296fa8451daba787cebef73b9a6ad0c43   (9.263 caracteres)
```

Isso importa: a comparação **4b × 2b** é uma comparação de variável única — mesmo prompt
byte a byte, mesmo tópico, mesmo ambiente registrado, **só o modelo mudou**. É o único
contraste experimentalmente válido desta execução.

### Como ler a métrica de latência

Duas definições precisam ficar claras, porque mudam a interpretação dos números:

- **A latência reportada é o tempo total de uma tentativa de geração completa**, campo
  `totalMs`, que inclui **as 3 tentativas internas** do serviço (`maxTentativas: 3`). Não
  é o tempo de uma única chamada ao modelo.
- **O bloco `metricas.latencia` dos JSONs está zerado** (`amostras: 0`). A camada só
  registra latência de modelo em chamada bem-sucedida, e não houve nenhuma. Por isso
  `latenciaModeloMs` é 0 em todas as gerações.
- Com **n = 3**, o "p95" calculado pelo comparador cai no índice 2 do vetor ordenado — ou
  seja, **o p95 aqui é literalmente o maior dos três valores**, não uma estimativa de
  cauda. Está reportado como tal.

---

## 5. Resultado — `qwen3.5:4b`

| Métrica | Valor |
|---|---|
| Gerações tentadas | 3 |
| **Entregues pela IA** | **0 / 3 (0%)** |
| Origem dos quizzes servidos | `fixo`: 3 · `ia`: 0 · `cache`: 0 |
| Questões recebidas | 0 |
| Questões aprovadas | 0 |
| Chamadas ao modelo | **9** (3 por geração) |
| Retentativas | 6 |
| Falhas de chamada | **9 — todas do tipo `resposta`** |
| JSON válido de primeira | 0 / 3 (0%) |

Tempos por geração, em ordem:

| | Tempo total da geração | Média por chamada |
|---|---:|---:|
| Mínimo | 498,5 s | ~166,2 s |
| **Mediana** | **505,7 s** | ~168,6 s |
| Máximo (= "p95" com n=3) | 581,2 s | ~193,7 s |

Média das três: **528,5 s**. Duração total da sondagem: **26,4 minutos**.

**Todas as 3 gerações terminaram em fallback**, com o motivo registrado como
`falha na chamada: resposta`.

---

## 6. Critério para testar o `qwen3.5:2b`

A decisão não foi improvisada: estava escrita no protocolo antes da execução. O passo 20
do [`06b-GUIA-PC-MESA.md`](06b-GUIA-PC-MESA.md) define:

| Mediana da sondagem | Decisão | N por tópico |
|---|---|---:|
| até 60 s | segue com o 4b | 10 |
| 60 a 150 s | segue com o 4b | 6 |
| acima de 150 s | segue com o 4b, bateria curta | 3 |
| **acima de 300 s**, ou o modelo não coube | **vá ao passo 21** | — |

Mediana medida no 4b: **505,7 s**. A faixa acionada é a última, e o passo 21 é
exatamente *"somente se necessário: testar o 2b"*. O modelo reserva foi testado por
**regra do protocolo**, não por escolha posterior aos dados.

---

## 7. Resultado — `qwen3.5:2b`

| Métrica | Valor |
|---|---|
| Gerações tentadas | 3 |
| **Entregues pela IA** | **0 / 3 (0%)** |
| Origem dos quizzes servidos | `fixo`: 3 · `ia`: 0 · `cache`: 0 |
| Questões recebidas | 0 |
| Questões aprovadas | 0 |
| Chamadas ao modelo | **9** |
| Retentativas | 6 |
| Falhas de chamada | **9 — todas do tipo `resposta`** |
| JSON válido de primeira | 0 / 3 (0%) |

| | Tempo total da geração | Média por chamada |
|---|---:|---:|
| Mínimo | 307,5 s | ~102,5 s |
| **Mediana** | **316,6 s** | ~105,5 s |
| Máximo (= "p95" com n=3) | 355,9 s | ~118,7 s |

Média das três: **326,7 s**. Duração total da sondagem: **16,3 minutos**.

Novamente, **as 3 gerações terminaram em fallback**, com o mesmo motivo.

---

## 8. Comparação 4b × 2b

| Métrica | `qwen3.5:4b` | `qwen3.5:2b` | Variação |
|---|---:|---:|---|
| Schema enviado | não | não | — |
| Gerações | 3 | 3 | — |
| **Entrega por IA** | **0/3 (0%)** | **0/3 (0%)** | **nenhuma** |
| Questões recebidas | 0 | 0 | — |
| Questões aprovadas | 0 | 0 | — |
| Retentativas | 6 | 6 | — |
| Falhas de chamada | 9 (`resposta`) | 9 (`resposta`) | — |
| JSON válido de 1ª | 0/3 (0%) | 0/3 (0%) | — |
| Latência mediana | 505,7 s | **316,6 s** | **−37,4%** |
| Latência máxima | 581,2 s | 355,9 s | −38,8% |
| Média por chamada | ~168,6 s | ~105,5 s | −37,4% |
| Duração da sondagem | 26,4 min | 16,3 min | −38,3% |

**O modelo menor foi cerca de 1,6× mais rápido — e isso não alterou o resultado.** A
redução de latência é real e consistente em todas as medidas, mas as duas colunas de
entrega são idênticas: zero. O 2b continuou **acima do limite de 300 s** do protocolo e
também não entregou um único quiz por IA.

Como o prompt era byte a byte idêntico e só o modelo mudou, essa é uma comparação de
variável única legítima. A conclusão que ela sustenta é limitada e específica: **reduzir o
tamanho do modelo, nesta configuração, resolve parte do problema de tempo e nenhuma parte
do problema de entrega.**

---

## 9. Interpretação dos resultados

### O que falhou não foi o formato — foi a resposta

Este é o ponto mais importante do documento, e é fácil ler os números de forma errada.

"JSON válido de primeira: 0/3" sugere que o modelo respondeu em formato ruim. **Não foi
isso que aconteceu.** As 18 chamadas (9 + 9) falharam com o tipo `resposta`, que em
[`cliente-ollama.js`](../script/ia/cliente-ollama.js) tem um significado único e preciso:

> `"O modelo devolveu uma resposta vazia."`

A requisição HTTP foi bem-sucedida. Cada chamada levou, pela média por chamada calculada
a partir do `totalMs`, cerca de 105 s no `2b` e 169 s no `4b` até retornar. E o campo
`message.content` voltou **vazio**. Não houve JSON malformado, não houve Markdown em
excesso, não houve texto para o parser tentar reparar — não houve texto nenhum. Os campos
`rejeicoesPorMotivo` e `estrategiasDoParser` estão vazios nos dois arquivos justamente
porque **nada chegou a ser analisado**: o validador e o parser nunca foram acionados.

### Hipótese sobre a causa — não comprovada nesta execução

Os dados registrados **não identificam a causa**. Uma hipótese técnica plausível e
prioritária para investigação — **que não foi comprovada nesta execução** e que uma próxima
rodada precisa testar — é a seguinte:

O `qwen3.5` é um modelo com raciocínio explícito. Nessa família, os tokens de pensamento
são emitidos em um campo separado de `message.content`. Se o teto de geração
(`numPredict: 4500`) se esgota antes de o modelo sair da fase de raciocínio, a chamada
retorna normalmente, com HTTP 200, e `content` vazio — exatamente o que foi registrado.

Três observações são consistentes com essa leitura, sem prová-la:

1. Nenhuma chamada atingiu o timeout de 300 s configurado para o provedor local
   (~168 s e ~105 s por chamada). **Não foi corte por tempo** — a chamada terminou sozinha.
2. Os tempos por chamada são estáveis dentro de cada modelo, o que é o padrão de quem
   gera um orçamento fixo de tokens até o fim, e não de quem para ao concluir uma resposta.
3. A razão de tempo entre 4b e 2b (~1,6×) acompanha a diferença de tamanho dos modelos,
   como se ambos estivessem produzindo a mesma quantidade de tokens.

**O parâmetro `think` não foi alterado nesta execução, e isso foi deliberado.** O protocolo
([`06-BENCHMARK-LOCAL.md`](06-BENCHMARK-LOCAL.md) §10.2) determinou que a primeira sondagem
mediria o comportamento da **configuração atual**, sem ajustes, e que a decisão sobre
`think: false` viria depois, com número na mão. É o que acontece agora: o número existe, e
ele aponta para esse teste como o próximo passo — registrado na §13 como trabalho futuro,
não como conclusão desta execução.

### Sobre a viabilidade interativa

Mesmo que a causa da resposta vazia fosse resolvida, os tempos medidos já respondem à
terceira pergunta da fase. Com mediana de **505,7 s** (4b) e **316,6 s** (2b) por tentativa
de geração — e ~168 s e ~105 s por chamada isolada —, o aluno esperaria de dois a dez
minutos por um quiz. **A latência local nesta máquina não é compatível com uso interativo**,
e muito menos com uma demonstração ao vivo.

---

## 10. Validação funcional do fluxo Cloud

Em paralelo, e **separadamente das sondagens**, o fluxo de nuvem do projeto foi validado à
mão no computador principal, com `gpt-oss:120b-cloud`.

Verificado manualmente no navegador:

- Ollama em execução e modelo de nuvem disponível;
- geração real de quiz pelo site;
- perguntas renderizadas corretamente;
- seleção de respostas funcionando;
- explicações exibidas;
- finalização do quiz;
- botão de gerar novas perguntas;
- **fallback funcionando com o Ollama indisponível.**

Suítes automatizadas, executadas novamente:

| Suíte | Resultado |
|---|---|
| Camada de IA | 67 / 67 |
| Integração | 46 / 46 |
| Diagnóstico | 82 / 82 |
| Benchmark | 61 / 61 |
| **Total** | **256 / 256 asserções, 0 falhas** |

> **Isto é validação funcional do sistema, não o Braço A do benchmark.** Não houve coleta
> instrumentada, não houve N definido, não houve gravação em `docs/dados-benchmark/`, e os
> números acima não são comparáveis com as sondagens locais. Tratar essa validação como
> braço experimental seria exatamente o erro metodológico que a Fase 5 já registrou uma vez
> (ver [`05-AVALIACAO-PILOTO.md`](05-AVALIACAO-PILOTO.md) §5.1).

---

## 11. Limitações do experimento

1. **n = 3 por modelo.** Três gerações não sustentam estatística. Sustentam uma decisão de
   viabilidade — que é para isso que a sondagem existe.
2. **Um único tópico.** Só `filo-cordados`. Outros tópicos têm volume de texto diferente e
   produziriam prompts de outro tamanho.
3. **Uma única máquina**, e não a prevista no guia. Nada aqui se generaliza para outro
   hardware.
4. **Sem registro de GPU.** O JSON não grava a saída do `ollama ps`, então não se sabe se
   houve aceleração.
5. **A bateria A/B/C não foi executada.** Sem braço A instrumentado e sem braço C, as duas
   primeiras perguntas da fase seguem sem resposta.
6. **A causa da resposta vazia não foi identificada** — apenas registrada e hipotetizada.
7. **Qualidade não pôde ser avaliada.** Zero questões recebidas significa que não há texto
   para o validador medir, para os marcadores de triagem apontarem, nem para leitura manual.
   A nota de português de 1 a 5 prevista no roteiro (§10.2) ficou sem objeto.
8. **`think` não foi testado**, por decisão do protocolo.

---

## 12. Decisão para a versão apresentada

**A versão apresentada permanece na nuvem**, com a configuração congelada e validada:

```js
provedor: "cloud",
modelo:   "gpt-oss:120b-cloud",
versaoPrompt: "V4",
```

A justificativa é inteiramente baseada nos dados desta execução:

- o `qwen3.5:4b` teve mediana de **505,7 s** e **0% de entrega por IA**;
- o `qwen3.5:2b` reduziu a mediana para **316,6 s**, mas manteve **0% de entrega por IA**;
- o próprio protocolo já previa recorrer ao 2b acima de 300 s, e **o 2b também ficou acima
  desse limite**;
- prosseguir com a bateria completa nessa máquina custaria horas de execução **sem
  qualquer evidência de viabilidade interativa** — os dois modelos disponíveis já haviam
  falhado em entregar um único quiz.

**Isto não é um fracasso do projeto.** É um resultado experimental: nesta configuração e
neste hardware, a execução local não é viável, e a sondagem cumpriu exatamente o papel para
o qual foi desenhada — **estabelecer isso com aproximadamente 43 minutos de tempo
acumulado entre as duas sondagens** (26,4 min e 16,3 min, executadas em datas distintas),
**em vez de várias horas de bateria completa.**

Vale registrar o que esses zeros também demonstram: **em 6 gerações consecutivas com o
modelo falhando por completo, o site entregou 6 quizzes.** A cascata IA → cache → quiz fixo
funcionou em 100% dos casos, com o motivo do fallback corretamente classificado e
registrado. Nas seis gerações observadas, a cascata impediu que a falha do modelo local
interrompesse a entrega do quiz, recorrendo ao conteúdo fixo.

---

## 13. Trabalhos futuros

Nenhum dos itens abaixo foi testado nesta execução. São hipóteses e caminhos, **não
resultados**.

| Investigação | Por quê |
|---|---|
| **`think: false`** | Hipótese principal para a resposta vazia. Exigiria acrescentar o parâmetro ao `cliente-ollama.js` e repetir a sondagem, sem mudar mais nada |
| **Outros modelos locais** | A família `qwen3.5` foi a única testada. Modelos sem raciocínio explícito, ou com teto de tokens menor, podem se comportar de outra forma |
| **JSON Schema (Braço C)** | A pergunta central da fase segue sem resposta. Depende de existir uma configuração local que entregue alguma coisa |
| **Aceleração por GPU** | Não houve registro nesta execução. Uma rodada com `ollama ps` documentado diria se a GPU foi usada |
| **Hardware diferente** | Inclusive o PC de mesa originalmente previsto no guia, com 32 GB e GPU dedicada |
| **Otimizações de execução local** | `num_predict` menor, quantização mais agressiva, `num_thread` ajustado, contexto reduzido |
| **Bateria A/B/C completa** | Só faz sentido depois que alguma configuração local passar da sondagem |

---

## 14. Conclusão

Duas sondagens do Braço B foram executadas, em `qwen3.5:4b` e `qwen3.5:2b`, num ambiente
com 12 CPUs lógicas e 15,7 GB de RAM — **diferente do PC de mesa previsto no guia**.

Os dois modelos **falharam em entregar qualquer quiz por IA**: 0 de 3 em cada um, 18
chamadas, todas retornando resposta vazia. O modelo menor foi ~1,6× mais rápido, reduzindo
a mediana de 505,7 s para 316,6 s, mas permaneceu acima do limite de 300 s do protocolo e
não alterou o resultado de entrega.

Por isso **a bateria completa A/B/C não foi executada**, e a versão apresentada do projeto
**permanece com o provedor de nuvem**, cujo funcionamento foi validado manualmente e por
256 asserções automatizadas.

O que esta execução estabelece é estreito e sólido: **nesta máquina e nesta configuração,
os dois modelos locais previstos no protocolo não são viáveis.** O que ela não estabelece é
igualmente importante e está dito por extenso na §2 e na §11 — sobretudo o efeito do JSON
Schema, que era a pergunta central da Fase 6 e continua em aberto.
