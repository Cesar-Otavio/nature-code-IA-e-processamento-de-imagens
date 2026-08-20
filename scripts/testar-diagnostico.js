/**
 * testar-diagnostico.js — testes da página de diagnóstico (Fase 4).
 *
 *     node scripts/testar-diagnostico.js            sem rede
 *     node scripts/testar-diagnostico.js --rede     inclui conexão e geração reais
 *
 * A página é quase toda DOM, e o modo mais comum de ela quebrar é um id trocado entre o
 * HTML e o JavaScript — falha silenciosa, porque `getElementById` devolve null e o
 * código simplesmente não pinta o campo. Por isso o teste mais importante daqui é o
 * cruzamento entre os ids que o JS procura e os ids que o HTML declara.
 *
 * O resto carrega o HTML de verdade num DOM mínimo e aciona a página como um clique
 * acionaria, conferindo o que foi para a tela.
 */

"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");
const { criarDom } = require("./lib/dom-de-teste");

const RAIZ = path.resolve(__dirname, "..");
const HTML = "ferramentas/diagnostico.html";
const JS = "ferramentas/diagnostico.js";

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
// Carrega a página real num DOM mínimo
// ---------------------------------------------------------------------------
function abrirDiagnostico(opcoes) {
  const configuracoes = opcoes || {};
  const html = fs.readFileSync(path.join(RAIZ, HTML), "utf8");
  const corpo = html.slice(html.indexOf("<body>") + 6, html.lastIndexOf("</body>"));

  const dom = criarDom();
  dom.body.innerHTML = corpo; // usa o HTML de verdade, não uma reconstrução

  const armazem = new Map(Object.entries(configuracoes.localStorage || {}));
  const falso = (mapa) => ({
    getItem: (c) => (mapa.has(c) ? mapa.get(c) : null),
    setItem: (c, v) => mapa.set(c, String(v)),
    removeItem: (c) => mapa.delete(c),
    clear: () => mapa.clear(),
  });

  const sandbox = {
    document: dom.document,
    localStorage: falso(armazem),
    sessionStorage: falso(new Map()),
    location: { pathname: "/" + HTML },
    console: configuracoes.silencioso === false ? console : { log() {}, error() {}, warn() {} },
    setTimeout, clearTimeout, AbortController, Math, Date, JSON,
    fetch: configuracoes.fetch || (async () => { throw new TypeError("failed to fetch"); }),
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;
  const contexto = vm.createContext(sandbox);

  for (const arquivo of fontesDaPagina()) {
    vm.runInContext(fs.readFileSync(path.join(RAIZ, arquivo), "utf8"), contexto, { filename: arquivo });
  }

  // Os globais da camada são declarados com `const`, então vivem no escopo léxico do
  // contexto e não viram propriedade do objeto global. Esta ponte os torna alcançáveis
  // pelo teste — é a mesma técnica usada em scripts/testar-camada-ia.js.
  vm.runInContext(
    `globalThis.__ia = { CONFIG_IA, configAtiva, MetricasIA, CacheQuiz, ServicoQuiz,
       ClienteOllama, PromptQuiz, ParserQuiz, ValidadorQuiz, BASE_CONHECIMENTO };`,
    contexto
  );

  return { dom, contexto, sandbox, armazem, doc: dom.document, ia: contexto.__ia };
}

/** Os <script> da página, na ordem, resolvidos a partir de ferramentas/. */
function fontesDaPagina() {
  const html = fs.readFileSync(path.join(RAIZ, HTML), "utf8");
  return [...html.matchAll(/<script src="([^"]+)"><\/script>/g)]
    .map((m) => path.posix.normalize(path.posix.join("ferramentas", m[1])));
}

function assentar(voltas) {
  return new Promise((resolve) => setTimeout(resolve, voltas || 0));
}

function textoDe(pagina, id) {
  const alvo = pagina.doc.getElementById(id);
  return alvo ? alvo.textContent.trim() : null;
}

// ---------------------------------------------------------------------------
// 1. Estrutura: scripts e ids
// ---------------------------------------------------------------------------
function testarEstrutura() {
  grupo("1. Estrutura da página");

  const fontes = fontesDaPagina();
  const faltando = fontes.filter((f) => !fs.existsSync(path.join(RAIZ, f)));
  verificar(`os ${fontes.length} <script> apontam para arquivos existentes`, faltando.length === 0, faltando.join(", "));

  // A ordem de dependência é a mesma das páginas de tópico.
  const esperada = ["base-conhecimento", "config-ia", "metricas-ia", "cliente-ollama",
    "prompt-quiz", "parser-quiz", "validador-quiz", "cache-quiz", "servico-quiz", "diagnostico"];
  const observada = fontes.map((f) => path.basename(f, ".js"));
  verificar("ordem de carregamento respeita as dependências",
    JSON.stringify(observada) === JSON.stringify(esperada), observada.join(" → "));

  // O cruzamento que importa: todo id procurado pelo JS existe no HTML?
  const js = fs.readFileSync(path.join(RAIZ, JS), "utf8");
  const html = fs.readFileSync(path.join(RAIZ, HTML), "utf8");
  const idsNoHtml = new Set([...html.matchAll(/id="([^"]+)"/g)].map((m) => m[1]));

  const procurados = new Set();
  for (const padrao of [
    /elemento\("([^"]+)"\)/g,
    /texto\(\s*"([^"]+)"/g,
    /selo\(\s*"([^"]+)"/g,
    /listaContada\(\s*"([^"]+)"/g,
    /ligar\("([^"]+)"/g,
    /getElementById\("([^"]+)"\)/g,
  ]) {
    for (const achado of js.matchAll(padrao)) procurados.add(achado[1]);
  }
  // Ids montados por template no código, conferidos à parte.
  for (const nome of ["ia", "cache", "fixo"]) procurados.add(`origem-cartao-${nome}`);

  const semHtml = [...procurados].filter((id) => !idsNoHtml.has(id));
  verificar(`os ${procurados.size} ids usados pelo JS existem no HTML`, semHtml.length === 0, semHtml.join(", "));

  verificar("a página não referencia nenhum CSS do site",
    html.indexOf('<link rel="stylesheet"') === -1);
  verificar("nenhuma página do site aponta para o diagnóstico", (() => {
    const raiz = require("child_process");
    let achou = false;
    const varrer = (dir) => {
      for (const nome of fs.readdirSync(path.join(RAIZ, dir))) {
        const relativo = `${dir}/${nome}`;
        const completo = path.join(RAIZ, relativo);
        if (fs.statSync(completo).isDirectory()) varrer(relativo);
        else if (nome.endsWith(".html") && fs.readFileSync(completo, "utf8").indexOf("diagnostico.html") !== -1) achou = true;
      }
    };
    varrer("pages");
    return !achou;
  })());
}

