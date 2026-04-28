import pandas as pd
from collections import Counter
def eh_primo(n: int) -> bool:
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True

def calcular_frequencia(df: pd.DataFrame) -> dict:
    cols = [f'n{i}' for i in range(1, 7)]
    melted = df[cols].melt(value_name='numero')
    return melted['numero'].value_counts().to_dict()

def calcular_atraso(df: pd.DataFrame) -> dict:
    cols = [f'n{i}' for i in range(1, 7)]
    ultimo_idx = len(df) - 1
    aparicoes = {num: [] for num in range(1, 61)}
    for idx, row in df.iterrows():
        for col in cols:
            num = int(row[col])
            aparicoes[num].append(idx)
    atrasos = {}
    for num in range(1, 61):
        if aparicoes[num]:
            atrasos[num] = ultimo_idx - aparicoes[num][-1]
        else:
            atrasos[num] = ultimo_idx + 1
    return atrasos

def calcular_pares_correlacao(df: pd.DataFrame) -> dict:
    pares = Counter()
    cols = [f'n{i}' for i in range(1, 7)]
    for _, row in df.iterrows():
        nums = sorted([int(row[col]) for col in cols])
        for i in range(6):
            for j in range(i + 1, 6):
                par = (nums[i], nums[j])
                pares[par] += 1
    return dict(pares)

def calcular_distribuicao_quadrante(df: pd.DataFrame) -> dict:
    def get_quadrante(num: int) -> str:
        if num <= 30:
            if num % 2 == 0:
                return 'Q1_Baixa_Par'
            else:
                return 'Q2_Baixa_Impar'
        else:
            if num % 2 == 0:
                return 'Q4_Alta_Par'
            else:
                return 'Q3_Alta_Impar'
    cols = [f'n{i}' for i in range(1, 7)]
    melted = df[cols].melt(value_name='numero')
    melted['quadrante'] = melted['numero'].apply(get_quadrante)
    return melted['quadrante'].value_counts().to_dict()

def calcular_estatisticas_soma(df: pd.DataFrame) -> dict:
    cols = [f'n{i}' for i in range(1, 7)]
    somas = df[cols].sum(axis=1)
    return {
        'minima': float(somas.min()),
        'maxima': float(somas.max()),
        'media': float(somas.mean()),
        'mediana': float(somas.median()),
        'desvio_padrao': float(somas.std())
    }

def calcular_estatisticas_paridade(df: pd.DataFrame) -> dict:
    cols = [f'n{i}' for i in range(1, 7)]
    contagens_pares = []
    for _, row in df.iterrows():
        pares = sum(1 for col in cols if int(row[col]) % 2 == 0)
        contagens_pares.append(pares)
    return {'distribuicao': dict(Counter(contagens_pares))}

def calcular_estatisticas_primos(df: pd.DataFrame) -> dict:
    cols = [f'n{i}' for i in range(1, 7)]
    contagens_primos = []
    for _, row in df.iterrows():
        primos = sum(1 for col in cols if eh_primo(int(row[col])))
        contagens_primos.append(primos)
    return {'distribuicao': dict(Counter(contagens_primos))}

def calcular_estatisticas_altas_baixas(df: pd.DataFrame) -> dict:
    cols = [f'n{i}' for i in range(1, 7)]
    contagens_baixas = []
    for _, row in df.iterrows():
        baixas = sum(1 for col in cols if int(row[col]) <= 30)
        contagens_baixas.append(baixas)
    return {'distribuicao': dict(Counter(contagens_baixas))}