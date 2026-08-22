# Fase 5 — Avaliação controlada e piloto

> **230 gerações, 752 questões recebidas, 648 aprovadas, ~90 lidas uma a uma.**
> Resultado: **13 dos 21 tópicos habilitados para IA**, 8 mantidos no quiz fixo, cada um
> com o motivo medido.
>
> Nenhum arquivo de conteúdo do site foi alterado. Os dados brutos de todas as amostras
> estão em `docs/dados-piloto/*.json` (0,9 MB), com o texto integral de cada questão
> gerada — nada neste relatório é estimativa.

---

## 1. Como a fase foi conduzida

Oito amostras, em ondas, do tópico com mais conteúdo para o com menos:

| Amostra | Prompt | Tópicos | Gerações | Para quê |
|---|---|---|---|---|
| `onda1-v1-cordados` | V1 | 1 | 20 | Linha de base |
| `onda2-v2-cordados` | V2 | 1 | 20 | Experimento: regra de títulos de seção |
| `onda3-v3-cordados` | V3 | 1 | 20 | Experimento: regra de perguntas negativas |
| `onda4-v3-grandes` | V3 | 4 | 40 | Tópicos de 3.047 a 1.985 caracteres |
| `onda5-v3-medios` | V3 | 8 | 80 | Tópicos de 1.032 a 733 caracteres |
| `onda6-v3-pequenos` | V3 | 3 | 30 | Tópicos de 668 a 645 caracteres |
| `onda7-v4-artropodes` | V4 | 1 | 10 | Experimento: as duas regras juntas |
| `onda8-v4-cordados` | V4 | 1 | 10 | Verificação de regressão — **contaminada** (§6) |

Cada tópico foi habilitado **apenas em memória** durante a medição. `topicosComIA` no
arquivo de configuração só foi alterado no fim da fase, com base nestes números.

Ferramentas criadas, todas reexecutáveis:

```bash
node scripts/avaliar-topicos.js --rotulo X --n 10 --prompt V4 --topicos a,b,c
node scripts/analisar-questoes.js X [--listar MARCADOR] [--amostra N] [--comparar]
node scripts/resumo-piloto.js [--markdown]
```

---

## 2. Tabela final — resultados reais das gerações

Entrega por IA = quantas das gerações chegaram ao aluno como quiz gerado, em vez de cair
no fallback. Onde o tópico foi medido com mais de uma versão de prompt, vale a que
descreve o comportamento atual do site.

| Tópico | Caract. | Máx. | Ger. | Entrega por IA | Receb. | Aprov. | Rejeit. | Taxa | Retent. | Mediana | Decisão |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Filo dos Cordados | 4.675 | 5 | 20 | 20/20 (100%) | 108 | 96 | 12 | 89% | 8 | 14,8 s | **IA** |
| Fluxo de Energia | 3.047 | 5 | 10 | 10/10 (100%) | 53 | 43 | 10 | 81% | 8 | 16,7 s | **IA** |
| Pirâmides Ecológicas | 2.677 | 4 | 10 | 10/10 (100%) | 47 | 39 | 8 | 83% | 6 | 13,3 s | **IA** |
| Ecossistemas da Terra | 1.996 | 5 | 10 | 10/10 (100%) | 48 | 44 | 4 | 92% | 3 | 13,1 s | **IA** |
| Sucessão Ecológica | 1.985 | 5 | 10 | 10/10 (100%) | 58 | 50 | 8 | 86% | 8 | 17,0 s | **IA** |
| Filo dos Artrópodes | 1.032 | 2 | 10 | 10/10 (100%) | 22 | 20 | 2 | 91% | 2 | 9,8 s | **IA** |
| Mundo Vivo e Ecologia | 980 | 2 | 10 | **4/10 (40%)** | 10 | 8 | 2 | 80% | 2 | 2,0 s | Fixo |
| Definição e Componentes | 976 | 2 | 10 | **3/10 (30%)** | 6 | 6 | 0 | 100% | 0 | 2,7 s | Fixo |
| Pteridófitas | 897 | 2 | 10 | 10/10 (100%) | 27 | 20 | 7 | 74% | 6 | 11,2 s | **IA** |
| Filo dos Poríferos | 852 | 2 | 10 | 10/10 (100%) | 23 | 20 | 3 | 87% | 3 | 9,2 s | **IA** |
| Briófitas | 766 | 2 | 10 | 10/10 (100%) | 25 | 20 | 5 | 80% | 4 | 8,1 s | **IA** |
| Reino Plantae | 757 | 2 | 10 | **1/10 (10%)** | 2 | 2 | 0 | 100% | 0 | 1,6 s | Fixo |
| Filo dos Equinodermos | 733 | 2 | 10 | 10/10 (100%) | 27 | 20 | 7 | 74% | 7 | 10,9 s | **IA** |
| Filo dos Cnidários | 668 | 1 | 10 | 10/10 (100%) | 13 | 10 | 3 | 77% | 3 | 4,1 s | **IA** |
| Reino Animalia | 663 | 1 | 10 | 8/10 (80%) | 9 | 8 | 1 | 89% | 1 | 4,3 s | **IA** |
| Filo dos Moluscos | 645 | 1 | 10 | 10/10 (100%) | 12 | 10 | 2 | 83% | 2 | 4,0 s | **IA** |
| Filo dos Nematelmintos | 581 | 0 | — | — | — | — | — | — | — | — | Fixo |
| Filo dos Anelídeos | 573 | 0 | — | — | — | — | — | — | — | — | Fixo |
| Filo dos Platelmintos | 531 | 0 | — | — | — | — | — | — | — | — | Fixo |
| Gimnospermas | 406 | 0 | — | — | — | — | — | — | — | — | Fixo |
| Angiospermas | 209 | 0 | — | — | — | — | — | — | — | — | Fixo |

