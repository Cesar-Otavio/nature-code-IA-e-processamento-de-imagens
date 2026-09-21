# Fase 11 — Robustez com fotos externas

```text
Status: infraestrutura pronta; avaliação externa aguardando fotos da equipe.
```

> **Nenhum resultado desta fase existe ainda.** Nenhuma foto externa foi tirada,
> processada ou inspecionada. Este documento descreve o que será feito e como; as seções
> de resultado serão preenchidas somente depois da execução real.
>
> **Esta fase não é desenvolvimento.** É uma avaliação de robustez do pipeline congelado
> em `fase-9-completa`. Nenhum parâmetro será ajustado com base nas fotos externas.

---

## 1. Objetivo

Observar como o pipeline congelado se comporta **fora do ambiente controlado do Flavia**,
com fotografias reais de folhas tiradas pela equipe:

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

## 3. Diferença entre o Flavia e as fotos externas

| Aspecto | Flavia (Fases 3–10) | Fotos externas (Fase 11) |
|---|---|---|
| Fundo | Branco, uniforme | Claro, escuro, colorido, irregular |
| Iluminação | Controlada, difusa | Natural, artificial, sombra, desigual |
| Enquadramento | Folha centralizada, inteira | Centralizada, inclinada, perto da borda, deslocada |
| Escala | Semelhante entre imagens | Grande, média, pequena no quadro |
| Câmera | Uma, fixa | Celulares e câmeras da equipe |
| Formato | JPEG 1600×1200 | JPEG e PNG, resoluções variadas |
| Seleção | Amostragem estratificada com semente | Fotos tiradas segundo protocolo |
| Quantidade | 96 | 10–15 |
| Verificação do resultado | Inspeção humana pendente | **Inspeção humana de todas as fotos** |

---

## 4. Pipeline congelado

| Item | Valor |
|---|---|
| Checkpoint | `fase-9-completa` → `4b66981` |
| Parâmetros | HSV H[25,95] S≥40 V≥20 · Gaussiano 5 · lado máximo 1024 · limpeza 0,001/0,002 · limiares da Fase 8 — **todos inalterados** |
| Verificação | Antes e depois da execução, o script compara os SHA-256 dos 9 arquivos do algoritmo com a referência da Fase 10 (`dados-avaliacao/hashes-pipeline-antes.txt`) e recusa rodar se houver diferença, ou se o Git mostrar alteração nesses arquivos |

### Riscos conhecidos antes da execução — a observar, não conclusões

São propriedades documentadas dos parâmetros congelados, registradas **antes** das fotos
para que a análise não se acomode ao resultado:

| Propriedade do pipeline | Condição externa em que pode importar |
|---|---|
| A segmentação aceita só matiz H∈[25,95] com saturação ≥ 40 | Fundo verde (grama) pode entrar na máscara; folha seca, avermelhada ou variegada pode sair |
| Pixels com brilho V < 20 são excluídos | Folha em sombra forte pode ser perdida |
| O objeto medido é o **maior** componente | Um objeto verde maior que a folha seria escolhido no lugar dela |
| Calibração em fundo branco (Fase 4) | Fundos texturizados nunca foram testados |
| HEIC não é suportado (Fase 9) | Fotos de iPhone em HEIC seriam recusadas |

Se algum desses riscos se confirmar, o registro correto é, por exemplo: *"a segmentação
HSV calibrada para o Flavia apresentou baixa robustez em fundos naturais"* — e não uma
mudança de parâmetro.

---

## 5. Protocolo de captura

Definido em [`11-PROTOCOLO-FOTOS-EXTERNAS.md`](11-PROTOCOLO-FOTOS-EXTERNAS.md): condições
a variar, formatos, regras de privacidade, o que não fazer depois de ver os resultados e
o critério da inspeção humana.

---

## 6. Quantidade prevista

**10 a 15 fotos, preferencialmente 12**, cada uma com uma folha principal, cobrindo pelo
menos uma vez cada valor de fundo, iluminação, posição e distância. Pelo menos uma JPEG
de celular sem conversão e, se possível, uma PNG.

---

## 7. Manifesto

`processamento-imagens/fotos-externas/manifesto.csv` — hoje contém **só o cabeçalho**:

```text
id,arquivo,fundo,iluminacao,posicao,distancia,formato,observacao
```

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

Uma entrada inválida **não interrompe** as demais.

---

## 8. Metodologia

