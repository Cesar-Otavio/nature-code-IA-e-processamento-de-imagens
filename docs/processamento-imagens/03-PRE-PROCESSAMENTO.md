# Fase 3 — Ambiente Python e pré-processamento inicial

> **Escopo:** fundação técnica do módulo e **apenas** as etapas de validação, leitura,
> redimensionamento, conversão de espaço de cor e redução de ruído.
>
> **Não implementado nesta fase:** segmentação, limiarização, morfologia, contornos,
> características, classificação, CLI, API, integração com o site.

---

## 1. Objetivo

Estabelecer a base sobre a qual as fases seguintes vão construir: ambiente reproduzível,
organização de módulos, validação rigorosa de entrada e as operações de pré-processamento
que antecedem qualquer segmentação.

A regra que governa a fase: **nada de escolher vencedor**. Gaussiano e mediana entram como
**candidatos em comparação**; a decisão é da Fase 4, medida sobre imagens reais.

---

## 2. Ambiente

| | Valor verificado |
|---|---|
| Sistema operacional | Windows 11 (build 10.0.26200) |
| Arquitetura | AMD64, 64 bits |
| Python | **3.14.3** (CPython) |
| pip | 26.2.1 (atualizado de 25.3 durante a fase) |
| Ambiente virtual | `processamento-imagens/.venv` |

O `.venv` fica **dentro** de `processamento-imagens/`, e não na raiz, para que o módulo seja
autocontido: `cd processamento-imagens` dá acesso ao ambiente, aos testes e ao código no
mesmo lugar.

### Criação

```bash
cd processamento-imagens
python -m venv .venv
.venv/Scripts/python.exe -m pip install numpy opencv-python pytest
```

---

## 3. Dependências

Apenas o estritamente necessário. **Flask não foi instalado** — a API é da Fase 8.
Matplotlib, Pillow, scikit-image e SciPy **não foram instalados**, por não haver uso.

### Diretas

| Pacote | Versão | Para quê |
|---|---|---|
| `numpy` | **2.5.3** | Matrizes de imagem; toda operação de pixel |
| `opencv-python` | **5.0.0.93** | Leitura, redimensionamento, espaços de cor, filtros |
| `pytest` | **9.1.1** | Suíte de testes |

### Transitivas

| Pacote | Versão | Origem |
|---|---|---|
| `colorama` | 0.4.6 | pytest (cor no terminal Windows) |
| `iniconfig` | 2.3.0 | pytest |
| `packaging` | 26.3 | pytest |
| `pluggy` | 1.6.0 | pytest |
| `Pygments` | 2.21.0 | pytest |

> **`requirements.txt` não foi criado**, conforme instruído. As versões acima ficam
> registradas aqui; o arquivo definitivo nasce quando o pipeline estabilizar, contendo
> apenas o que estiver realmente em uso.

### Nota sobre o Python 3.14

O risco R9 da Fase 0 — "Python muito recente pode não ter wheel" — **não se confirmou**.
O `opencv-python` distribui wheel `cp37-abi3`, de ABI estável, que funciona em 3.14 sem
compilação. Instalação limpa, sem aviso.

---

## 4. Estrutura criada

```
processamento-imagens/
├── pytest.ini                  configuração da suíte
├── .venv/                      ambiente virtual          [ignorado]
├── src/
│   ├── __init__.py             identidade e versão do pacote
│   ├── utils.py                validação, leitura, apoio
│   └── preprocessing.py        redimensionamento, cor, filtros
├── tests/
│   ├── __init__.py
│   ├── conftest.py             fixtures — imagens sintéticas
│   ├── test_utils.py
│   ├── test_preprocessing.py
│   └── test_isolamento.py      garante ausência de IA
├── exemplos/                   .gitkeep
├── resultados/                 .gitkeep
│   └── temporarios/            saídas de estudo          [ignorado]
└── dataset/
    ├── README.md
    └── dados/                  imagens do Flavia         [ignorado]
```

**Não criados nesta fase**, por pertencerem a fases posteriores: `segmentation.py`,
`morphology.py`, `contours.py`, `features.py`, `classification.py`, `pipeline.py`,
`api.py`, `cli.py`.

