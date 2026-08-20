/**
 * testar-integracao.js — testes de regressão da Fase 3. Script DE DESENVOLVIMENTO.
 *
 *     node scripts/testar-integracao.js            todos os cenários, sem rede
 *     node scripts/testar-integracao.js --rede     inclui uma geração real pelo Ollama
 *
 * Carrega, para cada tópico, a MESMA sequência de <script> que a página carrega, num
 * contexto `vm` com um DOM mínimo. Isso executa `quiz-engine.js` de verdade — renderizar,
 * responder, enviar, pontuar, resetar e navegar acontecem no código real do site, não numa
 * imitação dele.
 *
 * O DOM daqui é um esqueleto. Para ele não descolar da realidade, os ids usados são
 * conferidos contra o HTML de verdade no primeiro grupo de testes.
 */

"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const RAIZ = path.resolve(__dirname, "..");

// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// DOM mínimo — em scripts/lib/dom-de-teste.js, compartilhado com o teste da Fase 4
// ---------------------------------------------------------------------------
const { criarDom } = require("./lib/dom-de-teste");


/**
 * Monta o esqueleto do quiz com os mesmos ids e classes da página real.
 * A lista vem de docs/00-MAPEAMENTO.md §6 e é conferida contra o HTML no teste 1.
 */
const IDS_DO_QUIZ = [
  "quizTitle", "score", "progressInfo", "progressFill", "questionType", "questionTypeText",
  "questionTitle", "optionsContainer", "trueFalseContainer", "explanation", "explanationText",
  "prevBtn", "nextNavBtn", "resetBtn", "nextBtn",
];

function montarQuiz(dom) {
  const container = dom.document.createElement("div");
  container.setAttribute("class", "quiz-container");
  dom.body.appendChild(container);

  for (const id of IDS_DO_QUIZ) {
    const elemento = dom.document.createElement(id.endsWith("Btn") ? "button" : "div");
    elemento.setAttribute("id", id);
    container.appendChild(elemento);
  }
  const voltar = dom.document.createElement("button");
  voltar.setAttribute("class", "quiz-back-btn");
  container.appendChild(voltar);

  const div2 = dom.document.createElement("div");
  div2.setAttribute("class", "div2");
  div2.appendChild(container);
  return container;
}

// ---------------------------------------------------------------------------
// Carregamento de uma página de tópico
// ---------------------------------------------------------------------------
const PASTAS = {
  animais: "pages/modulos/topicos/topicos-animais",
  plantas: "pages/modulos/topicos/topicos-plantas",
  ecossistemas: "pages/modulos/topicos/topicos-ecossistemas",
};

function scriptsDaPagina(caminhoHtml) {
  const html = fs.readFileSync(path.join(RAIZ, caminhoHtml), "utf8");
  const fontes = [...html.matchAll(/<script src="([^"]+)"><\/script>/g)].map((m) => m[1]);
  const locais = [];
  for (const fonte of fontes) {
    if (/^https?:/.test(fonte)) continue; // Bootstrap por CDN: não participa do quiz
    // Resolve o caminho relativo à pasta da página, inclusive o "../..." torto do site.
    const absoluto = path.posix.normalize(
      path.posix.join(path.posix.dirname(caminhoHtml.replace(/\\/g, "/")), fonte)
    );
    locais.push(absoluto.replace(/^(\.\.\/)+/, ""));
  }
  return locais;
}

