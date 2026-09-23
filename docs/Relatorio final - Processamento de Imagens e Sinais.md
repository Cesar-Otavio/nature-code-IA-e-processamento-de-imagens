# Relatório final — Processamento de Imagens e Sinais

**Nature Code: análise morfológica de folhas**

> Relatório da disciplina de **Processamento de Imagens e Sinais**. É autocontido: resume o
> problema, cada etapa do pipeline com a sua justificativa, a avaliação e os resultados.
> Cada seção aponta o documento de fase de onde o conteúdo vem; onde houver divergência,
> vale o documento de fase.
>
> Relatório da outra disciplina: [`Relatorio final - IA.md`](Relatorio%20final%20-%20IA.md).
> Integração entre as duas: [`Relatorio final - IA + Processamento de Imagens e Sinais.md`](Relatorio%20final%20-%20IA%20+%20Processamento%20de%20Imagens%20e%20Sinais.md).

> **100 % de sucesso operacional não significa 100 % de segmentação correta.** Neste
> relatório, *sucesso operacional* quer dizer apenas que o pipeline chegou ao fim sem erro
> com um objeto medido. Se esse objeto é de fato a folha, só a **inspeção humana** diz.
>
> As regras geométricas **não têm acurácia**: não existe referência de verdade para
> categorias como "alongamento moderado". Nada aqui é medida de acerto.

---

## 1. Identificação do projeto

| | |
|---|---|
| **Projeto** | Nature Code — módulo de análise morfológica de folhas |
| **Disciplina** | Processamento de Imagens e Sinais |
| **Instituição** | Universidade do Sagrado Coração — Bauru/SP |
| **Curso** | Ciência da Computação |
| **Repositório** | https://github.com/Cesar-Otavio/nature-code-IA-e-processamento-de-imagens |
| **Código do módulo** | [`processamento-imagens/`](../processamento-imagens/) |
| **Versão avaliada** | Tag `fase-9-completa` → commit `4b66981` (pipeline congelado) |

---

## 2. Integrantes

- Amanda Pazold dos Santos
- Cesar Otavio da Silva Boiani
- Giovana Giraldeli
- Giovani Nogueira Pires
- Marcus Vinicius da Silva Capeteruchi

---

## 3. Contexto

O Nature Code é um site educacional de Biologia em HTML, CSS e JavaScript, com os módulos
Reino Animal, Plantas e Ecossistemas. No módulo **Plantas**, um botão leva à página
**Análise Morfológica de Folhas**, onde o aluno envia a imagem de uma folha e recebe a
máscara, o contorno, as medidas e uma descrição geométrica.

O processamento é feito por um pipeline em **Python, OpenCV e NumPy**, exposto por uma API
Flask local e por uma CLI.

---

## 4. Objetivo do módulo PDI

Dada a imagem de **uma folha isolada sobre fundo claro**, produzir:

1. a **máscara binária** da folha;
2. o **contorno** do objeto principal;
3. **características morfológicas** em pixels;
4. uma **descrição geométrica** por regras explícitas.

**Fora do escopo, por definição:** identificação de espécie, diagnóstico de doença,
medidas em unidade física (não há objeto de referência) e várias folhas por imagem.
Contrato de entrada e saída: [`01-DEFINICAO-PROBLEMA.md`](processamento-imagens/01-DEFINICAO-PROBLEMA.md).

---

## 5. Separação entre PDI e IA

> **O PDI não usa inteligência artificial** — nenhuma rede neural, nenhum modelo treinado,
> nenhum aprendizado de máquina, nenhuma LLM. As regras são condições escritas por pessoas.
> O resultado é **determinístico**: a mesma imagem produz sempre o mesmo resultado.
>
> **O PDI não identifica espécies.** Descreve a forma, não diz que planta é.

| | PDI | IA |
|---|---|---|
| Código | `processamento-imagens/`, `script/pdi/` | `script/ia/` |
| Serviço | API Flask, `127.0.0.1:5000` | Ollama, `localhost:11434` |
| Ligação | Só o site, que dá acesso às duas funcionalidades | |

Verificações automatizadas ([`test_isolamento.py`](../processamento-imagens/tests/test_isolamento.py)):
o Python do PDI não importa nenhuma das 27 bibliotecas de IA/ML verificadas nem usa
`cv2.dnn`; o JavaScript do PDI não fala com o Ollama; a página de análise não carrega
`script/ia/`; a camada de IA não referencia o PDI.