### Decisão sobre o risco R12

O diretório permanece **`processamento-imagens/`**, com hífen. O pacote importável é `src`,
e a execução se dá a partir do diretório:

```bash
cd processamento-imagens
.venv/Scripts/python.exe -m pytest          # testes
.venv/Scripts/python.exe -m src.cli ...     # CLI, a partir da Fase 8
```

Hífen não é identificador Python válido, mas `src` é — e o `pytest.ini` na raiz do módulo
faz com que `src` seja importável sem instalação. **R12 mitigado**, sem renomear nada.

---

## 5. Validação de entrada

Implementada em `utils.py`, seguindo o contrato da Fase 1 §11.

### Cadeia de validação

```
caminho  →  validar_caminho    →  E001  existe? é arquivo? é legível?
         →  validar_extensao   →  E002  .jpg .jpeg .png .bmp
         →  np.fromfile        →  E004  arquivo com zero bytes
         →  cv2.imdecode       →  E003  decodifica como imagem?
         →  validar_dimensoes  →  E004  matriz vazia
                               →  E005  lado menor que o mínimo
         →  (imagem BGR, metadados)
```

### O ponto central: extensão não basta

> Um arquivo `.jpg` contendo texto **é recusado** — com `E003`, não com uma exceção crua.

A extensão é o **primeiro** filtro, nunca o último. Quem decide é a decodificação. Há teste
dedicado a esse caso (`test_extensao_valida_com_conteudo_invalido_gera_E003`).

### Por que `imdecode` e não `imread`

`cv2.imread` devolve `None` tanto para arquivo ausente quanto para conteúdo inválido — dois
erros distintos, indistinguíveis. Além disso, tem problema conhecido com caminhos não-ASCII
no Windows. A leitura é feita com `np.fromfile` seguida de `cv2.imdecode`, o que separa os
casos e trata qualquer caminho.

### Códigos implementados

| Código | Situação | Origem |
|---|---|---|
| `E001` | Arquivo inexistente, não é arquivo, sem permissão | Fase 1 |
| `E002` | Extensão não suportada | Fase 1 |
| `E003` | Não decodifica como imagem | Fase 1 |
| `E004` | Vazio, matriz degenerada, argumento inválido | Fase 1 |
| `E005` | Resolução abaixo do mínimo | Fase 1 |
| **`E008`** | **Parâmetro inválido** (kernel par, negativo, tipo errado; `lado_maximo` inválido) | **Novo nesta fase** |

> **Extensão do contrato, registrada.** O `E008` **não** estava na Fase 1, que previa
> `E001`–`E007`. Ele cobre erro de *programação* — parâmetro inadequado passado pela camada
> que chama —, categoria distinta de erro de *entrada do usuário*. Manter os dois separados
> evita relatar "imagem inválida" quando o problema é um kernel par.

### Mensagens

Nenhuma mensagem de domínio contém rastreamento técnico. Há teste que verifica isso
(`test_mensagem_nao_expoe_rastreamento`). O rastreamento, quando existir, vai para log — a
mensagem é para uma pessoa.

---

## 6. Leitura

`ler_imagem(caminho, lado_minimo)` → `(imagem, metadados)`

| Metadado | Exemplo |
|---|---|
| `arquivo` | `"1.jpg"` |
| `formato` | `"JPG"` |
| `largura_original_px` | `1600` |
| `altura_original_px` | `1200` |
| `canais` | `3` |
| `bytes` | `1126400` |

> **Convenção de cor: o OpenCV lê em BGR, não em RGB.** Azul puro é `(255, 0, 0)` na
> matriz, não `(0, 0, 255)`. Todo o pacote trabalha em BGR, salvo onde o nome disser o
> contrário. Há teste que fixa essa convenção (`test_leitura_devolve_bgr`) — se uma versão
> futura do OpenCV mudasse isso, o teste quebraria em vez de o comportamento mudar em
> silêncio.

---

## 7. Redimensionamento

`redimensionar(imagem, lado_maximo, ampliar=False)` → `(imagem, info)`

### Comportamento

| Situação | Resultado |
|---|---|
| Imagem maior que `lado_maximo` | Reduzida, proporção preservada |
| Imagem menor, `ampliar=False` (padrão) | **Devolvida inalterada** |
| Imagem menor, `ampliar=True` | Ampliada |