function abrirPagina(moduloId, topicoId, opcoes) {
  const configuracoes = opcoes || {};
  const caminhoHtml = `${PASTAS[moduloId]}/${topicoId}.html`;
  const dom = criarDom();
  montarQuiz(dom);

  const armazem = new Map(Object.entries(configuracoes.localStorage || {}));
  const sessao = new Map(Object.entries(configuracoes.sessionStorage || {}));
  const falso = (mapa) => ({
    getItem: (c) => (mapa.has(c) ? mapa.get(c) : null),
    setItem: (c, v) => mapa.set(c, String(v)),
    removeItem: (c) => mapa.delete(c),
    clear: () => mapa.clear(),
  });

  const sandbox = {
    document: dom.document,
    localStorage: falso(armazem),
    sessionStorage: falso(sessao),
    location: { pathname: "/" + caminhoHtml },
    console: configuracoes.silencioso ? { log() {}, error() {}, warn() {} } : console,
    setTimeout, clearTimeout, AbortController, Math, Date, JSON,
    alert: () => {},
    fetch: configuracoes.fetch || (async () => { throw new TypeError("failed to fetch"); }),
  };
  sandbox.globalThis = sandbox;
  const contexto = vm.createContext(sandbox);

  for (const arquivo of scriptsDaPagina(caminhoHtml)) {
    const caminho = path.join(RAIZ, arquivo);
    if (!fs.existsSync(caminho)) throw new Error(`${caminhoHtml} referencia ${arquivo}, que não existe`);
    // particles-content.js mexe em <canvas>, que não existe aqui e nem é parte do quiz.
    if (arquivo.indexOf("particles") !== -1) continue;
    vm.runInContext(fs.readFileSync(caminho, "utf8"), contexto, { filename: arquivo });
  }

  vm.runInContext(
    `globalThis.__estado = () => ({ quizData, currentQuestion, userAnswers, quizSubmitted });
     globalThis.__ia = (typeof CONFIG_IA !== "undefined")
        ? { CONFIG_IA, CacheQuiz, MetricasIA, InterfaceQuizIA, ServicoQuiz } : null;`,
    contexto
  );

  return { dom, contexto, sandbox, armazem, sessao, caminhoHtml };
}

/** Deixa as promessas pendentes da partida assíncrona terminarem. */
function assentar(voltas) {
  return new Promise((resolve) => setTimeout(resolve, voltas || 0));
}

// ---------------------------------------------------------------------------
// Asserções
// ---------------------------------------------------------------------------
let passou = 0, falhou = 0;
const falhas = [];
let grupoAtual = "";

function grupo(nome) {
  grupoAtual = nome;
  console.log(`\n${nome}\n${"-".repeat(nome.length)}`);
}
function verificar(descricao, condicao, observado) {
  if (condicao) { passou++; console.log(`  ok    ${descricao}`); }
  else {
    falhou++;
    falhas.push(`${grupoAtual} > ${descricao}${observado ? ` (obtido: ${observado})` : ""}`);
    console.log(`  FALHA ${descricao}${observado ? ` -> ${observado}` : ""}`);
  }
}

// ---------------------------------------------------------------------------
function respostaValida(n) {
  const questoes = [];
  for (let i = 0; i < n; i++) {
    questoes.push({
      enunciado: `Sobre a notocorda dos cordados, qual afirmação número ${i + 1} está correta?`,
      alternativas: [
        { id: "a", texto: "Bastão cilíndrico e maciço que sustenta o embrião" },
        { id: "b", texto: "Fenda localizada na região da faringe" },
        { id: "c", texto: "Tubo nervoso situado na região ventral" },
        { id: "d", texto: "Escama placóide da pele dos peixes" },
      ],
      respostaCorreta: "a",
      explicacao:
        "O material define a notocorda como bastão cilíndrico e maciço, de células e substância gelatinosa, que sustenta o corpo do embrião. A opção que fala em fendas na faringe confunde a notocorda com as fendas faríngeas, que são outra característica dos cordados.",
      conceitoAvaliado: "Notocorda",
    });
  }
  return JSON.stringify({ questoes });
}

function daemonQue(comportamento) {
  return async function (url, opcoes) {
    if (String(url).indexOf("/api/tags") !== -1) {
      if (comportamento.offline) throw new TypeError("failed to fetch");
      return { ok: true, json: async () => ({ models: [{ name: "gpt-oss:120b-cloud" }] }) };
    }
    if (comportamento.offline) throw new TypeError("failed to fetch");
    if (comportamento.timeout) {
      const erro = new Error("abortado");
      erro.name = "AbortError";
      throw erro;
    }
    if (comportamento.http) {
      return { ok: false, status: comportamento.http, text: async () => "erro interno do servidor" };
    }
    comportamento.chamadas = (comportamento.chamadas || 0) + 1;
    const corpo = Array.isArray(comportamento.respostas)
      ? comportamento.respostas[Math.min(comportamento.chamadas - 1, comportamento.respostas.length - 1)]
      : comportamento.resposta;
    return { ok: true, json: async () => ({ message: { content: corpo } }) };
  };
}

