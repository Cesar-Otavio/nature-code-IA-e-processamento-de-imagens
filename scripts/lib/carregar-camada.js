/**
 * carregar-camada.js — carrega a camada de IA num contexto `vm` do Node.
 *
 * Módulo de apoio dos scripts de desenvolvimento. Não faz parte do site.
 *
 * Os arquivos de `script/ia/` são scripts clássicos que declaram globais com `const`,
 * exatamente como o navegador os carrega. Aqui eles rodam sem adaptação: o que é medido
 * é o mesmo código que roda na página do aluno.
 */

"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const RAIZ = path.resolve(__dirname, "..", "..");

const ARQUIVOS = [
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

function armazenamentoFalso() {
  const dados = new Map();
  return {
    getItem: (c) => (dados.has(c) ? dados.get(c) : null),
    setItem: (c, v) => dados.set(c, String(v)),
    removeItem: (c) => dados.delete(c),
    clear: () => dados.clear(),
    _dados: dados,
  };
}

/**
 * @param {object} opcoes
 *   fetch       função de rede (por padrão a do Node, isto é, rede de verdade)
 *   silencioso  true para calar o console da camada
 * @returns objeto com os globais da camada e o armazenamento em memória
 */
function carregar(opcoes) {
  const configuracoes = opcoes || {};
  const armazem = armazenamentoFalso();

  const sandbox = {
    localStorage: armazem,
    sessionStorage: armazenamentoFalso(),
    console: configuracoes.silencioso === false ? console : { log() {}, error() {}, warn() {} },
    location: { pathname: "/" },
    setTimeout, clearTimeout, AbortController, Math, Date, JSON,
    fetch: configuracoes.fetch || fetch,
  };
  sandbox.globalThis = sandbox;
  const contexto = vm.createContext(sandbox);

  for (const arquivo of ARQUIVOS) {
    vm.runInContext(fs.readFileSync(path.join(RAIZ, arquivo), "utf8"), contexto, { filename: arquivo });
  }

  // `const` no topo de um script vive no escopo léxico e não vira propriedade do objeto
  // global; esta ponte torna os globais alcançáveis pelo Node.
  vm.runInContext(
    `globalThis.__camada = { CONFIG_IA, configAtiva, MetricasIA, ClienteOllama, PromptQuiz,
       ParserQuiz, ValidadorQuiz, CacheQuiz, ServicoQuiz, obterQuiz, BASE_CONHECIMENTO };`,
    contexto
  );

  return Object.assign({ armazem, contexto }, contexto.__camada);
}

/** Todos os tópicos da base, do maior para o menor volume de texto. */
function topicosPorTamanho(camada) {
  const lista = [];
  for (const moduloId of Object.keys(camada.BASE_CONHECIMENTO)) {
    const modulo = camada.BASE_CONHECIMENTO[moduloId];
    for (const topicoId of Object.keys(modulo.topicos)) {
      const topico = modulo.topicos[topicoId];
      lista.push({
        moduloId,
        topicoId,
        titulo: topico.titulo,
        tituloModulo: modulo.titulo,
        caracteres: topico.metricas.caracteres,
        maxQuestoes: topico.maxQuestoes,
        suficiencia: topico.suficiencia,
        limitadoPor: topico.limitadoPor,
      });
    }
  }
  return lista.sort((a, b) => b.caracteres - a.caracteres);
}

module.exports = { carregar, topicosPorTamanho, RAIZ, ARQUIVOS };
