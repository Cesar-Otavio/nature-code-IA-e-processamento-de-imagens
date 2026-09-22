# Fase 11 — Protocolo das imagens externas

> Este protocolo foi definido **antes** de qualquer imagem externa ser processada, pelo
> mesmo motivo da Fase 2 (§15): o critério não pode se acomodar ao que se vê depois.

---

## 0. Como o protocolo foi aplicado

A avaliação foi executada com **9 imagens externas ao dataset Flavia**, **obtidas de fontes
externas** e convertidas para JPG, **selecionadas para representar condições visuais
diferentes** das do Flavia (fundo natural, céu, contraluz, várias folhas). **As imagens não
foram tiradas pela equipe.** Resultado e análise em
[`11-ROBUSTEZ-FOTOS-EXTERNAS.md`](11-ROBUSTEZ-FOTOS-EXTERNAS.md).

O protocolo original previa fotos capturadas para este fim. A tabela registra o que foi
seguido e onde a execução se afastou dele:

| Item do protocolo | Previsto | Executado |
|---|---|---|
| Quantidade (§1) | 10–15, preferência 12 | **9** |
| Origem (§4) | Fotografia real, tirada para este fim, sem edição | **Imagens de fontes externas**, convertidas para JPG; edição e compressão prévias desconhecidas |
| Cobertura das condições (§2) | Cada valor ao menos uma vez | Parcial: sem fundo escuro, luz artificial, sombra, inclinação, folha pequena |
| Formatos (§3) | JPG e, se possível, uma PNG | Só JPG |
| Uma folha principal por imagem (§4) | Sim | Sim, exceto EXT008 (ramo com várias folhas, incluída como caso de robustez) |
| Sem pessoas, textos ou dados privados (§4) | Sim | Não registrado na inspeção; as imagens não são versionadas |
| Não refazer nem remover imagens com falha (§5) | Sim | **Sim** — as 9 foram mantidas |
| Não ajustar parâmetros (§5) | Sim | **Sim** — hashes idênticos antes e depois |
| Inspeção humana de todas (§6) | Sim | **Sim** — 9/9 |
| Duas pessoas independentes (§6) | Se possível | Não registrado |

### Limitações introduzidas pela origem das imagens

- **Não houve controle de aquisição**: câmera, distância, balanço de branco e iluminação
  são desconhecidos.
- **Compressão e processamento prévios podem ser desconhecidos**: recompressão,
  redimensionamento ou filtros anteriores podem ter alterado as cores, e a segmentação do
  pipeline é por cor.
- **A avaliação é descritiva**: 9 imagens escolhidas manualmente não permitem estatística
  nem generalização.

---

## 1. Quantidade

**Entre 10 e 15 imagens. Preferência: 12.** (Executado: 9 — ver §0.)

O conjunto é pequeno de propósito: a Fase 11 não busca estatística, e sim observar o
comportamento do pipeline congelado sob condições que o Flavia não tem, com **inspeção
humana de todas as imagens**.

---

## 2. Condições a variar

A distribuição abaixo é aproximada. **Não é preciso cobrir todas as combinações**; o
importante é que cada valor apareça pelo menos uma vez.

| Dimensão | Valores (como escrever no manifesto) | O que representa |
|---|---|---|
| **Fundo** | `claro` | Papel, parede ou mesa clara — o mais próximo do Flavia |
| | `escuro` | Mesa escura, tecido escuro |
| | `colorido` | Superfície de cor forte, lisa |
| | `irregular` | Grama, terra, madeira com veios, piso texturizado |
| **Iluminação** | `natural` | Luz do dia, sem sol direto duro |
| | `artificial` | Lâmpada interna |
| | `sombra` | Parte da folha ou do fundo sob sombra marcada |
| | `desigual` | Um lado muito mais claro que o outro, reflexo, contraluz |
| **Posição** | `centralizada` | Folha no centro |
| | `inclinada` | Folha girada em relação ao quadro |
| | `proxima_borda` | Folha perto de uma borda da foto |
| | `deslocada` | Folha parcialmente fora do centro, sem tocar a borda |
| **Distância** | `grande` | A folha ocupa grande parte da imagem |
| | `media` | Distância intermediária |
| | `pequena` | A folha é pequena no quadro |

### Sugestão para 12 fotos

| Faixa | Fotos | Condição |
|---|---:|---|
| Referência | 2 | Fundo `claro`, luz `natural`, `centralizada`, `media` |
| Fundo | 4 | Uma de cada: `escuro`, `colorido`, `irregular` (×2, por exemplo grama e madeira) |
| Iluminação | 3 | `artificial`, `sombra`, `desigual` |
| Posição e distância | 3 | `inclinada`, `proxima_borda` com distância `grande`, `deslocada` com distância `pequena` |