// ===========================================================================
// 1. O esqueleto de DOM confere com o HTML real
// ===========================================================================
function testarFidelidadeDoDom() {
  grupo("1. O DOM de teste confere com o HTML real");
  const html = fs.readFileSync(path.join(RAIZ, PASTAS.animais, "filo-cordados.html"), "utf8");
  const idsNoHtml = [...html.matchAll(/id="([^"]+)"/g)].map((m) => m[1]);
  const faltando = IDS_DO_QUIZ.filter((id) => idsNoHtml.indexOf(id) === -1);
  verificar("todos os ids usados pelo motor existem na página real", faltando.length === 0, faltando.join(", "));
  verificar("a página real tem o .quiz-back-btn", html.indexOf('class="quiz-back-btn"') !== -1);
}

// ===========================================================================
// 2. Regressão: os 21 tópicos
// ===========================================================================
async function testarOs21Topicos() {
  grupo("2. Regressão nos 21 tópicos (Ollama desligado)");

  const topicos = [];
  for (const moduloId of Object.keys(PASTAS)) {
    for (const arquivo of fs.readdirSync(path.join(RAIZ, PASTAS[moduloId]))) {
      if (arquivo.endsWith(".html")) topicos.push({ moduloId, topicoId: arquivo.replace(/\.html$/, "") });
    }
  }
  verificar("21 tópicos encontrados", topicos.length === 21, String(topicos.length));

  let renderizaram = 0, comProgresso = 0, comPontuacao = 0;
  const problemas = [];

  for (const { moduloId, topicoId } of topicos) {
    try {
      const pagina = abrirPagina(moduloId, topicoId, { silencioso: true });
      await assentar(5);

      const doc = pagina.dom.document;
      const titulo = doc.getElementById("questionTitle").textContent;
      const estado = pagina.contexto.__estado();

      if (!titulo || !estado.quizData.length) { problemas.push(`${topicoId}: não renderizou`); continue; }
      renderizaram++;

      // Responde todas as questões e envia, exercitando o motor de verdade.
      for (let i = 0; i < estado.quizData.length; i++) {
        const questao = pagina.contexto.__estado().quizData[i];
        if (questao.type === "multiple") {
          const opcoes = doc.querySelectorAll("#optionsContainer .option");
          if (!opcoes.length) { problemas.push(`${topicoId}: questão ${i} sem opções`); break; }
          opcoes[0].clicar();
        } else {
          const botoes = doc.getElementById("trueFalseContainer").children;
          if (!botoes.length) { problemas.push(`${topicoId}: questão ${i} sem botões V/F`); break; }
          botoes[0].clicar();
        }
        if (i < estado.quizData.length - 1) doc.getElementById("nextNavBtn").clicar();
      }

      doc.getElementById("nextBtn").clicar(); // envia
      const progresso = JSON.parse(pagina.armazem.get("quizProgress") || "{}");
      const chaves = Object.keys(progresso.topics || {});
      if (chaves.length === 1) comProgresso++;
      else problemas.push(`${topicoId}: gravou ${chaves.length} chaves de progresso`);

      const registro = progresso.topics[chaves[0]];
      if (registro && registro.submitted === true && registro.progress === 100) comPontuacao++;
      else problemas.push(`${topicoId}: progresso não fechou em 100%`);
    } catch (erro) {
      problemas.push(`${topicoId}: ${erro.message}`);
    }
  }

  verificar("os 21 renderizaram uma questão", renderizaram === 21, `${renderizaram}/21`);
  verificar("os 21 gravaram progresso sob uma única chave", comProgresso === 21, `${comProgresso}/21`);
  verificar("os 21 registraram envio com 100% de progresso", comPontuacao === 21, `${comPontuacao}/21`);
  if (problemas.length) for (const p of problemas.slice(0, 8)) console.log("        " + p);
}

