# Como executar o site com a IA ligada

> Entregável previsto na seção 6.3 do roteiro. **Não foi produzido na Fase 2** — a lacuna
> foi identificada depois e este documento a fecha, já com os dados medidos.
>
> A finalidade é uma só: ninguém travar na hora da apresentação.

---

## 1. Roteiro rápido

```
1. Abra o Ollama            (ícone na bandeja do sistema, perto do relógio)
2. Sirva o site por HTTP    (Live Server do VS Code, ou o comando abaixo)
3. Abra a página do tópico  no endereço http://... — nunca por duplo clique
```

Com `python -m http.server`, a partir da **raiz do projeto**:

```bash
cd Site-Nature-Code-main
python -m http.server 8000
```

| Página | Endereço |
|---|---|
| Início | `http://localhost:8000/index.html` |
| Cordados (tópico com IA) | `http://localhost:8000/pages/modulos/topicos/topicos-animais/filo-cordados.html` |
| Diagnóstico | `http://localhost:8000/ferramentas/diagnostico.html` |

Com o **Live Server** do VS Code, o endereço costuma ser `http://127.0.0.1:5500/...` — funciona
igual, só muda a porta.

---

## 2. O site PRECISA ser servido por HTTP

Abrir o HTML por duplo clique (`file://`) faz o quiz cair no banco de questões fixas. Não é
defeito: é o Ollama recusando a origem.

**Medido em 19/08/2026**, mandando uma requisição de verificação (*preflight*) ao
`http://localhost:11434/api/chat` com cada origem:

| Origem da página | Resposta do Ollama |
|---|---|
| `http://127.0.0.1:5500` (Live Server) | **204**, com `Access-Control-Allow-Origin` |
| `http://localhost:5500` | **204** |
| `http://localhost:8000` · `http://127.0.0.1:8000` | **204** |
| `http://localhost:3000` | **204** |
| `null` — página aberta por `file://` | **403 Forbidden** |

Ou seja: **com qualquer servidor local funciona sem configurar nada.** A variável
`OLLAMA_ORIGINS` não precisou ser tocada nesta máquina.

### Se ainda assim aparecer erro de CORS

Só nesse caso, no Windows:

```cmd
setx OLLAMA_ORIGINS "*"
```

Depois **feche o Ollama pela bandeja do sistema e abra de novo**. Variável de ambiente só é lida
quando o processo inicia — reiniciar o computador também resolve, mas fechar e abrir o Ollama basta.

⚠️ Fechar a *janela* do Ollama não encerra o daemon. É preciso clicar no ícone da bandeja e usar
"Quit"/"Sair". Isso vale também para quando você quiser demonstrar o fallback de propósito.

---

## 3. O que você vê em cada situação

O site nunca fica sem quiz. O que muda é o selo acima da pergunta e o aviso abaixo dele.

| Situação | Selo na tela | Aviso ao aluno |
|---|---|---|
| Tudo funcionando | ✨ Perguntas geradas por IA | nenhum |
| Ollama fora do ar, com perguntas guardadas | ✨ Perguntas geradas por IA (salvas) | "Não foi possível falar com o modelo agora, então estas são perguntas geradas antes e guardadas neste navegador." |
| Ollama fora do ar, sem nada guardado | 📘 Banco de questões do site | "As perguntas novas não estão disponíveis no momento. Você está respondendo o banco de questões do site." |
| Tópico curto ou ainda não habilitado | 📘 Banco de questões do site | nenhum — é o comportamento normal dele |

Nenhuma dessas mensagens usa jargão técnico. Os detalhes técnicos ficam no console e na página de
diagnóstico, não na frente do aluno.

---

## 4. Mensagens de erro e o que fazer

| Sintoma | Causa | Correção |
|---|---|---|
| Console: `Failed to fetch` / `ERR_CONNECTION_REFUSED` em `localhost:11434` | Ollama fechado | Abrir o Ollama pela bandeja |
| Console: mensagem de bloqueio por CORS citando a origem `null` | Página aberta por `file://` | Servir por HTTP (§1) |
| Console: mensagem de bloqueio por CORS com uma origem `http://...` | Origem incomum | `setx OLLAMA_ORIGINS "*"` e reiniciar o Ollama (§2) |
| Diagnóstico mostra "não encontrado" no modelo | Modelo não registrado nesta máquina | `ollama pull gpt-oss:120b-cloud` |
| Diagnóstico mostra erro de assinatura | Modelo exige plano pago do Ollama Cloud | Trocar `modelo` em `script/ia/config-ia.js` por um gratuito |
| Quiz demora e cai no fixo | Timeout de 120 s estourado | Ver a latência na página de diagnóstico; se estiver alto, aumentar `timeoutMs` |

Para ver o prompt enviado, a resposta crua e o motivo de cada recusa no console do navegador,
ligue `modoDebug: true` em `script/ia/config-ia.js`.

---

## 5. Conferência antes de apresentar

1. **Ollama no ar?** Abra `ferramentas/diagnostico.html` e clique em **Testar conexão**.
   Precisa mostrar *online* e *registrado*.
2. **O modelo responde?** Na mesma página, o campo "Latência de uma geração" precisa mostrar um
   tempo, não "falhou".
3. **A geração funciona?** No gerador manual, escolha Reino Animal → Filo dos Cordados, 3 questões,
   e clique em **Gerar**. As três colunas precisam preencher.
4. **O site gera?** Abra Cordados. Deve aparecer o estado de carregamento e depois o selo
   ✨ *Perguntas geradas por IA*.
5. **O fallback funciona?** Feche o Ollama pela bandeja, clique em **Gerar novas perguntas** e
   confira que o quiz continua saindo, com o selo 📘.

O passo 5 vale a pena ensaiar: é a demonstração mais convincente da arquitetura, e é a que dá
errado se o Ollama for fechado só pela janela.

---

## 6. Limites desta arquitetura

- Só funciona em máquina com o Ollama **instalado e autenticado**. Não é publicável em hospedagem
  nesta forma: o navegador de um visitante não teria o daemon local. Para publicar seria preciso um
  backend intermediário guardando a credencial.
- O modelo `gpt-oss:120b-cloud` roda na nuvem, então **depende de internet**. Sem rede, o quiz cai
  para cache e depois para o quiz fixo — a apresentação continua funcionando, mas sem gerar
  perguntas novas. A Fase 6 avalia um modelo local, que remove essa dependência.
- O site também usa Bootstrap e Google Fonts por CDN, o que já era assim antes da IA: sem internet,
  as fontes e parte do CSS não carregam.
