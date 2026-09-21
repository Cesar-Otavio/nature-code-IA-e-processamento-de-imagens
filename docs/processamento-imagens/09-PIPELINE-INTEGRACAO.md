# Fase 9 — Pipeline completo, CLI, API e integração com o Nature Code

> **Escopo:** unir as Fases 3 a 8 num fluxo único, expô-lo por linha de comando e por
> API local, e integrá-lo ao site como a funcionalidade **Análise Morfológica de Folhas**.
>
> **Não feito nesta fase:** avaliação final nas 96 imagens reservadas, documentação final
> consolidada e README raiz.

---

## 1. Objetivo

Transformar oito módulos validados isoladamente numa ferramenta utilizável — sem
recalibrar nada e sem duplicar lógica.

---

## 2. Arquitetura

```
                    src/pipeline.py
              ÚNICO lugar com lógica de processamento
                  ↙                        ↘
          src/cli.py                    src/api.py
        (casca fina)                   (casca fina, Flask)
                                              ↓  HTTP local 127.0.0.1:5000
                                   pages/modulos/analise-folha.html
                                   script/pdi/analise-folha.js
```

**A regra que sustenta tudo:** `cli.py` e `api.py` não tomam nenhuma decisão de
processamento. Recebem entrada, chamam `processar_folha()`, formatam a saída. Isso é
**verificado por teste estrutural**, não prometido:

| Teste | Garante |
|---|---|
| `test_cli_nao_importa_opencv_nem_numpy` | A CLI não tem como processar imagem sozinha |
| `test_cli_importa_apenas_o_pipeline` | Nenhum import de `segmentation`, `morphology`, `contours`, `features`, `classification` |
| `test_api_nao_contem_logica_de_processamento` | O mesmo para a API |
| `test_pipeline_e_nucleo_nao_importam_flask` | A camada de processamento não sabe que existe uma API |
| `test_cli_e_api_produzem_o_mesmo_resultado` | A mesma imagem pelos dois caminhos dá características e classificação idênticas |

### Por que uma camada interna

O pipeline tem duas funções públicas:

| Função | Recebe | Usada por |
|---|---|---|
| `processar_folha(caminho)` | Caminho de arquivo | CLI, API |
| `processar_matriz(imagem, metadados)` | Imagem já decodificada | `processar_folha`, testes |

A API grava o upload num temporário e chama `processar_folha` — o mesmo caminho da CLI.
Não há ramo de código exclusivo de nenhuma das duas.

---

## 3. Separação IA × PDI

```
Nature Code
├── Módulo de Inteligência Artificial
│   └── script/ia/  →  daemon Ollama (localhost:11434)  →  LLM  →  quizzes
│
└── Módulo de Processamento de Imagens e Sinais
    └── script/pdi/  →  API Flask (127.0.0.1:5000)  →  Python / OpenCV / NumPy
```

**Os dois módulos coexistem no mesmo site e não se comunicam.** Não existe `PDI → Ollama`,
`PDI → LLM` nem `IA → pipeline PDI`.

A arquitetura é **simétrica**: nos dois casos o navegador fala com um serviço local por
HTTP, e o site permanece estático.

### Evidência executável

| Verificação | Resultado |
|---|---|
| O Python do PDI importa biblioteca de IA? | ❌ — varredura por `ast` de 27 bibliotecas |
| O Python do PDI usa `cv2.dnn`? | ❌ |
| O JavaScript do PDI fala com Ollama (`11434`, `api/chat`, `ollama`)? | ❌ |
| A página de análise carrega `script/ia/`? | ❌ — conferido pelas tags `<script src>` |
| A camada de IA referencia o PDI (`script/pdi`, `CONFIG_PDI`, `:5000`)? | ❌ |
| `script/ia/`, `quiz-engine.js` ou `ferramentas/` foram alterados? | ❌ — `git diff` vazio |

> **Um falso positivo, de novo, e a mesma solução.** Os dois primeiros testes de JavaScript
> falharam porque os *comentários* de `config-pdi.js` e da página diziam "separado de
> `script/ia/`". A varredura foi corrigida para ler código e não comentário — e um teste
> novo prova que ela **continua** detectando `fetch('…:11434/api/chat')` real.

---

## 4. Pipeline

Etapas em ordem, exatamente como validadas:

| # | Etapa | Módulo | Fase |
|---:|---|---|---|
| 1 | Validação de entrada | `utils` | 3 |
| 2 | Leitura (+ EXIF + alfa) | `utils` | 3, **9** |
| 3 | Redimensionamento a 1024 px | `preprocessing` | 3 |
| 4 | Filtro Gaussiano, kernel 5 | `preprocessing` | 4 |
| 5 | Conversão HSV + segmentação | `segmentation` | 4 |
| 6 | Limpeza morfológica | `morphology` | 5 |
| 7 | Contornos e objeto principal | `contours` | 6 |
| 8 | Características | `features` | 7 |
| 9 | Classificação determinística | `classification` | 8 |
| 10 | Reunião dos avisos (sem duplicar) | `pipeline` | 9 |
| 11 | Imagens intermediárias (opcional) | `visualizacao` | 9 |

### Nenhum parâmetro recalibrado

| Parâmetro | Valor | Fixado em |
|---|---|---|
| Faixa HSV | H [25,95] · S ≥ 40 · V ≥ 20 | Fase 4 |
| Kernel Gaussiano | 5 | Fase 4 |
| Componente pequeno | 0,001 | Fase 5 |
| Buraco pequeno | 0,002 | Fase 5 |
| Limiares de classificação | dez valores | Fase 8 |

O resultado de cada execução **reporta** esses parâmetros no bloco `processamento`, e há
teste (`test_parametros_das_fases_anteriores_nao_mudaram`) que falha se algum mudar.

---

## 5. Contrato JSON

Forma de uma resposta de sucesso pela API. **Os números abaixo são ilustrativos** — servem
para mostrar a estrutura, não são medição; campos marcados com `"…"` foram abreviados.

