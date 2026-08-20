# Fase 4 — Página de diagnóstico

> `ferramentas/diagnostico.html` — página independente, **fora do fluxo do site**. Nenhuma página
> do site aponta para ela, e nada dela é carregado pelas páginas de tópico.
>
> Nome do arquivo: o roteiro numera os documentos por entregável e não reservou número para a
> Fase 4 (o `05-` é da avaliação do piloto). Daí o `04b`.
>
> **Nenhum arquivo de conteúdo do site foi alterado nesta fase**, e os 20 tópicos continuam no quiz
> fixo — `topicosComIA` segue com `filo-cordados` apenas.

---

## 1. O que foi criado e alterado

| Arquivo | Situação | Papel |
|---|---|---|
| `ferramentas/diagnostico.html` | novo | Estrutura e estilo próprio da página |
| `ferramentas/diagnostico.js` | novo | Comportamento: painéis, teste de conexão, gerador manual |
| `scripts/testar-diagnostico.js` | novo | 87 testes da página |
| `scripts/lib/dom-de-teste.js` | novo | DOM mínimo, extraído do teste da Fase 3 e agora compartilhado |
| `script/ia/metricas-ia.js` | **alterado** | Passou a contar origem dos quizzes e motivo de fallback |
| `script/ia/servico-quiz.js` | **alterado** | Registra a origem e resume o motivo do fallback ao entregar |
| `scripts/testar-integracao.js` | alterado | Passou a importar o DOM do módulo compartilhado |
| `docs/02-EXECUCAO.md` | novo | Entregável da Fase 2 que estava em falta |

### Por que duas alterações na camada da Fase 2

Cinco itens da lista pedida — usos de cache, usos de quiz fixo, motivo dos fallbacks e a leitura
visual de "quem está atendendo" — **não tinham como ser exibidos**: a camada media a qualidade da
geração (quantas questões vieram, quantas passaram, quanto demorou), mas nunca registrava qual
nível da cascata acabou atendendo o aluno.

Duas adições fecharam isso:

```js
// metricas-ia.js
origens: { ia: 0, cache: 0, fixo: 0 },
motivosDeFallback: {},

// servico-quiz.js, na entrega
MetricasIA.registrarOrigem(origem, diagnostico.motivoFallback);
```

O motivo é resumido em uma frase curta a partir do diagnóstico que o serviço já montava —
"Ollama fora do ar", "tópico não elegível: …", "questões recusadas pelo validador". Sem isso a
métrica diria apenas que caiu, e não de onde.

---

## 2. O que a página mostra

### 2.1 Configuração ativa

Provedor, modelo, endpoint, timeout, temperatura/top_p, teto de tokens, número de tentativas, se a
camada está ligada e se o cache está ligado.

E, em destaque, **se o JSON Schema é respeitado**:

> `JSON Schema no format` — 🟡 **não respeitado — compensado no prompt**
>
> *Medido: modelos `:cloud` ignoram o parâmetro `format`. O formato é sustentado por instrução no
> prompt, parser tolerante e validação — nesta ordem. Trocar `CONFIG_IA.provedor` para "local"
> religa o schema automaticamente.*

Isso é deliberado: a limitação aparece na tela em vez de ficar escondida no código. Quando o
provedor local for ativado, o mesmo campo passa a mostrar 🟢 *enviado e respeitado*, sem mexer na
página.

### 2.2 Conexão com o Ollama

Botão **Testar conexão** que mede duas coisas diferentes, porque elas dizem coisas diferentes:

| Medida | O que significa |
|---|---|
| Latência do `/api/tags` | O daemon está no ar e responde — dezenas a centenas de ms |
| Latência de uma geração | Quanto o modelo demora para pensar de verdade — segundos |

Mostra também a lista de modelos registrados, marcando o que está em uso, e traduz a falha:
daemon fora do ar, modelo não registrado ou modelo que exige plano pago.

### 2.3 De onde vieram os quizzes — o painel que se lê de longe

Três cartões grandes, coloridos e contados:

```
   ✨ 8              💾 2              📘 5
gerados por IA   vindos do cache   quiz fixo do site
```

Cada cartão usa a mesma cor do selo que o aluno vê na página do quiz — verde para IA, verde-claro
para cache, azul-acinzentado para o fixo. Um cartão sem nenhuma ocorrência fica **apagado**, então
dá para saber num relance qual nível está atendendo. Abaixo, uma barra empilhada com a proporção e
a lista **por que caiu no fallback**, ordenada por frequência.

Era esse o pedido de "deixar visualmente claro quando a IA está funcionando e quando o sistema está
usando cache ou quiz fixo".

### 2.4 Geração e validação

