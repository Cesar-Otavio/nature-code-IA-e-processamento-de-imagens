/**
 * comparar-benchmark.js — consolida e compara os braços da Fase 6.
 *
 *     node scripts/comparar-benchmark.js                        compara tudo que houver
 *     node scripts/comparar-benchmark.js --listar termo-inedito listar questões marcadas
 *     node scripts/comparar-benchmark.js --amostra 10           amostra cega para leitura
 *     node scripts/comparar-benchmark.js --markdown             tabelas para o relatório
 *
 * Lê apenas `docs/dados-benchmark/`. NUNCA lê nem escreve em `docs/dados-piloto/` — os
 * dados da Fase 5 ficam intocados, e as duas fases não se misturam.
 *
 * Os marcadores pedagógicos são os mesmos de scripts/analisar-questoes.js, mais um
 * novo, específico da Fase 6:
 *
 *   termo-inedito — a alternativa CORRETA usa um termo técnico que não aparece no
 *                   material. É o detector do defeito registrado na Fase 5:
 *                   "alucinação ou corrupção de termo técnico parcialmente mascarada
 *                   pela sobreposição lexical" — o caso "trilobulados" no lugar de
 *                   "triblásticos". A cobertura lexical não pega, porque as outras
 *                   palavras da alternativa seguram o índice sozinhas.
 *
 * Como todos os marcadores, este é TRIAGEM: aponta o que ler, não decide.
 */

"use strict";

const fs = require("fs");
const path = require("path");
const { carregar, RAIZ } = require("./lib/carregar-camada");

const PASTA = path.join(RAIZ, "docs", "dados-benchmark");

const LIMIARES = {
  CORRETA_FRACA: 0.55,
  DISTRATOR_VAZIO: 0.15,
  PALAVRAS_LITERAIS: 5,
  // Palavra com pelo menos este tamanho é candidata a termo técnico.
  TAMANHO_TERMO: 8,
};

const PADRAO_NEGATIVA = /\bN[ÃA]O\b|\bEXCETO\b|\bINCORRET[AO]\b|\bFALS[AO]\b/;
const TITULOS_ESTRUTURAIS = [
  "caracteristicas gerais", "caracteristicas exclusivas", "caracteristicas",
  "morfologia", "classificacao", "reproducao", "ciclo reprodutivo",
  "ciclo de vida", "principais classes",
];

// Palavras longas e comuns que não são termo técnico — evitam ruído no detector.
const LONGAS_COMUNS = new Set(
  ("alternativa alternativas afirmacao afirmacoes caracteristica caracteristicas geralmente " +
   "principalmente especificamente completamente exclusivamente respectivamente diretamente " +
   "corretamente possivelmente aproximadamente determinado determinada apresentam apresentado " +
   "responsavel responsaveis representa representam constituem constituido diferentes " +
   "importante importantes necessario necessaria permitindo possibilita relacionado relacionada " +
   "encontrado encontrada denominado denominada considerado considerada " +
   // Conjunções e verbos comuns com 8+ letras. Não são termo técnico em nenhum contexto,
   // e apareceram como ruído na calibragem contra a amostra da Fase 5.
   "enquanto portanto contudo entretanto todavia embora porquanto " +
   "utilizam utilizado utilizada utilizando localiza localizado localizada localizadas " +
   "permanece permanecem correspondem corresponde pertencem pertence possuem produzem " +
   "realizam desenvolve desenvolvem originam originado transformam mantendo").split(" ")
);

function maiorTrechoLiteral(trecho, material, normalizar) {
  const palavras = normalizar(trecho).split(" ").filter((p) => p.length > 2);
  let maior = 0;
  for (let i = 0; i < palavras.length; i++) {
    for (let f = palavras.length; f > i + maior; f--) {
      if (material.indexOf(palavras.slice(i, f).join(" ")) !== -1) {
        maior = Math.max(maior, f - i);
        break;
      }
    }
  }
  return maior;
}

/**
 * Termos técnicos da alternativa correta que NÃO aparecem no material.
 *
 * Compara por radical, para não acusar plural nem flexão: "cordado" casa com
 * "cordados". Só olha a alternativa correta — um distrator pode e deve trazer termo
 * de fora, já que ele é uma afirmação falsa.
 */
function termosIneditos(textoCorreto, material, normalizar) {
  const palavras = normalizar(textoCorreto)
    .split(" ")
    .filter((p) => p.length >= LIMIARES.TAMANHO_TERMO && !LONGAS_COMUNS.has(p))
    // Advérbios em -mente e gerúndios não são termo técnico, e eram a maior fonte de
    // ruído na calibragem: sozinhos levavam o detector de ~9% para 20% da amostra.
    // Um deles, "predominantemente", só era acusado porque o texto do site tem um erro
    // de digitação ("predominan=ntemente") que quebra a comparação por radical.
    .filter((p) => !/mente$/.test(p) && !/(ando|endo|indo)$/.test(p));

  const ineditos = [];
  for (const palavra of palavras) {
    const radical = palavra.slice(0, Math.max(5, palavra.length - 3));
    if (material.indexOf(radical) === -1) ineditos.push(palavra);
  }
  return [...new Set(ineditos)];
}

