import streamlit as st
import pandas as pd
from estatisticas import calcular_frequencia, calcular_atraso, calcular_quadrantes, calcular_soma, calcular_paridade, calcular_primos, calcular_altas_baixas

st.set_page_config(page_title="Análise Estatística de Números", page_icon="📊", layout="wide")

st.title("📊 Análise Estatística Completa de Números da Loteria")

@st.cache_data
def padronizar_colunas(df):
    """Padroniza as colunas numéricas para n1 a n6."""
    df = df.copy()
    numeric_cols = df.select_dtypes(include=['number']).columns[:6]
    if len(numeric_cols) < 6:
        st.error("O arquivo deve conter pelo menos 6 colunas numéricas.")
        st.stop()
    df = df.rename(columns={numeric_cols[i]: f'n{i+1}' for i in range(6)})
    df = df[['n1', 'n2', 'n3', 'n4', 'n5', 'n6']].dropna()
    return df

uploaded_file = st.file_uploader("Carregue o arquivo CSV com os resultados:", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        df_padronizado = padronizar_colunas(df)
        
        st.success(f"✅ Dados carregados com sucesso! {len(df_padronizado)} linhas processadas.")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.subheader("Visualização dos Dados")
            st.dataframe(df_padronizado.head(10), use_container_width=True)
        with col2:
            st.subheader("Resumo Estatístico")
            st.dataframe(df_padronizado.describe(), use_container_width=True)
        
        tabs = st.tabs(["Frequência", "Atraso", "Quadrantes", "Soma", "Paridade", "Primos", "Altas/Baixas"])
        
        with tabs[0]:
            st.subheader("Frequência de Números")
            freq_data = calcular_frequencia(df_padronizado)
            st.dataframe(freq_data, use_container_width=True)
        
        with tabs[1]:
            st.subheader("Atraso dos Números")
            atraso_data = calcular_atraso(df_padronizado)
            st.dataframe(atraso_data, use_container_width=True)
        
        with tabs[2]:
            st.subheader("Distribuição por Quadrantes")
            quad_data = calcular_quadrantes(df_padronizado)
            st.dataframe(quad_data, use_container_width=True)
        
        with tabs[3]:
            st.subheader("Soma dos Números")
            soma_data = calcular_soma(df_padronizado)
            st.dataframe(soma_data, use_container_width=True)
        
        with tabs[4]:
            st.subheader("Paridade (Pares/Ímpares)")
            paridade_data = calcular_paridade(df_padronizado)
            st.dataframe(paridade_data, use_container_width=True)
        
        with tabs[5]:
            st.subheader("Números Primos")
            primos_data = calcular_primos(df_padronizado)
            st.dataframe(primos_data, use_container_width=True)
        
        with tabs[6]:
            st.subheader("Altas / Baixas")
            altas_baixas_data = calcular_altas_baixas(df_padronizado)
            st.dataframe(altas_baixas_data, use_container_width=True)
        
    except Exception as e:
        st.error(f"❌ Erro ao processar o arquivo: {str(e)}")
else:
    st.info("👆 Por favor, carregue um arquivo CSV para começar a análise.")
