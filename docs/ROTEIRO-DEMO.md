# Roteiro de demonstração técnica

> Roteiro para apresentar o Nature Code: site, IA e PDI. Tempo estimado: **12–15 minutos**.
> Ensaiar pelo menos uma vez na máquina da apresentação.

---

## Antes de começar

| Item | Como conferir |
|---|---|
| Ollama aberto pela bandeja e autenticado | `ollama list` mostra `gpt-oss:120b-cloud` |
| Site servido | `python -m http.server 8000` na raiz |
| API do PDI rodando | `cd processamento-imagens` → `.venv\Scripts\python.exe -m src.api` |
| Imagem de folha à mão | Uma do **conjunto de desenvolvimento** do Flavia (`1101.jpg`, `2400.jpg`, `1307.jpg` ou `2497.jpg`), copiada para a Área de Trabalho |
| Cache aquecido | Abrir o tópico de Cordados uma vez antes, para haver cache |
| Abas abertas | Início, Cordados, Diagnóstico, Análise de folhas, GitHub |

---

## Fluxo

| # | Passo | O que mostrar | O que dizer |
|---:|---|---|---|
| 1 | Abrir o Nature Code | `http://localhost:8000/index.html` | Site educacional de Biologia, HTML/CSS/JS puros, 21 tópicos |
| 2 | Mostrar os módulos | Reino Animal, Plantas, Ecossistemas | Três módulos de conteúdo; dois módulos técnicos por cima |
| 3 | Mostrar o quiz com IA | Tópico de Cordados | As perguntas são geradas por uma LLM a partir do próprio texto do tópico |
| 4 | Demonstrar a geração | Botão de gerar novas perguntas | Prompt V4 → Ollama → modelo → parser → validador. Nenhuma questão chega ao aluno sem passar pelo validador |
| 5 | Mostrar o fallback | Fechar o Ollama **pela bandeja** e gerar de novo | Cascata IA → cache → quiz fixo: o aluno nunca fica sem quiz |
| 6 | Abrir o PDI | Plantas → **Análise Morfológica de Folhas** | Módulo separado, outra disciplina, outro serviço |
| 7 | Enviar uma folha | Escolher a imagem, pré-visualização, *Analisar folha* | Vai para uma API Python local em `127.0.0.1:5000` |
| 8 | Mostrar a máscara | Imagem da máscara | Segmentação por cor em HSV: a folha em branco, o fundo em preto |
| 9 | Mostrar o contorno | Resultado anotado + legenda | Contorno, envelope convexo, caixas, centroide, eixo principal |
| 10 | Mostrar as características | Tabela de medidas | Área, perímetro, elongação, circularidade, solidez — em pixels |
| 11 | Mostrar a classificação | Descrição morfológica | Cinco atributos por **regras fixas**, com os limiares que as motivaram |
| 12 | Explicar que o PDI não usa IA | Aviso no topo da página | Processamento de imagens clássico; determinístico; **não identifica espécie** |
| 13 | Mostrar documentação e testes | GitHub + terminal com `pytest` | 881 testes do PDI e 256 da IA; avaliação em 96 imagens reservadas: 96/96 processadas, 0 erros — **não é acurácia**, é taxa de processamento válido |

---

## Plano B

| Situação | O que fazer |
|---|---|
| **IA offline** (sem internet, cota esgotada, Ollama com problema) | Mostrar que o quiz continua saindo do **cache** ou do **quiz fixo** — é exatamente a cascata funcionando. A página de diagnóstico mostra o motivo |
| **API do PDI offline** | A página mostra a mensagem com o comando para iniciar. Explicar e, se não subir, usar a **CLI**: `.venv\Scripts\python.exe -m src.cli <imagem>` mostra as mesmas medidas e descrição no terminal, e as imagens ficam em `resultados\execucoes\` |
| **Sem internet** | O PDI é **todo local** e funciona igual. A IA cai para cache ou quiz fixo. Bootstrap e Google Fonts vêm de CDN: o layout pode ficar simplificado, sem perder função |
| **Foto externa falha** | Não improvisar. Explicar que o pipeline foi calibrado no Flavia (fundo branco) e que a robustez em fotos reais é a Fase 11, com protocolo próprio. Usar a imagem do Flavia já validada |
| **Pergunta sobre "acerto"** | Não há acurácia: não existe referência de verdade para as categorias geométricas. O que foi medido é taxa de processamento, determinismo e distribuição; a inspeção visual é humana |

---

## Frases para não dizer

| Evitar | Dizer |
|---|---|
| "A IA reconhece a folha" | "O PDI mede a forma da folha, sem IA" |
| "Acurácia de 100 %" | "100 % de processamento válido no conjunto reservado" |
| "O sistema identifica a espécie" | "O sistema descreve a geometria; não identifica espécie" |
| "Treinamos o modelo de folhas" | "Os limiares foram calibrados por medição no conjunto de desenvolvimento" |