// ---------------------------------------------------------------------------
// 2. Painéis com o armazenamento vazio
// ---------------------------------------------------------------------------
function testarPaineisVazios() {
  grupo("2. Painéis com armazenamento vazio");

  const pagina = abrirDiagnostico();

  verificar("provedor exibido", textoDe(pagina, "cfg-provedor") === "cloud — Ollama Cloud", textoDe(pagina, "cfg-provedor"));
  verificar("modelo exibido", textoDe(pagina, "cfg-modelo") === "gpt-oss:120b-cloud", textoDe(pagina, "cfg-modelo"));
  verificar("endpoint exibido", textoDe(pagina, "cfg-host") === "http://localhost:11434", textoDe(pagina, "cfg-host"));
  verificar("limitação do JSON Schema declarada na tela",
    /não respeitado/.test(textoDe(pagina, "cfg-schema") || ""), textoDe(pagina, "cfg-schema"));
  verificar("observação explica o contorno e como religar o schema",
    /provedor.*local/i.test(textoDe(pagina, "cfg-observacao") || ""));
  verificar("teto de tokens exibido", textoDe(pagina, "cfg-tokens") === "4500", textoDe(pagina, "cfg-tokens"));

  verificar("contadores de origem começam em zero",
    textoDe(pagina, "origem-ia") === "0" && textoDe(pagina, "origem-cache") === "0" && textoDe(pagina, "origem-fixo") === "0");
  verificar("cartões sem ocorrência ficam apagados",
    pagina.doc.getElementById("origem-cartao-ia").className.indexOf("apagada") !== -1);
  verificar("sem fallback registrado, o painel diz isso",
    /Nenhum fallback/.test(textoDe(pagina, "motivos-fallback") || ""));

  verificar("tabela lista os 21 tópicos",
    pagina.doc.getElementById("tabela-topicos").children.length === 21,
    String(pagina.doc.getElementById("tabela-topicos").children.length));
  verificar("o tópico habilitado aparece destacado", (() => {
    const linhas = pagina.doc.getElementById("tabela-topicos").children;
    const destacadas = linhas.filter((l) => l.className.indexOf("habilitado") !== -1);
    return destacadas.length === 1 && destacadas[0].textContent.indexOf("Cordados") !== -1;
  })());
  verificar("os 5 tópicos sem conteúdo aparecem marcados como quiz fixo", (() => {
    const linhas = pagina.doc.getElementById("tabela-topicos").children;
    return linhas.filter((l) => l.className.indexOf("sem-ia") !== -1).length === 5;
  })());
  verificar("resumo dos tópicos cita o habilitado",
    /filo-cordados/.test(textoDe(pagina, "topicos-resumo") || ""), textoDe(pagina, "topicos-resumo"));

  verificar("seletor de módulos preenchido",
    pagina.doc.getElementById("sel-modulo").children.length === 3);
  verificar("seletor de tópicos preenchido com o módulo inicial",
    pagina.doc.getElementById("sel-topico").children.length === 10,
    String(pagina.doc.getElementById("sel-topico").children.length));
  verificar("tópico sem conteúdo suficiente vem desabilitado no seletor", (() => {
    const pag = abrirDiagnostico();
    pag.doc.getElementById("sel-modulo").value = "plantas";
    pag.contexto.Diagnostico.atualizarTudo();
    // repovoa o seletor de tópicos para o módulo de plantas
    pag.doc.getElementById("sel-modulo").ouvintes.change[0]();
    const opcoes = pag.doc.getElementById("sel-topico").children;
    const angiospermas = opcoes.filter((o) => o.value === "angiospermas")[0];
    return angiospermas && angiospermas.disabled === true;
  })());
}

