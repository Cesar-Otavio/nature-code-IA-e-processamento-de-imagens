/**
 * extrair-conteudo.js — script DE DESENVOLVIMENTO. Não faz parte do site em execução.
 *
 * Percorre os 21 HTMLs de tópico, limpa as tags e regenera `dados/base-conhecimento.js`,
 * que é o material que alimenta o prompt da LLM.
 *
 * Uso (a partir da raiz do projeto):
 *     node scripts/extrair-conteudo.js
 *     node scripts/extrair-conteudo.js --verificar    (não escreve; só compara e reporta)
 *
 * Sem dependências externas: apenas os módulos nativos `fs` e `path` do Node.
 *
 * REGRA CENTRAL: este script só transporta texto que já existe no site. Ele nunca
 * completa, resume ou reescreve conteúdo de Biologia. Quando um tópico tem pouco
 * texto, a saída registra isso em números — não tenta compensar.
 */

"use strict";

const fs = require("fs");
const path = require("path");

const RAIZ = path.resolve(__dirname, "..");
const SAIDA = path.join(RAIZ, "dados", "base-conhecimento.js");

// ---------------------------------------------------------------------------
// Parâmetros de suficiência de conteúdo
// ---------------------------------------------------------------------------
// Os três primeiros números não são arbitrários: saíram da medição do próprio site,
// registrada em docs/00-MAPEAMENTO.md (28.688 caracteres de texto distribuídos em
// 97 seções <h2>, ou seja, ~296 caracteres por seção).
const PARAMETROS = {
  // Custo textual estimado de uma questão honesta. Arredondado para cima a partir
  // dos ~296 caracteres/seção medidos, para ficar do lado conservador.
  CARACTERES_POR_QUESTAO: 350,

  // Abaixo disso o tópico é considerado insuficiente: a IA fica desligada nele e o
  // quiz fixo original assume. Equivale a menos de duas seções de texto.
  MINIMO_ABSOLUTO: 600,

  // Uma seção só conta como "seção com texto" a partir daqui. Serve para não
  // contar as seções que existem apenas para segurar uma imagem.
  MINIMO_POR_SECAO: 80,

  // Teto de questões por quiz, independente do volume de conteúdo.
  MAXIMO_QUESTOES: 5,
};

// Títulos de seção que são rótulos estruturais do site, não conceitos de Biologia.
// Usados apenas para filtrar `conceitosChave` — o texto da seção continua íntegro.
const TITULOS_ESTRUTURAIS = new Set(
  [
    "características",
    "características gerais",
    "morfologia",
    "classificação",
    "reprodução",
    "reprodução sexuada",
    "reprodução assexuada",
    "ciclo reprodutivo",
    "ciclo de vida",
    "descrição",
    "principais classes",
    "características exclusivas",
    "anexos",
    "grupos",
    "tipos",
    "exemplos",
    "observação",
    "importância",
    "curiosidades",
  ].map(normalizar)
);

// ---------------------------------------------------------------------------
// Módulos e onde procurar os tópicos
// ---------------------------------------------------------------------------
// O id do módulo e o id do tópico são derivados do caminho no disco — exatamente a
// mesma regra que a camada de IA usará em tempo de execução a partir de
// `location.pathname`. Ver docs/00-MAPEAMENTO.md §9.
const MODULOS = [
  {
    id: "animais",
    titulo: "Reino Animal",
    paginaModulo: "pages/modulos/animais.html",
    pastaTopicos: "pages/modulos/topicos/topicos-animais",
  },
  {
    id: "plantas",
    titulo: "Plantas",
    paginaModulo: "pages/modulos/plantas.html",
    pastaTopicos: "pages/modulos/topicos/topicos-plantas",
  },
  {
    id: "ecossistemas",
    titulo: "Ecossistemas",
    paginaModulo: "pages/modulos/ecossistemas.html",
    pastaTopicos: "pages/modulos/topicos/topicos-ecossistemas",
  },
];

// ---------------------------------------------------------------------------
// Utilitários de texto
// ---------------------------------------------------------------------------

/** Minúsculas, sem acento, sem pontuação nas pontas. Para comparação, não para exibição. */
function normalizar(texto) {
  return texto
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** Decodifica as poucas entidades que podem aparecer. O site hoje não usa nenhuma. */
function decodificarEntidades(texto) {
  return texto
    .replace(/&nbsp;/g, " ")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, "&");
}