**Totais da tabela:** 170 gerações · 146 por IA e 24 por fallback · 416 de 490 questões
aprovadas (84,9%) · 74 rejeitadas · 63 retentativas.

---

## 3. Os quatro números que a fase pediu para separar

| Categoria | Quantidade | O que significa |
|---|---:|---|
| Aprovadas automaticamente pelo validador | **648** de 752 (86,2%) | Passaram nas regras estruturais e pedagógicas sem intervenção |
| Rejeitadas pelo validador | **104** (13,8%) | Nunca chegaram à tela; motivo registrado em cada uma |
| Gerações que precisaram de retentativa | **100** de 230 | O serviço reenviou o motivo da recusa e pediu de novo |
| Defeitos encontrados na **leitura manual** | **2** em ~90 lidas | Passaram no validador e estavam pedagogicamente errados |

A última linha é a razão de existir esta fase. **86,2% de aprovação automática não é
86,2% de qualidade**: o validador responde "esta questão está bem formada?", não "esta
questão está certa?". Os dois defeitos abaixo passaram por ele sem um arranhão.

### Motivos de rejeição do validador

Somando as amostras que descrevem o comportamento atual:

| Motivo | Peso |
|---|---|
| `vazamento_por_comprimento` | maioria esmagadora |
| `explicacao_cita_letra` | poucos casos |
| `alternativa_vazia` | raríssimo |

O `vazamento_por_comprimento` responde por quase toda a rejeição: o modelo escreve a
alternativa correta mais longa que as outras. Custa retentativa e latência, **não custa
qualidade** — é barrado antes de chegar ao aluno. Se o limiar de 1,7× fosse afrouxado, a
taxa de aprovação subiria de imediato, ao preço de deixar passar um vazamento que o aluno
aprende a explorar sem estudar. Manter como está é coerente com a prioridade da fase.

---

## 4. Defeito 1 — pergunta negativa com duas respostas válidas

Encontrado lendo a amostra V1 de Cordados.

> **Sobre os condrictes (peixes cartilaginosos), qual característica NÃO se aplica a eles?**
> **A) Possuem bexiga natatória** ← marcada como correta
> B) Possuem mandíbula · C) Possuem escamas placóides · D) Possuem brânquias externas
>
> *"…mandíbula e brânquias externas não são mencionadas, mas também não são apresentadas
> como características reais; **ainda assim**, a única opção explicitamente refutada pelo
> texto é a presença de bexiga natatória."*

Condrictes **não têm brânquias externas** — têm fendas branquiais. A alternativa D também
é uma característica que não se aplica, então a questão tem duas respostas. A própria
explicação mostra o modelo hesitando.

**Causa estrutural:** numa pergunta negativa, as três alternativas que *não* são a
resposta precisam ser verdadeiras. O modelo tende a inventá-las em vez de tirá-las do
texto.

**Correção — prompt V3**, uma regra só: numa pergunta negativa, as três não-respostas
precisam ser afirmações que o material declara explicitamente sobre aquele mesmo assunto;
se não houver três, reescreva na forma afirmativa.

