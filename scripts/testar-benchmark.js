/**
 * testar-benchmark.js — testes da infraestrutura da Fase 6, SEM MODELO NENHUM.
 *
 *     node scripts/testar-benchmark.js
 *
 * Exercita o benchmark inteiro com um daemon dublado, para que a infraestrutura possa
 * ser validada antes de baixar 3,4 GB de modelo e antes de ir para o PC de mesa.
 *
 * O que estes testes protegem, em ordem de importância:
 *   1. os braços A e B recebem prompts byte a byte idênticos, e o benchmark PARA se
 *      divergirem — sem isso a comparação Cloud × Local não significa nada;
 *   2. `script/ia/config-ia.js` não é alterado por nenhum braço;
 *   3. os dados da Fase 5 não são lidos, escritos nem apagados;
 *   4. a gravação acontece só em docs/dados-benchmark/, sem sobrescrever por acidente.
 */

"use strict";

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const B = require("./benchmark-fase6");
const { carregar, RAIZ } = require("./lib/carregar-camada");

const PASTA_FASE5 = path.join(RAIZ, "docs", "dados-piloto");
const CONFIG = path.join(RAIZ, "script", "ia", "config-ia.js");

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

function sha256Arquivo(caminho) {
  return crypto.createHash("sha256").update(fs.readFileSync(caminho)).digest("hex");
}

/** Fotografa docs/dados-piloto/ para provar depois que nada mudou. */
function fotografarFase5() {
  const foto = {};
  for (const nome of fs.readdirSync(PASTA_FASE5)) {
    foto[nome] = sha256Arquivo(path.join(PASTA_FASE5, nome));
  }
  return foto;
}

/** Daemon dublado: /api/tags responde com o modelo pedido, /api/chat com JSON válido. */
function daemonFalso(modelo, comportamento) {
  const config = comportamento || {};
  let chamadas = 0;
  const fn = async function (url) {
    if (String(url).indexOf("/api/tags") !== -1) {
      return { ok: true, json: async () => ({ models: [{ name: modelo }] }) };
    }
    chamadas++;
    fn.chamadas = chamadas;
    if (config.corpo) return { ok: true, json: async () => ({ message: { content: config.corpo } }) };
    return { ok: true, json: async () => ({ message: { content: respostaValida(config.questoes || 5) } }) };
  };
  fn.chamadas = 0;
  return fn;
}

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

// ===========================================================================
function testarBracos() {
  grupo("1. Definição dos três braços");

  verificar("existem exatamente os braços A, B e C",
    JSON.stringify(Object.keys(B.BRACOS)) === '["A","B","C"]', Object.keys(B.BRACOS).join(","));

  const camada = carregar({ silencioso: true, fetch: async () => { throw new Error("sem rede"); } });

  const a = B.aplicarBraco(camada, "A", "qwen3.5:4b");
  verificar("braço A usa a nuvem", a.configAtiva.provedor === "cloud", a.configAtiva.provedor);
  verificar("braço A usa gpt-oss:120b-cloud", a.configAtiva.modelo === "gpt-oss:120b-cloud", a.configAtiva.modelo);
  verificar("braço A não envia schema", a.configAtiva.suportaSchema === false);

  const b = B.aplicarBraco(camada, "B", "qwen3.5:4b");
  verificar("braço B usa o modelo local pedido na linha de comando",
    b.configAtiva.modelo === "qwen3.5:4b", b.configAtiva.modelo);
  verificar("braço B NÃO envia schema (prompt igual ao A)", b.configAtiva.suportaSchema === false);

  const c = B.aplicarBraco(camada, "C", "qwen3.5:4b");
  verificar("braço C usa o MESMO modelo do braço B",
    c.configAtiva.modelo === b.configAtiva.modelo, c.configAtiva.modelo);
  verificar("braço C envia schema", c.configAtiva.suportaSchema === true);

  const d = B.aplicarBraco(camada, "B", "qwen3.5:2b");
  verificar("o modelo local é parametrizável (fallback 2b)", d.configAtiva.modelo === "qwen3.5:2b", d.configAtiva.modelo);

  verificar("todos os braços usam o prompt V4", camada.CONFIG_IA.versaoPrompt === "V4", camada.CONFIG_IA.versaoPrompt);

  let erro = null;
  try { B.aplicarBraco(camada, "Z", "x"); } catch (e) { erro = e.message; }
  verificar("braço inexistente é recusado", /não existe/.test(erro || ""), erro);
}