### Por que não ampliar por padrão

Ampliar **não cria informação** — apenas interpola. Uma folha de 300 px levada a 1024 px
teria área e perímetro maiores em pixels, sem qualquer detalhe novo. Como área e perímetro
são medidas do projeto, isso produziria números inflados artificialmente.

### Interpolação

| Sentido | Método | Motivo |
|---|---|---|
| Redução | `INTER_AREA` | Faz média dos pixels da região de origem; evita serrilhado, que distorceria o perímetro do contorno |
| Ampliação | `INTER_LINEAR` | Custo baixo e resultado adequado |

### Valor experimental

`LADO_MAXIMO_PX_EXPERIMENTAL = 1024`

O Flavia é uniformemente 1600×1200; reduzir para 1024 dá fator **0,640** e corta a área em
cerca de 59%, com ganho proporcional de tempo. **Não é decisão final**: o valor definitivo
sai da Fase 4, comparando custo de tempo contra estabilidade das medidas de contorno.

A constante está marcada como experimental no código, não espalhada como número mágico.

---

## 8. BGR → RGB

`para_rgb(imagem_bgr)` → imagem RGB, 3 canais, `uint8`, `0..255`

**Finalidade:** exibição e gravação em bibliotecas que esperam RGB.

**Não é usada no processamento.** A ordem dos canais não altera nenhuma medida geométrica —
área, perímetro e forma independem de qual canal vem primeiro. A função existe para a etapa
de apresentação, não para a de análise.

Propriedade verificada: a conversão é **involutiva** — aplicá-la duas vezes devolve o
original.

---

## 9. BGR → escala de cinza

`para_cinza(imagem_bgr)` → imagem de 1 canal, `uint8`, `0..255`

**Finalidade:** base da limiarização por intensidade. Otsu e o limiar adaptativo operam
sobre um único canal.

A conversão é uma **média ponderada** dos canais, com peso maior no verde, seguindo a
sensibilidade do olho humano. Há teste que confirma esse comportamento: verde puro produz
cinza mais claro que azul puro.

### Verificação em imagem real

Medido sobre as três imagens de estudo do Flavia:

| Imagem | Cinza mínimo | Cinza máximo |
|---|---:|---:|
| `1.jpg` | 46 | 255 |
| `16.jpg` | 5 | 253 |
| `18.jpg` | 79 | 255 |

Folha escura sobre fundo branco, com amplitude quase total em todos os casos. **É a
evidência direta de que a limiarização por intensidade tende a funcionar bem neste
dataset** — a hipótese da Fase 2 se sustenta na prática.

---

## 10. BGR → HSV

`para_hsv(imagem_bgr)` → imagem de 3 canais, `uint8`

**Finalidade:** separar **matiz** de **iluminação**. Uma folha verde mantém matiz
aproximadamente constante mesmo quando o brilho varia — propriedade que o RGB não oferece,
porque ali a luz afeta os três canais ao mesmo tempo.

### Intervalos no OpenCV — que não são os convencionais

| Canal | Intervalo OpenCV | Convenção usual |
|---|---|---|
| **H** (matiz) | **0..179** | 0..359° |
| **S** (saturação) | 0..255 | 0..100% |
| **V** (valor) | 0..255 | 0..100% |

O matiz é dividido por 2 para caber em 8 bits. Confundir isso com a escala de 360° é erro
comum e produz intervalos de cor completamente errados. Há teste que fixa os limites.

### Um achado desta fase

Matiz médio da região da folha, medido nas três imagens de estudo:

| Imagem | Matiz médio (0..179) | Equivalente em graus |
|---|---:|---:|
| `1.jpg` | **53,6** | ~107° |
| `16.jpg` | **54,9** | ~110° |
| `18.jpg` | **53,7** | ~107° |

> **Os três valores ficam dentro de uma faixa de 1,3 unidade**, apesar de serem espécies
> diferentes, com brilhos, texturas e formas distintas — incluindo uma folha brilhante com
> reflexo especular e uma acícula fina.
>
> É evidência favorável à segmentação por matiz, e dá um ponto de partida concreto para a
> faixa de verde da Fase 4. **Três imagens não são amostra** — a faixa definitiva sai da
> distribuição medida sobre o conjunto de desenvolvimento.

