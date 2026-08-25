/**
 * benchmark-fase6.js — benchmark controlado Cloud × Local. Script DE DESENVOLVIMENTO.
 *
 *     node scripts/benchmark-fase6.js --braco A --n 5
 *     node scripts/benchmark-fase6.js --braco B --n 5 --modelo-local qwen3.5:4b
 *     node scripts/benchmark-fase6.js --braco C --n 5 --modelo-local qwen3.5:4b
 *     node scripts/benchmark-fase6.js --verificar-prompts        (sem rede)
 *     node scripts/benchmark-fase6.js --sondagem --modelo-local qwen3.5:4b
 *
 * TRÊS BRAÇOS, uma variável experimental por comparação:
 *
 *   A  Cloud, gpt-oss:120b-cloud, sem schema (a nuvem ignora o parâmetro `format`)
 *   B  Local, sem schema  — prompt IDÊNTICO ao braço A  → isola o MODELO
 *   C  Local, com schema  — mesmo modelo do braço B     → isola o JSON SCHEMA
 *
 * Sem o braço B, comparar Cloud com Local mudaria modelo E prompt ao mesmo tempo: o
 * provedor local remove do prompt o bloco de instrução de JSON, porque lá o schema
 * funciona. A comparação ficaria sem causa única.
 *
 * GARANTIAS DE SEGURANÇA, verificadas em tempo de execução:
 *   1. `script/ia/config-ia.js` NUNCA é alterado. Toda troca de provedor, modelo e
 *      schema acontece em memória, no contexto `vm`.
 *   2. A gravação só acontece em `docs/dados-benchmark/`. Um caminho fora dali aborta.
 *   3. Um arquivo de resultado existente nunca é sobrescrito sem `--forcar`.
 *   4. Os dados da Fase 5, em `docs/dados-piloto/`, não são lidos nem tocados.
 *   5. Os prompts dos braços A e B são comparados por SHA-256. Se divergirem, o
 *      benchmark PARA — comparação inválida não continua em silêncio.
 */

"use strict";

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { carregar, RAIZ } = require("./lib/carregar-camada");

const PASTA_SAIDA = path.join(RAIZ, "docs", "dados-benchmark");
const PASTA_FASE5 = path.join(RAIZ, "docs", "dados-piloto");
const CONFIG = path.join(RAIZ, "script", "ia", "config-ia.js");

// ---------------------------------------------------------------------------
// Definição dos braços
// ---------------------------------------------------------------------------
const BRACOS = {
  A: {
    nome: "A — Cloud",
    provedor: "cloud",
    suportaSchema: false,
    descricao: "Referência. gpt-oss:120b-cloud. A nuvem ignora o parâmetro format.",
  },
  B: {
    nome: "B — Local sem schema",
    provedor: "local",
    suportaSchema: false,
    descricao: "Prompt idêntico ao braço A. Isola o efeito do MODELO.",
  },
  C: {
    nome: "C — Local com schema",
    provedor: "local",
    suportaSchema: true,
    descricao: "Mesmo modelo do braço B, com JSON Schema. Isola o efeito do SCHEMA.",
  },
};

const TOPICOS_PADRAO = ["filo-cordados", "filo-artropodes", "filo-moluscos"];

function argumento(nome, padrao) {
  const i = process.argv.indexOf("--" + nome);
  return i !== -1 && process.argv[i + 1] && !process.argv[i + 1].startsWith("--")
    ? process.argv[i + 1]
    : padrao;
}
const temFlag = (nome) => process.argv.indexOf("--" + nome) !== -1;

function sha256(texto) {
  return crypto.createHash("sha256").update(texto, "utf8").digest("hex");
}

/** Hash do conjunto de mensagens exatamente como vai para o modelo. */
function hashDoPrompt(mensagens) {
  return sha256(mensagens.map((m) => `${m.role}\n${m.content}`).join("\n---\n"));
}

// ---------------------------------------------------------------------------
// Salvaguardas
// ---------------------------------------------------------------------------
function impressaoDigitalDaConfig() {
  return sha256(fs.readFileSync(CONFIG, "utf8"));
}

/**
 * O arquivo de configuração é lido antes e depois da execução. Se o hash mudar, algo
 * escreveu nele — e o benchmark avisa em vez de deixar passar. A troca de provedor é
 * feita só no objeto em memória.
 */
