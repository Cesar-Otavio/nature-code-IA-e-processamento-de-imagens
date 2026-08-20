/**
 * metricas-ia.js — contadores de uso da camada de IA, persistidos no LocalStorage.
 *
 * Chave: `quiz_ia_metricas`. Não encosta em `quizProgress` — o progresso do aluno é
 * intocável e vive em outra chave.
 *
 * Existe para o relatório: taxa de rejeição por motivo, latência média e p95, e quantas
 * respostas precisaram de reparo no parser são números que sustentam a defesa do
 * trabalho. Medir em vez de afirmar.
 *
 * Depende de: config-ia.js
 */

const MetricasIA = (function () {
  const CHAVE = "quiz_ia_metricas";
  const MAX_LATENCIAS = 200; // guarda as últimas N para calcular mediana e p95

  function vazio() {
    return {
      versao: 1,
      geracoes: 0, // chamadas ao modelo que voltaram com resposta
      falhasDeChamada: 0, // chamadas que nem chegaram a produzir texto
      questoesRecebidas: 0,
      questoesAprovadas: 0,
      rejeicoesPorMotivo: {},
      estrategiasDoParser: {},
      falhasPorTipo: {},
      latenciasMs: [],
      porModelo: {},
      primeiroRegistro: null,
      ultimoRegistro: null,
    };
  }

  function ler() {
    try {
      const cru = localStorage.getItem(CHAVE);
      if (!cru) return vazio();
      const dados = JSON.parse(cru);
      return dados && dados.versao === 1 ? dados : vazio();
    } catch (e) {
      return vazio();
    }
  }

  function gravar(dados) {
    try {
      dados.ultimoRegistro = new Date().toISOString();
      if (!dados.primeiroRegistro) dados.primeiroRegistro = dados.ultimoRegistro;
      localStorage.setItem(CHAVE, JSON.stringify(dados));
    } catch (e) {
      logIA("não consegui gravar métricas:", e.message);
    }
  }

  function incrementar(mapa, chave, quanto) {
    if (!chave) return;
    mapa[chave] = (mapa[chave] || 0) + (quanto === undefined ? 1 : quanto);
  }

  /** Uma chamada ao modelo que voltou com texto. */
  function registrarGeracao(dados) {
    const m = ler();
    m.geracoes += 1;
    m.latenciasMs.push(dados.latenciaMs);
    if (m.latenciasMs.length > MAX_LATENCIAS) {
      m.latenciasMs = m.latenciasMs.slice(-MAX_LATENCIAS);
    }
    incrementar(m.estrategiasDoParser, dados.estrategiaParser);
    if (dados.modelo) {
      if (!m.porModelo[dados.modelo]) m.porModelo[dados.modelo] = { geracoes: 0, aprovadas: 0 };
      m.porModelo[dados.modelo].geracoes += 1;
    }
    gravar(m);
  }

  /** Uma chamada que falhou antes de produzir texto (rede, timeout, assinatura...). */
  function registrarFalhaDeChamada(tipo) {
    const m = ler();
    m.falhasDeChamada += 1;
    incrementar(m.falhasPorTipo, tipo || "desconhecido");
    gravar(m);
  }

  /** Resultado de uma validação: quantas entraram, quantas passaram, por que caíram. */
  function registrarValidacao(resultado, modelo) {
    const m = ler();
    m.questoesRecebidas += resultado.recebidas;
    m.questoesAprovadas += resultado.aprovadas.length;
    for (const rejeicao of resultado.rejeicoes) {
      incrementar(m.rejeicoesPorMotivo, rejeicao.motivo);
    }
    if (modelo && m.porModelo[modelo]) {
      m.porModelo[modelo].aprovadas += resultado.aprovadas.length;
    }
    gravar(m);
  }

  function percentil(ordenadas, fracao) {
    if (!ordenadas.length) return 0;
    const indice = Math.min(ordenadas.length - 1, Math.floor(fracao * ordenadas.length));
    return ordenadas[indice];
  }

  /** Números derivados, prontos para a página de diagnóstico e para o relatório. */
  function resumo() {
    const m = ler();
    const ordenadas = m.latenciasMs.slice().sort((a, b) => a - b);
    const soma = ordenadas.reduce((a, b) => a + b, 0);

    return {
      geracoes: m.geracoes,
      falhasDeChamada: m.falhasDeChamada,
      falhasPorTipo: m.falhasPorTipo,
      questoesRecebidas: m.questoesRecebidas,
      questoesAprovadas: m.questoesAprovadas,
      taxaAprovacao: m.questoesRecebidas ? m.questoesAprovadas / m.questoesRecebidas : null,
      taxaRejeicao: m.questoesRecebidas
        ? (m.questoesRecebidas - m.questoesAprovadas) / m.questoesRecebidas
        : null,
      rejeicoesPorMotivo: m.rejeicoesPorMotivo,
      estrategiasDoParser: m.estrategiasDoParser,
      latencia: {
        amostras: ordenadas.length,
        mediaMs: ordenadas.length ? Math.round(soma / ordenadas.length) : 0,
        medianaMs: percentil(ordenadas, 0.5),
        p95Ms: percentil(ordenadas, 0.95),
        minMs: ordenadas[0] || 0,
        maxMs: ordenadas[ordenadas.length - 1] || 0,
      },
      porModelo: m.porModelo,
      primeiroRegistro: m.primeiroRegistro,
      ultimoRegistro: m.ultimoRegistro,
    };
  }

  function limpar() {
    try {
      localStorage.removeItem(CHAVE);
    } catch (e) {
      /* sem LocalStorage: nada a limpar */
    }
  }

  return {
    CHAVE,
    registrarGeracao,
    registrarFalhaDeChamada,
    registrarValidacao,
    resumo,
    limpar,
    lerBruto: ler,
  };
})();