function carregarAmostras() {
  if (!fs.existsSync(PASTA)) return [];
  return fs
    .readdirSync(PASTA)
    .filter((n) => n.endsWith(".json") && n.indexOf("teste-mock") === -1)
    .map((n) => JSON.parse(fs.readFileSync(path.join(PASTA, n), "utf8")))
    .filter((a) => a.fase === 6)
    .sort((a, b) => String(a.braco).localeCompare(String(b.braco)));
}

function analisar(amostra, camada) {
  const V = camada.ValidadorQuiz;
  const resultado = {
    braco: amostra.braco, nome: amostra.nomeDoBraco, modelo: amostra.modelo,
    schema: amostra.schemaEnviado, rotulo: amostra.rotulo, maquina: amostra.maquina,
    hashes: amostra.hashesDePrompt || {}, topicos: [], questoes: [],
  };

  for (const registro of amostra.topicos) {
    const topico = camada.BASE_CONHECIMENTO[registro.moduloId].topicos[registro.topicoId];
    const material = V.normalizar(topico.conteudo);

    for (const geracao of registro.geracoes) {
      for (const questao of geracao.questoes || []) {
        const correta = questao.alternativas.filter((a) => a.correta)[0];
        if (!correta) continue;
        const distratores = questao.alternativas.filter((a) => !a.correta);
        const coberturaCorreta = V.cobertura(correta.texto, material);
        const coberturasDistratores = distratores.map((d) => V.cobertura(d.texto, material));
        const ineditos = termosIneditos(correta.texto, material, V.normalizar);

        const marcadores = [];
        if (PADRAO_NEGATIVA.test(questao.enunciado)) marcadores.push("negativa");
        const enunciadoNormalizado = V.normalizar(questao.enunciado);
        if (TITULOS_ESTRUTURAIS.some((t) => enunciadoNormalizado.indexOf(t) !== -1))
          marcadores.push("titulo-de-secao");
        if (coberturaCorreta < LIMIARES.CORRETA_FRACA) marcadores.push("alucinacao");
        if (coberturasDistratores.some((c) => c < LIMIARES.DISTRATOR_VAZIO)) marcadores.push("distrator-vazio");
        if (distratores.some((d) => maiorTrechoLiteral(d.texto, material, V.normalizar) >= LIMIARES.PALAVRAS_LITERAIS))
          marcadores.push("distrator-literal");
        if (ineditos.length) marcadores.push("termo-inedito");

        resultado.questoes.push({
          braco: amostra.braco, topicoId: registro.topicoId, geracao: geracao.indice,
          enunciado: questao.enunciado, alternativas: questao.alternativas,
          explicacao: questao.explicacao, conceitoAvaliado: questao.conceitoAvaliado,
          coberturaCorreta, termosIneditos: ineditos, marcadores,
        });
      }
    }

    const questoesDoTopico = registro.geracoes.flatMap((g) => g.questoes || []);
    const enunciados = new Set(questoesDoTopico.map((q) => V.normalizar(q.enunciado)));
    resultado.topicos.push({
      topicoId: registro.topicoId, titulo: registro.titulo,
      caracteres: registro.caracteres, maxQuestoes: registro.maxQuestoes,
      resumo: registro.resumo,
      diversidade: questoesDoTopico.length ? enunciados.size / questoesDoTopico.length : null,
    });
  }
  return resultado;
}

function totais(analise) {
  const t = analise.topicos.reduce((acc, x) => ({
    geracoes: acc.geracoes + x.resumo.geracoes,
    ia: acc.ia + x.resumo.porOrigem.ia,
    recebidas: acc.recebidas + x.resumo.recebidas,
    aprovadas: acc.aprovadas + x.resumo.aprovadas,
    rejeitadas: acc.rejeitadas + x.resumo.rejeitadas,
    retentativas: acc.retentativas + x.resumo.retentativas,
    jsonPrimeira: acc.jsonPrimeira + x.resumo.jsonValidoDePrimeira,
    latencias: acc.latencias.concat(x.resumo.latencias),
  }), { geracoes: 0, ia: 0, recebidas: 0, aprovadas: 0, rejeitadas: 0, retentativas: 0, jsonPrimeira: 0, latencias: [] });
  t.latencias.sort((a, b) => a - b);
  t.taxa = t.recebidas ? t.aprovadas / t.recebidas : null;
  t.entrega = t.geracoes ? t.ia / t.geracoes : null;
  t.mediana = t.latencias[Math.floor(t.latencias.length / 2)] || 0;
  t.p95 = t.latencias[Math.floor(t.latencias.length * 0.95)] || 0;
  t.questoes = analise.questoes.length;
  return t;
}