```json
{
  "status": "sucesso_com_avisos",
  "versao_pipeline": "1.0.0",
  "id_execucao": "3f9c…",
  "entrada": {
    "arquivo": "1101.jpg", "formato": "JPG",
    "largura_original_px": 1600, "altura_original_px": 1200,
    "largura_processada_px": 1024, "altura_processada_px": 768,
    "bytes": 158934, "tinha_canal_alfa": false
  },
  "processamento": {
    "etapas": ["validacao", "leitura", "redimensionamento", "…", "classificacao"],
    "parametros": {
      "lado_maximo_px": 1024, "kernel_gaussiano": 5,
      "faixa_hsv": {"h": [25, 95], "s": [40, 255], "v": [20, 255]},
      "fator_escala": 0.64,
      "operacoes_limpeza": ["remover_componentes_pequenos", "preencher_buracos_pequenos"]
    },
    "tempo_total_ms": 430.1,
    "tempo_por_etapa_ms": {"segmentacao": 21.0, "contornos": 15.1, "…": 0}
  },
  "objeto": {
    "detectado": true, "numero_contornos": 1, "dominancia": 1.0,
    "bbox": {"x": 58, "y": 101, "largura": 912, "altura": 571},
    "bbox_rotacionada": {"lado_maior": 944.2, "lado_menor": 440.9, "angulo_graus": 26.1, "…": 0},
    "centroide": {"x": 511.4, "y": 390.2},
    "toca_borda": {"topo": false, "base": false, "esquerda": false, "direita": false, "qualquer": false},
    "orientacao_graus": -26.3, "orientacao_confiavel": true, "anisotropia": 0.61
  },
  "caracteristicas": {
    "dimensoes": {"area_contorno_px2": 297410.5, "area_mascara_px2": 298591, "perimetro_px": 2432.8, "…": 0},
    "forma": {"elongacao": 2.14, "circularidade": 0.6315, "solidez": 0.9892, "extent": 0.5711, "…": 0},
    "orientacao": {"angulo_graus": -26.3, "anisotropia": 0.61, "confiavel": true},
    "convexidade": {"…": 0}, "cor": {"…": 0}, "qualidade": {"…": 0}, "avisos": []
  },
  "classificacao": {
    "alongamento": {"categoria": "moderada", "valores": {"elongacao": 2.14}, "…": 0},
    "concavidade": {"categoria": "baixa", "…": 0},
    "compacidade": {"categoria": "moderada", "…": 0},
    "complexidade_borda": {"categoria": "regular", "…": 0},
    "orientacao": {"categoria": "bem_definida", "…": 0},
    "resumo": "Folha moderadamente alongada, de compacidade intermediária, sem reentrâncias profundas, de contorno regular e com eixo principal bem definido.",
    "avisos": ["…"]
  },
  "avisos": ["descricao geometrica automatica; nao constitui identificacao botanica nem taxonomica"],
  "erro": null,
  "imagens_intermediarias": {
    "00-original": "/api/resultado/3f9c…/00-original.png",
    "07-final": "/api/resultado/3f9c…/07-final.png"
  }
}
```

> Medidas reais: tempos na §17; valores de características e categorias nas Fases 7 e 8.

### Regras do contrato

| Regra | Garantida por |
|---|---|
| Os **11 blocos existem sempre**, inclusive no erro | `test_contrato_de_erro_tem_os_mesmos_blocos` |
| `status` ∈ {`sucesso`, `sucesso_com_avisos`, `erro`} | `test_status_e_um_dos_tres` |
| Nomes das características são os da Fase 7 | `test_nomes_de_caracteristicas_sao_os_da_fase_7` |
| Nenhum caminho absoluto no JSON | `test_caminho_absoluto_nao_vaza` |
| Nenhum `NaN` nem `Infinity` | `test_json_e_valido_e_sem_nan` (serializa com `allow_nan=False`) |
| Nenhum array NumPy | `test_nenhum_array_no_resultado` |
| Avisos sem duplicata | `test_avisos_nao_sao_duplicados` |

`_serializar()` converte `np.int64` → `int`, `np.float64` → `float`, `NaN`/infinito →
`null`, e **descarta** qualquer `ndarray` — uma matriz de imagem nunca chega ao JSON.

---

## 6. Tratamento de erros

| Código | Situação | CLI (exit) | API (HTTP) |
|---|---|:---:|:---:|
| `E001` | Arquivo inexistente | 2 | — |
| `E002` | Extensão não suportada / campo ausente | 2 | 400 |
| `E003` | Não decodifica como imagem | 2 | 400 |
| `E004` | Imagem vazia | 2 | 400 |
| `E005` | Resolução abaixo do mínimo | 2 | 400 |
| `E006` | Arquivo acima de 12 MB | 2 | **413** |
| `E007` | Nenhuma folha detectada | **1** | **422** |
| `E011` | Objeto pequeno demais | 1 | 422 |
| `E404` | Recurso inexistente | — | 404 |
| `E500` | Erro interno | 3 | 500 |

**Nenhuma resposta contém rastreamento.** Há teste para isso na CLI, na API e no pipeline.

`processar_folha` **não levanta exceção de domínio**: todo `ErroImagem` vira um resultado
com `status: "erro"`. CLI e API tratam sucesso e falha pelo mesmo caminho.

---

## 7. Visualizações

Oito imagens, geradas opcionalmente (`salvar_imagens=False` desliga):

| Arquivo | Conteúdo |
|---|---|
| `00-original.png` | Imagem redimensionada |
| `01-cinza.png` | Escala de cinza |
| `02-hsv-matiz.png` | Canal de matiz |
| `03-suavizada.png` | Após o Gaussiano |
| `04-mascara.png` | Máscara da segmentação |
| `05-mascara-limpa.png` | Após a limpeza |
| `06-contorno.png` | Contorno principal |
| `07-final.png` | **Resultado anotado** |

### Legenda fixa

| Cor | Elemento |
|---|---|
| 🟢 Verde | Contorno principal |
| 🟣 Magenta | Convex hull |
| 🔵 Azul | Bounding box alinhada |
| 🟡 Amarelo | Bounding box rotacionada — pode ultrapassar a borda da imagem (§23.6) |
| 🔴 Vermelho | Centroide |
| 🩵 Ciano | Eixo principal (só se a orientação for confiável) |

