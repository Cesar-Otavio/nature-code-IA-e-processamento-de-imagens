"""Pipeline completo: da imagem ao resultado estruturado.

**Este é o único lugar onde a lógica de processamento existe.** `cli.py` e `api.py`
são cascas finas que chamam daqui e formatam a saída — nenhuma decisão de processamento
mora nelas, e há teste estrutural que falha se elas importarem ``cv2`` ou ``numpy``.

Sequência executada, exatamente como validada nas Fases 3 a 8:

.. code-block:: text

    validação → leitura → redimensionamento → Gaussiano → segmentação HSV
    → limpeza morfológica → contornos → objeto principal → características
    → classificação determinística → resultado

**Nenhum parâmetro foi recalibrado nesta fase.** Segmentação, filtro, limpeza e
limiares de classificação são os das fases anteriores, e os testes daquelas fases
continuam fixando seus valores.

Este módulo **não importa Flask** — verificado por teste. A camada de processamento não
sabe que existe uma API.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import asdict
from pathlib import Path

import numpy as np

from . import __version__
from .classification import classificar_morfologia
from .contours import analisar_contorno
from .features import extrair_caracteristicas
from .morphology import limpar_mascara
from .preprocessing import (
    KERNEL_PADRAO_EXPERIMENTAL,
    LADO_MAXIMO_PX_EXPERIMENTAL,
    redimensionar,
    suavizar_gaussiano,
)
from .segmentation import FAIXA_VERDE_EXPERIMENTAL, segmentar_hsv
from .utils import Cronometro, ErroImagem, ler_imagem
from .visualizacao import gravar_etapas

#: Versão do contrato de resultado. Muda quando a estrutura do JSON muda.
VERSAO_PIPELINE = "1.0.0"

#: Diretório raiz das execuções. Ignorado pelo Git.
PASTA_EXECUCOES = Path(__file__).resolve().parent.parent / "resultados" / "execucoes"


def _serializar(valor: object) -> object:
    """Converte para tipos aceitos por JSON, sem NaN nem infinito.

    NumPy devolve ``np.float64`` e ``np.int64``, que o ``json`` padrão recusa. E um
    ``NaN`` serializado vira o literal ``NaN``, que **não é JSON válido** — muitos
    analisadores o rejeitam. Aqui vira ``null``, que é.
    """
    if valor is None:
        return None
    if isinstance(valor, (bool, str, int)):
        return valor
    if isinstance(valor, float):
        return valor if math.isfinite(valor) else None
    if isinstance(valor, (np.integer,)):
        return int(valor)
    if isinstance(valor, (np.floating,)):
        numero = float(valor)
        return numero if math.isfinite(numero) else None
    if isinstance(valor, np.bool_):
        return bool(valor)
    if isinstance(valor, np.ndarray):
        # Arrays de imagem ou de contorno nunca devem chegar ao JSON.
        return None
    if isinstance(valor, dict):
        return {str(chave): _serializar(item) for chave, item in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_serializar(item) for item in valor]
    return str(valor)


def _resultado_de_erro(erro: ErroImagem, arquivo: str | None = None) -> dict[str, object]:
    """Monta o resultado de erro, com a mesma forma do resultado de sucesso.

    Consumidores não precisam de dois formatos: as chaves existem sempre, e os blocos
    que não se aplicam vêm como ``None``.
    """
    return {
        "status": "erro",
        "versao_pipeline": VERSAO_PIPELINE,
        "id_execucao": None,
        "entrada": {"arquivo": arquivo} if arquivo else None,
        "processamento": None,
        "objeto": None,
        "caracteristicas": None,
        "classificacao": None,
        "avisos": [],
        "erro": {"codigo": erro.codigo, "mensagem": erro.mensagem},
        "imagens_intermediarias": {},
    }


def processar_matriz(
    imagem_bgr: np.ndarray,
    metadados: dict[str, object],
    salvar_imagens: bool = True,
    destino: str | Path | None = None,
    id_execucao: str | None = None,
) -> dict[str, object]:
    """Executa o pipeline sobre uma imagem já decodificada.

    Camada interna, compartilhada por CLI e API: as duas entram por
    :func:`processar_folha`, que lê o arquivo e delega para cá. Assim não há
    duplicação de lógica entre os pontos de entrada.

    Args:
        imagem_bgr: Imagem em BGR, 3 canais.
        metadados: Metadados da leitura.
        salvar_imagens: Gerar as oito imagens intermediárias.
        destino: Onde gravá-las. ``None`` usa ``resultados/execucoes/<id>``.
        id_execucao: Identificador. ``None`` gera um UUID.

    Returns:
        O resultado no contrato da Fase 1, pronto para serialização.
    """
    identificador = id_execucao or uuid.uuid4().hex
    tempos: dict[str, float] = {}

    with Cronometro() as total:
        with Cronometro() as cronometro:
            redimensionada, info = redimensionar(imagem_bgr)
        tempos["redimensionamento"] = round(cronometro.ms, 3)

        with Cronometro() as cronometro:
            suavizada = suavizar_gaussiano(redimensionada, KERNEL_PADRAO_EXPERIMENTAL)
        tempos["suavizacao"] = round(cronometro.ms, 3)

        with Cronometro() as cronometro:
            segmentacao = segmentar_hsv(suavizada)
        tempos["segmentacao"] = round(cronometro.ms, 3)

        with Cronometro() as cronometro:
            limpeza = limpar_mascara(segmentacao.mascara)
        tempos["limpeza"] = round(cronometro.ms, 3)

        with Cronometro() as cronometro:
            contorno = analisar_contorno(limpeza.mascara)
        tempos["contornos"] = round(cronometro.ms, 3)

        with Cronometro() as cronometro:
            caracteristicas = extrair_caracteristicas(redimensionada, limpeza.mascara, contorno)
        tempos["caracteristicas"] = round(cronometro.ms, 3)

        with Cronometro() as cronometro:
            classificacao = classificar_morfologia(caracteristicas)
        tempos["classificacao"] = round(cronometro.ms, 3)

        imagens: dict[str, str] = {}
        if salvar_imagens:
            with Cronometro() as cronometro:
                pasta = Path(destino) if destino else PASTA_EXECUCOES / identificador
                imagens = gravar_etapas(
                    pasta, redimensionada, suavizada,
                    segmentacao.mascara, limpeza.mascara, contorno,
                    texto=[
                        f"area {caracteristicas.dimensoes.area_contorno_px2:.0f} px2",
                        f"elong {caracteristicas.forma.elongacao:.2f}",
                        f"circ {caracteristicas.forma.circularidade:.3f}",
                        f"sol {caracteristicas.forma.solidez:.3f}",
                    ],
                )
            tempos["visualizacao"] = round(cronometro.ms, 3)

    avisos = _reunir_avisos(segmentacao.avisos, limpeza.avisos, contorno.avisos,
                            caracteristicas.avisos, classificacao.avisos)

    resultado: dict[str, object] = {
        "status": "sucesso_com_avisos" if avisos else "sucesso",
        "versao_pipeline": VERSAO_PIPELINE,
        "id_execucao": identificador,
        "entrada": {
            "arquivo": metadados.get("arquivo"),
            "formato": metadados.get("formato"),
            "largura_original_px": metadados.get("largura_original_px"),
            "altura_original_px": metadados.get("altura_original_px"),
            "largura_processada_px": info["largura_px"],
            "altura_processada_px": info["altura_px"],
            "bytes": metadados.get("bytes"),
            "tinha_canal_alfa": metadados.get("tinha_canal_alfa", False),
        },
        "processamento": {
            "etapas": [
                "validacao", "leitura", "redimensionamento", "suavizacao_gaussiana",
                "conversao_hsv", "segmentacao", "limpeza_morfologica", "contornos",
                "selecao_objeto", "caracteristicas", "classificacao",
            ],
            "parametros": {
                "lado_maximo_px": LADO_MAXIMO_PX_EXPERIMENTAL,
                "kernel_gaussiano": KERNEL_PADRAO_EXPERIMENTAL,
                "faixa_hsv": {k: list(v) for k, v in FAIXA_VERDE_EXPERIMENTAL.items()},
                "fator_escala": info["fator_escala"],
                "operacoes_limpeza": limpeza.operacoes,
            },
            "tempo_total_ms": round(total.ms, 3),
            "tempo_por_etapa_ms": tempos,
        },
        "objeto": {
            "detectado": True,
            "numero_contornos": contorno.numero_contornos,
            "dominancia": contorno.dominancia,
            "fracao_foreground": segmentacao.metricas.get("fracao_foreground"),
            "bbox": contorno.bbox,
            "bbox_rotacionada": contorno.bbox_rotacionada,
            "centroide": contorno.centroide,
            "toca_borda": contorno.toca_borda,
            "distancia_minima_borda_px": contorno.distancia_minima_borda_px,
            "orientacao_graus": contorno.orientacao_graus,
            "orientacao_confiavel": contorno.orientacao_confiavel,
            "anisotropia": contorno.anisotropia,
        },
        "caracteristicas": asdict(caracteristicas),
        "classificacao": asdict(classificacao),
        "avisos": avisos,
        "erro": None,
        "imagens_intermediarias": imagens,
    }

    return _serializar(resultado)  # type: ignore[return-value]


def processar_folha(
    caminho: str | Path,
    salvar_imagens: bool = True,
    destino: str | Path | None = None,
    id_execucao: str | None = None,
) -> dict[str, object]:
    """Ponto de entrada público: de um arquivo ao resultado estruturado.

    **Não levanta exceção de domínio.** Qualquer :class:`ErroImagem` vira um resultado
    com ``status: "erro"`` e o código correspondente — assim CLI e API tratam sucesso e
    falha pelo mesmo caminho.

    Args:
        caminho: Caminho da imagem.
        salvar_imagens: Gerar as imagens intermediárias.
        destino: Diretório de saída.
        id_execucao: Identificador da execução.

    Returns:
        O resultado no contrato da Fase 1.
    """
    nome = Path(caminho).name
    try:
        imagem, metadados = ler_imagem(caminho)
        return processar_matriz(imagem, metadados, salvar_imagens, destino, id_execucao)
    except ErroImagem as erro:
        return _resultado_de_erro(erro, nome)


def _reunir_avisos(*colecoes: list[str]) -> list[str]:
    """Junta os avisos das fases, **sem duplicar**, preservando a ordem."""
    vistos: set[str] = set()
    reunidos: list[str] = []
    for colecao in colecoes:
        for aviso in colecao:
            if aviso not in vistos:
                vistos.add(aviso)
                reunidos.append(aviso)
    return reunidos


def limpar_execucoes_antigas(idade_maxima_horas: float = 24.0) -> int:
    """Remove diretórios de execução mais antigos que o limite.

    Mecanismo simples e deliberadamente sem agendador: a API o chama antes de cada
    processamento, o que basta para evitar acúmulo indefinido num serviço local.

    Args:
        idade_maxima_horas: Idade acima da qual remover.

    Returns:
        Quantos diretórios foram removidos.
    """
    import shutil
    import time

    if not PASTA_EXECUCOES.is_dir():
        return 0

    limite = time.time() - idade_maxima_horas * 3600
    removidos = 0

    for pasta in PASTA_EXECUCOES.iterdir():
        if not pasta.is_dir():
            continue
        try:
            if pasta.stat().st_mtime < limite:
                shutil.rmtree(pasta, ignore_errors=True)
                # Conta só o que de fato saiu: com ignore_errors, um arquivo travado
                # (comum no Windows) deixaria a pasta — e ela seria contada toda vez.
                if not pasta.exists():
                    removidos += 1
        except OSError:
            continue

    return removidos
