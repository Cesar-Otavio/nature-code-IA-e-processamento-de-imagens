# Nature Code — Processamento de Imagens e Sinais

> 📄 **Relatório final da disciplina:** [`Relatorio final - Processamento de Imagens e Sinais.md`](Relatorio%20final%20-%20Processamento%20de%20Imagens%20e%20Sinais.md)

> **Disciplina:** Processamento de Imagens e Sinais.
> **Funcionalidade:** análise morfológica de folhas — mede a forma de uma folha numa
> imagem e a descreve em termos geométricos.
>
> Este é um **índice**. O conteúdo detalhado está nos documentos das Fases 0–11, linkados
> abaixo. Para a outra disciplina, ver [`IA.md`](IA.md); para a visão geral da entrega,
> [`ENTREGA-GERAL.md`](ENTREGA-GERAL.md).

> **O PDI não usa inteligência artificial** — nenhuma rede neural, nenhum modelo treinado,
> nenhuma LLM. É processamento de imagens clássico e determinístico: a mesma imagem produz
> sempre o mesmo resultado.
>
> **O PDI não identifica espécies.** Descreve a geometria da folha (alongamento, recorte,
> compacidade, complexidade da borda, orientação), não diz que planta ela é.

---

## 1. Onde está o código

| Parte | Local |
|---|---|
| **Backend** (pipeline, CLI, API Flask) | [`processamento-imagens/`](../processamento-imagens/) — código em `processamento-imagens/src/` |
| **Frontend** | [`script/pdi/`](../script/pdi/) e [`pages/modulos/analise-folha.html`](../pages/modulos/analise-folha.html) |
| Testes | `processamento-imagens/tests/` (pytest) |
| Dependências | [`requirements.txt`](../requirements.txt) → `processamento-imagens/requirements.txt` (NumPy, OpenCV, Flask) |

---

## 2. Pipeline

```
imagem → validação → resize → Gaussiano → HSV → segmentação → morfologia → contornos
       → features → regras determinísticas → resultado
```

| Etapa | O que faz | Fase |
|---|---|---|
| Validação | Confere existência, extensão (JPG, JPEG, PNG, BMP), conteúdo real de imagem, tamanho; aplica orientação EXIF | [03](processamento-imagens/03-PRE-PROCESSAMENTO.md) |
| Resize | Lado maior ≤ 1024 px, proporção preservada | [03](processamento-imagens/03-PRE-PROCESSAMENTO.md) |
| Gaussiano | Suavização com kernel 5, reduz ruído antes da segmentação | [03](processamento-imagens/03-PRE-PROCESSAMENTO.md) |
| HSV | Conversão de cor: separa matiz de brilho | [04](processamento-imagens/04-SEGMENTACAO.md) |
| Segmentação | Máscara binária da folha: `H ∈ [25, 95]`, `S ≥ 40`, `V ≥ 20` | [04](processamento-imagens/04-SEGMENTACAO.md) |
| Morfologia | Remove componentes pequenos e preenche buracos internos | [05](processamento-imagens/05-MORFOLOGIA.md) |
| Contornos | Contornos externos; objeto principal = maior contorno | [06](processamento-imagens/06-CONTORNOS.md) |
| Features | Área, perímetro, elongação, circularidade, solidez, extent, razão perímetro/hull, orientação, anisotropia, cor | [07](processamento-imagens/07-CARACTERISTICAS.md) |
| Regras determinísticas | 5 atributos por limiares fixos, com os limiares que motivaram cada categoria | [08](processamento-imagens/08-CLASSIFICACAO-DETERMINISTICA.md) |
| Resultado | JSON, resumo textual geométrico e 8 imagens intermediárias | [09](processamento-imagens/09-PIPELINE-INTEGRACAO.md) |

O pipeline está **congelado** na tag `fase-9-completa` (`4b66981`): nenhum parâmetro mudou
depois disso, e os hashes SHA-256 dos arquivos do algoritmo provam isso.

---

## 3. Avaliação

| Conjunto | Processamento | Inspeção humana |
|---|---|---|
| **Flavia** — 96 imagens reservadas (Fase 10) | 96/96, 0 erros | 12 casos selecionados: **12 × correta** |
| **Imagens externas** — 9 (Fase 11) | 9/9, 0 erros | **0 adequados, 2 parciais, 7 inadequados** |

Sucesso operacional (chegar ao fim sem erro) **não é** segmentação correta. O método
funciona bem no domínio controlado do Flavia (fundo branco) e **não generaliza de forma
confiável** para fotografias naturais complexas. Não há acurácia: não existe referência de
verdade para as categorias geométricas.

---

## 4. Como executar

A partir da raiz do repositório, no Windows:

```cmd
python -m venv processamento-imagens\.venv
processamento-imagens\.venv\Scripts\python.exe -m pip install -r requirements.txt

cd processamento-imagens
.venv\Scripts\python.exe -m src.api
```

Em outro terminal, na raiz: `python -m http.server 8000`. Abra `http://127.0.0.1:8000/` →
**Plantas** → **Análise Morfológica de Folhas** → selecione uma imagem JPG, PNG ou BMP →
**Analisar folha**.

O PDI **não precisa do Ollama**. CLI e demais opções: [`processamento-imagens/README.md`](../processamento-imagens/README.md).

---

## 5. Documentação por fase

| Fase | Documento |
|---:|---|
| 0 | [Auditoria e planejamento](processamento-imagens/00-PLANEJAMENTO.md) |
| 1 | [Definição formal do problema e contrato do pipeline](processamento-imagens/01-DEFINICAO-PROBLEMA.md) |
| 2 | [Seleção, validação e documentação do dataset](processamento-imagens/02-DATASET.md) |
| 3 | [Ambiente Python e pré-processamento](processamento-imagens/03-PRE-PROCESSAMENTO.md) |
| 4 | [Segmentação da folha](processamento-imagens/04-SEGMENTACAO.md) |
| 5 | [Morfologia matemática e limpeza da máscara](processamento-imagens/05-MORFOLOGIA.md) |
| 6 | [Contornos e seleção do objeto principal](processamento-imagens/06-CONTORNOS.md) |
| 7 | [Extração das características morfológicas](processamento-imagens/07-CARACTERISTICAS.md) |
| 8 | [Regras determinísticas e classificação morfológica](processamento-imagens/08-CLASSIFICACAO-DETERMINISTICA.md) |
| 9 | [Pipeline completo, CLI, API e integração](processamento-imagens/09-PIPELINE-INTEGRACAO.md) |
| 10 | [Avaliação final nas 96 imagens reservadas](processamento-imagens/10-AVALIACAO-FINAL.md) |
| 11 | [Protocolo](processamento-imagens/11-PROTOCOLO-FOTOS-EXTERNAS.md) e [resultado da robustez com imagens externas](processamento-imagens/11-ROBUSTEZ-FOTOS-EXTERNAS.md) |

Dados de avaliação e reprodutibilidade:
[`dados-avaliacao/`](processamento-imagens/dados-avaliacao/) (Fase 10) e
[`dados-robustez/`](processamento-imagens/dados-robustez/) (Fase 11). Documento técnico dos
dois módulos: [`Relatorio final - IA + Processamento de Imagens e Sinais.md`](Relatorio%20final%20-%20IA%20+%20Processamento%20de%20Imagens%20e%20Sinais.md).
