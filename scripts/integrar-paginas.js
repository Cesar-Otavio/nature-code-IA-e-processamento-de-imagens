/**
 * integrar-paginas.js — insere (ou remove) os <script> da camada de IA nos 21 HTMLs
 * de tópico. Script DE DESENVOLVIMENTO; não faz parte do site em execução.
 *
 *     node scripts/integrar-paginas.js              insere
 *     node scripts/integrar-paginas.js --verificar  só relata o estado, não escreve
 *     node scripts/integrar-paginas.js --reverter   remove tudo o que foi inserido
 *
 * Existe por três razões:
 *   1. fazer a mesma alteração em 21 arquivos à mão convida ao erro;
 *   2. é idempotente — rodar duas vezes não duplica nada;
 *   3. é reversível, então o efeito no site é auditável e desfazível a qualquer momento.
 *
 * A inserção é PURAMENTE ADITIVA: nenhuma linha existente dos HTMLs é alterada ou
 * removida. As linhas novas entram logo antes do <script> do quiz-engine.js, que é onde
 * a ordem de dependência exige.
 */

"use strict";

const fs = require("fs");
const path = require("path");

const RAIZ = path.resolve(__dirname, "..");
const MARCA_INICIO = "<!-- Camada de IA (Fase 3) — ordem de dependência obrigatória -->";
const MARCA_FIM = "<!-- fim da camada de IA -->";

// A ordem importa: cada arquivo só usa globais declarados pelos anteriores.
// interface-quiz.js precisa vir antes do quiz-engine.js, porque a partida do motor
// pergunta por InterfaceQuizIA.
const ARQUIVOS_IA = [
  "dados/base-conhecimento.js",
  "script/ia/config-ia.js",
  "script/ia/metricas-ia.js",
  "script/ia/cliente-ollama.js",
  "script/ia/prompt-quiz.js",
  "script/ia/parser-quiz.js",
  "script/ia/validador-quiz.js",
  "script/ia/cache-quiz.js",
  "script/ia/servico-quiz.js",
  "script/ia/interface-quiz.js",
];

const PASTAS = [
  "pages/modulos/topicos/topicos-animais",
  "pages/modulos/topicos/topicos-plantas",
  "pages/modulos/topicos/topicos-ecossistemas",
];

/** Todos os tópicos ficam a 4 níveis da raiz, então o prefixo é sempre o mesmo. */
const PREFIXO = "../../../../";

function blocoDeScripts(recuo) {
  const linhas = [recuo + MARCA_INICIO];
  for (const arquivo of ARQUIVOS_IA) {
    linhas.push(`${recuo}<script src="${PREFIXO}${arquivo}"></script>`);
  }
  linhas.push(recuo + MARCA_FIM);
  return linhas.join("\n");
}

function listarPaginas() {
  const paginas = [];
  for (const pasta of PASTAS) {
    for (const arquivo of fs.readdirSync(path.join(RAIZ, pasta))) {
      if (arquivo.endsWith(".html")) paginas.push(`${pasta}/${arquivo}`);
    }
  }
  return paginas;
}

function inserir(html) {
  if (html.indexOf(MARCA_INICIO) !== -1) return { html, estado: "já integrada" };

  // Âncora: a linha do <script> do motor. É o único ponto válido — os arquivos da
  // camada precisam estar todos carregados quando o motor der a partida.
  const achado = html.match(/^([ \t]*)<script src="[^"]*quiz-engine\.js"><\/script>/m);
  if (!achado) return { html, estado: "ERRO: não achei o <script> do quiz-engine.js" };

  const recuo = achado[1];
  const novo = html.replace(achado[0], blocoDeScripts(recuo) + "\n" + achado[0]);
  return { html: novo, estado: "integrada" };
}

function reverter(html) {
  if (html.indexOf(MARCA_INICIO) === -1) return { html, estado: "nada a reverter" };
  const padrao = new RegExp(
    `[ \\t]*${MARCA_INICIO.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}[\\s\\S]*?${MARCA_FIM.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\r?\\n`,
    "g"
  );
  return { html: html.replace(padrao, ""), estado: "revertida" };
}

function main() {
  const soVerificar = process.argv.indexOf("--verificar") !== -1;
  const desfazer = process.argv.indexOf("--reverter") !== -1;

  // Confere que os arquivos referenciados existem, antes de espalhar <script> quebrado.
  for (const arquivo of ARQUIVOS_IA) {
    if (!fs.existsSync(path.join(RAIZ, arquivo))) {
      console.error(`ERRO: ${arquivo} não existe. Nada foi alterado.`);
      process.exitCode = 1;
      return;
    }
  }

  const paginas = listarPaginas();
  const contagem = {};
  let erros = 0;

  for (const pagina of paginas) {
    const caminho = path.join(RAIZ, pagina);
    const original = fs.readFileSync(caminho, "utf8");
    const resultado = desfazer ? reverter(original) : inserir(original);

    contagem[resultado.estado] = (contagem[resultado.estado] || 0) + 1;
    if (resultado.estado.indexOf("ERRO") === 0) {
      erros++;
      console.log(`  ${resultado.estado} — ${pagina}`);
      continue;
    }

    if (!soVerificar && resultado.html !== original) {
      fs.writeFileSync(caminho, resultado.html, "utf8");
    }
  }

  console.log(`${paginas.length} páginas de tópico`);
  for (const estado of Object.keys(contagem)) {
    console.log(`  ${String(contagem[estado]).padStart(3)}  ${estado}`);
  }
  if (soVerificar) console.log("(--verificar: nenhum arquivo foi escrito)");
  console.log(`${ARQUIVOS_IA.length} <script> por página, inseridos antes do quiz-engine.js`);

  process.exitCode = erros ? 1 : 0;
}

main();