```
equipe tira as fotos (protocolo) → copia para fotos-externas/imagens/ → preenche o manifesto
  → avaliar_fotos_externas.py verificar                  (opcional: só valida)
  → avaliar_fotos_externas.py
       ├─ manifesto vazio ou sem fotos → mensagem, encerra (código 0)
       ├─ inspeção já preenchida → recusa, para não sobrescrever (código 5)
       ├─ valida cada entrada; inválidas são registradas e puladas
       ├─ confere os hashes do pipeline contra o checkpoint (diferente → código 3)
       ├─ para cada foto válida: processar_folha(foto, salvar_imagens=True,
       │                                         destino=resultados/robustez-fase11/<id>/)
       ├─ confere os hashes de novo
       └─ grava JSON, CSV, resumo e fase11-inspecao.csv (colunas humanas vazias)
  → equipe inspeciona as imagens de TODAS as fotos e preenche a inspeção
  → avaliar_fotos_externas.py inspecao → fase11-inspecao-resumo.json
  → análise escrita por pessoas
```

### O script é uma casca

[`processamento-imagens/avaliar_fotos_externas.py`](../../processamento-imagens/avaliar_fotos_externas.py):

| Garantia | Verificada por |
|---|---|
| Não importa OpenCV nem NumPy | `test_script_nao_importa_opencv_nem_numpy` |
| O único módulo interno é `src.pipeline` (mais o script da Fase 10, só para hashes e estatística) | `test_script_usa_somente_o_pipeline_central` |
| Nenhuma constante de segmentação nem limiar de regra, nem por nome nem por valor numérico | `test_nenhuma_constante_de_segmentacao_nem_regra_duplicada` |
| Nenhuma atribuição a constante do pipeline | `test_script_nao_altera_constantes_do_pipeline` |
| `processar_folha` é chamado com a foto e gera imagens para todas | `test_pipeline_central_e_chamado` |

O script da Fase 10 é **reaproveitado por importação** e não foi modificado.

### Imagens intermediárias de todas as fotos

Diferente da Fase 10, **todas** as fotos geram as 8 imagens intermediárias, em
`processamento-imagens/resultados/robustez-fase11/<id>/`, **ignoradas pelo Git**. Com
10–15 fotos e inspeção humana de todas, o custo é pequeno e a inspeção depende delas.

Consequência: o tempo medido **inclui** a visualização e **não** é diretamente comparável
ao da Fase 10, que rodou sem imagens. O resumo registra essa ressalva.

---

## 9. Métricas

**Automáticas** (`fase11-resumo.json`):

| Métrica | Observação |
|---|---|
| Entradas no manifesto, inválidas, processadas | |
| Sucesso operacional · erros por código | "Sucesso operacional" = o pipeline chegou ao fim com um objeto medido |
| Taxa de processamento | Sobre as fotos processadas |
| Avisos técnicos, agrupados, com os IDs | O aviso padrão de não identificação botânica é separado |
| Características (fração de foreground, elongação, circularidade, solidez, razão perímetro/hull, anisotropia) | Descritivo; nenhum outlier removido |
| As cinco classificações | Contagem por categoria |
| **Frequência por condição de captura** | Fotos, sucessos, erros e avisos para cada valor de fundo, iluminação, posição e distância |
| Tempo por foto: média, mediana, P95, mínimo, máximo | Inclui a geração das imagens |

**Humanas** (`fase11-inspecao-resumo.json`, depois da revisão): contagem de `sim`,
`parcial` e `nao` em cada pergunta, e de cada categoria de problema.

**Termos que não serão usados:** acurácia, precisão, recall, F1, acerto, reconhecimento. O
pipeline não tem referência de verdade para ser "acertado", e não identifica espécies.
Os termos usados são: taxa de processamento, cobertura, sucesso operacional, falha de
segmentação após inspeção humana, comportamento sob condição externa.

---

## 10. Inspeção humana

`fase11-inspecao.csv` é criado com uma linha por foto processada e as colunas de
julgamento **vazias**:

```text
id,arquivo,folha_principal_segmentada,mascara_visual_adequada,contorno_visual_adequado,resultado_util,problema_principal,observacao_humana
```

| Garantia | Verificada por |
|---|---|
| Nasce vazia — nada é preenchido automaticamente | `test_inspecao_humana_nasce_vazia` |
| Depois de preenchida, nunca é sobrescrita (o script recusa reavaliar) | `test_inspecao_preenchida_nunca_e_sobrescrita` |
| Valores fora de `sim`/`parcial`/`nao` ou das categorias são apontados no resumo | `test_resumo_da_inspecao_humana` |

Critério de `sim` · `parcial` · `nao`: o mesmo da Fase 2 §15, detalhado no protocolo.

---

## 11. Categorias de falha

Para o avaliador humano escolher em `problema_principal`:

`fundo confundido com folha` · `folha parcialmente perdida` · `sombra incorporada` ·
`objeto secundario incorporado` · `folha fragmentada` · `folha nao detectada` ·
`contorno inadequado` · `recorte pela borda` · `cor fora da faixa` · `resultado adequado`
· `outro`

Definições no protocolo, §6.

---

## 12. Comparação prevista com a Fase 10

O resumo terá um bloco `comparacao_fase10` com as duas populações **lado a lado, sem
mistura e sem conclusão automática** (`"conclusao": null`):