Chamadas ao modelo, chamadas com erro, questões recebidas, aprovadas, rejeitadas, taxa de aprovação
com barra, motivos de rejeição e erros por tipo — ambos ordenados e com barra proporcional.

### 2.5 Tempo de geração

Amostras, média, mediana, p95, mínimo e máximo. Mais como o JSON foi extraído (`direto`, `cerca`,
`recorte`, `reparo`) e o uso por modelo.

A distinção entre média e mediana não é preciosismo: uma chamada que estourou o timeout distorce a
média e quase não move a mediana. Ter as duas lado a lado mostra se um número alto é regra ou
exceção.

### 2.6 Banco de questões

Total guardado, espaço usado com o teto, e a contagem por tópico. Dois botões: **Limpar cache** e
**Zerar métricas** — ambos avisam na tela que o progresso do aluno não foi tocado, e há teste
automatizado confirmando que `quizProgress` sobrevive aos dois.

### 2.7 Tópicos e capacidade

Tabela com os 21: módulo, tópico, caracteres, seções com texto, conceitos, máximo de questões,
suficiência e qual limite venceu. A linha do tópico habilitado vem destacada em verde; os 5 sem
conteúdo suficiente vêm esmaecidos e marcados como 📘 quiz fixo.

É o painel que responde "por que este tópico rende menos questões" com número, e não com opinião.

### 2.8 Gerador manual

Escolhe módulo e tópico, quantas questões, e se guarda no cache (desmarcado por padrão, para o
diagnóstico não poluir o banco do site). Ao gerar, mostra **lado a lado**:

| 1. Prompt enviado | 2. Resposta crua | 3. Parser e validação |
|---|---|---|
| Mensagens `system` e `user` inteiras, como foram para o modelo | O texto exato que voltou, sem tratamento | Latência, se o schema foi enviado, estratégia do parser, recebidas/aprovadas/recusadas e **o motivo de cada recusa** |

Abaixo, as questões aprovadas renderizadas com a correta destacada, a explicação e o conceito
avaliado.

O gerador **chama as camadas uma a uma** — `PromptQuiz` → `ClienteOllama` → `ParserQuiz` →
`ValidadorQuiz` — em vez de usar `obterQuiz()`. É de propósito: `obterQuiz()` devolve o quiz pronto
e esconde o caminho, e o que esta página precisa mostrar é justamente o caminho. Como efeito
colateral útil, ele funciona em **qualquer** tópico com conteúdo suficiente, inclusive os 20 que
ainda não estão habilitados no site — dá para inspecionar a qualidade antes de habilitar, na Fase 5.

---

## 3. Testes

```bash
node scripts/testar-diagnostico.js          # 82 testes, sem rede
node scripts/testar-diagnostico.js --rede   # + 5 com conexão e geração reais
```

**Resultado: 87 passaram, 0 falharam.**

| Grupo | Testes | Cobertura |
|---|---:|---|
| 1. Estrutura | 5 | Scripts existem, ordem de dependência, ids, isolamento do site |
| 2. Painéis vazios | 16 | Configuração, contadores zerados, tabela dos 21, seletores |
| 3. Painéis com dados | 27 | Cada número da lista pedida, com valores semeados e conferidos |
| 4. Conexão | 8 | Online, offline, erro de assinatura, latências, lista de modelos |
| 5. Gerador manual | 19 | As três colunas, cache opcional, resposta sem JSON, recusa, falha de rede |
| 6. Origem e fallback | 5 | As métricas novas alimentadas pelo serviço de verdade |
| 7. Rede real | 5 | Conexão e geração reais pelo Ollama |

### 3.1 O teste que mais importa

A página é quase toda DOM, e o jeito mais comum de ela quebrar é um id divergente entre o HTML e o
JavaScript. É uma falha **silenciosa**: `getElementById` devolve `null`, o código não pinta o campo
e nada acusa. Por isso o teste extrai do JS todos os ids procurados — por `elemento()`, `texto()`,
`selo()`, `listaContada()`, `ligar()` e `getElementById()` — e cruza com os `id="..."` do HTML:

```
ok    os 63 ids usados pelo JS existem no HTML
```

O teste também carrega **o HTML de verdade** num DOM mínimo, em vez de reconstruir a estrutura:
`dom.body.innerHTML = <corpo do arquivo>`. Assim um id renomeado no HTML aparece como falha, e não
como um teste que continua passando sobre uma cópia desatualizada.

### 3.2 Verificação por HTTP

Servindo a raiz do projeto: a página respondeu **200** e os **10 `<script>` também**.

### 3.3 Isolamento em relação ao site

Três verificações automatizadas:

- a página **não referencia nenhum CSS do site** — o estilo é próprio e local, então mexer aqui
  nunca pode afetar o visual das páginas de conteúdo;
