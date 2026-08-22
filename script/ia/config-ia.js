/**
 * config-ia.js — configuração central da camada de IA.
 *
 * É o único arquivo que precisa ser editado para trocar de modelo, de provedor ou de
 * parâmetros de geração. Nenhum outro arquivo da camada conhece nome de modelo ou URL.
 *
 * Script clássico, sem módulos ES: precisa ser carregado por <script> ANTES dos demais
 * arquivos de script/ia/. É o mesmo padrão que o site já usa.
 */

const CONFIG_IA = {
  // Chave geral. Em false, o site inteiro volta ao comportamento original sem tocar em
  // mais nada — útil como botão de pânico no dia da apresentação.
  habilitada: true,

  // ---------------------------------------------------------------------------
  // TROCA DE MODELO: mude apenas esta linha.
  // ---------------------------------------------------------------------------
  // "cloud" -> modelo hospedado, repassado pelo daemon local para ollama.com
  // "local" -> modelo rodando na própria máquina
  provedor: "cloud",

  provedores: {
    cloud: {
      rotulo: "Ollama Cloud",
      modelo: "gpt-oss:120b-cloud",
      host: "http://localhost:11434",

      // MEDIDO em 19/08/2026: nenhum modelo :cloud respeita o parâmetro `format` com
      // JSON Schema. O daemon repassa a requisição para ollama.com, e a restrição por
      // gramática (que é aplicada pelo runner local) não chega lá. Testado nos três
      // modelos gratuitos, em /api/chat e /api/generate, com schema e com "json", e
      // com think:false e think:"low" — todas as combinações devolveram Markdown.
      // Ver docs/03-CAMADA-IA.md §5.
      suportaSchema: false,

      timeoutMs: 120000,
    },

    local: {
      rotulo: "Ollama local",
      // Ainda não escolhido: será definido por benchmark na Fase 6. Trocar esta string
      // e `provedor: "local"` acima é tudo o que a migração exige.
      modelo: "qwen3:4b",
      host: "http://localhost:11434",

      // No modelo local o `format` funciona de verdade: a restrição por gramática é
      // aplicada pelo runner na própria máquina. Quando este provedor for ativado, a
      // camada passa a mandar o JSON Schema automaticamente — sem mudar mais nada.
      suportaSchema: true,

      // Inferência em CPU é bem mais lenta; o timeout precisa acompanhar.
      timeoutMs: 300000,
    },
  },

  // Parâmetros de geração, iguais para os dois provedores.
  geracao: {
    temperatura: 0.7,
    topP: 0.9,
    // Teto de tokens da resposta. O número saiu de medição, não de chute: com 3000,
    // 4 de 11 respostas (36%) vinham com o JSON cortado no meio de uma string e
    // precisavam do reparo do parser. Com 4500, 12 de 12 vieram inteiras.
    // Um pedido de 5 questões com explicação de 2 a 4 frases não cabe em 3000 tokens.
    numPredict: 4500,
  },

  numQuestoesPadrao: 5,
  maxTentativas: 3,

  // Migração gradual: só estes tópicos usam IA; os demais seguem com quiz fixo.
  // Um tópico listado aqui ainda pode ser recusado em tempo de execução se a base de
  // conhecimento disser que ele não tem texto suficiente (maxQuestoes = 0).
  //
  // Lista definida na Fase 5 por medição: 190 gerações, 435 questões, ~90 lidas uma a
  // uma. Cada tópico entrou por atender três critérios ao mesmo tempo — entregar quiz
  // por IA em pelo menos 80% das tentativas, taxa de aprovação estrutural acima de 70%
  // e nenhum defeito pedagógico não corrigido na leitura. Números por tópico em
  // docs/05-AVALIACAO-PILOTO.md.
  topicosComIA: [
    // Reino Animal
    "filo-cordados",
    "filo-artropodes",
    "filo-poriferos",
    "filo-equinodermos",
    "filo-cnidarios",
    "filo-moluscos",
    "reino-animalia",
    // Plantas
    "pteridofitas",
    "briofitas",
    // Ecossistemas
    "fluxo-de-energia",
    "piramides-ecologicas",
    "ecossistemas-da-terra",
    "sucessao-ecologica",
  ],

  // Fora da lista de propósito, com o motivo medido:
  //   reino-plantae ............. o modelo devolveu quiz em 1 de 10 tentativas
  //   definicao-e-componentes ... 3 de 10
  //   mundo-vivo-ecologia ....... 4 de 10
  //     Nesses três o modelo respondeu {"questoes":[]} — ele mesmo julgou o material
  //     insuficiente. Habilitá-los faria o aluno esperar alguns segundos para receber o
  //     quiz fixo na maioria das vezes.
  //   angiospermas, gimnospermas, filo-platelmintos, filo-anelideos e
  //   filo-nematelmintos ........ maxQuestoes = 0 desde a Fase 1; nem chegam a ser
  //                               consultados em tempo de execução.

  cacheHabilitado: true,

  // Versão do prompt do usuário. Cada versão acrescenta ao V1 uma regra e nada mais,
  // para que a comparação entre elas tenha causa única. Ver script/ia/prompt-quiz.js.
  //   V1  original
  //   V2  + títulos de seção não são exaustivos — MEDIDO E RECUSADO: não reduziu o
  //         problema que mirava e derrubou a aprovação de 92,3% para 87,4%
  //   V3  + perguntas negativas exigem três não-respostas explícitas no texto —
  //         enunciados negativos caíram de 5,2% para 2,1% em Cordados e os que
  //         restaram vieram ancorados no material
  //   V4  as duas regras juntas — ADOTADO. Medido em Artrópodes, onde o defeito de
  //         título de seção realmente ocorria: aprovação 80% -> 91%, retentativas
  //         5 -> 2, e os distratores deixaram de ser fatos verdadeiros de outra seção
  // Números em docs/05-AVALIACAO-PILOTO.md.
  versaoPrompt: "V4",

  // true -> loga no console o prompt enviado, a resposta crua e o motivo de cada rejeição.
  modoDebug: false,
};