---

## 11. Filtro Gaussiano

`suavizar_gaussiano(imagem, kernel=5, sigma=0.0)`

**Efeito:** atenua ruído de alta frequência pela média ponderada da vizinhança, com peso
decrescente conforme a distância ao centro.

**Custo:** suaviza as bordas **junto** com o ruído. Kernel grande demais arredonda o
contorno da folha e altera perímetro e circularidade — exatamente as medidas que o projeto
quer preservar. É a razão de o tamanho do kernel ser decidido por medição, e não por hábito.

Com `sigma = 0.0`, o OpenCV deriva o desvio padrão a partir do kernel.

---

## 12. Filtro de mediana

`suavizar_mediana(imagem, kernel=5)`

**Efeito:** substitui cada pixel pela mediana da vizinhança. Como a mediana **descarta**
valores extremos em vez de os diluir, é muito eficaz contra **ruído impulsivo** — o tipo que
os pequenos artefatos escuros do fundo do Flavia produzem.

Preserva bordas melhor que a média, porque não mistura os dois lados de uma transição.

**Custo:** mais caro, porque exige ordenar a vizinhança de cada pixel. Medido nesta fase:
**2,17 ms contra 0,35 ms** do Gaussiano, em imagem 1024×768 de um canal — cerca de **6×**.

---

## 13. Gaussiano × mediana — comparação, sem vencedor

| | Gaussiano | Mediana |
|---|---|---|
| Ruído de alta frequência | Bom | Bom |
| **Ruído impulsivo** (sal e pimenta) | Dilui os extremos | **Remove os extremos** |
| Preservação de borda | Suaviza | **Preserva melhor** |
| Custo medido (1024×768, 1 canal) | **0,35 ms** | 2,17 ms |

Medição sobre imagem sintética com 5% de ruído impulsivo: a mediana devolveu **mais de 90%
dos pixels extremos** ao valor de fundo, e o erro médio em relação ao valor real ficou
**menor que o do Gaussiano**. Há teste que registra essa comparação.

> **Nenhum vencedor é declarado.** A medição acima vale para *ruído impulsivo em imagem
> sintética*. A escolha do filtro do pipeline é da **Fase 4**, sobre imagens reais e
> avaliada pelo que realmente importa: a qualidade da máscara que a segmentação produz — não
> a suavidade da imagem intermediária.

---

## 14. Normalização — deliberadamente não implementada

Avaliada e **descartada nesta fase**.

Normalizar para `[0,1]` ou padronizar por média e desvio é prática de aprendizado de máquina,
onde a escala das entradas afeta a convergência. **Este projeto não usa aprendizado de
máquina.**

As operações previstas — Otsu, limiar adaptativo, morfologia, contornos — trabalham
diretamente sobre `uint8` em `0..255`, que é o formato nativo do OpenCV. Normalizar exigiria
converter para ponto flutuante e desfazer a conversão depois, gastando memória e tempo sem
produzir nenhuma diferença no resultado.

**Será implementada se e quando alguma operação a exigir** — com a razão registrada.

---

## 15. Testes

### Comando

```bash
cd processamento-imagens
.venv/Scripts/python.exe -m pytest
```

O `pytest.ini` define `testpaths = tests` e fixa a raiz do módulo, o que torna `src`
importável sem instalação.

### Resultado

```
132 passed in 1.50s
```

| Arquivo | Testes | Cobre |
|---|---:|---|
| `test_utils.py` | **37** | Validação de caminho, extensão, dimensões, leitura, erros, nome seguro |
| `test_preprocessing.py` | **72** | Redimensionamento, três conversões, dois filtros, validação de kernel, determinismo |
| `test_isolamento.py` | **23** | Ausência de IA no código e no ambiente |
| **Total** | **132** | **0 falhas** |

Contagens conferidas arquivo a arquivo. Vários testes são parametrizados — os de isolamento,
por exemplo, repetem a verificação para cada arquivo Python do módulo, o que faz 7
verificações distintas renderem 23 casos executados.

