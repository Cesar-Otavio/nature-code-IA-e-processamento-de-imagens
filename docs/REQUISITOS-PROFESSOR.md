# Matriz de requisitos da entrega

> Mapeia cada exigência formal da entrega para o lugar onde é atendida. Visão geral das
> duas disciplinas: [`ENTREGA-GERAL.md`](ENTREGA-GERAL.md). Origem das
> exigências: [`00-PLANEJAMENTO.md`](processamento-imagens/00-PLANEJAMENTO.md) §15, mais o
> repositório público.
>
> **Estado** reflete o que existe no repositório. Itens que dependem de conferência humana
> estão marcados como tal.

| # | Requisito | Onde está atendido | Arquivo / seção | Estado |
|---:|---|---|---|:---:|
| 1 | **Nomes completos dos integrantes** | README raiz, logo no início, separado por disciplina, e documento técnico | [`README.md`](../README.md) → *Integrantes* · [`Relatorio final - IA + Processamento de Imagens e Sinais.md`](Relatorio%20final%20-%20IA%20+%20Processamento%20de%20Imagens%20e%20Sinais.md) §3 | ✅ |
| 2 | **Descrição detalhada do projeto** | README raiz, índices por disciplina, documento técnico e documentação por fase | [`README.md`](../README.md) §1–6 · [`IA.md`](IA.md) · [`PDI.md`](PDI.md) · [`Relatorio final - IA + Processamento de Imagens e Sinais.md`](Relatorio%20final%20-%20IA%20+%20Processamento%20de%20Imagens%20e%20Sinais.md) · [`docs/processamento-imagens/`](processamento-imagens/) | ✅ |
| 3 | **Etapas do pipeline de PDI, uma a uma** | README raiz (tabela *O que cada etapa faz*), índice do PDI e documento técnico, com links para cada fase | [`README.md`](../README.md) §5 · [`PDI.md`](PDI.md) §2 · [`Relatorio final - IA + Processamento de Imagens e Sinais.md`](Relatorio%20final%20-%20IA%20+%20Processamento%20de%20Imagens%20e%20Sinais.md) §14–19 · fases 03 a 08 | ✅ |
| 4 | **Integração com a disciplina de IA** | Arquitetura com os dois módulos e os dois pipelines completos, separação verificada por teste | [`README.md`](../README.md) §3, §4 e §6 · [`ENTREGA-GERAL.md`](ENTREGA-GERAL.md) §1 · [`Relatorio final - IA + Processamento de Imagens e Sinais.md`](Relatorio%20final%20-%20IA%20+%20Processamento%20de%20Imagens%20e%20Sinais.md) §4 e §24 · [`09-PIPELINE-INTEGRACAO.md`](processamento-imagens/09-PIPELINE-INTEGRACAO.md) §3 | ✅ |
| 5 | **Pipeline completo** | Código executável (CLI, API, página) e documentação | `processamento-imagens/src/pipeline.py` · [`09-PIPELINE-INTEGRACAO.md`](processamento-imagens/09-PIPELINE-INTEGRACAO.md) · [`README.md`](../README.md) §10 | ✅ |
| 6 | **`requirements.txt`** | Na raiz, delegando ao módulo de PDI, onde estão as versões fixadas; `requirements-dev.txt` para testes | [`requirements.txt`](../requirements.txt) → [`processamento-imagens/requirements.txt`](../processamento-imagens/requirements.txt) · [`requirements-dev.txt`](../processamento-imagens/requirements-dev.txt) | ✅ |
| 7 | **Links do dataset** | README raiz e README do dataset | [`README.md`](../README.md) §11 · [`processamento-imagens/dataset/README.md`](../processamento-imagens/dataset/README.md) · [`02-DATASET.md`](processamento-imagens/02-DATASET.md) | ✅ |
| 8 | **GitHub público** | https://github.com/Cesar-Otavio/nature-code-IA-e-processamento-de-imagens | — | ⬜ Conferir |

---

## Os cinco requisitos informados pelo professor

| # | Requisito | Atendido | Evidência |
|---:|---|:---:|---|
| 1 | Integrantes | ✅ | README → *Integrantes*, em duas listas. **Inteligência Artificial** (6): Amanda Pazold dos Santos, Cesar Otavio da Silva Boiani, Giovana Giraldeli, Giovani Nogueira Pires, Marcus Vinicius da Silva Capeteruchi, Guilherme Ribeiro Zangrande. **Processamento de Imagens e Sinais** (5): os mesmos, sem Guilherme Ribeiro Zangrande |
| 2 | Descrição detalhada do PDI, com pipeline e explicação de cada etapa | ✅ | README §5 (pipeline, *O que cada etapa faz*, parâmetros) · [`PDI.md`](PDI.md) |
| 3 | Integração com a IA, com pipeline completo do projeto | ✅ | README §3 (diagrama dos dois módulos), §4 (pipeline da IA), §6 (integração) |
| 4 | `requirements.txt` na raiz, funcionando com `pip install -r requirements.txt` | ✅ | [`requirements.txt`](../requirements.txt) · verificado em ambiente virtual novo (ver [`CHECKLIST-ENTREGA-FINAL.md`](CHECKLIST-ENTREGA-FINAL.md)) |
| 5 | Dataset — Flavia Leaf Dataset, com links visíveis | ✅ | README §11: fonte oficial, projeto, download e artigo |

---

## Observações

**Item 6 — `requirements.txt` na raiz.** O arquivo da raiz contém uma única linha,
`-r processamento-imagens/requirements.txt`: `pip install -r requirements.txt` funciona a
partir da raiz, e as versões continuam definidas num só lugar, junto do código Python — o
único que tem dependências (a camada de IA é JavaScript puro). Verificado com
`pip install --dry-run` e pelo teste `tests/test_requirements.py`, que também confere que
as versões fixadas não mudaram.

**Item 8 — repositório público.** A URL está documentada e o `git push` da tag
`fase-9-completa` foi aceito. A visibilidade pública precisa ser conferida abrindo o link
numa janela anônima, sem login.

**O que a entrega não afirma.** O PDI não usa IA e não identifica espécies; a avaliação
não mede acurácia. Ver [`Relatorio final - IA + Processamento de Imagens e Sinais.md`](Relatorio%20final%20-%20IA%20+%20Processamento%20de%20Imagens%20e%20Sinais.md) §22 e §27.
