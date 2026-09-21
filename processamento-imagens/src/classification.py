"""Classificação morfológica determinística por regras explícitas.

Camada de **interpretação** sobre as características da Fase 7. Traduz números em
descrições geométricas legíveis, sem esconder de onde veio cada decisão.

**O que esta camada não faz, e nunca fará:** identificar espécie, gênero ou família;
diagnosticar doença; atribuir nome científico; substituir avaliação botânica. Há teste
que falha se qualquer campo com esses nomes aparecer na saída.

**Não é inteligência artificial.** Não há modelo, não há treinamento, não há predição,
não há inferência estatística. São condições ``if``/``elif`` escritas por pessoas, sobre
limiares derivados de uma distribuição medida. A mesma entrada produz sempre a mesma
saída, e cada decisão vem acompanhada dos valores e limiares que a motivaram.

**Vocabulário:** *regra*, *classificação determinística*, *interpretação geométrica*,
*descrição morfológica*. Nunca *modelo*, *aprendizado*, *predição* ou *confiança*
probabilística.

Todos os limiares foram **calibrados no conjunto de desenvolvimento do Flavia** — 64
imagens, folhas isoladas sobre fundo branco. **Não são universais**, e estão marcados
como experimentais.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .features import CaracteristicasFolha

# ---------------------------------------------------------------------------
# Limiares — todos centralizados, todos experimentais
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Limiares:
    """Limiares das regras. **Experimentais, calibrados no Flavia.**

    Cada valor tem origem declarada na documentação da fase. Nenhum foi escolhido por
    conveniência: vieram de quartis ou de **vales** da distribuição observada — faixas
    onde nenhuma folha do conjunto cai, e que por isso separam sem cortar ninguém ao
    meio.
    """

    # Alongamento — quartis da distribuição: p25≈1,48, p75≈3,08, p90≈6,47.
    elongacao_baixa: float = 1.5
    elongacao_alta: float = 3.0
    elongacao_extrema: float = 6.0

    # Concavidade — 0,70 cai dentro do MAIOR vale da distribuição de solidez
    # (nenhuma folha entre 0,599 e 0,723). 0,92 ≈ p20.
    solidez_concavidade_alta: float = 0.70
    solidez_concavidade_baixa: float = 0.92

    # Compacidade — quartis de circularidade: p25≈0,415, p75≈0,645.
    # O teto digital é ≈0,90, não 1,0 — ver R14.
    circularidade_baixa: float = 0.40
    circularidade_alta: float = 0.65

    # Complexidade de borda — p75≈1,127 e p90≈1,288 da razão perímetro/hull.
    # A referência de forma convexa é ≈1,05, não 1,0.
    razao_borda_moderada: float = 1.13
    razao_borda_complexa: float = 1.30

    # Orientação — 0,05 é o limiar de confiabilidade da Fase 6, NÃO alterado.
    # 0,30 cai dentro do maior vale da anisotropia (nada entre 0,217 e 0,376).
    anisotropia_minima: float = 0.05
    anisotropia_bem_definida: float = 0.30

    # Margem relativa abaixo da qual o caso é considerado limítrofe.
    margem_limitrofe: float = 0.05


LIMIARES = Limiares()

#: Campos proibidos na saída. Verificado por teste.
CAMPOS_PROIBIDOS = frozenset({
    "especie", "genero", "familia", "nome_cientifico", "taxon", "taxonomia",
    "diagnostico", "doenca", "patologia", "saude", "probabilidade", "score",
    "confianca", "acuracia", "predicao",
})


@dataclass
class ResultadoRegra:
    """Uma classificação, com tudo o que a motivou.

    Attributes:
        atributo: Qual propriedade foi classificada.
        categoria: A descrição atribuída, ou ``"indeterminado"``.
        features_usadas: Nomes das características consultadas.
        valores: Valores observados.
        limiares_aplicados: Limiares usados nesta decisão.
        margem_relativa: Distância relativa ao limiar mais próximo. **Não é
            probabilidade nem confiança** — é a folga geométrica até a fronteira.
        limitrofe: Se o caso está perto de um limiar.
        observacoes: Ressalvas, ambiguidades e razões de indeterminação.
    """

    atributo: str
    categoria: str
    features_usadas: list[str] = field(default_factory=list)
    valores: dict[str, float | None] = field(default_factory=dict)
    limiares_aplicados: dict[str, float] = field(default_factory=dict)
    margem_relativa: float | None = None
    limitrofe: bool = False
    observacoes: list[str] = field(default_factory=list)


@dataclass
class ClassificacaoMorfologica:
    """Descrição multiatributo de uma folha.

    Uma folha tem várias propriedades ao mesmo tempo — não se reduz a uma classe única.
    """

    alongamento: ResultadoRegra
    concavidade: ResultadoRegra
    compacidade: ResultadoRegra
    complexidade_borda: ResultadoRegra
    orientacao: ResultadoRegra
    resumo: str
    avisos: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------

def _valido(valor: float | None, minimo: float | None = None, maximo: float | None = None) -> bool:
    """Confere que o valor é utilizável como base de decisão.

    Rejeita ``None``, ``NaN``, infinito e valores fora do domínio esperado. Uma regra
    nunca decide sobre número inválido — devolve ``indeterminado`` e diz por quê.
    """
    if valor is None or isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return False
    if not math.isfinite(valor):
        return False
    if minimo is not None and valor < minimo:
        return False
    if maximo is not None and valor > maximo:
        return False
    return True


def _margem(valor: float, limiares: tuple[float, ...]) -> float:
    """Distância relativa ao limiar mais próximo.

    **Não é confiança nem probabilidade.** É apenas quão longe o valor está da
    fronteira mais próxima, em fração do próprio limiar. Um valor de 2,01 contra um
    limiar de 2,00 dá margem 0,005 — caso limítrofe, não "alta certeza".
    """
    return round(min(abs(valor - limiar) / limiar for limiar in limiares if limiar != 0), 6)


def _indeterminado(atributo: str, motivo: str, features: list[str],
                   valores: dict[str, float | None]) -> ResultadoRegra:
    """Resultado para quando as métricas não sustentam uma categoria."""
    return ResultadoRegra(
        atributo=atributo,
        categoria="indeterminado",
        features_usadas=features,
        valores=valores,
        observacoes=[motivo],
    )


# ---------------------------------------------------------------------------
# Regras
# ---------------------------------------------------------------------------

def classificar_alongamento(elongacao: float | None, limiares: Limiares = LIMIARES) -> ResultadoRegra:
    """Classifica o quanto a folha é alongada.

    Usa **`elongacao`** (lado maior / lado menor da caixa de área mínima), e não o
    aspect ratio da caixa reta. O motivo é medido: na acícula ``2407`` o aspect ratio
    reto dá **1,68** — descrevendo o ângulo da foto — enquanto a elongação dá
    **32,59**, descrevendo a folha.

    A elongação é ainda a característica **imune aos vieses R14 e R22**: não usa
    perímetro nem área.

    Categorias: ``baixa`` · ``moderada`` · ``alta`` · ``extrema``.
    """
    features = ["elongacao"]
    valores: dict[str, float | None] = {"elongacao": elongacao}

    if not _valido(elongacao, minimo=1.0):
        return _indeterminado(
            "alongamento",
            "elongação ausente ou fora do domínio esperado (deve ser >= 1)",
            features, valores,
        )

    assert elongacao is not None
    fronteiras = (limiares.elongacao_baixa, limiares.elongacao_alta, limiares.elongacao_extrema)

    if elongacao < limiares.elongacao_baixa:
        categoria = "baixa"
    elif elongacao < limiares.elongacao_alta:
        categoria = "moderada"
    elif elongacao < limiares.elongacao_extrema:
        categoria = "alta"
    else:
        categoria = "extrema"

    margem = _margem(elongacao, fronteiras)
    return ResultadoRegra(
        atributo="alongamento",
        categoria=categoria,
        features_usadas=features,
        valores=valores,
        limiares_aplicados={
            "baixa_ate": limiares.elongacao_baixa,
            "alta_a_partir_de": limiares.elongacao_alta,
            "extrema_a_partir_de": limiares.elongacao_extrema,
        },
        margem_relativa=margem,
        limitrofe=margem < limiares.margem_limitrofe,
    )


def classificar_concavidade(
    solidez: float | None,
    elongacao: float | None,
    limiares: Limiares = LIMIARES,
) -> ResultadoRegra:
    """Classifica o recorte da borda — **com a ressalva do R25**.

    Usa `solidez` como medida principal, mas **não sozinha**. A Fase 7 mediu uma
    ambiguidade real:

    ===========  ===========  =========  ==============================
    Imagem       Elongação    Solidez    Causa da solidez baixa
    ===========  ===========  =========  ==============================
    ``1307``     1,14         0,52       borda profundamente lobada
    ``2400``     19,94        0,47       acícula **curvada**
    ===========  ===========  =========  ==============================

    Solidez de 0,47 e 0,52 são quase iguais — e as causas são completamente
    diferentes. O hull de um arco é muito maior que o arco, sem que exista recorte
    algum.

    **Por isso a regra combina solidez com elongação:** quando a elongação é extrema,
    a concavidade é declarada **ambígua**, não "alta". Rotular a acícula como
    "recortada" seria uma afirmação falsa produzida por uma regra correta demais para
    o seu próprio bem.

    Categorias: ``baixa`` · ``moderada`` · ``alta`` · ``ambigua``.
    """
    features = ["solidez", "elongacao"]
    valores: dict[str, float | None] = {"solidez": solidez, "elongacao": elongacao}

    if not _valido(solidez, minimo=0.0, maximo=1.0):
        return _indeterminado(
            "concavidade",
            "solidez ausente ou fora do domínio (0, 1]",
            features, valores,
        )

    assert solidez is not None
    fronteiras = (limiares.solidez_concavidade_alta, limiares.solidez_concavidade_baixa)
    margem = _margem(solidez, fronteiras)

    if solidez >= limiares.solidez_concavidade_baixa:
        categoria = "baixa"
        observacoes: list[str] = []
    elif solidez >= limiares.solidez_concavidade_alta:
        categoria = "moderada"
        observacoes = []
    else:
        categoria = "alta"
        observacoes = []

    # A ressalva do R25: elongação extrema torna a leitura ambígua.
    if categoria in ("alta", "moderada") and _valido(elongacao) and elongacao is not None:
        if elongacao >= limiares.elongacao_extrema:
            categoria = "ambigua"
            observacoes.append(
                f"solidez de {solidez:.3f} sugeriria borda recortada, mas a elongação de "
                f"{elongacao:.2f} indica objeto muito alongado — em forma curvada o envelope "
                "convexo é naturalmente maior, sem que haja recorte. Causa não distinguível "
                "apenas por estas medidas."
            )

    return ResultadoRegra(
        atributo="concavidade",
        categoria=categoria,
        features_usadas=features,
        valores=valores,
        limiares_aplicados={
            "alta_abaixo_de": limiares.solidez_concavidade_alta,
            "baixa_a_partir_de": limiares.solidez_concavidade_baixa,
            "elongacao_que_torna_ambiguo": limiares.elongacao_extrema,
        },
        margem_relativa=margem,
        limitrofe=margem < limiares.margem_limitrofe,
        observacoes=observacoes,
    )


def classificar_compacidade(
    circularidade: float | None,
    limiares: Limiares = LIMIARES,
) -> ResultadoRegra:
    """Classifica a compacidade geométrica pela circularidade.

    **O limiar de "alta" é 0,65, e não 0,9.** A Fase 6 mediu que um círculo digital
    perfeito converge para ≈ **0,8973** — nunca 1,0 —, porque o perímetro é
    superestimado em ~5% e entra ao quadrado. O máximo observado nas 64 folhas é
    **0,8143**.

    Um limiar de 0,9 classificaria **nenhuma folha** como compacta, e um de 0,95,
    nem o próprio círculo.

    Os valores 0,40 e 0,65 são os quartis observados (p25 ≈ 0,415, p75 ≈ 0,645).

    Categorias: ``baixa`` · ``moderada`` · ``alta``.
    """
    features = ["circularidade"]
    valores: dict[str, float | None] = {"circularidade": circularidade}

    if not _valido(circularidade, minimo=0.0, maximo=1.0):
        return _indeterminado(
            "compacidade",
            "circularidade ausente ou fora do domínio (0, 1]",
            features, valores,
        )

    assert circularidade is not None
    fronteiras = (limiares.circularidade_baixa, limiares.circularidade_alta)

    if circularidade < limiares.circularidade_baixa:
        categoria = "baixa"
    elif circularidade < limiares.circularidade_alta:
        categoria = "moderada"
    else:
        categoria = "alta"

    margem = _margem(circularidade, fronteiras)
    return ResultadoRegra(
        atributo="compacidade",
        categoria=categoria,
        features_usadas=features,
        valores=valores,
        limiares_aplicados={
            "baixa_abaixo_de": limiares.circularidade_baixa,
            "alta_a_partir_de": limiares.circularidade_alta,
        },
        margem_relativa=margem,
        limitrofe=margem < limiares.margem_limitrofe,
        observacoes=[
            "a circularidade tem teto digital de aproximadamente 0,90 (R14); "
            "os limiares refletem a distribuição observada, não o valor teórico de 1,0"
        ],
    )


def classificar_complexidade_borda(
    razao_perimetro_hull: float | None,
    limiares: Limiares = LIMIARES,
) -> ResultadoRegra:
    """Classifica a complexidade da borda pela razão perímetro/hull.

    **Métrica experimental**, e a documentação precisa dizer isso. Dois motivos:

    1. **A referência não é 1,0.** Um círculo digital — perfeitamente convexo — dá
       **1,0507**, porque o viés do perímetro (R14) afeta o numerador e não o
       denominador: o contorno tem escada, o hull é um polígono de vértices.
    2. Ela correlaciona −0,743 com a solidez, que mede a mesma ideia por área e é
       imune ao R14.

    Continua reportada porque discrimina bem — 2,02 na folha lobada contra 1,07 no
    círculo — mas os limiares partem de 1,05, não de 1,0.

    Categorias: ``regular`` · ``moderada`` · ``complexa``.
    """
    features = ["razao_perimetro_hull"]
    valores: dict[str, float | None] = {"razao_perimetro_hull": razao_perimetro_hull}

    if not _valido(razao_perimetro_hull, minimo=1.0):
        return _indeterminado(
            "complexidade_borda",
            "razão perímetro/hull ausente ou fora do domínio esperado (deve ser >= 1)",
            features, valores,
        )

    assert razao_perimetro_hull is not None
    fronteiras = (limiares.razao_borda_moderada, limiares.razao_borda_complexa)

    if razao_perimetro_hull < limiares.razao_borda_moderada:
        categoria = "regular"
    elif razao_perimetro_hull < limiares.razao_borda_complexa:
        categoria = "moderada"
    else:
        categoria = "complexa"

    margem = _margem(razao_perimetro_hull, fronteiras)
    return ResultadoRegra(
        atributo="complexidade_borda",
        categoria=categoria,
        features_usadas=features,
        valores=valores,
        limiares_aplicados={
            "moderada_a_partir_de": limiares.razao_borda_moderada,
            "complexa_a_partir_de": limiares.razao_borda_complexa,
        },
        margem_relativa=margem,
        limitrofe=margem < limiares.margem_limitrofe,
        observacoes=[
            "métrica experimental: a referência de forma convexa é aproximadamente 1,05, "
            "e não 1,0, por efeito do viés do perímetro digital (R14)"
        ],
    )


def classificar_orientacao(
    angulo_graus: float | None,
    anisotropia: float | None,
    limiares: Limiares = LIMIARES,
) -> ResultadoRegra:
    """Classifica **quão definido** é o eixo principal — não a direção.

    > **O ângulo descreve a pose na imagem, não a forma da folha.** "Horizontal",
    > "vertical" ou "diagonal" são propriedades do enquadramento: a mesma folha
    > fotografada girada teria outro ângulo e continuaria sendo a mesma folha. Por isso
    > esta regra classifica a **definição** do eixo, e nunca a direção.

    O ângulo é reportado nos valores, para quem precisar dele, sempre acompanhado da
    anisotropia.

    Categorias: ``bem_definida`` · ``pouco_definida`` · ``indefinida``.
    """
    features = ["anisotropia", "orientacao_graus"]
    valores: dict[str, float | None] = {"anisotropia": anisotropia, "angulo_graus": angulo_graus}

    if not _valido(anisotropia, minimo=0.0, maximo=1.0):
        return _indeterminado(
            "orientacao",
            "anisotropia ausente ou fora do domínio [0, 1]",
            features, valores,
        )

    assert anisotropia is not None
    observacoes: list[str] = []

    if anisotropia < limiares.anisotropia_minima:
        categoria = "indefinida"
        observacoes.append(
            f"anisotropia de {anisotropia:.4f} abaixo de {limiares.anisotropia_minima}: "
            "não há eixo dominante, e o ângulo não tem significado estável"
        )
    elif anisotropia < limiares.anisotropia_bem_definida:
        categoria = "pouco_definida"
        observacoes.append(
            f"anisotropia de {anisotropia:.4f}: eixo existe, mas é fraco — o ângulo pode "
            "variar com pequenas alterações da borda"
        )
    else:
        categoria = "bem_definida"

    fronteiras = (limiares.anisotropia_minima, limiares.anisotropia_bem_definida)
    margem = _margem(anisotropia, fronteiras)

    return ResultadoRegra(
        atributo="orientacao",
        categoria=categoria,
        features_usadas=features,
        valores=valores,
        limiares_aplicados={
            "indefinida_abaixo_de": limiares.anisotropia_minima,
            "bem_definida_a_partir_de": limiares.anisotropia_bem_definida,
        },
        margem_relativa=margem,
        limitrofe=margem < limiares.margem_limitrofe,
        observacoes=observacoes,
    )


# ---------------------------------------------------------------------------
# Resumo e orquestração
# ---------------------------------------------------------------------------

_TEXTO_ALONGAMENTO = {
    "baixa": "pouco alongada",
    "moderada": "moderadamente alongada",
    "alta": "bastante alongada",
    "extrema": "extremamente alongada",
    "indeterminado": "com alongamento indeterminado",
}

_TEXTO_CONCAVIDADE = {
    "baixa": "borda pouco recortada",
    "moderada": "borda moderadamente recortada",
    "alta": "borda fortemente recortada",
    "ambigua": "concavidade ambígua — pode ser recorte ou curvatura",
    "indeterminado": "concavidade indeterminada",
}

_TEXTO_COMPACIDADE = {
    "baixa": "geometricamente pouco compacta",
    "moderada": "compacidade intermediária",
    "alta": "geometricamente compacta",
    "indeterminado": "compacidade indeterminada",
}

_TEXTO_ORIENTACAO = {
    "bem_definida": "eixo principal bem definido",
    "pouco_definida": "eixo principal pouco definido",
    "indefinida": "sem eixo principal definido",
    "indeterminado": "orientação indeterminada",
}


def montar_resumo(
    alongamento: ResultadoRegra,
    concavidade: ResultadoRegra,
    compacidade: ResultadoRegra,
    orientacao: ResultadoRegra,
) -> str:
    """Monta uma frase a partir das categorias já decididas.

    O texto é composto por **concatenação de mapeamentos fixos** — nenhum modelo de
    linguagem participa, e nada é gerado. Mudar uma categoria muda exatamente a parte
    correspondente da frase.
    """
    partes = [
        f"Folha {_TEXTO_ALONGAMENTO.get(alongamento.categoria, alongamento.categoria)}",
        _TEXTO_COMPACIDADE.get(compacidade.categoria, compacidade.categoria),
        f"com {_TEXTO_CONCAVIDADE.get(concavidade.categoria, concavidade.categoria)}",
        f"e {_TEXTO_ORIENTACAO.get(orientacao.categoria, orientacao.categoria)}",
    ]
    return ", ".join(partes) + "."


def classificar_morfologia(
    caracteristicas: CaracteristicasFolha,
    limiares: Limiares = LIMIARES,
) -> ClassificacaoMorfologica:
    """Aplica todas as regras e monta a descrição multiatributo.

    Args:
        caracteristicas: Saída da Fase 7.
        limiares: Conjunto de limiares. O padrão é o calibrado no Flavia.

    Returns:
        A classificação, com cada atributo auditável.
    """
    forma = caracteristicas.forma

    alongamento = classificar_alongamento(forma.elongacao, limiares)
    concavidade = classificar_concavidade(forma.solidez, forma.elongacao, limiares)
    compacidade = classificar_compacidade(forma.circularidade, limiares)
    complexidade = classificar_complexidade_borda(
        caracteristicas.convexidade.razao_perimetro_hull, limiares
    )
    orientacao = classificar_orientacao(
        caracteristicas.orientacao.angulo_graus,
        caracteristicas.orientacao.anisotropia,
        limiares,
    )

    regras = [alongamento, concavidade, compacidade, complexidade, orientacao]

    avisos: list[str] = []
    limitrofes = [regra.atributo for regra in regras if regra.limitrofe]
    if limitrofes:
        avisos.append(f"atributos proximos de um limiar: {', '.join(limitrofes)}")

    indeterminados = [regra.atributo for regra in regras if regra.categoria == "indeterminado"]
    if indeterminados:
        avisos.append(f"atributos indeterminados: {', '.join(indeterminados)}")

    if concavidade.categoria == "ambigua":
        avisos.append("concavidade ambigua: ver observacoes do atributo")

    avisos.append(
        "descricao geometrica automatica; nao constitui identificacao botanica nem taxonomica"
    )

    return ClassificacaoMorfologica(
        alongamento=alongamento,
        concavidade=concavidade,
        compacidade=compacidade,
        complexidade_borda=complexidade,
        orientacao=orientacao,
        resumo=montar_resumo(alongamento, concavidade, compacidade, orientacao),
        avisos=avisos,
    )