// ===========================================================================
// 3. Site funcionando com a IA desligada
// ===========================================================================
async function testarSemIA() {
  grupo("3. Site com a IA desligada");

  const pagina = abrirPagina("animais", "filo-cordados", { silencioso: true });
  await assentar(5);
  const doc = pagina.dom.document;
  const estado = pagina.contexto.__estado();

  verificar("caiu no quiz fixo", estado.quizData.length === 2 && estado.quizData[0].origem === "fixo",
    `${estado.quizData.length} questões, origem ${estado.quizData[0].origem}`);
  verificar("o texto do quiz fixo é o original do site",
    estado.quizData[0].question.indexOf("exclusiva dos vertebrados craniados") !== -1);
  verificar("o selo diz que são questões do site",
    (doc.getElementById("ia-selo") || {}).textContent === "📘 Banco de questões do site",
    (doc.getElementById("ia-selo") || {}).textContent);
  verificar("há aviso amigável, sem jargão técnico", (() => {
    const aviso = doc.getElementById("ia-aviso");
    if (!aviso) return false;
    return !/timeout|HTTP|JSON|daemon|fetch|Ollama|erro 5/i.test(aviso.textContent);
  })(), (doc.getElementById("ia-aviso") || {}).textContent);
  verificar("os botões de navegação foram reabilitados",
    doc.getElementById("prevBtn").disabled === true && doc.getElementById("nextNavBtn").disabled === false);

  // Tópico curto: nem tenta IA, nem mostra carregamento.
  const curto = abrirPagina("plantas", "angiospermas", { silencioso: true });
  await assentar(5);
  verificar("tópico curto usa o quiz fixo sem tentar gerar",
    curto.contexto.__estado().quizData[0].origem === undefined ||
    curto.contexto.__estado().quizData.length === 1);
  verificar("tópico curto não mostra aviso de falha",
    curto.dom.document.getElementById("ia-aviso") === null);
  verificar("tópico curto não oferece o botão de gerar novas perguntas",
    (curto.dom.document.getElementById("ia-regerar") || { hidden: true }).hidden === true);
}

