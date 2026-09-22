# Fase 11 — Robustez com fotos externas

```text
Status: avaliação externa executada e inspecionada manualmente.
```

> **Resultado em uma frase:** o pipeline processou **9 de 9** imagens externas sem erro,
> mas a inspeção humana considerou **0 resultados totalmente adequados, 2 parciais e 7
> inadequados**.
>
> **Esta fase não é desenvolvimento.** É uma avaliação de robustez do pipeline congelado
> em `fase-9-completa`. Nenhum parâmetro foi ajustado com base nas imagens externas —
> antes, durante ou depois da execução, e nem depois da inspeção.

> **100 % de processamento ≠ 100 % de segmentação correta.** *Sucesso operacional*
> significa apenas que o pipeline chegou ao fim com um objeto medido, sem erro. Ele não diz
> se o objeto medido é a folha. Isso só a inspeção humana verifica — e, nesta fase, ela
> mostrou que na maior parte dos casos **não era**.

---

## 1. Objetivo

Observar como o pipeline congelado se comporta **fora do ambiente controlado do Flavia**,
com imagens de folhas externas ao dataset:

- se ele chega ao fim (sucesso operacional) ou falha, e com que erro;
- que avisos emite;
- se o objeto que ele mede é de fato a folha — julgado por **inspeção humana**;
- como isso varia com fundo, iluminação, posição e distância.

---

## 2. Motivação

A Fase 10 processou 96 de 96 imagens reservadas do Flavia sem erro. Esse resultado vale
para **o Flavia**: folhas isoladas, fundo branco, iluminação controlada, mesma câmera. A
própria Fase 10 registrou como ameaça à validade que *"100 % de processamento válido aqui
não prediz o desempenho com fotos de celular"*.

A Fase 11 existe para testar exatamente essa lacuna, com o mesmo algoritmo, e registrar o
que acontecer — inclusive, e principalmente, as falhas.

---

## 3. Imagens avaliadas

| Item | Valor |
|---|---|
| Quantidade | **9 imagens** |
| Origem | **Externas ao dataset Flavia**, obtidas de fontes externas e convertidas para JPG |
| Uso anterior | **Nenhum** — não foram usadas em nenhuma fase de desenvolvimento, calibração ou avaliação anterior |
| Seleção | Escolhidas para representar condições visuais diferentes das do Flavia (fundo natural, céu, contraluz, várias folhas) |
| Formato | JPG, 332–408 × 234–252 px |
| Versionamento | **Não versionadas** — `processamento-imagens/fotos-externas/imagens/` é ignorada pelo Git |

As imagens **não foram tiradas pela equipe**. Não houve controle sobre câmera, aquisição,
compressão ou processamento anterior à conversão (ver §13).

### Diferença entre o Flavia e as imagens externas

| Aspecto | Flavia (Fases 3–10) | Imagens externas (Fase 11) |
|---|---|---|
| Fundo | Branco, uniforme | Colorido (4), irregular (4), claro (1) — declarado no manifesto |
| Iluminação | Controlada, difusa | Natural (7), desigual (2) |
| Enquadramento | Folha centralizada, inteira | Centralizada (7), próxima da borda (1), deslocada (1) |
| Escala | Semelhante entre imagens | Média (7), grande (2) |
| Câmera | Uma, fixa | Desconhecida |
| Formato | JPEG 1600×1200 | JPG ~350×245, origem e compressão prévias desconhecidas |
| Seleção | Amostragem estratificada com semente | Seleção manual por condição visual |
| Quantidade | 96 | 9 |
| Verificação do resultado | Inspeção humana de 12 casos selecionados | **Inspeção humana de todas as 9** |

Condições **não cobertas**: fundo escuro, iluminação artificial, sombra marcada, folha
inclinada, folha pequena no quadro, PNG.

---

## 4. Pipeline congelado