**Efeito medido, mesmo tópico, mesmo N:**

| | V1 | V3 |
|---|---|---|
| Enunciados negativos | 5,2% (5 de 96) | **2,1% (2 de 96)** |
| As negativas restantes | 1 defeituosa de 3 lidas | **2 corretas de 2 lidas** |
| Taxa de aprovação | 92,3% | 88,9% |

As duas negativas que sobraram em V3 são bem formadas: em ambas as três não-respostas
estão explícitas no texto, exatamente como a regra exigiu.

---

## 5. Defeito 2 — questão decidida pelo título da seção

Encontrado lendo a amostra V3 de Artrópodes.

> **De acordo com o texto, qual das seguintes características está incluída nas
> "Características Gerais" dos artrópodes?**
> A) Hormônio ecdisona · **B) Celomados** ← correta · C) Apêndices corporais articulados ·
> D) Sistema digestório completo
>
> *"Embora 'Sistema digestório completo' e 'Apêndices corporais articulados' também sejam
> características dos artrópodes, **elas aparecem na seção de Morfologia, não nas
> características gerais**."*

Só que "Corpo segmentado com **apêndices articulados**" está, sim, dentro de
`## Características Gerais` no conteúdo do site. A alternativa C também é correta.

E a explicação diz com todas as letras qual é o problema: a questão foi decidida por
**onde** o fato está escrito, não pelo que o texto afirma.

### 5.1 O experimento que eu conduzi errado, e a correção

Este é o mesmo defeito observado em Cordados na Fase 4 e que motivou o prompt **V2**.
Testei o V2 em Cordados, com 20 gerações, e o recusei:

| | V1 | V2 |
|---|---|---|
| Taxa de aprovação | 92,3% | **87,4%** |
| Retentativas | 6 | **11** |
| Questões com o defeito-alvo | **0 de 96** | **0 de 97** |

O raciocínio na hora foi: "não reduziu nada e piorou a aprovação, logo recusar". **O
raciocínio estava errado.** A taxa-base do defeito em Cordados era zero — em 193 questões
de V1 e V2 ele não apareceu uma única vez. Um experimento sobre um defeito que não ocorre
no tópico testado **não pode** demonstrar melhora, qualquer que seja o resultado. Eu medi
a coisa certa no lugar errado.

O defeito ocorre em **Artrópodes**, e foi lá que o teste tinha que ter sido feito.

### 5.2 O experimento refeito onde o defeito ocorre

**V4 = V1 + regra de negativas + regra de títulos de seção.** Medido em Artrópodes,
contra o V3 do mesmo tópico:

| | V3 | V4 |
|---|---|---|
| Taxa de aprovação | 80% | **91%** |
| Retentativas | 5 | **2** |
| Mediana | 12,6 s | **9,8 s** |
| Enunciados citando título de seção | 2 de 20 | 4 de 20 |
| **Desses, com mais de uma resposta válida** | **1** | **0** |

O número de enunciados que citam a seção subiu, e isso **não é problema**: o que mudou foi
o papel da seção. Em V3 ela era o discriminador e os distratores eram fatos verdadeiros de
outra seção; em V4 ela virou contexto e os distratores passaram a ser afirmações falsas.
Comparando as duas versões da mesma pergunta:

| | Alternativas erradas |
|---|---|
| V3 | *Apêndices corporais articulados*, *Sistema digestório completo* — ambas verdadeiras |
| V4 | *Deuterostômios*, *Acoelomados*, *Planários* — todas falsas para artrópodes |

**V4 foi adotado** como padrão em `CONFIG_IA.versaoPrompt`.

### 5.3 O detector também estava errado

O primeiro marcador para este problema procurava a palavra "exclusiva" no enunciado. Ele
marcou 2 de 96 questões em Cordados — **as duas corretas** — e **não pegou** o defeito de
Artrópodes, cujo enunciado não usa a palavra "exclusiva" nenhuma vez.

Foi substituído por um marcador que procura **títulos estruturais de seção** no enunciado
("Características Gerais", "Morfologia", "Classificação"…). Esse encontra o caso real: um
enunciado que se apoia num rótulo organizacional está perguntando onde o fato está, não o
que o texto afirma.

---

## 6. O limite do plano gratuito, e uma amostra perdida

Na oitava amostra o Ollama Cloud começou a responder em menos de 1 segundo, com falha:

```
{"error":"you (…) have reached your session usage limit, upgrade for higher limits"}
```

O limite de uso da sessão do plano gratuito foi atingido depois de cerca de 200 gerações.
A amostra `onda8-v4-cordados` está contaminada da quinta geração em diante e **ficou fora
da tabela final**: só as 4 primeiras gerações valem, o que é pouco para afirmar ausência
de regressão.

**Pendência honesta:** a verificação de que o V4 não regride em Cordados está incompleta.
Falta uma amostra limpa de 10 a 20 gerações quando os créditos voltarem.

O que a falha mostrou de bom: **a cascata funcionou exatamente como projetada**. Seis
quizzes foram servidos pelo banco fixo, nenhuma tela ficou vazia, nenhum erro chegou ao
aluno. Foi o teste de fallback mais realista da fase, e não foi simulado.

### 6.1 Defeito de diagnóstico encontrado por causa disso

Os 20 erros HTTP foram registrados no diagnóstico como
`"modelo não devolveu questão aproveitável"`. Errado: o modelo não devolveu nada porque
**nem chegou a ser consultado**.

A causa: `motivoDoFallback()` só reportava a falha quando ela interrompia o laço (rede,
assinatura, modelo). Falhas de HTTP e de timeout geram nova tentativa e não deixavam
rastro no motivo. Corrigido — quando todas as tentativas falham, o motivo passa a nomear
o tipo da falha.

Um motivo errado no diagnóstico é pior do que motivo nenhum: manda procurar problema de
qualidade onde o problema é de infraestrutura.

---

## 7. Por que três tópicos com conteúdo suficiente ficaram no quiz fixo

`reino-plantae` (10% de entrega), `definicao-e-componentes` (30%) e
`mundo-vivo-ecologia` (40%) têm `maxQuestoes > 0` e passaram no critério da Fase 1. Ainda
assim ficaram fora.

O que acontece neles: o modelo responde `{"questoes":[]}` — **JSON válido, array vazio**.
Não é erro nem alucinação. Parser `direto`, 0 questões recebidas, 0 rejeitadas, resposta
em cerca de 2 segundos. É o modelo obedecendo à instrução do prompt de sistema:

> *"Se o material não sustentar a quantidade de questões pedida, você entrega MENOS
> questões. Entregar menos é o comportamento correto."*

Ele julgou o material insuficiente e não gerou nada. Em Reino Plantae, **9 vezes em 10**.

Isso é um achado, não um defeito: a recusa do modelo é um **segundo critério de
suficiência de conteúdo**, que surgiu sozinho e é mais rigoroso que a fórmula de
`maxQuestoes` da Fase 1. Onde os dois discordam, o modelo tem sido o mais conservador.

Habilitar esses tópicos faria o aluno esperar alguns segundos para receber, na maioria das
vezes, o mesmo quiz fixo de sempre. A decisão de mantê-los no banco fixo é a que entrega
melhor experiência **e** a que respeita a prioridade de qualidade sobre quantidade.

Os outros cinco — Angiospermas, Gimnospermas, Platelmintos, Anelídeos e Nematelmintos —
já tinham `maxQuestoes = 0` desde a Fase 1 e nem chegam a ser consultados em tempo de
execução.

---

## 8. O que a triagem automática consegue e o que não consegue

Foram construídos marcadores automáticos para os problemas A a I. Dois deles se mostraram
**inúteis para o que prometiam**, e isso é resultado, não fracasso.

| Marcador | Primeira versão | O que aconteceu |
|---|---|---|
| `distrator-verdadeiro` | cobertura de termos do distrator ≥ 85% | Marcou **75% de todas as questões**. Numa delas, as **quatro** alternativas tinham 100% de cobertura e a questão estava correta |
| `distrator-literal` | trecho de 5+ palavras copiado do texto | Caiu para 4,2%. As 4 lidas estavam **todas corretas**: eram afirmações verdadeiras sobre **outros grupos**, usadas como distrator — que é bom design |
| `distrator-vazio` | cobertura < 15% | Em Sucessão marcou 32%. As lidas eram **bons distratores**: plausíveis e falsos, e por serem falsos não estão no texto |

**Conclusão metodológica:** sobreposição lexical não julga distrator em nenhuma das duas
direções. Cobertura alta é sinal de distrator *bem construído* — ele usa o vocabulário do
material. Cobertura baixa é sinal de distrator *falso* — que é o que ele deve ser.

