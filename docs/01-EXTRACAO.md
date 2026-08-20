# Fase 1 — Extração do conteúdo e base de conhecimento

> Entregáveis desta fase:
> - `scripts/extrair-conteudo.js` — script de desenvolvimento (Node), **não faz parte do site**
> - `dados/base-conhecimento.js` — arquivo gerado, é o que a camada de IA vai ler
> - este relatório
>
> Nenhum arquivo do site original foi alterado. Verificado com `git status` ao fim da fase.

---

## 1. Resultado

| Métrica | Valor |
|---|---|
| Tópicos extraídos | **21 de 21** (100% dos mapeados na Fase 0) |
| Caracteres de prosa na base | **25.649** |
| Tópicos com IA habilitável (`maxQuestoes > 0`) | **16** |
| Tópicos restritos ao quiz fixo (`maxQuestoes = 0`) | **5** |
| Teto total de questões geradáveis | 44 |
| Tamanho de `dados/base-conhecimento.js` | 57 KB, UTF-8 sem BOM |
| Reexecução do script | idempotente (`--verificar` confirma) |

Nenhum tópico ficou com conteúdo vazio e todos os 21 campos `origem.arquivo` apontam para
arquivos que existem no disco.

---

## 2. Por que os números diferem da Fase 0

A Fase 0 mediu **28.688** caracteres; a Fase 1 registra **25.649**. Não há conteúdo perdido —
as duas contas medem coisas diferentes:

| Parcela | Caracteres |
|---|---|
| Prosa (o que a métrica `caracteres` conta) | 25.649 |
| Títulos de seção `## …` (continuam dentro de `conteudo`) | 1.822 |
| Marcadores de item `- ` (continuam dentro de `conteudo`) | 374 |
| Espaços que a medição bruta da Fase 0 criou ao trocar cada tag por " " | 843 |
| **Total** | **28.688** |

A medição da Fase 0 era grosseira de propósito (trocar toda tag por espaço, contar o que sobrou),
serviu para dimensionar o problema. A da Fase 1 conta só prosa, depois da limpeza real, e é a que
alimenta o cálculo de `maxQuestoes`.

---

## 3. Tabela por tópico

`Seções` = seções com texto / seções totais. Uma seção só conta como "com texto" a partir de
80 caracteres — isso separa as seções reais das que existem apenas para segurar uma imagem.

| Módulo | Tópico | Caract. | Palavras | Seções | Conceitos | Máx. questões | Suficiência | Limitado por |
|---|---|---:|---:|:---:|---:|:---:|---|---|
| Reino Animal | `reino-animalia` | 663 | 94 | 2/3 | 12 | **1** | limitado | volume de texto |
| Reino Animal | `filo-poriferos` | 852 | 132 | 3/5 | 12 | **2** | limitado | volume de texto |
| Reino Animal | `filo-cnidarios` | 668 | 115 | 3/6 | 10 | **1** | limitado | volume de texto |
| Reino Animal | `filo-platelmintos` | 531 | 90 | 2/4 | 6 | **0** | insuficiente | abaixo do mínimo |
| Reino Animal | `filo-nematelmintos` | 581 | 99 | 2/5 | 9 | **0** | insuficiente | abaixo do mínimo |
| Reino Animal | `filo-moluscos` | 645 | 104 | 2/5 | 9 | **1** | limitado | volume de texto |
| Reino Animal | `filo-anelideos` | 573 | 82 | 2/2 | 6 | **0** | insuficiente | abaixo do mínimo |
| Reino Animal | `filo-artropodes` | 1.032 | 153 | 2/5 | 11 | **2** | limitado | volume de texto |
| Reino Animal | `filo-equinodermos` | 733 | 117 | 2/4 | 9 | **2** | limitado | volume de texto |
| Reino Animal | **`filo-cordados`** ⭐ | **4.675** | 797 | 13/14 | 15 | **5** | adequado | teto configurado |
| Plantas | `reino-plantae` | 757 | 121 | 2/2 | 3 | **2** | limitado | volume de texto |
| Plantas | `briofitas` | 766 | 116 | 3/3 | 3 | **2** | limitado | volume de texto |
| Plantas | `pteridofitas` | 897 | 137 | 2/3 | 4 | **2** | limitado | volume de texto |
| Plantas | `gimnospermas` | 406 | 60 | 1/2 | 1 | **0** | insuficiente | abaixo do mínimo |
| Plantas | `angiospermas` | 209 | 64 | 1/6 | 5 | **0** | insuficiente | abaixo do mínimo |
| Ecossistemas | `definicao-e-componentes` | 976 | 155 | 4/4 | 8 | **2** | limitado | volume de texto |
| Ecossistemas | `ecossistemas-da-terra` | 1.996 | 285 | 5/5 | 25 | **5** | adequado | volume de texto |
| Ecossistemas | `mundo-vivo-ecologia` | 980 | 180 | 4/4 | 9 | **2** | limitado | volume de texto |
| Ecossistemas | `fluxo-de-energia` | 3.047 | 496 | 5/5 | 19 | **5** | adequado | seções com texto |
| Ecossistemas | `sucessao-ecologica` | 1.985 | 306 | 5/5 | 15 | **5** | adequado | volume de texto |
| Ecossistemas | `piramides-ecologicas` | 2.677 | 447 | 4/5 | 4 | **4** | adequado | seções com texto |

