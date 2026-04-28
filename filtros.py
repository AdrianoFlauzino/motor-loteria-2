# filtros.py - Filtros matemáticos para Motor Loteria 2.0

"""
Funções para validar jogos de loteria (6 números ordenados únicos de 1 a 60).
Cada filtro retorna True se o jogo passa, False caso contrário.
"""

from collections import Counter
from typing import List

PRIMOS: set[int] = {2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59}

QUADRANTE_LIMITES = [(1,15), (16,30), (31,45), (46,60)]

def get_quadrante(n: int) -> int:
    """Retorna o quadrante do número (1 a 4)."""
    for i, (ini, fim) in enumerate(QUADRANTE_LIMITES, 1):
        if ini <= n <= fim:
            return i
    return 0

def get_decada(n: int) -> int:
    """Retorna a década do número (1 a 6)."""
    return (n - 1) // 10 + 1

def filtro_soma(jogo: List[int]) -> bool:
    """Soma dos números entre 100 e 230."""
    total = sum(jogo)
    return 100 <= total <= 230

def filtro_paridade(jogo: List[int]) -> bool:
    """Número de pares entre 2 e 4."""
    pares = sum(1 for n in jogo if n % 2 == 0)
    return 2 <= pares <= 4

def filtro_primos(jogo: List[int]) -> bool:
    """Número de primos entre 1 e 3."""
    count = sum(1 for n in jogo if n in PRIMOS)
    return 1 <= count <= 3

def filtro_altas_baixas(jogo: List[int]) -> bool:
    """Número de baixas (1-30) entre 2 e 4."""
    baixas = sum(1 for n in jogo if n <= 30)
    return 2 <= baixas <= 4

def filtro_distancia_media(jogo: List[int]) -> bool:
    """Distância média consecutiva entre 8 e 13."""
    dists = [jogo[i+1] - jogo[i] for i in range(5)]
    media = sum(dists) / 5
    return 8 <= media <= 13

def filtro_quadrantes(jogo: List[int]) -> bool:
    """Máximo 3 números por quadrante, pelo menos 3 quadrantes utilizados."""
    counts = [0] * 4
    for n in jogo:
        q = get_quadrante(n)
        if q > 0:
            counts[q-1] += 1
    max_count = max(counts)
    num_usados = sum(c > 0 for c in counts)
    return max_count <= 3 and num_usados >= 3

def filtro_padroes_proibidos(jogo: List[int]) -> bool:
    """Sem mais de 2 consecutivos, sem mais de 3 na mesma década."""
    # Consecutivos
    max_cons = 1
    cons = 1
    for i in range(1, 6):
        if jogo[i] == jogo[i-1] + 1:
            cons += 1
            if cons > max_cons:
                max_cons = cons
        else:
            cons = 1
    if max_cons > 2:
        return False
    
    # Décadas
    decadas = Counter(get_decada(n) for n in jogo)
    if any(v > 3 for v in decadas.values()):
        return False
    
    return True

def filtro_repetentes(jogo: List[int], anterior: List[int]) -> bool:
    """Número de repetentes com anterior entre 1 e 3."""
    comuns = len(set(jogo) & set(anterior))
    return 1 <= comuns <= 3