---

## 6. Dataset Flavia

| | |
|---|---|
| Nome | **Flavia Leaf Dataset** |
| Imagens | 1.907, de **32 espécies** |
| Formato | JPEG 1600×1200, fundo **branco** uniforme, uma folha por imagem |
| Fonte oficial | http://flavia.sourceforge.net/ |
| Projeto | https://sourceforge.net/projects/flavia/ |
| Download | https://sourceforge.net/projects/flavia/files/Leaf%20Image%20Dataset/1.0/Leaves.tar.bz2/download |
| Artigo | Stephen Gang Wu et al., *A Leaf Recognition Algorithm for Plant Classification Using Probabilistic Neural Network*, IEEE ISSPIT, 2007 |

Escolhido por ter folhas isoladas em fundo controlado — a condição do problema definido na
§4. **O dataset não está no repositório**; o [`manifesto.csv`](../processamento-imagens/dataset/manifesto.csv)
registra exatamente quais imagens foram usadas. Ressalva de licença: o SourceForge declara
o *projeto* Flavia como GPLv2; não foi localizada licença específica para as imagens. Uso
estritamente acadêmico, sem redistribuição.

Detalhes: [`02-DATASET.md`](processamento-imagens/02-DATASET.md).

---

## 7. Protocolo desenvolvimento × avaliação

| Conjunto | Imagens | Uso |
|---|---:|---|
| **Desenvolvimento** | 64 (2 por espécie) | Todas as decisões, comparações e calibrações |
| **Avaliação** | 96 (3 por espécie) | **Tocado uma única vez**, na Fase 10, com o pipeline congelado |

Amostragem aleatória estratificada por espécie, **semente `20260919`**, conjuntos
disjuntos. O critério de inspeção visual (correta · aceitável · falha) foi definido **antes**
de ver os resultados (Fase 2 §15). Antes da avaliação, o pipeline foi congelado na tag
`fase-9-completa`, e o script de avaliação compara os **SHA-256 dos 9 arquivos do
algoritmo** antes e depois — e recusa rodar se houver diferença.

---

## 8. Pré-processamento

```
validação → leitura → redimensionamento → suavização
```

| Etapa | O que faz |
|---|---|
| Validação | Existência, extensão (JPG, JPEG, PNG, BMP), tamanho ≤ 12 MB, decodificação real (arquivo que não é imagem é recusado mesmo com extensão `.jpg`), resolução mínima |
| Leitura | Orientação EXIF aplicada em JPEG; canal alfa de PNG composto sobre branco |
| Redimensionamento | **Lado maior ≤ 1024 px**, proporção preservada — as medidas e o tempo não dependem da resolução original |
| Suavização | Filtro **Gaussiano 5×5** (§11) |

Erros têm códigos estáveis (`E001` a `E011`), usados pela CLI, pela API e pela página.
Detalhes: [`03-PRE-PROCESSAMENTO.md`](processamento-imagens/03-PRE-PROCESSAMENTO.md).

---

## 9. Espaços de cores

O pipeline trabalha com três representações:

| Espaço | Uso |
|---|---|
| **BGR/RGB** | Leitura (o OpenCV lê em BGR) e estatísticas de cor da folha |
| **Tons de cinza** | Base do Otsu e do limiar adaptativo, comparados na Fase 4; imagem intermediária de visualização |
| **HSV** | **Segmentação** e estatísticas de cor |

No OpenCV, em imagens de 8 bits, o matiz **H** vai de 0 a 179 (metade dos graus), e
saturação **S** e brilho **V** vão de 0 a 255.

---

## 10. Justificativa do HSV

No espaço **RGB**, os três canais misturam **cor** e **intensidade**: quando a luz muda — uma
sombra, um reflexo, um gradiente de iluminação —, R, G e B mudam juntos. Uma regra fixa do
tipo "G alto, R e B baixos" teria de ser recalibrada a cada condição de luz, e um verde
escuro sombreado e um cinza escuro ficam próximos no RGB.

O **HSV** separa essas componentes:

- **H (matiz)** carrega a cor — o verde da folha fica num intervalo de matiz que varia
  pouco com o brilho;
