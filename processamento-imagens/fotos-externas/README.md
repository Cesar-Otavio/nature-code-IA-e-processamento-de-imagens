# Fotos externas — Fase 11

Esta pasta recebe as **fotografias reais de folhas** tiradas pela equipe, para testar o
pipeline fora do ambiente controlado do dataset Flavia.

> **As fotos NÃO são versionadas.** Tudo o que for colocado em `imagens/` é ignorado pelo
> Git. Fotos podem carregar dados da câmera, localização (GPS) ou elementos pessoais no
> fundo. Só este README e o `manifesto.csv` entram no repositório.
>
> **O pipeline não muda por causa destas fotos.** Se ele falhar numa foto real, a falha é
> o resultado da avaliação — não um motivo para ajustar o algoritmo.

O protocolo completo de captura está em
[`docs/processamento-imagens/11-PROTOCOLO-FOTOS-EXTERNAS.md`](../../docs/processamento-imagens/11-PROTOCOLO-FOTOS-EXTERNAS.md).

---

## Passo a passo

### 1. Tirar as fotos

Entre **10 e 15 fotos** (de preferência **12**), com celular ou câmera, variando fundo,
luz, posição e distância, conforme o protocolo. Cada foto deve ter **uma folha principal**.

Não fotografe rostos, documentos, telas ou qualquer informação pessoal. Não edite as
fotos antes, não use capturas de tela e não use imagens geradas por IA.

### 2. Copiar para `imagens/`

Coloque os arquivos **diretamente** em `fotos-externas/imagens/`, sem subpastas.
Formatos aceitos: **`.jpg`, `.jpeg`, `.png`**. Use nomes simples, sem espaços nem
acentos, por exemplo `folha-01.jpg`.

### 3. Preencher `manifesto.csv`

Uma linha por foto, depois do cabeçalho:

```text
id,arquivo,fundo,iluminacao,posicao,distancia,formato,observacao
```

| Coluna | Valores aceitos |
|---|---|
| `id` | `EXT001`, `EXT002`, … (único) |
| `arquivo` | nome exato do arquivo em `imagens/` (único) |
| `fundo` | `claro` · `escuro` · `colorido` · `irregular` |
| `iluminacao` | `natural` · `artificial` · `sombra` · `desigual` |
| `posicao` | `centralizada` · `inclinada` · `proxima_borda` · `deslocada` |
| `distancia` | `grande` (folha ocupa quase toda a foto) · `media` · `pequena` (folha pequena no quadro) |
| `formato` | `JPG` · `JPEG` · `PNG` (tem de corresponder à extensão) |
| `observacao` | texto livre, opcional — sem vírgulas |

**Exemplo de linha**, com nome fictício — **não é um resultado nem uma foto real**:

```text
EXT001,folha-01.jpg,claro,natural,centralizada,media,JPG,
```

Para conferir o manifesto sem processar nada:

```bash
cd processamento-imagens
.venv/Scripts/python.exe avaliar_fotos_externas.py verificar
```

Linhas inválidas são apontadas com o motivo. Ao avaliar, elas são registradas e **não**
são processadas; as demais seguem normalmente.

### 4. Executar a avaliação

```bash
cd processamento-imagens
.venv/Scripts/python.exe avaliar_fotos_externas.py
```

O script confere que o pipeline está idêntico ao congelado (hashes), processa cada foto e
gera, para **todas**, as 8 imagens intermediárias em `resultados/robustez-fase11/<id>/`
(também ignoradas pelo Git). Os resultados numéricos vão para
`docs/processamento-imagens/dados-robustez/`.

Sem fotos, o script só avisa e termina normalmente:

```text
Nenhuma foto externa disponível para avaliação.
Adicione as imagens em fotos-externas/imagens/ e preencha o manifesto.csv.
```

### 5. Revisar `fase11-inspecao.csv`

Abra as imagens de cada foto em `resultados/robustez-fase11/<id>/` (principalmente
`05-mascara-limpa.png` e `07-final.png`) e preencha
`docs/processamento-imagens/dados-robustez/fase11-inspecao.csv`:

| Coluna | Valores |
|---|---|
| `folha_principal_segmentada` | `sim` · `parcial` · `nao` |
| `mascara_visual_adequada` | `sim` · `parcial` · `nao` |
| `contorno_visual_adequado` | `sim` · `parcial` · `nao` |
| `resultado_util` | `sim` · `parcial` · `nao` |
| `problema_principal` | uma das categorias abaixo |
| `observacao_humana` | texto livre |

Categorias de `problema_principal`: `fundo confundido com folha` · `folha parcialmente
perdida` · `sombra incorporada` · `objeto secundario incorporado` · `folha fragmentada` ·
`folha nao detectada` · `contorno inadequado` · `recorte pela borda` · `cor fora da faixa`
· `resultado adequado` · `outro`.

Depois, para resumir a revisão:

```bash
.venv/Scripts/python.exe avaliar_fotos_externas.py inspecao
```

> Depois que a inspeção tiver algum campo preenchido, o script **se recusa** a rodar a
> avaliação de novo, para não apagar o julgamento da equipe.