function conferirConfigIntacta(antes) {
  const depois = impressaoDigitalDaConfig();
  if (antes !== depois) {
    console.error("\nERRO: script/ia/config-ia.js foi alterado durante a execução.");
    console.error("O benchmark não altera esse arquivo. Verifique com: git diff script/ia/config-ia.js");
    process.exitCode = 1;
    return false;
  }
  return true;
}

function destinoSeguro(nomeArquivo) {
  const destino = path.resolve(PASTA_SAIDA, nomeArquivo);
  if (!destino.startsWith(path.resolve(PASTA_SAIDA) + path.sep)) {
    throw new Error(`Destino fora de docs/dados-benchmark/: ${destino}`);
  }
  if (destino.indexOf(path.resolve(PASTA_FASE5)) === 0) {
    throw new Error("Recusado: tentativa de escrever em docs/dados-piloto/ (dados da Fase 5).");
  }
  if (fs.existsSync(destino) && !temFlag("forcar")) {
    throw new Error(
      `Já existe ${path.basename(destino)}. Use outro --rotulo, ou --forcar para sobrescrever de propósito.`
    );
  }
  return destino;
}

// ---------------------------------------------------------------------------
// Montagem do braço, em memória
// ---------------------------------------------------------------------------
function aplicarBraco(camada, chave, modeloLocal) {
  const braco = BRACOS[chave];
  if (!braco) throw new Error(`Braço "${chave}" não existe. Use A, B ou C.`);

  camada.CONFIG_IA.provedor = braco.provedor;
  camada.CONFIG_IA.provedores[braco.provedor].suportaSchema = braco.suportaSchema;
  if (braco.provedor === "local") {
    // O modelo local vem da linha de comando, e não do arquivo de configuração: a
    // escolha entre 4b e 2b é decisão de quem roda a sondagem, não do código.
    camada.CONFIG_IA.provedores.local.modelo = modeloLocal;
  }
  // O prompt é o mesmo dos 13 tópicos habilitados na Fase 5. Não muda no benchmark.
  camada.CONFIG_IA.versaoPrompt = "V4";

  return Object.assign({}, braco, { chave, configAtiva: camada.configAtiva() });
}

/**
 * Intercepta `PromptQuiz.montarMensagens` para registrar o hash de cada prompt realmente
 * enviado. Não altera arquivo nenhum: a substituição vive só no contexto `vm` desta
 * execução, e delega para a implementação original.
 */
function instrumentarPrompts(camada, registro) {
  const original = camada.PromptQuiz.montarMensagens;
  camada.PromptQuiz.montarMensagens = function (dados) {
    const mensagens = original.call(camada.PromptQuiz, dados);
    registro.push({
      topicoId: dados.topico && dados.topico.origem ? path.basename(dados.topico.origem.arquivo, ".html") : "?",
      numQuestoes: dados.numQuestoes,
      primeiraTentativa: !dados.motivoRejeicao && !(dados.conceitosExcluir || []).length,
      caracteres: mensagens.reduce((s, m) => s + m.content.length, 0),
      hash: hashDoPrompt(mensagens),
    });
    return mensagens;
  };
  return () => {
    camada.PromptQuiz.montarMensagens = original;
  };
}

// ---------------------------------------------------------------------------
// Modo --verificar-prompts: sem rede
// ---------------------------------------------------------------------------
/**
 * Monta o prompt de primeira tentativa de cada braço, para cada tópico, e compara os
 * hashes. É o teste da regra de integridade: A e B TÊM que ser idênticos; C tem que
 * diferir, porque no braço com schema o bloco de instrução de JSON sai do prompt.
 *
 * Roda sem tocar na rede, então serve de conferência antes de qualquer geração.
 */