- **S (saturação)** separa cor de branco e cinza — o fundo branco do Flavia tem saturação
  ≈ 0, e exigir saturação mínima também descarta ruído;
- **V (brilho)** fica isolado, e só precisa de um piso para descartar pixels escuros demais.

No cenário do projeto — **folha verde sobre fundo branco** —, isso permite segmentar por
**cor, não por brilho**. Na Fase 4, o HSV foi comparado no conjunto de desenvolvimento com
**Otsu** (intensidade em cinza), **limiarização adaptativa** e combinações:

| Critério | HSV | Otsu | Adaptativo |
|---|---:|---:|---:|
| Máximo de componentes na máscara | **3** | 66 | 2.148 |
| Imagens com mais de um componente | **12/64** | 22/64 | 64/64 |
| Falhas na inspeção visual | **0/64** | — | — |

O HSV também manteve a folha inteira em imagens com brilho especular e sombra, onde
métodos por intensidade falham.

> **Limite desta justificativa:** a limiarização direta em **RGB** não foi implementada
> como estratégia separada na Fase 4; a comparação experimental foi contra Otsu e
> adaptativo. O argumento contra o RGB é o de separação entre cor e brilho, acima. E o
> ponto fraco do HSV foi declarado antes da avaliação: **folha que não é verde** (seca,
> amarelada, avermelhada) e **fundo verde** — ambos confirmados na Fase 11 (§24).

Detalhes: [`04-SEGMENTACAO.md`](processamento-imagens/04-SEGMENTACAO.md).

---

## 11. Filtro Gaussiano

**Kernel 5×5**, com σ derivado do kernel pelo OpenCV (`sigma = 0`). Reduz ruído e textura
fina que fragmentariam a máscara; o custo é suavizar também as bordas, por isso o kernel
foi decidido por medição e não por hábito.

Gaussiano e **mediana** foram comparados: a mediana remove melhor ruído impulsivo, mas é
cerca de 6× mais lenta; no conjunto de desenvolvimento, **o Gaussiano deu a melhor máscara**
combinado ao HSV, e foi escolhido **por qualidade de máscara, não por velocidade**.

Detalhes: [`03-PRE-PROCESSAMENTO.md`](processamento-imagens/03-PRE-PROCESSAMENTO.md) §11–13 ·
[`04-SEGMENTACAO.md`](processamento-imagens/04-SEGMENTACAO.md) §10.

---

## 12. Segmentação

Limiarização em HSV sobre a imagem suavizada:

| Canal | Faixa |
|---|---|
| **H** | **25 – 95** |
| **S** | **40 – 255** |
| **V** | **20 – 255** |

Pixel dentro das três faixas → **folha (255)**; fora → **fundo (0)**. A faixa foi
calibrada sobre 16,2 milhões de pixels de folha do conjunto de desenvolvimento. Achado
medido: a faixa **justa** de matiz, tirada dos próprios percentis (H 43–67), é **pior** —
recorta bordas, nervuras e áreas de brilho e fragmenta a máscara em até **409
componentes**, contra **3** da faixa adotada. Quem separa a folha do fundo branco é a
**saturação mínima** (o fundo tem S ≈ 0); a faixa de H serve para excluir objetos
coloridos que não sejam verdes.

---

## 13. Limpeza morfológica

**Abertura e fechamento foram medidos e não adotados**, porque alteravam a geometria da
borda — e a geometria é justamente o que o módulo mede.

A limpeza adotada é por componentes:

- **remove** componentes com área **< 0,1 %** da área do maior componente;
- **preenche** buracos internos com área **< 0,2 %** da do maior componente.

Resultado no desenvolvimento: **0,0000 % de alteração no perímetro** e 44 das 64 máscaras
intactas. Detalhes: [`05-MORFOLOGIA.md`](processamento-imagens/05-MORFOLOGIA.md).

---

## 14. Contornos

`cv2.findContours` com **`RETR_EXTERNAL`** (só contornos externos; igual a `RETR_TREE` nas
64 imagens de desenvolvimento, porque os buracos já foram tratados) e
**`CHAIN_APPROX_SIMPLE`** (−46 % de pontos, sem perda de forma).

Viés medido: o **perímetro digital** superestima bordas curvas em ~5 % (um círculo digital
perfeito tem circularidade ≈ 0,90, não 1,0). Foi medido e documentado, não corrigido.
Detalhes: [`06-CONTORNOS.md`](processamento-imagens/06-CONTORNOS.md).