// ===========================================================================
// 4. Cascata de fallback com o motor real
// ===========================================================================
async function testarCascata() {
  grupo("4. Cascata de fallback, com o motor renderizando");

  async function cenario(nome, comportamento, extras) {
    const pagina = abrirPagina("animais", "filo-cordados",
      Object.assign({ silencioso: true, fetch: daemonQue(comportamento) }, extras || {}));
    await assentar(15);
    return pagina;
  }

  // --- IA funcionando ---
  let pagina = await cenario("ia", { resposta: respostaValida(5) });
  let estado = pagina.contexto.__estado();
  verificar("IA responde -> 5 questões geradas na tela", estado.quizData.length === 5, String(estado.quizData.length));
  verificar("selo indica origem IA",
    pagina.dom.document.getElementById("ia-selo").textContent.indexOf("geradas por IA") !== -1);
  verificar("o motor renderizou a primeira questão gerada",
    pagina.dom.document.getElementById("questionTitle").textContent.indexOf("notocorda") !== -1);
  verificar("4 opções renderizadas",
    pagina.dom.document.querySelectorAll("#optionsContainer .option").length === 4);
  verificar("botão de gerar novas perguntas visível",
    pagina.dom.document.getElementById("ia-regerar").hidden === false);
  verificar("o quiz gerado foi guardado no cache",
    JSON.parse(pagina.armazem.get("quiz_ia_banco")).topicos["animais/filo-cordados"].questoes.length === 5);

  // --- chave de progresso preservada ---
  const doc = pagina.dom.document;
  doc.querySelectorAll("#optionsContainer .option")[0].clicar();
  const progresso = JSON.parse(pagina.armazem.get("quizProgress"));
  verificar("progresso do quiz gerado grava sob a MESMA chave do quiz fixo",
    Object.keys(progresso.topics)[0] === "cordados", Object.keys(progresso.topics).join(", "));
  verificar("as três chaves de LocalStorage ficam separadas",
    pagina.armazem.has("quizProgress") && pagina.armazem.has("quiz_ia_banco") && pagina.armazem.has("quiz_ia_metricas"),
    [...pagina.armazem.keys()].join(", "));

  // --- Ollama desligado, com cache ---
  const bancoCheio = pagina.armazem.get("quiz_ia_banco");
  pagina = await cenario("cache", { offline: true }, { localStorage: { quiz_ia_banco: bancoCheio } });
  estado = pagina.contexto.__estado();
  verificar("Ollama desligado com cache -> questões do cache na tela",
    estado.quizData.length > 0 && estado.quizData[0].origem === "cache",
    `${estado.quizData.length} questões, origem ${estado.quizData[0].origem}`);
  verificar("aviso explica que são perguntas guardadas",
    /guardadas neste navegador/.test((pagina.dom.document.getElementById("ia-aviso") || {}).textContent || ""));

  // --- Ollama desligado, sem cache ---
  pagina = await cenario("offline", { offline: true });
  estado = pagina.contexto.__estado();
  verificar("Ollama desligado sem cache -> quiz fixo", estado.quizData[0].origem === "fixo", estado.quizData[0].origem);

  // --- timeout ---
  pagina = await cenario("timeout", { timeout: true });
  verificar("timeout -> quiz fixo, sem tela vazia",
    pagina.contexto.__estado().quizData.length === 2 &&
    pagina.dom.document.getElementById("questionTitle").textContent.length > 0);

  // --- erro HTTP ---
  pagina = await cenario("http500", { http: 500 });
  verificar("erro HTTP 500 -> quiz fixo", pagina.contexto.__estado().quizData[0].origem === "fixo");

  // --- resposta que não é JSON ---
  pagina = await cenario("prosa", { resposta: "Claro! Vou explicar sobre os cordados..." });
  verificar("resposta sem JSON -> quiz fixo depois das tentativas",
    pagina.contexto.__estado().quizData[0].origem === "fixo");

  // --- JSON válido, mas recusado pelo validador ---
  const recusavel = JSON.stringify({
    questoes: [{
      enunciado: "Qual é a característica principal da fotossíntese nas plantas vasculares terrestres?",
      alternativas: [
        { id: "a", texto: "Clorofila" }, { id: "b", texto: "Hemoglobina" },
        { id: "c", texto: "Melanina" }, { id: "d", texto: "Queratina" },
      ],
      respostaCorreta: "a",
      explicacao: "A clorofila é o pigmento responsável pela fotossíntese, capturando a energia luminosa necessária para a produção de glicose nas plantas.",
      conceitoAvaliado: "Fotossíntese das plantas",
    }],
  });
  pagina = await cenario("recusado", { resposta: recusavel });
  verificar("questão recusada pelo validador -> quiz fixo",
    pagina.contexto.__estado().quizData[0].origem === "fixo",
    pagina.contexto.__estado().quizData[0].origem);
  const metricas = JSON.parse(pagina.armazem.get("quiz_ia_metricas") || "{}");
  verificar("a recusa foi registrada nas métricas com motivo",
    Object.keys(metricas.rejeicoesPorMotivo || {}).length > 0,
    JSON.stringify(metricas.rejeicoesPorMotivo));

  // --- JSON truncado ---
  const truncado = '{"questoes":[' + respostaValida(1).slice(13, -2) + ',{"enunciado":"cortada no meio';
  pagina = await cenario("truncado", { resposta: truncado });
  verificar("JSON truncado -> aproveita a questão inteira",
    pagina.contexto.__estado().quizData[0].origem === "ia",
    pagina.contexto.__estado().quizData[0].origem);

  // --- primeira resposta inválida, segunda válida ---
  const comportamento = { respostas: ["não é json", respostaValida(3)] };
  pagina = await cenario("retentativa", comportamento);
  verificar("resposta inválida -> nova tentativa e sucesso",
    pagina.contexto.__estado().quizData[0].origem === "ia" && comportamento.chamadas === 2,
    `origem ${pagina.contexto.__estado().quizData[0].origem}, ${comportamento.chamadas} chamadas`);
}