| | Flavia — Fase 10 | Fotos externas — Fase 11 |
|---|---|---|
| Condição | Fundo branco controlado | Condições reais |
| Imagens | 96 | 10–15 |
| Taxa de processamento | 100 % (medido) | *a medir* |
| Com aviso técnico | 65 (medido) | *a medir* |
| Tempo mediano por imagem | 284,7 ms, sem imagens (medido) | *a medir*, com imagens |
| Inspeção humana | Pendente | *a fazer, em todas as fotos* |
| Principais falhas | Nenhum erro | *a observar* |

A conclusão será escrita por pessoas, depois da inspeção.

---

## 13. Limitações

| # | Limitação |
|---|---|
| 1 | 10–15 fotos não permitem estatística; o resultado é descritivo, por condição |
| 2 | As fotos são tiradas pela própria equipe, que conhece o pipeline — risco de, sem querer, fotografar "do jeito que funciona". O protocolo pede condições difíceis de propósito |
| 3 | O julgamento `sim`/`parcial`/`nao` é humano e subjetivo; duas pessoas podem discordar |
| 4 | As condições (fundo, luz, etc.) são declaradas por quem fotografa, não medidas |
| 5 | Fotos não são versionadas: a avaliação não pode ser reproduzida por terceiros com as mesmas imagens, só com o mesmo protocolo |
| 6 | O tempo inclui a visualização e depende da resolução de cada câmera |
| 7 | O teste do link simbólico para fora de `imagens/` é pulado em Windows sem permissão para criar links; a mesma checagem é coberta por um teste que simula a resolução do caminho |

---

## 14. Ameaças à validade

| Ameaça | Efeito |
|---|---|
| **Amostra pequena e não aleatória** | Não representa "fotos de folhas em geral"; representa as condições do protocolo |
| **Viés de quem fotografa** | A equipe conhece o pipeline e pode, sem intenção, favorecer condições fáceis |
| **Condições combinadas** | Uma foto com fundo irregular **e** sombra não permite atribuir a falha a uma causa só |
| **Espécies desconhecidas** | Formas de folha diferentes das do Flavia mudam as medidas, sem que isso seja falha |
| **Câmeras diferentes** | Compressão, balanço de branco e resolução variam e afetam a segmentação por cor |
| **Metadados EXIF** | Orientação EXIF é aplicada em JPEG; PNG com alfa e EXIF de rotação teria a rotação ignorada (limitação da Fase 9) |
| **Medidas em pixels** | Distâncias diferentes dão áreas diferentes para a mesma folha; sem referência física |
| **`proporcao_verde` circular** | É medida sobre a máscara definida pela própria faixa verde |
| **Julgamento humano** | É a única referência disponível, e é subjetivo |

---

## 15. Status atual

| Item | Estado |
|---|---|
| Protocolo de captura | ✅ Pronto |
| Estrutura de pastas (`fotos-externas/`, `imagens/` ignorada) | ✅ Pronta |
| Manifesto modelo (só cabeçalho) | ✅ Pronto |
| Script de avaliação | ✅ Pronto e testado com imagens **sintéticas** |
| Testes da infraestrutura | ✅ 51 passam, 1 pulado (link simbólico no Windows) |
| Pasta de saída `dados-robustez/` | ✅ Criada, **sem resultados** |
| **Fotos externas** | ⏳ **Aguardando a equipe** |
| **Execução** | ⏳ Não realizada |
| **Inspeção humana** | ⏳ Não realizada |
| **Conclusões** | ⏳ Nenhuma |

As imagens sintéticas dos testes validam só a infraestrutura; **não são fotos externas** e
nenhum resultado delas entra neste documento.

---

## 16. Procedimento para executar

```bash
# 1. copiar as fotos para processamento-imagens/fotos-externas/imagens/
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

No Windows (cmd), use `.venv\Scripts\python.exe`.

| Código de saída | Significado |
|---:|---|
| 0 | Avaliação concluída, ou nenhuma foto disponível |
| 2 | Nenhuma entrada válida no manifesto (ou, em `verificar`, alguma inválida) |
| 3 | Pipeline diferente do checkpoint congelado — **não executa** |
| 4 | Hashes divergentes depois da execução |
| 5 | Inspeção humana já preenchida — **não reexecuta** |

---

## 17. Próximos passos

1. A equipe tira e copia as fotos, conforme o protocolo.
2. Executar a avaliação uma vez.
3. Inspecionar **todas** as fotos e preencher `fase11-inspecao.csv`.
4. Resumir a inspeção e escrever os resultados nesta fase, por condição de captura,
   registrando as falhas como resultado.
5. Nenhuma correção do pipeline nesta fase. Uma eventual melhoria é trabalho futuro
   explícito, com novo conjunto de avaliação.