/**
 * Devolve a configuração do provedor ativo, já achatada.
 * Todo o resto da camada usa isto e nunca lê `CONFIG_IA.provedores` diretamente.
 */
function configAtiva() {
  const provedor = CONFIG_IA.provedores[CONFIG_IA.provedor];
  if (!provedor) {
    throw new Error(
      `CONFIG_IA.provedor = "${CONFIG_IA.provedor}" não existe. ` +
        `Valores válidos: ${Object.keys(CONFIG_IA.provedores).join(", ")}`
    );
  }
  return {
    provedor: CONFIG_IA.provedor,
    rotulo: provedor.rotulo,
    modelo: provedor.modelo,
    host: provedor.host,
    suportaSchema: provedor.suportaSchema,
    timeoutMs: provedor.timeoutMs,
    geracao: CONFIG_IA.geracao,
  };
}

/**
 * Descobre módulo e tópico a partir da URL da página, sem precisar de atributo nenhum
 * no HTML. A estrutura de pastas do site já é um identificador estável e sem acentos:
 *
 *   /pages/modulos/topicos/topicos-animais/filo-cordados.html
 *                          └── módulo: animais    └── tópico: filo-cordados
 *
 * Devolve null quando o caminho não bate — e null faz a cascata cair no quiz fixo,
 * que é o comportamento seguro. Ver docs/00-MAPEAMENTO.md §9.
 */
function identificarTopicoPelaUrl(caminho) {
  const url = caminho || (typeof location !== "undefined" ? location.pathname : "");
  const achado = url.match(/\/topicos-([a-z-]+)\/([a-z0-9-]+)\.html?$/i);
  if (!achado) return null;
  return { moduloId: achado[1].toLowerCase(), topicoId: achado[2].toLowerCase() };
}

/** Registra no console apenas quando modoDebug está ligado. */
function logIA(...argumentos) {
  if (CONFIG_IA.modoDebug && typeof console !== "undefined") {
    console.log("[ia]", ...argumentos);
  }
}