⭐ = tópico piloto.

---

## 4. Alerta: tópicos com pouco conteúdo

O roteiro pede alerta para tópicos abaixo de ~800 caracteres. São **11 dos 21** — mais da metade:

| Tópico | Caract. | Situação | O que acontece na prática |
|---|---:|---|---|
| `angiospermas` | 209 | 🔴 insuficiente | 5 das 6 seções são só imagem. Quiz fixo |
| `gimnospermas` | 406 | 🔴 insuficiente | Quiz fixo |
| `filo-platelmintos` | 531 | 🔴 insuficiente | Quiz fixo |
| `filo-anelideos` | 573 | 🔴 insuficiente | Quiz fixo |
| `filo-nematelmintos` | 581 | 🔴 insuficiente | Quiz fixo |
| `filo-moluscos` | 645 | 🟡 limitado | 1 questão gerada, no máximo |
| `reino-animalia` | 663 | 🟡 limitado | 1 questão |
| `filo-cnidarios` | 668 | 🟡 limitado | 1 questão |
| `filo-equinodermos` | 733 | 🟡 limitado | 2 questões |
| `reino-plantae` | 757 | 🟡 limitado | 2 questões |
| `briofitas` | 766 | 🟡 limitado | 2 questões |

O caso mais ilustrativo é **Angiospermas**: o tópico tem 6 seções, mas só a primeira tem texto.
As outras cinco — Estrutura da Flor, Ciclo Reprodutivo, Tipos de Corola, Tipos de Inflorescência
e Classificação dos Frutos Simples — são títulos seguidos apenas de imagem. Extraído, o tópico vira:

```
## Características
- **Flores e frutos:** aquisições evolutivas;
- Raiz, caule, folha, flor, semente e fruto; - Flores: cor, forma, cheiro e néctar;
- Polinização;
- Frutos: contém e protegem as sementes e auxiliam na dispersão na natureza.

## Estrutura da Flor

## Ciclo Reprodutivo

## Tipos de Corola (Conjunto de Pétalas)

## Tipos de Inflorescência (Conjunto de Flores)

## Classificação dos Frutos Simples
```

Pedir 5 questões daí seria pedir para o modelo escrever Botânica do próprio repertório. Por isso o
tópico sai da IA e continua com o quiz fixo — conforme a decisão de não enriquecer o conteúdo agora.

---

## 5. Como `maxQuestoes` é calculado

Regra implementada em `calcularCapacidade()`. Vale o **menor** de quatro limites:

