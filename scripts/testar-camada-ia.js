/**
 * testar-camada-ia.js — bateria de testes da camada de IA. Script DE DESENVOLVIMENTO.
 *
 *     node scripts/testar-camada-ia.js           só os testes offline (rápido, sem rede)
 *     node scripts/testar-camada-ia.js --rede    inclui uma chamada real ao Ollama
 *
 * Os arquivos de script/ia/ são scripts clássicos que declaram globais, exatamente como
 * o site os carrega. Aqui eles são carregados num contexto `vm` com `localStorage` e
 * `fetch` dublados — assim o que roda no teste é o mesmo código que roda no navegador,
 * sem adaptação e sem dependência nova.
 */

"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const RAIZ = path.resolve(__dirname, "..");

// ---------------------------------------------------------------------------
// Ambiente de navegador dublado
// ---------------------------------------------------------------------------
function criarLocalStorage() {
  const dados = new Map();
  return {
    getItem: (c) => (dados.has(c) ? dados.get(c) : null),
    setItem: (c, v) => dados.set(c, String(v)),
    removeItem: (c) => dados.delete(c),
    clear: () => dados.clear(),
    get length() {
      return dados.size;
    },
  };
}

function montarContexto() {
  const sandbox = {
    localStorage: criarLocalStorage(),
    console,
    location: { pathname: "/pages/modulos/topicos/topicos-animais/filo-cordados.html" },
    setTimeout,
    clearTimeout,
    AbortController,
    Math,
    Date,
    JSON,
    fetch: async () => {
      throw new TypeError("fetch não foi dublado neste teste");
    },
  };
  sandbox.globalThis = sandbox;
  const contexto = vm.createContext(sandbox);

  const arquivos = [
    "dados/base-conhecimento.js",
    "script/ia/config-ia.js",
    "script/ia/metricas-ia.js",
    "script/ia/cliente-ollama.js",
    "script/ia/prompt-quiz.js",
    "script/ia/parser-quiz.js",
    "script/ia/validador-quiz.js",
    "script/ia/cache-quiz.js",
    "script/ia/servico-quiz.js",
  ];
  for (const arquivo of arquivos) {
    vm.runInContext(fs.readFileSync(path.join(RAIZ, arquivo), "utf8"), contexto, {
      filename: arquivo,
    });
  }

  // `const` no topo de um script não vira propriedade do objeto global, então os globais
  // são reexpostos aqui para o teste poder alcançá-los de fora do contexto.
  vm.runInContext(
    `globalThis.__ia = { CONFIG_IA, configAtiva, identificarTopicoPelaUrl, MetricasIA,
       ClienteOllama, PromptQuiz, ParserQuiz, ValidadorQuiz, CacheQuiz, ServicoQuiz,
       obterQuiz, BASE_CONHECIMENTO };`,
    contexto
  );

  return { contexto, ia: contexto.__ia, sandbox };
}

// ---------------------------------------------------------------------------
// Mini framework de asserção
// ---------------------------------------------------------------------------
let passou = 0;
let falhou = 0;
const falhas = [];
let grupoAtual = "";

function grupo(nome) {
  grupoAtual = nome;
  console.log(`\n${nome}`);
  console.log("-".repeat(nome.length));
}

function verificar(descricao, condicao, observado) {
  if (condicao) {
    passou++;
    console.log(`  ok    ${descricao}`);
  } else {
    falhou++;
    falhas.push(`${grupoAtual} > ${descricao}` + (observado ? ` (obtido: ${observado})` : ""));
    console.log(`  FALHA ${descricao}${observado ? ` -> obtido: ${observado}` : ""}`);
  }
}

