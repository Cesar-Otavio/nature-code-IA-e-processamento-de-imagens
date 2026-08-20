/**
 * cache-quiz.js — banco de questões validadas no LocalStorage.
 *
 * Chave: `quiz_ia_banco`. Não encosta em `quizProgress`.
 *
 * Tem função dupla, e a segunda é a que importa para a apresentação:
 *   1. reduz latência — questão já gerada não precisa de nova chamada;
 *   2. É o segundo nível do fallback. Com o Ollama fora do ar, o quiz continua saindo
 *      com questões geradas por IA, e não com o quiz fixo.
 *
 * Guarda as questões no formato da IA (validado), não no formato do site. A conversão
 * acontece num lugar só, no servico-quiz.js.
 *
 * Depende de: config-ia.js
 */

const CacheQuiz = (function () {
  const CHAVE = "quiz_ia_banco";
  const VERSAO = 1;

  // O LocalStorage costuma ficar em torno de 5 MB para a origem inteira, e essa cota é
  // compartilhada com o `quizProgress` do aluno — que tem prioridade absoluta. 1,5 MB é
  // um teto folgado para o banco de questões sem ameaçar o progresso.
  const LIMITE_BYTES = 1500000;

  function vazio() {
    return { versao: VERSAO, topicos: {} };
  }

  function ler() {
    try {
      const cru = localStorage.getItem(CHAVE);
      if (!cru) return vazio();
      const dados = JSON.parse(cru);
      return dados && dados.versao === VERSAO && dados.topicos ? dados : vazio();
    } catch (e) {
      logIA("banco de questões ilegível, recomeçando:", e.message);
      return vazio();
    }
  }

  function gravar(banco) {
    try {
      localStorage.setItem(CHAVE, JSON.stringify(banco));
      return true;
    } catch (e) {
      // QuotaExceededError: descarta metade das mais antigas e tenta de novo, uma vez.
      logIA("cota estourada, descartando as mais antigas:", e.message);
      descartarMaisAntigas(banco, 0.5);
      try {
        localStorage.setItem(CHAVE, JSON.stringify(banco));
        return true;
      } catch (e2) {
        logIA("não consegui gravar o banco nem depois de podar:", e2.message);
        return false;
      }
    }
  }

  function chaveDoTopico(moduloId, topicoId) {
    return `${moduloId}/${topicoId}`;
  }

  /**
   * Hash do enunciado normalizado, para deduplicação.
   * djb2 em base36: curto, determinístico e suficiente para comparar enunciados —
   * não é uso criptográfico.
   */
  function hashDoEnunciado(enunciado) {
    const texto = String(enunciado || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .replace(/[^a-z0-9]/g, "");

    let h = 5381;
    for (let i = 0; i < texto.length; i++) {
      h = ((h << 5) + h + texto.charCodeAt(i)) | 0;
    }
    return (h >>> 0).toString(36);
  }

  /** Remove as `fracao` mais antigas do banco inteiro, olhando o carimbo de data. */
  function descartarMaisAntigas(banco, fracao) {
    const todas = [];
    for (const chave of Object.keys(banco.topicos)) {
      for (const item of banco.topicos[chave].questoes) {
        todas.push({ chave, hash: item.hash, criadoEm: item.criadoEm });
      }
    }
    todas.sort((a, b) => String(a.criadoEm).localeCompare(String(b.criadoEm)));

    const quantos = Math.max(1, Math.floor(todas.length * fracao));
    const condenadas = new Set(todas.slice(0, quantos).map((x) => x.chave + "|" + x.hash));

    for (const chave of Object.keys(banco.topicos)) {
      banco.topicos[chave].questoes = banco.topicos[chave].questoes.filter(
        (item) => !condenadas.has(chave + "|" + item.hash)
      );
      if (!banco.topicos[chave].questoes.length) delete banco.topicos[chave];
    }
    return quantos;
  }

  /**
   * Guarda questões já aprovadas pelo validador.
   * Questão com enunciado repetido é ignorada — é o que impede o banco de encher de
   * variações da mesma pergunta a cada nova geração.
   *
   * @returns {{guardadas: number, duplicadas: number}}
   */
  function guardar(moduloId, topicoId, questoes, modelo) {
    if (!CONFIG_IA.cacheHabilitado) return { guardadas: 0, duplicadas: 0 };

    const banco = ler();
    const chave = chaveDoTopico(moduloId, topicoId);
    if (!banco.topicos[chave]) banco.topicos[chave] = { questoes: [] };

    const existentes = new Set(banco.topicos[chave].questoes.map((q) => q.hash));
    const agora = new Date().toISOString();
    let guardadas = 0;
    let duplicadas = 0;

    for (const questao of questoes) {
      const hash = hashDoEnunciado(questao.enunciado);
      if (existentes.has(hash)) {
        duplicadas++;
        continue;
      }
      existentes.add(hash);
      banco.topicos[chave].questoes.push({
        hash,
        criadoEm: agora,
        conceitoAvaliado: questao.conceitoAvaliado || null,
        modelo: modelo || null,
        questao,
      });
      guardadas++;
    }

    banco.topicos[chave].atualizadoEm = agora;

    if (JSON.stringify(banco).length > LIMITE_BYTES) {
      const removidas = descartarMaisAntigas(banco, 0.3);
      logIA(`banco acima de ${LIMITE_BYTES} bytes: ${removidas} questões antigas descartadas`);
    }

    gravar(banco);
    logIA(`cache: ${guardadas} guardadas, ${duplicadas} duplicadas em ${chave}`);
    return { guardadas, duplicadas };
  }

  /**
   * Tira até `quantidade` questões do banco, sorteadas.
   * O sorteio existe para que o segundo quiz offline não seja idêntico ao primeiro.
   */
  function obter(moduloId, topicoId, quantidade) {
    if (!CONFIG_IA.cacheHabilitado) return [];

    const banco = ler();
    const entrada = banco.topicos[chaveDoTopico(moduloId, topicoId)];
    if (!entrada || !entrada.questoes.length) return [];

    const copia = entrada.questoes.slice();
    for (let i = copia.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const t = copia[i];
      copia[i] = copia[j];
      copia[j] = t;
    }
    return copia.slice(0, quantidade).map((item) => item.questao);
  }

  /**
   * Conceitos já cobrados neste tópico. Vai para o prompt como `conceitosExcluir`,
   * forçando variação entre tentativas.
   */
  function conceitosGuardados(moduloId, topicoId, limite) {
    const banco = ler();
    const entrada = banco.topicos[chaveDoTopico(moduloId, topicoId)];
    if (!entrada) return [];

    const conceitos = [];
    for (let i = entrada.questoes.length - 1; i >= 0; i--) {
      const conceito = entrada.questoes[i].conceitoAvaliado;
      if (conceito && conceitos.indexOf(conceito) === -1) conceitos.push(conceito);
      if (limite && conceitos.length >= limite) break;
    }
    return conceitos;
  }

  /** Números para a página de diagnóstico. */
  function estatisticas() {
    const banco = ler();
    const porTopico = {};
    let total = 0;
    for (const chave of Object.keys(banco.topicos)) {
      const n = banco.topicos[chave].questoes.length;
      porTopico[chave] = { questoes: n, atualizadoEm: banco.topicos[chave].atualizadoEm || null };
      total += n;
    }
    let bytes = 0;
    try {
      bytes = (localStorage.getItem(CHAVE) || "").length;
    } catch (e) {
      /* sem LocalStorage */
    }
    return { total, topicos: porTopico, bytes, limiteBytes: LIMITE_BYTES };
  }

  function limpar() {
    try {
      localStorage.removeItem(CHAVE);
    } catch (e) {
      /* nada a limpar */
    }
  }

  function limparTopico(moduloId, topicoId) {
    const banco = ler();
    delete banco.topicos[chaveDoTopico(moduloId, topicoId)];
    gravar(banco);
  }

  return {
    CHAVE,
    guardar,
    obter,
    conceitosGuardados,
    estatisticas,
    limpar,
    limparTopico,
    hashDoEnunciado,
  };
})();