| Limite | Fórmula | Justificativa |
|---|---|---|
| Volume de texto | `caracteres / 350` | O site tem 97 seções `<h2>` para 28.688 caracteres, ou **~296 caracteres por seção** (medido, não estimado). 350 arredonda para cima, ficando do lado conservador |
| Seções com texto | contagem direta | Não dá para perguntar sobre mais assuntos do que os que estão escritos |
| Conceitos-chave | contagem direta | Cada questão avalia um conceito distinto; sem conceito sobrando, a próxima questão repete ou inventa |
| Teto | 5 | Limite de tamanho do quiz |

E um piso: **abaixo de 600 caracteres, o resultado é 0** — o tópico fica fora da IA. 600 é o
equivalente a duas seções de texto do próprio site.

O campo `limitadoPor` grava qual dos quatro limites venceu em cada tópico. Isso vai direto para a
página de diagnóstico da Fase 4 e para o relatório: dá para mostrar *por que* um tópico rende menos
questões, em vez de só afirmar que rende.

Os quatro parâmetros ficam expostos no arquivo gerado, em `BASE_CONHECIMENTO_PARAMETROS`, para
poderem ser exibidos e discutidos sem abrir o código do extrator.

---

## 6. Formato da base

```js
const BASE_CONHECIMENTO = {
  "animais": {                              // id do módulo = pasta topicos-animais
    titulo: "Reino Animal",
    topicos: {
      "filo-cordados": {                    // id do tópico = nome do arquivo HTML
        titulo: "Filo dos Cordados",        // vindo do .header-title da página
        assuntos: ["Notocorda", "Fendas Faríngeas", ...],   // os <h2> na ordem
        conteudo: "## Filo dos Cordados\n\nFilo com animais mais complexos...",
        conceitosChave: ["Notocorda", "Ciclóstomas", "Condrictes", ...],
        ilustracoes: ["Morfologia Cordado", "Lampreia", ...],  // alt das imagens (metadado)
        nivel: "ensino_medio",
        metricas: { caracteres: 4675, palavras: 797, secoes: 14,
                    secoesComTexto: 13, ilustracoes: 11, conceitos: 15 },
        maxQuestoes: 5,
        suficiencia: "adequado",            // adequado | limitado | insuficiente
        limitadoPor: "teto configurado",
        origem: { arquivo: "pages/modulos/topicos/topicos-animais/filo-cordados.html",
                  linhas: "47-287" }
      }
    }
  }
};
```

Diferenças em relação ao esqueleto do roteiro, e por quê:

| Campo | Motivo |
|---|---|
| `ilustracoes` (novo) | Guarda o `alt` das imagens **fora** de `conteudo`, de propósito. Se o texto da figura entrasse no material, o modelo poderia formular pergunta sobre algo que só existe na imagem. Fica como metadado, e serve para explicar por que um tópico tem tanta seção e tão pouco texto |
| `metricas`, `maxQuestoes`, `suficiencia`, `limitadoPor` (novos) | Implementam a decisão de calcular a quantidade de questões a partir do conteúdo disponível. Ficam pré-calculados no arquivo para a camada de IA só consultar |
| ids de módulo e tópico | `animais` / `filo-cordados`, derivados do caminho no disco — a mesma regra que a Fase 3 vai usar sobre `location.pathname`. Evita as chaves acentuadas do LocalStorage (riscos R4 e R5 da Fase 0) |
| `.js` e não `.json` | Conforme o roteiro: `.json` exigiria `fetch()`, que quebra em `file://` |

---

## 7. Decisões de limpeza do HTML

O conteúdo não usa `<ul>`/`<li>`: as listas foram escritas à mão com `<br />` como separador e
`<strong>` como rótulo. Descartar essa marcação destruiria justamente a parte mais aproveitável.
As regras aplicadas:

| Marcação de origem | Vira | Por quê |
|---|---|---|
| `<h2 class="section-title">X</h2>` | `## X` | Delimita o assunto para o modelo |
| `<br />` | quebra de linha | É o separador de item real do site |
| quebra de linha da indentação | espaço | Cosmética do formatador de código. Sem esse tratamento saía `"A região anterior do TND se\ndilata"`, com frases partidas no meio |
| `<strong>Rótulo: </strong>valor` | `**Rótulo:** valor` | Preserva a estrutura rótulo/valor, que é onde estão as definições |
| `<img alt="X">` | vai para `ilustracoes` | Não entra no material de geração (§6) |

---

## 8. Três defeitos do site encontrados durante a extração

Registrados, **não corrigidos** — a regra 1 do roteiro proíbe reescrever o site, e nenhum deles
impede a extração. Complementam os 14 riscos da Fase 0.

| # | Defeito | Onde | Como apareceu |
|---|---|---|---|
| **R15** | `<p lass="text">` — falta o `c` de `class`. O parágrafo renderiza sem o estilo `.text` | `pages/modulos/topicos/topicos-animais/filo-cordados.html:155` | O extrator, que filtrava por `class="text"`, perdia esse parágrafo. Justamente no tópico piloto. Passou a aceitar qualquer `<p>` dentro do bloco de conteúdo |
| **R16** | Terceiro contêiner de texto não documentado: `<div class="list-item">`, 11 ocorrências em 3 tópicos de Ecossistemas | `definicao-e-componentes`, `fluxo-de-energia`, `mundo-vivo-ecologia` | Ignorá-lo custava mais da metade do texto de `mundo-vivo-ecologia` (408 → 980 caracteres depois da correção) |
| **R17** | Tags de fechamento quebradas em duas linhas pelo formatador (`</strong\n              >`) | vários tópicos, com destaque para `ecossistemas-da-terra` | Rótulos como "Zona abissal:" e "Fatores que influenciam:" saíam sem marcação. Os regex passaram a tolerar espaço antes do `>` |

Os três só apareceram porque a saída foi **lida**, não apenas gerada. Vale registrar isso no
relatório final: a primeira versão da extração rodou sem erro e mesmo assim estava perdendo
conteúdo em 4 dos 21 tópicos.

---

## 9. Tópico piloto: `filo-cordados`

Confirmado como a melhor escolha, pelos números medidos:

| | `filo-cordados` | `filo-artropodes` (sugestão original do roteiro) |
|---|---:|---:|
| Caracteres de prosa | **4.675** | 1.032 |
| Seções com texto | **13 de 14** | 2 de 5 |
| Conceitos-chave | **15** | 11 |
| Máximo de questões | **5** | 2 |

Artrópodes tem 6 imagens e 3 seções sem nenhum texto (Classe Insecta, Classe Crustacea,
Classe Arachnida são só figura), o que o deixa no limite. Cordados é o único tópico do site que
permite avaliar a geração com o quiz cheio.

---

## 10. Como regenerar

```bash
node scripts/extrair-conteudo.js              # regenera dados/base-conhecimento.js
node scripts/extrair-conteudo.js --verificar  # não escreve; diz se está desatualizado (sai 1 se estiver)
node scripts/extrair-conteudo.js --tabela     # imprime a tabela da §3 pronta para colar
```

O script roda em Node puro, sem nenhuma dependência: só `fs` e `path`. Precisa ser rodado de novo
sempre que o conteúdo de algum HTML de tópico mudar — o site em execução nunca o chama.

---

## 11. Critério de aceite

> "100% dos tópicos da Fase 0 estão na base, com texto utilizável."

- **21 de 21 tópicos** na base, nenhum faltando, nenhum sobrando, nenhum com `conteudo` vazio —
  verificado por script contra os HTMLs no disco.
- "Texto utilizável" foi tratado como algo a medir, não a afirmar: 16 tópicos têm texto suficiente
  para gerar questões e **5 não têm**. Esses 5 estão nomeados na §4 e continuam com o quiz fixo,
  em vez de receberem questões inventadas.

**Estado do repositório:** nenhum arquivo do site foi criado, alterado ou removido nesta fase.
Acréscimos: `scripts/extrair-conteudo.js`, `dados/base-conhecimento.js` e este documento.