// ---------------------------------------------------------------------------
// Massa de teste
// ---------------------------------------------------------------------------
function questaoBoa(sobrescrever) {
  return Object.assign(
    {
      enunciado: "Qual estrutura substitui a notocorda durante a embriogênese dos vertebrados?",
      alternativas: [
        { id: "a", texto: "O crânio e a coluna vertebral" },
        { id: "b", texto: "As fendas faríngeas" },
        { id: "c", texto: "O tubo nervoso dorsal" },
        { id: "d", texto: "A medula espinhal" },
      ],
      respostaCorreta: "a",
      explicacao:
        "A notocorda é substituída por uma estrutura cartilaginosa ou óssea, o crânio e a coluna vertebral, durante a embriogênese. A opção que aponta o tubo nervoso dorsal é tentadora porque ele também é característica exclusiva dos cordados, mas ele não substitui a notocorda em momento nenhum.",
      conceitoAvaliado: "Notocorda",
    },
    sobrescrever || {}
  );
}

function respostaDoModelo(questoes) {
  return JSON.stringify({ questoes });
}

// ---------------------------------------------------------------------------
// 1. Parser
// ---------------------------------------------------------------------------
function testarParser(ia) {
  grupo("1. Parser tolerante");
  const P = ia.ParserQuiz;

  const limpo = respostaDoModelo([questaoBoa()]);
  let r = P.extrair(limpo);
  verificar("JSON limpo -> estratégia 'direto'", r.ok && r.estrategia === "direto", r.estrategia);

  r = P.extrair("```json\n" + limpo + "\n```");
  verificar("bloco de código ``` -> extrai mesmo assim", r.ok && r.dados.questoes.length === 1, r.estrategia);

  r = P.extrair("Claro! Aqui estão as questões:\n\n" + limpo + "\n\nEspero ter ajudado.");
  verificar("prosa em volta -> estratégia 'recorte'", r.ok && r.estrategia === "recorte", r.estrategia);

  // Truncamento: duas questões inteiras e uma cortada no meio de uma string.
  const truncado =
    '{"questoes":[' +
    JSON.stringify(questaoBoa()) +
    "," +
    JSON.stringify(questaoBoa({ enunciado: "Segunda questão sobre as fendas faríngeas dos cordados?" })) +
    ',{"enunciado":"Terceira questão que foi cortada no meio do texto porque acabou';
  r = P.extrair(truncado);
  verificar(
    "JSON truncado -> aproveita as 2 questões inteiras e descarta a incompleta",
    r.ok && r.estrategia === "reparo" && r.dados.questoes.length === 2,
    r.ok ? `${r.estrategia}, ${r.dados.questoes.length} questões` : r.erro
  );

  r = P.extrair(JSON.stringify([questaoBoa()]));
  verificar("array solto -> embrulhado em {questoes:[...]}", r.ok && r.dados.questoes.length === 1);

  r = P.extrair(JSON.stringify({ perguntas: [questaoBoa()] }));
  verificar("chave com outro nome -> reconhecida", r.ok && r.dados.questoes.length === 1);

  r = P.extrair("Desculpe, não consigo gerar questões sobre esse assunto.");
  verificar("texto sem JSON -> falha explícita", !r.ok && !!r.erro);

  r = P.extrair("");
  verificar("resposta vazia -> falha explícita", !r.ok);
}

