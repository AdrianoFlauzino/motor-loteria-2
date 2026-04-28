import streamlit as st
import pandas as pd
import numpy as np
from estatisticas import (
    calcular_frequencia,
    calcular_atraso,
    calcular_pares_correlacao,
    calcular_distribuicao_quadrante,
    calcular_estatisticas_soma,
    calcular_estatisticas_paridade,
    calcular_estatisticas_primos,
    calcular_estatisticas_altas_baixas
)


@st.cache_data
def padronizar_df(_df):
    """
    Padroniza o DataFrame para ter colunas n1 a n6 com números inteiros ordenados.
    Assume que as primeiras 6 colunas são os números da loteria.
    """
    df = _df.iloc[:, :6].copy()
    df.columns = [f'n{i+1}' for i in range(6)]
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna()
    # Ordena os números em cada linha (sorteio)
    df = df.apply(lambda row: sorted(row), axis=1).apply(pd.Series)
    df.columns = [f'n{i+1}' for i in range(6)]
    return df.astype(int)


st.set_page_config(
    layout="wide",
    page_title="Estatísticas de Loterias",
    page_icon="📊"
)

st.title("📊 Análise Estatística Completa de Loterias")

st.markdown("---")

# Upload do arquivo CSV
uploaded_file = st.file_uploader(
    "Escolha um arquivo CSV com os resultados da loteria",
    type="csv",
    help="O CSV deve conter pelo menos 6 colunas numéricas com os números dos sorteios."
)

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        df_padronizado = padronizar_df(df)

        st.success(f"✅ Dados carregados e padronizados com sucesso! Total de sorteios: {len(df_padronizado):,}")

        st.subheader("Visualização dos dados padronizados (primeiros 10 sorteios)")
        st.dataframe(df_padronizado.head(10), use_container_width=True)

        st.markdown("---")

        # Criação das abas
        tab_frequencia, tab_atraso, tab_quadrantes, tab_soma, tab_paridade, tab_primos, tab_altas_baixas = st.tabs([
            "Frequência",
            "Atraso",
            "Quadrantes",
            "Soma",
            "Paridade",
            "Primos",
            "Altas/Baixas"
        ])

        with tab_frequencia:
            st.header("Frequência de Números")
            df_freq = calcular_frequencia(df_padronizado)
            st.dataframe(df_freq, use_container_width=True, hide_index=False)

        with tab_atraso:
            st.header("Atraso dos Números")
            df_atraso = calcular_atraso(df_padronizado)
            st.dataframe(df_atraso, use_container_width=True, hide_index=False)

        with tab_quadrantes:
            st.header("Análise de Quadrantes")
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Pares de Correlação")
                df_correl = calcular_pares_correlacao(df_padronizado)
                st.dataframe(df_correl, use_container_width=True, hide_index=False)
            with col2:
                st.subheader("Distribuição por Quadrante")
                df_quad = calcular_distribuicao_quadrante(df_padronizado)
                st.dataframe(df_quad, use_container_width=True, hide_index=False)

        with tab_soma:
            st.header("Estatísticas de Soma")
            df_soma = calcular_estatisticas_soma(df_padronizado)
            st.dataframe(df_soma, use_container_width=True, hide_index=False)

        with tab_paridade:
            st.header("Estatísticas de Paridade")
            df_paridade = calcular_estatisticas_paridade(df_padronizado)
            st.dataframe(df_paridade, use_container_width=True, hide_index=False)

        with tab_primos:
            st.header("Estatísticas de Números Primos")
            df_primos = calcular_estatisticas_primos(df_padronizado)
            st.dataframe(df_primos, use_container_width=True, hide_index=False)

        with tab_altas_baixas:
            st.header("Estatísticas de Altas/Baixas")
            df_altas_baixas = calcular_estatisticas_altas_baixas(df_padronizado)
            st.dataframe(df_altas_baixas, use_container_width=True, hide_index=False)

    except Exception as e:
        st.error(f"❌ Erro ao processar o arquivo: {str(e)}")
        st.info("Verifique se o CSV está no formato correto.")
else:
    st.info("👆 Por favor, faça o upload de um arquivo CSV para começar a análise.")

st.markdown("---")
st.markdown("*Aplicação desenvolvida para análise de loterias. Compatível com Streamlit Cloud.*")
