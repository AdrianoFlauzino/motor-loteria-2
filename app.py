import streamlit as st
import pandas as pd
import estatisticas

st.set_page_config(page_title="Análise de Estatísticas", page_icon="📊", layout="wide")

st.title("📊 Análise Completa de Estatísticas de Sorteios")

st.sidebar.header("Carregar Dados")
uploaded_file = st.sidebar.file_uploader("Escolha um arquivo CSV", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.sidebar.success("Arquivo carregado com sucesso!")
        st.sidebar.write(f"Shape: {df.shape}")
        st.sidebar.dataframe(df.head())

        st.header("Visualização dos Dados Originais")
        st.dataframe(df.head(10))

        tabs = st.tabs(["Frequência", "Atraso", "Quadrantes", "Soma", "Paridade", "Primos", "Altas/Baixas"])

        with tabs[0]:
            st.subheader("Frequência dos Números")
            freq_df = estatisticas.calcular_frequencia(df)
            st.dataframe(freq_df)

        with tabs[1]:
            st.subheader("Atraso dos Números")
            atraso_df = estatisticas.calcular_atraso(df)
            st.dataframe(atraso_df)

        with tabs[2]:
            st.subheader("Distribuição por Quadrantes")
            quadrante_df = estatisticas.calcular_distribuicao_quadrante(df)
            st.dataframe(quadrante_df)

        with tabs[3]:
            st.subheader("Estatísticas de Soma")
            soma_df = estatisticas.calcular_estatisticas_soma(df)
            st.dataframe(soma_df)

        with tabs[4]:
            st.subheader("Estatísticas de Paridade")
            paridade_df = estatisticas.calcular_estatisticas_paridade(df)
            st.dataframe(paridade_df)

        with tabs[5]:
            st.subheader("Estatísticas de Números Primos")
            primos_df = estatisticas.calcular_estatisticas_primos(df)
            st.dataframe(primos_df)

        with tabs[6]:
            st.subheader("Estatísticas Altas/Baixas")
            altas_baixas_df = estatisticas.calcular_estatisticas_altas_baixas(df)
            st.dataframe(altas_baixas_df)

    except Exception as e:
        st.error(f"Erro ao carregar o arquivo: {str(e)}")
else:
    st.info("👈 Por favor, carregue um arquivo CSV no sidebar para visualizar as estatísticas.")

st.sidebar.markdown("---")