// ===========================================================================
// 5. Recarregar a página e gerar novas perguntas
// ===========================================================================
async function testarSessaoEBotao() {
  grupo("5. Recarregamento da página e botão de gerar novas perguntas");

  const comportamento = { resposta: respostaValida(3) };
  const primeira = abrirPagina("animais", "filo-cordados", { silencioso: true, fetch: daemonQue(comportamento) });
  await assentar(15);
  const enunciadosAntes = primeira.contexto.__estado().quizData.map((q) => q.question);
  const chamadasAntes = comportamento.chamadas;

  // Recarrega: mesmo localStorage E mesmo sessionStorage, como um F5 de verdade.
  const recarregada = abrirPagina("animais", "filo-cordados", {
    silencioso: true,
    fetch: daemonQue(comportamento),
    localStorage: Object.fromEntries(primeira.armazem),
    sessionStorage: Object.fromEntries(primeira.sessao),
  });
  await assentar(15);

  verificar("F5 devolve exatamente as mesmas perguntas",
    JSON.stringify(recarregada.contexto.__estado().quizData.map((q) => q.question)) === JSON.stringify(enunciadosAntes));
  verificar("F5 não chama o modelo de novo", comportamento.chamadas === chamadasAntes,
    `${comportamento.chamadas} chamadas (era ${chamadasAntes})`);

  // Respostas dadas antes do F5 continuam casando com os índices das perguntas.
  primeira.dom.document.querySelectorAll("#optionsContainer .option")[2].clicar();
  const comResposta = abrirPagina("animais", "filo-cordados", {
    silencioso: true,
    fetch: daemonQue(comportamento),
    localStorage: Object.fromEntries(primeira.armazem),
    sessionStorage: Object.fromEntries(primeira.sessao),
  });
  await assentar(15);
  verificar("resposta marcada antes do F5 é restaurada", comResposta.contexto.__estado().userAnswers[0] === 2,
    JSON.stringify(comResposta.contexto.__estado().userAnswers));

  // Botão de gerar novas perguntas.
  const novas = { resposta: respostaValida(2) };
  recarregada.sandbox.fetch = daemonQue(novas);
  recarregada.dom.document.getElementById("ia-regerar").clicar();
  await assentar(15);
  verificar("botão gera um conjunto novo", recarregada.contexto.__estado().quizData.length === 2,
    String(recarregada.contexto.__estado().quizData.length));
  verificar("botão zera o estado do quiz",
    recarregada.contexto.__estado().currentQuestion === 0 &&
    Object.keys(recarregada.contexto.__estado().userAnswers).length === 0);
}