---

## 15. Seleção do objeto principal

O objeto principal é o **maior contorno**. São registrados a **dominância** (fração da área
do maior sobre o total) e avisos técnicos quando a seleção é duvidosa:

| Aviso | Quando |
|---|---|
| `multiplos_contornos` | Mais de um contorno relevante |
| `selecao_ambigua` | O segundo maior contorno tem mais da metade da área do primeiro |
| `objeto_toca_borda` | O objeto toca a borda da imagem — pode estar cortado |

Esse critério é adequado a uma folha isolada em fundo limpo. Com várias folhas ou fundo
verde, o maior objeto verde pode não ser a folha de interesse — o que a Fase 11 observou.

---

## 16. Características

Calculadas sobre o contorno principal, **em pixels**:

| Característica | Definição resumida |
|---|---|
| Área, perímetro | Do contorno |
| **Elongação** | Lado maior ÷ lado menor da caixa de área mínima (`minAreaRect`) |
| **Circularidade** | 4π · área ÷ perímetro² |
| **Solidez** | Área ÷ área do envelope convexo |
| **Extent** | Área ÷ área da caixa alinhada (e da caixa rotacionada) |
| **Razão perímetro/hull** | Perímetro ÷ perímetro do envelope convexo — complexidade da borda |
| **Orientação e anisotropia** | Pelos autovalores da matriz de momentos centrais (μ20, μ02, μ11); a anisotropia, em [0, 1], mede quão definido é o eixo principal |
| Cor | Médias e medianas em RGB e HSV, proporção de verde |
| Qualidade | Centroide, distância à borda, número de contornos, dominância |

Cada uma tem definição, fórmula, intervalo e limitação em
[`07-CARACTERISTICAS.md`](processamento-imagens/07-CARACTERISTICAS.md).

---

## 17. Classificação determinística

Cinco atributos, cada um por **limiares fixos** derivados de quartis e vales do conjunto de
desenvolvimento:

| Atributo | Característica | Limiares | Categorias |
|---|---|---|---|
| Alongamento | elongação | 1,5 · 3,0 · 6,0 | baixa · moderada · alta · extrema |
| Concavidade | solidez (+ elongação) | 0,70 · 0,92 | baixa · moderada · alta · ambígua |
| Compacidade | circularidade | 0,40 · 0,65 | baixa · moderada · alta |
| Complexidade da borda | razão perímetro/hull | 1,13 · 1,30 | regular · moderada · complexa |
| Orientação | anisotropia | 0,05 · 0,30 | indefinida · pouco definida · bem definida |

Cada resultado traz o valor usado, o limiar aplicado e a **margem relativa** até o limiar
mais próximo (não é probabilidade); valores perto do limiar geram aviso de caso limítrofe.
A concavidade vira **ambígua** com elongação extrema, porque uma folha acicular curvada tem
solidez baixa sem ter recorte.

**Não é IA e não tem acurácia:** são condições `if/elif`, sem treinamento nem referência de
verdade. Detalhes: [`08-CLASSIFICACAO-DETERMINISTICA.md`](processamento-imagens/08-CLASSIFICACAO-DETERMINISTICA.md).

---

## 18. Pipeline completo

```
imagem → validação → resize → Gaussiano → HSV → segmentação → morfologia → contornos
       → objeto principal → features → regras determinísticas → resultado
```

| Parâmetro congelado | Valor |
|---|---|
| Lado máximo | **1024 px** |
| Filtro | **Gaussiano 5×5** |
| Segmentação | **H 25–95 · S 40–255 · V 20–255** |
| Limpeza | Componentes < 0,1 % removidos · buracos < 0,2 % preenchidos |
| Contornos | `RETR_EXTERNAL` + `CHAIN_APPROX_SIMPLE`; maior contorno |
| Regras | Limiares da Fase 8 (§17) |

Toda a lógica está em [`src/pipeline.py`](../processamento-imagens/src/pipeline.py) e nos
módulos que ele chama; CLI e API são cascas finas, verificadas por teste. A saída é um JSON
com 11 blocos sempre presentes (sem NaN nem caminho absoluto), um resumo textual e **8
imagens intermediárias**: original, cinza, matiz, suavizada, máscara, máscara limpa,
contorno e resultado anotado.

