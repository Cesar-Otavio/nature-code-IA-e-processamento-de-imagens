/**
 * parser-quiz.js — extração tolerante do JSON devolvido pelo modelo.
 *
 * Este arquivo não estava no roteiro original. Ele existe por causa de uma limitação
 * medida: os modelos :cloud gratuitos ignoram o parâmetro `format` com JSON Schema e
 * devolvem Markdown em prosa. Ver docs/03-CAMADA-IA.md §5.
 *
 * Tolerante na extração, rigoroso depois: aqui só se tenta ACHAR o JSON. Julgar se o
 * conteúdo presta é trabalho do validador-quiz.js, que roda em seguida e não perdoa nada.
 *
 * Quatro estratégias, da mais limpa para a mais defensiva. A que funcionou é devolvida
 * em `estrategia` e vira métrica: saber quantas respostas precisaram de reparo é um
 * número interessante para o relatório.
 *
 * Depende de: config-ia.js
 */

const ParserQuiz = (function () {
  /**
   * Percorre o texto a partir de `inicio` sabendo diferenciar chave de abertura dentro
   * e fora de string. Devolve o índice do fechamento correspondente, ou -1.
   */
  function acharFechamento(texto, inicio) {
    let profundidade = 0;
    let dentroDeString = false;
    let escapado = false;

    for (let i = inicio; i < texto.length; i++) {
      const c = texto[i];
      if (escapado) {
        escapado = false;
        continue;
      }
      if (c === "\\") {
        if (dentroDeString) escapado = true;
        continue;
      }
      if (c === '"') {
        dentroDeString = !dentroDeString;
        continue;
      }
      if (dentroDeString) continue;

      if (c === "{" || c === "[") profundidade++;
      else if (c === "}" || c === "]") {
        profundidade--;
        if (profundidade === 0) return i;
      }
    }
    return -1;
  }

  /**
   * Recolhe os objetos `{...}` COMPLETOS de dentro de um array, ignorando um último
   * objeto que tenha ficado pela metade.
   *
   * É o tratamento de JSON truncado: em vez de tentar remendar o texto cortado — o que
   * produz objeto meia-boca que passa no parse e falha na tela —, descarta-se a questão
   * incompleta e aproveitam-se as inteiras.
   */
  function recolherObjetosCompletos(texto, inicioDoArray) {
    const objetos = [];
    let profundidade = 0;
    let comeco = -1;
    let dentroDeString = false;
    let escapado = false;

    for (let i = inicioDoArray + 1; i < texto.length; i++) {
      const c = texto[i];
      if (escapado) {
        escapado = false;
        continue;
      }
      if (c === "\\") {
        if (dentroDeString) escapado = true;
        continue;
      }
      if (c === '"') {
        dentroDeString = !dentroDeString;
        continue;
      }
      if (dentroDeString) continue;

      if (c === "{") {
        if (profundidade === 0) comeco = i;
        profundidade++;
      } else if (c === "}") {
        profundidade--;
        if (profundidade === 0 && comeco !== -1) {
          objetos.push(texto.slice(comeco, i + 1));
          comeco = -1;
        }
      } else if (c === "]" && profundidade === 0) {
        break;
      }
    }
    return objetos;
  }

  /**
   * Aceita as formas que os modelos costumam inventar e devolve sempre `{questoes: []}`:
   *   {"questoes":[...]}   o formato pedido
   *   [...]                array solto
   *   {"perguntas":[...]}  outro nome de chave
   *   {...}                uma questão única, fora de array
   */
  function normalizarEnvelope(objeto) {
    if (Array.isArray(objeto)) return { questoes: objeto };
    if (!objeto || typeof objeto !== "object") return null;

    if (Array.isArray(objeto.questoes)) return { questoes: objeto.questoes };

    for (const chave of Object.keys(objeto)) {
      const valor = objeto[chave];
      if (Array.isArray(valor) && valor.length && typeof valor[0] === "object") {
        return { questoes: valor };
      }
    }

    // Uma questão solta, sem envelope.
    if (objeto.enunciado || objeto.alternativas) return { questoes: [objeto] };

    return null;
  }

  /** Remove cercas de bloco de código e rótulos como "json" antes do objeto. */
  function tirarCercas(texto) {
    return texto
      .replace(/^[\s\S]*?```(?:json)?\s*/i, (trecho) => (trecho.indexOf("```") === -1 ? trecho : ""))
      .replace(/```[\s\S]*$/, "")
      .trim();
  }

  /**
   * Tenta extrair o JSON de uma resposta crua.
   * @returns {{ok: boolean, dados: object|null, estrategia: string, erro: string|null}}
   */
  function extrair(respostaCrua) {
    if (typeof respostaCrua !== "string" || respostaCrua.trim() === "") {
      return { ok: false, dados: null, estrategia: "nenhuma", erro: "resposta vazia" };
    }

    const texto = respostaCrua.trim();
    const tentativas = [];

    // 1. Direto: o modelo obedeceu.
    try {
      const envelope = normalizarEnvelope(JSON.parse(texto));
      if (envelope) return { ok: true, dados: envelope, estrategia: "direto", erro: null };
    } catch (e) {
      tentativas.push("direto: " + e.message);
    }

    // 2. Cercas: veio embrulhado em ```json ... ```
    const semCercas = tirarCercas(texto);
    if (semCercas && semCercas !== texto) {
      try {
        const envelope = normalizarEnvelope(JSON.parse(semCercas));
        if (envelope) return { ok: true, dados: envelope, estrategia: "cerca", erro: null };
      } catch (e) {
        tentativas.push("cerca: " + e.message);
      }
    }

    // 3. Recorte: o JSON está inteiro, mas cercado de prosa.
    const base = semCercas || texto;
    const primeiraChave = base.search(/[{[]/);
    if (primeiraChave !== -1) {
      const fechamento = acharFechamento(base, primeiraChave);
      if (fechamento !== -1) {
        try {
          const envelope = normalizarEnvelope(JSON.parse(base.slice(primeiraChave, fechamento + 1)));
          if (envelope) return { ok: true, dados: envelope, estrategia: "recorte", erro: null };
        } catch (e) {
          tentativas.push("recorte: " + e.message);
        }
      }
    }

    // 4. Reparo: a resposta foi cortada. Aproveita as questões inteiras.
    const inicioArray = base.indexOf("[");
    if (inicioArray !== -1) {
      const brutos = recolherObjetosCompletos(base, inicioArray);
      const questoes = [];
      for (const bruto of brutos) {
        try {
          questoes.push(JSON.parse(bruto));
        } catch (e) {
          /* objeto quebrado no meio: descartado de propósito */
        }
      }
      if (questoes.length) {
        return {
          ok: true,
          dados: { questoes },
          estrategia: "reparo",
          erro: null,
          observacao: `resposta truncada: ${questoes.length} ${questoes.length === 1 ? "questão aproveitada" : "questões aproveitadas"} de ${brutos.length} ${brutos.length === 1 ? "bloco" : "blocos"}`,
        };
      }
      tentativas.push("reparo: nenhum objeto completo dentro do array");
    }

    logIA("parser falhou. Resposta crua:", texto.slice(0, 400));
    return {
      ok: false,
      dados: null,
      estrategia: "nenhuma",
      erro: "não encontrei JSON aproveitável na resposta (" + tentativas.join(" | ") + ")",
    };
  }

  return { extrair, acharFechamento, recolherObjetosCompletos, normalizarEnvelope };
})();