// ---------------------------------------------------------------------------
// 2. Validador
// ---------------------------------------------------------------------------
function testarValidador(ia) {
  grupo("2. Validador");
  const V = ia.ValidadorQuiz;
  const topico = ia.BASE_CONHECIMENTO.animais.topicos["filo-cordados"];
  const material = V.normalizar(topico.conteudo);

  function motivo(sobrescrever) {
    const falha = V.validarQuestao(questaoBoa(sobrescrever), material);
    return falha ? falha.motivo : null;
  }

  verificar("questão boa passa", motivo() === null, motivo());

  verificar(
    "3 alternativas -> numero_de_alternativas",
    motivo({ alternativas: questaoBoa().alternativas.slice(0, 3) }) === "numero_de_alternativas",
    motivo({ alternativas: questaoBoa().alternativas.slice(0, 3) })
  );

  verificar(
    "respostaCorreta que não existe -> resposta_correta_inexistente",
    motivo({ respostaCorreta: "z" }) === "resposta_correta_inexistente",
    motivo({ respostaCorreta: "z" })
  );

  verificar("explicação ausente -> campo_faltando", motivo({ explicacao: "" }) === "campo_faltando");
  verificar("conceitoAvaliado ausente -> campo_faltando", motivo({ conceitoAvaliado: "" }) === "campo_faltando");

  verificar(
    "explicação curta demais -> explicacao_trivial",
    motivo({ explicacao: "Porque sim." }) === "explicacao_trivial",
    motivo({ explicacao: "Porque sim." })
  );

  verificar(
    "enunciado curto demais -> enunciado_curto",
    motivo({ enunciado: "Notocorda?" }) === "enunciado_curto",
    motivo({ enunciado: "Notocorda?" })
  );

  const comProibida = questaoBoa().alternativas.slice();
  comProibida[3] = { id: "d", texto: "Todas as anteriores" };
  verificar(
    '"todas as anteriores" -> expressao_proibida',
    motivo({ alternativas: comProibida }) === "expressao_proibida",
    motivo({ alternativas: comProibida })
  );

  const vazando = questaoBoa().alternativas.slice();
  vazando[0] = {
    id: "a",
    texto:
      "O crânio e a coluna vertebral, que são estruturas cartilaginosas ou ósseas formadas durante a embriogênese e que passam a sustentar o corpo no lugar da notocorda",
  };
  verificar(
    "correta muito mais longa que as outras -> vazamento_por_comprimento",
    motivo({ alternativas: vazando }) === "vazamento_por_comprimento",
    motivo({ alternativas: vazando })
  );

  const duplicadas = questaoBoa().alternativas.slice();
  duplicadas[2] = { id: "c", texto: "As fendas faríngeas" };
  verificar(
    "duas alternativas iguais -> alternativas_duplicadas",
    motivo({ alternativas: duplicadas }) === "alternativas_duplicadas",
    motivo({ alternativas: duplicadas })
  );

  const idsRepetidos = questaoBoa().alternativas.slice();
  idsRepetidos[1] = { id: "a", texto: "As fendas faríngeas" };
  verificar(
    "ids repetidos -> ids_duplicados",
    motivo({ alternativas: idsRepetidos }) === "ids_duplicados",
    motivo({ alternativas: idsRepetidos })
  );

  // Citação por letra: as alternativas são embaralhadas antes de exibir, então uma
  // explicação que diz "a alternativa c" fica apontando para a opção errada.
  // Defeito real observado numa geração da Fase 2.
  verificar(
    'explicação com "a alternativa c" -> explicacao_cita_letra',
    motivo({ explicacao: "A notocorda sustenta o corpo do embrião, conforme o material. A alternativa c está errada porque descreve o tubo nervoso dorsal, que é outra estrutura." }) === "explicacao_cita_letra",
    motivo({ explicacao: "A notocorda sustenta o corpo do embrião, conforme o material. A alternativa c está errada porque descreve o tubo nervoso dorsal, que é outra estrutura." })
  );
  verificar(
    'explicação com "opção b)" -> explicacao_cita_letra',
    motivo({ explicacao: "O material define a notocorda como bastão cilíndrico e maciço que sustenta o embrião. Já a opção b) trata das fendas faríngeas, que ficam na faringe." }) === "explicacao_cita_letra"
  );
  verificar(
    'explicação com "letra D" -> explicacao_cita_letra',
    motivo({ explicacao: "A notocorda sustenta o corpo do embrião por ser rígida, como diz o texto. A letra D confunde essa função com a do tubo nervoso dorsal, que forma o encéfalo." }) === "explicacao_cita_letra"
  );
  // Falso positivo que o padrão precisa evitar: "a" é artigo em português.
  verificar(
    '"as alternativas a seguir" NÃO é citação por letra',
    motivo({ explicacao: "A notocorda sustenta o corpo do embrião, segundo o material. As alternativas a seguir confundem essa estrutura com o tubo nervoso dorsal, que tem outra função descrita no texto." }) === null,
    motivo({ explicacao: "A notocorda sustenta o corpo do embrião, segundo o material. As alternativas a seguir confundem essa estrutura com o tubo nervoso dorsal, que tem outra função descrita no texto." })
  );

  // Anti-alucinação: conceito que não existe no conteúdo do tópico.
  verificar(
    "conceito inventado -> conceito_fora_do_material",
    motivo({ conceitoAvaliado: "Fotossíntese das plantas vasculares" }) === "conceito_fora_do_material",
    motivo({ conceitoAvaliado: "Fotossíntese das plantas vasculares" })
  );

  verificar(
    "enunciado sobre assunto de outro tópico -> enunciado_fora_do_material",
    motivo({
      enunciado: "Qual pigmento realiza a fotossíntese nos cloroplastos das briófitas terrestres?",
      alternativas: [
        { id: "a", texto: "Clorofila presente nos cloroplastos" },
        { id: "b", texto: "Hemoglobina presente no sangue" },
        { id: "c", texto: "Hemocianina presente na hemolinfa" },
        { id: "d", texto: "Melanina presente na epiderme" },
      ],
      conceitoAvaliado: "Notocorda",
    }) === "enunciado_fora_do_material",
    motivo({
      enunciado: "Qual pigmento realiza a fotossíntese nos cloroplastos das briófitas terrestres?",
      alternativas: [
        { id: "a", texto: "Clorofila presente nos cloroplastos" },
        { id: "b", texto: "Hemoglobina presente no sangue" },
        { id: "c", texto: "Hemocianina presente na hemolinfa" },
        { id: "d", texto: "Melanina presente na epiderme" },
      ],
      conceitoAvaliado: "Notocorda",
    })
  );

  // Lote misto: as boas passam, as ruins caem, nada é aceito em silêncio.
  const lote = {
    questoes: [
      questaoBoa(),
      questaoBoa({ enunciado: "As fendas faríngeas permanecem no adulto em quais cordados?", conceitoAvaliado: "Fendas Faríngeas" }),
      questaoBoa({ alternativas: questaoBoa().alternativas.slice(0, 2) }),
      questaoBoa({ explicacao: "" }),
    ],
  };
  const resultado = V.validarLote(lote, topico);
  verificar(
    "lote com 2 boas e 2 ruins -> aprova 2 e recusa 2",
    resultado.aprovadas.length === 2 && resultado.rejeicoes.length === 2,
    `${resultado.aprovadas.length} aprovadas, ${resultado.rejeicoes.length} recusadas`
  );
  verificar("cada recusa vem com motivo", resultado.rejeicoes.every((r) => !!r.motivo && !!r.detalhe));
}