Detalhes: [`09-PIPELINE-INTEGRACAO.md`](processamento-imagens/09-PIPELINE-INTEGRACAO.md).

---

## 19. CLI

```cmd
cd processamento-imagens
.venv\Scripts\python.exe -m src.cli <imagem>
```

Opções `--json-apenas`, `--sem-imagens`, `--saida DIR` e `--verboso`. Códigos de saída:
**0** sucesso · **1** nenhuma folha · **2** erro de entrada · **3** erro interno.

---

## 20. API Flask

```cmd
cd processamento-imagens
.venv\Scripts\python.exe -m src.api
```

| | |
|---|---|
| Endereço | `127.0.0.1:5000` — só a própria máquina, `debug=False` |
| Rotas | `GET /health` · `POST /api/processar-folha` · `GET /api/resultado/<id>/<arquivo>` |
| Segurança | Upload ≤ 12 MB · verificação de conteúdo real · CORS com lista fechada de origens · proteção contra travessia de caminho · upload original sempre apagado · resultados antigos removidos por TTL |

---

## 21. Interface web

[`pages/modulos/analise-folha.html`](../pages/modulos/analise-folha.html), com o código em
[`script/pdi/`](../script/pdi/), acessada por **Plantas → Análise Morfológica de Folhas**.

Mostra o aviso de que **não usa IA e não identifica espécies**, as condições ideais de foto,
o estado do serviço, o upload com pré-visualização, as imagens (analisada, máscara,
resultado anotado com legenda), as medidas, a descrição e os avisos. Todo texto vindo da
API entra por `textContent`. Com a API desligada, a página explica como iniciá-la e o resto
do site continua funcionando.

Testada no Node com DOM simulado e **manualmente no navegador**: upload, preview,
processamento, troca e remoção de imagem, arquivo inválido, API offline e recuperação,
celular, tablet e desktop ([`TESTES-MANUAIS-FINAIS.md`](TESTES-MANUAIS-FINAIS.md) §2).

---

## 22. Avaliação controlada — Fase 10

Pipeline congelado, executado **uma única vez** sobre o conjunto reservado.

| Item | Resultado |
|---|---|
| Imagens | **96** — **32 espécies × 3 por espécie**, nunca usadas no desenvolvimento |
| Processadas | **96/96** |
| Erros | **0** |
| Taxa de processamento válido | **100 %** |
| Com aviso técnico / sem | 65 / 31 |
| Com pelo menos um atributo limítrofe | 62 |
| Contornos por imagem | 1 em todas; nenhuma tocando a borda |
| Tempo mediano por imagem | ~285 ms |
| Determinismo | 5 imagens reprocessadas + 12 com visualização: resultados idênticos |
| **Pipeline** | **Não recalibrado** — 9 hashes SHA-256 idênticos antes e depois |

Duas descobertas registradas **sem ajuste**: os "vales" que justificavam os limiares de
concavidade (0,70) e orientação (0,30) **não estão vazios** na avaliação (7 e 6 imagens), e
o limiar de complexidade da borda (1,13) fica numa região densa — é o atributo com mais
casos limítrofes (35), como a Fase 8 previa.

Detalhes: [`10-AVALIACAO-FINAL.md`](processamento-imagens/10-AVALIACAO-FINAL.md).

---

## 23. Inspeção humana da Fase 10

Os 12 casos foram **selecionados automaticamente**, por critérios objetivos (extremos de
elongação, circularidade, solidez e razão perímetro/hull; mais atributos limítrofes; e
controles sem aviso), e inspecionados visualmente com o critério da Fase 2.

| Caso | Motivo da seleção | Julgamento |
|---|---|---|
| 2370, 2353, 2417 | Maior elongação; menor circularidade | `correta` |
| 1302, 1282, 1269 | Menor solidez; maior razão perímetro/hull | `correta` |
| 2194, 2458, 3026 | Mais atributos limítrofes | `correta` |
| 1052, 1191, 1195 | Controle sem aviso técnico | `correta` |

**12/12 classificados como `correta`**: folha principal segmentada, máscara e contorno
adequados, e **nenhuma alteração do pipeline**. Observações:

- **1302** — orientação pouco/não confiável, coerente com a geometria quase simétrica da
  folha; não é erro de segmentação;
