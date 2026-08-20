## 1. Contexto

Trabalho acadêmico de faculdade. Já existe um **site educacional de Biologia** em **HTML, CSS e
JavaScript puros** (sem framework, sem build step, sem npm), organizado em:

```
Módulos  →  Tópicos  →  Assuntos
```

- **Reino Animal** → tópicos por filo (Arthropoda, Annelida, Mollusca, Chordata…)
- **Plantas** → tópicos de botânica
- **Ecossistemas** → tópicos de ecologia

Cada tópico tem conteúdo teórico e um **quiz fixo** escrito à mão em JavaScript, com progresso
salvo no **LocalStorage**.

**Objetivo:** usar uma LLM via **Ollama** para gerar os quizzes **dinamicamente** a partir do
conteúdo de cada tópico — perguntas diferentes a cada tentativa, com enunciado, 4 alternativas,
resposta correta e **explicação educativa**.

---

## 2. Arquitetura definida (não questione, implemente)

**NÃO haverá backend.** Nada de Python, FastAPI, Node ou servidor de API. O projeto roda apenas
como site estático em `localhost` e **não será publicado em hosting**.

O fluxo é:

```
Navegador (site estático em localhost)
        │  fetch → http://localhost:11434/api/chat
        ▼
Daemon local do Ollama (já instalado na minha máquina)
        │  como o modelo tem sufixo :cloud, o daemon repassa para a nuvem
        ▼
Ollama Cloud  →  deepseek-v4-flash:cloud
```

**Por que isso é seguro e legítimo mesmo sem backend:** o modelo `deepseek-v4-flash:cloud` já está
instalado e é executado **através do daemon local** em `http://localhost:11434`. É o daemon que
guarda as credenciais da conta Ollama e faz a autenticação com a nuvem. **Nenhuma chave de API
aparece no código JavaScript**, porque o navegador nunca fala com `ollama.com` diretamente.

**Consequência importante para a Etapa 2 (modelo local):** trocar da nuvem para um modelo rodando
na minha máquina será apenas **mudar uma string de configuração** (`deepseek-v4-flash:cloud` →
nome do modelo local). Nenhuma outra linha de código muda. Isso deve ficar explícito no design.

### Modelo em uso

- **Etapa 1 (agora):** `deepseek-v4-flash:cloud` — já baixado/registrado via `ollama pull`.
- **Etapa 2 (depois):** modelo local, a definir por benchmark.

Antes de escrever código, o Claude Code deve validar o ambiente com:

```bash
ollama list                # o modelo deve aparecer na lista
curl http://localhost:11434/api/tags
curl http://localhost:11434/api/chat -d "{\"model\":\"deepseek-v4-flash:cloud\",\"messages\":[{\"role\":\"user\",\"content\":\"Responda apenas: ok\"}],\"stream\":false}"
```

Se o último comando falhar por autenticação, preciso rodar `ollama signin`.

---

## 3. Regras invioláveis

1. **Não reescreva o site.** O código existente é entregável acadêmico: estenda, não refaça.
   Alterações em arquivos existentes devem ser mínimas e justificadas por escrito.
2. **Zero dependências novas.** Nada de npm, nada de bundler, nada de CDN externo.
   Apenas JavaScript nativo com `fetch` e módulos ES ou scripts clássicos, seguindo o padrão
   que o site já usa.
3. **Nenhuma chave de API no código.** A autenticação é responsabilidade do daemon do Ollama.
4. **O site deve continuar funcionando com a IA desligada.** Se o Ollama estiver fora do ar, o
   quiz fixo original assume automaticamente. Isso é crítico para a apresentação ao professor.
5. **Todo texto de interface, comentário e documentação em português do Brasil.**
6. Trabalhe na branch `feat/quiz-ia`, com commits pequenos e descritivos.
7. **Não invente conteúdo de Biologia.** As perguntas devem ser geradas a partir do texto real do
   tópico, extraído do próprio site.
8. Ao final de cada fase: **pare, resuma o que foi feito e aguarde minha aprovação.**

---

## 4. FASE 0 — Mapeamento do projeto existente

**Sem escrever código.** Apenas leia e documente.

1. Percorra todos os arquivos do repositório e monte a árvore de diretórios comentada.
2. Liste todos os **módulos**, **tópicos** e **assuntos**.
3. Para cada tópico, identifique:
   - onde está o **conteúdo teórico** (HTML inline? array JS? outro?);
   - onde está o **quiz fixo**, com o **formato exato** do objeto de questão (nomes dos campos!);
   - quantas questões fixas existem.
4. Liste todas as **chaves do LocalStorage** e o que cada uma guarda.
5. Documente o **fluxo atual do quiz**, do clique até o resultado: quais funções, em quais
   arquivos, em qual ordem. Faça um diagrama Mermaid.