### Imagens sintéticas

Todas geradas por NumPy e OpenCV, sem depender do dataset: preta, branca, gradiente,
círculo, retângulo, elipse verde sobre branco (imita o Flavia) e ruído sal e pimenta com
**semente fixa `20260919`**.

A semente é fixa porque um teste que usa ruído aleatório sem semente é um teste que falha de
vez em quando sem que ninguém saiba por quê.

### Determinismo

Requisito da Fase 1, verificado em cinco pontos: leitura, redimensionamento, cada conversão
de cor, cada filtro, e o encadeamento completo. Todos comparam duas execuções por
`np.array_equal` — igualdade exata, não aproximada.

---

## 16. Teste de isolamento

Primeira versão de `test_isolamento.py`, com 14 verificações.

| # | Verificação |
|---|---|
| 1 | Existem arquivos Python para verificar — guarda contra a suíte "passar" por não achar nada |
| 2 | Nenhum arquivo importa biblioteca de IA (27 nomes: torch, tensorflow, sklearn, ultralytics, transformers, ollama, …) |
| 3 | Nenhum arquivo importa cliente HTTP (`requests`, `httpx`, `urllib3`, `aiohttp`) |
| 4 | Nenhum termo proibido no código — inclusive **`cv2.dnn`**, o módulo de redes neurais do próprio OpenCV |
| 5 | Nenhuma referência a `script/ia` |
| 6 | **A camada de IA do site não referencia o módulo de PDI** — a independência vale nos dois sentidos |
| 7 | **Nenhuma biblioteca de IA instalada no ambiente**, mesmo sem import |

A verificação de imports usa `ast`, não expressão regular: analisar a árvore sintática evita
falso positivo em comentário ou string.

### Um falso positivo real, e o que ele ensinou

Na primeira execução, dois testes falharam apontando `src/__init__.py`. O motivo: a docstring
do módulo diz *"não importa nada de `script/ia/`"* — e a varredura textual encontrou o termo.

**A varredura estava certa em olhar; errada em onde olhar.** Reprovar uma docstring que
documenta a ausência forçaria a piorar a documentação para agradar o teste.

Correção: `_codigo_sem_docstrings()` remove docstrings de módulo, classe e função antes da
varredura — usando `ast` para localizá-las com precisão. **Comentários e strings comuns
continuam sendo analisados.**

E, para que a correção não afrouxasse o detector em silêncio, foram acrescentados **dois
testes do próprio detector**:

| Teste | Garante |
|---|---|
| `test_a_varredura_ainda_detecta_violacao_real` | Um arquivo com `import torch`, `cv2.dnn` e `localhost:11434` **em código** continua sendo detectado |
| `test_a_varredura_ignora_termo_apenas_em_docstring` | Um arquivo que cita os termos **apenas em docstring** não é acusado |

> Sem esses dois testes, a correção poderia ter transformado o detector em algo que aprova
> tudo — e ninguém perceberia.

### Pendência registrada

Os testes das **cascas finas** (`cli.py` e `api.py` não importam `cv2` nem `numpy`) não
foram criados: os arquivos ainda não existem. Entram na Fase 8.

---

## 17. Testes em imagens reais do Flavia

### Material

32 imagens do subconjunto `standardleaves` (uma por espécie), já obtido na Fase 2 da fonte
oficial. Copiadas para `processamento-imagens/dataset/dados/amostra-flavia/` —
**diretório ignorado pelo Git**. O pacote completo de 965,7 MB **não foi baixado**.

### Verificações

| Verificação | Resultado |
|---|---|
| Leitura das 32 imagens | ✅ 32/32 sem erro |
| Resolução original | ✅ **32/32 em 1600×1200** |
| Redimensionamento | ✅ 32/32 para **1024×768**, fator **0,640** |
| Conversão para cinza | ✅ separação folha/fundo alta em todas |
| Conversão para HSV | ✅ matiz consistente (§10) |
| Gaussiano e mediana | ✅ sem erro |

### Inspeção visual das saídas

Três imagens de estudo, escolhidas na Fase 2 por representarem casos distintos, tiveram as
saídas intermediárias gravadas em `resultados/temporarios/` (ignorado) e inspecionadas:

