# Checklist de entrega final

> Separa o que foi **verificado automaticamente** do que **depende de uma pessoa**. Nada da
> parte manual está marcado como concluído: só marque depois de fazer.
>
> Roteiro detalhado dos testes manuais: [`TESTES-MANUAIS-FINAIS.md`](TESTES-MANUAIS-FINAIS.md).

---

## Automático — concluído

| # | Item | Evidência | Estado |
|---:|---|---|:---:|
| 1 | Testes do PDI | `python -m pytest` → **881 passam, 1 pulado** (link simbólico no Windows) | ✅ |
| 2 | Testes da IA | 67 + 46 + 82 + 61 = **256/256** | ✅ |
| 3 | Pipeline congelado | 9 hashes SHA-256 idênticos antes e depois da Fase 10 ([`hashes-pipeline-comparacao.txt`](processamento-imagens/dados-avaliacao/hashes-pipeline-comparacao.txt)) | ✅ |
| 4 | Git | Tag `fase-9-completa` → `4b66981`, enviada ao GitHub; tags anteriores intactas | ✅ |
| 5 | Dataset fora do repositório | `processamento-imagens/dataset/dados/` ignorado; só README e manifesto versionados | ✅ |
| 6 | Fotos externas fora do repositório | `processamento-imagens/fotos-externas/imagens/` ignorado | ✅ |
| 7 | Isolamento IA × PDI | `tests/test_isolamento.py` | ✅ |
| 8 | Avaliação final nas 96 reservadas | 96/96 processadas, 0 erros ([`10-AVALIACAO-FINAL.md`](processamento-imagens/10-AVALIACAO-FINAL.md)) | ✅ |
| 9 | `requirements.txt` válido | Suíte inteira rodou num ambiente virtual novo instalado só com ele; o da raiz delega ao do módulo (`tests/test_requirements.py`) | ✅ |
| 10 | Links internos da documentação | `tests/test_links_documentacao.py` | ✅ |
| 11 | Comportamento da página do PDI | Node com DOM simulado, 10 cenários (`tests/test_interface_web.py`) | ✅ |

---

## Manual — pendente

| # | Item | Onde está o roteiro | Estado |
|---:|---|---|:---:|
| 1 | Site abre pelo navegador via `http.server` | [Testes manuais §2](TESTES-MANUAIS-FINAIS.md#2-navegador) | ⬜ |
| 2 | Upload de folha na página do PDI | idem | ⬜ |
| 3 | Pré-visualização da imagem | idem | ⬜ |
| 4 | Processamento e exibição visual (imagens, medidas, descrição) | idem | ⬜ |
| 5 | API do PDI desligada → mensagem e site funcionando | idem | ⬜ |
| 6 | Responsividade: celular, tablet, desktop | idem | ⬜ |
| 7 | IA com Ollama: geração, cache, fallback, F5, diagnóstico | [Testes manuais §3](TESTES-MANUAIS-FINAIS.md#3-ia) | ⬜ |
| 8 | Inspeção visual dos 12 casos da Fase 10 | [Testes manuais §4](TESTES-MANUAIS-FINAIS.md#4-avaliação-visual-da-fase-10) | ⬜ |
| 9 | Fotos externas e execução da Fase 11 | [`fotos-externas/README.md`](../processamento-imagens/fotos-externas/README.md) | ⬜ |
| 10 | Clone limpo em outra máquina, seguindo só o README | [Testes manuais §5](TESTES-MANUAIS-FINAIS.md#5-clone-limpo) | ⬜ |
| 11 | README renderizado corretamente no GitHub (tabelas, diagrama Mermaid, links) | Abrir o repositório no navegador | ⬜ |
| 12 | Repositório público acessível sem login | Abrir o link numa janela anônima | ⬜ |
| 13 | Apresentação ensaiada | [`ROTEIRO-DEMO.md`](ROTEIRO-DEMO.md) | ⬜ |

---

## Decisões ainda em aberto

| Decisão | Contexto |
|---|---|
| Licença do código | O repositório não define licença |
