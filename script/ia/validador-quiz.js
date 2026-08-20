/**
 * validador-quiz.js — camada obrigatória. Nenhuma questão chega à tela sem passar aqui.
 *
 * O parser é tolerante para achar o JSON; este arquivo é o oposto: rigoroso, e recusa
 * sem dó. Uma resposta inválida da IA nunca é aceita em silêncio — ou é recusada com
 * motivo registrado, ou não passa.
 *
 * A validação é por questão, não por resposta inteira: se o modelo mandar 5 questões e
 * 2 forem ruins, aproveitam-se as 3 boas e pedem-se as que faltam numa nova tentativa.
 * Isso conversa com a regra do projeto de entregar menos questões em vez de inventar.
 *
 * Depende de: config-ia.js, metricas-ia.js
 */

const ValidadorQuiz = (function () {
  // ---------------------------------------------------------------------------
  // Limiares. Todos ajustáveis e todos justificados em docs/03-CAMADA-IA.md §7.
  // ---------------------------------------------------------------------------
  const LIMIARES = {
    MIN_ENUNCIADO: 25, // caracteres
    MIN_ALTERNATIVA: 2,
    MIN_EXPLICACAO: 60, // 2 a 4 frases não cabem em menos que isso
    NUM_ALTERNATIVAS: 4,

    // Vazamento clássico de resposta: a correta ser sistematicamente a mais longa.
    // Só acusa quando a diferença é grande nos dois critérios ao mesmo tempo, para não
    // punir uma correta que é legitimamente um pouco mais descritiva.
    FATOR_COMPRIMENTO: 1.7, // correta / média das outras
    DIFERENCA_MINIMA_CARACTERES: 25,

    // Anti-alucinação: fração das palavras de conteúdo que precisa aparecer no material.
    COBERTURA_CONCEITO: 0.5,
    COBERTURA_ENUNCIADO: 0.35,
  };

  // A explicação não pode citar alternativa por letra.
  //
  // Não é preciosismo: o serviço embaralha as alternativas antes de exibir (modelos de
  // linguagem tendem a colocar a resposta certa sempre na mesma posição), então
  // "a alternativa c está errada" passa a apontar para outra opção depois do sorteio.
  // Defeito observado numa geração real na Fase 2 — ver docs/03-CAMADA-IA.md §9.
  // A saída correta é a explicação descrever a alternativa pelo que ela diz.
  //
  // A letra "a" sozinha é artigo e preposição em português, então só conta como citação
  // quando vem entre aspas, colada em pontuação, ou seguida de verbo — senão "as
  // alternativas a seguir" viraria falso positivo.
  const CITACAO_POR_LETRA = [
    /\b(alternativas?|op(ç|c)(õ|o)es?|letras?|itens?|item)\s+["'“]?[b-dB-D]\b/,
    /\b(alternativas?|op(ç|c)(õ|o)es?|letras?|itens?|item)\s+["'“][aA]/,
    /\b(alternativas?|op(ç|c)(õ|o)es?|letras?|itens?|item)\s+[aA]\s*[,.;:)]/,
    /\b(alternativas?|op(ç|c)(õ|o)es?|letras?|itens?|item)\s+[aA]\s+(est[áa]|[ée]|eh|afirma|diz|descreve|apresenta|traz|menciona|indica|confunde|inverte|ignora|sugere)\b/,
    /(^|\s)[a-dA-D]\)/,
  ];

  const EXPRESSOES_PROIBIDAS = [
    /todas as (anteriores|alternativas|op(c|ç)(o|õ)es)/i,
    /nenhuma das (anteriores|alternativas|op(c|ç)(o|õ)es)/i,
    /(todas|nenhuma) as acima/i,
    /^n\.?d\.?a\.?$/i,
    /^(todas|nenhuma)$/i,
  ];

  // Palavras sem carga semântica, descartadas antes de medir sobreposição com o material.
  const VAZIAS = new Set(
    ("a as o os um uma uns umas de do da dos das em no na nos nas por para com sem sobre entre " +
      "e ou mas que qual quais quando onde como porque pois se ja nao sim seu sua seus suas " +
      "este esta estes estas esse essa esses essas aquele aquela isso isto ser sao eh foi era " +
      "tem tem possui possuem apresenta apresentam pode podem deve devem mais menos muito pouco " +
      "todo toda todos todas cada outro outra outros outras seguinte seguintes abaixo acima " +
      "alternativa alternativas questao opcao correta correto incorreta incorreto assinale " +
      "considerando respeito referente relacao").split(" ")
  );

  /** minúsculas, sem acento, só letras, números e espaço. */
  function normalizar(texto) {
    return String(texto == null ? "" : texto)
      .toLowerCase()
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .replace(/[^a-z0-9\s]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function palavrasDeConteudo(texto) {
    return normalizar(texto)
      .split(" ")
      .filter((p) => p.length > 3 && !VAZIAS.has(p));
  }

  /**
   * Fração das palavras de conteúdo de `trecho` que aparecem em `materialNormalizado`.
   * Devolve 1 quando não sobra nenhuma palavra a checar — nesse caso a checagem não se
   * aplica, e recusar seria arbitrário.
   */
  function cobertura(trecho, materialNormalizado) {
    const palavras = palavrasDeConteudo(trecho);
    if (!palavras.length) return 1;
    let encontradas = 0;
    for (const palavra of palavras) {
      // Prefixo de 4 letras absorve plural e flexão ("cordado"/"cordados", "fenda"/"fendas").
      const radical = palavra.slice(0, Math.max(4, palavra.length - 2));
      if (materialNormalizado.indexOf(radical) !== -1) encontradas++;
    }
    return encontradas / palavras.length;
  }

  function textoVazio(valor) {
    return typeof valor !== "string" || valor.trim() === "";
  }

  /**
   * Valida UMA questão. Devolve null se passou, ou {motivo, detalhe} se caiu.
   * O `motivo` é uma chave curta e estável — é ele que vira contador nas métricas.
   */
  function validarQuestao(questao, materialNormalizado) {
    if (!questao || typeof questao !== "object") {
      return { motivo: "nao_e_objeto", detalhe: "a questão não é um objeto" };
    }

    // ----- estrutural -----
    if (textoVazio(questao.enunciado)) {
      return { motivo: "campo_faltando", detalhe: "enunciado ausente ou vazio" };
    }
    if (textoVazio(questao.explicacao)) {
      return { motivo: "campo_faltando", detalhe: "explicação ausente ou vazia" };
    }
    if (textoVazio(questao.conceitoAvaliado)) {
      return { motivo: "campo_faltando", detalhe: "conceitoAvaliado ausente ou vazio" };
    }
    if (textoVazio(questao.respostaCorreta)) {
      return { motivo: "campo_faltando", detalhe: "respostaCorreta ausente ou vazia" };
    }
    if (!Array.isArray(questao.alternativas)) {
      return { motivo: "campo_faltando", detalhe: "alternativas não é uma lista" };
    }
    if (questao.alternativas.length !== LIMIARES.NUM_ALTERNATIVAS) {
      return {
        motivo: "numero_de_alternativas",
        detalhe: `vieram ${questao.alternativas.length} alternativas, e precisam ser ${LIMIARES.NUM_ALTERNATIVAS}`,
      };
    }

    const ids = [];
    for (const alternativa of questao.alternativas) {
      if (!alternativa || typeof alternativa !== "object") {
        return { motivo: "alternativa_malformada", detalhe: "alternativa não é um objeto" };
      }
      if (textoVazio(alternativa.id)) {
        return { motivo: "alternativa_malformada", detalhe: "alternativa sem id" };
      }
      if (textoVazio(alternativa.texto)) {
        return { motivo: "alternativa_vazia", detalhe: `alternativa "${alternativa.id}" sem texto` };
      }
      if (alternativa.texto.trim().length < LIMIARES.MIN_ALTERNATIVA) {
        return { motivo: "alternativa_vazia", detalhe: `alternativa "${alternativa.id}" curta demais` };
      }
      ids.push(String(alternativa.id).trim());
    }

    if (new Set(ids).size !== ids.length) {
      return { motivo: "ids_duplicados", detalhe: `ids repetidos: ${ids.join(", ")}` };
    }

    const textosNormalizados = questao.alternativas.map((a) => normalizar(a.texto));
    if (new Set(textosNormalizados).size !== textosNormalizados.length) {
      return { motivo: "alternativas_duplicadas", detalhe: "duas alternativas dizem a mesma coisa" };
    }

    if (ids.indexOf(String(questao.respostaCorreta).trim()) === -1) {
      return {
        motivo: "resposta_correta_inexistente",
        detalhe: `respostaCorreta "${questao.respostaCorreta}" não está entre os ids [${ids.join(", ")}]`,
      };
    }

    // ----- pedagógico -----
    if (questao.enunciado.trim().length < LIMIARES.MIN_ENUNCIADO) {
      return {
        motivo: "enunciado_curto",
        detalhe: `${questao.enunciado.trim().length} caracteres, mínimo ${LIMIARES.MIN_ENUNCIADO}`,
      };
    }
    if (questao.explicacao.trim().length < LIMIARES.MIN_EXPLICACAO) {
      return {
        motivo: "explicacao_trivial",
        detalhe: `${questao.explicacao.trim().length} caracteres, mínimo ${LIMIARES.MIN_EXPLICACAO}`,
      };
    }

    for (const alternativa of questao.alternativas) {
      for (const proibida of EXPRESSOES_PROIBIDAS) {
        if (proibida.test(alternativa.texto.trim())) {
          return {
            motivo: "expressao_proibida",
            detalhe: `alternativa "${alternativa.id}": ${alternativa.texto.trim().slice(0, 60)}`,
          };
        }
      }
    }

    for (const padrao of CITACAO_POR_LETRA) {
      const achado = questao.explicacao.match(padrao);
      if (achado) {
        return {
          motivo: "explicacao_cita_letra",
          detalhe: `a explicação cita a alternativa por letra ("${achado[0].trim()}"), e as alternativas são reordenadas antes de exibir`,
        };
      }
    }

    const indiceCorreta = ids.indexOf(String(questao.respostaCorreta).trim());
    const correta = questao.alternativas[indiceCorreta];
    const outras = questao.alternativas.filter((_, i) => i !== indiceCorreta);
    const mediaOutras = outras.reduce((s, a) => s + a.texto.trim().length, 0) / outras.length;
    const tamanhoCorreta = correta.texto.trim().length;

    if (
      tamanhoCorreta > mediaOutras * LIMIARES.FATOR_COMPRIMENTO &&
      tamanhoCorreta - mediaOutras > LIMIARES.DIFERENCA_MINIMA_CARACTERES
    ) {
      return {
        motivo: "vazamento_por_comprimento",
        detalhe: `a correta tem ${tamanhoCorreta} caracteres contra média ${Math.round(mediaOutras)} das outras`,
      };
    }

    // ----- anti-alucinação -----
    // Só o enunciado e a alternativa CORRETA são conferidos contra o material.
    // Distratores ficam de fora de propósito: um bom distrator é justamente uma
    // afirmação errada, que por definição pode não estar escrita no texto.
    const coberturaConceito = cobertura(questao.conceitoAvaliado, materialNormalizado);
    if (coberturaConceito < LIMIARES.COBERTURA_CONCEITO) {
      return {
        motivo: "conceito_fora_do_material",
        detalhe: `"${questao.conceitoAvaliado}" — só ${Math.round(coberturaConceito * 100)}% dos termos aparecem no conteúdo do tópico`,
      };
    }

    const coberturaEnunciado = cobertura(
      questao.enunciado + " " + correta.texto,
      materialNormalizado
    );
    if (coberturaEnunciado < LIMIARES.COBERTURA_ENUNCIADO) {
      return {
        motivo: "enunciado_fora_do_material",
        detalhe: `só ${Math.round(coberturaEnunciado * 100)}% dos termos do enunciado e da resposta correta aparecem no conteúdo`,
      };
    }

    return null;
  }

  /**
   * Valida um lote.
   *
   * @param {object} envelope  {questoes: [...]} vindo do ParserQuiz
   * @param {object} topico    entrada da BASE_CONHECIMENTO (para a checagem anti-alucinação)
   * @returns {{aprovadas: [], rejeicoes: [], recebidas: number, resumoTexto: string}}
   */
  function validarLote(envelope, topico) {
    const questoes = envelope && Array.isArray(envelope.questoes) ? envelope.questoes : [];
    const material = normalizar((topico && topico.conteudo) || "");

    const aprovadas = [];
    const rejeicoes = [];

    questoes.forEach(function (questao, indice) {
      const falha = validarQuestao(questao, material);
      if (falha) {
        rejeicoes.push({ indice, motivo: falha.motivo, detalhe: falha.detalhe });
        logIA(`questão ${indice} recusada [${falha.motivo}]: ${falha.detalhe}`);
      } else {
        aprovadas.push(questao);
      }
    });

    return {
      aprovadas,
      rejeicoes,
      recebidas: questoes.length,
      resumoTexto: rejeicoes.length
        ? rejeicoes.map((r) => `- questão ${r.indice + 1}: ${r.detalhe}`).join("\n")
        : "",
    };
  }

  /** Valida, registra nas métricas e devolve o resultado. Atalho usado pelo serviço. */
  function validarERegistrar(envelope, topico, modelo) {
    const resultado = validarLote(envelope, topico);
    MetricasIA.registrarValidacao(resultado, modelo);
    return resultado;
  }

  return {
    validarLote,
    validarERegistrar,
    validarQuestao,
    normalizar,
    cobertura,
    LIMIARES,
  };
})();