// ---------------------------------------------------------------------------
// 3. Painéis com métricas semeadas
// ---------------------------------------------------------------------------
function testarPaineisComDados() {
  grupo("3. Painéis com métricas acumuladas");

  const metricas = {
    versao: 1,
    geracoes: 12, falhasDeChamada: 3,
    questoesRecebidas: 45, questoesAprovadas: 40,
    rejeicoesPorMotivo: { vazamento_por_comprimento: 4, conceito_fora_do_material: 1 },
    estrategiasDoParser: { direto: 10, reparo: 2 },
    falhasPorTipo: { rede: 2, assinatura: 1 },
    latenciasMs: [4000, 6000, 7000, 8000, 12000],
    porModelo: { "gpt-oss:120b-cloud": { geracoes: 12, aprovadas: 40 } },
    origens: { ia: 8, cache: 2, fixo: 5 },
    motivosDeFallback: { "Ollama fora do ar": 4, "questões recusadas pelo validador": 3 },
    primeiroRegistro: "2026-08-20T00:00:00.000Z",
    ultimoRegistro: "2026-08-20T01:00:00.000Z",
  };
  const banco = {
    versao: 1,
    topicos: { "animais/filo-cordados": { atualizadoEm: "2026-08-20T01:00:00.000Z", questoes: [
      { hash: "a1", criadoEm: "2026-08-20T01:00:00.000Z", conceitoAvaliado: "Notocorda", questao: {} },
      { hash: "b2", criadoEm: "2026-08-20T01:00:00.000Z", conceitoAvaliado: "Aves", questao: {} },
    ] } },
  };

  const pagina = abrirDiagnostico({
    localStorage: {
      quiz_ia_metricas: JSON.stringify(metricas),
      quiz_ia_banco: JSON.stringify(banco),
      quizProgress: JSON.stringify({ topics: { cordados: { submitted: true } } }),
    },
  });

  verificar("chamadas ao modelo", textoDe(pagina, "met-chamadas") === "12", textoDe(pagina, "met-chamadas"));
  verificar("erros de chamada", textoDe(pagina, "met-erros") === "3", textoDe(pagina, "met-erros"));
  verificar("questões recebidas", textoDe(pagina, "met-recebidas") === "45", textoDe(pagina, "met-recebidas"));
  verificar("questões aprovadas", textoDe(pagina, "met-aprovadas") === "40", textoDe(pagina, "met-aprovadas"));
  verificar("questões rejeitadas calculadas", textoDe(pagina, "met-rejeitadas") === "5", textoDe(pagina, "met-rejeitadas"));
  verificar("taxa de aprovação", textoDe(pagina, "met-taxa") === "88.9%", textoDe(pagina, "met-taxa"));
  verificar("barra da taxa proporcional",
    pagina.doc.getElementById("met-taxa-barra").style.width.indexOf("88.8") === 0,
    pagina.doc.getElementById("met-taxa-barra").style.width);

  verificar("latência média", textoDe(pagina, "lat-media") === "7.4 s", textoDe(pagina, "lat-media"));
  verificar("latência mediana", textoDe(pagina, "lat-mediana") === "7.0 s", textoDe(pagina, "lat-mediana"));
  verificar("p95", textoDe(pagina, "lat-p95") === "12.0 s", textoDe(pagina, "lat-p95"));
  verificar("amostras de latência", textoDe(pagina, "lat-amostras") === "5");

  verificar("origem IA", textoDe(pagina, "origem-ia") === "8", textoDe(pagina, "origem-ia"));
  verificar("origem cache", textoDe(pagina, "origem-cache") === "2", textoDe(pagina, "origem-cache"));
  verificar("origem quiz fixo", textoDe(pagina, "origem-fixo") === "5", textoDe(pagina, "origem-fixo"));
  verificar("total de quizzes servidos", /15 quizzes/.test(textoDe(pagina, "origem-total") || ""), textoDe(pagina, "origem-total"));
  verificar("barra de origem tem três fatias",
    pagina.doc.getElementById("origem-barra").children.length === 3);
  verificar("cartões com ocorrência não ficam apagados",
    pagina.doc.getElementById("origem-cartao-ia").className.indexOf("apagada") === -1);

  verificar("motivos de fallback listados",
    /Ollama fora do ar/.test(textoDe(pagina, "motivos-fallback") || ""), textoDe(pagina, "motivos-fallback"));
  verificar("motivos de rejeição listados",
    /vazamento_por_comprimento/.test(textoDe(pagina, "met-rejeicoes") || ""));
  verificar("estratégias do parser listadas",
    /direto/.test(textoDe(pagina, "met-parser") || "") && /reparo/.test(textoDe(pagina, "met-parser") || ""));
  verificar("erros por tipo listados",
    /assinatura/.test(textoDe(pagina, "met-erros-tipo") || ""));
  verificar("uso por modelo listado",
    /gpt-oss:120b-cloud/.test(textoDe(pagina, "met-por-modelo") || ""));

  verificar("cache: total de questões", textoDe(pagina, "cache-total") === "2", textoDe(pagina, "cache-total"));
  verificar("cache: por tópico", /animais\/filo-cordados/.test(textoDe(pagina, "cache-topicos") || ""));

  // Limpeza não pode encostar no progresso do aluno.
  pagina.contexto.Diagnostico.limparCache();
  verificar("limpar cache esvazia o banco", textoDe(pagina, "cache-total") === "0", textoDe(pagina, "cache-total"));
  verificar("limpar cache NÃO apaga o progresso do aluno", pagina.armazem.has("quizProgress"));

  pagina.contexto.Diagnostico.limparMetricas();
  verificar("zerar métricas zera os contadores", textoDe(pagina, "met-chamadas") === "0", textoDe(pagina, "met-chamadas"));
  verificar("zerar métricas NÃO apaga o progresso do aluno", pagina.armazem.has("quizProgress"));
  verificar("aviso confirma que o progresso foi preservado",
    /quizProgress/.test(textoDe(pagina, "cache-aviso") || ""), textoDe(pagina, "cache-aviso"));
}

