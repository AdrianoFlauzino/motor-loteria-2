import pandas as pd


def calcular_acertos(bilhete, resultado):
    """
    Calcula o número de acertos entre um bilhete e o resultado real.

    :param bilhete: lista de números do bilhete (6 números únicos)
    :param resultado: lista de números do resultado (6 números)
    :return: int - número de acertos
    """
    return len(set(bilhete) & set(resultado))


def executar_backtesting(df, estrategia, freq, atraso, correlacao, qtd_bilhetes, janela):
    """
    Executa backtesting da estratégia nos dados históricos da loteria.

    Percorre cada concurso, usa dados anteriores para gerar bilhetes via estratégia,
    compara com resultado real e computa estatísticas por concurso.

    :param df: DataFrame com colunas 'concurso' (int) e 'resultado' (lista de 6 ints),
               ordenado por concurso crescente.
    :param estrategia: callable(historico_df, freq, atraso, correlacao, qtd_bilhetes, janela) -> list[lists]
    :param freq: parâmetro de frequência para a estratégia
    :param atraso: parâmetro de atraso para a estratégia
    :param correlacao: parâmetro de correlação para a estratégia
    :param qtd_bilhetes: quantidade aproximada de bilhetes a gerar por concurso
    :param janela: tamanho da janela histórica para a estratégia
    :return: DataFrame com estatísticas por concurso
    """
    resultados = []
    for idx in range(len(df)):
        historico = df.iloc[:idx]
        bilhetes = estrategia(historico, freq, atraso, correlacao, qtd_bilhetes, janela)
        if not bilhetes:
            continue
        resultado_real = set(df.iloc[idx]['resultado'])
        acertos_lista = [calcular_acertos(bilhete, resultado_real) for bilhete in bilhetes]
        max_acertos = max(acertos_lista)
        media_acertos = sum(acertos_lista) / len(acertos_lista)
        quadras = acertos_lista.count(4)
        quinas = acertos_lista.count(5)
        senas = acertos_lista.count(6)
        concurso = df.iloc[idx]['concurso']
        resultados.append({
            'concurso': concurso,
            'qtd_bilhetes': len(bilhetes),
            'max_acertos': max_acertos,
            'media_acertos': round(media_acertos, 2),
            'quadras': quadras,
            'quinas': quinas,
            'senas': senas
        })
    return pd.DataFrame(resultados)


def resumo_backtesting(df_backtest):
    """
    Gera resumo consolidado das métricas de desempenho do backtesting.

    :param df_backtest: DataFrame retornado por executar_backtesting
    :return: dict com métricas consolidadas (média de acertos, distribuição, quadras, quinas, senas)
    """
    if df_backtest.empty:
        return {}

    total_concursos = len(df_backtest)
    total_bilhetes = df_backtest['qtd_bilhetes'].sum()
    media_max_acertos = round(df_backtest['max_acertos'].mean(), 2)
    total_acertos = sum(df_backtest['media_acertos'] * df_backtest['qtd_bilhetes'])
    media_acertos = round(total_acertos / total_bilhetes, 2)
    distribuicao_max_acertos = df_backtest['max_acertos'].value_counts().sort_index().to_dict()
    total_quadras = df_backtest['quadras'].sum()
    total_quinas = df_backtest['quinas'].sum()
    total_senas = df_backtest['senas'].sum()

    resumo = {
        'total_concursos': total_concursos,
        'total_bilhetes': int(total_bilhetes),
        'media_max_acertos': media_max_acertos,
        'media_acertos_por_bilhete': media_acertos,
        'distribuicao_max_acertos': distribuicao_max_acertos,
        'total_quadras': total_quadras,
        'total_quinas': total_quinas,
        'total_senas': total_senas,
        'taxa_quadra_pct': round(total_quadras / total_bilhetes * 100, 4),
        'taxa_quina_pct': round(total_quinas / total_bilhetes * 100, 4),
        'taxa_sena_pct': round(total_senas / total_bilhetes * 100, 4)
    }
    return resumo
