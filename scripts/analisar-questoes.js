/**
 * analisar-questoes.js — triagem pedagógica das questões geradas na Fase 5.
 *
 *     node scripts/analisar-questoes.js onda1-v1-cordados
 *     node scripts/analisar-questoes.js onda1-v1-cordados --listar exclusividade
 *     node scripts/analisar-questoes.js onda1-v1 onda2-v2 --comparar
 *
 * O validador da Fase 2 responde "esta questão está bem formada?". Este script responde
 * uma pergunta diferente e mais difícil: "esta questão está pedagogicamente correta?".
 *
 * IMPORTANTE — o que este script é e o que não é. Ele faz TRIAGEM, não julgamento: marca
 * candidatos a problema para leitura humana. Um marcador não é um defeito confirmado, e a
 * ausência de marcador não é atestado de qualidade. A conclusão sobre correção biológica
 * sai da leitura, e os números daqui só dizem onde olhar primeiro.
 *
 * Marcadores, na numeração de problemas da Fase 5:
 *   A/E  exclusividade   enunciado pergunta pelo "exclusivo/único/apenas"
 *   C    distrator-verdadeiro  alternativa dada como errada é quase citação do material
 *   F    alucinacao      a alternativa correta mal aparece no material
 *   G    explicacao-solta a explicação não menciona o que a correta afirma
 *   H    negativa        enunciado com NÃO / EXCETO / INCORRETA / FALSA
 *   I    distrator-vazio alternativa errada sem nenhuma relação com o material
 *   —    repetida        o mesmo enunciado saiu em gerações diferentes
 */

"use strict";

const fs = require("fs");
const path = require("path");
const { carregar, RAIZ } = require("./lib/carregar-camada");

const PASTA = path.join(RAIZ, "docs", "dados-piloto");

// Limiares da triagem. Escolhidos para errar para o lado de marcar demais: um falso
// positivo custa uma leitura, um falso negativo deixa passar questão ruim.
const LIMIARES = {
  CORRETA_FRACA: 0.55, // cobertura abaixo disso: a "certa" mal aparece no material
  DISTRATOR_VAZIO: 0.15, // cobertura abaixo disso: inventado do nada
  EXPLICACAO_SOLTA: 0.2, // sobreposição entre explicação e alternativa correta
  PALAVRAS_LITERAIS: 5, // sequência de palavras copiada do material
};

/**
 * Maior sequência de palavras de conteúdo do `trecho` que aparece, na mesma ordem e sem
 * interrupção, no `material`.
 *
 * Substitui uma primeira versão do detector que media apenas SOBREPOSIÇÃO DE TERMOS entre
 * o distrator e o material — e que marcou 75% das questões, quase tudo falso positivo.
 * O motivo é instrutivo: um bom distrator é feito com o vocabulário do material, então
 * sobreposição alta é sinal de distrator BOM, não de distrator verdadeiro. Numa das
 * questões lidas, as quatro alternativas tinham 100% de sobreposição e a questão estava
 * correta.
 *
 * Trecho literal é outra coisa: se a alternativa dada como errada reproduz uma sequência
 * inteira do texto, há chance real de ela estar afirmando algo que o material afirma.
 */
function maiorTrechoLiteral(trecho, materialNormalizado, normalizar) {
  const palavras = normalizar(trecho).split(" ").filter((p) => p.length > 2);
  let maior = 0;
  for (let inicio = 0; inicio < palavras.length; inicio++) {
    for (let fim = palavras.length; fim > inicio + maior; fim--) {
      const sequencia = palavras.slice(inicio, fim).join(" ");
      if (materialNormalizado.indexOf(sequencia) !== -1) {
        maior = Math.max(maior, fim - inicio);
        break;
      }
    }
  }
  return maior;
}

