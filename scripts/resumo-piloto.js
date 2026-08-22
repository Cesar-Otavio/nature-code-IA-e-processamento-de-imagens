/**
 * resumo-piloto.js — consolida as amostras da Fase 5 numa tabela única.
 *
 *     node scripts/resumo-piloto.js            tabela de leitura
 *     node scripts/resumo-piloto.js --markdown tabela pronta para o relatório
 *
 * Lê tudo de `docs/dados-piloto/*.json`. Os números saem dos arquivos gravados durante
 * as gerações — nada aqui é estimado ou recalculado por fora.
 *
 * Quando um tópico aparece em mais de uma amostra, vale a MAIS RECENTE por versão de
 * prompt: Artrópodes, por exemplo, foi medido com V3 e depois com V4, e o que descreve o
 * comportamento atual do site é o V4.
 */

"use strict";

const fs = require("fs");
const path = require("path");
const { carregar, RAIZ } = require("./lib/carregar-camada");

const PASTA = path.join(RAIZ, "docs", "dados-piloto");

// Ordem de preferência: amostra mais à direita vence para o mesmo tópico.
const AMOSTRAS = [
  "onda1-v1-cordados",
  "onda2-v2-cordados",
  "onda3-v3-cordados",
  "onda4-v3-grandes",
  "onda5-v3-medios",
  "onda6-v3-pequenos",
  "onda7-v4-artropodes",
  "onda8-v4-cordados",
];

// Amostras que não descrevem o comportamento atual e por isso ficam fora da tabela final.
const EXCLUIDAS = {
  "onda1-v1-cordados": "experimento de prompt V1",
  "onda2-v2-cordados": "experimento de prompt V2 (recusado)",
  "onda8-v4-cordados": "contaminada pelo limite de uso do Ollama Cloud",
};

