/**
 * prompt-quiz.js — montagem do prompt e do schema.
 *
 * Os textos de prompt ficam em constantes nomeadas e versionadas (sufixo _V1),
 * separadas da lógica que as monta. Assim dá para mostrar a evolução da engenharia de
 * prompt no relatório sem caçar strings dentro de funções.
 *
 * Depende de: config-ia.js
 */

// ---------------------------------------------------------------------------
// Prompt de sistema
// ---------------------------------------------------------------------------
const PROMPT_SISTEMA_V1 = [
  "Você é um professor de Biologia do ensino médio brasileiro, especialista em elaboração de avaliações.",
  "",
  "Regras que você nunca quebra:",
  "1. Você escreve exclusivamente em português do Brasil, com ortografia e acentuação corretas.",
  "2. Você formula questões usando SOMENTE o material que recebe. Você não usa conhecimento próprio",
  "   de Biologia para acrescentar fatos, números, exemplos, nomes de espécies ou classificações que",
  "   não estejam escritos no material.",
  "3. Se o material não sustentar a quantidade de questões pedida, você entrega MENOS questões.",
  "   Entregar menos é o comportamento correto. Completar com invenção é erro grave.",
  "4. Você responde SEMPRE e SOMENTE com um objeto JSON válido: sem crases, sem blocos de código,",
  "   sem markdown, sem comentários, sem nenhuma frase antes ou depois do JSON.",
].join("\n");

// ---------------------------------------------------------------------------
// Bloco de formato — usado quando o modelo NÃO respeita o parâmetro `format`.
// ---------------------------------------------------------------------------
// Contorno deliberado e documentado, não a solução preferida: os modelos :cloud
// gratuitos ignoram o JSON Schema (medido — ver docs/03-CAMADA-IA.md §5). Quando o
// provedor ativo declara `suportaSchema: true`, este bloco sai do prompt e o schema
// abaixo é enviado no parâmetro `format`, que é o mecanismo correto.
const INSTRUCAO_JSON_V1 = [
  "Responda EXATAMENTE neste formato, um único objeto JSON:",
  "",
  '{"questoes":[{"enunciado":"...","alternativas":[{"id":"a","texto":"..."},{"id":"b","texto":"..."},{"id":"c","texto":"..."},{"id":"d","texto":"..."}],"respostaCorreta":"a","explicacao":"...","conceitoAvaliado":"..."}]}',
  "",
  'Os ids das alternativas são sempre exatamente "a", "b", "c" e "d", nessa ordem.',
  '"respostaCorreta" contém o id da única alternativa correta.',
  "Não escreva mais nada além desse JSON.",
].join("\n");

