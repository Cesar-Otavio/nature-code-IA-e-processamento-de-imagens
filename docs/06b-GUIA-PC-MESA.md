# Guia de execução da Fase 6 no PC de mesa

> Passo a passo do zero, para Windows. Todos os comandos são para o **PowerShell**.
>
> **Máquina de destino:** Ryzen 7 5800X · 32 GB DDR4 · GTX 1650 · ~500 GB livres · Windows.
>
> Cada passo diz **o que esperar**. Se o resultado não bater, pare e me mande o que apareceu
> — não force o passo seguinte.
>
> Nenhum passo altera o repositório de desenvolvimento. Tudo acontece numa cópia.

---

## Antes de começar

Leve para o PC de mesa **um arquivo só**:

```
nature-code-fase6-preparada-20260825.bundle      (~119 MB)
```

> **Atenção ao nome do arquivo.** Existe um bundle anterior,
> `nature-code-fase5-20260823.bundle`, gerado antes da preparação da Fase 6. Ele **não
> contém os scripts do benchmark**. Use o arquivo com `fase6-preparada` no nome.
>
> O SHA-256 do bundle não fica escrito aqui de propósito: um arquivo não pode conter o
> próprio hash. Ele é informado junto com o bundle — a conferência do passo 7 usa esse
> valor.