// ---------------------------------------------------------------------------
// 3. Cache
// ---------------------------------------------------------------------------
function testarCache(ia) {
  grupo("3. Cache");
  const C = ia.CacheQuiz;
  C.limpar();

  C.guardar("animais", "filo-cordados", [questaoBoa()], "modelo-de-teste");
  verificar("guarda e devolve", C.obter("animais", "filo-cordados", 5).length === 1);

  const repetido = C.guardar("animais", "filo-cordados", [questaoBoa()], "modelo-de-teste");
  verificar(
    "enunciado repetido é descartado por hash",
    repetido.guardadas === 0 && repetido.duplicadas === 1,
    `${repetido.guardadas} guardadas, ${repetido.duplicadas} duplicadas`
  );

  C.guardar("animais", "filo-cordados", [questaoBoa({ enunciado: "Outra pergunta bem diferente sobre cordados?", conceitoAvaliado: "Fendas Faríngeas" })], "m");
  verificar("segunda questão distinta entra", C.obter("animais", "filo-cordados", 5).length === 2);

  const conceitos = C.conceitosGuardados("animais", "filo-cordados", 10);
  verificar(
    "conceitos guardados alimentam conceitosExcluir",
    conceitos.indexOf("Notocorda") !== -1 && conceitos.indexOf("Fendas Faríngeas") !== -1,
    conceitos.join(", ")
  );

  verificar("tópico sem cache devolve lista vazia", C.obter("plantas", "briofitas", 5).length === 0);
  verificar("estatísticas contam as questões", C.estatisticas().total === 2, String(C.estatisticas().total));
  C.limpar();
  verificar("limpar esvazia o banco", C.estatisticas().total === 0);
}