// Títulos de seção que só organizam o texto. Um enunciado que se apoia num deles está
// perguntando ONDE o fato está escrito, não O QUE o texto afirma — e é aí que nascem as
// questões com duas respostas certas. Mesma lista usada por scripts/extrair-conteudo.js.
//
// Este marcador substituiu, para o problema E, a busca pela palavra "exclusiva": aquela
// marcava o adjetivo mesmo quando ele era incidental (2 de 96 em Cordados, ambas
// corretas), e não pegava o defeito real de Artrópodes, cujo enunciado cita
// "Características Gerais" sem usar a palavra "exclusiva" nenhuma vez.
const TITULOS_ESTRUTURAIS = [
  "caracteristicas gerais", "caracteristicas exclusivas", "caracteristicas",
  "morfologia", "classificacao", "reproducao", "reproducao sexuada",
  "reproducao assexuada", "ciclo reprodutivo", "ciclo de vida", "principais classes",
];

const PADRAO_EXCLUSIVIDADE =
  /\bexclusiv|\búnic[ao]\b|\bapenas\b|\bsomente\b|\bsó\b|\bexclusivamente\b|\bcaracteriza exclusivamente\b/i;
const PADRAO_NEGATIVA =
  /\bN[ÃA]O\b|\bEXCETO\b|\bINCORRET[AO]\b|\bFALS[AO]\b|\bnão (é|corresponde|está|faz|possui|pertence)\b/;

function carregarAmostra(rotulo) {
  const caminho = path.join(PASTA, `${rotulo}.json`);
  if (!fs.existsSync(caminho)) {
    console.error(`Amostra não encontrada: docs/dados-piloto/${rotulo}.json`);
    process.exit(1);
  }
  return JSON.parse(fs.readFileSync(caminho, "utf8"));
}

/** Analisa uma amostra e devolve as questões com seus marcadores. */
function analisar(amostra, camada) {
  const V = camada.ValidadorQuiz;
  const resultado = { rotulo: amostra.rotulo, versaoPrompt: amostra.versaoPrompt, topicos: [] };

  for (const registroTopico of amostra.topicos) {
    const topico =
      camada.BASE_CONHECIMENTO[registroTopico.moduloId].topicos[registroTopico.topicoId];
    const material = V.normalizar(topico.conteudo);

    const questoes = [];
    const vistos = new Map();

    for (const geracao of registroTopico.geracoes) {
      for (const questao of geracao.questoes || []) {
        const correta = questao.alternativas.filter((a) => a.correta)[0];
        const distratores = questao.alternativas.filter((a) => !a.correta);
        if (!correta) continue;

        const coberturaCorreta = V.cobertura(correta.texto, material);
        const coberturasDistratores = distratores.map((d) => V.cobertura(d.texto, material));

        const marcadores = [];
        if (PADRAO_EXCLUSIVIDADE.test(questao.enunciado)) marcadores.push("exclusividade");

        const enunciadoNormalizado = V.normalizar(questao.enunciado);
        if (TITULOS_ESTRUTURAIS.some((t) => enunciadoNormalizado.indexOf(t) !== -1))
          marcadores.push("titulo-de-secao");
        if (PADRAO_NEGATIVA.test(questao.enunciado)) marcadores.push("negativa");
        if (coberturaCorreta < LIMIARES.CORRETA_FRACA) marcadores.push("alucinacao");
        const literaisDistratores = distratores.map((d) =>
          maiorTrechoLiteral(d.texto, material, V.normalizar)
        );
        if (literaisDistratores.some((n) => n >= LIMIARES.PALAVRAS_LITERAIS))
          marcadores.push("distrator-literal");
        if (coberturasDistratores.some((c) => c < LIMIARES.DISTRATOR_VAZIO))
          marcadores.push("distrator-vazio");
        if (V.cobertura(correta.texto, V.normalizar(questao.explicacao)) < LIMIARES.EXPLICACAO_SOLTA)
          marcadores.push("explicacao-solta");

        const chave = V.normalizar(questao.enunciado);
        if (vistos.has(chave)) {
          vistos.get(chave).repeticoes++;
          marcadores.push("repetida");
        } else {
          vistos.set(chave, { repeticoes: 1 });
        }

        questoes.push({
          geracao: geracao.indice,
          enunciado: questao.enunciado,
          alternativas: questao.alternativas,
          explicacao: questao.explicacao,
          conceitoAvaliado: questao.conceitoAvaliado,
          coberturaCorreta,
          coberturasDistratores,
          marcadores,
        });
      }
    }

    const enunciadosUnicos = vistos.size;
    resultado.topicos.push({
      topicoId: registroTopico.topicoId,
      titulo: registroTopico.titulo,
      caracteres: registroTopico.caracteres,
      maxQuestoes: registroTopico.maxQuestoes,
      resumo: registroTopico.resumo,
      questoes,
      enunciadosUnicos,
      diversidade: questoes.length ? enunciadosUnicos / questoes.length : null,
    });
  }
  return resultado;
}