As fotos podem combinar condições; o manifesto registra todas.

---

## 3. Formatos

| Formato | Pedido |
|---|---|
| **JPG/JPEG** | A maioria — é o que o celular gera. **Pelo menos uma foto JPEG de celular, sem conversão** |
| **PNG** | **Pelo menos uma**, se possível (por exemplo, exportada sem edição de conteúdo) |

Formatos fora de `.jpg`, `.jpeg` e `.png` são recusados pelo manifesto. HEIC, padrão em
alguns iPhones, não é suportado pelo pipeline: configure a câmera para JPEG ou converta
sem editar a imagem.

---

## 4. Regras de captura

> Regras escritas para a captura planejada. Na execução, as imagens vieram de fontes
> externas; as divergências estão na §0.

Cada foto **deve**:

- conter **uma folha principal**;
- ser uma fotografia real, tirada para este fim;
- ser usada como saiu da câmera, sem recorte de conteúdo, filtro ou retoque.

Cada foto **não pode** conter:

- rostos, pessoas identificáveis ou partes do corpo em destaque;
- documentos, telas, placas ou qualquer texto pessoal;
- informação privada de qualquer tipo.

**Evitar propositalmente:** colagens, capturas de tela, imagens artificiais e imagens
geradas por IA.

**Não é necessário saber a espécie.** O pipeline não identifica espécies, e o manifesto
não tem coluna para isso.

> **Privacidade:** fotos de celular podem conter localização GPS nos metadados. Como as
> fotos **não são versionadas**, elas não saem da máquina de quem avalia; ainda assim,
> desative a localização da câmera antes de fotografar, se possível.

---

## 5. O que NÃO fazer depois de ver os resultados

- Não refazer uma foto porque o resultado ficou ruim. A foto ruim é o dado.
- Não remover fotos com falha.
- Não ajustar HSV, Gaussiano, morfologia, contornos, features, limiares ou regras.

Se, mais tarde, a equipe decidir melhorar o pipeline, isso é **outra fase**, com
desenvolvimento explícito e novo conjunto de avaliação — nunca uma correção silenciosa
feita em cima destas fotos.

---

## 6. Inspeção humana

Toda foto processada é inspecionada por uma pessoa, olhando as imagens intermediárias,
principalmente `05-mascara-limpa.png` e `07-final.png`.

| Pergunta | Coluna | Valores |
|---|---|---|
| A folha principal foi segmentada? | `folha_principal_segmentada` | `sim` · `parcial` · `nao` |
| A máscara corresponde visualmente à folha? | `mascara_visual_adequada` | `sim` · `parcial` · `nao` |
| O contorno acompanha a borda real? | `contorno_visual_adequado` | `sim` · `parcial` · `nao` |
| As medidas são utilizáveis? | `resultado_util` | `sim` · `parcial` · `nao` |
| Qual o problema principal? | `problema_principal` | categoria da tabela abaixo |
| Observações | `observacao_humana` | texto livre |

### Categorias de problema

| Categoria | Quando usar |
|---|---|
| `fundo confundido com folha` | Parte do fundo entrou na máscara |
| `folha parcialmente perdida` | Parte da folha ficou fora da máscara |
| `sombra incorporada` | A sombra foi tratada como folha |
| `objeto secundario incorporado` | Outro objeto (galho, outra folha, pedra) entrou no objeto medido |
| `folha fragmentada` | A máscara quebrou a folha em pedaços |
| `folha nao detectada` | O pipeline não encontrou a folha (inclui erro `E007`) |
| `contorno inadequado` | A máscara é razoável, mas o contorno selecionado não representa a folha |
| `recorte pela borda` | A folha estava cortada pela borda da foto |
| `cor fora da faixa` | A folha não é verde o bastante para a faixa HSV (seca, avermelhada, variegada) |
| `resultado adequado` | Nenhum problema relevante |
| `outro` | Explicar em `observacao_humana` |

**Como decidir entre `sim`, `parcial` e `nao`** — mesmo critério da Fase 2 §15:

| Valor | Critério |
|---|---|
| `sim` | Cobre a folha inteira, borda acompanha o contorno real, sem fundo, sombra ou artefato |
| `parcial` | Essencialmente certo, com desvios pequenos e localizados; medidas utilizáveis com ressalva |
| `nao` | Objeto errado, parte significativa perdida, fundo ou sombra incorporados, máscara fragmentada ou nada detectado |

**Se possível, duas pessoas inspecionam de forma independente** e registram as
divergências em `observacao_humana`.