A imagem final traz ainda área, elongação, circularidade e solidez escritas no canto.

> **Visualização não influencia número algum** — verificado por
> `test_resultado_numerico_identico_com_e_sem_imagens`: características, classificação e
> objeto são idênticos com e sem imagens geradas.

Os arquivos ficam em `resultados/execucoes/<uuid>/`, **ignorado pelo Git**.

---

## 8. CLI

```bash
cd processamento-imagens
python -m src.cli caminho/da/folha.jpg
```

| Opção | Efeito |
|---|---|
| `--json-apenas` | Somente JSON em stdout — utilizável em script |
| `--sem-imagens` | Não grava as imagens intermediárias |
| `--saida DIR` | Diretório das imagens |
| `--verboso` | Tempo por etapa em stderr |

Saída normal:

```
Imagem processada com sucesso

  arquivo ............ 1101.jpg
  original ........... 1600x1200
  processada ......... 1024x768

Medidas
  área ............... 297.410 px²
  perímetro .......... 2.432,8 px
  elongação .......... 2.14
  …
Descrição morfológica
  alongamento         moderada
  concavidade         baixa
  …
```

**stdout e stderr separados:** erros vão para stderr, e com `--json-apenas` o stdout
contém **somente** JSON — há teste que confere que ele começa com `{` e termina com `}`.

### Códigos de saída

| Código | Significado |
|---:|---|
| **0** | Sucesso, com ou sem avisos |
| **1** | Nenhuma folha detectada / objeto pequeno demais |
| **2** | Erro de entrada |
| **3** | Erro interno |

---

## 9. API

```bash
cd processamento-imagens
python -m src.api
```

| Método | Rota | Função |
|---|---|---|
| GET | `/health` | Disponibilidade; não processa nada. Declara `"usa_ia": false` |
| POST | `/api/processar-folha` | `multipart/form-data`, campo `imagem` |
| GET | `/api/resultado/<id>/<arquivo>` | Serve uma imagem intermediária |

Criada por **fábrica** (`criar_app()`), para que os testes usem o cliente de teste do Flask
sem subir servidor real.

---

## 10. Segurança local

| # | Medida | Implementação |
|---|---|---|
| 1 | **Endereço local** | `HOST_PADRAO = "127.0.0.1"`, nunca `0.0.0.0` — testado |
| 2 | **`debug=False`** | O modo de depuração do Flask expõe console de execução de código — testado |
| 3 | **Limite de upload** | 12 MB via `MAX_CONTENT_LENGTH`; rejeita com 413 antes de ler tudo — testado |
| 4 | **Extensão validada** | Lista fechada JPG/JPEG/PNG/BMP |
| 5 | **Conteúdo validado** | Extensão correta com conteúdo falso → `E003` — testado |
| 6 | **Nome não confiável** | O nome enviado **nunca** determina o caminho de gravação; o temporário usa UUID |
| 7 | **Upload descartado** | O arquivo original é apagado em `finally`, com ou sem erro — testado |
| 8 | **Travessia de caminho** | Nomes saneados + caminho resolvido e conferido contra a pasta de execuções |
| 9 | **Só PNG servido** | Pedido de outro tipo → 404 |
| 10 | **Sem rastreamento** | Manipulador global devolve mensagem genérica |
| 11 | **Limpeza por idade** | Execuções com mais de 24 h removidas antes de cada processamento |

### Travessia de caminho — cinco ataques testados

```
/api/resultado/../../api.py
/api/resultado/..%2F..%2Fsrc/api.py
/api/resultado/abc/..%2F..%2F..%2Fsrc%2Fapi.py
/api/resultado/abc/..%5C..%5Csrc%5Capi.py
/api/resultado/..%5C..%5C/api.py
```

Todos devolvem **404**, e o teste confere que o conteúdo de `api.py` não aparece na
resposta. A proteção tem duas camadas — saneamento dos nomes **e** conferência de que o
caminho resolvido começa pela pasta de execuções —, de modo que uma falha em uma delas não
basta para escapar.

### Um defeito encontrado no teste manual

Ao enviar um arquivo inválido pela API real, a resposta de erro trazia em
`entrada.arquivo` o nome do **temporário interno** (`nature-code-pdi-<uuid>.jpg`) em vez do
nome enviado. A substituição do nome só acontecia no ramo de sucesso.

Não era vazamento de caminho, mas expunha um detalhe de implementação e tornava o erro
inconsistente com o sucesso. **Corrigido**, e fixado em
`test_nome_temporario_nao_vaza_no_erro`.

> Os testes automatizados cobriam o *código* do erro, não o *nome* no erro. O teste manual
> contra o servidor real encontrou o que a suíte não procurava.

---

## 11. CORS

**Implementado sem biblioteca adicional.** `Flask-CORS` foi avaliado e dispensado: o que é
necessário são quatro cabeçalhos numa função `after_request`, e uma dependência a mais
pesaria mais que o código que substituiria.

| Decisão | Motivo |
|---|---|
| **Lista fechada de origens, não `*`** | Um curinga permitiria que qualquer página aberta no navegador chamasse o serviço |
| Origens: `localhost` e `127.0.0.1` nas portas 8000, 5500 e 3000 | 8000 é o `http.server` documentado; 5500 é Live Server; 3000 é comum |
| `Vary: Origin` | Evita que um cache sirva a resposta de uma origem a outra |
| Preflight `OPTIONS` → 204 | Necessário para `multipart/form-data` |

Testado: origem local recebe o cabeçalho; origem externa **não** recebe.

---

## 12. Integração com o site

### Arquivos

| Arquivo | Papel |
|---|---|
| `pages/modulos/analise-folha.html` | Página da funcionalidade, com estilo próprio embutido |
| `script/pdi/config-pdi.js` | **Único** lugar onde a URL da API aparece — testado |
| `script/pdi/validacao-pdi.js` | Confere o formato da resposta e das URLs de imagem antes de exibir (§23.3) |
| `script/pdi/analise-folha.js` | Upload, preview, chamada à API, exibição |
| `pages/modulos/plantas.html` | **+10 linhas**: um botão de acesso, abaixo dos cards |