// ---------------------------------------------------------------------------
// Prompt do usuário
// ---------------------------------------------------------------------------
const PROMPT_USUARIO_V1 = function (dados) {
  const partes = [];

  partes.push(
    `Gere ${dados.numQuestoes} ${dados.numQuestoes === 1 ? "questão" : "questões"} ` +
      `de múltipla escolha sobre o tópico "${dados.tituloTopico}", do módulo "${dados.tituloModulo}".`
  );
  partes.push("");
  partes.push(
    "Use EXCLUSIVAMENTE o material delimitado por <conteudo> abaixo. Cada questão, cada alternativa e",
    "cada explicação precisa poder ser conferida diretamente nesse texto. Se o material não der base",
    `para as ${dados.numQuestoes} questões, gere menos.`
  );
  partes.push("");
  partes.push("<conteudo>");
  partes.push(dados.conteudo);
  partes.push("</conteudo>");
  partes.push("");

  if (dados.conceitosExcluir && dados.conceitosExcluir.length) {
    partes.push(
      "Estes conceitos JÁ foram cobrados em tentativas anteriores. Escolha outros:",
      dados.conceitosExcluir.map((c) => `- ${c}`).join("\n"),
      ""
    );
  }

  partes.push("Requisitos de cada questão:");
  partes.push(
    "- exatamente 4 alternativas;",
    "- uma única alternativa correta;",
    "- distratores plausíveis: erros conceituais que um estudante realmente cometeria, extraídos ou",
    "  derivados do próprio material. Nada de alternativas absurdas ou obviamente descartáveis;",
    "- alternativas de comprimento parecido — a correta não pode ser a mais longa por hábito,",
    "  porque isso entrega a resposta;",
    '- é proibido usar "todas as anteriores", "nenhuma das anteriores" e variantes;',
    "- explicação de 2 a 4 frases dizendo por que a correta está certa E por que a alternativa mais",
    "  tentadora está errada;",
    "- na explicação, NUNCA cite as alternativas por letra. Nada de \"a alternativa b\", \"a opção c\",",
    "  \"letra D\". Refira-se a elas pelo que dizem: \"a alternativa que afirma que o tubo nervoso é",
    "  ventral está errada porque...\". As alternativas são reordenadas antes de chegar ao aluno, e",
    "  qualquer referência por letra fica apontando para a opção errada;",
    '- "conceitoAvaliado": o termo do material que a questão cobra, escrito como aparece no texto;',
    `- dificuldade compatível com o nível ${dados.nivel === "ensino_medio" ? "de ensino médio" : dados.nivel}.`
  );

  if (dados.motivoRejeicao) {
    partes.push("");
    partes.push(
      "ATENÇÃO — sua resposta anterior foi recusada pela validação automática pelos motivos abaixo.",
      "Corrija todos eles nesta nova tentativa:",
      dados.motivoRejeicao
    );
  }

  if (dados.incluirInstrucaoJson) {
    partes.push("");
    partes.push(INSTRUCAO_JSON_V1);
  }

  return partes.join("\n");
};

// ---------------------------------------------------------------------------
// JSON Schema — enviado no parâmetro `format` quando o provedor suporta.
// ---------------------------------------------------------------------------
const SCHEMA_QUIZ = {
  type: "object",
  properties: {
    questoes: {
      type: "array",
      items: {
        type: "object",
        properties: {
          enunciado: { type: "string" },
          alternativas: {
            type: "array",
            items: {
              type: "object",
              properties: { id: { type: "string" }, texto: { type: "string" } },
              required: ["id", "texto"],
            },
            minItems: 4,
            maxItems: 4,
          },
          respostaCorreta: { type: "string" },
          explicacao: { type: "string" },
          conceitoAvaliado: { type: "string" },
        },
        required: ["enunciado", "alternativas", "respostaCorreta", "explicacao", "conceitoAvaliado"],
      },
    },
  },
  required: ["questoes"],
};

const PromptQuiz = (function () {
  /**
   * Monta as mensagens da chamada.
   *
   * @param {object} dados
   *   topico            entrada da BASE_CONHECIMENTO
   *   tituloModulo      nome do módulo, para contexto
   *   numQuestoes       quantas pedir nesta tentativa
   *   conceitosExcluir  conceitos já cobrados (varia as perguntas entre tentativas)
   *   motivoRejeicao    texto com os motivos da recusa anterior, em caso de retentativa
   */
  function montarMensagens(dados) {
    const cfg = configAtiva();

    const conteudoUsuario = PROMPT_USUARIO_V1({
      numQuestoes: dados.numQuestoes,
      tituloTopico: dados.topico.titulo,
      tituloModulo: dados.tituloModulo || "",
      conteudo: dados.topico.conteudo,
      nivel: dados.topico.nivel,
      conceitosExcluir: dados.conceitosExcluir || [],
      motivoRejeicao: dados.motivoRejeicao || null,
      // A instrução de formato em texto só entra quando o schema não vai ser respeitado.
      incluirInstrucaoJson: !cfg.suportaSchema,
    });

    return [
      { role: "system", content: PROMPT_SISTEMA_V1 },
      { role: "user", content: conteudoUsuario },
    ];
  }

  return {
    montarMensagens,
    schema: SCHEMA_QUIZ,
    versao: "V1",
  };
})();