// ---------------------------------------------------------------------------
// 4. Serviço e cascata de fallback
// ---------------------------------------------------------------------------
async function testarServico(ia, sandbox) {
  grupo("4. Serviço: cascata IA -> cache -> quiz fixo");

  const quizFixo = [
    {
      title: "Cordados",
      type: "multiple",
      question: "Pergunta fixa original do site",
      explanation: "Explicação fixa original.",
      options: [
        { text: "a", correct: false },
        { text: "b", correct: true },
        { text: "c", correct: false },
        { text: "d", correct: false },
      ],
    },
  ];

  // Dubla o daemon: /api/tags responde com o modelo configurado, /api/chat responde o
  // que o teste mandar na fila.
  let filaDeRespostas = [];
  let daemonOnline = true;
  let chamadasAoChat = 0;

  sandbox.fetch = async function (url, opcoes) {
    if (!daemonOnline) throw new TypeError("failed to fetch");
    if (String(url).indexOf("/api/tags") !== -1) {
      return {
        ok: true,
        json: async () => ({ models: [{ name: ia.configAtiva().modelo }] }),
      };
    }
    chamadasAoChat++;
    const proxima = filaDeRespostas.shift();
    if (proxima === undefined) throw new TypeError("fila de respostas vazia");
    if (proxima.status && proxima.status !== 200) {
      return { ok: false, status: proxima.status, text: async () => proxima.corpo };
    }
    return { ok: true, json: async () => ({ message: { content: proxima.corpo } }) };
  };

  ia.CacheQuiz.limpar();
  ia.MetricasIA.limpar();

  // --- caminho feliz ---
  filaDeRespostas = [
    {
      corpo: respostaDoModelo([
        questaoBoa(),
        questaoBoa({ enunciado: "Em quais cordados as fendas faríngeas permanecem no adulto?", conceitoAvaliado: "Fendas Faríngeas" }),
      ]),
    },
  ];
  let quiz = await ia.obterQuiz("animais", "filo-cordados", { quizFixo, numQuestoes: 2 });
  verificar("IA disponível -> origem 'ia'", quiz.origem === "ia", quiz.origem);
  verificar("devolve as 2 questões", quiz.questoes.length === 2, String(quiz.questoes.length));

  // --- formato do site ---
  const primeira = quiz.questoes[0];
  verificar("formato do site: campos title/type/question/explanation/options",
    typeof primeira.title === "string" && primeira.type === "multiple" &&
    typeof primeira.question === "string" && typeof primeira.explanation === "string" &&
    Array.isArray(primeira.options));
  verificar("4 opções no formato {text, correct}",
    primeira.options.length === 4 && primeira.options.every((o) => typeof o.text === "string" && typeof o.correct === "boolean"));
  verificar("exatamente uma opção correta",
    primeira.options.filter((o) => o.correct).length === 1,
    String(primeira.options.filter((o) => o.correct).length));

  // --- preservação da chave de progresso ---
  verificar(
    "title copiado do quiz fixo, preservando a chave do LocalStorage",
    quiz.questoes.every((q) => q.title === "Cordados"),
    quiz.questoes[0].title
  );

  // --- retentativa com motivo da recusa ---
  ia.CacheQuiz.limpar();
  chamadasAoChat = 0;
  filaDeRespostas = [
    { corpo: "Desculpe, não vou responder em JSON." },
    { corpo: respostaDoModelo([questaoBoa()]) },
  ];
  quiz = await ia.obterQuiz("animais", "filo-cordados", { quizFixo, numQuestoes: 1 });
  verificar("resposta inválida -> tenta de novo e aceita a segunda",
    quiz.origem === "ia" && chamadasAoChat === 2,
    `origem ${quiz.origem}, ${chamadasAoChat} chamadas`);

  // --- todas as tentativas inválidas, sem cache -> quiz fixo ---
  ia.CacheQuiz.limpar();
  filaDeRespostas = [{ corpo: "nada" }, { corpo: "nada" }, { corpo: "nada" }];
  quiz = await ia.obterQuiz("animais", "filo-cordados", { quizFixo, numQuestoes: 2 });
  verificar("IA falha em todas as tentativas e cache vazio -> quiz fixo",
    quiz.origem === "fixo" && quiz.questoes[0].question === "Pergunta fixa original do site",
    quiz.origem);

  // --- Ollama fora do ar, com cache cheio -> cache ---
  ia.CacheQuiz.limpar();
  ia.CacheQuiz.guardar("animais", "filo-cordados", [questaoBoa()], "modelo-de-teste");
  daemonOnline = false;
  quiz = await ia.obterQuiz("animais", "filo-cordados", { quizFixo, numQuestoes: 1 });
  verificar("Ollama offline com cache -> origem 'cache'", quiz.origem === "cache", quiz.origem);
  verificar("questão do cache também sai no formato do site",
    quiz.questoes[0].type === "multiple" && quiz.questoes[0].options.length === 4);

  // --- Ollama fora do ar e cache vazio -> quiz fixo ---
  ia.CacheQuiz.limpar();
  quiz = await ia.obterQuiz("animais", "filo-cordados", { quizFixo, numQuestoes: 1 });
  verificar("Ollama offline e cache vazio -> quiz fixo", quiz.origem === "fixo", quiz.origem);
  daemonOnline = true;

  // --- tópico fora de topicosComIA ---
  quiz = await ia.obterQuiz("plantas", "briofitas", { quizFixo, numQuestoes: 2 });
  verificar("tópico fora de topicosComIA -> quiz fixo", quiz.origem === "fixo", quiz.origem);
  verificar("diagnóstico explica por que não foi elegível",
    /topicosComIA/.test(quiz.diagnostico.motivoNaoElegivel || ""),
    quiz.diagnostico.motivoNaoElegivel);

  // --- tópico curto: elegibilidade negada mesmo se listado ---
  ia.CONFIG_IA.topicosComIA.push("angiospermas");
  const elegibilidade = ia.ServicoQuiz.avaliarElegibilidade("plantas", "angiospermas");
  verificar("tópico com maxQuestoes 0 é recusado mesmo estando na lista",
    elegibilidade.elegivel === false && /insuficiente/.test(elegibilidade.motivo),
    elegibilidade.motivo);
  ia.CONFIG_IA.topicosComIA.pop();

  // --- alvo limitado pelo maxQuestoes do tópico ---
  ia.CacheQuiz.limpar();
  filaDeRespostas = [{ corpo: respostaDoModelo([questaoBoa()]) }];
  quiz = await ia.obterQuiz("animais", "filo-cordados", { quizFixo, numQuestoes: 99 });
  verificar("pedido de 99 questões é limitado ao maxQuestoes do tópico",
    quiz.diagnostico.alvo === ia.BASE_CONHECIMENTO.animais.topicos["filo-cordados"].maxQuestoes,
    String(quiz.diagnostico.alvo));

  // --- erro de assinatura não vira retentativa ---
  ia.CacheQuiz.limpar();
  chamadasAoChat = 0;
  filaDeRespostas = [
    { status: 402, corpo: '{"error":"this model requires a subscription, upgrade for access"}' },
  ];
  quiz = await ia.obterQuiz("animais", "filo-cordados", { quizFixo, numQuestoes: 2 });
  verificar("erro de assinatura não gera retentativa inútil",
    chamadasAoChat === 1 && quiz.origem === "fixo",
    `${chamadasAoChat} chamada(s), origem ${quiz.origem}`);

  // --- métricas ---
  grupo("5. Métricas");
  const resumo = ia.MetricasIA.resumo();
  verificar("contou as gerações", resumo.geracoes > 0, String(resumo.geracoes));
  verificar("contou as questões recebidas e aprovadas",
    resumo.questoesRecebidas > 0 && resumo.questoesAprovadas > 0,
    `${resumo.questoesAprovadas}/${resumo.questoesRecebidas}`);
  verificar("registrou motivos de rejeição", Object.keys(resumo.rejeicoesPorMotivo).length >= 0);
  verificar("registrou a falha de assinatura",
    (resumo.falhasPorTipo || {}).assinatura >= 1,
    JSON.stringify(resumo.falhasPorTipo));
  verificar("calculou latência", resumo.latencia.amostras > 0 && resumo.latencia.medianaMs >= 0);
}