function contarMarcadores(questoes) {
  const contagem = {};
  for (const q of questoes) for (const m of q.marcadores) contagem[m] = (contagem[m] || 0) + 1;
  return contagem;
}

function imprimirResumo(analise) {
  console.log(`\nAmostra "${analise.rotulo}" — prompt ${analise.versaoPrompt}`);
  console.log("=".repeat(78));

  for (const t of analise.topicos) {
    const contagem = contarMarcadores(t.questoes);
    const comMarcador = t.questoes.filter((q) => q.marcadores.length).length;
    const lat = t.resumo.latencias;
    const mediana = lat[Math.floor(lat.length / 2)] || 0;

    console.log(`\n${t.titulo}  (${t.caracteres} car., máx. ${t.maxQuestoes})`);
    console.log(
      `  gerações ${t.resumo.geracoes} | recebidas ${t.resumo.recebidas} | aprovadas ${t.resumo.aprovadas}` +
        ` (${(t.resumo.taxaAprovacao * 100).toFixed(1)}%) | retentativas ${t.resumo.retentativas}` +
        ` | mediana ${(mediana / 1000).toFixed(1)}s`
    );
    console.log(
      `  origem: IA ${t.resumo.porOrigem.ia} · cache ${t.resumo.porOrigem.cache} · fixo ${t.resumo.porOrigem.fixo}`
    );
    console.log(
      `  enunciados distintos: ${t.enunciadosUnicos}/${t.questoes.length}` +
        ` (${(t.diversidade * 100).toFixed(0)}% de diversidade)`
    );
    console.log(`  questões com algum marcador: ${comMarcador}/${t.questoes.length}` +
      ` (${((comMarcador / t.questoes.length) * 100).toFixed(1)}%)`);

    const ordenados = Object.keys(contagem).sort((a, b) => contagem[b] - contagem[a]);
    for (const marcador of ordenados) {
      const pct = ((contagem[marcador] / t.questoes.length) * 100).toFixed(1);
      console.log(`     ${marcador.padEnd(22)} ${String(contagem[marcador]).padStart(3)}  (${pct}%)`);
    }

    const motivos = {};
    for (const g of t.resumo && [] ) void g;
    void motivos;
  }
}

function imprimirQuestoes(analise, filtro, limite) {
  let mostradas = 0;
  for (const t of analise.topicos) {
    for (const q of t.questoes) {
      if (filtro && q.marcadores.indexOf(filtro) === -1) continue;
      if (!filtro && !q.marcadores.length) continue;
      if (mostradas >= limite) return;
      mostradas++;
      console.log(`\n--- [${t.topicoId} · geração ${q.geracao}] marcadores: ${q.marcadores.join(", ") || "nenhum"}`);
      console.log(`  ${q.enunciado}`);
      q.alternativas.forEach((a, i) => {
        const cobertura = a.correta ? q.coberturaCorreta : q.coberturasDistratores[
          q.alternativas.filter((x) => !x.correta).indexOf(a)
        ];
        console.log(
          `    ${a.correta ? "->" : "  "} ${String.fromCharCode(65 + i)}) ${a.texto}` +
            `   [cobertura ${(cobertura * 100).toFixed(0)}%]`
        );
      });
      console.log(`    conceito: ${q.conceitoAvaliado}`);
      console.log(`    explicação: ${q.explicacao}`);
    }
  }
  if (!mostradas) console.log("\n(nenhuma questão com esse marcador)");
}

