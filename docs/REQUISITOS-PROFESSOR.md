# Matriz de requisitos da entrega

> Mapeia cada exigência formal da entrega para o lugar onde é atendida. Origem das
> exigências: [`00-PLANEJAMENTO.md`](processamento-imagens/00-PLANEJAMENTO.md) §15, mais o
> repositório público.
>
> **Estado** reflete o que existe no repositório. Itens que dependem de conferência humana
> estão marcados como tal.

| # | Requisito | Onde está atendido | Arquivo / seção | Estado |
|---:|---|---|---|:---:|
| 1 | **Nomes completos dos integrantes** | README raiz e documento técnico | [`README.md`](../README.md) → *Integrantes* · [`DOCUMENTACAO-FINAL-IA-PDI.md`](DOCUMENTACAO-FINAL-IA-PDI.md) §3 | ✅ |
| 2 | **Descrição detalhada do projeto** | README raiz, documento técnico e documentação por fase | [`README.md`](../README.md) §1–6 · [`DOCUMENTACAO-FINAL-IA-PDI.md`](DOCUMENTACAO-FINAL-IA-PDI.md) · [`docs/processamento-imagens/`](processamento-imagens/) | ✅ |
| 3 | **Etapas do pipeline de PDI, uma a uma** | README raiz e documento técnico, com links para cada fase | [`README.md`](../README.md) §5 · [`DOCUMENTACAO-FINAL-IA-PDI.md`](DOCUMENTACAO-FINAL-IA-PDI.md) §14–19 · fases 03 a 08 | ✅ |
| 4 | **Integração com a disciplina de IA** | Arquitetura com os dois módulos, separação verificada por teste | [`README.md`](../README.md) §3 e §6 · [`DOCUMENTACAO-FINAL-IA-PDI.md`](DOCUMENTACAO-FINAL-IA-PDI.md) §4 e §24 · [`09-PIPELINE-INTEGRACAO.md`](processamento-imagens/09-PIPELINE-INTEGRACAO.md) §3 | ✅ |
| 5 | **Pipeline completo** | Código executável (CLI, API, página) e documentação | `processamento-imagens/src/pipeline.py` · [`09-PIPELINE-INTEGRACAO.md`](processamento-imagens/09-PIPELINE-INTEGRACAO.md) · [`README.md`](../README.md) §10 | ✅ |
| 6 | **`requirements.txt`** | Na raiz, delegando ao módulo de PDI, onde estão as versões fixadas; `requirements-dev.txt` para testes | [`requirements.txt`](../requirements.txt) → [`processamento-imagens/requirements.txt`](../processamento-imagens/requirements.txt) · [`requirements-dev.txt`](../processamento-imagens/requirements-dev.txt) | ✅ |
| 7 | **Links do dataset** | README raiz e README do dataset | [`README.md`](../README.md) §11 · [`processamento-imagens/dataset/README.md`](../processamento-imagens/dataset/README.md) · [`02-DATASET.md`](processamento-imagens/02-DATASET.md) | ✅ |
| 8 | **GitHub público** | https://github.com/Cesar-Otavio/nature-code-IA-e-processamento-de-imagens | — | ⬜ Conferir |

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
não mede acurácia. Ver [`DOCUMENTACAO-FINAL-IA-PDI.md`](DOCUMENTACAO-FINAL-IA-PDI.md) §22 e §27.