Ele está em `C:\Users\zrazo\Downloads\`. Copie para um pendrive.

---

# PARTE 1 — Ambiente

## Passo 1. Verificar o Windows

```powershell
[System.Environment]::OSVersion.Version
(Get-CimInstance Win32_OperatingSystem).Caption
```

**Esperado:** Windows 10 ou 11, 64 bits.

## Passo 2. Verificar o Node.js

```powershell
node --version
```

**Esperado:** `v18` ou superior (aqui foi usado o `v24.13.0`).

Se der "não é reconhecido", instale de <https://nodejs.org> (versão LTS), **feche e reabra
o PowerShell**, e repita.

## Passo 3. Verificar o Git

```powershell
git --version
```

**Esperado:** `git version 2.x`.

Se faltar, instale de <https://git-scm.com/download/win>, reabra o PowerShell e repita.

## Passo 4. Verificar / instalar o Ollama

```powershell
ollama --version
```

**Esperado:** `ollama version is 0.3x.x`.

Se faltar, instale de <https://ollama.com/download/windows>. Depois de instalar, o ícone
aparece na bandeja do sistema, perto do relógio.

**Ainda não baixe modelo nenhum.** Isso é o passo 13.

## Passo 5. Verificar a NVIDIA

```powershell
Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, AdapterRAM
```

**Esperado:** uma linha com `NVIDIA GeForce GTX 1650`.

## Passo 6. Rodar o `nvidia-smi`

```powershell
nvidia-smi
```

**Esperado:** tabela com o nome da GPU, versão do driver, versão do CUDA e uso de memória.

**Se der "não é reconhecido":** o driver NVIDIA não está instalado ou não está no PATH.
**Não instale nem atualize driver por causa deste benchmark.** Apenas anote que o
`nvidia-smi` não existe — o Ollama vai rodar em CPU, e isso é um resultado válido a
registrar.

Guarde a saída deste passo; ela entra no relatório.

---

# PARTE 2 — Restaurar o projeto

## Passo 7. Clonar a partir do bundle

Escolha uma pasta de trabalho, por exemplo `C:\Projetos`:

```powershell
New-Item -ItemType Directory -Force C:\Projetos
Set-Location C:\Projetos
Copy-Item E:\nature-code-fase6-preparada-20260825.bundle .    # ajuste a letra do pendrive
```

Confira que o arquivo chegou inteiro:

```powershell
Get-FileHash .\nature-code-fase6-preparada-20260825.bundle -Algorithm SHA256
```

**Esperado:** o mesmo valor que foi informado junto com o bundle. O PowerShell mostra em
maiúsculas; é o mesmo hash.

Se não bater, a cópia corrompeu. Copie de novo antes de seguir.

```powershell
git bundle verify .\nature-code-fase6-preparada-20260825.bundle
git clone -b feat/quiz-ia .\nature-code-fase6-preparada-20260825.bundle Site-Nature-Code-main
Set-Location Site-Nature-Code-main
```

**Esperado:** `is okay`, `The bundle records a complete history`, e o clone concluindo.

## Passo 8. Corrigir os fins de linha (OBRIGATÓRIO)

```powershell
git config core.autocrlf false
git rm -q --cached -r .
git reset -q --hard
```

**Por que isto é obrigatório.** O Git for Windows define `core.autocrlf=true` no config do
sistema. Configuração local **não viaja no bundle**, então o clone nasce convertendo tudo
para CRLF: `dados\base-conhecimento.js` passaria de 57.520 para 58.454 bytes. O efeito
prático seria rodar o extrator e ver um diff falso de 934 linhas.

**Confira:**

```powershell
(Get-Item dados\base-conhecimento.js).Length
```

**Esperado:** `57520`. Se der `58454`, o passo não pegou — repita.

## Passo 9. Confirmar branch e commit

```powershell
git branch --show-current
git rev-parse --short HEAD
```

**Esperado:** `feat/quiz-ia`.

O hash do commit não é conferido aqui — ele muda a cada correção, e um número fixo neste
guia envelheceria. A verificação que importa é de **conteúdo**: os scripts da Fase 6
precisam existir no clone.

```powershell
Test-Path scripts\benchmark-fase6.js, scripts\comparar-benchmark.js, scripts\testar-benchmark.js
git log --oneline -1
```

**Esperado:** três `True` e um commit que menciona a Fase 6.

Se algum der `False`, você clonou o bundle antigo. Refaça o passo 7 com o arquivo que tem
`fase6-preparada` no nome.

## Passo 10. Confirmar que o working tree está limpo

```powershell
git status --short
```

**Esperado:** **nenhuma saída**. Se aparecer qualquer arquivo modificado, pare e me avise.

## Passo 11. Confirmar a tag de restauração

```powershell
git tag -l
git rev-parse --short fase-5-completa^{commit}
```

**Esperado:** `fase-5-completa` na lista, apontando para `8a85e29`.

Essa tag é o ponto de retorno. Se algo der errado em qualquer momento:

```powershell
git reset --hard fase-5-completa
git clean -fd
```

## Passo 12. Verificar o ambiente do projeto

```powershell
node scripts\testar-camada-ia.js
node scripts\testar-integracao.js
node scripts\testar-diagnostico.js
node scripts\testar-benchmark.js
node scripts\benchmark-fase6.js --verificar-prompts
```

**Esperado:**

```
67 passaram, 0 falharam
46 passaram, 0 falharam
82 passaram, 0 falharam
61 passaram, 0 falharam
OK: braços A e B recebem prompts byte a byte idênticos. Comparação válida.
```

**Se qualquer suíte falhar, pare aqui e me mande a saída.** Não adianta medir modelo com
a base quebrada.

---

# PARTE 3 — O modelo local

## Passo 13. Baixar o modelo (só agora)

```powershell
ollama pull qwen3.5:4b
```

**Esperado:** download de ~3,4 GB terminando em `success`.

## Passo 14. Verificar o modelo

```powershell
ollama list
```

**Esperado:** `qwen3.5:4b` na lista, com tamanho em torno de 3,4 GB.

## Passo 15. Garantir o Ollama no ar

O Ollama sobe sozinho com o Windows. Se o ícone não estiver na bandeja, abra pelo menu
Iniciar.

```powershell
Get-Process ollama -ErrorAction SilentlyContinue | Select-Object ProcessName, Id
```

**Esperado:** pelo menos um processo `ollama`.

## Passo 16. Testar o `/api/tags`

```powershell
Invoke-RestMethod http://localhost:11434/api/tags | ConvertTo-Json -Depth 3
```

**Esperado:** JSON listando os modelos, com `qwen3.5:4b` entre eles.

## Passo 17. Testar uma geração simples

```powershell
$corpo = @{ model = "qwen3.5:4b"; stream = $false
            messages = @(@{ role = "user"; content = "Responda apenas: ok" }) } | ConvertTo-Json -Depth 4