/** Colapsa espaços e quebras vindas da indentação do HTML, preservando \n intencionais. */
function colapsarEspacos(texto) {
  return texto
    .split("\n")
    .map((linha) => linha.replace(/[ \t]+/g, " ").trim())
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

/**
 * Converte o miolo de um <p class="text"> em texto limpo.
 *
 * O conteúdo do site não usa <ul>/<li>: as listas foram escritas à mão com <br /> como
 * separador e <strong> como rótulo do item ("<strong>Sistema circulatório:</strong> aberto...").
 * Remover as tags sem tratar isso gruda as frases e destrói a estrutura — que é justamente
 * a parte mais aproveitável para gerar questões. Por isso:
 *   <br />           -> quebra de linha
 *   <strong>X: </strong> -> "**X:** " (rótulo preservado como negrito Markdown)
 */
function limparParagrafo(html) {
  // Os HTMLs foram formatados por um editor, então o texto vem quebrado no meio das
  // frases pela indentação ("A região anterior do TND se\n  dilata..."). Essas quebras
  // são cosméticas e precisam sumir; as quebras de <br /> são semânticas e precisam ficar.
  // Marcamos as de <br /> com um sentinela antes de colapsar todo o resto.
  const QUEBRA = "\u0001";

  let texto = html.replace(/<br\s*\/?>/gi, QUEBRA);

  // <strong> vira rótulo em negrito; o espaço que costuma ficar dentro da tag sai para fora.
  // O `\s*` antes do `>` de fechamento não é decoração: o formatador de código quebrou
  // várias tags como `</strong\n              >`, e sem essa tolerância os rótulos
  // "Fatores que influenciam:" e "Zona abissal:" saíam sem marcação.
  texto = texto.replace(/<strong[^>]*>([\s\S]*?)<\/strong\s*>/gi, (_, miolo) => {
    const limpo = miolo.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
    return limpo ? `**${limpo}** ` : "";
  });

  // Qualquer outra tag some.
  texto = texto.replace(/<[^>]+>/g, " ");
  texto = decodificarEntidades(texto);

  // Agora sim: todo espaço em branco vira um espaço só — inclusive as quebras cosméticas.
  texto = texto.replace(/\s+/g, " ");

  // O sentinela volta a ser quebra de linha; itens ganham hífen normalizado.
  return texto
    .split(QUEBRA)
    .map((linha) => linha.replace(/\s+/g, " ").trim().replace(/^-\s*/, "- "))
    .filter((linha) => linha !== "" && linha !== "-" && linha !== "**")
    .join("\n");
}

/** Remove marcação Markdown e quebras para contar apenas caracteres de prosa. */
function contarProsa(texto) {
  return texto
    .replace(/^##\s+.*$/gm, "")
    .replace(/\*\*/g, "")
    .replace(/^-\s*/gm, "")
    .replace(/\s+/g, " ")
    .trim().length;
}

// ---------------------------------------------------------------------------
// Extração de um tópico
// ---------------------------------------------------------------------------

/**
 * Recorta o bloco de conteúdo teórico: de `<div class="content">` até `<div class="bottom-spacing">`.
 * Esse recorte é estável nos 21 arquivos (verificado na Fase 0).
 */
function recortarConteudo(html, arquivo) {
  const inicio = html.indexOf('class="content"');
  if (inicio === -1) {
    throw new Error(`${arquivo}: não encontrei <div class="content">`);
  }
  const restante = html.slice(inicio);
  const fim = restante.indexOf("bottom-spacing");
  if (fim === -1) {
    throw new Error(`${arquivo}: não encontrei o marcador bottom-spacing`);
  }
  const bloco = restante.slice(0, fim);
  const linhaInicial = html.slice(0, inicio).split("\n").length;
  const linhaFinal = linhaInicial + bloco.split("\n").length - 1;
  return { bloco, linhas: `${linhaInicial}-${linhaFinal}` };
}

/**
 * Percorre o bloco em ordem de documento e devolve as seções.
 * Texto que aparece antes do primeiro <h2> entra numa seção sem título.
 */
function extrairSecoes(bloco) {
  const secoes = [];
  let atual = { titulo: null, paragrafos: [], ilustracoes: [] };

  // Três variações de contêiner de texto convivem no site e todas contam:
  //   <p class="text">          o caso normal (113 ocorrências)
  //   <p lass="text">           erro de digitação em filo-cordados.html:155 — por isso o
  //                             padrão aceita qualquer <p>, e não só os que têm class="text"
  //   <div class="list-item">   usado nos tópicos de Ecossistemas (11 ocorrências)
  // Deixar qualquer uma de fora descarta conteúdo real: só o list-item responde por
  // mais de metade do texto de mundo-vivo-ecologia.
  const padrao =
    /<h2[^>]*>([\s\S]*?)<\/h2\s*>|<p[^>]*>([\s\S]*?)<\/p\s*>|<div[^>]*class="list-item"[^>]*>([\s\S]*?)<\/div\s*>|<img\b([^>]*)>/gi;
  let achado;

  while ((achado = padrao.exec(bloco)) !== null) {
    const [, tituloBruto, paragrafoP, paragrafoDiv, atributosImg] = achado;
    const paragrafoBruto = paragrafoP !== undefined ? paragrafoP : paragrafoDiv;

    if (tituloBruto !== undefined) {
      if (atual.titulo !== null || atual.paragrafos.length || atual.ilustracoes.length) {
        secoes.push(atual);
      }
      const titulo = colapsarEspacos(
        decodificarEntidades(tituloBruto.replace(/<[^>]+>/g, " "))
      ).replace(/\s+/g, " ");
      atual = { titulo, paragrafos: [], ilustracoes: [] };
    } else if (paragrafoBruto !== undefined) {
      const texto = limparParagrafo(paragrafoBruto);
      if (texto) atual.paragrafos.push(texto);
    } else if (atributosImg !== undefined) {
      const alt = (atributosImg.match(/alt="([^"]*)"/i) || [])[1];
      if (alt && alt.trim()) atual.ilustracoes.push(alt.trim());
    }
  }

  if (atual.titulo !== null || atual.paragrafos.length || atual.ilustracoes.length) {
    secoes.push(atual);
  }
  return secoes;
}

/**
 * Monta os conceitos-chave a partir do que o próprio site marcou como importante:
 * os títulos de seção e os rótulos em <strong>. Nada é inventado nem inferido.
 *
 * É uma heurística, não um glossário curado. Serve para dois usos, ambos tolerantes
 * a ruído: alimentar `conceitosExcluir` (variar as perguntas entre tentativas) e dar
 * um teto ao número de questões. A checagem anti-alucinação da Fase 2 compara contra
 * o `conteudo` completo, não contra esta lista.
 */
function extrairConceitos(secoes, tituloDoTopico) {
  const conceitos = [];
  const vistos = new Set();
  const tituloNormalizado = normalizar(tituloDoTopico || "");

  function adicionar(bruto) {
    const limpo = bruto.replace(/[:;.\s]+$/, "").replace(/\s+/g, " ").trim();
    if (limpo.length < 3 || limpo.length > 60) return;

    const chave = normalizar(limpo);
    if (!chave || vistos.has(chave)) return;
    if (TITULOS_ESTRUTURAIS.has(chave)) return;

    // O próprio nome do tópico não é um conceito avaliável dentro dele.
    if (chave === tituloNormalizado) return;

    // Rótulos que introduzem uma lista ("Classificação quanto à luminosidade:",
    // "Quanto à temperatura:") são estrutura do texto, não termo a ser cobrado.
    if (/^(classificacao )?quanto a/.test(chave)) return;

    // Frase longa é enunciado, não conceito ("As águas lênticas podem ser classificadas em").
    if (chave.split(" ").length > 6) return;

    vistos.add(chave);
    conceitos.push(limpo);
  }

  for (const secao of secoes) {
    if (secao.titulo) adicionar(secao.titulo);
    for (const paragrafo of secao.paragrafos) {
      for (const achado of paragrafo.matchAll(/\*\*([^*]+)\*\*/g)) {
        adicionar(achado[1].replace(/^-\s*/, ""));
      }
    }
  }
  return conceitos;
}

/**
 * Decide quantas questões esse tópico comporta.
 *
 * Três limites, e vale o menor deles:
 *   1. volume de texto   — caracteres de prosa / CARACTERES_POR_QUESTAO
 *   2. seções com texto  — não dá para fazer mais perguntas do que assuntos escritos
 *   3. conceitos-chave   — cada questão avalia um conceito distinto
 * Mais o teto absoluto de MAXIMO_QUESTOES e o piso de MINIMO_ABSOLUTO caracteres.
 *
 * Abaixo do piso, o resultado é 0: o tópico fica no quiz fixo. Preferimos entregar
 * menos questões (ou nenhuma gerada) a pedir que o modelo preencha lacunas sozinho.
 */
function calcularCapacidade(caracteres, secoesComTexto, totalConceitos) {
  if (caracteres < PARAMETROS.MINIMO_ABSOLUTO) {
    return {
      maxQuestoes: 0,
      suficiencia: "insuficiente",
      limitadoPor: "volume de texto abaixo do mínimo",
    };
  }

  const porTexto = Math.floor(caracteres / PARAMETROS.CARACTERES_POR_QUESTAO);
  const candidatos = [
    { valor: porTexto, motivo: "volume de texto" },
    { valor: secoesComTexto, motivo: "seções com texto" },
    { valor: totalConceitos, motivo: "conceitos-chave distintos" },
    { valor: PARAMETROS.MAXIMO_QUESTOES, motivo: "teto configurado" },
  ];
  const vencedor = candidatos.reduce((a, b) => (b.valor < a.valor ? b : a));

  return {
    maxQuestoes: Math.max(0, vencedor.valor),
    suficiencia: vencedor.valor >= 3 ? "adequado" : "limitado",
    limitadoPor: vencedor.motivo,
  };
}

/** Extrai um tópico inteiro a partir do caminho do HTML. */
function extrairTopico(modulo, nomeArquivo) {
  const caminhoRelativo = `${modulo.pastaTopicos}/${nomeArquivo}`;
  const html = fs.readFileSync(path.join(RAIZ, caminhoRelativo), "utf8");

  const titulo =
    (html.match(/class="header-title"[^>]*>([^<]*)/) || [])[1]?.trim() ||
    nomeArquivo.replace(/\.html$/, "");

  const { bloco, linhas } = recortarConteudo(html, caminhoRelativo);
  const secoes = extrairSecoes(bloco);

  // Texto final entregue à LLM: cabeçalhos de seção + parágrafos, em ordem.
  // As imagens NÃO entram aqui de propósito — o `alt` fica em `ilustracoes`, como
  // metadado. Se o texto da ilustração entrasse no conteúdo, o modelo poderia
  // formular perguntas sobre algo que o aluno só vê na figura.
  const partes = [];
  for (const secao of secoes) {
    if (secao.titulo) partes.push(`## ${secao.titulo}`);
    for (const paragrafo of secao.paragrafos) partes.push(paragrafo);
  }
  const conteudo = partes.join("\n\n").trim();

  const assuntos = secoes.filter((s) => s.titulo).map((s) => s.titulo);
  const ilustracoes = [...new Set(secoes.flatMap((s) => s.ilustracoes))];
  const conceitosChave = extrairConceitos(secoes, titulo);

  const caracteres = contarProsa(conteudo);
  const palavras = conteudo ? conteudo.replace(/\s+/g, " ").trim().split(" ").length : 0;
  const secoesComTexto = secoes.filter(
    (s) => contarProsa(s.paragrafos.join("\n")) >= PARAMETROS.MINIMO_POR_SECAO
  ).length;

  const capacidade = calcularCapacidade(caracteres, secoesComTexto, conceitosChave.length);

  return {
    id: nomeArquivo.replace(/\.html$/, ""),
    dados: {
      titulo,
      assuntos,
      conteudo,
      conceitosChave,
      ilustracoes,
      nivel: "ensino_medio",
      metricas: {
        caracteres,
        palavras,
        secoes: assuntos.length,
        secoesComTexto,
        ilustracoes: ilustracoes.length,
        conceitos: conceitosChave.length,
      },
      maxQuestoes: capacidade.maxQuestoes,
      suficiencia: capacidade.suficiencia,
      limitadoPor: capacidade.limitadoPor,
      origem: { arquivo: caminhoRelativo, linhas },
    },
  };
}

// ---------------------------------------------------------------------------
// Ordem dos tópicos: a mesma da página do módulo
// ---------------------------------------------------------------------------
function lerOrdemDosTopicos(modulo) {
  const html = fs.readFileSync(path.join(RAIZ, modulo.paginaModulo), "utf8");
  const encontrados = [...html.matchAll(/href="\.\/topicos\/[a-z-]+\/([a-z-]+\.html)"/g)].map(
    (m) => m[1]
  );
  const ordem = [...new Set(encontrados)];

  // Rede de segurança: se algum tópico existir na pasta mas não estiver linkado na
  // página do módulo, ele entra no fim em vez de sumir da base silenciosamente.
  const naPasta = fs
    .readdirSync(path.join(RAIZ, modulo.pastaTopicos))
    .filter((f) => f.endsWith(".html"));
  for (const arquivo of naPasta) {
    if (!ordem.includes(arquivo)) {
      console.warn(`  aviso: ${arquivo} não está linkado em ${modulo.paginaModulo}`);
      ordem.push(arquivo);
    }
  }
  return ordem;
}

// ---------------------------------------------------------------------------
// Serialização
// ---------------------------------------------------------------------------

/**
 * Gera o arquivo .js. É .js e não .json de propósito: um .json exigiria fetch(),
 * que falha em file://. Um .js carregado por <script> funciona em qualquer situação.
 */
function serializar(base, resumo) {
  const cabecalho = [
    "// Base de conhecimento extraída do conteúdo do site.",
    "// Gerada por scripts/extrair-conteudo.js — NÃO EDITAR À MÃO.",
    "//",
    "// Para regenerar, a partir da raiz do projeto:  node scripts/extrair-conteudo.js",
    "//",
    `// Tópicos: ${resumo.topicos} | caracteres de prosa: ${resumo.caracteres} | ` +
      `com IA habilitável: ${resumo.comIA} | somente quiz fixo: ${resumo.semIA}`,
    "//",
    "// Arquivo .js e não .json de propósito: .json exigiria fetch(), que quebra em file://.",
    "",
    "const BASE_CONHECIMENTO = ",
  ].join("\n");

  const rodape = [
    ";",
    "",
    "// Parâmetros usados no cálculo de maxQuestoes, expostos para a página de diagnóstico.",
    `const BASE_CONHECIMENTO_PARAMETROS = ${JSON.stringify(PARAMETROS, null, 2)};`,
    "",
  ].join("\n");

  return cabecalho + JSON.stringify(base, null, 2) + rodape;
}

// ---------------------------------------------------------------------------
// Execução
// ---------------------------------------------------------------------------
function main() {
  const apenasVerificar = process.argv.includes("--verificar");

  const base = {};
  const resumo = { topicos: 0, caracteres: 0, comIA: 0, semIA: 0, linhas: [] };

  for (const modulo of MODULOS) {
    base[modulo.id] = { titulo: modulo.titulo, topicos: {} };
    console.log(`\n[${modulo.titulo}]`);

    for (const arquivo of lerOrdemDosTopicos(modulo)) {
      const { id, dados } = extrairTopico(modulo, arquivo);
      base[modulo.id].topicos[id] = dados;

      resumo.topicos += 1;
      resumo.caracteres += dados.metricas.caracteres;
      if (dados.maxQuestoes > 0) resumo.comIA += 1;
      else resumo.semIA += 1;
      resumo.linhas.push({ modulo: modulo.titulo, id, ...dados.metricas, maxQuestoes: dados.maxQuestoes, suficiencia: dados.suficiencia, limitadoPor: dados.limitadoPor });

      const alerta = dados.maxQuestoes === 0 ? "  <-- SEM IA (quiz fixo)" : "";
      console.log(
        `  ${id.padEnd(26)} ${String(dados.metricas.caracteres).padStart(5)} car.` +
          ` | ${dados.metricas.secoesComTexto}/${dados.metricas.secoes} seções com texto` +
          ` | ${String(dados.metricas.conceitos).padStart(2)} conceitos` +
          ` | max ${dados.maxQuestoes} questões${alerta}`
      );
    }
  }

  const saida = serializar(base, resumo);

  if (apenasVerificar) {
    const atual = fs.existsSync(SAIDA) ? fs.readFileSync(SAIDA, "utf8") : "";
    console.log(
      atual === saida
        ? "\n[--verificar] base-conhecimento.js está em dia."
        : "\n[--verificar] base-conhecimento.js está DESATUALIZADO. Rode sem --verificar."
    );
    process.exitCode = atual === saida ? 0 : 1;
    return;
  }

  fs.mkdirSync(path.dirname(SAIDA), { recursive: true });
  fs.writeFileSync(SAIDA, saida, "utf8");

  console.log(
    `\nGravado: dados/base-conhecimento.js` +
      `\n  ${resumo.topicos} tópicos | ${resumo.caracteres} caracteres de prosa` +
      `\n  ${resumo.comIA} com IA habilitável | ${resumo.semIA} restritos ao quiz fixo`
  );

  // Tabela para colar em docs/01-EXTRACAO.md
  if (process.argv.includes("--tabela")) {
    console.log("\n--- tabela markdown ---");
    for (const l of resumo.linhas) {
      console.log(
        `| ${l.modulo} | \`${l.id}\` | ${l.caracteres} | ${l.palavras} | ` +
          `${l.secoesComTexto}/${l.secoes} | ${l.conceitos} | **${l.maxQuestoes}** | ${l.suficiencia} | ${l.limitadoPor} |`
      );
    }
  }
}

main();