6. Aponte riscos: código duplicado, variáveis globais, IDs de DOM repetidos, lógica misturada
   com renderização.
7. Identifique o **ponto de extensão ideal**: o menor lugar onde dá para trocar "quiz fixo" por
   "quiz gerado por IA" sem tocar em mais nada.

**Entregável:** `docs/00-MAPEAMENTO.md`, com tabela
`Módulo | Tópico | Arquivo | Linhas | Nº de questões fixas | Formato do objeto`.

**Critério de aceite:** lendo só esse arquivo eu sei exatamente onde fica cada quiz e cada texto.

---

## 5. FASE 1 — Base de conhecimento

O conteúdo teórico precisa virar dado estruturado para alimentar o prompt da LLM.

1. Crie `dados/base-conhecimento.js` — **arquivo `.js`, não `.json`**. Motivo: um `.json` exigiria
   `fetch`, que quebra se eu abrir o site com `file://`. Um `.js` carregado por `<script>`
   funciona em qualquer situação. Formato:

```js
// Base de conhecimento extraída do conteúdo do site.
// Gerada por scripts/extrair-conteudo.js — não editar à mão.
const BASE_CONHECIMENTO = {
  "reino-animal": {
    titulo: "Reino Animal",
    topicos: {
      "filo-arthropoda": {
        titulo: "Filo Arthropoda",
        assuntos: ["Características gerais", "Classificação", "Importância ecológica"],
        conteudo: "Texto teórico limpo, sem tags HTML...",
        conceitosChave: ["exoesqueleto de quitina", "metameria", "ecdise"],
        nivel: "ensino_medio",
        origem: { arquivo: "modulos/animais/arthropoda.html", linhas: "45-190" }
      }
    }
  }
};
```

2. Crie `scripts/extrair-conteudo.js` — script **de desenvolvimento** (rodado por mim no Node,
   uma vez, quando eu editar o conteúdo) que percorre os HTMLs, limpa as tags e regenera o
   arquivo acima. Ele não faz parte do site em execução.
3. Gere `docs/01-EXTRACAO.md` com: total de tópicos extraídos, contagem de caracteres por tópico
   e **alerta para tópicos com menos de ~800 caracteres** — conteúdo curto produz perguntas
   genéricas ou inventadas.

**Critério de aceite:** 100% dos tópicos da Fase 0 estão na base, com texto utilizável.

---

## 6. FASE 2 — Camada de IA em JavaScript

Crie a pasta `site/js/ia/` com **cinco arquivos de responsabilidade única**:

```
site/js/ia/
├── config-ia.js         # configuração central
├── cliente-ollama.js    # comunicação HTTP com o daemon
├── prompt-quiz.js       # montagem do prompt e do schema
├── validador-quiz.js    # validação estrutural e pedagógica
├── cache-quiz.js        # persistência no LocalStorage
└── servico-quiz.js      # orquestrador: é a única coisa que o site chama
```

### 6.1 `config-ia.js`

```js
const CONFIG_IA = {
  habilitada: true,

  // Etapa 1 (nuvem): "deepseek-v4-flash:cloud"
  // Etapa 2 (local): trocar apenas esta string pelo nome do modelo local
  modelo: "deepseek-v4-flash:cloud",

  host: "http://localhost:11434",
  temperatura: 0.7,
  numQuestoesPadrao: 5,
  timeoutMs: 120000,
  maxTentativas: 3,

  // Migração gradual: só estes tópicos usam IA. Os demais seguem com quiz fixo.
  topicosComIA: ["filo-arthropoda"],

  cacheHabilitado: true,
  modoDebug: false // true → loga prompt, resposta crua e motivos de rejeição no console
};
```

### 6.2 `cliente-ollama.js`

Responsabilidades: montar o `fetch`, tratar timeout, tratar erros, checar disponibilidade.

- Endpoint: `POST {host}/api/chat`
- `stream: false` (simplifica o parsing; a UI mostra estado de carregamento)
- Use o parâmetro **`format`** com um **JSON Schema** — isso força o modelo a devolver JSON
  estruturado e elimina quase todos os erros de parsing. **Não peça JSON só no texto do prompt.**
- Timeout com `AbortController`.
- Exponha `verificarDisponibilidade()` que chama `GET /api/tags` e confirma que o modelo
  configurado está na lista.

Esqueleto:

```js
async function chamarOllama(mensagens, schema) {
  const controlador = new AbortController();
  const timer = setTimeout(() => controlador.abort(), CONFIG_IA.timeoutMs);

  try {
    const resposta = await fetch(`${CONFIG_IA.host}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controlador.sinal,
      body: JSON.stringify({
        model: CONFIG_IA.modelo,
        messages: mensagens,
        stream: false,
        format: schema,
        options: { temperature: CONFIG_IA.temperatura }
      })
    });
    if (!resposta.ok) throw new Error(`Ollama respondeu ${resposta.status}`);
    const dados = await resposta.json();
    return JSON.parse(dados.message.content);
  } finally {
    clearTimeout(timer);
  }
}
```

### 6.3 Sobre CORS — trate isso explicitamente

O Ollama aceita requisições de origens locais por padrão, mas **não aceita `file://`**
(origem `null`). Portanto:

- O site **deve** ser servido por um servidor HTTP local — Live Server do VS Code
  (`http://127.0.0.1:5500`) ou `python -m http.server`.
- Se ainda assim aparecer erro de CORS no console, a solução é definir a variável de ambiente
  `OLLAMA_ORIGINS` e reiniciar o Ollama. No Windows:
  ```cmd
  setx OLLAMA_ORIGINS "*"
  ```
  Depois **feche o Ollama pela bandeja do sistema e abra de novo** — variável de ambiente só é
  lida na inicialização do processo.
- Documente isso em `docs/02-EXECUCAO.md` com o passo a passo e a mensagem de erro exata que o
  usuário veria, para eu não travar na hora da apresentação.

### 6.4 `prompt-quiz.js`

Mantenha os textos de prompt em **constantes nomeadas e versionadas** neste arquivo
(`PROMPT_SISTEMA_V1`, `PROMPT_USUARIO_V1`), separadas da lógica — isso me permite mostrar a
evolução da engenharia de prompt no relatório.

Regras do prompt:

- **System:** professor de Biologia do ensino médio brasileiro, especialista em avaliação.
- O conteúdo do tópico entra delimitado (`<conteudo>…</conteudo>`) com instrução explícita:
  **usar exclusivamente esse material**; se não houver base suficiente, gerar menos questões em
  vez de inventar.
- Exigir: exatamente 4 alternativas; uma única correta; **distratores plausíveis** (erros
  conceituais reais de estudante, não alternativas absurdas); explicação de 2 a 4 frases dizendo
  por que a correta está certa **e** por que a mais tentadora está errada.
- Passar a lista de conceitos já cobrados (`conceitosExcluir`) para forçar variação entre
  tentativas.
- Tudo em português do Brasil.

Schema para o parâmetro `format`:

```js
const SCHEMA_QUIZ = {
  type: "object",
  properties: {
    questoes: {
      type: "array",
      items: {
        type: "object",
        properties: {
          enunciado: { type: "string" },
          alternativas: {
            type: "array",
            items: {
              type: "object",
              properties: { id: { type: "string" }, texto: { type: "string" } },
              required: ["id", "texto"]
            },
            minItems: 4,
            maxItems: 4
          },
          respostaCorreta: { type: "string" },
          explicacao: { type: "string" },
          conceitoAvaliado: { type: "string" }
        },
        required: ["enunciado", "alternativas", "respostaCorreta", "explicacao", "conceitoAvaliado"]
      }
    }
  },
  required: ["questoes"]
};
```

### 6.5 `validador-quiz.js` (camada obrigatória)

Nenhuma questão chega à tela sem passar por aqui.

**Estrutural:** JSON válido; número de questões correto; exatamente 4 alternativas;
`respostaCorreta` existe entre os IDs; nenhum campo vazio; alternativas não duplicadas.

**Pedagógico/heurístico:**
- enunciado com tamanho mínimo razoável;
- alternativas com comprimentos parecidos — a correta sistematicamente mais longa é vazamento
  clássico de resposta;
- rejeitar "todas as anteriores" / "nenhuma das anteriores";
- explicação presente e não trivial;
- **anti-alucinação simples:** verificar sobreposição de termos entre o `conceitoAvaliado` e o
  texto do tópico na base de conhecimento. Se o conceito não aparece no material, rejeite.

**Em caso de falha:** nova tentativa (até `maxTentativas`), reenviando ao modelo o **motivo da
rejeição**. Esgotadas as tentativas, cai para o fallback.

Registre toda rejeição em um contador no LocalStorage (`quiz_ia_metricas`): total de gerações,
rejeições por motivo, latência média. **Essa métrica vale muito na defesa do trabalho.**

### 6.6 `cache-quiz.js`

LocalStorage, chave `quiz_ia_banco`, com:
- questões validadas, cada uma com um **hash** (do enunciado normalizado) para deduplicação;
- carimbo de data e o `conceitoAvaliado`;
- limite de tamanho (LocalStorage costuma ficar em torno de 5 MB) com descarte das mais antigas.

Esse banco tem função dupla: reduz latência **e** vira automaticamente o fallback offline.

### 6.7 `servico-quiz.js` — a única porta de entrada

Expõe uma função só:

```js
async function obterQuiz(moduloId, topicoId, opcoes = {}) { /* ... */ }
```

