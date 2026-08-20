/**
 * cliente-ollama.js — comunicação HTTP com o daemon local do Ollama.
 *
 * Responsabilidade única: falar com o daemon. Não sabe o que é uma questão, não monta
 * prompt e não valida nada. Devolve texto cru e mede o tempo.
 *
 * Nenhuma chave de API aparece aqui, nem em lugar nenhum do JavaScript: quem guarda a
 * credencial da conta e autentica com a nuvem é o daemon, em http://localhost:11434.
 *
 * Depende de: config-ia.js
 */

const ClienteOllama = (function () {
  /** Erro com causa classificada, para a interface poder dar mensagem decente. */
  function ErroOllama(tipo, mensagem, detalhe) {
    const erro = new Error(mensagem);
    erro.tipo = tipo; // "rede" | "timeout" | "assinatura" | "modelo" | "http" | "resposta"
    erro.detalhe = detalhe || null;
    return erro;
  }

  /**
   * Traduz a falha do daemon para um tipo tratável.
   * O caso "assinatura" é real e foi medido: modelos cloud fora do plano gratuito
   * respondem em ~150 ms com {"error":"this model requires a subscription..."}.
   */
  function classificarFalhaHttp(status, corpo) {
    if (/requires a subscription|upgrade for access/i.test(corpo)) {
      return ErroOllama(
        "assinatura",
        "O modelo configurado exige um plano pago do Ollama Cloud.",
        corpo
      );
    }
    if (status === 404) {
      return ErroOllama(
        "modelo",
        "O modelo configurado não está registrado no Ollama. Rode: ollama pull <modelo>",
        corpo
      );
    }
    return ErroOllama("http", `O Ollama respondeu ${status}.`, corpo);
  }

  /**
   * POST /api/chat com stream desligado.
   *
   * `stream: false` simplifica o parsing — a interface mostra estado de carregamento
   * em vez de texto aparecendo aos poucos.
   *
   * O parâmetro `format` só é enviado quando o provedor ativo declara `suportaSchema`.
   * Mandar schema para um modelo :cloud não dá erro: ele é silenciosamente ignorado,
   * o que é pior do que dar erro, porque esconde a limitação. Por isso a decisão fica
   * explícita na configuração e é devolvida no diagnóstico de cada chamada.
   */
  async function chamar(mensagens, opcoes) {
    const cfg = configAtiva();
    const configuracoes = opcoes || {};

    const corpo = {
      model: cfg.modelo,
      messages: mensagens,
      stream: false,
      options: {
        temperature: cfg.geracao.temperatura,
        top_p: cfg.geracao.topP,
        num_predict: cfg.geracao.numPredict,
      },
    };

    if (cfg.suportaSchema && configuracoes.schema) {
      corpo.format = configuracoes.schema;
    }

    const controlador = new AbortController();
    const temporizador = setTimeout(() => controlador.abort(), cfg.timeoutMs);
    const inicio = Date.now();

    try {
      logIA("POST", `${cfg.host}/api/chat`, "modelo:", cfg.modelo, "schema:", !!corpo.format);

      const resposta = await fetch(`${cfg.host}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controlador.signal,
        body: JSON.stringify(corpo),
      });

      if (!resposta.ok) {
        throw classificarFalhaHttp(resposta.status, await resposta.text());
      }

      const dados = await resposta.json();
      const conteudo = dados && dados.message && dados.message.content;
      if (typeof conteudo !== "string" || conteudo.trim() === "") {
        throw ErroOllama("resposta", "O modelo devolveu uma resposta vazia.", JSON.stringify(dados).slice(0, 300));
      }

      const latenciaMs = Date.now() - inicio;
      logIA(`resposta em ${latenciaMs} ms, ${conteudo.length} caracteres`);

      return {
        conteudo,
        latenciaMs,
        modelo: cfg.modelo,
        provedor: cfg.provedor,
        schemaEnviado: !!corpo.format,
      };
    } catch (erro) {
      if (erro.name === "AbortError") {
        throw ErroOllama("timeout", `O modelo não respondeu em ${cfg.timeoutMs / 1000} segundos.`);
      }
      if (erro.tipo) throw erro; // já classificado acima
      // TypeError de fetch = daemon fora do ar, porta fechada ou CORS bloqueado.
      throw ErroOllama(
        "rede",
        "Não foi possível falar com o Ollama. Ele está rodando? O site está sendo servido por HTTP?",
        erro.message
      );
    } finally {
      clearTimeout(temporizador);
    }
  }

  /**
   * GET /api/tags — o daemon está no ar e o modelo configurado está registrado?
   *
   * Nunca lança: devolve um objeto de status, porque a cascata de fallback precisa
   * seguir em frente quando o Ollama está desligado.
   */
  async function verificarDisponibilidade() {
    const cfg = configAtiva();
    const controlador = new AbortController();
    const temporizador = setTimeout(() => controlador.abort(), 5000);
    const inicio = Date.now();

    try {
      const resposta = await fetch(`${cfg.host}/api/tags`, { signal: controlador.signal });
      if (!resposta.ok) {
        return { online: false, modeloRegistrado: false, motivo: `daemon respondeu ${resposta.status}`, latenciaMs: Date.now() - inicio };
      }

      const dados = await resposta.json();
      const registrados = (dados.models || []).map((m) => m.name);
      const modeloRegistrado = registrados.indexOf(cfg.modelo) !== -1;

      return {
        online: true,
        modeloRegistrado,
        modelo: cfg.modelo,
        provedor: cfg.provedor,
        rotulo: cfg.rotulo,
        modelosDisponiveis: registrados,
        motivo: modeloRegistrado ? null : `o modelo "${cfg.modelo}" não está em ollama list`,
        latenciaMs: Date.now() - inicio,
      };
    } catch (erro) {
      return {
        online: false,
        modeloRegistrado: false,
        motivo: erro.name === "AbortError" ? "o daemon não respondeu em 5 s" : "daemon inacessível",
        detalhe: erro.message,
        latenciaMs: Date.now() - inicio,
      };
    } finally {
      clearTimeout(temporizador);
    }
  }

  return { chamar, verificarDisponibilidade };
})();
