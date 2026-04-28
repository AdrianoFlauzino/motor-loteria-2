"""
MOTOR DE PROBABILIDADE 2.0 – Loterias
Autor: Adriano Flauzino
Descrição:
    Núcleo matemático completo para geração estruturada de bilhetes da
    Mega‑Sena com filtros, estratégias e motor probabilístico.

Módulos envolvidos:
    filtros.py         → Filtros matemáticos
    estatisticas.py    → Estatísticas históricas
    gerador.py         → Estratégias e pesos
    backtesting.py     → Simulação real
"""

import random
from filtros import (
    filtro_soma,
    filtro_paridade,
    filtro_primos,
    filtro_repetentes,
    filtro_distancia,
    filtro_quadrantes,
    filtro_sequencias
)
from estatisticas import (
    carregar_estatisticas,
    score_dezenas
)


# ----------------------------------------------------------------------
# FUNÇÃO: validar bilhete
# ----------------------------------------------------------------------
def validar_bilhete(bilhete, ultimo_sorteio):
    """
    Aplica todos os filtros simultaneamente.
    O bilhete só é aceito se passar por todos.
    """

    return (
        filtro_soma(bilhete)
        and filtro_paridade(bilhete)
        and filtro_primos(bilhete)
        and filtro_repetentes(bilhete, ultimo_sorteio)
        and filtro_distancia(bilhete)
        and filtro_quadrantes(bilhete)
        and filtro_sequencias(bilhete)
    )


# ----------------------------------------------------------------------
# FUNÇÃO: gerar bilhete via estratégia
# ----------------------------------------------------------------------
def gerar_bilhete_com_score(pesos):
    """
    Gera um bilhete usando pesos probabilísticos.
    pesos → dicionário com a pontuação de cada dezena (1 a 60)
    """

    dezenas = list(range(1, 61))
    scores = [pesos[d] for d in dezenas]

    bilhete = sorted(random.choices(
        population=dezenas,
        weights=scores,
        k=6
    ))

    # Garantir 6 dezenas distintas
    bilhete = sorted(set(bilhete))
    while len(bilhete) < 6:
        novo = random.choice(dezenas)
        if novo not in bilhete:
            bilhete.append(novo)

    return bilhete


# ----------------------------------------------------------------------
# FUNÇÃO: motor de geração (conservador / agressivo / híbrido / ponderado)
# ----------------------------------------------------------------------
def motor_loteria(qtd_bilhetes, estrategia, ultimo_sorteio, df_historico):
    """
    Estratégias disponíveis:
        - conservador
        - agressivo
        - hibrido
        - ponderado
    """

    estat = carregar_estatisticas(df_historico)

    if estrategia == "conservador":
        pesos = estat["freq_norm"]

    elif estrategia == "agressivo":
        pesos = estat["atraso_norm"]

    elif estrategia == "hibrido":
        pesos = {
            d: 0.5 * estat["freq_norm"][d] + 0.5 * estat["atraso_norm"][d]
            for d in range(1, 61)
        }

    elif estrategia == "ponderado":
        pesos = score_dezenas(df_historico)

    else:
        raise ValueError("Estratégia inválida.")

    bilhetes = []

    for _ in range(qtd_bilhetes):

        while True:
            b = gerar_bilhete_com_score(pesos)

            if validar_bilhete(b, ultimo_sorteio):
                bilhetes.append(b)
                break

    return bilhetes


# ----------------------------------------------------------------------
# FUNÇÃO AUXILIAR – execução direta
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import pandas as pd

    # Exemplo rápido de teste:
    df = pd.read_csv("loterias.csv")
    ultimo = [1, 5, 12, 23, 34, 45]

    pacote = motor_loteria(
        qtd_bilhetes=10,
        estrategia="hibrido",
        ultimo_sorteio=ultimo,
        df_historico=df
    )

    print("Bilhetes gerados:")
    for b in pacote:
        print(b)