Detectar "esta alternativa também é uma resposta correta" exige saber se a afirmação é
verdadeira **para o assunto daquela pergunta específica**, e isso nenhum método lexical
resolve. Foi por leitura que os dois defeitos apareceram — e nenhum deles tinha marcador.

O que a triagem automática entrega de verdade é **ordem de leitura**: ela diz onde olhar
primeiro. Os marcadores que se mostraram úteis foram `negativa` e `titulo-de-secao`,
justamente os que descrevem uma **forma de pergunta arriscada**, não uma estatística de
palavras.

---

## 9. Critério de decisão por tópico

Um tópico foi habilitado quando atendeu aos três ao mesmo tempo:

1. **Entrega por IA ≥ 80%** — abaixo disso o aluno espera e recebe o quiz fixo assim mesmo;
2. **Taxa de aprovação ≥ 70%** — abaixo disso a geração custa retentativas demais;
3. **Nenhum defeito pedagógico não corrigido** na leitura manual.

| Decisão | Tópicos | Motivo |
|---|---|---|
| **IA — 13** | Cordados, Fluxo de Energia, Pirâmides, Ecossistemas da Terra, Sucessão, Artrópodes, Pteridófitas, Poríferos, Briófitas, Equinodermos, Cnidários, Reino Animalia, Moluscos | Entrega de 80% a 100%, aprovação de 74% a 92%, leitura sem defeito pendente |
| **Fixo — 3** | Reino Plantae, Definição e Componentes, Mundo Vivo e Ecologia | Entrega de 10% a 40%: o próprio modelo recusa o material |
| **Fixo — 5** | Angiospermas, Gimnospermas, Platelmintos, Anelídeos, Nematelmintos | `maxQuestoes = 0` desde a Fase 1 |

Os dois tópicos com aprovação mais baixa entre os habilitados — Pteridófitas e
Equinodermos, ambos 74% — foram lidos e não apresentaram defeito. A rejeição neles é
quase toda `vazamento_por_comprimento`, que o validador barra. Ficam habilitados **e sob
observação**: se a taxa cair na próxima medição, saem.

---

## 10. Dez questões para revisão manual de Biologia

O roteiro pede uma amostra para revisão humana da correção biológica. Uma questão de cada
tópico habilitado, escolhida sistematicamente (a do meio da amostra), em
`docs/dados-piloto/`. As dez estão reproduzidas no relatório da fase entregue junto com
este documento.

Minha leitura não substitui a sua: eu posso conferir fidelidade ao material do site e
coerência interna, mas o julgamento final sobre correção biológica é seu.

---

## 11. Limitações desta fase

1. **A verificação do V4 em Cordados está incompleta** — a amostra foi perdida para o
   limite de uso do plano gratuito (§6). Pendente.
2. **~90 questões lidas de 752 geradas** (12%). A taxa de defeito observada — 2 em ~90 —
   não é uma estimativa estatística; com essa amostra, defeitos raros passam sem ser
   vistos.
3. **Amostra de 10 gerações por tópico** para 15 dos 16 avaliados; só Cordados teve 20.
   Para tópicos de `maxQuestoes` 1 ou 2, isso são 10 a 20 questões, o que é pouco para
   distinguir 74% de 83% de aprovação.
4. **A diversidade é medida por enunciado, não por sentido.** Pirâmides marcou 100% de
   enunciados distintos e mesmo assim produziu duas perguntas semanticamente iguais
   ("por que a pirâmide tem a ponta para cima") com redações diferentes.
5. **Um único modelo.** Tudo aqui descreve o `gpt-oss:120b-cloud`. A comparação com modelo
   local é a Fase 6.
6. Seguem valendo as limitações anteriores: o JSON Schema não é respeitado na nuvem, só se
   geram questões de múltipla escolha, e a validação roda no cliente.

---

## 12. Estado do repositório

Alterados nesta fase: `script/ia/config-ia.js` (lista de tópicos e versão do prompt),
`script/ia/prompt-quiz.js` (regras V2, V3 e V4), `script/ia/servico-quiz.js` (motivo de
fallback) e três scripts de teste, cujas asserções presumiam que só Cordados estava
habilitado.

**Nenhum arquivo de conteúdo, CSS, imagem, quiz fixo ou HTML de tópico foi alterado.**
As 195 asserções das suítes das Fases 2, 3 e 4 continuam passando.