| Item | Valor |
|---|---|
| Checkpoint | `fase-9-completa` → `4b66981` |
| Commit no momento da execução | `6a9ff60` (só documentação e scripts de avaliação sobre o checkpoint) |
| Parâmetros | HSV H[25,95] S≥40 V≥20 · Gaussiano 5 · lado máximo 1024 · limpeza 0,001/0,002 · limiares da Fase 8 — **todos inalterados** |
| Verificação | Antes e depois da execução, o script comparou os SHA-256 dos 9 arquivos do algoritmo com a referência da Fase 10 (`dados-avaliacao/hashes-pipeline-antes.txt`): **9 × idênticos antes, 9 × idênticos depois** ([`hashes-pipeline-antes.txt`](dados-robustez/hashes-pipeline-antes.txt), [`hashes-pipeline-depois.txt`](dados-robustez/hashes-pipeline-depois.txt)) |

### Riscos conhecidos antes da execução

Registrados **antes** das imagens, para que a análise não se acomodasse ao resultado. A
coluna da direita registra o que se observou depois.

| Propriedade do pipeline | Condição externa em que pode importar | Observado |
|---|---|---|
| A segmentação aceita só matiz H∈[25,95] com saturação ≥ 40 | Fundo verde pode entrar na máscara; folha seca, avermelhada ou variegada pode sair | **Confirmado.** Fundo natural esverdeado entrou na máscara em 5 casos; a folha amarelada (EXT003) saiu |
| Pixels com brilho V < 20 são excluídos | Folha em sombra forte pode ser perdida | Não isolado — contraluz (EXT009) combinou perda e contaminação |
| O objeto medido é o **maior** componente | Um objeto verde maior que a folha seria escolhido no lugar dela | **Confirmado.** Em EXT003 e EXT008 o objeto escolhido não é a folha de interesse |
| Calibração em fundo branco (Fase 4) | Fundos texturizados nunca foram testados | **Confirmado** — nenhum fundo não branco deu resultado adequado |
| HEIC não é suportado (Fase 9) | Fotos de iPhone em HEIC seriam recusadas | Não testado (todas em JPG) |

---

## 5. Protocolo

Definido em [`11-PROTOCOLO-FOTOS-EXTERNAS.md`](11-PROTOCOLO-FOTOS-EXTERNAS.md): condições
a variar, formatos, regras de conteúdo, o que não fazer depois de ver os resultados e o
critério da inspeção humana.

---

## 6. Manifesto

[`processamento-imagens/fotos-externas/manifesto.csv`](../../processamento-imagens/fotos-externas/manifesto.csv)
— **9 entradas**, versionado. As imagens a que ele se refere não são versionadas.

| ID | Arquivo | Fundo | Iluminação | Posição | Distância | Observação |
|---|---|---|---|---|---|---|
| EXT001 | `folha-01.jpg` | colorido | natural | centralizada | media | folha avermelhada, fundo natural desfocado |
| EXT002 | `folha-02.jpg` | irregular | natural | centralizada | media | folha verde escura, fundo natural desfocado |
| EXT003 | `folha-03.jpg` | colorido | natural | centralizada | media | folha amarelada contra céu e vegetação |
| EXT004 | `folha-04.jpg` | claro | natural | centralizada | media | folha verde em fundo relativamente uniforme |
| EXT005 | `folha-05.jpg` | irregular | desigual | deslocada | media | samambaia com estrutura composta |
| EXT006 | `folha-06.jpg` | colorido | natural | proxima_borda | grande | folha contra céu e nuvens |
| EXT007 | `folha-07.jpg` | irregular | natural | centralizada | media | folha com gotas de água e outras folhas ao fundo |
| EXT008 | `folha-08.jpg` | irregular | natural | centralizada | media | múltiplas folhas em ramo |
| EXT009 | `folha-09.jpg` | colorido | desigual | centralizada | grande | folha contra céu com forte contraluz |

