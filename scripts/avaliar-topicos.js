/**
 * avaliar-topicos.js — bateria de avaliação controlada da Fase 5.
 *
 * Roda N gerações por tópico ATRAVÉS DO SERVIÇO REAL (`obterQuiz`), para que a cascata,
 * as retentativas, o cache e os fallbacks sejam exercitados como no site, e guarda tudo
 * em `docs/dados-piloto/<rotulo>.json` — inclusive o texto integral de cada questão
 * aprovada, que é o material da análise pedagógica.
 *
 *     node scripts/avaliar-topicos.js --rotulo onda1-v1 --n 10 --topicos filo-cordados,fluxo-de-energia
 *     node scripts/avaliar-topicos.js --rotulo onda1-v1 --n 20 --topicos filo-cordados --prompt V1
 *
 * Opções:
 *   --rotulo NOME     nome da amostra (obrigatório) — vira o nome do arquivo
 *   --n N             gerações por tópico (padrão 10)
 *   --topicos a,b,c   ids de tópico; sem isto, usa os elegíveis do maior para o menor
 *   --prompt V1|V2    versão do prompt do usuário a usar
 *   --limite N        para depois de N tópicos
 *
 * O tópico é habilitado APENAS EM MEMÓRIA. `topicosComIA` no arquivo de configuração não
 * é tocado — habilitar de verdade é decisão do fim da fase, com base nestes números.
 */

"use strict";

const fs = require("fs");
const path = require("path");
const { carregar, topicosPorTamanho, RAIZ } = require("./lib/carregar-camada");

const PASTA_DADOS = path.join(RAIZ, "docs", "dados-piloto");

function argumento(nome, padrao) {
  const i = process.argv.indexOf("--" + nome);
  return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : padrao;
}

function agora() {
  return new Date().toISOString();
}

