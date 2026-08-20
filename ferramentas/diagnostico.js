/**
 * diagnostico.js — comportamento da página de diagnóstico da camada de IA.
 *
 * Página independente, fora do fluxo do site. Nenhuma página do site aponta para cá, e
 * nada daqui é carregado pelas páginas de tópico.
 *
 * O gerador manual chama as camadas UMA A UMA — prompt, cliente, parser, validador —
 * em vez de usar `obterQuiz()`. É de propósito: `obterQuiz()` devolve o quiz pronto e
 * esconde o caminho, e o que esta página precisa mostrar é justamente o caminho.
 *
 * Depende de: toda a camada script/ia/ e de dados/base-conhecimento.js.
 */

(function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // Utilitários de tela
  // ---------------------------------------------------------------------------
  function elemento(id) {
    return document.getElementById(id);
  }

  function texto(id, valor) {
    const alvo = elemento(id);
    if (alvo) alvo.textContent = valor;
  }

  /** Selo colorido. `estado` vira a classe: ok, aviso, ruim ou nenhuma. */
  function selo(id, rotulo, estado) {
    const alvo = elemento(id);
    if (!alvo) return;
    alvo.textContent = "";
    const marca = document.createElement("span");
    marca.className = "selo" + (estado ? " " + estado : "");
    marca.textContent = rotulo;
    alvo.appendChild(marca);
  }

  function ms(valor) {
    if (valor === null || valor === undefined || valor === "") return "—";
    if (valor < 1000) return `${Math.round(valor)} ms`;
    return `${(valor / 1000).toFixed(1)} s`;
  }

  function porcento(fracao) {
    if (fracao === null || fracao === undefined) return "—";
    return `${(fracao * 100).toFixed(1)}%`;
  }

  /**
   * Lista de "rótulo — contagem" ordenada da maior para a menor, com barra proporcional.
   * Sempre por textContent: o texto pode vir do modelo, e não pode virar HTML.
   */
  function listaContada(id, mapa, vazio) {
    const alvo = elemento(id);
    if (!alvo) return;
    alvo.textContent = "";
    const entradas = Object.keys(mapa || {})
      .map((chave) => [chave, mapa[chave]])
      .filter((par) => par[1])
      .sort((a, b) => b[1] - a[1]);

    if (!entradas.length) {
      alvo.className = "vazio";
      alvo.textContent = vazio;
      return;
    }
    alvo.className = "";
    const maior = entradas[0][1];
    for (const [chave, contagem] of entradas) {
      const linha = document.createElement("div");
      linha.className = "linha";
      const rotulo = document.createElement("dt");
      rotulo.textContent = chave;
      const valor = document.createElement("dd");
      valor.textContent = String(contagem);
      linha.appendChild(rotulo);
      linha.appendChild(valor);
      alvo.appendChild(linha);

      const barra = document.createElement("div");
      barra.className = "barra";
      barra.style.height = "4px";
      barra.style.marginBottom = "4px";
      const fatia = document.createElement("span");
      fatia.className = "fatia-taxa";
      fatia.style.width = `${Math.round((contagem / maior) * 100)}%`;
      barra.appendChild(fatia);
      alvo.appendChild(barra);
    }
  }

  // ---------------------------------------------------------------------------
  // Painel: configuração
  // ---------------------------------------------------------------------------
  function pintarConfiguracao() {
    const cfg = configAtiva();

    texto("cfg-provedor", `${cfg.provedor} — ${cfg.rotulo}`);
    texto("cfg-modelo", cfg.modelo);
    texto("cfg-host", cfg.host);
    texto("cfg-timeout", ms(cfg.timeoutMs));
    texto("cfg-geracao", `${cfg.geracao.temperatura} / ${cfg.geracao.topP}`);
    texto("cfg-tokens", String(cfg.geracao.numPredict));
    texto("cfg-tentativas", String(CONFIG_IA.maxTentativas));

    selo("cfg-habilitada", CONFIG_IA.habilitada ? "ligada" : "desligada",
      CONFIG_IA.habilitada ? "ok" : "ruim");
    selo("cfg-cache", CONFIG_IA.cacheHabilitado ? "ligado" : "desligado",
      CONFIG_IA.cacheHabilitado ? "ok" : "aviso");

    // O ponto que o roteiro pede para deixar explícito: na nuvem o schema não é
    // respeitado, e a página tem que dizer isso, não escondê-lo.
    selo("cfg-schema", cfg.suportaSchema ? "enviado e respeitado" : "não respeitado — compensado no prompt",
      cfg.suportaSchema ? "ok" : "aviso");

    texto(
      "cfg-observacao",
      cfg.suportaSchema
        ? "O parâmetro format é enviado com o JSON Schema e aplicado pelo runner local, que é o mecanismo correto de saída estruturada."
        : "Medido: modelos :cloud ignoram o parâmetro format. O formato é sustentado por instrução no prompt, parser tolerante e validação — nesta ordem. Trocar CONFIG_IA.provedor para \"local\" religa o schema automaticamente."
    );
  }

  // ---------------------------------------------------------------------------
  // Painel: origem dos quizzes
  // ---------------------------------------------------------------------------
  function pintarOrigens(resumo) {
    const origens = resumo.origens || { ia: 0, cache: 0, fixo: 0 };
    const total = origens.ia + origens.cache + origens.fixo;

    texto("origem-ia", String(origens.ia));
    texto("origem-cache", String(origens.cache));
    texto("origem-fixo", String(origens.fixo));
    texto("origem-total", `${total} ${total === 1 ? "quiz servido" : "quizzes servidos"}`);

    // Cartão sem nenhuma ocorrência fica apagado: o painel precisa dizer de longe
    // qual nível da cascata está atendendo.
    for (const nome of ["ia", "cache", "fixo"]) {
      const cartao = elemento(`origem-cartao-${nome}`);
      if (cartao) {
        cartao.className = `origem ${nome}` + (origens[nome] ? "" : " apagada");
      }
    }

    const barra = elemento("origem-barra");
    if (barra) {
      barra.textContent = "";
      if (total) {
        for (const nome of ["ia", "cache", "fixo"]) {
          if (!origens[nome]) continue;
          const fatia = document.createElement("span");
          fatia.className = `fatia-${nome}`;
          fatia.style.width = `${(origens[nome] / total) * 100}%`;
          fatia.title = `${nome}: ${origens[nome]}`;
          barra.appendChild(fatia);
        }
      }
    }

    listaContada("motivos-fallback", resumo.motivosDeFallback, "Nenhum fallback registrado.");
  }

  // ---------------------------------------------------------------------------
  // Painel: métricas de geração e latência
  // ---------------------------------------------------------------------------
  function pintarMetricas() {
    const resumo = MetricasIA.resumo();

    texto("met-chamadas", String(resumo.geracoes));
    texto("met-erros", String(resumo.falhasDeChamada));
    texto("met-recebidas", String(resumo.questoesRecebidas));
    texto("met-aprovadas", String(resumo.questoesAprovadas));
    texto("met-rejeitadas", String(resumo.questoesRecebidas - resumo.questoesAprovadas));
    texto("met-taxa", porcento(resumo.taxaAprovacao));

    const barraTaxa = elemento("met-taxa-barra");
    if (barraTaxa) barraTaxa.style.width = `${(resumo.taxaAprovacao || 0) * 100}%`;

    listaContada("met-rejeicoes", resumo.rejeicoesPorMotivo, "Nenhuma rejeição registrada.");
    listaContada("met-erros-tipo", resumo.falhasPorTipo, "Nenhum erro registrado.");
    listaContada("met-parser", resumo.estrategiasDoParser, "Nenhuma extração registrada.");

    const porModelo = {};
    for (const nome of Object.keys(resumo.porModelo || {})) {
      porModelo[`${nome} (aprovadas: ${resumo.porModelo[nome].aprovadas})`] = resumo.porModelo[nome].geracoes;
    }
    listaContada("met-por-modelo", porModelo, "Nenhum modelo registrado.");

    texto("lat-amostras", String(resumo.latencia.amostras));
    texto("lat-media", ms(resumo.latencia.mediaMs));
    texto("lat-mediana", ms(resumo.latencia.medianaMs));
    texto("lat-p95", ms(resumo.latencia.p95Ms));
    texto("lat-min", ms(resumo.latencia.minMs));
    texto("lat-max", ms(resumo.latencia.maxMs));

    pintarOrigens(resumo);
  }

  // ---------------------------------------------------------------------------
  // Painel: cache
  // ---------------------------------------------------------------------------
  function pintarCache() {
    const estatisticas = CacheQuiz.estatisticas();
    texto("cache-total", String(estatisticas.total));
    texto(
      "cache-bytes",
      `${(estatisticas.bytes / 1024).toFixed(1)} KB de ${Math.round(estatisticas.limiteBytes / 1024)} KB`
    );

    const porTopico = {};
    for (const chave of Object.keys(estatisticas.topicos)) {
      porTopico[chave] = estatisticas.topicos[chave].questoes;
    }
    listaContada("cache-topicos", porTopico, "Cache vazio.");
  }

  // ---------------------------------------------------------------------------
  // Painel: tópicos
  // ---------------------------------------------------------------------------
  function pintarTopicos() {
    const corpo = elemento("tabela-topicos");
    if (!corpo) return;
    corpo.textContent = "";

    let comConteudo = 0;
    let total = 0;

    for (const moduloId of Object.keys(BASE_CONHECIMENTO)) {
      const modulo = BASE_CONHECIMENTO[moduloId];
      for (const topicoId of Object.keys(modulo.topicos)) {
        const topico = modulo.topicos[topicoId];
        const habilitado = CONFIG_IA.topicosComIA.indexOf(topicoId) !== -1;
        total++;
        if (topico.maxQuestoes > 0) comConteudo++;

        const linha = document.createElement("tr");
        linha.className = habilitado ? "habilitado" : topico.maxQuestoes ? "" : "sem-ia";

        const celulas = [
          modulo.titulo,
          topico.titulo,
          String(topico.metricas.caracteres),
          `${topico.metricas.secoesComTexto}/${topico.metricas.secoes}`,
          String(topico.metricas.conceitos),
          String(topico.maxQuestoes),
          topico.suficiencia,
          topico.limitadoPor,
          habilitado ? "✨ habilitado" : topico.maxQuestoes ? "— aguardando" : "📘 quiz fixo",
        ];

        celulas.forEach(function (valor, indice) {
          const celula = document.createElement("td");
          if (indice >= 2 && indice <= 5) celula.className = "numero";
          celula.textContent = valor;
          linha.appendChild(celula);
        });
        corpo.appendChild(linha);
      }
    }

    texto(
      "topicos-resumo",
      `${total} tópicos na base · ${comConteudo} com conteúdo suficiente para gerar · ` +
        `${CONFIG_IA.topicosComIA.length} habilitado(s) no site: ${CONFIG_IA.topicosComIA.join(", ")}`
    );
  }

  // ---------------------------------------------------------------------------
  // Teste de conexão
  // ---------------------------------------------------------------------------
  async function testarConexao() {
    const botao = elemento("btn-testar");
    if (botao) botao.disabled = true;
    selo("con-status", "verificando…", "aviso");
    texto("con-detalhe", "");

    const status = await ClienteOllama.verificarDisponibilidade();

    selo("con-status", status.online ? "online" : "offline", status.online ? "ok" : "ruim");
    selo(
      "con-modelo",
      status.modeloRegistrado ? "registrado" : "não encontrado",
      status.modeloRegistrado ? "ok" : "ruim"
    );
    texto("con-latencia", ms(status.latenciaMs));

    const lista = elemento("con-modelos");
    if (lista) {
      lista.textContent = "";
      if (status.modelosDisponiveis && status.modelosDisponiveis.length) {
        lista.className = "";
        for (const nome of status.modelosDisponiveis) {
          const linha = document.createElement("div");
          linha.className = "linha";
          const rotulo = document.createElement("dt");
          rotulo.textContent = nome;
          const marca = document.createElement("dd");
          marca.textContent = nome === configAtiva().modelo ? "◀ em uso" : "";
          linha.appendChild(rotulo);
          linha.appendChild(marca);
          lista.appendChild(linha);
        }
      } else {
        lista.className = "vazio";
        lista.textContent = "Nenhum modelo listado.";
      }
    }

    // Latência de uma geração de verdade: `/api/tags` responde em milissegundos e não
    // diz nada sobre quanto o modelo demora para pensar.
    if (status.online && status.modeloRegistrado) {
      try {
        const resposta = await ClienteOllama.chamar(
          [{ role: "user", content: "Responda apenas: ok" }],
          {}
        );
        texto("con-latencia-chat", ms(resposta.latenciaMs));
        texto("con-detalhe", `Resposta do modelo: “${resposta.conteudo.trim().slice(0, 80)}”`);
      } catch (erro) {
        texto("con-latencia-chat", "falhou");
        texto("con-detalhe", `${erro.tipo || "erro"}: ${erro.message}`);
      }
    } else {
      texto("con-latencia-chat", "—");
      texto("con-detalhe", status.motivo || "");
    }

    if (botao) botao.disabled = false;
  }

  // ---------------------------------------------------------------------------
  // Gerador manual
  // ---------------------------------------------------------------------------
  function preencherSeletores() {
    const selModulo = elemento("sel-modulo");
    const selTopico = elemento("sel-topico");
    if (!selModulo || !selTopico) return;

    selModulo.textContent = "";
    for (const moduloId of Object.keys(BASE_CONHECIMENTO)) {
      const opcao = document.createElement("option");
      opcao.value = moduloId;
      opcao.textContent = BASE_CONHECIMENTO[moduloId].titulo;
      selModulo.appendChild(opcao);
    }
    selModulo.addEventListener("change", preencherTopicos);
    preencherTopicos();
  }

  function preencherTopicos() {
    const selModulo = elemento("sel-modulo");
    const selTopico = elemento("sel-topico");
    if (!selModulo || !selTopico) return;

    const modulo = BASE_CONHECIMENTO[selModulo.value];
    selTopico.textContent = "";
    for (const topicoId of Object.keys(modulo.topicos)) {
      const topico = modulo.topicos[topicoId];
      const opcao = document.createElement("option");
      opcao.value = topicoId;
      opcao.textContent =
        `${topico.titulo} (${topico.metricas.caracteres} car., máx. ${topico.maxQuestoes})` +
        (topico.maxQuestoes ? "" : " — sem conteúdo suficiente");
      opcao.disabled = topico.maxQuestoes === 0;
      selTopico.appendChild(opcao);
    }
    ajustarTetoDeQuestoes();
    selTopico.addEventListener("change", ajustarTetoDeQuestoes);
  }

  function ajustarTetoDeQuestoes() {
    const campo = elemento("inp-questoes");
    const topico = topicoSelecionado();
    if (!campo || !topico) return;
    campo.max = String(topico.maxQuestoes || 1);
    if (Number(campo.value) > topico.maxQuestoes) campo.value = String(topico.maxQuestoes);
  }

  function topicoSelecionado() {
    const selModulo = elemento("sel-modulo");
    const selTopico = elemento("sel-topico");
    if (!selModulo || !selTopico || !selTopico.value) return null;
    const modulo = BASE_CONHECIMENTO[selModulo.value];
    return modulo ? modulo.topicos[selTopico.value] : null;
  }

  async function gerarManual() {
    const botao = elemento("btn-gerar");
    const selModulo = elemento("sel-modulo");
    const selTopico = elemento("sel-topico");
    const topico = topicoSelecionado();
    if (!topico) return;

    const quantas = Math.max(1, Math.min(Number(elemento("inp-questoes").value) || 1, topico.maxQuestoes));

    if (botao) botao.disabled = true;
    selo("ger-status", "montando o prompt…", "aviso");
    texto("col-cru", "—");
    const colunaValidacao = elemento("col-validacao");
    if (colunaValidacao) {
      colunaValidacao.className = "vazio";
      colunaValidacao.textContent = "—";
    }

    // 1. Prompt ------------------------------------------------------------
    const mensagens = PromptQuiz.montarMensagens({
      topico,
      tituloModulo: BASE_CONHECIMENTO[selModulo.value].titulo,
      numQuestoes: quantas,
      conceitosExcluir: CacheQuiz.conceitosGuardados(selModulo.value, selTopico.value, 10),
    });
    texto(
      "col-prompt",
      mensagens.map((m) => `### ${m.role}\n${m.content}`).join("\n\n")
    );

    // 2. Chamada -----------------------------------------------------------
    selo("ger-status", "chamando o modelo…", "aviso");
    let resposta;
    try {
      resposta = await ClienteOllama.chamar(mensagens, { schema: PromptQuiz.schema });
    } catch (erro) {
      MetricasIA.registrarFalhaDeChamada(erro.tipo);
      selo("ger-status", `falhou: ${erro.tipo || "erro"}`, "ruim");
      texto("col-cru", `${erro.message}\n\n${erro.detalhe || ""}`);
      if (botao) botao.disabled = false;
      pintarMetricas();
      return;
    }
    texto("col-cru", resposta.conteudo);

    // 3. Parser e validação ------------------------------------------------
    const extraido = ParserQuiz.extrair(resposta.conteudo);
    MetricasIA.registrarGeracao({
      latenciaMs: resposta.latenciaMs,
      estrategiaParser: extraido.estrategia,
      modelo: resposta.modelo,
    });

    const validacao = extraido.ok
      ? ValidadorQuiz.validarERegistrar(extraido.dados, topico, resposta.modelo)
      : { aprovadas: [], rejeicoes: [], recebidas: 0 };

    pintarValidacao(resposta, extraido, validacao);
    pintarQuestoes(validacao.aprovadas);

    if (elemento("chk-cache").checked && validacao.aprovadas.length) {
      CacheQuiz.guardar(selModulo.value, selTopico.value, validacao.aprovadas, resposta.modelo);
    }

    selo(
      "ger-status",
      `${validacao.aprovadas.length} de ${validacao.recebidas} aprovadas em ${ms(resposta.latenciaMs)}`,
      validacao.aprovadas.length ? "ok" : "ruim"
    );

    if (botao) botao.disabled = false;
    pintarMetricas();
    pintarCache();
  }

  function pintarValidacao(resposta, extraido, validacao) {
    const alvo = elemento("col-validacao");
    if (!alvo) return;
    alvo.className = "";
    alvo.textContent = "";

    function linha(rotulo, valor) {
      const div = document.createElement("div");
      div.className = "linha";
      const dt = document.createElement("dt");
      dt.textContent = rotulo;
      const dd = document.createElement("dd");
      dd.textContent = valor;
      div.appendChild(dt);
      div.appendChild(dd);
      alvo.appendChild(div);
    }

    linha("Latência", ms(resposta.latenciaMs));
    linha("Schema enviado", resposta.schemaEnviado ? "sim" : "não");
    linha("Estratégia do parser", extraido.estrategia);
    if (extraido.observacao) linha("Observação", extraido.observacao);
    if (!extraido.ok) {
      linha("Erro do parser", extraido.erro || "");
      return;
    }
    linha("Questões recebidas", String(validacao.recebidas));
    linha("Aprovadas", String(validacao.aprovadas.length));
    linha("Recusadas", String(validacao.rejeicoes.length));

    if (validacao.rejeicoes.length) {
      const titulo = document.createElement("h3");
      titulo.style.marginTop = "12px";
      titulo.textContent = "Recusas";
      alvo.appendChild(titulo);

      for (const rejeicao of validacao.rejeicoes) {
        const bloco = document.createElement("div");
        bloco.className = "recusa";
        const motivo = document.createElement("code");
        motivo.textContent = rejeicao.motivo;
        bloco.appendChild(document.createTextNode(`Questão ${rejeicao.indice + 1} — `));
        bloco.appendChild(motivo);
        bloco.appendChild(document.createTextNode(`: ${rejeicao.detalhe}`));
        alvo.appendChild(bloco);
      }
    }
  }

  function pintarQuestoes(questoes) {
    const alvo = elemento("ger-questoes");
    if (!alvo) return;
    alvo.textContent = "";

    if (!questoes.length) {
      alvo.className = "vazio";
      alvo.textContent = "Nenhuma questão foi aprovada nesta geração.";
      return;
    }
    alvo.className = "";

    for (const questao of questoes) {
      const cartao = document.createElement("div");
      cartao.className = "questao";

      const enunciado = document.createElement("div");
      enunciado.className = "enunciado";
      enunciado.textContent = questao.enunciado;
      cartao.appendChild(enunciado);

      const lista = document.createElement("ol");
      lista.type = "A";
      for (const alternativa of questao.alternativas) {
        const item = document.createElement("li");
        const correta = String(alternativa.id) === String(questao.respostaCorreta);
        if (correta) item.className = "correta";
        item.textContent = alternativa.texto + (correta ? "  ✓" : "");
        lista.appendChild(item);
      }
      cartao.appendChild(lista);

      const explicacao = document.createElement("div");
      explicacao.className = "explicacao";
      explicacao.textContent = questao.explicacao;
      cartao.appendChild(explicacao);

      const conceito = document.createElement("div");
      conceito.className = "conceito";
      conceito.textContent = `Conceito avaliado: ${questao.conceitoAvaliado}`;
      cartao.appendChild(conceito);

      alvo.appendChild(cartao);
    }
  }

  // ---------------------------------------------------------------------------
  // Botões de limpeza
  // ---------------------------------------------------------------------------
  function limparCache() {
    CacheQuiz.limpar();
    pintarCache();
    texto("cache-aviso", "Cache apagado. O progresso do aluno (quizProgress) não foi tocado.");
  }

  function limparMetricas() {
    MetricasIA.limpar();
    pintarMetricas();
    texto("cache-aviso", "Métricas zeradas. O progresso do aluno (quizProgress) não foi tocado.");
  }

  // ---------------------------------------------------------------------------
  function atualizarTudo() {
    pintarConfiguracao();
    pintarMetricas();
    pintarCache();
    pintarTopicos();
  }

  function ligar(id, funcao) {
    const alvo = elemento(id);
    if (alvo) alvo.addEventListener("click", funcao);
  }

  ligar("btn-atualizar", atualizarTudo);
  ligar("btn-testar", testarConexao);
  ligar("btn-gerar", gerarManual);
  ligar("btn-limpar-cache", limparCache);
  ligar("btn-limpar-metricas", limparMetricas);

  preencherSeletores();
  atualizarTudo();

  // Exposto para os testes automatizados poderem acionar a página sem clique de mouse.
  window.Diagnostico = {
    atualizarTudo,
    testarConexao,
    gerarManual,
    limparCache,
    limparMetricas,
    pintarMetricas,
    pintarTopicos,
  };
})();