Measure-Command { $r = Invoke-RestMethod http://localhost:11434/api/chat -Method Post -Body $corpo -ContentType "application/json" }
$r.message.content
```

**Esperado:** uma resposta curta e o tempo decorrido. **Anote esse tempo** — é a primeira
medida de latência da máquina.

Se demorar mais de 2 minutos para responder "ok", o modelo está pesado demais; siga assim
mesmo até o passo 20, que é onde se decide.

---

# PARTE 4 — Sondagem e decisão

## Passo 18. Sondagem de 3 gerações

**Antes**, abra o Gerenciador de Tarefas (`Ctrl+Shift+Esc`) na aba **Desempenho**, para
observar CPU, memória e GPU durante a execução.

```powershell
node scripts\benchmark-fase6.js --sondagem --modelo-local qwen3.5:4b
```

**Esperado:** três pontos aparecendo um a um e uma linha final com a mediana, algo como:

```
filo-cordados          15/ 15 aprovadas (100%) | 0 retent. | JSON 1a: 3/3 | mediana 48.2s | IA 3/3
gravado: docs/dados-benchmark/fase6-sondagem-qwen3-5-4b.json
config-ia.js intacto (sha256 inalterado)
```

## Passo 19. Medir CPU, RAM, GPU e VRAM

**Durante** o passo 18, no Gerenciador de Tarefas → Desempenho, anote:

| O que | Onde olhar | Anote |
|---|---|---|
| CPU | aba CPU | % de uso durante a geração |
| RAM | aba Memória | quanto subiu em GB |
| GPU | aba GPU | se sobe acima de ~5% durante a geração |
| VRAM | aba GPU, "Memória de GPU dedicada" | quanto foi usado |

E, numa **segunda janela do PowerShell**, durante a geração:

```powershell
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv -l 2
```

**Esperado:** se o Ollama estiver usando a GPU, `utilization.gpu` sobe e `memory.used`
aumenta em ~3 a 4 GB. Se ficar em zero, está rodando em CPU.

Confirme também pelo próprio Ollama:

```powershell
ollama ps
```

A coluna `PROCESSOR` diz `100% GPU`, `100% CPU` ou uma divisão entre os dois. **É a
resposta mais direta**, e é o que registramos.

## Passo 20. Decidir se o 4b é viável

| Mediana da sondagem | Decisão | N por tópico |
|---|---|---:|
| até 60 s | segue com o 4b | 10 |
| 60 a 150 s | segue com o 4b | 6 |
| acima de 150 s | segue com o 4b, bateria curta | 3 |
| acima de 300 s, ou o modelo não coube | vá ao passo 21 | — |

Com 32 GB de RAM, memória não deve ser problema. O critério aqui é **tempo**.

## Passo 21. Somente se necessário: testar o 2b

```powershell
ollama pull qwen3.5:2b
node scripts\benchmark-fase6.js --sondagem --modelo-local qwen3.5:2b --rotulo fase6-sondagem-qwen3-5-2b
```

Se usar o 2b, **troque `qwen3.5:4b` por `qwen3.5:2b` em todos os comandos seguintes**.

---

# PARTE 5 — O benchmark

Nos comandos abaixo, substitua `<N>` pelo número decidido no passo 20.

## Passo 22. Executar os três braços

Rode **na ordem**, um de cada vez, esperando cada um terminar:

```powershell
node scripts\benchmark-fase6.js --braco A --n <N>
node scripts\benchmark-fase6.js --braco B --n <N> --modelo-local qwen3.5:4b
node scripts\benchmark-fase6.js --braco C --n <N> --modelo-local qwen3.5:4b
```

**Braço A** precisa de internet e usa a cota do Ollama Cloud. Ele leva ~10 minutos.
Se aparecer `usage limit`, a cota acabou — espere algumas horas e rode só o braço A depois.

**Braços B e C** rodam offline, na CPU/GPU da máquina, e são os demorados.

**Esperado em cada braço:** a conferência de hashes passando (nos braços A e B), uma linha
por tópico e, ao final:

```
gravado: docs/dados-benchmark/fase6-braco-X-....json
config-ia.js intacto (sha256 inalterado)
```

## Passo 23. O que observar durante o teste

| Sinal | O que significa |
|---|---|
| `.` | geração servida pela IA — o esperado |
| `F` | caiu no quiz fixo. Alguns são normais; muitos seguidos indicam problema |
| `c` | veio do cache — não deveria aparecer, o cache é limpo a cada tópico |
| `!` | erro na geração |
| `JSON 1a: 3/3` | quantas gerações produziram JSON válido na primeira tentativa |
| `retent.` | retentativas. Muitas indicam que o modelo erra o formato ou o validador recusa |

No Gerenciador de Tarefas, acompanhe se a memória continua estável. Se começar a paginar
em disco, a latência medida deixa de ser confiável — anote isso.

## Passo 24. Como interromper com segurança

**`Ctrl+C`** na janela do PowerShell. É seguro a qualquer momento.

O braço interrompido **não grava arquivo** — a gravação só acontece ao final. Você perde a
execução daquele braço, e nada mais. Os braços já concluídos e todos os dados da Fase 5
continuam intactos.

Para retomar, rode o mesmo comando de novo.

Se precisar parar o modelo:

```powershell
ollama stop qwen3.5:4b
```

## Passo 25. Localizar os resultados

```powershell
Get-ChildItem docs\dados-benchmark\ | Select-Object Name, Length, LastWriteTime
```

**Esperado:** um arquivo por braço executado.

**Confirme que a Fase 5 não foi tocada:**

```powershell
git status --short
```

**Esperado:** apenas arquivos novos em `docs/dados-benchmark/` como não rastreados.
**Nada** em `docs/dados-piloto/`, **nada** em `script/ia/`.

## Passo 26. Rodar os testes de novo

```powershell
node scripts\testar-camada-ia.js
node scripts\testar-integracao.js
node scripts\testar-diagnostico.js
node scripts\testar-benchmark.js
```

**Esperado:** os mesmos números do passo 12 — 67, 46, 82 e 61, sem falhas. Isso confirma
que o benchmark não alterou nada do que já funcionava.

## Passo 27. Comparar os resultados

```powershell
node scripts\comparar-benchmark.js
```

**Esperado:** a conferência de hashes, a tabela comparando os braços e, se B e C rodaram,
o bloco do efeito do JSON Schema.

Para ver as questões marcadas:

```powershell
node scripts\comparar-benchmark.js --listar termo-inedito --limite 20
node scripts\comparar-benchmark.js --listar negativa --limite 20
node scripts\comparar-benchmark.js --amostra 12
```

## Passo 28. Restaurar, se precisar

Para voltar exatamente ao estado da Fase 5, **descartando os resultados do benchmark**:

```powershell
git reset --hard fase-5-completa
git clean -fd
```

Para **manter** os resultados e descartar só alterações acidentais de código:

```powershell
git stash list
git checkout -- script\ia\
git status --short
```

Para apagar um modelo baixado:

```powershell
ollama rm qwen3.5:4b
```

Lembrando: o repositório de desenvolvimento, na outra máquina, não é afetado por nada
disso. O bundle continua sendo o ponto de restauração completo.

---

# PARTE 6 — O que me enviar depois

Copie e me mande:

1. **A pasta inteira** `docs\dados-benchmark\` — são os dados brutos, com o texto de todas
   as questões geradas.
2. **A saída do passo 27** (`comparar-benchmark.js`), copiada do terminal.
3. **A saída do passo 6** (`nvidia-smi`).
4. **A saída de `ollama ps`** durante a geração (passo 19) — é ela que diz se a GPU foi usada.
5. **Suas anotações do passo 19**: CPU, RAM, GPU e VRAM observados.
6. **O tempo do passo 17**.
7. **Qualquer coisa que não bateu com o esperado**, mesmo que pareça pequena.

Se for mais fácil, um zip da pasta `docs\dados-benchmark\` resolve os itens 1 e 2.

---

# PARTE 7 — O que farei com os resultados

1. Conferir os **hashes** dos prompts. Se A e B divergirem, a comparação A × B é declarada
   inválida e eu digo isso, em vez de tirar conclusão de dado ruim.
2. Montar a tabela comparativa dos três braços com os números reais.
3. **Ler as questões**, com o mesmo protocolo da Fase 5: todas as marcadas em `negativa`,
   `titulo-de-secao` e `termo-inedito`, mais amostra cega. É a leitura que encontra o que o
   validador aprova e está errado.
4. Isolar o **efeito do JSON Schema** comparando C com B — mesmo modelo, mesma máquina.
5. Registrar se o Ollama usou a GTX 1650, e o que isso significou na latência.
6. Escrever `docs/06c-RESULTADO-BENCHMARK.md` com o contraste nuvem × local: latência,
   qualidade, confiabilidade de formato, custo, privacidade e independência de rede.
7. Recomendar — com número, não com preferência — se vale trocar o provedor para local, e
   parar para sua aprovação antes de mexer no `config-ia.js`.

---

## Resumo de segurança

| Garantia | Como |
|---|---|
| O repositório de desenvolvimento não é tocado | O PC de mesa trabalha num clone do bundle |
| Os dados da Fase 5 não são sobrescritos | O benchmark grava só em `docs/dados-benchmark/`, com teste automatizado |
| `config-ia.js` não muda | SHA-256 conferido antes e depois de cada braço |
| Dá para voltar atrás | `git reset --hard fase-5-completa` |
| Interromper é seguro | `Ctrl+C`; nada é gravado pela metade |