### Por que ao lado de `plantas.html`, e não em `ferramentas/`

`ferramentas/diagnostico.html` é ferramenta de **desenvolvimento** da IA. A análise de
folhas é funcionalidade para o **usuário**, ligada tematicamente ao módulo Plantas — o
lugar natural é junto dele.

### O que a página mostra

| Seção | Conteúdo |
|---|---|
| **Aviso de método** | *"Esta ferramenta utiliza processamento digital de imagens clássico. Não utiliza inteligência artificial e não identifica espécies."* — testado |
| **Calibração** | *"calibrado principalmente para folhas verdes em fundo claro"* |
| **Condições ideais** | Uma folha, fundo claro, folha inteira, boa luz, pouca sombra, sem outros objetos |
| **Estado do serviço** | Verificado via `/health` ao abrir |
| **Upload** | Seleção, preview, remover/trocar, validação de formato e tamanho no cliente |
| **Imagens** | Analisada · máscara limpa · resultado anotado, com legenda de cores |
| **Medidas** | Área, perímetro, elongação, circularidade, solidez, extent, orientação — com nota de que o círculo digital mede ≈0,90 |
| **Descrição morfológica** | Os cinco atributos + resumo + aviso de que não é identificação botânica |
| **Avisos** | Traduzidos para linguagem de usuário |

### Serviço desligado

A página mostra:

> *"O serviço local de processamento de imagens não está disponível. Inicie o módulo Python
> para utilizar esta funcionalidade: `cd processamento-imagens && python -m src.api`"*

e desabilita o botão de análise. **O resto do site não é afetado** — verificado com a API
parada: `index.html`, `plantas.html` e as páginas de tópico continuaram respondendo 200.

### Segurança no cliente

Todo texto vindo da API é inserido com **`textContent`, nunca `innerHTML`**. O nome do
arquivo é escolhido pelo usuário e não pode virar marcação na página.

---

## 13. Fluxo do usuário

```
1. terminal 1:  cd processamento-imagens && python -m src.api
2. terminal 2:  python -m http.server 8000          (na raiz do repositório)
3. navegador:   http://localhost:8000/index.html
4.              Módulos → Plantas → "Análise Morfológica de Folhas"
5.              painel confirma "Serviço de processamento disponível"
6.              escolher imagem → preview → "Analisar folha"
7.              imagens, medidas, descrição e avisos
8.              "Remover imagem" → escolher outra
```

---

## 14. R16 — EXIF e canal alfa

Resolvido nesta fase, **por medição** do comportamento do OpenCV — que se mostrou
diferente do esperado.

### O que foi medido

| Flag de leitura | Orientação EXIF | Canal alfa |
|---|---|---|
| `IMREAD_COLOR` | ✅ **aplicada** — JPEG 200×100 com `Orientation=6` sai 100×200 | ❌ descartado, e o pixel transparente **mantém a cor que estava sob ele** |
| `IMREAD_UNCHANGED` | ❌ **ignorada** | ✅ preservado |

**As duas flags resolvem problemas diferentes e são mutuamente exclusivas.**

> **Achado durante a implementação.** A primeira versão trocou `IMREAD_COLOR` por
> `IMREAD_UNCHANGED` para preservar o alfa — e o teste de EXIF, que passava antes, falhou:
> a rotação tinha deixado de ser aplicada. A troca de flag havia consertado um problema e
> criado outro.

### A solução

Inspecionar o **cabeçalho** antes de decodificar. No PNG, o byte 25 do bloco IHDR é o
*color type*: 4 ou 6 declaram alfa. Custo: 26 bytes, contra uma segunda decodificação
completa.

- Com alfa → `IMREAD_UNCHANGED` e **composição sobre fundo branco**:
  `resultado = cor·α + branco·(1−α)`
- Sem alfa → `IMREAD_COLOR`, que aplica o EXIF

**Branco, e não preto**, porque o pipeline foi calibrado para folha escura sobre fundo
claro. Um PNG transparente composto sobre preto criaria um fundo que a segmentação não sabe
tratar.

### Testes

| Teste | Verifica |
|---|---|
| `test_png_com_alfa_e_composto_sobre_branco` | Região transparente sobre preto vira `(255, 255, 255)` |
| `test_png_com_alfa_percorre_o_pipeline` | Imagem com alfa é analisada com sucesso |
| `test_orientacao_exif_e_aplicada` | JPEG com `Orientation=6` é rotacionado |
| `test_retrato_e_paisagem` | As duas orientações de enquadramento funcionam |
| `test_normalizar_canais_trata_os_tres_casos` | 1, 3 e 4 canais |

### Limitação remanescente — PNG com alfa **e** orientação EXIF

**O que acontece.** Um PNG que declara canal alfa é lido com `IMREAD_UNCHANGED`, e essa
flag **ignora** a tag EXIF `Orientation`. A imagem é analisada na orientação em que os
pixels foram gravados, não na orientação que um visualizador de fotos exibiria.

**Consequência.** O ângulo reportado e as imagens intermediárias aparecem girados em
relação ao que o usuário vê no próprio computador. Não há erro nem aviso: o
processamento segue normalmente.

**Por que não foi resolvido.** Tratar isso exige ler o bloco EXIF do PNG (`eXIf`)
manualmente ou adicionar uma dependência (Pillow), e mexeria na leitura já validada. A
combinação é rara: EXIF é metadado de câmera e vem quase sempre em JPEG, que **não** tem
alfa e segue pelo caminho que aplica a rotação (`IMREAD_COLOR`, testado com
`Orientation=6`).

**O que está validado:** PNG com alfa → `tinha_canal_alfa = true` e processamento normal;
JPEG com `Orientation=6` → rotação aplicada. **O que não está:** o caso combinado — nenhum
teste o cobre, porque o comportamento esperado hoje é justamente ignorar a rotação.

HEIC não é suportado.

---

## 15. Testes ponta a ponta

