/**
 * analise-folha.js — interface da Análise Morfológica de Folhas.
 *
 * Envia a imagem ao serviço local (CONFIG_PDI.urlBase) e exibe o resultado.
 * Nenhum processamento acontece aqui: esta camada só mostra o que a API devolveu.
 *
 * Todo texto vindo da API é inserido com textContent, nunca innerHTML — o nome do
 * arquivo é escolhido pelo usuário e não pode virar marcação na página.
 *
 * Erros não são escondidos: o usuário vê uma mensagem clara, e o detalhe técnico vai
 * para o console do navegador (console.error), nunca para a tela.
 *
 * Depende de: config-pdi.js, validacao-pdi.js
 */

(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);

  const ROTULOS = {
    alongamento: "Alongamento",
    concavidade: "Concavidade",
    compacidade: "Compacidade",
    complexidade_borda: "Complexidade da borda",
    orientacao: "Orientação do eixo",
  };

  const TEXTO_CATEGORIA = {
    baixa: "baixa", moderada: "moderada", alta: "alta", extrema: "extrema",
    ambigua: "ambígua", regular: "regular", complexa: "complexa",
    bem_definida: "bem definida", pouco_definida: "pouco definida",
    indefinida: "indefinida", indeterminado: "indeterminado",
  };

  const TEXTO_AVISO = {
    objeto_toca_borda: "A folha toca a borda da imagem — pode estar cortada, e área e perímetro ficam subestimados.",
    orientacao_nao_confiavel: "A folha não tem eixo principal definido — a orientação não é confiável.",
    multiplos_contornos: "Mais de um objeto foi encontrado; foi analisado o maior.",
    selecao_ambigua: "Há dois objetos de tamanho parecido — a escolha da folha é incerta.",
    solidez_baixa_borda_muito_recortada: "Borda muito recortada.",
    objeto_muito_alongado: "Objeto muito alongado.",
    "concavidade ambigua: ver observacoes do atributo":
      "A concavidade é ambígua: em objetos muito alongados, curvatura e recorte produzem o mesmo sinal.",
  };

  const MENSAGEM_OFFLINE =
    "O serviço local de processamento de imagens não está disponível. " +
    "Inicie o módulo Python para utilizar esta funcionalidade: " +
    "cd processamento-imagens && python -m src.api";

  const MENSAGEM_RESPOSTA_INVALIDA =
    "O serviço respondeu num formato inesperado. Tente novamente ou reinicie o serviço.";

  let arquivoAtual = null;
  let urlPreview = null;
  let servicoDisponivel = false;
  let emProcessamento = false;
  // Cada análise recebe um número; respostas de uma análise anterior são ignoradas.
  let analiseAtual = 0;
  let controleAnalise = null;

  function texto(id, conteudo) {
    $(id).textContent = conteudo;
  }

  function mostrar(id, visivel) {
    $(id).hidden = !visivel;
  }

  function atualizarBotao() {
    $("botao-processar").disabled = arquivoAtual === null || emProcessamento;
  }

  function formatar(numero, casas) {
    if (typeof numero !== "number" || !Number.isFinite(numero)) return "—";
    return numero.toLocaleString("pt-BR", {
      minimumFractionDigits: casas, maximumFractionDigits: casas,
    });
  }

  /** fetch com limite de tempo que de fato cancela a requisição. */
  async function buscarComLimite(url, opcoes, ms, controle = new AbortController()) {
    const relogio = setTimeout(() => controle.abort(), ms);
    try {
      return await fetch(url, { ...opcoes, signal: controle.signal });
    } finally {
      clearTimeout(relogio);
    }
  }

  /** Lê o corpo como JSON; devolve null se não for JSON. */
  async function lerJson(resposta) {
    try {
      return await resposta.json();
    } catch (erro) {
      console.error("[PDI] resposta não é JSON:", resposta.status, erro);
      return null;
    }
  }

  /** Cancela a análise em andamento, se houver, e invalida sua resposta. */
  function cancelarAnalise() {
    analiseAtual += 1;
    if (controleAnalise) controleAnalise.abort();
    controleAnalise = null;
  }

  function liberarPreview() {
    if (urlPreview) URL.revokeObjectURL(urlPreview);
    urlPreview = null;
    $("preview").removeAttribute("src");
  }

  // ---------------------------------------------------------------------------
  // Estado do serviço
  // ---------------------------------------------------------------------------

  async function verificarServico() {
    try {
      const resposta = await buscarComLimite(`${CONFIG_PDI.urlBase}/health`, {}, 4000);
      const dados = resposta.ok ? await lerJson(resposta) : null;
      if (!dados || dados.status !== "ok") throw new Error(`health respondeu ${resposta.status}`);

      servicoDisponivel = true;
      $("estado-servico").className = "estado estado-ok";
      const versao = typeof dados.versao === "string" ? ` (versão ${dados.versao})` : "";
      texto("estado-servico", `Serviço de processamento disponível${versao}.`);
    } catch (erro) {
      console.error("[PDI] serviço indisponível:", erro);
      servicoDisponivel = false;
      $("estado-servico").className = "estado estado-erro";
      texto("estado-servico", MENSAGEM_OFFLINE);
    }
    // O botão depende só de haver arquivo: com o serviço fora, clicar informa o
    // problema e tenta de novo — o usuário nunca fica preso num botão desabilitado.
    atualizarBotao();
    return servicoDisponivel;
  }

  // ---------------------------------------------------------------------------
  // Seleção de arquivo
  // ---------------------------------------------------------------------------

  function selecionarArquivo(arquivo) {
    // Qualquer nova seleção descarta a anterior — inclusive se a nova for inválida.
    cancelarAnalise();
    arquivoAtual = null;
    liberarPreview();
    mostrar("area-preview", false);
    limparResultado();
    mostrar("erro", false);

    if (!arquivo) {
      atualizarBotao();
      return;
    }

    const nome = arquivo.name.toLowerCase();
    const extensaoValida = CONFIG_PDI.extensoesAceitas.some((ext) => nome.endsWith(ext));
    if (!extensaoValida) {
      $("entrada-arquivo").value = "";
      mostrarErro("Formato não suportado. Use JPG, PNG ou BMP.");
      atualizarBotao();
      return;
    }
    if (arquivo.size > CONFIG_PDI.tamanhoMaximoBytes) {
      $("entrada-arquivo").value = "";
      mostrarErro("Arquivo muito grande. O máximo é 12 MB.");
      atualizarBotao();
      return;
    }

    arquivoAtual = arquivo;
    urlPreview = URL.createObjectURL(arquivo);
    $("preview").src = urlPreview;
    texto("nome-arquivo", arquivo.name);
    mostrar("area-preview", true);
    atualizarBotao();
    verificarServico();
  }

  function removerArquivo() {
    cancelarAnalise();
    arquivoAtual = null;
    liberarPreview();
    $("entrada-arquivo").value = "";
    mostrar("area-preview", false);
    limparResultado();
    mostrar("erro", false);
    atualizarBotao();
  }

  // ---------------------------------------------------------------------------
  // Processamento
  // ---------------------------------------------------------------------------

  async function processar() {
    if (!arquivoAtual || emProcessamento) return;

    const minhaAnalise = ++analiseAtual;
    const controle = new AbortController();
    controleAnalise = controle;
    emProcessamento = true;
    limparResultado();
    mostrar("erro", false);
    mostrar("carregando", true);
    atualizarBotao();

    const formulario = new FormData();
    formulario.append("imagem", arquivoAtual);

    try {
      let resposta;
      try {
        resposta = await buscarComLimite(
          `${CONFIG_PDI.urlBase}/api/processar-folha`,
          { method: "POST", body: formulario },
          CONFIG_PDI.timeoutMs,
          controle
        );
      } catch (erro) {
        console.error("[PDI] falha de rede:", erro);
        if (minhaAnalise !== analiseAtual) return;
        const tempoEsgotado = erro && erro.name === "AbortError";
        await verificarServico();
        mostrarErro(
          tempoEsgotado
            ? "O processamento demorou mais que o esperado e foi cancelado. Tente novamente."
            : servicoDisponivel
              ? "A comunicação com o serviço falhou. Tente novamente."
              : MENSAGEM_OFFLINE
        );
        return;
      }

      const dados = await lerJson(resposta);
      if (minhaAnalise !== analiseAtual) return; // o usuário já trocou de imagem

      const problemas = ValidacaoPDI.problemasDaResposta(dados);
      if (problemas.length > 0) {
        console.error("[PDI] resposta inesperada:", resposta.status, problemas, dados);
        mostrarErro(MENSAGEM_RESPOSTA_INVALIDA);
        return;
      }

      if (dados.status === "erro") {
        mostrarErro(ValidacaoPDI.mensagemDeErro(dados));
        return;
      }

      try {
        exibirResultado(dados);
      } catch (erro) {
        // Defesa final: nada de tela meio montada nem exceção sem tratamento.
        console.error("[PDI] falha ao exibir o resultado:", erro);
        limparResultado();
        mostrarErro(MENSAGEM_RESPOSTA_INVALIDA);
      }
    } finally {
      if (minhaAnalise === analiseAtual) {
        mostrar("carregando", false);
        controleAnalise = null;
      }
      emProcessamento = false;
      atualizarBotao();
    }
  }

  function mostrarErro(mensagem) {
    texto("erro", mensagem);
    mostrar("erro", true);
  }

  function limparResultado() {
    mostrar("resultado", false);
    mostrar("carregando", false);
    $("lista-medidas").replaceChildren();
    $("lista-classificacao").replaceChildren();
    $("lista-avisos").replaceChildren();
    texto("resumo", "");
    texto("tempo", "");
    for (const id of ["img-original", "img-mascara", "img-final"]) definirImagem(id, null, false);
  }

  // ---------------------------------------------------------------------------
  // Exibição
  // ---------------------------------------------------------------------------

  /**
   * Mostra a imagem se a URL for válida. Sem URL, esconde a imagem — e, se
   * `avisarAusencia`, mostra "Imagem indisponível". Falha de carregamento também avisa.
   */
  function definirImagem(id, url, avisarAusencia) {
    const img = $(id);
    const aviso = img.parentElement.querySelector(".img-indisponivel");

    img.onerror = null;
    if (!url) {
      img.removeAttribute("src");
      img.hidden = true;
      if (aviso) aviso.hidden = !avisarAusencia;
      return;
    }

    img.hidden = false;
    if (aviso) aviso.hidden = true;
    img.onerror = () => {
      console.error("[PDI] imagem intermediária não carregou:", url);
      img.hidden = true;
      if (aviso) aviso.hidden = false;
    };
    img.src = url;
  }

  function linha(lista, rotulo, valor, detalhe) {
    const item = document.createElement("div");
    item.className = "linha";

    const r = document.createElement("span");
    r.className = "rotulo";
    r.textContent = rotulo;

    const v = document.createElement("span");
    v.className = "valor";
    v.textContent = valor;

    item.append(r, v);

    if (detalhe) {
      const d = document.createElement("span");
      d.className = "detalhe";
      d.textContent = detalhe;
      item.append(d);
    }

    lista.append(item);
  }

  function exibirResultado(dados) {
    const imagens = dados.imagens_intermediarias || {};
    const pares = [["img-original", "00-original"], ["img-mascara", "05-mascara-limpa"], ["img-final", "07-final"]];
    for (const [id, etapa] of pares) {
      const url = ValidacaoPDI.urlDeImagemSegura(imagens[etapa], CONFIG_PDI.urlBase);
      if (imagens[etapa] !== undefined && url === null) {
        console.error("[PDI] URL de imagem recusada:", imagens[etapa]);
      }
      definirImagem(id, url, true);
    }

    const d = dados.caracteristicas.dimensoes;
    const f = dados.caracteristicas.forma;
    const o = dados.caracteristicas.orientacao;
    const medidas = $("lista-medidas");

    linha(medidas, "Área", `${formatar(d.area_contorno_px2, 0)} px²`);
    linha(medidas, "Perímetro", `${formatar(d.perimetro_px, 1)} px`);
    linha(medidas, "Elongação", formatar(f.elongacao, 2), "lado maior ÷ lado menor");
    linha(medidas, "Circularidade", formatar(f.circularidade, 3), "um círculo digital mede ≈ 0,90");
    linha(medidas, "Solidez", formatar(f.solidez, 3), "área ÷ envelope convexo");
    linha(medidas, "Extent", formatar(f.extent, 3), "área ÷ caixa envolvente");
    linha(
      medidas, "Orientação",
      typeof o.angulo_graus === "number" ? `${formatar(o.angulo_graus, 1)}°` : "indefinida",
      `anisotropia ${formatar(o.anisotropia, 3)}`
    );

    const classificacao = $("lista-classificacao");
    for (const atributo of Object.keys(ROTULOS)) {
      const categoria = dados.classificacao[atributo].categoria;
      linha(classificacao, ROTULOS[atributo], TEXTO_CATEGORIA[categoria] || categoria);
    }
    texto("resumo", dados.classificacao.resumo);

    const listaAvisos = $("lista-avisos");
    for (const aviso of dados.avisos || []) {
      if (typeof aviso !== "string") continue;
      if (aviso.startsWith("descricao geometrica") || aviso.startsWith("atributos proximos")) continue;
      const li = document.createElement("li");
      li.textContent = TEXTO_AVISO[aviso] || aviso;
      listaAvisos.append(li);
    }
    mostrar("bloco-avisos", listaAvisos.children.length > 0);

    const tempo = dados.processamento && dados.processamento.tempo_total_ms;
    texto("tempo", typeof tempo === "number" ? `Processado em ${formatar(tempo, 0)} ms.` : "");
    mostrar("resultado", true);
  }

  // ---------------------------------------------------------------------------
  // Início
  // ---------------------------------------------------------------------------

  document.addEventListener("DOMContentLoaded", () => {
    $("entrada-arquivo").addEventListener("change", (e) => selecionarArquivo(e.target.files[0]));
    $("botao-remover").addEventListener("click", removerArquivo);
    $("botao-processar").addEventListener("click", processar);
    $("botao-verificar").addEventListener("click", verificarServico);
    window.addEventListener("pagehide", liberarPreview);
    verificarServico();
  });
})();