// ---------------------------------------------------------------------------
// 4. Teste de conexão
// ---------------------------------------------------------------------------
async function testarConexao() {
  grupo("4. Botão de teste de conexão");

  const online = async function (url) {
    if (String(url).indexOf("/api/tags") !== -1) {
      return { ok: true, json: async () => ({ models: [{ name: "gpt-oss:120b-cloud" }, { name: "gemma4:cloud" }] }) };
    }
    return { ok: true, json: async () => ({ message: { content: "ok" } }) };
  };

  let pagina = abrirDiagnostico({ fetch: online });
  await pagina.contexto.Diagnostico.testarConexao();
  verificar("status online", textoDe(pagina, "con-status") === "online", textoDe(pagina, "con-status"));
  verificar("modelo registrado", textoDe(pagina, "con-modelo") === "registrado", textoDe(pagina, "con-modelo"));
  verificar("latência do /api/tags medida", /ms|s$/.test(textoDe(pagina, "con-latencia") || ""), textoDe(pagina, "con-latencia"));
  verificar("latência de uma geração medida", textoDe(pagina, "con-latencia-chat") !== "—", textoDe(pagina, "con-latencia-chat"));
  verificar("lista os modelos registrados e marca o em uso",
    /gemma4:cloud/.test(textoDe(pagina, "con-modelos") || "") && /em uso/.test(textoDe(pagina, "con-modelos") || ""));

  pagina = abrirDiagnostico({ fetch: async () => { throw new TypeError("failed to fetch"); } });
  await pagina.contexto.Diagnostico.testarConexao();
  verificar("daemon fora do ar -> status offline", textoDe(pagina, "con-status") === "offline", textoDe(pagina, "con-status"));
  verificar("offline explica o motivo", (textoDe(pagina, "con-detalhe") || "").length > 0, textoDe(pagina, "con-detalhe"));

  const pago = async function (url) {
    if (String(url).indexOf("/api/tags") !== -1) {
      return { ok: true, json: async () => ({ models: [{ name: "gpt-oss:120b-cloud" }] }) };
    }
    return { ok: false, status: 402, text: async () => '{"error":"this model requires a subscription, upgrade for access"}' };
  };
  pagina = abrirDiagnostico({ fetch: pago });
  await pagina.contexto.Diagnostico.testarConexao();
  verificar("erro de assinatura é identificado como tal",
    /assinatura|plano pago/.test(textoDe(pagina, "con-detalhe") || ""), textoDe(pagina, "con-detalhe"));
}

