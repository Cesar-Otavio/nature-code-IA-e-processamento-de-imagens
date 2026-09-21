"""API HTTP local — casca fina sobre o pipeline.

Uso::

    cd processamento-imagens
    python -m src.api

**Nenhuma lógica de processamento mora aqui.** Este módulo recebe a requisição, valida
a entrada, chama ``pipeline.processar_folha()`` e serializa. Há teste estrutural que
falha se ele importar ``segmentation``, ``morphology``, ``contours``, ``features`` ou
``classification`` — só o ``pipeline`` é permitido.

Serviço **local**: escuta em ``127.0.0.1``, nunca em ``0.0.0.0``. O site do Nature Code
é estático e fala com esta API pelo navegador — a mesma forma que o módulo de IA usa
para falar com o daemon do Ollama.

Endpoints:

==========  =================================  =====================================
GET         ``/health``                        Disponibilidade
POST        ``/api/processar-folha``           Recebe imagem, devolve análise
GET         ``/api/resultado/<id>/<arquivo>``  Serve uma imagem intermediária
==========  =================================  =====================================
"""

from __future__ import annotations

import mimetypes
import os
import tempfile
import uuid
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_file

from . import __version__
from .pipeline import PASTA_EXECUCOES, VERSAO_PIPELINE, limpar_execucoes_antigas, processar_folha
from .utils import EXTENSOES_SUPORTADAS, nome_seguro

#: Endereço de escuta. **Sempre local** — expor a API à rede não é o caso de uso.
HOST_PADRAO = "127.0.0.1"
PORTA_PADRAO = 5000

#: Limite de upload, em bytes.
#:
#: **12 MB**, escolhido com justificativa: o Flavia tem 1600×1200 em JPEG (~1 MB), e
#: uma foto de celular de 12 megapixels em JPEG de boa qualidade fica entre 3 e 8 MB.
#: 12 MB acomoda isso com folga sem permitir upload abusivo num serviço local.
TAMANHO_MAXIMO_BYTES = 12 * 1024 * 1024

#: Origens aceitas pelo CORS.
#:
#: **Lista fechada, não ``*``.** O site é servido por ``python -m http.server`` na
#: porta 8000, e Live Server costuma usar 5500. Um curinga permitiria que qualquer
#: página aberta no navegador chamasse este serviço.
ORIGENS_PERMITIDAS = frozenset({
    "http://localhost:8000", "http://127.0.0.1:8000",
    "http://localhost:5500", "http://127.0.0.1:5500",
    "http://localhost:3000", "http://127.0.0.1:3000",
})

#: Idade máxima das execuções antes da limpeza automática.
IDADE_MAXIMA_HORAS = 24.0