function verificarPrompts(modeloLocal, topicos) {
  const camada = carregar({ silencioso: true, fetch: async () => { throw new Error("sem rede"); } });
  const hashes = {};

  for (const chave of ["A", "B", "C"]) {
    aplicarBraco(camada, chave, modeloLocal);
    hashes[chave] = {};
    for (const topicoId of topicos) {
      const achado = camada.ServicoQuiz.buscarTopico(moduloDe(camada, topicoId), topicoId);
      if (!achado) throw new Error(`Tópico "${topicoId}" não está na base de conhecimento.`);
      const mensagens = camada.PromptQuiz.montarMensagens({
        topico: achado.topico,
        tituloModulo: achado.tituloModulo,
        numQuestoes: achado.topico.maxQuestoes,
        conceitosExcluir: [],
        motivoRejeicao: null,
      });
      hashes[chave][topicoId] = { hash: hashDoPrompt(mensagens), caracteres: mensagens.reduce((s, m) => s + m.content.length, 0) };
    }
  }

  console.log("Conferência de prompts — primeira tentativa, sem conceitos excluídos\n");
  console.log("tópico              | braço A (cloud)  | braço B (local)  | iguais? | braço C (schema)");
  console.log("-".repeat(96));

  let todosIguais = true;
  for (const topicoId of topicos) {
    const a = hashes.A[topicoId];
    const b = hashes.B[topicoId];
    const c = hashes.C[topicoId];
    const iguais = a.hash === b.hash;
    if (!iguais) todosIguais = false;
    console.log(
      topicoId.padEnd(20) + "| " + a.hash.slice(0, 16) + " | " + b.hash.slice(0, 16) +
        " |  " + (iguais ? " SIM  " : " NÃO! ") + " | " + c.hash.slice(0, 16) +
        (c.hash === a.hash ? "  <- ATENÇÃO: igual ao A" : "")
    );
    console.log(
      " ".repeat(20) + "| " + String(a.caracteres).padStart(16) + " | " + String(b.caracteres).padStart(16) +
        " |        | " + String(c.caracteres).padStart(16) + "  (schema tira " + (a.caracteres - c.caracteres) + " car.)"
    );
  }

  console.log("\n" + (todosIguais
    ? "OK: braços A e B recebem prompts byte a byte idênticos. Comparação válida."
    : "FALHA: A e B divergem. A comparação A × B seria inválida — NÃO execute o benchmark."));

  return todosIguais;
}

function moduloDe(camada, topicoId) {
  for (const moduloId of Object.keys(camada.BASE_CONHECIMENTO)) {
    if (camada.BASE_CONHECIMENTO[moduloId].topicos[topicoId]) return moduloId;
  }
  throw new Error(`Tópico "${topicoId}" não encontrado em nenhum módulo.`);
}

