/**
 * Teste comportamental de script/pdi/analise-folha.js, no Node, sem navegador.
 *
 * Carrega os três scripts da página num contexto isolado (vm) com um DOM mínimo
 * simulado e um fetch falso, e executa um cenário. Chamado por test_interface_web.py:
 *
 *     node interface_pdi.js <raiz-do-repositorio> <cenario> [resposta-real.json]
 *
 * Imprime JSON: {"ok": true} ou {"ok": false, "falhas": [...]}.
 *
 * O DOM simulado torna `innerHTML` uma armadilha: qualquer escrita lança erro.
 */

"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const [raiz, cenario, caminhoRespostaReal] = process.argv.slice(2);

const IDS = [
  "estado-servico", "botao-verificar", "entrada-arquivo", "area-preview", "preview",
  "nome-arquivo", "botao-processar", "botao-remover", "carregando", "erro", "resultado",
  "img-original", "img-mascara", "img-final", "lista-medidas", "lista-classificacao",
  "resumo", "bloco-avisos", "lista-avisos", "tempo",
];

// ---------------------------------------------------------------------------
// DOM mínimo
// ---------------------------------------------------------------------------

function criarElemento(id) {
  const el = {
    id, textContent: "", hidden: false, className: "", disabled: false, value: "",
    dataset: {}, children: [], onerror: null, ouvintes: {}, atributos: {},
    parentElement: null,
    get src() { return this.atributos.src || ""; },
    set src(v) { this.atributos.src = String(v); },
    removeAttribute(nome) { delete this.atributos[nome]; },
    replaceChildren() { this.children = []; },
    append(...nos) { this.children.push(...nos); },
    addEventListener(tipo, f) { (this.ouvintes[tipo] = this.ouvintes[tipo] || []).push(f); },
  };
  Object.defineProperty(el, "innerHTML", {
    set() { throw new Error(`innerHTML usado em #${id}`); },
    get() { return ""; },
  });
  return el;
}

const elementos = {};
for (const id of IDS) elementos[id] = criarElemento(id);
elementos["botao-processar"].disabled = true;
for (const id of ["area-preview", "carregando", "erro", "resultado", "bloco-avisos"]) {
  elementos[id].hidden = true;
}
// Cada imagem de etapa vive numa <figure> com um aviso de indisponibilidade.
const avisos = {};
for (const id of ["img-original", "img-mascara", "img-final"]) {
  avisos[id] = criarElemento(`${id}-aviso`);
  avisos[id].hidden = true;
  elementos[id].parentElement = {
    querySelector: (seletor) => (seletor === ".img-indisponivel" ? avisos[id] : null),
  };
}

const ouvintesDocumento = {};
const ouvintesJanela = {};
const document = {
  getElementById: (id) => {
    if (!elementos[id]) throw new Error(`elemento inexistente: #${id}`);
    return elementos[id];
  },
  createElement: () => criarElemento("(criado)"),
  addEventListener: (tipo, f) => { (ouvintesDocumento[tipo] = ouvintesDocumento[tipo] || []).push(f); },
};

// ---------------------------------------------------------------------------
// URL e fetch falsos
// ---------------------------------------------------------------------------

let contadorBlob = 0;
const criados = [];
const revogados = [];
const URLFalsa = {
  createObjectURL: () => { const u = `blob:falso-${++contadorBlob}`; criados.push(u); return u; },
  revokeObjectURL: (u) => { revogados.push(u); },
};

const errosConsole = [];
const consoleFalso = { error: (...a) => errosConsole.push(a.map(String).join(" ")), log: () => {}, warn: () => {} };

function respostaJson(corpo, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => corpo };
}
function respostaNaoJson(status = 502) {
  return { ok: false, status, json: async () => { throw new SyntaxError("Unexpected token <"); } };
}
const HEALTH_OK = respostaJson({ status: "ok", servico: "nature-code-pdi", versao: "0.1.0", usa_ia: false });