| Arquivo | Caso | Observação na saída |
|---|---|---|
| `1.jpg` | Fácil | Folha lanceolada, fundo limpo. Conversão para cinza produz contraste quase binário |
| `16.jpg` | Difícil | Folha brilhante com reflexo; **confirmado visualmente que toca a borda direita** — caso real dos avisos `A001`/`A008` |
| `18.jpg` | Extremo | Acícula fina; cinza mínimo 79, o mais alto dos três, porque há pouco pixel escuro |

---

## 18. Performance

Medido sobre as 32 imagens reais, uma execução por etapa, em milissegundos. São **ordens de
grandeza**, não benchmark — nenhuma otimização foi feita nem é necessária agora.

| Etapa | Mediana | Mínimo | Máximo |
|---|---:|---:|---:|
| Leitura e decodificação | **22,06** | 13,19 | 30,36 |
| Redimensionamento 1600×1200 → 1024×768 | 4,36 | 3,99 | 13,04 |
| BGR → cinza | 0,30 | 0,22 | 0,81 |
| BGR → HSV | 1,36 | 0,97 | 1,83 |
| BGR → RGB | 1,24 | 0,78 | 1,51 |
| Gaussiano, kernel 5 | **0,35** | 0,28 | 0,89 |
| Mediana, kernel 5 | **2,17** | 2,02 | 3,03 |

**Pré-processamento completo (leitura + redimensionamento + cinza + HSV + Gaussiano):
mediana de 28,4 ms por imagem.**

### Duas leituras

1. **A leitura domina** — 22 de 28,4 ms, cerca de 78% do tempo. Decodificar um JPEG de
   1600×1200 custa mais que todas as operações subsequentes somadas. Se algum dia houver
   necessidade de otimizar, é aqui.
2. **A mediana custa ~6× o Gaussiano.** Diferença real, mas irrelevante em valor absoluto:
   2 ms contra 0,35 ms. **Não deve pesar na escolha do filtro** — o critério da Fase 4 é a
   qualidade da máscara, e 2 ms não são argumento contra nada.

---

## 19. Decisões desta fase

| # | Decisão | Motivo |
|---|---|---|
| 1 | `.venv` dentro de `processamento-imagens/` | Módulo autocontido |
| 2 | `imdecode` em vez de `imread` | Separa "arquivo ausente" de "conteúdo inválido"; trata caminho não-ASCII |
| 3 | Não ampliar por padrão | Ampliar não cria informação e inflaria área e perímetro |
| 4 | `INTER_AREA` ao reduzir | Evita serrilhado, que distorceria o perímetro |
| 5 | Código de erro novo `E008` | Erro de parâmetro é categoria distinta de erro de entrada |
| 6 | **Normalização não implementada** | Não há operação que a exija; é hábito de ML, não deste projeto |
| 7 | **Nenhum filtro declarado vencedor** | A comparação pertence à Fase 4, sobre imagens reais |
| 8 | Docstrings excluídas da varredura de isolamento | A varredura deve olhar código; e dois testes provam que o detector continua funcionando |
| 9 | Constantes experimentais marcadas como tais | `LADO_MAXIMO_PX_EXPERIMENTAL`, `KERNEL_PADRAO_EXPERIMENTAL`, `LADO_MINIMO_PX_EXPERIMENTAL` |

---

## 20. Limitações

| # | Limitação |
|---|---|
| 1 | **Valores ainda experimentais:** lado máximo 1024, lado mínimo 64, kernel 5. Nenhum foi medido contra alternativas |
| 2 | **32 imagens não são amostra.** Os dados de matiz e tempo vêm de uma imagem por espécie, não do conjunto de desenvolvimento |
| 3 | **Dataset completo não baixado** — 965,7 MB pendentes para a Fase 4 |
| 4 | **Conjuntos de desenvolvimento e avaliação não sorteados** — o `manifesto.csv` ainda não existe |
| 5 | **Sem tratamento de imagem com canal alfa.** `IMREAD_COLOR` descarta transparência; um PNG com fundo transparente é lido como se o fundo fosse preto |
| 6 | **Sem suporte a EXIF de rotação.** Fotos de celular com orientação em metadados podem ser lidas giradas |
| 7 | **Só uma execução por medição de tempo** — ordem de grandeza, não estatística |
| 8 | **Isolamento é sintático**, não semântico: detecta violação óbvia, não prova ausência formal |