- **3026** — a caixa mínima rotacionada pode ultrapassar visualmente a imagem;
  comportamento conhecido do `minAreaRect`, não falha de segmentação;
- **2370, 2353, 2417** — casos extremamente alongados, com geometria observada coerente.

As outras 84 imagens não foram inspecionadas individualmente. Registro:
[`fase10-casos-inspecao.csv`](processamento-imagens/dados-avaliacao/fase10-casos-inspecao.csv).

---

## 24. Robustez externa — Fase 11

O mesmo pipeline congelado foi executado sobre **9 imagens externas ao Flavia**, obtidas de
fontes externas, convertidas para JPG, **nunca usadas no desenvolvimento** e escolhidas para
representar condições visuais diferentes: fundo natural, céu, contraluz, várias folhas.
As imagens **não são versionadas**.

| Métrica | Resultado |
|---|---:|
| Imagens externas | 9 |
| Processadas operacionalmente | **9/9** |
| Erros | **0** |
| Com aviso técnico | 9 |
| Objeto tocando a borda | 8 |
| Mais de um contorno | 6 |
| Hashes do pipeline | Idênticos antes e depois |

Os avisos já indicavam problema — no Flavia, nenhuma imagem tocou a borda —, mas aviso não
é diagnóstico. Em 6 das 9 imagens, a máscara ocupou mais da imagem do que em **qualquer**
imagem do Flavia; em duas, mais de 99 % do quadro.

Detalhes: [`11-ROBUSTEZ-FOTOS-EXTERNAS.md`](processamento-imagens/11-ROBUSTEZ-FOTOS-EXTERNAS.md) ·
protocolo em [`11-PROTOCOLO-FOTOS-EXTERNAS.md`](processamento-imagens/11-PROTOCOLO-FOTOS-EXTERNAS.md).

---

## 25. Inspeção humana da Fase 11

Todas as 9 imagens foram inspecionadas.

| Pergunta | sim | parcial | não |
|---|---:|---:|---:|
| A folha principal foi segmentada? | 2 | 5 | 2 |
| A máscara corresponde à folha? | 0 | 2 | 7 |
| O contorno acompanha a borda real? | 0 | 2 | 7 |
| **O resultado é útil?** | **0** | **2** | **7** |

| Problema principal | Imagens |
|---|---:|
| Fundo confundido com folha | **5** |
| Objeto secundário incorporado | **2** |
| Folha parcialmente perdida | **1** |
| Cor fora da faixa HSV | **1** |
| Resultado adequado | 0 |

As quatro falhas decorrem de propriedades do método conhecidas antes da execução:
segmentação só por cor, faixa calibrada para folha verde em fundo branco, e seleção pelo
maior componente. **Nenhuma motivou ajuste de parâmetro.**

---

## 26. Comparação Fase 10 × Fase 11

| | Flavia — Fase 10 | Imagens externas — Fase 11 |
|---|---|---|
| Condição | Fundo branco controlado | Fundo e iluminação não controlados |
| Imagens | 96 | 9 |
| Processamento sem erro | 96/96 (100 %) | 9/9 (100 %) |
| Objeto tocando a borda | 0 | 8 |
| Mais de um contorno | 0 | 6 |
| Inspeção humana | 12 casos selecionados | Todas as 9 |
| **Resultado da inspeção** | **12/12 `correta`** | **0 adequado · 2 parciais · 7 inadequados** |

**A taxa de processamento é idêntica e não distingue os dois cenários.** O que os distingue
é a inspeção humana. O pipeline apresentou 100 % de sucesso operacional nas 9 imagens
externas, mas baixa robustez visual fora das condições do Flavia: o método funciona bem no
domínio controlado para o qual foi desenvolvido e **não generaliza de forma confiável para
fotografias naturais complexas** sem novas estratégias de segmentação.

---

## 27. Testes

| Suíte | Comando | Resultado |
|---|---|---|
| PDI | `cd processamento-imagens` → `.venv\Scripts\python.exe -m pytest` | Todos passam; 1 pulado no Windows (link simbólico sem permissão) — contagem atual no [`CHECKLIST-ENTREGA-FINAL.md`](CHECKLIST-ENTREGA-FINAL.md) |