// ===========================================================================
// 6. Pontuação, reset e navegação sobre questões geradas
// ===========================================================================
async function testarMotorComQuestoesGeradas() {
  grupo("6. Pontuação, navegação e reset sobre questões geradas");

  const pagina = abrirPagina("animais", "filo-cordados",
    { silencioso: true, fetch: daemonQue({ resposta: respostaValida(3) }) });
  await assentar(15);
  const doc = pagina.dom.document;

  verificar("progresso mostra 3 questões", doc.getElementById("progressInfo").textContent === "Questão 1 de 3",
    doc.getElementById("progressInfo").textContent);

  doc.getElementById("nextNavBtn").clicar();
  verificar("navegar para a frente muda a questão", pagina.contexto.__estado().currentQuestion === 1);
  doc.getElementById("prevBtn").clicar();
  verificar("navegar para trás volta a questão", pagina.contexto.__estado().currentQuestion === 0);

  // Acerta todas (a correta é sempre "Bastão cilíndrico..." em respostaValida).
  for (let i = 0; i < 3; i++) {
    const opcoes = doc.querySelectorAll("#optionsContainer .option");
    const indiceCorreto = pagina.contexto.__estado().quizData[i].options.findIndex((o) => o.correct);
    opcoes[indiceCorreto].clicar();
    if (i < 2) doc.getElementById("nextNavBtn").clicar();
  }
  doc.getElementById("nextBtn").clicar();

  const modal = doc.querySelector(".confirm-modal-message");
  verificar("modal de resultado mostra a pontuação", modal && /3 de 3/.test(modal.textContent),
    modal ? modal.textContent.slice(0, 60) : "sem modal");
  verificar("progresso gravado como enviado",
    JSON.parse(pagina.armazem.get("quizProgress")).topics.cordados.submitted === true);
  verificar("totalQuestions acompanha o quiz gerado",
    JSON.parse(pagina.armazem.get("quizProgress")).topics.cordados.totalQuestions === 3);

  // Fecha o modal de resultado antes de resetar, como o usuário faria — senão o
  // querySelector seguinte acharia o botão do modal antigo, que ainda está na tela.
  doc.querySelector(".confirm-modal-btn-confirm").clicar();
  verificar("botão 'Ver respostas' fecha o modal", doc.querySelector(".confirm-modal-overlay") === null);

  // Reset.
  doc.getElementById("resetBtn").clicar();
  doc.querySelector(".confirm-modal-btn-confirm").clicar();
  verificar("reset zera as respostas", Object.keys(pagina.contexto.__estado().userAnswers).length === 0);
  verificar("reset não apaga o cache nem as métricas",
    pagina.armazem.has("quiz_ia_banco") && pagina.armazem.has("quiz_ia_metricas"));
}

// ===========================================================================
// 7. Geração real (--rede)
// ===========================================================================
async function testarComRede() {
  grupo("7. Geração real pelo Ollama (--rede)");
  const pagina = abrirPagina("animais", "filo-cordados", { silencioso: true, fetch });
  const inicio = Date.now();
  // Antes da partida assíncrona terminar, quizData ainda é o array fixo original, cujos
  // objetos NÃO têm o campo `origem`. Esperar até `origem` existir é o sinal de que a
  // cascata concluiu — esperar por "fixo" sairia do laço na primeira volta.
  for (let i = 0; i < 600 && pagina.contexto.__estado().quizData[0].origem === undefined; i++) {
    await assentar(200);
  }
  const ms = Date.now() - inicio;
  const estado = pagina.contexto.__estado();
  const doc = pagina.dom.document;

  console.log(`  origem: ${estado.quizData[0].origem} | ${estado.quizData.length} questões | ${ms} ms`);
  verificar("gerou pela IA na página real", estado.quizData[0].origem === "ia", estado.quizData[0].origem);
  verificar("o motor renderizou a questão gerada", doc.getElementById("questionTitle").textContent.length > 20);
  verificar("4 opções na tela", doc.querySelectorAll("#optionsContainer .option").length === 4);
  verificar("uma única correta por questão",
    estado.quizData.every((q) => (q.options || []).filter((o) => o.correct).length === 1));
  console.log(`\n  ${doc.getElementById("questionTitle").textContent}`);
  for (const opcao of doc.querySelectorAll("#optionsContainer .option")) {
    console.log(`    ${opcao.textContent.trim().slice(0, 100)}`);
  }
}

// ---------------------------------------------------------------------------
async function main() {
  console.log("Testes de integração — Fase 3");
  console.log("=============================");

  testarFidelidadeDoDom();
  await testarOs21Topicos();
  await testarSemIA();
  await testarCascata();
  await testarSessaoEBotao();
  await testarMotorComQuestoesGeradas();
  if (process.argv.indexOf("--rede") !== -1) await testarComRede();
  else console.log("\n(geração real pulada — use --rede)");

  console.log("\n" + "=".repeat(50));
  console.log(`${passou} passaram, ${falhou} falharam`);
  if (falhas.length) {
    console.log("\nFalhas:");
    for (const f of falhas) console.log("  - " + f);
  }
  process.exitCode = falhou ? 1 : 0;
}

main();