// ---------------------------------------------------------------------------
// 6. Configuração e troca de provedor
// ---------------------------------------------------------------------------
function testarConfiguracao(ia) {
  grupo("6. Configuração e troca cloud <-> local");

  const antes = ia.CONFIG_IA.provedor;

  ia.CONFIG_IA.provedor = "cloud";
  let cfg = ia.configAtiva();
  verificar("provedor cloud resolve o modelo certo", cfg.modelo === "gpt-oss:120b-cloud", cfg.modelo);
  verificar("cloud NÃO envia JSON Schema", cfg.suportaSchema === false, String(cfg.suportaSchema));

  ia.CONFIG_IA.provedor = "local";
  cfg = ia.configAtiva();
  verificar("trocar uma string muda o provedor inteiro", cfg.provedor === "local" && cfg.rotulo === "Ollama local");
  verificar("local envia JSON Schema", cfg.suportaSchema === true, String(cfg.suportaSchema));
  verificar("local tem timeout maior (CPU é lenta)", cfg.timeoutMs > 120000, String(cfg.timeoutMs));

  // O prompt muda sozinho conforme o provedor: instrução de JSON em texto só na nuvem.
  const topico = ia.BASE_CONHECIMENTO.animais.topicos["filo-cordados"];
  let mensagens = ia.PromptQuiz.montarMensagens({ topico, tituloModulo: "Reino Animal", numQuestoes: 2 });
  verificar("no local, o prompt NÃO repete a instrução de formato JSON",
    mensagens[1].content.indexOf("Responda EXATAMENTE neste formato") === -1);

  ia.CONFIG_IA.provedor = "cloud";
  mensagens = ia.PromptQuiz.montarMensagens({ topico, tituloModulo: "Reino Animal", numQuestoes: 2 });
  verificar("na nuvem, o prompt inclui a instrução de formato JSON",
    mensagens[1].content.indexOf("Responda EXATAMENTE neste formato") !== -1);
  verificar("o conteúdo do tópico entra delimitado por <conteudo>",
    mensagens[1].content.indexOf("<conteudo>") !== -1 && mensagens[1].content.indexOf("</conteudo>") !== -1);
  verificar("o prompt manda usar exclusivamente o material",
    /EXCLUSIVAMENTE/.test(mensagens[1].content));
  verificar("o prompt de sistema proíbe conhecimento externo",
    /não usa conhecimento próprio/.test(mensagens[0].content));

  ia.CONFIG_IA.provedor = "cloud";
  const identificado = ia.identificarTopicoPelaUrl(
    "/pages/modulos/topicos/topicos-animais/filo-cordados.html"
  );
  verificar("identifica módulo e tópico pela URL",
    identificado && identificado.moduloId === "animais" && identificado.topicoId === "filo-cordados",
    JSON.stringify(identificado));
  verificar("URL desconhecida devolve null (cai no quiz fixo)",
    ia.identificarTopicoPelaUrl("/qualquer/outra/pagina.html") === null);

  ia.CONFIG_IA.provedor = antes;
}

