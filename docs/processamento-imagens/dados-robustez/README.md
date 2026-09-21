# Dados da Fase 11 — robustez com fotos externas

**Status: vazio.** A avaliação externa ainda não foi executada, porque aguarda as fotos da
equipe. Nenhum resultado desta pasta foi gerado até agora.

Quando a avaliação for executada (`processamento-imagens/avaliar_fotos_externas.py`), esta
pasta receberá:

| Arquivo | Conteúdo |
|---|---|
| `fase11-resultados-completos.json` | Metadados, resultado completo do pipeline por foto e entradas inválidas |
| `fase11-resultados.csv` | Uma linha por foto processada |
| `fase11-resumo.json` | Agregados: cobertura, erros, avisos, condições de captura, comparação com a Fase 10 |
| `fase11-inspecao.csv` | Revisão humana — colunas de julgamento **vazias** até a equipe preencher |
| `fase11-inspecao-resumo.json` | Resumo da revisão humana (comando `inspecao`) |
| `hashes-pipeline-antes.txt` / `-depois.txt` | Conferência do pipeline contra o checkpoint congelado |

As fotos e as imagens intermediárias **não** ficam aqui nem no Git.
