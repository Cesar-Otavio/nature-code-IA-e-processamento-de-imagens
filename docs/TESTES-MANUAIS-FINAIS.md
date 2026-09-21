# Testes manuais finais

> Roteiro para a equipe executar e registrar. **Nenhum item está aprovado ainda.**
>
> Para cada item: execute, compare com o **esperado** e preencha a coluna **Resultado**
> (`ok` / `falhou` + observação). Se falhar, **anote e não corrija o pipeline** — o PDI está
> congelado; uma falha é um resultado a registrar.
>
> Data: ____/____/______ · Máquina: ______________________ · Responsável: ______________

---

## Preparação

Três terminais, a partir da raiz do repositório:

```cmd
:: Terminal 1 — site
python -m http.server 8000

:: Terminal 2 — API do PDI
cd processamento-imagens
.venv\Scripts\python.exe -m src.api

:: Terminal 3 — comandos de teste
cd processamento-imagens
```

Tenha à mão uma imagem de folha do Flavia do **conjunto de desenvolvimento** (por exemplo
`1101.jpg`, `2400.jpg`, `1307.jpg`, `2497.jpg`, em `dataset/dados/Leaves/`), um arquivo que
não seja imagem renomeado para `.jpg`, e um arquivo de mais de 12 MB.

---

## 1. CMD / API

| # | Teste | Comando ou ação | Esperado | Resultado |
|---:|---|---|---|---|
| 1.1 | Health | `curl http://127.0.0.1:5000/health` | JSON com `"status":"ok"` e `"usa_ia":false` | |
| 1.2 | Upload válido | `curl -F "imagem=@dataset/dados/Leaves/1101.jpg" http://127.0.0.1:5000/api/processar-folha` | `status` `sucesso_com_avisos`, 8 URLs em `imagens_intermediarias` | |
| 1.3 | Upload inválido | `curl -F "imagem=@falso.jpg" http://127.0.0.1:5000/api/processar-folha` | HTTP 400, código `E003`, `entrada.arquivo = falso.jpg` | |
| 1.4 | Arquivo > 12 MB | `curl -F "imagem=@grande.jpg" http://127.0.0.1:5000/api/processar-folha` | HTTP 413, `E006`, *"Arquivo muito grande. Máximo: 12 MB."* | |
| 1.5 | Travessia de caminho | `curl -i "http://127.0.0.1:5000/api/resultado/<id>/..%2F..%2Fsrc%2Fapi.py"` | HTTP 404, `E404`, nenhum código-fonte na resposta | |
| 1.6 | CLI | `.venv\Scripts\python.exe -m src.cli dataset\dados\Leaves\1101.jpg` | Resumo legível com medidas e descrição | |
| 1.7 | CLI só JSON | `... -m src.cli <imagem> --json-apenas` | Saída é só JSON | |
| 1.8 | Exit code — sucesso | `... -m src.cli <imagem>` e depois `echo %ERRORLEVEL%` | `0` | |
| 1.9 | Exit code — sem folha | Imagem toda branca | `1` | |
| 1.10 | Exit code — entrada | Arquivo inexistente | `2` | |
| 1.11 | Temporários | Depois dos uploads: `dir %TEMP%\nature-code-pdi-*` | Nenhum arquivo | |
| 1.12 | TTL | Pasta em `resultados\execucoes\` com mais de 24 h, depois um upload | A pasta antiga some; a nova permanece | |

---

## 2. Navegador

Abrir **http://localhost:8000/index.html** (nunca por duplo clique).

| # | Teste | Ação | Esperado | Resultado |
|---:|---|---|---|---|
| 2.1 | Página principal | Abrir `index.html` | Carrega sem erro no console (F12) | |
| 2.2 | Plantas | Módulos → Plantas | Cards dos 5 tópicos e o botão **Análise Morfológica de Folhas** | |
| 2.3 | Botão do PDI | Clicar no botão | Abre `analise-folha.html` com o aviso *"não utiliza inteligência artificial e não identifica espécies"* | |
| 2.4 | Estado do serviço | Com a API ligada | *"Serviço de processamento disponível"* | |
| 2.5 | Upload | Escolher `1101.jpg` | Nome do arquivo e botão *Analisar folha* habilitado | |
| 2.6 | Preview | — | A imagem aparece antes do processamento | |
| 2.7 | Processar | *Analisar folha* | Aviso de processamento e, em seguida, o resultado | |
| 2.8 | Resultados | — | 7 medidas, 5 atributos, resumo, avisos | |
| 2.9 | Imagens | — | Imagem analisada, máscara e resultado anotado, com legenda | |
| 2.10 | Trocar foto | Escolher outra imagem | Preview e resultado anteriores somem | |
| 2.11 | Remover | *Remover imagem* | Preview some, botão de análise desabilitado | |
| 2.12 | Erro | Escolher `documento.txt` e depois `falso.jpg` | Mensagem de formato; depois, mensagem de erro da API — sem detalhe técnico | |
| 2.13 | API offline | Parar a API (Ctrl+C) → *Verificar novamente* | Mensagem de serviço indisponível com o comando para iniciar; o resto do site continua | |
| 2.14 | Reconexão | Religar a API → *Verificar novamente* → analisar | Volta a funcionar sem recarregar a página | |
| 2.15 | Voltar | *VOLTAR* | Retorna a Plantas | |
| 2.16 | Celular | F12 → modo dispositivo, ~375 px | Sem rolagem horizontal; imagens e tabelas legíveis | |
| 2.17 | Tablet | ~768 px | Idem | |
| 2.18 | Desktop | ≥ 1280 px | Imagens lado a lado | |

---

## 3. IA

Pré-requisito: Ollama aberto pela bandeja e autenticado.

| # | Teste | Ação | Esperado | Resultado |
|---:|---|---|---|---|
| 3.1 | Ollama online | `curl http://localhost:11434/api/tags` | Lista inclui `gpt-oss:120b-cloud` | |
| 3.2 | Geração | Abrir o tópico de Cordados | Estado de carregamento e selo de questões geradas por IA | |
| 3.3 | Gerar de novo | Botão de gerar novas perguntas | Perguntas mudam | |
| 3.4 | F5 | Recarregar a página | As **mesmas** perguntas voltam, sem nova geração | |
| 3.5 | Cache | Fechar o Ollama pela **bandeja** e gerar de novo | Quiz sai do cache (se houver) | |
| 3.6 | Fallback | Com o Ollama fechado e sem cache para o tópico | Quiz fixo, com selo de origem fixa, sem tela vazia | |
| 3.7 | Diagnóstico | `http://localhost:8000/ferramentas/diagnostico.html` | Modelo, provedor, latência e resposta crua | |