// ---------------------------------------------------------------------------
// 5. Gerador manual
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

async function testarGeradorManual() {
  grupo("5. Gerador manual");

  function daemon(corpo) {
    return async function (url) {
      if (String(url).indexOf("/api/tags") !== -1) {
        return { ok: true, json: async () => ({ models: [{ name: "gpt-oss:120b-cloud" }] }) };
      }
      return { ok: true, json: async () => ({ message: { content: corpo } }) };
    };
  }

  /**
   * Seleciona o tópico no formulário. É obrigatório: o seletor abre no primeiro tópico
   * do primeiro módulo (reino-animalia), e a massa de teste fala de notocorda — sem
   * escolher Cordados, o validador recusa tudo por conceito_fora_do_material, que aliás
   * é a checagem anti-alucinação funcionando corretamente.
   */
  function escolher(pagina, moduloId, topicoId, quantas) {
    pagina.doc.getElementById("sel-modulo").value = moduloId;
    pagina.doc.getElementById("sel-topico").value = topicoId;
    pagina.doc.getElementById("inp-questoes").value = String(quantas);
  }

  // --- geração bem-sucedida ---
  let pagina = abrirDiagnostico({ fetch: daemon(respostaValida(3)) });
  escolher(pagina, "animais", "filo-cordados", 3);
  await pagina.contexto.Diagnostico.gerarManual();

  verificar("coluna 1 mostra o prompt enviado, com system e user",
    /### system/.test(textoDe(pagina, "col-prompt") || "") && /### user/.test(textoDe(pagina, "col-prompt") || ""));
  verificar("o prompt mostrado contém o conteúdo do tópico delimitado",
    /<conteudo>/.test(textoDe(pagina, "col-prompt") || ""));
  verificar("coluna 2 mostra o JSON cru recebido",
    /"questoes"/.test(textoDe(pagina, "col-cru") || ""));
  verificar("coluna 3 mostra a estratégia do parser",
    /direto/.test(textoDe(pagina, "col-validacao") || ""), textoDe(pagina, "col-validacao"));
  verificar("coluna 3 informa se o schema foi enviado",
    /Schema enviado/.test(textoDe(pagina, "col-validacao") || ""));
  verificar("coluna 3 conta recebidas e aprovadas",
    /Aprovadas3|Aprovadas\s*3/.test((textoDe(pagina, "col-validacao") || "").replace(/\s+/g, " ")),
    (textoDe(pagina, "col-validacao") || "").replace(/\s+/g, " ").slice(0, 120));
  verificar("as 3 questões aprovadas foram renderizadas",
    pagina.doc.getElementById("ger-questoes").children.length === 3,
    String(pagina.doc.getElementById("ger-questoes").children.length));
  verificar("a alternativa correta vem destacada", (() => {
    const cartao = pagina.doc.getElementById("ger-questoes").children[0];
    return !!cartao && cartao.querySelectorAll(".correta").length === 1;
  })());
  verificar("status final resume aprovadas e tempo",
    /3 de 3 aprovadas/.test(textoDe(pagina, "ger-status") || ""), textoDe(pagina, "ger-status"));
  verificar("a geração entrou nas métricas", textoDe(pagina, "met-chamadas") === "1", textoDe(pagina, "met-chamadas"));
  verificar("sem marcar a caixa, o cache NÃO é alimentado",
    textoDe(pagina, "cache-total") === "0", textoDe(pagina, "cache-total"));

  // --- com a caixa marcada ---
  pagina = abrirDiagnostico({ fetch: daemon(respostaValida(2)) });
  escolher(pagina, "animais", "filo-cordados", 2);
  pagina.doc.getElementById("chk-cache").checked = true;
  await pagina.contexto.Diagnostico.gerarManual();
  verificar("com a caixa marcada, as aprovadas vão para o cache",
    textoDe(pagina, "cache-total") === "2", textoDe(pagina, "cache-total"));

  // --- resposta sem JSON ---
  pagina = abrirDiagnostico({ fetch: daemon("Claro! Vou falar sobre cordados.") });
  escolher(pagina, "animais", "filo-cordados", 2);
  await pagina.contexto.Diagnostico.gerarManual();
  verificar("resposta sem JSON: a coluna 3 mostra o erro do parser",
    /Erro do parser/.test(textoDe(pagina, "col-validacao") || ""), textoDe(pagina, "col-validacao"));
  verificar("resposta sem JSON: nenhuma questão renderizada",
    /Nenhuma questão/.test(textoDe(pagina, "ger-questoes") || ""));
  verificar("resposta sem JSON: a resposta crua fica visível para inspeção",
    /Claro!/.test(textoDe(pagina, "col-cru") || ""));

  // --- questão recusada pelo validador ---
  const recusavel = JSON.stringify({ questoes: [{
    enunciado: "Qual pigmento realiza a fotossíntese nos cloroplastos das briófitas terrestres?",
    alternativas: [
      { id: "a", texto: "Clorofila" }, { id: "b", texto: "Hemoglobina" },
      { id: "c", texto: "Melanina" }, { id: "d", texto: "Queratina" },
    ],
    respostaCorreta: "a",
    explicacao: "A clorofila é o pigmento responsável pela fotossíntese nas plantas, capturando energia luminosa para produzir glicose ao longo do processo.",
    conceitoAvaliado: "Fotossíntese das briófitas",
  }] });
  pagina = abrirDiagnostico({ fetch: daemon(recusavel) });
  escolher(pagina, "animais", "filo-cordados", 1);
  await pagina.contexto.Diagnostico.gerarManual();
  verificar("questão recusada: motivo aparece na coluna 3",
    /conceito_fora_do_material/.test(textoDe(pagina, "col-validacao") || ""), textoDe(pagina, "col-validacao"));
  verificar("questão recusada: nada é renderizado como aprovado",
    /Nenhuma questão/.test(textoDe(pagina, "ger-questoes") || ""));

  // --- falha de rede ---
  pagina = abrirDiagnostico({ fetch: async () => { throw new TypeError("failed to fetch"); } });
  escolher(pagina, "animais", "filo-cordados", 2);
  await pagina.contexto.Diagnostico.gerarManual();
  verificar("falha de rede: status vira erro", /falhou/.test(textoDe(pagina, "ger-status") || ""), textoDe(pagina, "ger-status"));
  verificar("falha de rede: registrada nas métricas", textoDe(pagina, "met-erros") === "1", textoDe(pagina, "met-erros"));
}

// ---------------------------------------------------------------------------
// 6. As novas métricas são alimentadas pelo serviço
// ---------------------------------------------------------------------------
async function testarRegistroDeOrigem() {
  grupo("6. Origem e motivo de fallback registrados pelo serviço");

  const pagina = abrirDiagnostico({ fetch: async () => { throw new TypeError("failed to fetch"); } });
  const quizFixo = [{ title: "Cordados", type: "multiple", question: "fixa", explanation: "fixa", options: [] }];

  await pagina.contexto.obterQuiz("animais", "filo-cordados", { quizFixo });
  await pagina.contexto.obterQuiz("plantas", "briofitas", { quizFixo });

  const resumo = pagina.ia.MetricasIA.resumo();
  verificar("dois quizzes servidos pelo quiz fixo foram contados",
    resumo.origens.fixo === 2, JSON.stringify(resumo.origens));
  verificar("motivo 'Ollama fora do ar' registrado",
    resumo.motivosDeFallback["Ollama fora do ar"] === 1, JSON.stringify(resumo.motivosDeFallback));
  verificar("motivo 'tópico não elegível' registrado",
    Object.keys(resumo.motivosDeFallback).some((m) => /não elegível/.test(m)),
    JSON.stringify(resumo.motivosDeFallback));

  pagina.contexto.Diagnostico.pintarMetricas();
  verificar("a página reflete os dois usos do quiz fixo",
    textoDe(pagina, "origem-fixo") === "2", textoDe(pagina, "origem-fixo"));
  verificar("a página lista os motivos vindos do serviço",
    /Ollama fora do ar/.test(textoDe(pagina, "motivos-fallback") || ""), textoDe(pagina, "motivos-fallback"));
}

// ---------------------------------------------------------------------------
// 7. Rede real
// ---------------------------------------------------------------------------
async function testarComRede() {
  grupo("7. Conexão e geração reais (--rede)");

  const pagina = abrirDiagnostico({ fetch });
  await pagina.contexto.Diagnostico.testarConexao();
  const status = textoDe(pagina, "con-status");
  console.log(`  daemon: ${status} | tags: ${textoDe(pagina, "con-latencia")} | geração: ${textoDe(pagina, "con-latencia-chat")}`);

  // Sem daemon no ar não há o que medir. Isso é ambiente, não defeito: em vez de
  // acusar falhas que não existem no código, o grupo é pulado com aviso.
  if (status !== "online") {
    console.log("  AVISO  o daemon do Ollama não está no ar — grupo pulado.");
    console.log("         abra o Ollama e rode de novo para exercitar a geração real.");
    return;
  }

  verificar("conexão real: modelo registrado", textoDe(pagina, "con-modelo") === "registrado");
  verificar("latência de uma geração real foi medida", textoDe(pagina, "con-latencia-chat") !== "—");

  pagina.doc.getElementById("sel-modulo").value = "animais";
  pagina.doc.getElementById("sel-topico").value = "filo-cordados";
  pagina.doc.getElementById("inp-questoes").value = "2";
  await pagina.contexto.Diagnostico.gerarManual();
  console.log(`  gerador: ${textoDe(pagina, "ger-status")}`);

  // Conta cartões de questão, e não filhos quaisquer: o contêiner já nasce com um nó
  // de texto ("Nenhuma geração feita..."), então children.length > 0 daria positivo
  // mesmo com a geração tendo falhado. Foi exatamente o falso positivo observado aqui.
  const cartoes = pagina.doc.getElementById("ger-questoes").querySelectorAll(".questao");
  verificar("geração real produziu cartões de questão na página", cartoes.length > 0, String(cartoes.length));
  verificar("a resposta crua do modelo ficou visível", (textoDe(pagina, "col-cru") || "").length > 50);
  verificar("cada questão tem exatamente uma correta destacada",
    cartoes.length > 0 && cartoes.every((c) => c.querySelectorAll(".correta").length === 1));

  if (cartoes.length) console.log(`
  ${cartoes[0].children[0].textContent}`);
}

// ---------------------------------------------------------------------------
async function main() {
  console.log("Testes da página de diagnóstico — Fase 4");
  console.log("=======================================");

  testarEstrutura();
  testarPaineisVazios();
  testarPaineisComDados();
  await testarConexao();
  await testarGeradorManual();
  await testarRegistroDeOrigem();
  if (process.argv.indexOf("--rede") !== -1) await testarComRede();
  else console.log("\n(conexão e geração reais puladas — use --rede)");

  console.log("\n" + "=".repeat(50));
  console.log(`${passou} passaram, ${falhou} falharam`);
  if (falhas.length) {
    console.log("\nFalhas:");
    for (const f of falhas) console.log("  - " + f);
  }
  process.exitCode = falhou ? 1 : 0;
}

main();