const pct = (x) => (x === null || x === undefined ? "—" : `${(x * 100).toFixed(0)}%`);
const seg = (ms) => `${(ms / 1000).toFixed(1)}s`;

function imprimirComparacao(analises, markdown) {
  const linhas = [
    ["métrica", ...analises.map((a) => `${a.braco} (${a.modelo})`)],
  ];
  const t = analises.map(totais);

  linhas.push(["schema enviado", ...analises.map((a) => (a.schema ? "SIM" : "não"))]);
  linhas.push(["gerações", ...t.map((x) => String(x.geracoes))]);
  linhas.push(["entrega por IA", ...t.map((x) => `${x.ia}/${x.geracoes} (${pct(x.entrega)})`)]);
  linhas.push(["questões recebidas", ...t.map((x) => String(x.recebidas))]);
  linhas.push(["questões aprovadas", ...t.map((x) => String(x.aprovadas))]);
  linhas.push(["questões rejeitadas", ...t.map((x) => String(x.rejeitadas))]);
  linhas.push(["taxa de aprovação", ...t.map((x) => pct(x.taxa))]);
  linhas.push(["retentativas", ...t.map((x) => String(x.retentativas))]);
  linhas.push(["JSON válido de 1a", ...t.map((x) => `${x.jsonPrimeira}/${x.geracoes} (${pct(x.geracoes ? x.jsonPrimeira / x.geracoes : null)})`)]);
  linhas.push(["latência mediana", ...t.map((x) => seg(x.mediana))]);
  linhas.push(["latência p95", ...t.map((x) => seg(x.p95))]);

  const marcadores = new Set();
  for (const a of analises) for (const q of a.questoes) for (const m of q.marcadores) marcadores.add(m);
  for (const m of [...marcadores].sort()) {
    linhas.push([m, ...analises.map((a) => {
      const n = a.questoes.filter((q) => q.marcadores.indexOf(m) !== -1).length;
      return a.questoes.length ? `${n} (${((n / a.questoes.length) * 100).toFixed(1)}%)` : "—";
    })]);
  }

  if (markdown) {
    console.log("| " + linhas[0].join(" | ") + " |");
    console.log("|" + linhas[0].map(() => "---").join("|") + "|");
    for (const l of linhas.slice(1)) console.log("| " + l.join(" | ") + " |");
    return;
  }
  const larguras = linhas[0].map((_, i) => Math.max(...linhas.map((l) => String(l[i]).length)));
  for (const l of linhas) console.log("  " + l.map((c, i) => String(c).padEnd(larguras[i])).join("  |  "));
}

function conferirHashes(analises) {
  const a = analises.filter((x) => x.braco === "A")[0];
  const b = analises.filter((x) => x.braco === "B")[0];
  const c = analises.filter((x) => x.braco === "C")[0];
  if (!a || !b) {
    console.log("  (braços A e B ainda não foram executados — sem o que conferir)");
    return null;
  }
  let todosIguais = true;
  console.log("  tópico              | braço A          | braço B          | iguais?");
  for (const topicoId of Object.keys(a.hashes)) {
    const ha = a.hashes[topicoId], hb = b.hashes[topicoId];
    const iguais = hb && ha.hash === hb.hash;
    if (!iguais) todosIguais = false;
    console.log(`  ${topicoId.padEnd(20)}| ${ha.hash.slice(0, 16)} | ${hb ? hb.hash.slice(0, 16) : "(ausente)".padEnd(16)} |  ${iguais ? "SIM" : "NÃO!"}`);
  }
  console.log(todosIguais
    ? "\n  OK — a comparação A × B é válida: prompts byte a byte idênticos."
    : "\n  INVÁLIDA — os prompts divergiram. A comparação A × B não pode ser usada.");
  if (c) {
    const difere = Object.keys(a.hashes).every((t) => !c.hashes[t] || c.hashes[t].hash !== a.hashes[t].hash);
    console.log(`  Braço C difere do A em todos os tópicos: ${difere ? "sim (esperado — o schema tira o bloco de JSON)" : "NÃO — verifique"}`);
  }
  return todosIguais;
}

