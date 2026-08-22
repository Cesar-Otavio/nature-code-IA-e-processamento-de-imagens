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
// V2 — regra acrescentada na Fase 5. ALTERAÇÃO ÚNICA em relação ao V1.
// ---------------------------------------------------------------------------
// Motivo: numa geração observada, o modelo tratou o título de seção
// "## Características exclusivas" como se fosse uma classificação exaustiva. Como só o
// tubo nervoso dorsal aparece sob aquele título — a notocorda e as fendas faríngeas têm
// seções próprias —, ele produziu "qual é a característica exclusiva dos cordados?" com
// três alternativas igualmente verdadeiras. O próprio quiz fixo do site diz que os três
// são exclusivos.
//
// Não é alucinação: é fidelidade à ORGANIZAÇÃO do texto em vez de fidelidade ao que o
// texto AFIRMA. A regra abaixo separa as duas coisas.
//
// Esta é a única diferença entre V1 e V2, para que a comparação antes × depois tenha
// uma causa só. Ver docs/05-AVALIACAO-PILOTO.md.
const REGRA_SECOES_V2 = [
  "",
  "SOBRE A ORGANIZAÇÃO DO MATERIAL:",
  "Os títulos de seção (as linhas que começam com ##) servem para organizar o texto e NÃO são",
  "listas exaustivas. Um fato que aparece sob um título continua valendo para o tópico inteiro, e",
  "um fato que aparece em outra seção não deixa de valer por isso. Exemplo: se houver uma seção",
  '"Características exclusivas" com um item, isso NÃO significa que os assuntos das outras seções',
  "não sejam também exclusivos.",
  "Portanto: a resposta correta tem que se sustentar no que o texto AFIRMA, nunca em ONDE o fato",
  "está escrito. Se a pergunta só tiver uma resposta certa por causa da divisão em seções, ela tem",
  "mais de uma resposta certa de verdade — não faça essa pergunta.",
].join("\n");

// ---------------------------------------------------------------------------
// V3 — regra acrescentada na Fase 5. ALTERAÇÃO ÚNICA em relação ao V1.
// ---------------------------------------------------------------------------
// Motivo: o único defeito pedagógico confirmado na leitura de 193 questões apareceu num
// enunciado negativo. "Sobre os condrictes, qual característica NÃO se aplica a eles?"
// trazia "possuem bexiga natatória" como resposta e "possuem brânquias externas" como
// distrator — só que condrictes também não têm brânquias externas, então havia duas
// respostas válidas. A própria explicação do modelo hesitava: "mandíbula e brânquias
// externas não são mencionadas... ainda assim, a única opção explicitamente refutada
// pelo texto é...".
//
// A causa é estrutural: numa pergunta negativa, as três alternativas que NÃO são a
// resposta precisam ser verdadeiras, e o modelo tende a inventá-las em vez de tirá-las
// do texto. A regra fecha essa porta.
//
// V3 = V1 + esta regra. Não é V2 + regra: V2 foi medido e recusado (ver
// docs/05-AVALIACAO-PILOTO.md), então acumular as duas confundiria as causas.
const REGRA_NEGATIVAS_V3 = [
  "",
  "SOBRE PERGUNTAS NEGATIVAS:",
  'Se você formular uma pergunta do tipo "qual NÃO se aplica", "assinale a INCORRETA", "EXCETO"',
  "ou equivalente, as TRÊS alternativas que não são a resposta precisam ser afirmações que o",
  "material declara explicitamente sobre AQUELE MESMO assunto. Não invente características",
  "plausíveis para preencher; não use afirmações que o texto apenas deixa de mencionar.",
  "Se o material não tiver três afirmações explícitas sobre o assunto, NÃO faça a pergunta na",
  "forma negativa — reescreva na forma afirmativa.",
  "Motivo: numa pergunta negativa, qualquer alternativa que também seja falsa vira uma segunda",
  "resposta correta, e a questão passa a ter duas respostas.",
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

  if (dados.regraExtra) {
    partes.push(dados.regraExtra);
  }

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
      // A versão do prompt é escolhida na configuração. Cada versão acrescenta ao V1
      // UMA regra e nada mais, para que a comparação entre elas tenha causa única.
      //   V1  original
      //   V2  + regra sobre títulos de seção
      //   V3  + regra sobre perguntas negativas
      //   V4  as duas regras — é o padrão adotado ao fim da Fase 5
      regraExtra: {
        V2: REGRA_SECOES_V2,
        V3: REGRA_NEGATIVAS_V3,
        V4: REGRA_NEGATIVAS_V3 + "\n" + REGRA_SECOES_V2,
      }[CONFIG_IA.versaoPrompt] || null,
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