function testarHashes() {
  grupo("2. Integridade dos prompts (SHA-256)");

  const camada = carregar({ silencioso: true, fetch: async () => { throw new Error("sem rede"); } });
  const topicos = B.TOPICOS_PADRAO;
  const hash = {};

  for (const chave of ["A", "B", "C"]) {
    B.aplicarBraco(camada, chave, "qwen3.5:4b");
    hash[chave] = {};
    for (const topicoId of topicos) {
      const moduloId = B.moduloDe(camada, topicoId);
      const achado = camada.ServicoQuiz.buscarTopico(moduloId, topicoId);
      const mensagens = camada.PromptQuiz.montarMensagens({
        topico: achado.topico, tituloModulo: achado.tituloModulo,
        numQuestoes: achado.topico.maxQuestoes, conceitosExcluir: [], motivoRejeicao: null,
      });
      hash[chave][topicoId] = B.hashDoPrompt(mensagens);
    }
  }

  for (const topicoId of topicos) {
    verificar(`${topicoId}: hash do braço A é idêntico ao do braço B`,
      hash.A[topicoId] === hash.B[topicoId],
      `${hash.A[topicoId].slice(0, 12)} vs ${hash.B[topicoId].slice(0, 12)}`);
    verificar(`${topicoId}: hash do braço C difere (o schema tira o bloco de JSON)`,
      hash.C[topicoId] !== hash.A[topicoId]);
  }

  verificar("tópicos diferentes produzem hashes diferentes",
    new Set(topicos.map((t) => hash.A[t])).size === topicos.length);

  verificar("verificarPrompts() aprova a configuração atual",
    B.verificarPrompts("qwen3.5:4b", topicos) === true);

  // O hash tem que reagir a qualquer mudança no conteúdo enviado.
  B.aplicarBraco(camada, "A", "qwen3.5:4b");
  const achado = camada.ServicoQuiz.buscarTopico("animais", "filo-cordados");
  const base = B.hashDoPrompt(camada.PromptQuiz.montarMensagens({
    topico: achado.topico, tituloModulo: achado.tituloModulo, numQuestoes: 5,
    conceitosExcluir: [], motivoRejeicao: null,
  }));
  const comConceitos = B.hashDoPrompt(camada.PromptQuiz.montarMensagens({
    topico: achado.topico, tituloModulo: achado.tituloModulo, numQuestoes: 5,
    conceitosExcluir: ["Notocorda"], motivoRejeicao: null,
  }));
  verificar("o hash muda quando o prompt muda (conceitosExcluir)", base !== comConceitos);
}

function testarSalvaguardas() {
  grupo("3. Salvaguardas de escrita");

  let erro = null;
  try { B.destinoSeguro("../dados-piloto/onda1-v1-cordados.json"); } catch (e) { erro = e.message; }
  verificar("recusa gravar fora de docs/dados-benchmark/", erro !== null, erro);

  erro = null;
  try { B.destinoSeguro("../../fora.json"); } catch (e) { erro = e.message; }
  verificar("recusa caminho que escapa da pasta de saída", erro !== null, erro);

  const alvo = path.join(B.PASTA_SAIDA, "teste-nao-sobrescrever.json");
  fs.mkdirSync(B.PASTA_SAIDA, { recursive: true });
  fs.writeFileSync(alvo, "{}", "utf8");
  erro = null;
  try { B.destinoSeguro("teste-nao-sobrescrever.json"); } catch (e) { erro = e.message; }
  verificar("recusa sobrescrever resultado existente sem --forcar", /Já existe/.test(erro || ""), erro);
  fs.unlinkSync(alvo);

  verificar("aceita um nome novo dentro da pasta certa", (() => {
    try { return B.destinoSeguro("resultado-novo.json").indexOf("dados-benchmark") !== -1; }
    catch (e) { return false; }
  })());

  verificar("a pasta da Fase 6 é diferente da pasta da Fase 5",
    path.resolve(B.PASTA_SAIDA) !== path.resolve(B.PASTA_FASE5));
}