function main() {
  const camada = carregar({ silencioso: true, fetch: async () => { throw new Error("sem rede"); } });
  const porTopico = new Map();

  for (const rotulo of AMOSTRAS) {
    const caminho = path.join(PASTA, `${rotulo}.json`);
    if (!fs.existsSync(caminho) || EXCLUIDAS[rotulo]) continue;
    const amostra = JSON.parse(fs.readFileSync(caminho, "utf8"));

    for (const registro of amostra.topicos) {
      const questoes = registro.geracoes.flatMap((g) => g.questoes || []);
      const enunciados = new Set(
        questoes.map((q) => camada.ValidadorQuiz.normalizar(q.enunciado))
      );
      const latencias = registro.resumo.latencias;

      porTopico.set(registro.topicoId, {
        rotulo,
        versao: amostra.versaoPrompt,
        titulo: registro.titulo,
        caracteres: registro.caracteres,
        maxQuestoes: registro.maxQuestoes,
        geracoes: registro.resumo.geracoes,
        ia: registro.resumo.porOrigem.ia,
        fixo: registro.resumo.porOrigem.fixo,
        entrega: registro.resumo.porOrigem.ia / registro.resumo.geracoes,
        solicitadas: registro.resumo.solicitadas,
        recebidas: registro.resumo.recebidas,
        aprovadas: registro.resumo.aprovadas,
        rejeitadas: registro.resumo.rejeitadas,
        taxa: registro.resumo.recebidas ? registro.resumo.aprovadas / registro.resumo.recebidas : null,
        retentativas: registro.resumo.retentativas,
        geracoesComRetentativa: registro.geracoes.filter((g) => (g.tentativas || 0) > 1).length,
        medianaMs: latencias[Math.floor(latencias.length / 2)] || 0,
        p95Ms: latencias[Math.floor(latencias.length * 0.95)] || 0,
        diversidade: questoes.length ? enunciados.size / questoes.length : null,
        questoes: questoes.length,
      });
    }
  }

  // Os tópicos com maxQuestoes = 0 nunca são gerados; entram na tabela pela base.
  for (const moduloId of Object.keys(camada.BASE_CONHECIMENTO)) {
    const modulo = camada.BASE_CONHECIMENTO[moduloId];
    for (const topicoId of Object.keys(modulo.topicos)) {
      if (porTopico.has(topicoId)) continue;
      const topico = modulo.topicos[topicoId];
      porTopico.set(topicoId, {
        titulo: topico.titulo,
        caracteres: topico.metricas.caracteres,
        maxQuestoes: topico.maxQuestoes,
        naoAvaliado: true,
        motivo: topico.limitadoPor,
      });
    }
  }

  const linhas = [...porTopico.entries()]
    .map(([id, dados]) => ({ id, ...dados }))
    .sort((a, b) => b.caracteres - a.caracteres);

  const habilitados = new Set(camada.CONFIG_IA.topicosComIA);
  const pct = (x) => (x === null || x === undefined ? "—" : `${(x * 100).toFixed(0)}%`);
  const seg = (ms) => `${(ms / 1000).toFixed(1)}s`;

  if (process.argv.indexOf("--markdown") !== -1) {
    console.log(
      "| Tópico | Caract. | Máx. | Gerações | Entrega por IA | Recebidas | Aprovadas | Rejeitadas | Taxa | Retentativas | Mediana | Decisão |"
    );
    console.log("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|");
    for (const l of linhas) {
      const decisao = habilitados.has(l.id) ? "**IA**" : "Fixo";
      if (l.naoAvaliado) {
        console.log(
          `| ${l.titulo} | ${l.caracteres} | 0 | — | — | — | — | — | — | — | — | ${decisao} |`
        );
        continue;
      }
      console.log(
        `| ${l.titulo} | ${l.caracteres} | ${l.maxQuestoes} | ${l.geracoes} | ` +
          `${l.ia}/${l.geracoes} (${pct(l.entrega)}) | ${l.recebidas} | ${l.aprovadas} | ` +
          `${l.rejeitadas} | ${pct(l.taxa)} | ${l.retentativas} | ${seg(l.medianaMs)} | ${decisao} |`
      );
    }
    return;
  }

  console.log(
    "topico                        car  max | ger  IA fixo entrega | rec  apr  rej  taxa | ret gRet | mediana  p95 | div  | decisao"
  );
  console.log("-".repeat(130));
  let total = { ger: 0, ia: 0, fixo: 0, rec: 0, apr: 0, rej: 0, ret: 0, q: 0 };
  for (const l of linhas) {
    const decisao = habilitados.has(l.id) ? "IA" : "fixo";
    if (l.naoAvaliado) {
      console.log(
        `${l.titulo.slice(0, 28).padEnd(29)}${String(l.caracteres).padStart(5)}${String(l.maxQuestoes).padStart(5)} | ` +
          `sem geração — ${l.motivo}`.padEnd(75) + decisao
      );
      continue;
    }
    total.ger += l.geracoes; total.ia += l.ia; total.fixo += l.fixo;
    total.rec += l.recebidas; total.apr += l.aprovadas; total.rej += l.rejeitadas;
    total.ret += l.retentativas; total.q += l.questoes;
    console.log(
      l.titulo.slice(0, 28).padEnd(29) + String(l.caracteres).padStart(5) + String(l.maxQuestoes).padStart(5) + " |" +
        String(l.geracoes).padStart(4) + String(l.ia).padStart(4) + String(l.fixo).padStart(5) + pct(l.entrega).padStart(8) + " |" +
        String(l.recebidas).padStart(5) + String(l.aprovadas).padStart(5) + String(l.rejeitadas).padStart(5) + pct(l.taxa).padStart(6) + " |" +
        String(l.retentativas).padStart(4) + String(l.geracoesComRetentativa).padStart(5) + " |" +
        seg(l.medianaMs).padStart(8) + seg(l.p95Ms).padStart(7) + " |" + pct(l.diversidade).padStart(5) + " | " + decisao
    );
  }
  console.log("-".repeat(130));
  console.log(
    `TOTAL na tabela: ${total.ger} gerações | IA ${total.ia} · fixo ${total.fixo} | ` +
      `${total.apr}/${total.rec} aprovadas (${((total.apr / total.rec) * 100).toFixed(1)}%) | ` +
      `${total.rej} rejeitadas | ${total.ret} retentativas | ${total.q} questões guardadas`
  );
  console.log(`\nHabilitados para IA: ${habilitados.size} de 21 tópicos`);
  console.log("Amostras fora da tabela:");
  for (const rotulo of Object.keys(EXCLUIDAS)) console.log(`  ${rotulo} — ${EXCLUIDAS[rotulo]}`);
}

main();