// ---------------------------------------------------------------------------
// Execução de um braço
// ---------------------------------------------------------------------------
async function rodarBraco(chave, opcoes) {
  const { n, topicos, modeloLocal, rotulo, sondagem } = opcoes;
  const configAntes = impressaoDigitalDaConfig();

  // `opcoes.fetch` existe para os testes de scripts/testar-benchmark.js exercitarem o
  // benchmark inteiro sem modelo nenhum. Em uso normal fica indefinido, e a camada usa
  // o fetch de verdade.
  const camada = carregar({ silencioso: true, fetch: opcoes.fetch });
  const braco = aplicarBraco(camada, chave, modeloLocal);
  const prompts = [];
  const restaurar = instrumentarPrompts(camada, prompts);

  console.log(`Braço ${braco.nome}`);
  console.log(`  ${braco.descricao}`);
  console.log(`  modelo: ${braco.configAtiva.modelo} | schema: ${braco.configAtiva.suportaSchema ? "SIM" : "não"} | prompt: V4`);
  console.log(`  ${topicos.length} tópico(s) × ${n} gerações\n`);

  // Confere que o daemon responde antes de gastar tempo.
  const status = await camada.ClienteOllama.verificarDisponibilidade();
  if (!status.online) {
    console.error(`ERRO: Ollama não respondeu (${status.motivo}). Abra o Ollama e tente de novo.`);
    process.exitCode = 1;
    return null;
  }
  if (!status.modeloRegistrado) {
    console.error(`ERRO: o modelo "${braco.configAtiva.modelo}" não está registrado.`);
    console.error(`Rode:  ollama pull ${braco.configAtiva.modelo}`);
    console.error(`Registrados: ${(status.modelosDisponiveis || []).join(", ")}`);
    process.exitCode = 1;
    return null;
  }

  const amostra = {
    fase: 6,
    braco: chave,
    nomeDoBraco: braco.nome,
    rotulo,
    modelo: braco.configAtiva.modelo,
    provedor: braco.configAtiva.provedor,
    schemaEnviado: braco.configAtiva.suportaSchema,
    versaoPrompt: "V4",
    sondagem: !!sondagem,
    inicio: new Date().toISOString(),
    geracoesPorTopico: n,
    maquina: {
      plataforma: process.platform,
      node: process.version,
      cpus: require("os").cpus().length,
      memoriaTotalGB: Math.round((require("os").totalmem() / 1073741824) * 10) / 10,
    },
    topicos: [],
  };

  for (const topicoId of topicos) {
    const moduloId = moduloDe(camada, topicoId);
    const topico = camada.BASE_CONHECIMENTO[moduloId].topicos[topicoId];
    if (camada.CONFIG_IA.topicosComIA.indexOf(topicoId) === -1) {
      camada.CONFIG_IA.topicosComIA.push(topicoId);
    }
    camada.CacheQuiz.limpar(); // a amostra mede o modelo, não o banco

    const registro = {
      moduloId, topicoId, titulo: topico.titulo,
      caracteres: topico.metricas.caracteres, maxQuestoes: topico.maxQuestoes,
      geracoes: [],
    };
    process.stdout.write(`  ${topicoId.padEnd(20)} `);

    for (let i = 1; i <= n; i++) {
      const marcaPrompts = prompts.length;
      const inicio = Date.now();
      let quiz;
      try {
        quiz = await camada.obterQuiz(moduloId, topicoId, {
          numQuestoes: topico.maxQuestoes,
          ignorarCache: true,
        });
      } catch (erro) {
        registro.geracoes.push({ indice: i, erro: erro.message, totalMs: Date.now() - inicio });
        process.stdout.write("!");
        continue;
      }

      const geracao = quiz.diagnostico.geracao || { tentativas: [] };
      const promptsDesta = prompts.slice(marcaPrompts);
      const estrategias = geracao.tentativas.map((t) => t.estrategiaParser || t.falha);

      registro.geracoes.push({
        indice: i,
        origem: quiz.origem,
        motivoFallback: quiz.diagnostico.motivoFallback || null,
        alvo: quiz.diagnostico.alvo || null,
        tentativas: geracao.tentativas.length,
        recebidas: geracao.totalRecebidas || 0,
        aprovadas: quiz.origem === "ia" ? quiz.questoes.length : 0,
        rejeitadas: geracao.totalRejeitadas || 0,
        rejeicoes: geracao.tentativas.flatMap((t) => (t.rejeicoes || []).map((r) => ({ motivo: r.motivo, detalhe: r.detalhe }))),
        estrategiasParser: estrategias,
        // "JSON válido de primeira" é a métrica-chave do braço C: a primeira tentativa
        // produziu JSON aproveitável sem recorte nem reparo?
        jsonValidoDePrimeira: estrategias[0] === "direto",
        latenciaModeloMs: geracao.latenciaTotalMs || 0,
        totalMs: Date.now() - inicio,
        prompts: promptsDesta,
        questoes: quiz.origem === "ia" ? quiz.questoes.map((q) => ({
          enunciado: q.question,
          explicacao: q.explanation,
          conceitoAvaliado: q.conceitoAvaliado,
          alternativas: q.options.map((o) => ({ texto: o.text, correta: o.correct })),
        })) : [],
      });

      process.stdout.write(quiz.origem === "ia" ? "." : quiz.origem === "cache" ? "c" : "F");
    }

    resumirTopico(registro);
    const r = registro.resumo;
    const mediana = r.latencias[Math.floor(r.latencias.length / 2)] || 0;
    console.log(
      ` ${String(r.aprovadas).padStart(3)}/${String(r.recebidas).padStart(3)} aprovadas` +
        ` (${r.taxaAprovacao === null ? "—" : (r.taxaAprovacao * 100).toFixed(0) + "%"})` +
        ` | ${r.retentativas} retent. | JSON 1a: ${r.jsonValidoDePrimeira}/${r.geracoes}` +
        ` | mediana ${(mediana / 1000).toFixed(1)}s | IA ${r.porOrigem.ia}/${r.geracoes}`
    );
    amostra.topicos.push(registro);
  }

  restaurar();
  amostra.fim = new Date().toISOString();
  amostra.metricas = camada.MetricasIA.resumo();
  amostra.hashesDePrompt = consolidarHashes(amostra);

  if (!conferirConfigIntacta(configAntes)) return null;

  fs.mkdirSync(PASTA_SAIDA, { recursive: true });
  const destino = destinoSeguro(`${rotulo}.json`);
  fs.writeFileSync(destino, JSON.stringify(amostra, null, 2), "utf8");
  console.log(`\ngravado: docs/dados-benchmark/${path.basename(destino)}`);
  console.log(`config-ia.js intacto (sha256 inalterado)`);

  return amostra;
}