// Roteador do fetch: cada cenário define `rotas`.
let rotas = { health: () => HEALTH_OK, processar: () => respostaJson({}) };
const chamadas = [];
function fetchFalso(url, opcoes = {}) {
  chamadas.push(url);
  const rota = url.endsWith("/health") ? rotas.health : rotas.processar;
  return new Promise((resolver, rejeitar) => {
    if (opcoes.signal) {
      opcoes.signal.addEventListener("abort", () => {
        const e = new Error("abortado"); e.name = "AbortError"; rejeitar(e);
      });
    }
    Promise.resolve().then(() => rota(opcoes)).then((r) => { if (r !== PENDENTE) resolver(r); }, rejeitar);
  });
}
const PENDENTE = Symbol("pendente");
const offline = () => { throw new TypeError("Failed to fetch"); };

// ---------------------------------------------------------------------------
// Carregamento dos scripts
// ---------------------------------------------------------------------------

const errosNaoTratados = [];
process.on("unhandledRejection", (e) => errosNaoTratados.push(String(e && e.stack || e)));
process.on("uncaughtException", (e) => errosNaoTratados.push(String(e && e.stack || e)));

const contexto = vm.createContext({
  document, URL: URLFalsa, fetch: fetchFalso, console: consoleFalso,
  FormData, AbortController, setTimeout, clearTimeout, Promise, Error, TypeError,
  Number, String, Object, Array, Symbol,
  window: { addEventListener: (t, f) => { (ouvintesJanela[t] = ouvintesJanela[t] || []).push(f); } },
});

const codigo = ["config-pdi.js", "validacao-pdi.js", "analise-folha.js"]
  .map((nome) => fs.readFileSync(path.join(raiz, "script", "pdi", nome), "utf-8"))
  .join("\n;\n");
try {
  vm.runInContext(codigo + "\n;globalThis.__CONFIG = CONFIG_PDI;", contexto);
} catch (e) {
  // Erro de sintaxe ou de carregamento: reportado, nunca engolido.
  console.log(JSON.stringify({ ok: false, falhas: [`falha ao carregar os scripts: ${e && e.stack || e}`] }));
  process.exit(0);
}

const esperar = async (n = 20) => { for (let i = 0; i < n; i++) await new Promise((r) => setImmediate(r)); };
const disparar = async (el, tipo, evento = {}) => {
  for (const f of el.ouvintes[tipo] || []) f(evento);
  await esperar();
};
const iniciar = async () => { for (const f of ouvintesDocumento.DOMContentLoaded || []) f(); await esperar(); };
const arquivo = (nome = "folha.jpg", size = 1000) => ({ name: nome, size });
const selecionar = (a) => disparar(elementos["entrada-arquivo"], "change", { target: { files: [a] } });
const clicar = (id) => disparar(elementos[id], "click");

const falhas = [];
function conferir(condicao, mensagem) { if (!condicao) falhas.push(mensagem); }
const E = elementos;

function respostaReal() {
  return JSON.parse(fs.readFileSync(caminhoRespostaReal, "utf-8"));
}

// ---------------------------------------------------------------------------
// Cenários
// ---------------------------------------------------------------------------