// ---------------------------------------------------------------------------
// 7. Teste de integração real (--rede)
// ---------------------------------------------------------------------------
async function testarComRede() {
  grupo("7. Integração real com o Ollama (--rede)");

  const { ia, sandbox } = montarContexto();
  sandbox.fetch = fetch; // o fetch de verdade do Node

  const status = await ia.ClienteOllama.verificarDisponibilidade();
  verificar(`daemon online (${status.motivo || "ok"})`, status.online === true, status.motivo);
  if (!status.online) return;
  verificar(`modelo ${ia.configAtiva().modelo} registrado`, status.modeloRegistrado === true, status.motivo);
  if (!status.modeloRegistrado) return;

  ia.CacheQuiz.limpar();
  ia.MetricasIA.limpar();

  const quizFixo = [{ title: "Cordados", type: "multiple", question: "fixa", explanation: "fixa", options: [] }];
  const inicio = Date.now();
  const quiz = await ia.obterQuiz("animais", "filo-cordados", { quizFixo, numQuestoes: 3 });
  const ms = Date.now() - inicio;

  console.log(`\n  origem: ${quiz.origem} | modelo: ${quiz.modelo} | ${ms} ms | ${quiz.questoes.length} questões`);
  const g = quiz.diagnostico.geracao;
  if (g) {
    for (const t of g.tentativas) {
      console.log(
        `  tentativa ${t.tentativa}: ${t.latenciaMs || "-"} ms | parser: ${t.estrategiaParser || t.falha} | ` +
          `recebidas ${t.recebidas || 0} | aprovadas ${t.aprovadas || 0} | recusadas ${(t.rejeicoes || []).length}`
      );
      for (const r of t.rejeicoes || []) console.log(`      recusa [${r.motivo}] ${r.detalhe}`);
    }
  }

  verificar("gerou questões pela IA de verdade", quiz.origem === "ia", quiz.origem);
  verificar("todas passaram pelo validador", quiz.questoes.every((q) => q.options.filter((o) => o.correct).length === 1));

  for (const q of quiz.questoes) {
    console.log(`\n  ${q.question}`);
    q.options.forEach((o, i) => console.log(`    ${String.fromCharCode(65 + i)}) ${o.text}${o.correct ? "   <= correta" : ""}`));
    console.log(`    conceito: ${q.conceitoAvaliado}`);
    console.log(`    explicação: ${q.explanation}`);
  }

  const cache = ia.CacheQuiz.estatisticas();
  verificar("as questões aprovadas foram para o cache", cache.total === quiz.questoes.length,
    `${cache.total} no cache, ${quiz.questoes.length} na tela`);
}

// ---------------------------------------------------------------------------
async function main() {
  console.log("Bateria de testes da camada de IA");
  console.log("=================================");

  const { ia, sandbox } = montarContexto();
  testarParser(ia);
  testarValidador(ia);
  testarCache(ia);
  await testarServico(ia, sandbox);
  testarConfiguracao(ia);

  if (process.argv.indexOf("--rede") !== -1) {
    await testarComRede();
  } else {
    console.log("\n(teste de rede pulado — use --rede para chamar o Ollama de verdade)");
  }

  console.log("\n" + "=".repeat(50));
  console.log(`${passou} passaram, ${falhou} falharam`);
  if (falhas.length) {
    console.log("\nFalhas:");
    for (const f of falhas) console.log("  - " + f);
  }
  process.exitCode = falhou ? 1 : 0;
}

main();
