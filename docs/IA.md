# Nature Code — Inteligência Artificial

> 📄 **Relatório final da disciplina:** [`RELATORIO-FINAL-IA.md`](RELATORIO-FINAL-IA.md)

> **Disciplina:** Inteligência Artificial.
> **Funcionalidade:** quizzes dinâmicos, com perguntas geradas por uma LLM a partir do
> conteúdo de cada tópico do site.
>
> Este é um **índice**. O conteúdo detalhado está nos documentos linkados abaixo, que são a
> fonte primária. Para a outra disciplina, ver [`PDI.md`](PDI.md); para a visão geral da
> entrega, [`ENTREGA-GERAL.md`](ENTREGA-GERAL.md).

---

## 1. Objetivo

Os 21 tópicos do Nature Code tinham quizzes fixos, escritos à mão. O módulo de IA gera
**perguntas novas a partir do próprio texto de cada tópico**, sem backend e sem chave de
API no navegador, e garante que o aluno **nunca fica sem quiz**.

---

## 2. Pipeline

```
conteúdo → prompt → Ollama → LLM → parser → validador → cache → quiz
```

| Etapa | O que faz | Onde |
|---|---|---|
| Conteúdo | Texto do tópico, extraído para uma base de conhecimento | `dados/` · [`01-EXTRACAO.md`](01-EXTRACAO.md) |
| Prompt | **Prompt V4** — instruções e regras pedagógicas (versões V1–V4 registradas) | `script/ia/prompt-quiz.js` |
| Ollama | Daemon local em `localhost:11434`; guarda a credencial da conta | `script/ia/cliente-ollama.js` |
| LLM | **`gpt-oss:120b-cloud`**, executado na nuvem via daemon | `script/ia/config-ia.js` |
| Parser | Extrai o JSON da resposta mesmo com prosa, bloco de código ou truncamento | `script/ia/parser-quiz.js` |
| Validador | Critérios estruturais e pedagógicos; questão reprovada não chega ao aluno | `script/ia/validador-quiz.js` |
| Cache | Banco de questões validadas no `localStorage` (`quiz_ia_banco`) | `script/ia/cache-quiz.js` |
| Quiz | Conversão para o formato do site e exibição | `script/ia/servico-quiz.js`, `script/ia/interface-quiz.js` |

### Fallback

```
IA → cache → questões fixas
```

Se o Ollama estiver fora do ar, sem internet ou sem cota, o quiz sai do **cache**; se não
houver cache para o tópico, sai o **quiz fixo original** — os 21 quizzes fixos nunca foram
apagados. Botão de pânico: `CONFIG_IA.habilitada = false` em `script/ia/config-ia.js`
devolve o site ao comportamento original.

### Diagnóstico

[`ferramentas/diagnostico.html`](../ferramentas/diagnostico.html) mostra modelo, provedor,
latência, resposta crua do modelo e o motivo de cada fallback. Ver
[`04b-DIAGNOSTICO.md`](04b-DIAGNOSTICO.md).

---

## 3. Números principais

| Item | Valor |
|---|---|
| Tópicos que geram por IA | **13 de 21**, habilitados por medição |
| Piloto (Fase 5) | 230 gerações · 752 questões · 648 aprovadas pelo validador (86,2 %) |
| Testes | **256/256** asserções offline (67 + 46 + 82 + 61) |
| Benchmark nuvem × local (Fase 6) | **Parcial** — duas sondagens; bateria completa não executada |

---

## 4. Como executar só a IA

A IA **não depende do PDI**: não é preciso instalar Python, ambiente virtual nem API para
testá-la.

1. Instale o **Ollama** (https://ollama.com/download), abra-o pela bandeja do sistema e
   autentique:
   ```cmd
   ollama signin
   ollama pull gpt-oss:120b-cloud
   ollama list
   ```
2. Na raiz do repositório, sirva o site por HTTP (nunca por `file://`):
   ```cmd
   python -m http.server 8000
   ```
3. Abra `http://127.0.0.1:8000/` e entre num tópico — por exemplo, Reino Animal → Cordados.

Sem Ollama, o site funciona do mesmo jeito, com cache ou quiz fixo. Passo a passo e
solução de problemas (CORS, autenticação): [`02-EXECUCAO.md`](02-EXECUCAO.md).

---

## 5. Documentação detalhada

| Documento | Conteúdo |
|---|---|
| [`DOCUMENTACAO-FINAL-NATURE-CODE.md`](DOCUMENTACAO-FINAL-NATURE-CODE.md) | **Documentação final completa do módulo de IA** |
| [`README.md`](README.md) | Resumo e índice da documentação de IA |
| [`00-MAPEAMENTO.md`](00-MAPEAMENTO.md) | Fase 0 — Mapeamento do site original |
| [`01-EXTRACAO.md`](01-EXTRACAO.md) | Fase 1 — Extração do conteúdo e base de conhecimento |
| [`02-EXECUCAO.md`](02-EXECUCAO.md) | Como executar o site com a IA ligada |
| [`03-CAMADA-IA.md`](03-CAMADA-IA.md) | Fase 2 — Camada de IA em JavaScript |
| [`04-INTERFACE.md`](04-INTERFACE.md) | Fase 3 — Integração na interface |
| [`04b-DIAGNOSTICO.md`](04b-DIAGNOSTICO.md) | Fase 4 — Página de diagnóstico |
| [`05-AVALIACAO-PILOTO.md`](05-AVALIACAO-PILOTO.md) | Fase 5 — Avaliação controlada e piloto |
| [`05b-REVALIDACAO-V4.md`](05b-REVALIDACAO-V4.md) | Fase 5 — Revalidação do Prompt V4 |
| [`06-BENCHMARK-LOCAL.md`](06-BENCHMARK-LOCAL.md) | Fase 6 — Protocolo do benchmark nuvem × local |
| [`06c-RESULTADO-BENCHMARK.md`](06c-RESULTADO-BENCHMARK.md) | Fase 6 — Resultado das sondagens |
| [`DOCUMENTACAO-FINAL-IA-PDI.md`](DOCUMENTACAO-FINAL-IA-PDI.md) | Documento técnico dos dois módulos |

As numerações de fase da IA e do PDI são **independentes**: "Fase 5" da IA não tem relação
com "Fase 5" do PDI.