- **nenhuma página do site aponta para o diagnóstico** — varredura em `pages/`;
- **limpar cache e zerar métricas não apagam `quizProgress`**.

### 3.4 Defeitos encontrados durante a fase

| # | Onde | Sintoma | Correção |
|---|---|---|---|
| 1 | `scripts/testar-diagnostico.js` | O teste do gerador usava o tópico que o seletor abre por padrão (`reino-animalia`) com massa de teste sobre notocorda. Tudo era recusado por `conceito_fora_do_material` | O teste passou a escolher Cordados. A recusa estava certa: era a checagem anti-alucinação funcionando |
| 2 | `scripts/testar-diagnostico.js` | **Falso positivo:** "geração real produziu questões" passava contando `children.length > 0`, mas o contêiner já nasce com um nó de texto. Passou mesmo com a geração falhando | Passou a contar cartões `.questao` |
| 3 | `scripts/testar-diagnostico.js` | Com o daemon fechado, o grupo `--rede` acusava duas falhas de código que eram só ambiente | O grupo detecta o daemon fora do ar e é pulado com aviso |
| 4 | `scripts/lib/dom-de-teste.js` | `<select>` não assumia o valor da primeira `<option>`, e faltava `createTextNode` | Ambos implementados |

O nº 2 merece registro: era um teste que **mentia**. Ele passou na primeira execução com o daemon
desligado, e só apareceu porque o resultado foi lido em vez de conferido pelo total.

---

## 4. Suítes do projeto, com o daemon no ar

| Suíte | Testes | Resultado |
|---|---:|---|
| `scripts/testar-camada-ia.js --rede` | 72 | 72 passaram |
| `scripts/testar-integracao.js --rede` | 50 | 50 passaram |
| `scripts/testar-diagnostico.js --rede` | 87 | 87 passaram |
| **Total** | **209** | **209 passaram, 0 falharam** |

As alterações em `metricas-ia.js` e `servico-quiz.js` foram feitas antes da página e as duas suítes
anteriores foram reexecutadas para confirmar que nada regrediu.

---

## 5. Cobertura da lista pedida

| Item | Onde aparece |
|---|---|
| Provedor atual | Configuração ativa |
| Modelo atual | Configuração ativa e lista de modelos registrados |
| Status da conexão | Conexão — selo online/offline + motivo |
| Suporte a JSON Schema | Configuração ativa, com a limitação escrita por extenso |
| Chamadas realizadas | Geração e validação |
| Questões geradas | Geração e validação — recebidas |
| Aprovadas / rejeitadas | Geração e validação, com barra da taxa |
| Taxa de aprovação | Geração e validação |
| Tempo médio / mediano | Tempo de geração — mais p95, mínimo e máximo |
| Quantidade de erros | Geração e validação, detalhada por tipo |
| Usos de cache | Cartão 💾 do painel de origem |
| Usos do quiz fixo | Cartão 📘 do painel de origem |
| Motivo dos fallbacks | Painel de origem, lista ordenada |
| Tópico habilitado para IA | Tabela de tópicos, linha destacada, e resumo acima dela |
| Clareza visual IA × cache × fixo | Três cartões coloridos, barra empilhada e cartão apagado quando zerado |

---

## 6. Limitações

1. **Sem verificação visual em navegador por automação.** Continua valendo o da Fase 3: não há
   Playwright nem Puppeteer, e instalá-los violaria a regra de zero dependências. O que existe é a
   página real rodando sobre um DOM mínimo e a checagem de carregamento por HTTP. O layout precisa
   de conferência visual.
2. **Os números são deste navegador.** As métricas vivem no LocalStorage, então cada navegador e
   cada perfil tem os seus. Zerar métricas é irreversível.
3. **A página escreve nas mesmas chaves que o site.** Gerar pelo diagnóstico soma nas métricas do
   site — o que é desejável para acumular amostra, mas significa que a taxa de aprovação mistura
   uso real e teste manual. A caixa "guardar no cache" fica desmarcada por padrão justamente para o
   banco de questões não ser afetado sem intenção.
4. **O gerador manual não passa pela cascata.** Ele chama as camadas diretamente, então não exercita
   fallback nem cache-como-fallback. Quem cobre esses caminhos são as suítes automatizadas.
5. Seguem valendo as limitações das fases anteriores: o schema não é respeitado na nuvem, só se
   geram questões de múltipla escolha e a validação roda no cliente.

---

## 7. Estado do repositório

Nenhum arquivo de conteúdo, CSS, imagem ou quiz fixo foi alterado. As páginas de tópico continuam
exatamente como ficaram na Fase 3 (+12/−0 cada), e `topicosComIA` segue com um único tópico.
