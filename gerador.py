"""
Motor gerador de bilhetes da Loteria 2.0.
Gera bilhetes baseados em scores calculados a partir de frequência, atraso e correlação.
"""

import random


def normalizar(dic: dict[int, float]) -> dict[int, float]:
    """
    Normaliza os valores do dicionário para o intervalo [0, 1] usando min-max.

    :param dic: Dicionário com chaves de 1 a 60 e valores numéricos.
    :return: Dicionário normalizado.
    """
    if not dic:
        return {}
    valores = list(dic.values())
    min_v = min(valores)
    max_v = max(valores)
    if max_v == min_v:
        return {k: 0.5 for k in dic}
    return {k: (v - min_v) / (max_v - min_v) for k, v in dic.items()}


def score_conservador(freq: dict[int, float]) -> dict[int, float]:
    """
    Calcula score conservador baseado na frequência normalizada.

    :param freq: Dicionário de frequências.
    :return: Scores normalizados.
    """
    return normalizar(freq)


def score_agressivo(atraso: dict[int, float]) -> dict[int, float]:
    """
    Calcula score agressivo baseado no atraso normalizado.

    :param atraso: Dicionário de atrasos.
    :return: Scores normalizados.
    """
    return normalizar(atraso)


def score_hibrido(freq: dict[int, float], atraso: dict[int, float]) -> dict[int, float]:
    """
    Calcula score híbrido: soma de frequência e atraso normalizados.

    :param freq: Dicionário de frequências.
    :param atraso: Dicionário de atrasos.
    :return: Scores híbridos.
    """
    nf = normalizar(freq)
    na = normalizar(atraso)
    scores = {}
    for k in range(1, 61):
        scores[k] = nf.get(k, 0.0) + na.get(k, 0.0)
    return scores


def score_ponderado(freq: dict[int, float], atraso: dict[int, float], correlacao: dict[int, float]) -> dict[int, float]:
    """
    Calcula score ponderado: 0.45*freq + 0.35*atraso + 0.20*correlacao (normalizados).

    :param freq: Dicionário de frequências.
    :param atraso: Dicionário de atrasos.
    :param correlacao: Dicionário de correlações.
    :return: Scores ponderados.
    """
    nf = normalizar(freq)
    na = normalizar(atraso)
    nc = normalizar(correlacao)
    scores = {}
    for k in range(1, 61):
        scores[k] = 0.45 * nf.get(k, 0.0) + 0.35 * na.get(k, 0.0) + 0.20 * nc.get(k, 0.0)
    return scores


def obter_scores(estrategia: str, freq: dict[int, float], atraso: dict[int, float], correlacao: dict[int, float]) -> dict[int, float]:
    """
    Obtém os scores de acordo com a estratégia selecionada.

    Estratégias: 'conservador', 'agressivo', 'hibrido', 'ponderado'.

    :param estrategia: Nome da estratégia.
    :param freq: Dicionário de frequências.
    :param atraso: Dicionário de atrasos.
    :param correlacao: Dicionário de correlações.
    :return: Dicionário de scores.
    :raises ValueError: Se estratégia inválida.
    """
    if estrategia == "conservador":
        return score_conservador(freq)
    elif estrategia == "agressivo":
        return score_agressivo(atraso)
    elif estrategia == "hibrido":
        return score_hibrido(freq, atraso)
    elif estrategia == "ponderado":
        return score_ponderado(freq, atraso, correlacao)
    else:
        raise ValueError(f"Estratégia inválida: {estrategia}")


def gerar_dezena(scores: dict[int, float]) -> int:
    """
    Gera uma dezena (1-60) via sorteio ponderado pelos scores.

    :param scores: Dicionário de scores para cada dezena.
    :return: Dezena selecionada.
    """
    numeros = list(range(1, 61))
    pesos = [max(scores.get(n, 0.0), 1e-6) for n in numeros]
    return random.choices(numeros, weights=pesos, k=1)[0]


def gerar_bilhete(estrategia: str, freq: dict[int, float], atraso: dict[int, float], correlacao: dict[int, float]) -> list[int]:
    """
    Gera um bilhete completo com 6 dezenas únicas e ordenadas.

    :param estrategia: Nome da estratégia.
    :param freq: Dicionário de frequências.
    :param atraso: Dicionário de atrasos.
    :param correlacao: Dicionário de correlações.
    :return: Lista de 6 dezenas ordenadas.
    """
    scores = obter_scores(estrategia, freq, atraso, correlacao)
    bilhete = set()
    while len(bilhete) < 6:
        dezena = gerar_dezena(scores)
        bilhete.add(dezena)
    return sorted(bilhete)


def gerar_pacote(qtd: int, estrategia: str, freq: dict[int, float], atraso: dict[int, float], correlacao: dict[int, float]) -> list[list[int]]:
    """
    Gera um pacote com a quantidade especificada de bilhetes.

    :param qtd: Quantidade de bilhetes.
    :param estrategia: Nome da estratégia.
    :param freq: Dicionário de frequências.
    :param atraso: Dicionário de atrasos.
    :param correlacao: Dicionário de correlações.
    :return: Lista de bilhetes.
    """
    return [gerar_bilhete(estrategia, freq, atraso, correlacao) for _ in range(qtd)]