async function main() {
  const rotulo = argumento("rotulo", null);
  if (!rotulo) {
    console.error("Faltou --rotulo. Ex.: --rotulo onda1-v1");
    process.exitCode = 1;
    return;
  }
  const porTopico = Number(argumento("n", "10"));
  const versaoPrompt = argumento("prompt", "V1").toUpperCase();
  const limite = Number(argumento("limite", "99"));

  const camada = carregar({ silencioso: true });
  camada.CONFIG_IA.versaoPrompt = versaoPrompt;

  const pedidos = argumento("topicos", null);
  let alvos = topicosPorTamanho(camada).filter((t) => t.maxQuestoes > 0);
  if (pedidos) {
    const ids = pedidos.split(",").map((s) => s.trim());
    alvos = ids
      .map((id) => topicosPorTamanho(camada).filter((t) => t.topicoId === id)[0])
      .filter(Boolean);
  }
  alvos = alvos.slice(0, limite);

  console.log(`Amostra "${rotulo}" — prompt ${versaoPrompt} — modelo ${camada.configAtiva().modelo}`);
  console.log(`${alvos.length} tópico(s) × ${porTopico} gerações\n`);

  const amostra = {
    rotulo,
    versaoPrompt,
    modelo: camada.configAtiva().modelo,
    provedor: camada.configAtiva().provedor,
    inicio: agora(),
    geracoesPorTopico: porTopico,
    topicos: [],
  };

  for (const alvo of alvos) {
    // Habilita só nesta execução. O arquivo de configuração continua intocado.
    if (camada.CONFIG_IA.topicosComIA.indexOf(alvo.topicoId) === -1) {
      camada.CONFIG_IA.topicosComIA.push(alvo.topicoId);
    }
    // Cache limpo entre tópicos: com cache cheio, o serviço poderia servir do banco e a
    // amostra mediria o cache em vez do modelo. As questões geradas são guardadas de
    // qualquer forma no registro da amostra.
    camada.CacheQuiz.limpar();

    const registro = {
      moduloId: alvo.moduloId,
      topicoId: alvo.topicoId,
      titulo: alvo.titulo,
      caracteres: alvo.caracteres,
      maxQuestoes: alvo.maxQuestoes,
      suficiencia: alvo.suficiencia,
      limitadoPor: alvo.limitadoPor,
      geracoes: [],
    };

    process.stdout.write(`${alvo.topicoId.padEnd(26)} `);

    for (let i = 1; i <= porTopico; i++) {
      const inicio = Date.now();
      let quiz;
      try {
        quiz = await camada.obterQuiz(alvo.moduloId, alvo.topicoId, {
          numQuestoes: alvo.maxQuestoes,
          ignorarCache: true, // a amostra mede o modelo, não o banco
        });
      } catch (erro) {
        registro.geracoes.push({ indice: i, erro: erro.message, totalMs: Date.now() - inicio });
        process.stdout.write("!");
        continue;
      }

      const geracao = quiz.diagnostico.geracao || { tentativas: [] };
      const rejeicoes = geracao.tentativas.flatMap((t) => t.rejeicoes || []);

      registro.geracoes.push({
        indice: i,
        origem: quiz.origem,
        motivoFallback: quiz.diagnostico.motivoFallback || null,
        alvo: quiz.diagnostico.alvo || null,
        tentativas: geracao.tentativas.length,
        recebidas: geracao.totalRecebidas || 0,
        aprovadas: quiz.origem === "ia" ? quiz.questoes.length : 0,
        rejeitadas: geracao.totalRejeitadas || 0,
        rejeicoes: rejeicoes.map((r) => ({ motivo: r.motivo, detalhe: r.detalhe })),
        estrategiasParser: geracao.tentativas.map((t) => t.estrategiaParser || t.falha),
        latenciaModeloMs: geracao.latenciaTotalMs || 0,
        totalMs: Date.now() - inicio,
        // Texto integral, para a análise pedagógica poder ser feita depois sem regerar.
        questoes:
          quiz.origem === "ia"
            ? quiz.questoes.map((q) => ({
                enunciado: q.question,
                explicacao: q.explanation,
                conceitoAvaliado: q.conceitoAvaliado,
                alternativas: q.options.map((o) => ({ texto: o.text, correta: o.correct })),
              }))
            : [],
      });

      process.stdout.write(quiz.origem === "ia" ? "." : quiz.origem === "cache" ? "c" : "F");
    }

    const geracoes = registro.geracoes;
    const comIA = geracoes.filter((g) => g.origem === "ia");
    registro.resumo = {
      geracoes: geracoes.length,
      porOrigem: {
        ia: comIA.length,
        cache: geracoes.filter((g) => g.origem === "cache").length,
        fixo: geracoes.filter((g) => g.origem === "fixo").length,
      },
      solicitadas: geracoes.reduce((s, g) => s + (g.alvo || 0), 0),
      recebidas: geracoes.reduce((s, g) => s + g.recebidas, 0),
      aprovadas: geracoes.reduce((s, g) => s + g.aprovadas, 0),
      rejeitadas: geracoes.reduce((s, g) => s + g.rejeitadas, 0),
      tentativasTotais: geracoes.reduce((s, g) => s + (g.tentativas || 0), 0),
      retentativas: geracoes.reduce((s, g) => s + Math.max(0, (g.tentativas || 1) - 1), 0),
      latencias: geracoes.map((g) => g.totalMs).sort((a, b) => a - b),
    };
    registro.resumo.taxaAprovacao = registro.resumo.recebidas
      ? registro.resumo.aprovadas / registro.resumo.recebidas
      : null;

    const r = registro.resumo;
    const mediana = r.latencias[Math.floor(r.latencias.length / 2)] || 0;
    console.log(
      ` ${String(r.aprovadas).padStart(3)}/${String(r.recebidas).padStart(3)} aprovadas` +
        ` (${r.taxaAprovacao === null ? "—" : (r.taxaAprovacao * 100).toFixed(0) + "%"})` +
        ` | ${r.retentativas} retentativas | mediana ${(mediana / 1000).toFixed(1)}s` +
        ` | IA ${r.porOrigem.ia} / fixo ${r.porOrigem.fixo}`
    );

    amostra.topicos.push(registro);
  }

  amostra.fim = agora();

  // Métricas acumuladas, no mesmo formato da chave `quiz_ia_metricas` do navegador —
  // dá para carregar na página de diagnóstico se quiser ver na tela.
  amostra.metricas = camada.MetricasIA.resumo();
  amostra.metricasBrutas = camada.MetricasIA.lerBruto();

  fs.mkdirSync(PASTA_DADOS, { recursive: true });
  const destino = path.join(PASTA_DADOS, `${rotulo}.json`);
  fs.writeFileSync(destino, JSON.stringify(amostra, null, 2), "utf8");

  const total = amostra.topicos.reduce(
    (acc, t) => ({
      recebidas: acc.recebidas + t.resumo.recebidas,
      aprovadas: acc.aprovadas + t.resumo.aprovadas,
      geracoes: acc.geracoes + t.resumo.geracoes,
    }),
    { recebidas: 0, aprovadas: 0, geracoes: 0 }
  );

  console.log(
    `\n${total.geracoes} gerações | ${total.aprovadas}/${total.recebidas} questões aprovadas ` +
      `(${((total.aprovadas / total.recebidas) * 100).toFixed(1)}%)`
  );
  console.log(`gravado: docs/dados-piloto/${rotulo}.json`);
}

main();