function imprimirQuestoes(analises, filtro, limite) {
  let n = 0;
  for (const a of analises) {
    for (const q of a.questoes) {
      if (filtro && q.marcadores.indexOf(filtro) === -1) continue;
      if (!filtro && !q.marcadores.length) continue;
      if (n++ >= limite) return;
      console.log(`\n--- [braço ${q.braco} · ${q.topicoId} · geração ${q.geracao}] ${q.marcadores.join(", ")}`);
      console.log(`  ${q.enunciado}`);
      q.alternativas.forEach((x, i) =>
        console.log(`    ${x.correta ? "->" : "  "} ${String.fromCharCode(65 + i)}) ${x.texto}`));
      if (q.termosIneditos.length) console.log(`    TERMOS INÉDITOS NA CORRETA: ${q.termosIneditos.join(", ")}`);
      console.log(`    conceito: ${q.conceitoAvaliado}`);
      console.log(`    explicação: ${q.explicacao}`);
    }
  }
  if (!n) console.log("\n(nenhuma questão com esse marcador)");
}

function imprimirAmostraCega(analises, quantas) {
  const todas = analises.flatMap((a) => a.questoes);
  if (!todas.length) return;
  const passo = Math.max(1, Math.floor(todas.length / quantas));
  console.log(`\n\nAMOSTRA CEGA — 1 a cada ${passo} questões, para leitura manual`);
  console.log("=".repeat(76));
  for (let i = 0; i < todas.length && i / passo < quantas; i += passo) {
    const q = todas[i];
    console.log(`\n--- [braço ${q.braco} · ${q.topicoId} · geração ${q.geracao}] ${q.marcadores.join(", ") || "sem marcador"}`);
    console.log(`  ${q.enunciado}`);
    q.alternativas.forEach((x, j) =>
      console.log(`    ${x.correta ? "->" : "  "} ${String.fromCharCode(65 + j)}) ${x.texto}`));
    console.log(`    explicação: ${q.explicacao}`);
  }
}

function main() {
  const amostras = carregarAmostras();
  if (!amostras.length) {
    console.log("Nenhum resultado da Fase 6 em docs/dados-benchmark/.");
    console.log("Rode o benchmark primeiro — ver docs/06b-GUIA-PC-MESA.md.");
    return;
  }

  const camada = carregar({ silencioso: true, fetch: async () => { throw new Error("sem rede"); } });
  const analises = amostras.map((a) => analisar(a, camada));
  const markdown = process.argv.indexOf("--markdown") !== -1;

  console.log(`\nBenchmark da Fase 6 — ${analises.length} braço(s) executado(s)\n`);
  for (const a of analises) {
    const m = a.maquina || {};
    console.log(`  ${a.braco}: ${a.nome} | ${a.modelo} | schema ${a.schema ? "SIM" : "não"} | ${m.cpus || "?"} CPUs, ${m.memoriaTotalGB || "?"} GB`);
  }

  console.log("\n\nINTEGRIDADE DOS PROMPTS");
  console.log("=".repeat(76));
  conferirHashes(analises);

  console.log("\n\nCOMPARAÇÃO ENTRE BRAÇOS");
  console.log("=".repeat(76));
  imprimirComparacao(analises, markdown);

  const b = analises.filter((x) => x.braco === "B")[0];
  const c = analises.filter((x) => x.braco === "C")[0];
  if (b && c) {
    const tb = totais(b), tc = totais(c);
    console.log("\n\nEFEITO DO JSON SCHEMA (braço C × braço B, mesmo modelo)");
    console.log("=".repeat(76));
    console.log(`  JSON válido de 1a tentativa:  sem schema ${pct(tb.jsonPrimeira / tb.geracoes)}  ->  com schema ${pct(tc.jsonPrimeira / tc.geracoes)}`);
    console.log(`  taxa de aprovação:            sem schema ${pct(tb.taxa)}  ->  com schema ${pct(tc.taxa)}`);
    console.log(`  retentativas:                 sem schema ${tb.retentativas}  ->  com schema ${tc.retentativas}`);
    console.log(`  latência mediana:             sem schema ${seg(tb.mediana)}  ->  com schema ${seg(tc.mediana)}`);
  }

  const iListar = process.argv.indexOf("--listar");
  if (iListar !== -1) {
    const filtro = process.argv[iListar + 1] === "todos" ? null : process.argv[iListar + 1];
    console.log(`\n\nQUESTÕES COM O MARCADOR "${filtro || "qualquer"}"`);
    console.log("=".repeat(76));
    imprimirQuestoes(analises, filtro, Number(process.argv[process.argv.indexOf("--limite") + 1]) || 20);
  }

  const iAmostra = process.argv.indexOf("--amostra");
  if (iAmostra !== -1) imprimirAmostraCega(analises, Number(process.argv[iAmostra + 1]) || 10);
}

if (require.main === module) main();
module.exports = { termosIneditos, analisar, totais, PASTA };
