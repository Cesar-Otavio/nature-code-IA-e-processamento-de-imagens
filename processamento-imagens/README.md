# Nature Code — Processamento de Imagens e Sinais

**Análise Morfológica de Folhas** por processamento digital clássico de imagens.

> **Este módulo não utiliza inteligência artificial e não identifica espécies.**
> Não há rede neural, modelo treinado, aprendizado de máquina nem LLM. Todo o
> processamento é determinístico: a mesma imagem produz sempre o mesmo resultado.

O módulo mede a forma de uma folha — área, perímetro, alongamento, recorte da borda,
orientação — e descreve essas medidas em termos geométricos. Ele é **independente** do
módulo de Inteligência Artificial do Nature Code (os quizzes com Ollama): nenhum dos dois
importa o outro, e há testes que verificam isso.

---

## Pipeline

```
imagem → validação → leitura → redimensionamento → filtro Gaussiano → segmentação HSV
       → limpeza morfológica → contornos → objeto principal → características
       → classificação determinística → resultado JSON + imagens intermediárias
```

---

## 1. Instalar o Python

Python **3.14** foi o usado na validação (3.12 ou superior deve funcionar).
Baixe em https://www.python.org/downloads/ e, no Windows, marque **"Add python.exe to PATH"**.

```bash
python --version
```

## 2. Criar o ambiente virtual

A partir da pasta do módulo:

```bash
cd processamento-imagens
python -m venv .venv
```

## 3. Ativar

| Sistema | Comando |
|---|---|
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Windows (cmd) | `.venv\Scripts\activate.bat` |
| Windows (Git Bash) | `source .venv/Scripts/activate` |
| Linux / macOS | `source .venv/bin/activate` |

## 4. Instalar as dependências

Somente para executar:

```bash
python -m pip install -r requirements.txt
```

Para executar **e** rodar os testes:

```bash
python -m pip install -r requirements-dev.txt
```

| Pacote | Uso |
|---|---|
| `numpy` | Matrizes de imagem |
| `opencv-python` | Leitura, filtros, segmentação, contornos |
| `Flask` | API local |
| `pytest` | Testes (só em `requirements-dev.txt`) |

## 5. Rodar os testes

```bash
python -m pytest
```

Esperado: **todos os testes passando** (886 na versão atual, mais 1 pulado no Windows; num clone sem o dataset, o teste que depende dele também é pulado). Os testes não precisam do
dataset — usam imagens sintéticas geradas no próprio teste.

Os testes de comportamento da página web (`tests/test_interface_web.py`) executam o
JavaScript no **Node.js**, que o projeto já usa nas suítes da camada de IA. Sem Node,
esses testes aparecem como *skipped* — os demais rodam normalmente.

## 6. Usar pela linha de comando

```bash
python -m src.cli caminho/da/folha.jpg
```

| Opção | Efeito |
|---|---|
| `--json-apenas` | Imprime somente o JSON (para uso em scripts) |
| `--sem-imagens` | Não gera as imagens intermediárias |
| `--saida DIR` | Diretório das imagens geradas |
| `--verboso` | Mostra o tempo de cada etapa |

**Códigos de saída:** `0` sucesso · `1` nenhuma folha detectada · `2` erro de entrada ·
`3` erro interno.

As imagens intermediárias vão para `resultados/execucoes/<id>/` (ignorado pelo Git).

## 7. Iniciar a API local

```bash
python -m src.api
```

O serviço sobe em **`http://127.0.0.1:5000`** — apenas na própria máquina, nunca exposto
à rede. Teste com:

```bash
curl http://127.0.0.1:5000/health
```

| Método | Rota | Função |
|---|---|---|
| GET | `/health` | Disponibilidade |
| POST | `/api/processar-folha` | Recebe a imagem (campo `imagem`) e devolve a análise |
| GET | `/api/resultado/<id>/<arquivo>` | Serve uma imagem intermediária |

Limite de upload: **12 MB**. Formatos: **JPG, PNG, BMP**.

Porta diferente: defina `NATURE_CODE_PDI_PORTA` antes de iniciar — e ajuste
`script/pdi/config-pdi.js`, que é o único lugar do site onde a URL aparece.

## 8. Iniciar o Nature Code

Em **outro terminal**, a partir da **raiz do repositório** (não de `processamento-imagens`):

```bash
python -m http.server 8000
```

> **Não abra o site por duplo clique (`file://`).** O navegador trata essa origem como
> `null`, e a API só aceita as origens locais configuradas.

## 9. Testar no navegador

1. Abra **http://localhost:8000/index.html**
2. Entre no módulo **Plantas**
3. Clique em **Análise Morfológica de Folhas**
4. Confira se o painel diz *"Serviço de processamento disponível"*
5. Escolha uma imagem de folha e clique em **Analisar folha**

Para melhores resultados: uma folha por imagem, fundo claro, folha inteira, boa luz e
pouca sombra. O processamento foi **calibrado principalmente para folhas verdes em fundo
claro** (dataset Flavia).

Se a API estiver desligada, a página mostra uma mensagem explicando como iniciá-la — o
resto do site continua funcionando normalmente.

---

## Dataset

Desenvolvido e validado com o **Flavia Leaf Dataset** — http://flavia.sourceforge.net/.
O dataset **não** está no repositório; veja [`dataset/README.md`](dataset/README.md) para
baixá-lo. Ele só é necessário para reproduzir as medições documentadas, não para usar a
ferramenta nem rodar os testes.

## Documentação

A documentação completa, fase a fase, está em
[`docs/processamento-imagens/`](../docs/processamento-imagens/).

## Limitações principais

- Mede em **pixels**: sem objeto de referência, não há conversão para centímetros.
- Calibrado em **folhas verdes sobre fundo branco**; fundo verde, sombra dura ou folha
  seca reduzem a qualidade da segmentação.
- A descrição morfológica é **geométrica**, não botânica.