/** Amostra aleatória e reprodutível, para leitura manual sem viés de seleção. */
function imprimirAmostraCega(analise, quantas) {
  const todas = [];
  for (const t of analise.topicos) for (const q of t.questoes) todas.push({ t, q });
  const passo = Math.max(1, Math.floor(todas.length / quantas));
  console.log(`\n\nAMOSTRA SISTEMÁTICA — 1 a cada ${passo} questões, para leitura manual`);
  console.log("=".repeat(78));
  for (let i = 0; i < todas.length && i / passo < quantas; i += passo) {
    const { t, q } = todas[i];
    console.log(`\n--- [${t.topicoId} · geração ${q.geracao}] marcadores: ${q.marcadores.join(", ") || "nenhum"}`);
    console.log(`  ${q.enunciado}`);
    q.alternativas.forEach((a, j) =>
      console.log(`    ${a.correta ? "->" : "  "} ${String.fromCharCode(65 + j)}) ${a.texto}`)
    );
    console.log(`    explicação: ${q.explicacao}`);
  }
}

function comparar(analises) {
  console.log("\nCOMPARAÇÃO ENTRE AMOSTRAS");
  console.log("=".repeat(78));
  const marcadores = new Set();
  for (const a of analises) for (const t of a.topicos) for (const q of t.questoes)
    for (const m of q.marcadores) marcadores.add(m);

  const linhas = [["métrica", ...analises.map((a) => a.rotulo)]];
  const totais = analises.map((a) => {
    const questoes = a.topicos.flatMap((t) => t.questoes);
    return {
      questoes,
      recebidas: a.topicos.reduce((s, t) => s + t.resumo.recebidas, 0),
      aprovadas: a.topicos.reduce((s, t) => s + t.resumo.aprovadas, 0),
      retentativas: a.topicos.reduce((s, t) => s + t.resumo.retentativas, 0),
    };
  });

  linhas.push(["questões analisadas", ...totais.map((t) => String(t.questoes.length))]);
  linhas.push(["taxa de aprovação", ...totais.map((t) => ((t.aprovadas / t.recebidas) * 100).toFixed(1) + "%")]);
  linhas.push(["retentativas", ...totais.map((t) => String(t.retentativas))]);
  for (const m of [...marcadores].sort()) {
    linhas.push([
      m,
      ...totais.map((t) => {
        const n = t.questoes.filter((q) => q.marcadores.indexOf(m) !== -1).length;
        return `${n} (${((n / t.questoes.length) * 100).toFixed(1)}%)`;
      }),
    ]);
  }

  const larguras = linhas[0].map((_, i) => Math.max(...linhas.map((l) => String(l[i]).length)));
  for (const linha of linhas) {
    console.log("  " + linha.map((c, i) => String(c).padEnd(larguras[i])).join("  |  "));
  }
}

function main() {
  // Os rótulos são os argumentos livres. O valor que vem depois de uma opção não é um
  // rótulo — sem esta exclusão, `--listar exclusividade` faria o script procurar uma
  // amostra chamada "exclusividade".
  const OPCOES_COM_VALOR = ["--listar", "--limite", "--amostra"];
  const argumentos = process.argv.slice(2);
  const rotulos = argumentos.filter(
    (a, i) => !a.startsWith("--") && OPCOES_COM_VALOR.indexOf(argumentos[i - 1]) === -1
  );
  if (!rotulos.length) {
    console.error("Uso: node scripts/analisar-questoes.js <rotulo> [rotulo2] [--comparar] [--listar MARCADOR] [--amostra N]");
    process.exitCode = 1;
    return;
  }

  const camada = carregar({ silencioso: true, fetch: async () => { throw new Error("sem rede"); } });
  const analises = rotulos.map((r) => analisar(carregarAmostra(r), camada));

  if (process.argv.indexOf("--comparar") !== -1) {
    for (const a of analises) imprimirResumo(a);
    comparar(analises);
    return;
  }

  for (const a of analises) imprimirResumo(a);

  const iListar = process.argv.indexOf("--listar");
  if (iListar !== -1) {
    const filtro = process.argv[iListar + 1] === "todos" ? null : process.argv[iListar + 1];
    const limite = Number(process.argv[process.argv.indexOf("--limite") + 1]) || 20;
    console.log(`\n\nQUESTÕES COM O MARCADOR "${filtro || "qualquer"}"`);
    console.log("=".repeat(78));
    imprimirQuestoes(analises[0], filtro, limite);
  }

  const iAmostra = process.argv.indexOf("--amostra");
  if (iAmostra !== -1) {
    imprimirAmostraCega(analises[0], Number(process.argv[iAmostra + 1]) || 10);
  }
}

main();
