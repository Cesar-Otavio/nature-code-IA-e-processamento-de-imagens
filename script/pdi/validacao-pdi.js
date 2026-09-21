/**
 * validacao-pdi.js — conferência das respostas da API antes de exibi-las.
 *
 * Funções puras, sem DOM: a interface só mostra uma resposta depois que ela passa por
 * aqui. Uma resposta fora do formato esperado vira mensagem de erro clara, e não uma
 * exceção no meio da montagem da tela.
 *
 * Também carregável no Node (module.exports), para os testes automatizados.
 *
 * Depende de: nada.
 */

const ValidacaoPDI = (function () {
  "use strict";

  const STATUS_VALIDOS = ["sucesso", "sucesso_com_avisos", "erro"];
  const ATRIBUTOS = ["alongamento", "concavidade", "compacidade", "complexidade_borda", "orientacao"];

  // Formato exato das URLs que a API gera: /api/resultado/<uuid hex>/<NN-nome>.png
  const PADRAO_URL_IMAGEM = /^\/api\/resultado\/[0-9a-f]{32}\/[0-9]{2}-[a-z-]+\.png$/;

  function ehObjeto(valor) {
    return valor !== null && typeof valor === "object" && !Array.isArray(valor);
  }

  /**
   * Devolve a URL completa de uma imagem intermediária, ou null se o caminho não tiver
   * exatamente o formato gerado pela API. Nada de outro host, protocolo ou "../".
   */
  function urlDeImagemSegura(caminho, urlBase) {
    if (typeof caminho !== "string" || !PADRAO_URL_IMAGEM.test(caminho)) return null;
    return urlBase + caminho;
  }

  /**
   * Lista os problemas de formato de uma resposta. Lista vazia = pode exibir.
   */
  function problemasDaResposta(dados) {
    if (!ehObjeto(dados)) return ["a resposta não é um objeto JSON"];
    if (!STATUS_VALIDOS.includes(dados.status)) return ["status ausente ou desconhecido"];

    const problemas = [];

    if (dados.status === "erro") {
      if (!ehObjeto(dados.erro)) problemas.push("erro sem detalhes");
      else if (typeof dados.erro.mensagem !== "string") problemas.push("erro sem mensagem");
      return problemas;
    }

    const c = dados.caracteristicas;
    if (!ehObjeto(c)) {
      problemas.push("características ausentes");
    } else {
      for (const bloco of ["dimensoes", "forma", "orientacao"]) {
        if (!ehObjeto(c[bloco])) problemas.push(`características sem '${bloco}'`);
      }
    }

    const cl = dados.classificacao;
    if (!ehObjeto(cl)) {
      problemas.push("classificação ausente");
    } else {
      for (const atributo of ATRIBUTOS) {
        if (!ehObjeto(cl[atributo]) || typeof cl[atributo].categoria !== "string") {
          problemas.push(`classificação sem '${atributo}'`);
        }
      }
      if (typeof cl.resumo !== "string") problemas.push("classificação sem resumo");
    }

    if (dados.avisos !== undefined && !Array.isArray(dados.avisos)) problemas.push("avisos fora do formato");
    if (dados.imagens_intermediarias !== undefined && dados.imagens_intermediarias !== null &&
        !ehObjeto(dados.imagens_intermediarias)) {
      problemas.push("imagens fora do formato");
    }

    return problemas;
  }

  /** Mensagem para o usuário a partir de uma resposta de erro já validada. */
  function mensagemDeErro(dados) {
    const codigo = typeof dados.erro.codigo === "string" ? ` (código ${dados.erro.codigo})` : "";
    return dados.erro.mensagem + codigo;
  }

  return { urlDeImagemSegura, problemasDaResposta, mensagemDeErro, PADRAO_URL_IMAGEM };
})();

if (typeof module !== "undefined" && module.exports) {
  module.exports = ValidacaoPDI;
}