const CENARIOS = {
  async api_offline() {
    rotas = { health: offline, processar: offline };
    await iniciar();
    conferir(E["estado-servico"].className.includes("estado-erro"), "estado não indica erro");
    conferir(E["estado-servico"].textContent.includes("python -m src.api"), "mensagem offline sem instrução");

    await selecionar(arquivo());
    conferir(E["botao-processar"].disabled === false, "botão desabilitado com arquivo selecionado e serviço fora");

    await clicar("botao-processar");
    conferir(E.erro.hidden === false, "erro não exibido com serviço fora");
    conferir(E.erro.textContent.includes("não está disponível"), `mensagem inadequada: ${E.erro.textContent}`);
    conferir(!/TypeError|Failed to fetch|stack/i.test(E.erro.textContent), "detalhe técnico na tela");
    conferir(E.carregando.hidden === true, "'processando' ficou visível");
    conferir(E["botao-processar"].disabled === false, "botão ficou desabilitado após a falha");
    conferir(errosConsole.length > 0, "erro não registrado no console");
  },

  async json_invalido() {
    rotas = { health: () => HEALTH_OK, processar: () => respostaNaoJson(502) };
    await iniciar();
    await selecionar(arquivo());
    await clicar("botao-processar");
    conferir(E.erro.hidden === false, "erro não exibido");
    conferir(E.erro.textContent.includes("formato inesperado"), `mensagem: ${E.erro.textContent}`);
    conferir(E.resultado.hidden === true, "resultado exibido com resposta inválida");
    conferir(E["botao-processar"].disabled === false, "botão travado");
    conferir(errosConsole.some((l) => l.includes("não é JSON")), "falha de JSON não registrada no console");
  },

  async json_formato_inesperado() {
    const formatos = [
      { status: "sucesso" },
      { status: "sucesso", caracteristicas: { dimensoes: {}, forma: {}, orientacao: {} }, classificacao: {} },
      { status: "erro" },
      { status: "erro", erro: null },
      { status: "qualquer" },
      [],
      null,
    ];
    await iniciar();
    for (const corpo of formatos) {
      rotas = { health: () => HEALTH_OK, processar: () => respostaJson(corpo) };
      await selecionar(arquivo());
      await clicar("botao-processar");
      const rotulo = JSON.stringify(corpo);
      conferir(E.erro.textContent.includes("formato inesperado"), `${rotulo}: mensagem ${E.erro.textContent}`);
      conferir(E.resultado.hidden === true, `${rotulo}: resultado exibido`);
      conferir(E["lista-medidas"].children.length === 0, `${rotulo}: tela meio montada`);
      conferir(E["botao-processar"].disabled === false, `${rotulo}: botão travado`);
    }
  },

  async erro_da_api_e_nova_tentativa() {
    let vez = 0;
    const real = respostaReal();
    rotas = {
      health: () => HEALTH_OK,
      processar: () => (++vez === 1
        ? respostaJson({ status: "erro", erro: { codigo: "E007", mensagem: "Nenhuma folha detectada." } }, 422)
        : respostaJson(real)),
    };
    await iniciar();
    await selecionar(arquivo("vazia.jpg"));
    await clicar("botao-processar");
    conferir(E.erro.textContent === "Nenhuma folha detectada. (código E007)", `mensagem: ${E.erro.textContent}`);
    conferir(E["botao-processar"].disabled === false, "botão travado após erro da API");

    await selecionar(arquivo("outra.jpg"));
    conferir(E.erro.hidden === true, "erro anterior continuou visível após nova seleção");
    await clicar("botao-processar");
    conferir(E.resultado.hidden === false, "segunda tentativa não exibiu resultado");
  },

  async sucesso_com_resposta_real() {
    const real = respostaReal();
    rotas = { health: () => HEALTH_OK, processar: () => respostaJson(real) };
    await iniciar();
    await selecionar(arquivo());
    await clicar("botao-processar");
    const base = contexto.__CONFIG.urlBase;
    conferir(E.erro.hidden === true, `erro exibido: ${E.erro.textContent}`);
    conferir(E.resultado.hidden === false, "resultado não exibido");
    conferir(E["img-final"].src === base + real.imagens_intermediarias["07-final"], `src final: ${E["img-final"].src}`);
    conferir(E["img-final"].hidden === false, "imagem final escondida");
    conferir(E.resumo.textContent === real.classificacao.resumo, "resumo diferente do da API");
    conferir(E["lista-medidas"].children.length === 7, "medidas incompletas");
    conferir(E["lista-classificacao"].children.length === 5, "classificação incompleta");
    conferir(E["botao-processar"].disabled === false, "botão travado após sucesso");
  },

  async url_de_imagem_maliciosa() {
    const real = respostaReal();
    real.imagens_intermediarias = {
      "00-original": "https://site-malicioso.example/x.png",
      "05-mascara-limpa": "/api/resultado/../../src/api.py",
      "07-final": "javascript:alert(1)",
    };
    rotas = { health: () => HEALTH_OK, processar: () => respostaJson(real) };
    await iniciar();
    await selecionar(arquivo());
    await clicar("botao-processar");
    for (const id of ["img-original", "img-mascara", "img-final"]) {
      conferir(E[id].src === "", `#${id} recebeu src ${E[id].src}`);
      conferir(E[id].hidden === true, `#${id} visível sem URL válida`);
      conferir(avisos[id].hidden === false, `#${id} sem aviso de indisponível`);
    }
    conferir(E.resultado.hidden === false, "medidas deveriam aparecer mesmo sem imagens");
    conferir(errosConsole.some((l) => l.includes("URL de imagem recusada")), "recusa não registrada");
  },

  async imagem_que_falha_ao_carregar() {
    rotas = { health: () => HEALTH_OK, processar: () => respostaJson(respostaReal()) };
    await iniciar();
    await selecionar(arquivo());
    await clicar("botao-processar");
    E["img-final"].onerror();
    conferir(E["img-final"].hidden === true, "imagem quebrada continuou visível");
    conferir(avisos["img-final"].hidden === false, "sem aviso para imagem que não carregou");
  },

  async tempo_esgotado() {
    rotas = { health: () => HEALTH_OK, processar: () => PENDENTE };
    await iniciar();
    contexto.__CONFIG.timeoutMs = 30;
    await selecionar(arquivo());
    await clicar("botao-processar");
    await new Promise((r) => setTimeout(r, 80));
    await esperar();
    conferir(E.erro.textContent.includes("demorou mais"), `mensagem: ${E.erro.textContent}`);
    conferir(E["botao-processar"].disabled === false, "botão travado após tempo esgotado");
    conferir(E.carregando.hidden === true, "'processando' ficou visível");
  },

  async troca_de_imagem_durante_analise() {
    let liberar;
    const real = respostaReal();
    rotas = {
      health: () => HEALTH_OK,
      processar: () => new Promise((r) => { liberar = () => r(respostaJson(real)); }),
    };
    await iniciar();
    await selecionar(arquivo("primeira.jpg"));
    await clicar("botao-processar");
    await selecionar(arquivo("segunda.jpg"));
    if (liberar) liberar();
    await esperar();
    conferir(E.resultado.hidden === true, "resultado da imagem anterior exibido para a nova");
    conferir(E["nome-arquivo"].textContent === "segunda.jpg", "nome do arquivo não trocou");
    conferir(E["botao-processar"].disabled === false, "botão travado após trocar de imagem");
    conferir(E.carregando.hidden === true, "'processando' ficou visível");
  },

  async preview_e_revoke() {
    await iniciar();
    await selecionar(arquivo("a.jpg"));
    const primeiro = E.preview.src;
    await selecionar(arquivo("b.png"));
    conferir(revogados.includes(primeiro), "preview anterior não foi revogado ao trocar");
    conferir(E.preview.src !== primeiro, "preview não trocou");

    const segundo = E.preview.src;
    await selecionar(arquivo("documento.txt"));
    conferir(revogados.includes(segundo), "preview não revogado ao escolher arquivo inválido");
    conferir(E["area-preview"].hidden === true, "preview antigo visível após arquivo inválido");
    conferir(E["botao-processar"].disabled === true, "botão habilitado sem arquivo válido");
    conferir(E.erro.textContent.includes("Formato não suportado"), "sem mensagem de formato");

    await selecionar(arquivo("grande.jpg", 13 * 1024 * 1024));
    conferir(E.erro.textContent.includes("muito grande"), "sem mensagem de tamanho");

    await selecionar(arquivo("c.jpg"));
    const terceiro = E.preview.src;
    await clicar("botao-remover");
    conferir(revogados.includes(terceiro), "preview não revogado ao remover");
    conferir(E.preview.src === "", "preview manteve src após remover");

    await selecionar(arquivo("d.jpg"));
    const quarto = E.preview.src;
    for (const f of ouvintesJanela.pagehide || []) f();
    conferir(revogados.includes(quarto), "preview não revogado ao sair da página");
    conferir(criados.every((u) => revogados.includes(u)), "algum blob nunca foi revogado");
  },
};

(async () => {
  if (!CENARIOS[cenario]) {
    console.log(JSON.stringify({ ok: false, falhas: [`cenário desconhecido: ${cenario}`] }));
    process.exit(2);
  }
  try {
    await CENARIOS[cenario]();
  } catch (e) {
    falhas.push(`exceção no cenário: ${e && e.stack || e}`);
  }
  await esperar();
  for (const e of errosNaoTratados) falhas.push(`exceção não tratada: ${e}`);
  console.log(JSON.stringify({ ok: falhas.length === 0, falhas }));
  process.exit(0);
})();
