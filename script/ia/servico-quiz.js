/**
 * servico-quiz.js — orquestrador. É a ÚNICA coisa que o site chama.
 *
 *     const quiz = await obterQuiz("animais", "filo-cordados", { quizFixo: quizData });
 *
 * Cascata de fallback, nesta ordem:
 *   1. IA    — se habilitada, o tópico está em topicosComIA, tem conteúdo suficiente e o Ollama responde
 *   2. Cache — questões validadas em tentativas anteriores, no LocalStorage
 *   3. Quiz fixo original do site — sempre presente, nunca apagado
 *
 * Devolve SEMPRE no formato de objeto que o site já usa, acrescido de `origem` e
 * `modelo`. O resto do site não precisa saber de onde o quiz veio.
 *
 * Depende de: config-ia.js, metricas-ia.js, cliente-ollama.js, prompt-quiz.js,
 *             parser-quiz.js, validador-quiz.js, cache-quiz.js
 * e, opcionalmente, da global BASE_CONHECIMENTO (dados/base-conhecimento.js).
 */

const ServicoQuiz = (function () {
  /** Busca o tópico na base de conhecimento. Devolve null se a base não estiver carregada. */
  function buscarTopico(moduloId, topicoId) {
    if (typeof BASE_CONHECIMENTO === "undefined") return null;
    const modulo = BASE_CONHECIMENTO[moduloId];
    if (!modulo || !modulo.topicos) return null;
    const topico = modulo.topicos[topicoId];
    if (!topico) return null;
    return { topico, tituloModulo: modulo.titulo };
  }

  /**
   * O tópico pode usar IA? Devolve o motivo da recusa, para o diagnóstico poder explicar
   * por que caiu no fallback em vez de só dizer que caiu.
   */
  function avaliarElegibilidade(moduloId, topicoId) {
    if (!CONFIG_IA.habilitada) {
      return { elegivel: false, motivo: "a camada de IA está desligada em CONFIG_IA.habilitada" };
    }
    if (CONFIG_IA.topicosComIA.indexOf(topicoId) === -1) {
      return { elegivel: false, motivo: `"${topicoId}" ainda não está em CONFIG_IA.topicosComIA` };
    }
    const achado = buscarTopico(moduloId, topicoId);
    if (!achado) {
      return { elegivel: false, motivo: `"${moduloId}/${topicoId}" não está na base de conhecimento` };
    }
    if (!achado.topico.maxQuestoes) {
      return {
        elegivel: false,
        motivo: `conteúdo insuficiente: ${achado.topico.metricas.caracteres} caracteres (${achado.topico.limitadoPor})`,
        topico: achado.topico,
      };
    }
    return { elegivel: true, motivo: null, topico: achado.topico, tituloModulo: achado.tituloModulo };
  }

  /** Embaralha in place, algoritmo de Fisher-Yates. */
  function embaralhar(lista) {
    for (let i = lista.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const t = lista[i];
      lista[i] = lista[j];
      lista[j] = t;
    }
    return lista;
  }

  /**
   * Converte do formato da IA para o formato do site (descoberto na Fase 0).
   *
   * DECISÃO IMPORTANTE: `title` é copiado do quiz fixo, não da base de conhecimento.
   * O motor deriva a chave de progresso do LocalStorage de `quizData[0].title`
   * (quiz-engine.js:89). Mudar esse texto criaria uma chave nova e o aluno perderia o
   * histórico do tópico. Ver docs/00-MAPEAMENTO.md §5.
   *
   * As alternativas são embaralhadas: modelos de linguagem tendem a colocar a resposta
   * certa sempre na mesma posição, e isso é aprendível pelo aluno em poucas tentativas.
   */
  function converterParaFormatoDoSite(questoesIA, titulo, extras) {
    return questoesIA.map(function (questao) {
      const alternativas = embaralhar(questao.alternativas.slice());
      return {
        // ----- campos que o motor do site lê -----
        title: titulo,
        type: "multiple",
        question: questao.enunciado,
        explanation: questao.explicacao,
        options: alternativas.map(function (alternativa) {
          return {
            text: alternativa.texto,
            correct: String(alternativa.id) === String(questao.respostaCorreta),
          };
        }),
        // ----- campos extras: o motor ignora o que não conhece -----
        origem: extras.origem,
        modelo: extras.modelo || null,
        conceitoAvaliado: questao.conceitoAvaliado || null,
      };
    });
  }

  /** Título a usar, preservando a chave de progresso já existente. */
  function tituloDoQuiz(quizFixo, topico) {
    if (Array.isArray(quizFixo) && quizFixo.length && quizFixo[0].title) {
      return quizFixo[0].title;
    }
    return (topico && topico.titulo) || "Quiz";
  }

  /**
   * Laço de geração: pede, faz o parse, valida, acumula as aprovadas e tenta de novo
   * pelas que faltam — reenviando ao modelo o motivo exato da recusa anterior.
   */
  async function gerarComIA(elegibilidade, alvo, aoMudarEstado) {
    const topico = elegibilidade.topico;
    const aprovadas = [];
    const diagnostico = {
      tentativas: [],
      totalRecebidas: 0,
      totalRejeitadas: 0,
      latenciaTotalMs: 0,
    };

    let motivoRejeicaoAnterior = null;

    for (let tentativa = 1; tentativa <= CONFIG_IA.maxTentativas; tentativa++) {
      const faltam = alvo - aprovadas.length;
      if (faltam <= 0) break;

      if (aoMudarEstado) {
        aoMudarEstado({ fase: "gerando", tentativa, de: CONFIG_IA.maxTentativas, faltam });
      }

      // Conceitos já cobrados (no cache e nesta rodada) saem do cardápio, para as
      // questões variarem entre tentativas em vez de repetir o mesmo assunto.
      const conceitosExcluir = CacheQuiz.conceitosGuardados(
        elegibilidade.moduloId,
        elegibilidade.topicoId,
        10
      ).concat(aprovadas.map((q) => q.conceitoAvaliado).filter(Boolean));

      const mensagens = PromptQuiz.montarMensagens({
        topico,
        tituloModulo: elegibilidade.tituloModulo,
        numQuestoes: faltam,
        conceitosExcluir,
        motivoRejeicao: motivoRejeicaoAnterior,
      });

      logIA(`tentativa ${tentativa}: pedindo ${faltam} questão(ões)`);

      let resposta;
      try {
        resposta = await ClienteOllama.chamar(mensagens, { schema: PromptQuiz.schema });
      } catch (erro) {
        MetricasIA.registrarFalhaDeChamada(erro.tipo);
        diagnostico.tentativas.push({
          tentativa,
          falha: erro.tipo,
          mensagem: erro.message,
        });
        // Rede, timeout ou assinatura não melhoram com nova tentativa: sai do laço.
        if (erro.tipo === "rede" || erro.tipo === "assinatura" || erro.tipo === "modelo") {
          diagnostico.erroFinal = erro;
          break;
        }
        continue;
      }

      diagnostico.latenciaTotalMs += resposta.latenciaMs;

      if (aoMudarEstado) aoMudarEstado({ fase: "validando", tentativa });

      const extraido = ParserQuiz.extrair(resposta.conteudo);
      MetricasIA.registrarGeracao({
        latenciaMs: resposta.latenciaMs,
        estrategiaParser: extraido.estrategia,
        modelo: resposta.modelo,
      });

      if (!extraido.ok) {
        diagnostico.tentativas.push({
          tentativa,
          latenciaMs: resposta.latenciaMs,
          estrategiaParser: extraido.estrategia,
          falha: "parser",
          mensagem: extraido.erro,
        });
        motivoRejeicaoAnterior =
          "Sua resposta anterior não era um JSON válido. Responda apenas com o objeto JSON, sem nenhum outro texto.";
        continue;
      }

      const validacao = ValidadorQuiz.validarERegistrar(extraido.dados, topico, resposta.modelo);
      diagnostico.totalRecebidas += validacao.recebidas;
      diagnostico.totalRejeitadas += validacao.rejeicoes.length;

      diagnostico.tentativas.push({
        tentativa,
        latenciaMs: resposta.latenciaMs,
        estrategiaParser: extraido.estrategia,
        observacaoParser: extraido.observacao || null,
        recebidas: validacao.recebidas,
        aprovadas: validacao.aprovadas.length,
        rejeicoes: validacao.rejeicoes,
      });

      for (const questao of validacao.aprovadas) {
        if (aprovadas.length < alvo) aprovadas.push(questao);
      }

      motivoRejeicaoAnterior = validacao.resumoTexto || null;

      // Nada foi recusado e ainda falta questão: o modelo simplesmente entregou menos do
      // que foi pedido. Insistir tende a produzir repetição, então aceita-se o que veio.
      if (!validacao.rejeicoes.length && validacao.recebidas < faltam) {
        logIA("o modelo entregou menos questões do que o pedido; encerrando as tentativas");
        break;
      }
    }

    return { aprovadas, diagnostico };
  }

  /**
   * Porta de entrada única.
   *
   * @param {string} moduloId    ex.: "animais"
   * @param {string} topicoId    ex.: "filo-cordados"
   * @param {object} opcoes
   *   quizFixo        array `quizData` da página — último nível do fallback (recomendado)
   *   numQuestoes     quantas pedir; o teto real continua sendo o `maxQuestoes` do tópico
   *   aoMudarEstado   callback(estado) para a interface mostrar o carregamento
   *   ignorarCache    true para não usar o cache como fallback (usado no diagnóstico)
   */
  async function obterQuiz(moduloId, topicoId, opcoes) {
    const configuracoes = opcoes || {};
    const quizFixo = Array.isArray(configuracoes.quizFixo) ? configuracoes.quizFixo : [];
    const inicio = Date.now();

    const elegibilidade = avaliarElegibilidade(moduloId, topicoId);
    elegibilidade.moduloId = moduloId;
    elegibilidade.topicoId = topicoId;

    const titulo = tituloDoQuiz(quizFixo, elegibilidade.topico);
    const diagnostico = {
      moduloId,
      topicoId,
      elegivel: elegibilidade.elegivel,
      motivoNaoElegivel: elegibilidade.motivo,
      cascata: [],
    };

    /**
     * Resume em uma frase curta por que o quiz não veio da IA. É o que a página de
     * diagnóstico agrupa em "motivos de fallback" — sem isso a métrica diria apenas
     * que caiu, e não de onde.
     */
    function motivoDoFallback() {
      if (!elegibilidade.elegivel) return `tópico não elegível: ${elegibilidade.motivo}`;
      const status = diagnostico.status;
      if (status && !status.online) return "Ollama fora do ar";
      if (status && !status.modeloRegistrado) return `modelo não registrado: ${status.motivo}`;
      const geracao = diagnostico.geracao;
      if (geracao && geracao.erroFinal) return `falha na chamada: ${geracao.erroFinal.tipo}`;
      if (geracao && geracao.totalRejeitadas) return "questões recusadas pelo validador";
      if (geracao) return "modelo não devolveu questão aproveitável";
      return "indeterminado";
    }

    function entregar(origem, questoes, extras) {
      diagnostico.totalMs = Date.now() - inicio;
      diagnostico.origem = origem;
      diagnostico.motivoFallback = origem === "ia" ? null : motivoDoFallback();
      MetricasIA.registrarOrigem(origem, diagnostico.motivoFallback);
      return Object.assign(
        {
          questoes,
          origem,
          modelo: (extras && extras.modelo) || null,
          provedor: CONFIG_IA.provedor,
          titulo,
          diagnostico,
        },
        extras || {}
      );
    }

    // ----- nível 1: IA -----
    if (elegibilidade.elegivel) {
      if (configuracoes.aoMudarEstado) configuracoes.aoMudarEstado({ fase: "verificando" });

      const status = await ClienteOllama.verificarDisponibilidade();
      diagnostico.status = status;

      if (status.online && status.modeloRegistrado) {
        const alvo = Math.min(
          configuracoes.numQuestoes || CONFIG_IA.numQuestoesPadrao,
          elegibilidade.topico.maxQuestoes
        );
        diagnostico.alvo = alvo;
        diagnostico.maxQuestoesDoTopico = elegibilidade.topico.maxQuestoes;

        const resultado = await gerarComIA(elegibilidade, alvo, configuracoes.aoMudarEstado);
        diagnostico.geracao = resultado.diagnostico;

        if (resultado.aprovadas.length) {
          CacheQuiz.guardar(moduloId, topicoId, resultado.aprovadas, status.modelo);
          diagnostico.cascata.push({ nivel: "ia", resultado: "ok", questoes: resultado.aprovadas.length });
          if (configuracoes.aoMudarEstado) configuracoes.aoMudarEstado({ fase: "pronto", origem: "ia" });

          return entregar(
            "ia",
            converterParaFormatoDoSite(resultado.aprovadas, titulo, {
              origem: "ia",
              modelo: status.modelo,
            }),
            { modelo: status.modelo }
          );
        }

        diagnostico.cascata.push({
          nivel: "ia",
          resultado: "sem questões aprovadas",
          detalhe: resultado.diagnostico.erroFinal ? resultado.diagnostico.erroFinal.message : null,
        });
      } else {
        diagnostico.cascata.push({ nivel: "ia", resultado: "indisponível", detalhe: status.motivo });
      }
    } else {
      diagnostico.cascata.push({ nivel: "ia", resultado: "não elegível", detalhe: elegibilidade.motivo });
    }

    // ----- nível 2: cache -----
    if (!configuracoes.ignorarCache && CONFIG_IA.cacheHabilitado) {
      const alvo = Math.min(
        configuracoes.numQuestoes || CONFIG_IA.numQuestoesPadrao,
        (elegibilidade.topico && elegibilidade.topico.maxQuestoes) || CONFIG_IA.numQuestoesPadrao
      );
      const doCache = CacheQuiz.obter(moduloId, topicoId, alvo);
      if (doCache.length) {
        diagnostico.cascata.push({ nivel: "cache", resultado: "ok", questoes: doCache.length });
        if (configuracoes.aoMudarEstado) configuracoes.aoMudarEstado({ fase: "pronto", origem: "cache" });

        return entregar(
          "cache",
          converterParaFormatoDoSite(doCache, titulo, { origem: "cache", modelo: null })
        );
      }
      diagnostico.cascata.push({ nivel: "cache", resultado: "vazio" });
    }

    // ----- nível 3: quiz fixo -----
    diagnostico.cascata.push({ nivel: "fixo", resultado: "ok", questoes: quizFixo.length });
    if (configuracoes.aoMudarEstado) configuracoes.aoMudarEstado({ fase: "pronto", origem: "fixo" });

    // O quiz fixo é devolvido como está, com `origem` acrescentada. Não é convertido nem
    // embaralhado: é o material original do site e precisa continuar idêntico.
    return entregar(
      "fixo",
      quizFixo.map(function (questao) {
        return Object.assign({}, questao, { origem: "fixo" });
      })
    );
  }

  return {
    obterQuiz,
    avaliarElegibilidade,
    converterParaFormatoDoSite,
    buscarTopico,
  };
})();

/** Atalho global exigido pelo roteiro (§6.7). É a única porta de entrada do site. */
async function obterQuiz(moduloId, topicoId, opcoes) {
  return ServicoQuiz.obterQuiz(moduloId, topicoId, opcoes);
}
