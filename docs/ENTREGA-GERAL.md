# Nature Code — Guia geral de entrega

> O **Nature Code** é um projeto interdisciplinar entregue em **duas disciplinas**:
> **Inteligência Artificial** e **Processamento de Imagens e Sinais**.

---

## 1. Duas disciplinas, um site

| | Inteligência Artificial | Processamento de Imagens e Sinais |
|---|---|---|
| Funcionalidade | Quizzes dinâmicos gerados por LLM | Análise morfológica de folhas |
| Usa IA? | **Sim** — LLM `gpt-oss:120b-cloud` via Ollama | **Não** — processamento clássico e determinístico |
| Código no site | `script/ia/` | `script/pdi/` · `pages/modulos/analise-folha.html` |
| Serviço local | Daemon Ollama, `localhost:11434` | API Flask, `127.0.0.1:5000` (`processamento-imagens/`) |
| Pipeline | conteúdo → prompt → Ollama → LLM → parser → validador → cache → quiz | imagem → validação → resize → Gaussiano → HSV → segmentação → morfologia → contornos → features → regras → resultado |
| Se o serviço estiver fora | Cai para cache e quiz fixo | Mensagem explicando como iniciar a API |
| Índice da disciplina | [**`IA.md`**](IA.md) | [**`PDI.md`**](PDI.md) |

As duas funcionalidades **compartilham o mesmo site** — o aluno acessa ambas pela mesma
interface —, mas os **pipelines são independentes**: não compartilham código, serviço nem
dados. Nenhum módulo importa o outro, e testes automatizados verificam essa separação
(`processamento-imagens/tests/test_isolamento.py`).

---

## 2. Relatórios acadêmicos

| Documento | Para quem |
|---|---|
| [**`Relatorio final - IA.md`**](Relatorio%20final%20-%20IA.md) | Disciplina de **Inteligência Artificial** |
| [**`Relatorio final - Processamento de Imagens e Sinais.md`**](Relatorio%20final%20-%20Processamento%20de%20Imagens%20e%20Sinais.md) | Disciplina de **Processamento de Imagens e Sinais** |
| [**`Relatorio final - IA + Processamento de Imagens e Sinais.md`**](Relatorio%20final%20-%20IA%20+%20Processamento%20de%20Imagens%20e%20Sinais.md) | Integração entre as duas disciplinas |

---

## 3. Requisitos da entrega

Matriz completa, com o local exato de cada item:
[**`REQUISITOS-PROFESSOR.md`**](REQUISITOS-PROFESSOR.md).

| Requisito | Onde |
|---|---|
| Integrantes | [`README.md`](../README.md#integrantes) |
| Descrição detalhada do PDI | [`README.md`](../README.md) §5 · [`PDI.md`](PDI.md) |
| Integração com a IA | [`README.md`](../README.md) §3 e §6 · esta página |
| `requirements.txt` | [`requirements.txt`](../requirements.txt), na raiz |
| Dataset | [`README.md`](../README.md) §11 · [`processamento-imagens/dataset/README.md`](../processamento-imagens/dataset/README.md) |

---

## 4. Instalação (Windows)

Pré-requisito: **Python 3.12+**. Para a IA, também o **Ollama**.

```cmd
git clone https://github.com/Cesar-Otavio/nature-code-IA-e-processamento-de-imagens.git
cd nature-code-IA-e-processamento-de-imagens

python -m venv processamento-imagens\.venv
processamento-imagens\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

O `requirements.txt` da raiz delega a `processamento-imagens/requirements.txt`, onde estão
as versões fixadas (NumPy, OpenCV, Flask). A camada de IA é JavaScript puro, sem
dependências.

---

## 5. Execução

**Terminal 1 — API do PDI** (só para a análise de folhas):

```cmd
cd processamento-imagens
.venv\Scripts\python.exe -m src.api
```

**Terminal 2 — site**, a partir da raiz:

```cmd
python -m http.server 8000
```

Abra **http://127.0.0.1:8000/**. **Não abra o site por duplo clique (`file://`)**: o
Ollama e a API recusam essa origem.

| Para testar | Precisa de | Caminho no site |
|---|---|---|
| **IA** | Site + Ollama aberto e autenticado, com `gpt-oss:120b-cloud` | Qualquer tópico que gere por IA, por exemplo Reino Animal → Cordados |
| **PDI** | Site + API do PDI | Plantas → **Análise Morfológica de Folhas** → selecionar JPG/PNG/BMP → Analisar |

Cada disciplina pode ser testada sem a outra. Detalhes: [`IA.md`](IA.md) §4 e
[`PDI.md`](PDI.md) §4.

---

## 6. Dataset e dados de avaliação

- **Flavia Leaf Dataset** — 1.907 imagens, 32 espécies. **Não está no Git.** Links e
  download: [`README.md`](../README.md) §11 e
  [`processamento-imagens/dataset/README.md`](../processamento-imagens/dataset/README.md).
  O manifesto versionado registra exatamente quais imagens foram usadas (64 de
  desenvolvimento, 96 de avaliação, semente `20260919`).
- Resultados versionados da avaliação: [`dados-avaliacao/`](processamento-imagens/dados-avaliacao/)
  (Fase 10) e [`dados-robustez/`](processamento-imagens/dados-robustez/) (Fase 11). As
  imagens externas da Fase 11 **não** são publicadas.
- Documento técnico dos dois módulos: [`Relatorio final - IA + Processamento de Imagens e Sinais.md`](Relatorio%20final%20-%20IA%20+%20Processamento%20de%20Imagens%20e%20Sinais.md).

---

## 7. Licença

Licença do código: não definida pela equipe. O dataset Flavia tem ressalva própria de
licença ([`README.md`](../README.md) §11).