def criar_app() -> Flask:
    """Constrói a aplicação Flask.

    Fábrica em vez de instância global para que os testes possam criar uma aplicação
    isolada com o cliente de teste, sem subir servidor de verdade.
    """
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = TAMANHO_MAXIMO_BYTES

    @app.after_request
    def aplicar_cors(resposta: Response) -> Response:
        """Libera apenas as origens locais conhecidas."""
        origem = request.headers.get("Origin")
        if origem in ORIGENS_PERMITIDAS:
            resposta.headers["Access-Control-Allow-Origin"] = origem
            resposta.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            resposta.headers["Access-Control-Allow-Headers"] = "Content-Type"
            resposta.headers["Vary"] = "Origin"
        return resposta

    @app.errorhandler(413)
    def payload_grande(_erro: object) -> tuple[Response, int]:
        return jsonify({
            "status": "erro",
            "erro": {
                "codigo": "E006",
                "mensagem": f"Arquivo muito grande. Máximo: "
                            f"{TAMANHO_MAXIMO_BYTES // (1024 * 1024)} MB.",
            },
        }), 413

    @app.errorhandler(404)
    def nao_encontrado(_erro: object) -> tuple[Response, int]:
        return jsonify({
            "status": "erro",
            "erro": {"codigo": "E404", "mensagem": "Recurso não encontrado."},
        }), 404

    @app.errorhandler(Exception)
    def erro_interno(_erro: Exception) -> tuple[Response, int]:
        """Nunca devolve rastreamento ao cliente."""
        return jsonify({
            "status": "erro",
            "erro": {"codigo": "E500", "mensagem": "Erro interno no processamento."},
        }), 500

    @app.get("/health")
    def health() -> Response:
        """Disponibilidade do serviço. Não executa processamento."""
        return jsonify({
            "status": "ok",
            "servico": "nature-code-pdi",
            "versao": __version__,
            "versao_pipeline": VERSAO_PIPELINE,
            "usa_ia": False,
        })

    @app.route("/api/processar-folha", methods=["POST", "OPTIONS"])
    def processar() -> tuple[Response, int] | Response:
        """Recebe uma imagem e devolve a análise morfológica."""
        if request.method == "OPTIONS":
            return Response(status=204)

        if "imagem" not in request.files:
            return jsonify({
                "status": "erro",
                "erro": {"codigo": "E002", "mensagem": "Campo 'imagem' ausente na requisição."},
            }), 400

        enviado = request.files["imagem"]
        if not enviado.filename:
            return jsonify({
                "status": "erro",
                "erro": {"codigo": "E002", "mensagem": "Nenhum arquivo foi selecionado."},
            }), 400

        # O nome enviado NUNCA determina o caminho de gravação.
        extensao = Path(nome_seguro(enviado.filename)).suffix.lower()
        if extensao not in EXTENSOES_SUPORTADAS:
            aceitas = ", ".join(sorted(e.lstrip(".").upper() for e in EXTENSOES_SUPORTADAS))
            return jsonify({
                "status": "erro",
                "erro": {"codigo": "E002", "mensagem": f"Formato não suportado. Aceitos: {aceitas}."},
            }), 400

        limpar_execucoes_antigas(IDADE_MAXIMA_HORAS)

        identificador = uuid.uuid4().hex
        temporario = Path(tempfile.gettempdir()) / f"nature-code-pdi-{identificador}{extensao}"

        try:
            enviado.save(str(temporario))
            resultado = processar_folha(
                temporario,
                salvar_imagens=True,
                destino=PASTA_EXECUCOES / identificador,
                id_execucao=identificador,
            )
        finally:
            # O upload original nunca é mantido.
            try:
                temporario.unlink(missing_ok=True)
            except OSError:
                pass

        # O nome do arquivo temporário é detalhe interno e não pode vazar — nem no
        # sucesso, nem no erro. O cliente vê o nome (saneado) do que enviou.
        if resultado["entrada"]:
            resultado["entrada"]["arquivo"] = nome_seguro(enviado.filename)  # type: ignore[index]

        if resultado["status"] == "erro":
            codigo = resultado["erro"]["codigo"]  # type: ignore[index]
            http = 422 if codigo in ("E007", "E011") else 400
            return jsonify(resultado), http

        resultado["imagens_intermediarias"] = {
            etapa: f"/api/resultado/{identificador}/{nome}"
            for etapa, nome in resultado["imagens_intermediarias"].items()  # type: ignore[union-attr]
        }

        return jsonify(resultado)

    @app.get("/api/resultado/<identificador>/<arquivo>")
    def servir_resultado(identificador: str, arquivo: str) -> Response | tuple[Response, int]:
        """Serve uma imagem intermediária de uma execução.

        **Protegido contra travessia de caminho.** Tanto o identificador quanto o nome
        do arquivo são saneados, e o caminho final é resolvido e conferido contra a
        pasta de execuções — uma entrada como ``../../etc/passwd`` não escapa.
        """
        id_seguro = nome_seguro(identificador)
        arquivo_seguro = nome_seguro(arquivo)

        if not id_seguro or not arquivo_seguro or not arquivo_seguro.endswith(".png"):
            return jsonify({
                "status": "erro",
                "erro": {"codigo": "E404", "mensagem": "Recurso não encontrado."},
            }), 404

        raiz = PASTA_EXECUCOES.resolve()
        alvo = (raiz / id_seguro / arquivo_seguro).resolve()

        # A conferência que realmente impede a travessia.
        if not str(alvo).startswith(str(raiz) + os.sep) or not alvo.is_file():
            return jsonify({
                "status": "erro",
                "erro": {"codigo": "E404", "mensagem": "Recurso não encontrado."},
            }), 404

        tipo = mimetypes.guess_type(alvo.name)[0] or "application/octet-stream"
        return send_file(alvo, mimetype=tipo)

    return app


def main() -> int:
    """Sobe o servidor local."""
    porta = int(os.environ.get("NATURE_CODE_PDI_PORTA", PORTA_PADRAO))
    app = criar_app()

    print(f"Nature Code — API de Processamento de Imagens")
    print(f"  http://{HOST_PADRAO}:{porta}/health")
    print(f"  sem IA, sem aprendizado de máquina")
    print(f"  Ctrl+C para encerrar\n")

    # debug=False: o modo de depuração do Flask expõe um console de execução de código.
    app.run(host=HOST_PADRAO, port=porta, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
