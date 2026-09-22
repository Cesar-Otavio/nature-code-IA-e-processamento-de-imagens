# Checklist de entrega final

> Separa o que foi **verificado automaticamente** do que **depende de uma pessoa**. Os itens
> manuais marcados como concluídos foram executados pela equipe em 21/09/2026.
>
> Roteiro detalhado dos testes manuais: [`TESTES-MANUAIS-FINAIS.md`](TESTES-MANUAIS-FINAIS.md).

---

## Automático — concluído

| # | Item | Evidência | Estado |
|---:|---|---|:---:|
| 1 | Testes do PDI | `python -m pytest` → **886 passam, 1 pulado** (link simbólico no Windows) | ✅ |
| 2 | Testes da IA | 67 + 46 + 82 + 61 = **256/256** | ✅ |
| 3 | Pipeline congelado | 9 hashes SHA-256 idênticos antes e depois da Fase 10 ([`hashes-pipeline-comparacao.txt`](processamento-imagens/dados-avaliacao/hashes-pipeline-comparacao.txt)) e da Fase 11 ([`antes`](processamento-imagens/dados-robustez/hashes-pipeline-antes.txt) · [`depois`](processamento-imagens/dados-robustez/hashes-pipeline-depois.txt)) | ✅ |
| 4 | Git | Tag `fase-9-completa` → `4b66981`, enviada ao GitHub; tags anteriores intactas | ✅ |
| 5 | Dataset fora do repositório | `processamento-imagens/dataset/dados/` ignorado; só README e manifesto versionados | ✅ |
| 6 | Imagens externas fora do repositório | `processamento-imagens/fotos-externas/imagens/` e `processamento-imagens/resultados/robustez-fase11/` ignorados | ✅ |
| 7 | Isolamento IA × PDI | `tests/test_isolamento.py` | ✅ |
| 8 | Avaliação final nas 96 reservadas | 96/96 processadas, 0 erros ([`10-AVALIACAO-FINAL.md`](processamento-imagens/10-AVALIACAO-FINAL.md)) | ✅ |
| 9 | `requirements.txt` válido | Suíte inteira rodou num ambiente virtual novo instalado só com ele; o da raiz delega ao do módulo (`tests/test_requirements.py`) | ✅ |
| 10 | Links internos da documentação | `tests/test_links_documentacao.py` | ✅ |
| 11 | Comportamento da página do PDI | Node com DOM simulado, 10 cenários (`tests/test_interface_web.py`) | ✅ |
| 12 | Clone estrutural | Cópia só com os arquivos versionáveis (sem dataset, imagens, `.venv`): `pip install -r requirements.txt` da raiz ok; API responde `/health` e processa imagem; páginas do site 200; referências locais de HTML/CSS resolvem; pytest **883 passam, 2 pulados** (dataset ausente, link simbólico) — medido antes dos 2 relatórios, que acrescentaram 2 testes de links | ✅ |
| 13 | Execução da Fase 11 | 9/9 imagens externas processadas, 0 erros ([`11-ROBUSTEZ-FOTOS-EXTERNAS.md`](processamento-imagens/11-ROBUSTEZ-FOTOS-EXTERNAS.md)) | ✅ |

---

## Manual — concluído

| # | Item | Registro | Estado |
|---:|---|---|:---:|
| 1 | Site aberto pelo navegador via `http.server` | [Testes manuais §2](TESTES-MANUAIS-FINAIS.md#2-navegador) | ✅ |
| 2 | Teste manual da interface PDI: botão, upload, preview, processamento, trocar e remover imagem, arquivo inválido | idem | ✅ |
| 3 | API do PDI offline → mensagem; recuperação sem recarregar | idem | ✅ |
| 4 | Responsividade **celular** (~375 px) | idem | ✅ |
| 5 | Responsividade **tablet** (~768 px) | idem | ✅ |
| 6 | Responsividade **desktop** (≥ 1280 px) | idem | ✅ |
| 7 | API PDI manual: `/health`, upload válido, PNG de resultado, formato inválido, `.jpg` falso, campo ausente, > 12 MB, travessia de caminho | [Testes manuais §1](TESTES-MANUAIS-FINAIS.md#1-cmd--api) | ✅ |
| 8 | CLI PDI manual: verboso, JSON, sem imagens, `E001` e `E002` com código de saída 2 | idem | ✅ |
| 9 | IA/Ollama manual: geração real, novo conjunto, resposta ao quiz, F5 | [Testes manuais §3](TESTES-MANUAIS-FINAIS.md#3-ia) | ✅ |
| 10 | IA: cache | idem | ✅ |
| 11 | IA: fallback para questões fixas; Ollama offline e religado | idem | ✅ |
| 12 | IA: diagnóstico | idem | ✅ |
| 13 | Inspeção dos 12 casos da Fase 10 — 12 × `correta`, registrada no CSV | [`10-AVALIACAO-FINAL.md`](processamento-imagens/10-AVALIACAO-FINAL.md) §17 | ✅ |
| 14 | Fase 11 com imagens externas — 9/9 processadas, 0 erros | [`11-ROBUSTEZ-FOTOS-EXTERNAS.md`](processamento-imagens/11-ROBUSTEZ-FOTOS-EXTERNAS.md) §8 | ✅ |
| 15 | Inspeção humana da Fase 11 — 0 adequados, 2 parciais, 7 inadequados | idem §9 | ✅ |

Observações registradas: cache do navegador na primeira abertura (resolvido com `Ctrl+F5`)
e aviso de extensão do navegador no console, sem relação com o código do projeto
([Testes manuais §2 e §3](TESTES-MANUAIS-FINAIS.md)).

---

## Manual — pendente

| # | Item | Onde está o roteiro | Estado |
|---:|---|---|:---:|
| 1 | Clone limpo em **outra máquina**, seguindo só o README (o clone estrutural nesta máquina já passou — automático #12) | [Testes manuais §5](TESTES-MANUAIS-FINAIS.md#5-clone-limpo) | ⬜ |
| 2 | README renderizado corretamente no GitHub (tabelas, diagrama Mermaid, links) | Abrir o repositório no navegador | ⬜ |
| 3 | Repositório público acessível sem login | Abrir o link numa janela anônima | ⬜ |
| 4 | Apresentação ensaiada | [`ROTEIRO-DEMO.md`](ROTEIRO-DEMO.md) | ⬜ |
| 5 | Itens menores não registrados: exit code 0 e 1 da CLI, temporários, TTL, botão *VOLTAR* | [Testes manuais §1–2](TESTES-MANUAIS-FINAIS.md) | ⬜ |

---

## Decisões ainda em aberto

| Decisão | Contexto |
|---|---|
| Licença do código | Não definida pela equipe; não é requisito informado pelo professor |