`test_pipeline.py` percorre **imagem → pipeline → JSON** com fixtures sintéticas: contrato
completo, blocos internos, serialização, oito imagens, modo sem imagens, erros, R16,
determinismo, limpeza de execuções, parâmetros preservados.

**Determinismo:** duas execuções sobre a mesma imagem dão características, classificação e
objeto **idênticos**; só o `id_execucao` difere.

---

## 16. Consistência CLI × API

`test_cli_e_api_produzem_o_mesmo_resultado` envia a **mesma imagem** pela CLI
(`--json-apenas`) e pela API, e compara `caracteristicas`, `classificacao` e `objeto`:
**idênticos**.

Não se comparam campos variáveis — `id_execucao`, tempos e URLs.

---

## 17. Performance

24 imagens do conjunto de desenvolvimento, 1600×1200 → 1024×768.

| Etapa | Mediana | Mín | Máx |
|---|---:|---:|---:|
| Leitura | 21,11 ms | 16,05 | 40,87 |
| Redimensionamento | 4,13 ms | 3,50 | 12,63 |
| Suavização | 1,18 ms | 1,06 | 1,38 |
| Segmentação | 20,98 ms | 20,21 | 34,73 |
| Limpeza | 57,52 ms | 55,71 | 59,88 |
| Contornos | 15,09 ms | 14,44 | 16,40 |
| Características | 65,05 ms | 38,83 | 95,91 |
| Classificação | **0,08 ms** | 0,07 | 0,11 |
| **Visualização** | **166,86 ms** | 110,84 | 232,47 |
| **Total sem imagens** | **166,95 ms** | 137,29 | 194,70 |
| **Total com imagens** | **329,54 ms** | 247,53 | 426,40 |

**A visualização custa tanto quanto todo o processamento** — gravar oito PNGs dobra o
tempo. É o motivo de `salvar_imagens=False` existir.

Pela API real, com rede local e upload, as quatro imagens de teste levaram **243 a 469 ms**.
Nada foi otimizado: meio segundo por folha não é gargalo para uso educacional.

---

## 18. Testes manuais

Executados contra servidores **reais** — API Flask na porta 5000 e `http.server` na 8000.

| # | Cenário | Resultado |
|---:|---|---|
| 1 | `GET /health` | ✅ `{"status":"ok", "usa_ia": false, …}` |
| 2 | Site serve `index`, `plantas`, `analise-folha`, JS do PDI, tópico de IA | ✅ 200 em todos |
| 3 | Botão de acesso presente em `plantas.html` | ✅ |
| 4 | CORS com origem `http://localhost:8000` | ✅ cabeçalho devolvido |
| 5 | CORS com origem externa | ✅ **nenhum** cabeçalho |
| 6 | Upload de 4 imagens reais (`1101`, `2400`, `1307`, `2497`) | ✅ 8 imagens cada; `2400` → extrema + **ambígua**; `1307` → concavidade **alta** |
| 7 | Imagem intermediária servida | ✅ 200, `image/png`, 573 KB |
| 8 | Arquivo inválido | ✅ `E003` — **e o defeito do nome temporário, corrigido** |
| 9 | Travessia de caminho | ✅ 404 |
| 10 | **API desligada** | ✅ `/health` recusa conexão; site continua 200 |
| 11 | Execuções no Git | ✅ 7 diretórios no disco, **0 no Git** |

### O que não foi testado por mim, e precisa ser

> **A interação no navegador não foi executada por mim.** Não havia navegador controlável
> nesta sessão. Testei cada peça pela rede — a página é servida, o JS é servido, a API
> responde com CORS correto à origem do site, o upload funciona, as imagens são servidas —,
> mas **não cliquei na interface**.
>
> **Validação manual pendente, para a equipe:** abrir a página, selecionar imagem, ver o
> preview, analisar, conferir as três imagens e as medidas, trocar a imagem, desligar a API
> e ver a mensagem. É o equivalente ao teste manual que a etapa de IA fez na Fase 3.

**Foto externa (§65):** não testada — não havia foto de folha própria disponível. Fica
registrada como robustez a verificar, junto com o conjunto próprio proposto na Fase 2.

> **Estado após a rodada de correção (§23):** a interface continua **aguardando validação
> manual no navegador**. O comportamento do JavaScript agora tem testes automatizados com
> DOM simulado (§23.3), o que reduz o risco, mas **não** equivale a abrir a página e clicar.
> A foto externa continua pendente.

---

## 19. Requirements

**`processamento-imagens/requirements.txt`** — execução:

```
numpy==2.5.3
opencv-python==5.0.0.93
Flask==3.1.3
```

**`processamento-imagens/requirements-dev.txt`** — execução + testes:

```
-r requirements.txt
pytest==9.1.1
```

Versões **fixadas** nas validadas. As transitivas do Flask (Werkzeug, Jinja2, click,
itsdangerous, blinker, MarkupSafe) **não** foram congeladas — o pip as resolve.

### Verificado em ambiente limpo

Um `venv` novo, criado do zero, com `pip install -r requirements-dev.txt`, rodou a suíte
inteira: **662 passed** (a contagem antes do último teste acrescentado). O arquivo é
utilizável sem nada além do Python.

Refeito na rodada de correção — ver §23.8.

---

## 20. Limitações

| # | Limitação |
|---|---|
| 1 | **Interface não validada por clique** nesta sessão — ver §18 |
| 2 | **Nenhuma foto externa testada** |
| 3 | PNG com alfa **e** EXIF de rotação teria a rotação ignorada |
| 4 | HEIC não suportado |
| 5 | CORS restrito a três portas; outra porta exige editar `ORIGENS_PERMITIDAS` |
| 6 | A API processa uma requisição por vez (servidor de desenvolvimento do Flask) — adequado para uso local, não para produção |
| 7 | Limpeza de execuções só roda quando chega uma nova requisição |
| 8 | Visualização dobra o tempo de processamento |
| 9 | A caixa rotacionada de uma folha **grande no quadro** ultrapassa a borda da imagem (`2497`: 77 px; `1101`: 50 px). É a geometria correta; o desenho mostra só a parte visível (§23.6) |
| 10 | O `minAreaRect` alinha com uma aresta do envelope convexo, não necessariamente com o eixo principal: em `2497` a caixa está a ~21° e o eixo a ~3°, e a elongação sai 1,41. Comportamento da definição da Fase 6, **não alterado** — registrado para a avaliação final |
| 11 | Os testes de comportamento da interface (§23.3) precisam do Node.js; sem ele, são pulados e o pytest mostra o pulo |