Cascata interna de fallback, nesta ordem:

1. **IA** (se `habilitada` e o tópico está em `topicosComIA` e o Ollama responde)
2. **Cache** de questões validadas do LocalStorage
3. **Quiz fixo original** do site

Sempre devolva o quiz **no mesmo formato de objeto que o site já usa** (descoberto na Fase 0),
acrescido de um campo `origem: "ia" | "cache" | "fixo"` e `modelo`. Assim o restante do site não
precisa saber de onde o quiz veio.

**Entregável:** `docs/03-CAMADA-IA.md` explicando cada arquivo e as decisões tomadas.

---

## 7. FASE 3 — Integração na interface

1. Nos arquivos existentes, **a única mudança permitida** é trocar a leitura do array fixo por
   `await obterQuiz(moduloId, topicoId)`. Nada além disso.
2. Adicione os `<script>` novos nas páginas, na ordem correta de dependência.
3. **UX obrigatória:**
   - estado de carregamento visível (a geração leva alguns segundos — nunca deixar a tela parada);
   - mensagem de erro amigável quando cair no fallback, sem jargão técnico;
   - botão **"Gerar novas perguntas"**;
   - selo discreto indicando a origem ("Perguntas geradas por IA" / "Banco de questões").
4. **Preserve integralmente** o formato de progresso já salvo no LocalStorage — nada de histórico
   perdido.

**Entregável:** `docs/04-INTERFACE.md` com o antes/depois de cada arquivo alterado.

---

## 8. FASE 4 — Página de diagnóstico

Crie `site/ferramentas/diagnostico.html` — página independente, fora do fluxo do site, que mostra:

- status do daemon Ollama (online/offline) e modelo ativo;
- botão de teste de conexão com latência medida;
- gerador manual: escolher módulo/tópico → gerar → ver **prompt enviado, JSON cru recebido e
  resultado da validação** lado a lado;
- métricas acumuladas (nº de gerações, taxa de rejeição, latência média);
- botão para limpar o cache.

Essa página é a peça que eu vou usar para **demonstrar o funcionamento ao professor**. Capriche.

---

## 9. FASE 5 — Piloto e migração gradual

1. Ative a IA em **um único tópico** (sugestão: Filo Arthropoda, conteúdo mais extenso).
2. Gere 20 quizzes seguidos e produza `docs/05-AVALIACAO-PILOTO.md` com: taxa de rejeição por
   motivo, latência média e p95, e **10 questões de amostra para eu revisar manualmente** quanto
   à correção biológica.
3. Só depois da minha aprovação, expanda — **um módulo por vez**, adicionando IDs em
   `topicosComIA`.
4. Nunca apague os quizzes fixos: eles continuam sendo o último nível de fallback.

---

## 10. FASE 6 — Etapa 2: modelo local

1. **Me pergunte a configuração da máquina** (RAM, GPU/VRAM, sistema operacional) antes de
   sugerir qualquer modelo. A escolha depende inteiramente disso.
2. Crie `site/ferramentas/benchmark.html`: roda o **mesmo conjunto de prompts** em vários modelos
   e monta uma tabela comparativa — modelo, latência média por quiz, taxa de JSON válido na 1ª
   tentativa, taxa de aprovação na validação, qualidade do português (nota manual minha, 1–5).
3. Priorize modelos com bom suporte a **português** e a **saída estruturada em JSON**. Consulte o
   catálogo atual do Ollama antes de recomendar — não confie em listas de memória.
4. Documente em `docs/06-BENCHMARK-LOCAL.md` a comparação **nuvem vs. local**: latência, custo,
   privacidade, independência de rede. Esse contraste é um ótimo fecho para o relatório.

---

## 11. Documentação final

Consolide em `docs/README.md`:

- diagrama da arquitetura e justificativa da escolha sem backend;
- como executar (servidor local + Ollama + variáveis de ambiente);
- decisões técnicas: por que validação no cliente, por que fallback em cascata, por que schema
  no `format`;
- **limitações conhecidas, escritas com honestidade** — este ponto conta na avaliação:
  - a aplicação só funciona em máquina com Ollama instalado e autenticado;
  - não é publicável em hosting nesta arquitetura, pois o navegador de um visitante não teria
    o daemon local (para publicar, seria necessário um backend intermediário guardando a
    credencial);
  - a validação roda no cliente e, num cenário real com usuários, poderia ser contornada;
- trabalhos futuros: RAG para conteúdos maiores, fine-tuning para estilo pedagógico, backend
  para publicação.

---

## 12. Antes de começar

Leia este documento inteiro e me devolva:

1. Sua interpretação resumida do objetivo.
2. As dúvidas que precisam ser resolvidas antes da Fase 0.
3. O plano de execução com estimativa de esforço por fase.

**Não escreva código antes dessa confirmação.**