| Coluna | Regra |
|---|---|
| `id` | `EXT000` a `EXT999`, único |
| `arquivo` | Nome simples de arquivo diretamente em `imagens/`, único (sem distinguir maiúsculas) |
| `fundo` | `claro` · `escuro` · `colorido` · `irregular` |
| `iluminacao` | `natural` · `artificial` · `sombra` · `desigual` |
| `posicao` | `centralizada` · `inclinada` · `proxima_borda` · `deslocada` |
| `distancia` | `grande` · `media` · `pequena` |
| `formato` | `JPG` · `JPEG` · `PNG`, correspondente à extensão |
| `observacao` | Livre |

### Validações antes de processar

| Verificação | Resultado se falhar |
|---|---|
| ID no padrão e único | Entrada registrada como inválida, não processada |
| Arquivo único | idem |
| Caminho absoluto (`C:\…`, `/…`, `\\servidor\…`, `D:x`) | idem |
| `..` em qualquer parte do nome | idem |
| Subpasta (`/` ou `\` no nome) | idem |
| Caminho resolvido fora de `imagens/` (por exemplo, link simbólico) | idem |
| Arquivo existe | idem |
| Extensão `.jpg`, `.jpeg` ou `.png` | idem |
| Condições dentro do vocabulário | idem |
| Formato coerente com a extensão | idem |

Uma entrada inválida **não interrompe** as demais. Na execução real: **0 entradas
inválidas**.

---

## 7. Metodologia

```
imagens externas selecionadas → copiadas para fotos-externas/imagens/ → manifesto preenchido
  → avaliar_fotos_externas.py verificar                  (só valida)
  → avaliar_fotos_externas.py                            (execução única, 2026-09-21 21:38)
       ├─ valida cada entrada; inválidas são registradas e puladas
       ├─ confere os hashes do pipeline contra o checkpoint (diferente → código 3)
       ├─ para cada imagem válida: processar_folha(imagem, salvar_imagens=True,
       │                                           destino=resultados/robustez-fase11/<id>/)
       ├─ confere os hashes de novo
       └─ grava JSON, CSV, resumo e fase11-inspecao.csv (colunas humanas vazias)
  → inspeção humana das imagens intermediárias de TODAS as 9 → fase11-inspecao.csv
  → avaliar_fotos_externas.py inspecao → fase11-inspecao-resumo.json
  → análise escrita por pessoas (este documento)
```

### O script é uma casca

[`processamento-imagens/avaliar_fotos_externas.py`](../../processamento-imagens/avaliar_fotos_externas.py):

| Garantia | Verificada por |
|---|---|
| Não importa OpenCV nem NumPy | `test_script_nao_importa_opencv_nem_numpy` |
| O único módulo interno é `src.pipeline` (mais o script da Fase 10, só para hashes e estatística) | `test_script_usa_somente_o_pipeline_central` |
| Nenhuma constante de segmentação nem limiar de regra, nem por nome nem por valor numérico | `test_nenhuma_constante_de_segmentacao_nem_regra_duplicada` |
| Nenhuma atribuição a constante do pipeline | `test_script_nao_altera_constantes_do_pipeline` |
| `processar_folha` é chamado com a imagem e gera imagens intermediárias para todas | `test_pipeline_central_e_chamado` |
| O manifesto versionado só contém entradas avaliadas e inspecionadas | `test_manifesto_versionado_corresponde_a_avaliacao_executada` |

O script da Fase 10 é **reaproveitado por importação** e não foi modificado.

### Imagens intermediárias de todas as imagens

Diferente da Fase 10, **todas** as imagens geraram as 8 imagens intermediárias, em
`processamento-imagens/resultados/robustez-fase11/<id>/`, **ignoradas pelo Git**. A
inspeção dependeu delas, principalmente de `05-mascara-limpa.png` e `07-final.png`.

Consequência: o tempo medido **inclui** a visualização e **não** é diretamente comparável
ao da Fase 10, que rodou sem imagens.

---

## 8. Resultado operacional (automático)

Fonte: [`fase11-resumo.json`](dados-robustez/fase11-resumo.json).

| Métrica | Resultado |
|---|---:|
| Entradas no manifesto | 9 |
| Entradas inválidas | 0 |
| Processadas | 9 |
| Sucesso operacional | 9 |
| Erros | 0 |
| **Taxa de processamento operacional** | **100 %** |
| Com aviso técnico | 9 de 9 |
| Tempo por imagem (mediana, com geração de imagens) | 92,2 ms |

### Avisos técnicos

| Aviso | Imagens | IDs |
|---|---:|---|
| `objeto_toca_borda` | 8 | todas exceto EXT003 |
| `multiplos_contornos` | 6 | EXT001, EXT003, EXT005, EXT006, EXT008, EXT009 |
| atributos próximos de um limiar | 5 | EXT002, EXT003, EXT005, EXT007, EXT008 |
| `iou_abaixo_de_0_99` | 3 | EXT005, EXT008, EXT009 |
| `variacao_area_acima_de_1pct` | 2 | EXT005, EXT008 |
| `selecao_ambigua` | 1 | EXT003 |

Os avisos já sinalizavam problema — no Flavia, **nenhuma** das 96 imagens tocou a borda e
todas tiveram um único contorno. Mas aviso não é diagnóstico: só a inspeção diz se o
resultado serve.

### Fração da imagem ocupada pela máscara

| | Flavia — Fase 10 (96) | Externas — Fase 11 (9) |
|---|---:|---:|
| Mínimo | 0,027 | 0,016 |
| Mediana | 0,350 | 0,624 |
| Máximo | 0,528 | **0,999** |

Em 6 das 9 imagens a máscara ocupa mais da imagem do que em **qualquer** imagem do Flavia;
em EXT002 e EXT004 ela cobre mais de 99 % do quadro. É o sinal numérico do problema que a
inspeção nomeou como *fundo confundido com folha*. No outro extremo, em EXT003 a máscara
cobre 1,6 % — a folha amarelada ficou fora da faixa HSV.

---

## 9. Inspeção humana

Fontes: [`fase11-inspecao.csv`](dados-robustez/fase11-inspecao.csv) (9 revisadas, 0 valores
inválidos) e [`fase11-inspecao-resumo.json`](dados-robustez/fase11-inspecao-resumo.json).

### Resumo quantitativo

| Pergunta | sim | parcial | não |
|---|---:|---:|---:|
| A folha principal foi segmentada? (`folha_principal_segmentada`) | 2 | 5 | 2 |
| A máscara corresponde visualmente à folha? (`mascara_visual_adequada`) | **0** | 2 | 7 |
| O contorno acompanha a borda real? (`contorno_visual_adequado`) | **0** | 2 | 7 |
| **As medidas são utilizáveis? (`resultado_util`)** | **0** | **2** | **7** |

### Problema principal

| Problema | Imagens | IDs |
|---|---:|---|
| Fundo confundido com folha | **5** | EXT001, EXT002, EXT004, EXT005, EXT006 |
| Objeto secundário incorporado | 2 | EXT007, EXT008 |
| Folha parcialmente perdida | 1 | EXT009 |
| Cor fora da faixa HSV | 1 | EXT003 |
| Resultado adequado | **0** | — |

### Por imagem

| ID | Folha segmentada | Máscara | Contorno | Útil | Problema principal |
|---|---|---|---|---|---|
| EXT001 | parcial | não | não | **não** | fundo confundido com folha |
| EXT002 | parcial | não | não | **não** | fundo confundido com folha |
| EXT003 | não | não | não | **não** | cor fora da faixa |
| EXT004 | parcial | não | não | **não** | fundo confundido com folha |
| EXT005 | parcial | não | não | **não** | fundo confundido com folha |
| EXT006 | sim | parcial | parcial | **parcial** | fundo confundido com folha |
| EXT007 | sim | parcial | parcial | **parcial** | objeto secundário incorporado |
| EXT008 | não | não | não | **não** | objeto secundário incorporado |
| EXT009 | parcial | não | não | **não** | folha parcialmente perdida |

As observações textuais de cada caso estão no CSV. Os dois casos parciais (EXT006, EXT007)
detectaram a folha, mas com regiões extras incorporadas; as medidas geométricas podem
estar distorcidas.

### Por condição de captura (descritivo)

| Condição | Imagens | Útil: sim | parcial | não |
|---|---:|---:|---:|---:|
| Fundo colorido | 4 | 0 | 1 | 3 |
| Fundo irregular | 4 | 0 | 1 | 3 |
| Fundo claro | 1 | 0 | 0 | 1 |
| Iluminação natural | 7 | 0 | 2 | 5 |
| Iluminação desigual | 2 | 0 | 0 | 2 |

Com 1 a 7 imagens por condição, e condições combinadas na mesma imagem, **nenhuma causa
pode ser atribuída a uma condição isolada**. Nenhuma condição coberta produziu resultado
adequado.

---

## 10. Principais falhas

1. **Fundo confundido com folha (5).** Vegetação desfocada, fundo esverdeado ou claro caem
   na faixa HSV H[25,95] S≥40 e entram na máscara. Em EXT002 e EXT004 praticamente toda a
   imagem virou "objeto", e o contorno medido é o quadro, não a folha.
2. **Objeto secundário incorporado (2).** Com várias folhas verdes na cena (EXT007, EXT008),
   a segmentação por cor não as separa, e o critério do *maior componente* escolhe um
   aglomerado.
3. **Folha parcialmente perdida (1).** Em contraluz forte (EXT009), parte da folha se perde
   e a máscara ainda é contaminada por regiões externas.
4. **Cor fora da faixa HSV (1).** A folha amarelada (EXT003) fica fora da faixa calibrada
   para folhas verdes; sobram fragmentos, e o objeto escolhido não é a folha.

As quatro falhas decorrem de propriedades conhecidas e documentadas antes da execução
(§4): segmentação só por cor, calibrada em fundo branco, e seleção pelo maior componente.
**Nenhuma motivou ajuste de parâmetro.**

---

## 11. Comparação com a Fase 10

| | Flavia — Fase 10 | Imagens externas — Fase 11 |
|---|---|---|
| Condição | Fundo branco controlado | Fundo e iluminação não controlados |
| Imagens | 96 | 9 |
| Taxa de processamento operacional | 100 % | 100 % |
| Erros | 0 | 0 |
| Com aviso técnico | 65 de 96 | 9 de 9 |
| Objeto tocando a borda | 0 | 8 |
| Mais de um contorno | 0 | 6 |
| Máscara ocupando a imagem (mediana) | 0,35 | 0,62 |
| Tempo mediano por imagem | 284,7 ms, sem imagens, 1600×1200 | 92,2 ms, com imagens, ~350×245 — **não comparável** |
| Inspeção humana | 12 casos selecionados | Todas as 9 |
| Resultado da inspeção | **12/12 utilizáveis** | **0 adequados, 2 parciais, 7 inadequados** |

A taxa de processamento é idêntica nas duas fases e **não distingue** os dois cenários. O
que os distingue é a inspeção humana — e, de forma indireta, os avisos técnicos.

### Correção de uma referência desatualizada no resumo

Em [`fase11-resumo.json`](dados-robustez/fase11-resumo.json), o bloco
`comparacao_fase10.flavia_fase10` registra `"inspecao_humana": "pendente (Fase 10)"`. Era
verdade no momento da execução (2026-09-21 21:38), porque o script copia o estado da Fase
10 daquele instante. **O estado atual é: inspeção humana concluída nos 12 casos
selecionados da Fase 10, todos utilizáveis.**

O JSON é artefato gerado pela execução única e **não foi editado à mão**, para preservar a
proveniência dos dados; a correção fica registrada aqui. Pelo mesmo motivo, o campo
`"conclusao": null` do JSON permanece nulo: a conclusão é a da §12.

---

## 12. Conclusão

O pipeline apresentou **100 % de sucesso operacional** nas 9 imagens externas, pois todas
chegaram ao fim do processamento sem erro. Porém, a inspeção humana mostrou **baixa
robustez visual** fora das condições controladas do Flavia: **nenhum caso foi considerado
totalmente adequado, 2 foram parcialmente utilizáveis e 7 inadequados**. As principais
limitações foram confusão entre fundo e folha, incorporação de objetos secundários, perda
parcial da folha e cores fora da faixa HSV calibrada. Isso indica que o método funciona
bem no domínio controlado para o qual foi desenvolvido, mas **não generaliza de forma
confiável para fotografias naturais complexas** sem novas estratégias de segmentação.

---

## 13. Limitações

| # | Limitação |
|---|---|
| 1 | **9 imagens** não permitem estatística; o resultado é **descritivo**, por imagem e por condição |
| 2 | **Não houve controle de aquisição**: câmera, distância real, balanço de branco e iluminação são desconhecidos |
| 3 | **Compressão e processamento prévios desconhecidos**: as imagens vieram de fontes externas e foram convertidas para JPG; recompressão, redimensionamento ou edição anteriores podem ter alterado as cores |
| 4 | Resolução baixa (~350×245), muito menor que a do Flavia (1600×1200) |
| 5 | As condições (fundo, luz, etc.) foram declaradas por quem montou o manifesto, não medidas |
| 6 | O julgamento `sim`/`parcial`/`nao` é humano e subjetivo; não houve segunda inspeção independente registrada |
| 7 | Condições não cobertas: fundo escuro, luz artificial, sombra, inclinação, folha pequena, PNG, HEIC |
| 8 | Imagens não versionadas: terceiros não podem reproduzir a avaliação com as mesmas imagens, só com o mesmo protocolo |
| 9 | O tempo inclui a visualização e não é comparável ao da Fase 10 |
| 10 | O teste do link simbólico para fora de `imagens/` é pulado em Windows sem permissão para criar links; a mesma checagem é coberta por um teste que simula a resolução do caminho |

---

## 14. Ameaças à validade

| Ameaça | Efeito |
|---|---|
| **Amostra pequena e não aleatória** | Não representa "fotos de folhas em geral"; representa as 9 imagens escolhidas |
| **Viés de seleção** | As imagens foram escolhidas para representar condições difíceis; o resultado tende a ser **pior** que o de fotos tiradas seguindo o protocolo com fundo simples. Por outro lado, nenhuma condição coberta deu resultado adequado |
| **Condições combinadas** | Uma imagem com fundo colorido **e** contraluz não permite atribuir a falha a uma causa só |
| **Origem desconhecida** | Imagens de fontes externas podem ter passado por edição, filtros ou compressão forte que mudam a cor — e a segmentação é por cor |
| **Espécies desconhecidas** | Formas de folha diferentes das do Flavia mudam as medidas, sem que isso seja falha |
| **Metadados EXIF** | Orientação EXIF é aplicada em JPEG; com imagens convertidas, os metadados originais podem ter sido perdidos |
| **Medidas em pixels** | Distâncias diferentes dão áreas diferentes para a mesma folha; sem referência física |
| **`proporcao_verde` circular** | É medida sobre a máscara definida pela própria faixa verde |
| **Julgamento humano** | É a única referência disponível, e é subjetivo |

---

## 15. Status

| Item | Estado |
|---|---|
| Protocolo | ✅ Pronto |
| Estrutura de pastas (`fotos-externas/`, `imagens/` ignorada) | ✅ Pronta |
| Manifesto | ✅ 9 entradas, versionado |
| Script de avaliação | ✅ Pronto e testado |
| Execução | ✅ 9/9 processadas, 0 erros, hashes idênticos antes e depois |
| Inspeção humana | ✅ 9/9 revisadas, 0 valores inválidos |
| Resultado visual | ⚠️ **0 adequados, 2 parciais, 7 inadequados** — robustez externa limitada |
| Conclusão | ✅ Escrita (§12) |
| Imagens externas e intermediárias | 🔒 Fora do Git |

As imagens sintéticas dos testes validam só a infraestrutura; **não são imagens externas** e
nenhum resultado delas entra neste documento.

---

## 16. Procedimento para reexecutar

```bash
# 1. copiar as imagens para processamento-imagens/fotos-externas/imagens/
# 2. preencher processamento-imagens/fotos-externas/manifesto.csv

cd processamento-imagens

# 3. conferir o manifesto (não processa nada)
.venv/Scripts/python.exe avaliar_fotos_externas.py verificar

# 4. executar a avaliação
.venv/Scripts/python.exe avaliar_fotos_externas.py

# 5. inspecionar resultados/robustez-fase11/<id>/ e preencher
#    docs/processamento-imagens/dados-robustez/fase11-inspecao.csv

# 6. resumir a inspeção
.venv/Scripts/python.exe avaliar_fotos_externas.py inspecao
```

No Windows (cmd), use `.venv\Scripts\python.exe`. Com a inspeção atual preenchida, o passo
4 **recusa** rodar (código 5), para não sobrescrever o julgamento humano.

| Código de saída | Significado |
|---:|---|
| 0 | Avaliação concluída, ou nenhuma imagem disponível |
| 2 | Nenhuma entrada válida no manifesto (ou, em `verificar`, alguma inválida) |
| 3 | Pipeline diferente do checkpoint congelado — **não executa** |
| 4 | Hashes divergentes depois da execução |
| 5 | Inspeção humana já preenchida — **não reexecuta** |

---

## 17. Métricas e termos

**Termos que não são usados:** acurácia, precisão, recall, F1, acerto, reconhecimento. O
pipeline não tem referência de verdade para ser "acertado", e não identifica espécies. Os
termos usados são: taxa de processamento, sucesso operacional, avisos técnicos, falha de
segmentação após inspeção humana, comportamento sob condição externa.

### Categorias de falha

`fundo confundido com folha` · `folha parcialmente perdida` · `sombra incorporada` ·
`objeto secundario incorporado` · `folha fragmentada` · `folha nao detectada` ·
`contorno inadequado` · `recorte pela borda` · `cor fora da faixa` · `resultado adequado`
· `outro` — definições no protocolo, §6.

---

## 18. Próximos passos

Nenhuma correção do pipeline nesta fase. Melhorar a robustez externa seria **trabalho
futuro explícito**, com novo conjunto de avaliação, por exemplo:

- segmentação que não dependa só de cor (limiarização adaptativa, GrabCut, bordas);
- critério de seleção do objeto que não seja só o maior componente;
- orientação de captura com fundo simples, documentada para o usuário da página.

---

## Arquivos desta fase

| Arquivo | Conteúdo | Git |
|---|---|:---:|
| `processamento-imagens/avaliar_fotos_externas.py` | Script de avaliação (casca) | ✅ |
| `processamento-imagens/fotos-externas/manifesto.csv` | 9 entradas | ✅ |
| `processamento-imagens/fotos-externas/imagens/` | Imagens externas | ❌ ignorada |
| `processamento-imagens/resultados/robustez-fase11/` | Imagens intermediárias | ❌ ignorada |
| `dados-robustez/fase11-resultados-completos.json` | Resultado completo por imagem | ✅ |
| `dados-robustez/fase11-resultados.csv` | 9 linhas | ✅ |
| `dados-robustez/fase11-resumo.json` | Agregados (ver §11 sobre o campo desatualizado) | ✅ |
| `dados-robustez/fase11-inspecao.csv` | Inspeção humana, 9 linhas | ✅ |
| `dados-robustez/fase11-inspecao-resumo.json` | Resumo da inspeção | ✅ |
| `dados-robustez/hashes-pipeline-antes.txt` / `-depois.txt` | Conferência do pipeline | ✅ |