Os testes cobrem cada etapa do pipeline, o contrato JSON, a CLI, a API (inclusive
segurança), o isolamento em relação à IA, o comportamento da página com DOM simulado, a
infraestrutura das Fases 10 e 11 e os links da documentação. Os testes críticos foram
verificados com **mutantes** — versões sabotadas do código que os testes precisam detectar.
Manualmente: API, CLI e interface ([`TESTES-MANUAIS-FINAIS.md`](TESTES-MANUAIS-FINAIS.md)).

---

## 28. Limitações

1. Calibrado e avaliado no **Flavia** — fundo branco, iluminação controlada.
2. **Robustez externa limitada** (Fase 11): 0 de 9 imagens externas com resultado adequado.
3. Segmentação **só por cor**: folhas não verdes e fundos verdes são pontos fracos.
4. Seleção pelo **maior componente**: falha com várias folhas ou objetos verdes maiores.
5. Medidas em **pixels**, sem calibração física.
6. **Não há referência de verdade** para as categorias geométricas.
7. Perímetro digital com viés de ~5 %; `minAreaRect` pode divergir do eixo principal;
   `proporcao_verde` tem viés circular (é medida sobre a máscara definida pelo verde).
8. Inspeção humana da Fase 10 limitada a 12 das 96 imagens.
9. Servidor de desenvolvimento do Flask — adequado a uso local, não a publicação.

---

## 29. Ameaças à validade

| Ameaça | Efeito |
|---|---|
| Desenvolvimento e avaliação vêm do mesmo dataset | A avaliação reservada protege contra ajuste caso a caso, não contra viés do dataset |
| Limiares derivados de 64 imagens | Heurísticas; os vales de dois limiares não se confirmaram na avaliação |
| Inspeção humana subjetiva | É a única referência disponível; não houve segunda inspeção independente registrada |
| Fase 11 com 9 imagens escolhidas manualmente | Resultado descritivo; condições combinadas impedem atribuir cada falha a uma causa só |
| Imagens externas de origem desconhecida | Compressão e edição prévias podem ter alterado as cores |
| Determinismo verificado numa só máquina | Outra versão do OpenCV pode mudar valores |

---

## 30. Reprodutibilidade

| O quê | Como |
|---|---|
| Ambiente | [`requirements.txt`](../requirements.txt) na raiz → versões fixadas (NumPy 2.5.3, OpenCV 5.0.0.93, Flask 3.1.3); verificado em ambiente virtual limpo |
| Dataset | Download da fonte oficial + [`manifesto.csv`](../processamento-imagens/dataset/manifesto.csv) com a seleção exata, semente `20260919` |
| Pipeline avaliado | Tag `fase-9-completa` (`4b66981`) + hashes SHA-256 antes e depois de cada avaliação |
| Resultados da Fase 10 | [`dados-avaliacao/`](processamento-imagens/dados-avaliacao/) — por imagem, resumo, hashes e inspeção |
| Resultados da Fase 11 | [`dados-robustez/`](processamento-imagens/dados-robustez/) — manifesto, resultados, hashes e inspeção (imagens não versionadas) |
| Execução | README raiz §9–10 · [`processamento-imagens/README.md`](../processamento-imagens/README.md) |

---

## 31. Conclusão

O módulo resolve com **processamento digital de imagens clássico, sem IA**, a descrição
geométrica de uma folha: cada etapa — redimensionamento a 1024 px, Gaussiano 5×5, HSV com
H 25–95, S 40–255 e V 20–255, limpeza por componentes, contornos externos, características
e regras fixas — foi **escolhida por medição no conjunto de desenvolvimento**, e o pipeline
foi **congelado antes de ser avaliado**.

No domínio para o qual foi projetado, o resultado é consistente: **96/96 imagens
reservadas processadas sem erro**, de forma determinística, com o algoritmo provadamente
inalterado, e **12/12 casos inspecionados classificados como `correta`**. Fora desse
domínio, o pipeline continuou executando sem erro nas 9 imagens externas, mas a inspeção
humana mostrou **0 resultados adequados, 2 parciais e 7 inadequados**.

A lição central é metodológica: **100 % de sucesso operacional não significa 100 % de
segmentação correta.** Só a inspeção humana separou os dois cenários — e o limite
encontrado, a dependência de fundo e iluminação controlados, foi registrado como resultado,
não corrigido às escondidas.