async function testarExecucaoCompleta() {
  grupo("4. Execução completa com daemon dublado");

  const fotoAntes = fotografarFase5();
  const configAntes = sha256Arquivo(CONFIG);
  const rotulo = "teste-mock-braco-B";
  const destino = path.join(B.PASTA_SAIDA, `${rotulo}.json`);
  if (fs.existsSync(destino)) fs.unlinkSync(destino);

  const daemon = daemonFalso("qwen3.5:4b", { questoes: 5 });
  const amostra = await B.rodarBraco("B", {
    n: 2,
    topicos: ["filo-cordados", "filo-moluscos"],
    modeloLocal: "qwen3.5:4b",
    rotulo,
    fetch: daemon,
  });

  verificar("a execução devolveu uma amostra", !!amostra);
  if (!amostra) return;

  verificar("amostra identificada como Fase 6", amostra.fase === 6);
  verificar("braço registrado", amostra.braco === "B", amostra.braco);
  verificar("modelo registrado", amostra.modelo === "qwen3.5:4b", amostra.modelo);
  verificar("schema registrado como não enviado", amostra.schemaEnviado === false);
  verificar("prompt V4 registrado", amostra.versaoPrompt === "V4");
  verificar("dois tópicos medidos", amostra.topicos.length === 2, String(amostra.topicos.length));
  verificar("máquina registrada (para comparar entre PCs)",
    !!amostra.maquina && amostra.maquina.cpus > 0 && amostra.maquina.memoriaTotalGB > 0,
    JSON.stringify(amostra.maquina));

  const cordados = amostra.topicos[0];
  verificar("2 gerações por tópico", cordados.resumo.geracoes === 2, String(cordados.resumo.geracoes));
  verificar("questões recebidas contabilizadas", cordados.resumo.recebidas === 10, String(cordados.resumo.recebidas));
  verificar("taxa de aprovação calculada", cordados.resumo.taxaAprovacao !== null);
  verificar("latências coletadas por geração", cordados.resumo.latencias.length === 2);
  verificar("JSON válido de primeira contabilizado",
    cordados.resumo.jsonValidoDePrimeira === 2, String(cordados.resumo.jsonValidoDePrimeira));
  verificar("retentativas contabilizadas", typeof cordados.resumo.retentativas === "number");
  verificar("origem de cada geração registrada",
    cordados.geracoes.every((g) => ["ia", "cache", "fixo"].indexOf(g.origem) !== -1));
  verificar("texto integral das questões guardado",
    cordados.geracoes[0].questoes.length === 5 && !!cordados.geracoes[0].questoes[0].enunciado);
  verificar("alternativas guardadas com a marca de correta",
    cordados.geracoes[0].questoes[0].alternativas.filter((a) => a.correta).length === 1);

  verificar("hash do prompt gravado por tópico",
    !!amostra.hashesDePrompt["filo-cordados"] && amostra.hashesDePrompt["filo-cordados"].hash.length === 64,
    JSON.stringify(Object.keys(amostra.hashesDePrompt)));
  verificar("cada geração guarda os prompts que enviou",
    (cordados.geracoes[0].prompts || []).length > 0);

  verificar("o arquivo foi gravado em docs/dados-benchmark/", fs.existsSync(destino));
  verificar("config-ia.js NÃO foi alterado", sha256Arquivo(CONFIG) === configAntes);

  const fotoDepois = fotografarFase5();
  verificar("nenhum arquivo da Fase 5 foi alterado",
    JSON.stringify(fotoAntes) === JSON.stringify(fotoDepois));
  verificar("nenhum arquivo da Fase 5 foi apagado",
    Object.keys(fotoDepois).length === Object.keys(fotoAntes).length &&
    Object.keys(fotoAntes).length === 9,
    `${Object.keys(fotoDepois).length} arquivos`);

  fs.unlinkSync(destino);
}

async function testarFalhas() {
  grupo("5. Comportamento diante de falhas");

  const rotulo = "teste-mock-falhas";
  const destino = path.join(B.PASTA_SAIDA, `${rotulo}.json`);
  if (fs.existsSync(destino)) fs.unlinkSync(destino);

  // Modelo não registrado: o braço tem que recusar antes de gastar tempo.
  const semModelo = async function (url) {
    if (String(url).indexOf("/api/tags") !== -1) {
      return { ok: true, json: async () => ({ models: [{ name: "outro-modelo" }] }) };
    }
    return { ok: true, json: async () => ({ message: { content: respostaValida(1) } }) };
  };
  const r1 = await B.rodarBraco("B", {
    n: 1, topicos: ["filo-moluscos"], modeloLocal: "qwen3.5:4b", rotulo, fetch: semModelo,
  });
  verificar("modelo não registrado -> aborta sem gravar", r1 === null && !fs.existsSync(destino));
  process.exitCode = 0; // rodarBraco marca exitCode ao abortar; o teste segue

  // Daemon fora do ar.
  const offline = async () => { throw new TypeError("failed to fetch"); };
  const r2 = await B.rodarBraco("B", {
    n: 1, topicos: ["filo-moluscos"], modeloLocal: "qwen3.5:4b", rotulo, fetch: offline,
  });
  verificar("daemon offline -> aborta sem gravar", r2 === null && !fs.existsSync(destino));
  process.exitCode = 0;

  // Resposta sem JSON: a cascata cai no quiz fixo e o benchmark registra, não quebra.
  const semJson = daemonFalso("qwen3.5:4b", { corpo: "Desculpe, não vou responder em JSON." });
  const r3 = await B.rodarBraco("B", {
    n: 1, topicos: ["filo-moluscos"], modeloLocal: "qwen3.5:4b", rotulo, fetch: semJson,
  });
  verificar("resposta inválida -> registra fallback em vez de quebrar",
    !!r3 && r3.topicos[0].geracoes[0].origem === "fixo",
    r3 ? r3.topicos[0].geracoes[0].origem : "null");
  verificar("motivo do fallback registrado",
    !!r3 && !!r3.topicos[0].geracoes[0].motivoFallback,
    r3 ? r3.topicos[0].geracoes[0].motivoFallback : "");
  verificar("jsonValidoDePrimeira marcado como falso",
    !!r3 && r3.topicos[0].geracoes[0].jsonValidoDePrimeira === false);
  if (fs.existsSync(destino)) fs.unlinkSync(destino);
}