/** Hash da primeira tentativa de cada tópico — é o que sustenta a comparação A × B. */
function consolidarHashes(amostra) {
  const porTopico = {};
  for (const t of amostra.topicos) {
    for (const g of t.geracoes) {
      const primeiro = (g.prompts || []).filter((p) => p.primeiraTentativa)[0];
      if (primeiro && !porTopico[t.topicoId]) {
        porTopico[t.topicoId] = { hash: primeiro.hash, caracteres: primeiro.caracteres };
      }
    }
  }
  return porTopico;
}

function resumirTopico(registro) {
  const g = registro.geracoes;
  registro.resumo = {
    geracoes: g.length,
    porOrigem: {
      ia: g.filter((x) => x.origem === "ia").length,
      cache: g.filter((x) => x.origem === "cache").length,
      fixo: g.filter((x) => x.origem === "fixo").length,
    },
    solicitadas: g.reduce((s, x) => s + (x.alvo || 0), 0),
    recebidas: g.reduce((s, x) => s + (x.recebidas || 0), 0),
    aprovadas: g.reduce((s, x) => s + (x.aprovadas || 0), 0),
    rejeitadas: g.reduce((s, x) => s + (x.rejeitadas || 0), 0),
    retentativas: g.reduce((s, x) => s + Math.max(0, (x.tentativas || 1) - 1), 0),
    geracoesComRetentativa: g.filter((x) => (x.tentativas || 0) > 1).length,
    jsonValidoDePrimeira: g.filter((x) => x.jsonValidoDePrimeira).length,
    latencias: g.map((x) => x.totalMs).sort((a, b) => a - b),
    latenciasModelo: g.map((x) => x.latenciaModeloMs || 0).sort((a, b) => a - b),
  };
  registro.resumo.taxaAprovacao = registro.resumo.recebidas
    ? registro.resumo.aprovadas / registro.resumo.recebidas
    : null;
}

// ---------------------------------------------------------------------------
async function main() {
  const modeloLocal = argumento("modelo-local", "qwen3.5:4b");
  const topicos = (argumento("topicos", TOPICOS_PADRAO.join(","))).split(",").map((s) => s.trim());

  if (temFlag("verificar-prompts")) {
    const ok = verificarPrompts(modeloLocal, topicos);
    process.exitCode = ok ? 0 : 1;
    return;
  }

  if (temFlag("sondagem")) {
    console.log("SONDAGEM — 3 gerações em filo-cordados, para medir latência real antes de dimensionar a bateria.\n");
    await rodarBraco("B", {
      n: 3,
      topicos: ["filo-cordados"],
      modeloLocal,
      rotulo: argumento("rotulo", `fase6-sondagem-${modeloLocal.replace(/[:.]/g, "-")}`),
      sondagem: true,
    });
    console.log("\nUse a latência mediana acima para dimensionar a bateria — ver docs/06-BENCHMARK-LOCAL.md §5.");
    return;
  }

  const chave = (argumento("braco", "") || "").toUpperCase();
  if (!BRACOS[chave]) {
    console.error("Faltou --braco A, B ou C.\n");
    console.error("Modos:");
    console.error("  --verificar-prompts                     confere os hashes sem usar rede");
    console.error("  --sondagem --modelo-local qwen3.5:4b    3 gerações para medir latência");
    console.error("  --braco A --n 5                         executa um braço");
    process.exitCode = 1;
    return;
  }

  // Antes de gerar qualquer coisa, a integridade da comparação é conferida.
  if (chave === "B" || chave === "A") {
    console.log("Conferindo integridade dos prompts antes de começar…\n");
    if (!verificarPrompts(modeloLocal, topicos)) {
      console.error("\nBenchmark ABORTADO: os prompts dos braços A e B não são idênticos.");
      process.exitCode = 1;
      return;
    }
    console.log("");
  }

  const n = Number(argumento("n", "5"));
  const rotulo = argumento("rotulo", `fase6-braco-${chave}-${modeloLocal.replace(/[:.]/g, "-")}`);
  await rodarBraco(chave, { n, topicos, modeloLocal, rotulo });
}

// Só executa quando chamado direto pela linha de comando. Quando é importado por
// scripts/testar-benchmark.js, apenas expõe as funções.
if (require.main === module) {
  main();
}

module.exports = {
  BRACOS,
  TOPICOS_PADRAO,
  PASTA_SAIDA,
  PASTA_FASE5,
  aplicarBraco,
  verificarPrompts,
  rodarBraco,
  hashDoPrompt,
  destinoSeguro,
  impressaoDigitalDaConfig,
  moduloDe,
};