---

## 21. Riscos atualizados

| # | Risco | Estado | Nota |
|---|---|---|---|
| **R12** | Hífen no nome do diretório | 🟢 **Resolvido na prática** | `python -m src.cli` e `python -m src.api` funcionam a partir de `processamento-imagens/` |
| **R13** | CORS na API local | 🟢 **Resolvido** | Lista fechada, testada nos dois sentidos |
| **R16** | EXIF e alfa | 🟢 **Resolvido** | Inspeção de cabeçalho; 5 testes |
| **R3** | Tamanho do repositório | 🟢 Mantido | Execuções e uploads fora do Git |
| **R27** | Descrição geométrica lida como botânica | 🟠 Mitigado | Aviso na página, no JSON e na CLI |
| **R19** | Calibrado só em folha verde | 🟠 Aberto | Declarado na interface |
| **R30** 🆕 | **Interface sem validação por clique** | 🟠 Aberto | Mitigado por testes com DOM simulado (§23.3); ainda pendente para a equipe |
| **R31** 🆕 | **Servidor de desenvolvimento do Flask** | 🟡 Novo | Adequado a uso local; não para publicação |
| **R32** 🆕 | **Resumo textual contradizendo a categoria** | 🟢 **Resolvido** | Encontrado na revisão externa (§23.1); 27 testes, 22 deles de correspondência categoria → texto |
| **R33** 🆕 | **Caixa mínima desalinhada do eixo em folha pouco alongada** | 🟡 Observado | Limitação 10; não alterado sem defeito comprovado |

---

## 22. Próxima etapa

**Avaliação final**, com o pipeline **congelado**:

1. Abrir pela **primeira e única vez** as 96 imagens de avaliação.
2. Aplicar o protocolo de inspeção definido na Fase 2 (correta / aceitável / falha).
3. Reportar taxas, causas das falhas e tempos, sem ajustar nada.
4. Validação manual da interface pela equipe.
5. Documentação final e README raiz.

---

## 23. Rodada de correção após revisão externa

A Fase 9 foi revisada externamente, com testes manuais adicionais no backend. Esta seção
registra **somente** o que foi corrigido e verificado. Nenhum parâmetro das Fases 4–8 e
nenhum limiar de classificação foi alterado; o conjunto de avaliação não foi usado.

### 23.1 Resumo textual contradizendo a classificação — corrigido

**Caso real** (`amostra-flavia/16.jpg`, fora do manifesto):

| Atributo | Valor | Categoria |
|---|---:|---|
| `complexidade_borda` | razão perímetro/hull **1,479** (limiar 1,30) | **complexa** |
| `concavidade` | solidez **0,977** (limiar 0,92) | baixa |

Resumo antigo: *"…com **borda pouco recortada**…"*.

**Causa exata.** `montar_resumo()` recebia **quatro** dos cinco atributos: a
`complexidade_borda` nunca entrava no texto. O trecho "borda pouco recortada" vinha da
**concavidade** (solidez), e o texto da concavidade falava em "borda".

**As duas medidas não se contradizem.** A solidez mede área: a folha quase não perde área
para o envelope convexo, ou seja, **não tem reentrâncias profundas**. A razão
perímetro/hull mede comprimento: o contorno é **1,48 vez** mais longo que o envelope, sinal
de muitas irregularidades pequenas. Uma borda finamente serrilhada produz exatamente essa
combinação. O defeito era só do texto.

**Correção — só no texto:**

| Atributo | Vocabulário | Textos por categoria |
|---|---|---|
| Concavidade (área) | reentrâncias | `sem reentrâncias profundas` · `com reentrâncias moderadas` · `com reentrâncias profundas` · `com concavidade ambígua (recorte ou curvatura)` · `com concavidade indeterminada` |
| Complexidade da borda (perímetro) 🆕 | contorno | `de contorno regular` · `de contorno moderadamente irregular` · `de contorno complexo (muito irregular)` · `de complexidade do contorno indeterminada` |
| Compacidade | — | `geometricamente pouco compacta` · `de compacidade intermediária` · `geometricamente compacta` · `de compacidade indeterminada` |
| Alongamento | — | `pouco` / `moderadamente` / `bastante` / `extremamente alongada` · `com alongamento indeterminado` |
| Orientação | — | `com eixo principal bem definido` · `com eixo principal pouco definido` · `sem eixo principal definido` · `com orientação indeterminada` |

Resumo novo de `16.jpg`:

> *Folha moderadamente alongada, geometricamente pouco compacta, sem reentrâncias
> profundas, de contorno complexo (muito irregular) e com eixo principal bem definido.*

Duas salvaguardas a mais:

- Os mapeamentos são lidos com `[]` em vez de `.get(categoria, categoria)`. Uma categoria
  sem texto levanta `KeyError` em vez de aparecer crua na frase, como `bem_definida`.
- A assinatura de `montar_resumo()` passou a exigir `complexidade_borda`, então não há
  como montar o resumo esquecendo o atributo.

> As Fases 7 e 8 trazem exemplos de resumo no formato antigo. Esses documentos **não**
> foram reescritos: registram o estado de cada fase.

### 23.2 Auditoria categoria → texto

Todas as **22 categorias possíveis** dos cinco atributos têm um caso em
`test_resumo_corresponde_a_categoria`. Cada caso fixa os outros quatro atributos e confere:

- **trechos obrigatórios**, escritos à mão no teste (e não copiados do dicionário, para o
  teste não repetir a implementação);
- **trechos proibidos no trecho do próprio atributo**. Exemplo: `complexa` não pode
  conter "contorno regular" nem "pouco recortada".

