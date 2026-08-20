/**
 * dom-de-teste.js — DOM mínimo para rodar o JavaScript do site fora do navegador.
 *
 * Módulo compartilhado por scripts/testar-integracao.js e scripts/testar-diagnostico.js.
 * Não faz parte do site: existe só para que o código real — quiz-engine.js,
 * interface-quiz.js, diagnostico.js — possa ser executado num contexto `vm` do Node,
 * sem instalar jsdom nem nenhuma outra dependência.
 *
 * É um esqueleto, não um navegador: implementa o que o site usa de verdade
 * (getElementById, querySelector com um nível de descendência, classList, innerHTML com
 * análise de tags e nós de texto, addEventListener) e nada além disso. Justamente por
 * ser incompleto, os testes que o usam conferem seus ids contra o HTML real.
 */

"use strict";

function criarDom() {
  function Elemento(tag) {
    this.tagName = String(tag || "div").toUpperCase();
    this.id = "";
    this.className = "";
    this.children = [];
    this.parentNode = null;
    this.style = {};
    this.dataset = {};
    this.atributos = {};
    this.ouvintes = {};
    this._texto = "";
    this._html = "";
    this.disabled = false;
    this.hidden = false;
    this.title = "";
    this.type = "";
    const self = this;
    this.classList = {
      add(...nomes) {
        const atuais = self.className.split(/\s+/).filter(Boolean);
        for (const n of nomes) if (atuais.indexOf(n) === -1) atuais.push(n);
        self.className = atuais.join(" ");
      },
      remove(...nomes) {
        self.className = self.className
          .split(/\s+/)
          .filter((c) => c && nomes.indexOf(c) === -1)
          .join(" ");
      },
      contains(nome) {
        return self.className.split(/\s+/).indexOf(nome) !== -1;
      },
    };
  }

  Object.defineProperty(Elemento.prototype, "textContent", {
    get() {
      if (this._texto) return this._texto;
      return this.children.map((c) => c.textContent).join("");
    },
    set(valor) {
      this._texto = String(valor);
      this._html = "";
      this.children = [];
    },
  });

  // innerHTML guarda o texto E monta os filhos, porque o código do site faz
  // elemento.innerHTML = "..." e logo depois elemento.querySelector(".classe").
  Object.defineProperty(Elemento.prototype, "innerHTML", {
    get() {
      return this._html;
    },
    set(valor) {
      this._html = String(valor);
      this._texto = "";
      this.children = [];
      for (const filho of analisarHtml(String(valor))) {
        filho.parentNode = this;
        this.children.push(filho);
      }
    },
  });

  Elemento.prototype.appendChild = function (filho) {
    filho.parentNode = this;
    this.children.push(filho);
    // Um <select> assume o valor da primeira <option>, como no navegador. Sem isto,
    // select.value sairia undefined e a página de diagnóstico quebraria no teste por
    // um motivo que não existe de verdade.
    if (this.tagName === "SELECT" && filho.tagName === "OPTION" && this.value === undefined) {
      this.value = filho.value;
    }
    return filho;
  };
  Elemento.prototype.insertBefore = function (novo, referencia) {
    novo.parentNode = this;
    const i = this.children.indexOf(referencia);
    if (i === -1) this.children.push(novo);
    else this.children.splice(i, 0, novo);
    return novo;
  };
  Elemento.prototype.remove = function () {
    if (!this.parentNode) return;
    const i = this.parentNode.children.indexOf(this);
    if (i !== -1) this.parentNode.children.splice(i, 1);
    this.parentNode = null;
  };
  Elemento.prototype.setAttribute = function (nome, valor) {
    this.atributos[nome] = String(valor);
    if (nome === "id") this.id = String(valor);
    if (nome === "class") this.className = String(valor);
  };
  Elemento.prototype.getAttribute = function (nome) {
    return Object.prototype.hasOwnProperty.call(this.atributos, nome) ? this.atributos[nome] : null;
  };
  Elemento.prototype.addEventListener = function (evento, funcao) {
    (this.ouvintes[evento] = this.ouvintes[evento] || []).push(funcao);
  };
  Elemento.prototype.clicar = function () {
    for (const f of this.ouvintes.click || []) f({ target: this });
  };
  Elemento.prototype.todos = function () {
    const lista = [];
    for (const filho of this.children) {
      lista.push(filho);
      lista.push(...filho.todos());
    }
    return lista;
  };
  Elemento.prototype.combina = function (seletor) {
    if (seletor.charAt(0) === "#") return this.id === seletor.slice(1);
    if (seletor.charAt(0) === ".") return this.classList.contains(seletor.slice(1));
    return this.tagName === seletor.toUpperCase();
  };
  Elemento.prototype.querySelectorAll = function (seletor) {
    // Suporta "a b" (descendente) e seletor simples — é tudo o que o site usa.
    const partes = seletor.trim().split(/\s+/);
    let candidatos = this.todos();
    if (partes.length === 1) return candidatos.filter((e) => e.combina(partes[0]));
    const ancestrais = candidatos.filter((e) => e.combina(partes[0]));
    const resultado = [];
    for (const a of ancestrais) {
      for (const d of a.todos()) if (d.combina(partes[1]) && resultado.indexOf(d) === -1) resultado.push(d);
    }
    return resultado;
  };
  Elemento.prototype.querySelector = function (seletor) {
    return this.querySelectorAll(seletor)[0] || null;
  };
  Elemento.prototype.scrollTo = function () {};

  /** Analisador de HTML minúsculo: só o suficiente para o innerHTML do site. */
  function analisarHtml(html) {
    const raizes = [];
    const pilha = [];
    let ultimoFim = 0;

    // Nós de texto contam: o modal do site monta a pontuação como
    // "Você acertou <span>3 de 3</span> questões", e sem capturar o texto solto
    // o textContent sairia vazio.
    function texto(bruto) {
      const conteudo = bruto.replace(/\s+/g, " ");
      if (!conteudo.trim()) return;
      const no = new Elemento("#text");
      no._texto = conteudo;
      if (pilha.length) pilha[pilha.length - 1].appendChild(no);
      else raizes.push(no);
    }
    // Atributos sem valor (`hidden`, `disabled`) precisam casar: o interface-quiz.js
    // cria o botão com `hidden`, e um padrão que exija ="..." descarta a tag inteira.
    const padrao = /<\/?([a-zA-Z][\w-]*)((?:\s+[\w-]+(?:\s*=\s*"[^"]*")?)*)\s*(\/?)>/g;
    let achado;
    while ((achado = padrao.exec(html)) !== null) {
      const [tudo, tag, atributos, autoFechada] = achado;
      texto(html.slice(ultimoFim, achado.index));
      ultimoFim = achado.index + tudo.length;
      if (tudo.charAt(1) === "/") {
        pilha.pop();
        continue;
      }
      const elemento = new Elemento(tag);
      for (const atributo of atributos.matchAll(/([\w-]+)(?:\s*=\s*"([^"]*)")?/g)) {
        if (!atributo[1]) continue;
        if (atributo[2] === undefined) elemento[atributo[1]] = true; // hidden, disabled
        else elemento.setAttribute(atributo[1], atributo[2]);
      }
      if (pilha.length) pilha[pilha.length - 1].appendChild(elemento);
      else raizes.push(elemento);
      if (!autoFechada && ["br", "img", "input", "hr", "meta", "link"].indexOf(tag.toLowerCase()) === -1) {
        pilha.push(elemento);
      }
    }
    texto(html.slice(ultimoFim));
    return raizes;
  }

  const raiz = new Elemento("html");
  const head = raiz.appendChild(new Elemento("head"));
  const body = raiz.appendChild(new Elemento("body"));

  const document = {
    head,
    body,
    createElement: (tag) => new Elemento(tag),
    createTextNode: (conteudo) => {
      const no = new Elemento("#text");
      no.textContent = String(conteudo);
      return no;
    },
    getElementById: (id) => raiz.querySelectorAll("#" + id)[0] || null,
    querySelector: (s) => raiz.querySelector(s),
    querySelectorAll: (s) => raiz.querySelectorAll(s),
    addEventListener: () => {},
  };

  return { document, raiz, body, Elemento };
}

module.exports = { criarDom };