As limitações 5 e 6 não afetam o Flavia, que é JPEG sem alfa e sem EXIF de rotação. Passam a
importar quando o usuário enviar foto própria — ou seja, na Fase 9.

---

## 21. Riscos atualizados

| # | Risco | Estado | Nota |
|---|---|---|---|
| **R9** | Python 3.14 muito recente | 🟢 **Confirmado resolvido** | Wheel `abi3` instalou sem incidente |
| **R12** | Hífen no diretório impede import | 🟢 **Mitigado nesta fase** | Pacote `src`, execução a partir do módulo, `pytest.ini` como âncora |
| **R2** | `.gitignore` | 🟢 **Validado na prática** | `.venv`, `__pycache__`, `.pytest_cache`, dataset e resultados criados de verdade e **nenhum apareceu no Git** |
| **R14** | Perímetro digital distorce circularidade | 🟠 Aberto | Não aplicável ainda; contornos são da Fase 6 |
| **R6** | Segmentação depende de contraste | 🟢 **Evidência favorável** | Cinza com amplitude quase total e matiz consistente nas três imagens |
| **R7** | Limiares arbitrários | 🟠 Aberto | Três constantes experimentais criadas, **todas marcadas como tais** |
| **R16** 🆕 | **Imagens com canal alfa ou EXIF de rotação** | 🟡 Novo | Não afeta o Flavia; afeta upload do usuário na Fase 9 |
| **R17** 🆕 | **Isolamento sintático pode ter ponto cego** | 🟡 Novo | Mitigado por dois testes do próprio detector; não é prova formal |

---

## 22. Verificação do `.gitignore`

Os cinco artefatos foram criados **de verdade** e conferidos:

| Artefato | Existe no disco | Visível ao Git |
|---|:---:|:---:|
| `processamento-imagens/.venv/` | ✅ | ❌ |
| `processamento-imagens/src/__pycache__/` | ✅ | ❌ |
| `processamento-imagens/.pytest_cache/` | ✅ | ❌ |
| `processamento-imagens/dataset/dados/` (32 imagens) | ✅ | ❌ |
| `processamento-imagens/resultados/temporarios/` (15 PNGs) | ✅ | ❌ |

O Git oferece exatamente **11 arquivos**, todos de código ou configuração — nenhum artefato,
nenhuma imagem, nenhum binário.

---

## 23. Regressão legada

```
node scripts/testar-camada-ia.js     →  67 passaram, 0 falharam
node scripts/testar-integracao.js    →  46 passaram, 0 falharam
node scripts/testar-diagnostico.js   →  82 passaram, 0 falharam
node scripts/testar-benchmark.js     →  61 passaram, 0 falharam
                                        ──────────────────────
                                        256 / 256, 0 falhas
```

Esperado, já que nenhum arquivo do site ou da camada de IA foi tocado — mas verificado, não
presumido.

---

## 24. Próxima fase

**Fase 4 — Segmentação.**

| # | Ação |
|---|---|
| 1 | Baixar o Flavia completo para `dataset/dados/` |
| 2 | Escrever o script de seleção estratificada, semente `20260919` |
| 3 | Gerar `manifesto.csv` com 64 imagens de desenvolvimento e 96 de avaliação |
| 4 | Implementar `segmentation.py`: Otsu, limiar adaptativo e faixa em HSV |
| 5 | Comparar os métodos **no conjunto de desenvolvimento**, com critério definido antes |
| 6 | **Decidir o filtro** entre Gaussiano e mediana — pelo efeito na máscara |
| 7 | Fixar `lado_maximo`, `lado_minimo` e `kernel` com medição |
| 8 | Definir a faixa de verde em HSV a partir da distribuição observada |
| 9 | Documentar em `04-SEGMENTACAO.md` |

---

*Fase 3 concluída em 19 de setembro de 2026, sobre o commit `1d307fb`. 132 testes do módulo
e 256 asserções legadas, todos passando.*