`test_todas_as_categorias_possiveis_estao_cobertas` falha se uma categoria ficar sem caso.
Somam-se o teste de regressão com os valores exatos de `16.jpg`, um teste de que
`classificar_morfologia` passa a complexidade adiante, e os dois das salvaguardas.
**27 testes novos em `test_classification.py`.**

### 23.3 Interface: navegação e JavaScript

**Navegação (revisão estática + testes):**

| Verificação | Resultado |
|---|---|
| `plantas.html` tem âncora visível, fora de comentário, com o texto "Análise Morfológica de Folhas" | ✅ |
| `href="./analise-folha.html"` resolve para o arquivo real a partir de `pages/modulos/` | ✅ |
| Todo `href`/`src` local das duas páginas aponta para um arquivo existente | ✅ |
| VOLTAR de `analise-folha.html` resolve para `plantas.html` | ✅ |
| Scripts do PDI na ordem `config-pdi` → `validacao-pdi` → `analise-folha` | ✅ |
| Todo `id` usado pelo JS existe no HTML | ✅ |
| Nenhum `file://`; a API é `http://127.0.0.1:5000` e a origem `:8000` está no CORS | ✅ |

`particles.js` foi conferido: ele se basta com o `<canvas id="particles">` que a página
tem, e não depende de `script.js`, que só atua no carrossel.

**Defeitos encontrados no `analise-folha.js` e corrigidos:**

| # | Antes | Depois |
|---|---|---|
| 1 | Resposta não-JSON ou sem `erro`/`caracteristicas` gerava `TypeError`, caía no `catch` genérico e mostrava *"não foi possível falar com o serviço"* — mensagem falsa, e a tela podia ficar meio montada | A resposta é validada **antes** de exibir (`validacao-pdi.js`); formato inesperado → mensagem própria |
| 2 | URLs de imagem concatenadas sem conferência | Só aceitas se casarem exatamente com `/api/resultado/<32 hex>/<NN-nome>.png` |
| 3 | Erros engolidos sem registro | `console.error` com o detalhe; a tela mostra só mensagem amigável |
| 4 | O tempo limite não cancelava o `fetch` | `AbortController`, com mensagem própria de tempo esgotado |
| 5 | Trocar de imagem durante a análise fazia o resultado antigo aparecer para a imagem nova | A troca cancela a requisição **e** respostas antigas são descartadas |
| 6 | Escolher arquivo inválido deixava o preview anterior ativo | Qualquer nova seleção descarta a anterior e revoga o `blob:` |
| 7 | Imagem intermediária que falhasse ao carregar (execução expirada, API parada) ficava quebrada | `onerror` esconde a imagem e mostra "Imagem indisponível" |
| 8 | `blob:` do preview não era revogado ao sair da página | Revogado em `pagehide` |

Com o serviço fora do ar, o botão **não** fica desabilitado: clicar mostra a mensagem de
serviço indisponível e tenta de novo. A página ganhou também `[hidden] { display: none
!important; }`, para que nenhum `display` do CSS anule o atributo `hidden`.

**Testes (`test_interface_web.py`, 27):** 14 estáticos (navegação, ids, `file://`, CORS,
ausência de `innerHTML`/`eval` em cada JS do PDI, nenhum detalhe técnico passado para a
tela), 3 do validador executado no Node (incluindo a resposta **real** da API como
entrada, o que prova que o contrato Python e o validador JS concordam) e **10 cenários de
comportamento**. Nesses, `analise-folha.js` roda no Node com DOM simulado e `fetch` falso
(`tests/js/interface_pdi.js`); o DOM simulado lança erro em qualquer escrita em
`innerHTML`.

| Cenário | Verifica |
|---|---|
| `api_offline` | Mensagem de serviço fora, botão utilizável, nada técnico na tela, erro no console |
| `json_invalido` | Mensagem de formato inesperado, sem resultado exibido |
| `json_formato_inesperado` | 7 formatos errados, nenhum deixa a tela meio montada |
| `erro_da_api_e_nova_tentativa` | E007 exibido; outra imagem funciona em seguida |
| `sucesso_com_resposta_real` | Imagens, 7 medidas, 5 atributos, resumo idêntico ao da API |
| `url_de_imagem_maliciosa` | `https://…`, `../`, `javascript:` recusados |
| `imagem_que_falha_ao_carregar` | "Imagem indisponível" |
| `tempo_esgotado` | Requisição abortada, mensagem própria, botão liberado |
| `troca_de_imagem_durante_analise` | Resultado antigo não aparece |
| `preview_e_revoke` | Todo `blob:` criado é revogado |

**Os testes foram verificados contra mutantes.** Doze versões do JS com defeitos
introduzidos de propósito foram rodadas: sem `revokeObjectURL`, sem validar URL, sem
validar resposta, com `innerHTML`, botão travado, sem cancelamento na troca, com
`String(erro)` na tela, sem abort no timeout, sem `onerror`, sem esconder "processando",
erro de sintaxe, e o mutante duplo sem cancelamento **e** sem descarte. **Os doze foram
detectados.** Um mutante que remove só o cancelamento **sobrevive**, e isso é esperado:
cancelar e descartar são defesas redundantes, e cada uma basta sozinha.

> **Um defeito do próprio harness, achado pelos mutantes:** um erro de sintaxe no JS era
> engolido em silêncio. Agora é reportado como falha.

### 23.4 Testes automatizados de segurança

As verificações manuais da revisão passaram a ter testes explícitos:

| Verificação manual | Teste |
|---|---|
| 13 MB → 413, `E006`, *"Arquivo muito grande. Máximo: 12 MB."* | `test_upload_de_13_mb_retorna_413_com_mensagem` (mensagem exata) |
| — | `test_upload_logo_abaixo_do_limite_nao_e_barrado_pelo_tamanho` (11 MB → pipeline, não 413) |
| `/api/resultado/<uuid>/..%2F..%2Fsrc%2Fapi.py` → 404, `E404` | `test_path_traversal_a_partir_de_execucao_real`: **7 variantes** a partir de uma execução real (`../` cru, `%2F`, `%5C`, `%2E%2E`, `..`) |
| Acessar arquivo fora da execução | `test_png_fora_da_execucao_nao_e_servido`: um **PNG real** fora da pasta, e outro na raiz das execuções, inalcançáveis por 5 caminhos |
| Servir não-PNG | `test_arquivo_nao_png_dentro_da_execucao_nao_e_servido`: `.txt` e `.json` **existentes** na pasta da execução → 404 |