/**
 * Calibra o detector de termo inédito contra o caso REAL da Fase 5: a questão em que o
 * modelo escreveu "trilobulados" no lugar de "triblásticos".
 *
 * A amostra da Fase 5 é aberta em modo LEITURA, só para conferir o detector. Nada é
 * escrito, e os resultados das duas fases seguem separados.
 */
function testarDetectorDeTermoInedito() {
  grupo("6. Detector de termo técnico inédito (calibrado no caso real da Fase 5)");

  const C = require("./comparar-benchmark");
  const camada = carregar({ silencioso: true, fetch: async () => { throw new Error("sem rede"); } });
  const V = camada.ValidadorQuiz;
  const material = V.normalizar(camada.BASE_CONHECIMENTO.animais.topicos["filo-cordados"].conteudo);

  verificar('pega "trilobulados", que nao existe no material',
    C.termosIneditos("São celomados, trilobulados e deuterostômios.", material, V.normalizar)
      .indexOf("trilobulados") !== -1);

  verificar('NAO acusa "deuterostomios", que esta no material',
    C.termosIneditos("São deuterostômios.", material, V.normalizar).length === 0);

  verificar('NAO acusa "cartilaginoso", que esta no material',
    C.termosIneditos("Peixes com esqueleto cartilaginoso.", material, V.normalizar).length === 0);

  verificar("NAO acusa plural nem flexao (compara por radical)",
    C.termosIneditos("As fendas faríngeas permanecem no adulto.", material, V.normalizar).length === 0,
    JSON.stringify(C.termosIneditos("As fendas faríngeas permanecem no adulto.", material, V.normalizar)));

  verificar("NAO acusa palavras longas comuns do enunciado",
    C.termosIneditos("Apresentam características gerais importantes.", material, V.normalizar).length === 0,
    JSON.stringify(C.termosIneditos("Apresentam características gerais importantes.", material, V.normalizar)));

  // Calibragem: quantas das 74 questões da revalidação V4 o detector marcaria?
  // Um detector que marca metade da amostra não serve para orientar leitura.
  const caminho = path.join(PASTA_FASE5, "onda9-v4-cordados-revalidacao.json");
  if (fs.existsSync(caminho)) {
    const amostra = JSON.parse(fs.readFileSync(caminho, "utf8"));
    const questoes = amostra.topicos[0].geracoes.flatMap((g) => g.questoes || []);
    const marcadas = questoes.filter((q) => {
      const correta = q.alternativas.filter((a) => a.correta)[0];
      return correta && C.termosIneditos(correta.texto, material, V.normalizar).length > 0;
    });
    const pegouTrilobulados = marcadas.some((q) =>
      /trilobulad/i.test(q.alternativas.filter((a) => a.correta)[0].texto));

    console.log(`        calibragem: ${marcadas.length} de ${questoes.length} questões marcadas ` +
      `(${((marcadas.length / questoes.length) * 100).toFixed(1)}%)`);
    for (const q of marcadas.slice(0, 5)) {
      const correta = q.alternativas.filter((a) => a.correta)[0];
      console.log(`          - ${C.termosIneditos(correta.texto, material, V.normalizar).join(", ")}`);
    }

    verificar("encontra o defeito real da Fase 5 na amostra de revalidação", pegouTrilobulados);
    verificar("marca menos de 20% da amostra (senão não orienta leitura)",
      marcadas.length / questoes.length < 0.2,
      `${((marcadas.length / questoes.length) * 100).toFixed(1)}%`);
  }

  verificar("a amostra da Fase 5 continua intacta apos a leitura",
    fs.existsSync(caminho) && fs.statSync(caminho).size > 0);
}

// ---------------------------------------------------------------------------
async function main() {
  console.log("Testes da infraestrutura da Fase 6 — sem modelo, sem rede");
  console.log("=========================================================");

  testarBracos();
  testarHashes();
  testarSalvaguardas();
  await testarExecucaoCompleta();
  await testarFalhas();
  testarDetectorDeTermoInedito();

  console.log("\n" + "=".repeat(58));
  console.log(`${passou} passaram, ${falhou} falharam`);
  if (falhas.length) {
    console.log("\nFalhas:");
    for (const f of falhas) console.log("  - " + f);
  }
  process.exitCode = falhou ? 1 : 0;
}

main();
