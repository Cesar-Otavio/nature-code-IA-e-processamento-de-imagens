# Dados da Fase 11 — robustez com fotos externas

**Status: avaliação executada e inspecionada manualmente.** 9 imagens externas ao Flavia,
9 processadas, 0 erros; inspeção humana: 0 adequados, 2 parciais, 7 inadequados. Análise em
[`11-ROBUSTEZ-FOTOS-EXTERNAS.md`](../11-ROBUSTEZ-FOTOS-EXTERNAS.md).

Arquivos gerados pela execução única (`processamento-imagens/avaliar_fotos_externas.py`),
exceto a inspeção, preenchida por pessoas:

| Arquivo | Conteúdo |
|---|---|
| `fase11-resultados-completos.json` | Metadados, resultado completo do pipeline por foto e entradas inválidas |
| `fase11-resultados.csv` | Uma linha por foto processada |
| `fase11-resumo.json` | Agregados: cobertura, erros, avisos, condições de captura, comparação com a Fase 10 |
| `fase11-inspecao.csv` | Revisão humana — 9 linhas preenchidas pela equipe |
| `fase11-inspecao-resumo.json` | Resumo da revisão humana (comando `inspecao`) |
| `hashes-pipeline-antes.txt` / `-depois.txt` | Conferência do pipeline contra o checkpoint congelado |

As fotos e as imagens intermediárias **não** ficam aqui nem no Git.

> **Referência desatualizada, não editada:** em `fase11-resumo.json`,
> `comparacao_fase10.flavia_fase10.inspecao_humana` diz `"pendente (Fase 10)"`, o estado no
> momento da execução. Hoje a inspeção dos 12 casos da Fase 10 está concluída. O JSON foi
> mantido como gerado; a correção está no §11 do documento da fase.