Somam-se aos 5 testes de travessia que já existiam.

> **Observação:** para `/api/resultado/..%2F/segredo.png`, o Werkzeug responde **308**,
> redirecionando para a URL com as barras duplas fundidas. O teste segue o
> redirecionamento e confirma que o destino final é **404**, sem PNG. Não há exposição.

### 23.5 Temporários e TTL

| Exigência | Teste |
|---|---|
| Upload temporário removido quando o pipeline **rejeita** (E003) | `test_upload_temporario_removido_quando_o_pipeline_rejeita` |
| … quando não há folha (E007) | `test_upload_temporario_removido_quando_nao_ha_folha` |
| … quando o pipeline **levanta exceção** | `test_upload_temporario_removido_quando_o_pipeline_explode`: confere que o temporário existia durante o processamento, sumiu depois, e que a resposta é 500 sem rastreamento nem a mensagem interna |
| Remoção de diretório antigo e preservação do recente | `test_limpeza_de_execucoes_antigas` (já existia) |
| **Idempotência** — 1 removido, depois 0 e 0 | `test_limpeza_e_idempotente` (reproduz a verificação manual) |
| Arquivo solto na raiz não é tocado | `test_limpeza_ignora_arquivos_soltos` |
| A API limpa antes de processar e preserva a execução nova | `test_api_limpa_execucoes_antigas_antes_de_processar` |

**Defeito encontrado e corrigido:** `limpar_execucoes_antigas` usa
`rmtree(ignore_errors=True)` e contava a pasta como removida mesmo quando ela ficava, por
exemplo com um arquivo travado no Windows. A mesma pasta seria contada a cada chamada, e
a função não seria idempotente. Agora só conta o que de fato desapareceu
(`test_limpeza_nao_conta_o_que_nao_conseguiu_remover`).

Ao fim da rodada, **nenhum** `nature-code-pdi-*` restou no diretório temporário do sistema.

### 23.6 Caixa rotacionada fora do quadro — só a renderização

**A observação anterior estava imprecisa.** Não é folha "quase redonda": `2497` tem
anisotropia 0,376 (eixo bem definido). Medido nas quatro imagens de desenvolvimento
usadas no teste manual:

| Imagem | A caixa desenhada é o `minAreaRect`? | Contorno inteiro dentro dela? | Excede o quadro em |
|---|:---:|:---:|---:|
| `2497` | ✅ | ✅ | **76,7 px** |
| `1101` | ✅ | ✅ | **49,6 px** |
| `2400` | ✅ | ✅ | 7,6 px |
| `1307` | ✅ | ✅ | 0 |

A caixa está **correta**. Quando a folha é grande no quadro, o retângulo girado que a
envolve precisa sair da imagem.

**Correção aplicada, só no desenho.** Empurrar os vértices para dentro da imagem
**deformaria** o retângulo e desenharia uma caixa inexistente. Em vez disso, cada aresta é
recortada com `cv2.clipLine` (`segmento_visivel()` em `visualizacao.py`), e o eixo
principal também. Toda coordenada passada ao desenho fica dentro da imagem, e a parte
visível continua sendo a da caixa verdadeira.

> **Efeito visual honesto:** a imagem fica **praticamente igual** à anterior. O OpenCV já
> recortava as linhas internamente, e a caixa continua saindo pelas bordas, porque ela
> **é** assim. O que muda para o usuário é a legenda da página: *"caixa mínima
> rotacionada (pode ultrapassar a borda da imagem)"*.

Testes: recorte de uma aresta real de `2497`; todas as coordenadas de `cv2.line` dentro do
quadro numa folha sintética cuja caixa excede a imagem (com a pré-condição conferida);
`objeto`, `caracteristicas` e `classificacao` idênticos com e sem imagens; caixa igual ao
`minAreaRect` calculado de forma independente. Um mutante que desenha sem recortar é
detectado.

**Observação registrada, não alterada:** em `2497` a caixa mínima está girada ~21° enquanto
o eixo principal está a ~3°. O `minAreaRect` alinha com uma aresta do envelope convexo, e
a elongação sai 1,41. É a definição da Fase 6 funcionando como definida; fica para a
avaliação final dizer se isso importa (limitação 10, R33).

### 23.7 PNG com alfa + EXIF

Nada foi alterado. A limitação foi reescrita em detalhe em §14.

### 23.8 Números finais

| Suíte | Resultado |
|---|---|
| PDI (`python -m pytest`) | **746 passed**, 0 falhas, 0 pulados (eram 669) |
| PDI em `venv` novo, só com `requirements-dev.txt` | **746 passed** |
| Camada de IA | 67/67 |
| Integração | 46/46 |
| Diagnóstico | 82/82 |
| Benchmark | 61/61 |
| **Legado total** | **256/256** |

Testes novos por arquivo: `test_classification` +27, `test_interface_web` +27 (novo),
`test_api` +15, `test_pipeline` +6, `test_isolamento` +2 (as varreduras de JS passaram a
incluir `validacao-pdi.js`). Total: **+77**.

### 23.9 O que continua pendente

- **Interface aguardando validação manual no navegador.** Os testes com DOM simulado não
  substituem abrir a página e clicar.
- **Foto externa** não testada.
- **As 96 imagens de avaliação continuam intocadas.** Nesta rodada foram usadas só
  imagens sintéticas, as de desenvolvimento `1101`, `1307`, `2400` e `2497`, e as da
  amostra `1`, `7` e `16`. Nenhuma delas está no subconjunto de avaliação do manifesto.

---

*Fase 9 implementada em 21 de setembro de 2026, sobre o commit `81afa7e`, e corrigida após
revisão externa (§23). **746 testes do módulo** e **256 asserções legadas**, todos passando.
Interface aguardando validação manual no navegador; foto externa pendente; as 96 imagens
de avaliação continuam intocadas.*