---

## 4. Avaliação visual da Fase 10

Casos selecionados automaticamente em [`fase10-casos-inspecao.csv`](processamento-imagens/dados-avaliacao/fase10-casos-inspecao.csv).
Imagens: `processamento-imagens/resultados/inspecao-fase10/<arquivo>/`, principalmente
`05-mascara-limpa.png` e `07-final.png`. Regenerar, se preciso:
`.venv\Scripts\python.exe avaliar_conjunto_final.py inspecao`.

Critério ([`02-DATASET.md`](processamento-imagens/02-DATASET.md) §15): **correta** ·
**aceitável** · **falha**.

| # | Arquivo | Espécie | Motivo da seleção | Julgamento | Observação |
|---:|---|---|---|---|---|
| 1 | `2370` | Cedrus deodara | maior elongação; menor circularidade | | |
| 2 | `2353` | Cedrus deodara | maior elongação; menor circularidade | | |
| 3 | `2417` | Cedrus deodara | maior elongação; menor circularidade | | |
| 4 | `1302` | Acer palmatum | menor solidez; maior razão perímetro/hull | | |
| 5 | `1282` | Acer palmatum | menor solidez; maior razão perímetro/hull | | |
| 6 | `1269` | Acer palmatum | menor solidez; maior razão perímetro/hull | | |
| 7 | `2194` | Cinnamomum camphora | mais atributos limítrofes | | |
| 8 | `2458` | Ginkgo biloba | mais atributos limítrofes | | |
| 9 | `3026` | Prunus serrulata | mais atributos limítrofes | | |
| 10 | `1052` | Phyllostachys edulis | controle sem aviso técnico | | |
| 11 | `1191` | Cercis chinensis | controle sem aviso técnico | | |
| 12 | `1195` | Indigofera tinctoria | controle sem aviso técnico | | |

Registre também o julgamento nas colunas `inspecao_humana` e `observacao` do CSV.

---

## 5. Clone limpo

| # | Teste | Esperado | Resultado |
|---:|---|---|---|
| 5.1 | `git clone` numa pasta nova | Sem dataset, sem fotos, sem `.venv` | |
| 5.2 | Seguir **só** o README raiz: venv, `pip install -r requirements-dev.txt`, pytest | Suíte passa (os testes que dependem do dataset baixado são pulados) | |
| 5.3 | Servir o site e abrir a página do PDI | Mensagem de serviço indisponível até iniciar a API | |
| 5.4 | Iniciar a API e analisar uma imagem | Funciona | |
