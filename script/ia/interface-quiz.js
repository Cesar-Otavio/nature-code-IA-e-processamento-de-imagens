/**
 * interface-quiz.js — ponte entre a camada de IA e o motor de quiz do site.
 *
 * Existe para que `quiz-engine.js` mude o mínimo possível. Todo o DOM novo (estado de
 * carregamento, selo de origem, botão de gerar novas perguntas, mensagem de fallback) e
 * todo o CSS novo nascem aqui, em tempo de execução. Nenhum HTML do site ganha elemento
 * novo, e nenhum arquivo CSS do site é tocado.
 *
 * A única alteração em `quiz-engine.js` é a chamada de partida no fim do arquivo.
 *
 * Depende de: config-ia.js … servico-quiz.js (toda a camada), e das funções globais do
 * motor: loadSavedAnswers(), renderQuestion(), e das variáveis currentQuestion,
 * userAnswers, quizSubmitted e quizData.
 */

const InterfaceQuizIA = (function () {
  const CHAVE_SESSAO = "quiz_ia_sessao";

  let origemAtual = null;
  let elegivelParaIA = false;
  let alvoAtual = null;
  let quizFixoOriginal = [];

  // ---------------------------------------------------------------------------
  // CSS injetado
  // ---------------------------------------------------------------------------
  // Cores copiadas do que o quiz já usa em css/topicsConteude.css (#00ff88 de destaque,
  // #b0b0b0 de texto secundário), para o acréscimo não destoar do visual existente.
  const ESTILO = `
    .ia-barra {
      display: flex; align-items: center; justify-content: space-between;
      gap: 10px; flex-wrap: wrap; margin: -10px 0 18px 0;
    }
    .ia-selo {
      display: inline-flex; align-items: center; gap: 6px;
      font-size: 12px; color: #b0b0b0; border: 1px solid #2c2c2c;
      border-radius: 20px; padding: 4px 12px; background: rgba(0,0,0,0.25);
    }
    .ia-selo[data-origem="ia"]    { color: #00ff88; border-color: #0d4a3a; }
    .ia-selo[data-origem="cache"] { color: #80e27e; border-color: #1b4332; }
    .ia-botao-regerar {
      background: none; border: 1px solid #2c2c2c; color: #00ff88;
      font-size: 12px; border-radius: 20px; padding: 4px 12px;
      cursor: pointer; transition: opacity .2s, border-color .2s;
      font-family: inherit;
    }
    .ia-botao-regerar:hover:not(:disabled) { border-color: #00ff88; }
    .ia-botao-regerar:disabled { opacity: .45; cursor: default; }
    .ia-aviso {
      font-size: 13px; color: #b0d9ff; background: rgba(13,74,58,.45);
      border: 1px solid #1b4332; border-radius: 10px;
      padding: 10px 14px; margin-bottom: 18px; line-height: 1.5;
    }
    .ia-carregando { display: flex; align-items: center; gap: 10px; color: #b0b0b0; }
    .ia-pontos::after {
      content: ""; animation: ia-pontos 1.2s steps(4, end) infinite;
    }
    @keyframes ia-pontos {
      0% { content: ""; } 25% { content: "."; }
      50% { content: ".."; } 75% { content: "..."; }
    }
    .ia-esqueleto {
      height: 54px; border-radius: 12px; margin-bottom: 12px;
      background: linear-gradient(90deg, #16202a 25%, #1e2a32 50%, #16202a 75%);
      background-size: 200% 100%; animation: ia-brilho 1.4s ease-in-out infinite;
    }
    @keyframes ia-brilho {
      0% { background-position: 200% 0; } 100% { background-position: -200% 0; }
    }
  `;

  function injetarEstilo() {
    if (document.getElementById("ia-estilo")) return;
    const tag = document.createElement("style");
    tag.id = "ia-estilo";
    tag.textContent = ESTILO;
    document.head.appendChild(tag);
  }

  // ---------------------------------------------------------------------------
  // Elementos criados em tempo de execução
  // ---------------------------------------------------------------------------
  /** Barra com o selo de origem e o botão de gerar novas perguntas. */
  function barra() {
    let existente = document.getElementById("ia-barra");
    if (existente) return existente;

    const tipo = document.getElementById("questionType");
    if (!tipo || !tipo.parentNode) return null;

    const div = document.createElement("div");
    div.className = "ia-barra";
    div.id = "ia-barra";
    div.innerHTML =
      '<span class="ia-selo" id="ia-selo"></span>' +
      '<button type="button" class="ia-botao-regerar" id="ia-regerar" hidden>↻ Gerar novas perguntas</button>';
    tipo.parentNode.insertBefore(div, tipo.nextSibling);

    div.querySelector("#ia-regerar").addEventListener("click", regerar);
    return div;
  }

  function definirSelo(origem, modelo) {
    origemAtual = origem;
    if (!barra()) return;
    const selo = document.getElementById("ia-selo");
    if (!selo) return;

    const rotulos = {
      ia: { texto: "✨ Perguntas geradas por IA", titulo: modelo ? `Modelo: ${modelo}` : "" },
      cache: { texto: "✨ Perguntas geradas por IA (salvas)", titulo: "Geradas antes e guardadas neste navegador" },
      fixo: { texto: "📘 Banco de questões do site", titulo: "Questões fixas escritas pelos autores do site" },
    };
    const escolhido = rotulos[origem] || rotulos.fixo;
    selo.textContent = escolhido.texto;
    selo.title = escolhido.titulo;
    selo.setAttribute("data-origem", origem);

    const botao = document.getElementById("ia-regerar");
    if (botao) {
      botao.hidden = !elegivelParaIA;
      botao.disabled = false;
    }
  }

  /** Aviso amigável, sem jargão técnico. Some sozinho quando não há motivo. */
  function definirAviso(texto) {
    let aviso = document.getElementById("ia-aviso");
    if (!texto) {
      if (aviso) aviso.remove();
      return;
    }
    if (!aviso) {
      const referencia = document.getElementById("ia-barra") || document.getElementById("questionType");
      if (!referencia || !referencia.parentNode) return;
      aviso = document.createElement("div");
      aviso.className = "ia-aviso";
      aviso.id = "ia-aviso";
      referencia.parentNode.insertBefore(aviso, referencia.nextSibling);
    }
    aviso.textContent = texto;
  }

  // ---------------------------------------------------------------------------
  // Estado de carregamento
  // ---------------------------------------------------------------------------
  function texto(id, valor) {
    const elemento = document.getElementById(id);
    if (elemento) elemento.textContent = valor;
  }

  function desabilitarNavegacao(desabilitado) {
    ["nextBtn", "prevBtn", "nextNavBtn", "resetBtn"].forEach(function (id) {
      const botao = document.getElementById(id);
      if (botao) botao.disabled = desabilitado;
    });
  }

  function mostrarCarregando(mensagem) {
    injetarEstilo();
    texto("questionTypeText", "Preparando o quiz");
    texto("progressInfo", mensagem || "Gerando perguntas a partir do conteúdo do tópico");

    const titulo = document.getElementById("questionTitle");
    if (titulo) {
      titulo.innerHTML =
        '<span class="ia-carregando"><span>' +
        (mensagem || "Gerando perguntas") +
        '</span><span class="ia-pontos"></span></span>';
    }

    const opcoes = document.getElementById("optionsContainer");
    if (opcoes) {
      opcoes.style.display = "flex";
      opcoes.innerHTML = '<div class="ia-esqueleto"></div>'.repeat(4);
    }
    const vf = document.getElementById("trueFalseContainer");
    if (vf) vf.style.display = "none";

    const barraProgresso = document.getElementById("progressFill");
    if (barraProgresso) barraProgresso.style.width = "0%";

    const explicacao = document.getElementById("explanation");
    if (explicacao) explicacao.classList.remove("show");

    desabilitarNavegacao(true);
  }

  function acompanharEstado(estado) {
    if (estado.fase === "verificando") {
      mostrarCarregando("Conectando ao modelo de IA");
    } else if (estado.fase === "gerando") {
      mostrarCarregando(
        estado.tentativa > 1
          ? `Ajustando as perguntas (tentativa ${estado.tentativa} de ${estado.de})`
          : "Gerando perguntas a partir do conteúdo do tópico"
      );
    } else if (estado.fase === "validando") {
      mostrarCarregando("Conferindo as perguntas geradas");
    }
  }

  // ---------------------------------------------------------------------------
  // Sessão: o quiz que está na tela agora
  // ---------------------------------------------------------------------------
  // Sem isto, recarregar a página geraria um quiz DIFERENTE e as respostas já dadas
  // passariam a apontar para outras perguntas — porque `quizProgress` guarda as respostas
  // por índice. Guardar o conjunto exibido faz o F5 se comportar como no quiz fixo.
  // sessionStorage e não localStorage de propósito: vale só enquanto a aba estiver aberta.
  function chaveDe(alvo) {
    return `${alvo.moduloId}/${alvo.topicoId}`;
  }

  function lerSessao(alvo) {
    try {
      const cru = sessionStorage.getItem(CHAVE_SESSAO);
      if (!cru) return null;
      const dados = JSON.parse(cru);
      if (dados && dados.chave === chaveDe(alvo) && Array.isArray(dados.questoes) && dados.questoes.length) {
        return dados;
      }
    } catch (e) {
      /* sem sessionStorage: segue sem a otimização */
    }
    return null;
  }

  function gravarSessao(alvo, quiz) {
    try {
      sessionStorage.setItem(
        CHAVE_SESSAO,
        JSON.stringify({
          chave: chaveDe(alvo),
          origem: quiz.origem,
          modelo: quiz.modelo,
          questoes: quiz.questoes,
        })
      );
    } catch (e) {
      /* cota cheia: o quiz continua funcionando, só o F5 gera de novo */
    }
  }

  function apagarSessao() {
    try {
      sessionStorage.removeItem(CHAVE_SESSAO);
    } catch (e) {
      /* nada a apagar */
    }
  }

  // ---------------------------------------------------------------------------
  // Entrega das questões ao motor
  // ---------------------------------------------------------------------------
  /**
   * Substitui o conteúdo de `quizData` NO LUGAR, sem reatribuir a variável.
   *
   * `quizData` é declarado com `const` no escopo global pelos arquivos de
   * local-storage/, e `const` impede reatribuir — mas não impede mutar o array. Trocar o
   * conteúdo assim é o que permite que `quiz-engine.js` continue lendo `quizData` nos
   * seus 24 pontos, sem uma única alteração neles.
   *
   * A alternativa seria renomear o identificador dentro do motor, mexendo em 24 linhas
   * originais em vez de nenhuma.
   */
  function entregarAoMotor(questoes) {
    quizData.length = 0;
    Array.prototype.push.apply(quizData, questoes);
  }

  /** Zera o estado do motor. Conjunto de perguntas novo é tentativa nova. */
  function zerarEstado() {
    currentQuestion = 0;
    userAnswers = {};
    quizSubmitted = false;
  }

  // ---------------------------------------------------------------------------
  // Partida
  // ---------------------------------------------------------------------------
  /**
   * Chamada pelo fim de `quiz-engine.js`. Nunca lança: qualquer problema aqui cai no
   * comportamento original do site, que é o quiz fixo.
   */
  async function iniciar() {
    try {
      quizFixoOriginal = Array.isArray(quizData) ? quizData.slice() : [];

      // A camada de IA não está carregada nesta página: comportamento original, intocado.
      if (typeof obterQuiz !== "function" || typeof identificarTopicoPelaUrl !== "function") {
        return partidaOriginal();
      }

      alvoAtual = identificarTopicoPelaUrl();
      if (!alvoAtual) {
        logIA("não reconheci módulo/tópico pela URL; seguindo com o quiz fixo");
        return partidaOriginal();
      }

      const elegibilidade = ServicoQuiz.avaliarElegibilidade(alvoAtual.moduloId, alvoAtual.topicoId);
      elegivelParaIA = elegibilidade.elegivel;

      // Este tópico nunca usa IA (conteúdo insuficiente ou fora da lista): não mostra
      // carregamento nem pisca a tela. O site se comporta exatamente como antes.
      if (!elegivelParaIA) {
        partidaOriginal();
        injetarEstilo();
        definirSelo("fixo");
        return;
      }

      injetarEstilo();

      // Mesmo quiz da sessão: recarregar a página não gera de novo nem embaralha as
      // perguntas, então as respostas salvas continuam casando com os índices.
      const sessao = lerSessao(alvoAtual);
      if (sessao) {
        entregarAoMotor(sessao.questoes);
        partidaOriginal();
        definirSelo(sessao.origem, sessao.modelo);
        return;
      }

      await gerar();
    } catch (erro) {
      // Rede de segurança final: nada pode impedir o aluno de responder o quiz.
      if (typeof console !== "undefined") {
        console.error("[ia] falha na integração; usando o quiz fixo:", erro);
      }
      try {
        if (quizFixoOriginal.length) entregarAoMotor(quizFixoOriginal);
        partidaOriginal();
        definirSelo("fixo");
        definirAviso("Não foi possível preparar as perguntas novas. Você está respondendo o banco de questões do site.");
      } catch (e) {
        /* nem isso deu: a página já renderizou o que dava */
      }
    }
  }

  /** O comportamento original do motor, exatamente como era antes da integração. */
  function partidaOriginal() {
    desabilitarNavegacao(false);
    loadSavedAnswers();
    renderQuestion();
  }

  /** Pede o quiz à camada de IA e entrega ao motor. */
  async function gerar() {
    const botao = document.getElementById("ia-regerar");
    if (botao) botao.disabled = true;

    mostrarCarregando("Conectando ao modelo de IA");

    const quiz = await obterQuiz(alvoAtual.moduloId, alvoAtual.topicoId, {
      quizFixo: quizFixoOriginal,
      aoMudarEstado: acompanharEstado,
    });

    desabilitarNavegacao(false);

    if (quiz.origem === "fixo") {
      // O serviço devolve o quiz fixo com o campo `origem` acrescentado. Entregar
      // `quiz.questoes` em vez de `quizFixoOriginal` mantém essa marca, que é o que o
      // selo e o diagnóstico leem. O conteúdo das questões é o mesmo do site.
      // (`quizData` pode ter sido mutado por uma geração anterior nesta mesma aba, então
      // a reentrega também serve de restauração.)
      entregarAoMotor(quiz.questoes.length ? quiz.questoes : quizFixoOriginal);
      apagarSessao();
      zerarEstado();
      partidaOriginal();
      definirSelo("fixo");
      definirAviso(mensagemDeFallback(quiz));
      return;
    }

    entregarAoMotor(quiz.questoes);
    gravarSessao(alvoAtual, quiz);
    zerarEstado();
    desabilitarNavegacao(false);
    renderQuestion();
    definirSelo(quiz.origem, quiz.modelo);
    definirAviso(
      quiz.origem === "cache"
        ? "Não foi possível falar com o modelo agora, então estas são perguntas geradas antes e guardadas neste navegador."
        : null
    );
  }

  /** Texto para o aluno. Sem jargão: nada de timeout, HTTP, JSON ou daemon. */
  function mensagemDeFallback(quiz) {
    const status = quiz.diagnostico && quiz.diagnostico.status;
    if (status && !status.online) {
      return "As perguntas novas não estão disponíveis no momento. Você está respondendo o banco de questões do site.";
    }
    if (status && !status.modeloRegistrado) {
      return "As perguntas novas não estão disponíveis nesta máquina. Você está respondendo o banco de questões do site.";
    }
    return "Não foi possível preparar perguntas novas agora. Você está respondendo o banco de questões do site.";
  }

  /** Botão "Gerar novas perguntas". */
  async function regerar() {
    if (!alvoAtual) return;
    apagarSessao();
    definirAviso(null);
    try {
      await gerar();
    } catch (erro) {
      desabilitarNavegacao(false);
      definirAviso("Não foi possível gerar perguntas novas agora. Tente de novo em instantes.");
      const botao = document.getElementById("ia-regerar");
      if (botao) botao.disabled = false;
    }
  }

  return {
    iniciar,
    regerar,
    apagarSessao,
    get origem() {
      return origemAtual;
    },
  };
})();
