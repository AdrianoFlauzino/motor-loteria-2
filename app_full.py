import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.io as pio
from itertools import combinations

# ==========================================
# TEMA BRANCO EXECUTIVO
# ==========================================
def apply_white_theme():
    pio.templates.default = "plotly_white"
    st.markdown('''
    <style>
    .stApp { background-color: #FFFFFF; }
    h1, h2, h3 { color: #0A2342 !important; }
    .stMarkdown p, .stText { color: #333333; }
    [data-testid="metric-container"] .stMetricValue { color: #0066CC !important; font-size: 2.5rem !important; font-weight: 700 !important; }
    [data-testid="metric-container"] .stMetricLabel { color: #333333 !important; font-size: 1rem !important; }
    .stButton > button { background-color: #0066CC; color: white; border-radius: 6px; font-weight: 500; }
    .stButton > button:hover { background-color: #0052A3; }
    </style>
    ''', unsafe_allow_html=True)

# ==========================================
# TEMA AZUL CORPORATIVO
# ==========================================
def apply_blue_theme():
    pio.templates.default = "plotly_dark"
    st.markdown('''
    <style>
    .stApp { background-color: #001F3F; }
    h1, h2, h3 { color: #00A6FB !important; }
    .stMarkdown p, .stText { color: #BBE1FA !important; }
    [data-testid="metric-container"] .stMetricValue { color: #00A6FB !important; font-size: 2.5rem !important; font-weight: 700 !important; }
    [data-testid="metric-container"] .stMetricLabel { color: #D0E8FF !important; font-size: 1rem !important; }
    .stButton > button { background-color: #003B73 !important; color: white !important; border-radius: 6px; }
    .stButton > button:hover { background-color: #00A6FB !important; }
    </style>
    ''', unsafe_allow_html=True)

# ==========================================
# DATA LAYER: INGESTÃO DIA DE SORTE
# ==========================================
@st.cache_data
def carregar_dados_dia_de_sorte():
    """Gera dados simulados do Dia de Sorte (Substituir por API/CSV real)"""
    np.random.seed(42)
    n_concursos = 500
    sorteios = []
    for _ in range(n_concursos):
        dezenas = np.sort(np.random.choice(range(1, 32), 7, replace=False))
        sorteios.append(dezenas)
        
    df_sorte = pd.DataFrame(sorteios, columns=[f"Bola_{i+1}" for i in range(7)])
    df_sorte.index.name = "Concurso"
    df_sorte.index += 1
    return df_sorte

# ==========================================
# DOMAIN LAYER: MOTOR MATEMÁTICO
# ==========================================
@st.cache_data
def calcular_matriz_coocorrencia(df_sorte, universo=31):
    matriz = np.zeros((universo + 1, universo + 1), dtype=int)
    for dezenas in df_sorte.values:
        pares = list(combinations(dezenas, 2))
        for n1, n2 in pares:
            matriz[n1, n2] += 1
            matriz[n2, n1] += 1
    return matriz

@st.cache_data
def monte_carlo_dia_de_sorte(n_concursos, n_simulacoes=200, universo=31, dezenas_por_sorteio=7):
    matriz_esperada = np.zeros((universo + 1, universo + 1), dtype=float)
    for _ in range(n_simulacoes):
        matriz_sim = np.zeros((universo + 1, universo + 1), dtype=int)
        for _ in range(n_concursos):
            sorteio_sim = np.random.choice(range(1, universo + 1), dezenas_por_sorteio, replace=False)
            pares_sim = list(combinations(np.sort(sorteio_sim), 2))
            for n1, n2 in pares_sim:
                matriz_sim[n1, n2] += 1
                matriz_sim[n2, n1] += 1
        matriz_esperada += matriz_sim
    matriz_esperada /= n_simulacoes
    return matriz_esperada

@st.cache_data
def analisar_dia_de_sorte(df_sorte):
    n_concursos = len(df_sorte)
    matriz_real = calcular_matriz_coocorrencia(df_sorte, universo=31)
    matriz_esperada = monte_carlo_dia_de_sorte(n_concursos, n_simulacoes=100) # 100 para agilizar UI
    matriz_esperada_segura = np.where(matriz_esperada == 0, 1, matriz_esperada)
    matriz_forca = matriz_real / matriz_esperada_segura
    return matriz_real, matriz_esperada, matriz_forca

def preparar_df_pares(matriz_real, matriz_esperada, matriz_forca):
    pares = []
    for i in range(1, 32):
        for j in range(i + 1, 32):
            if matriz_real[i, j] > 0:
                pares.append({
                    "Par": f"{i:02d} - {j:02d}",
                    "Ocorrências (Real)": matriz_real[i, j],
                    "Esperado (Monte Carlo)": round(matriz_esperada[i, j], 2),
                    "Força (Real/Esperado)": round(matriz_forca[i, j], 2)
                })
    return pd.DataFrame(pares).sort_values(by="Força (Real/Esperado)", ascending=False)

# ==========================================
# UI LAYER: RENDERIZAÇÃO
# ==========================================
def render_dashboard(tema_nome, df_sorte, matriz_real, matriz_forca, df_pares):
    if tema_nome == "Tema Branco":
        apply_white_theme()
        cor_grafico = "#0066CC"
        template_grafico = "plotly_white"
    else:
        apply_blue_theme()
        cor_grafico = "#00A6FB"
        template_grafico = "plotly_dark"

    st.title("📊 Motor Analítico — Dia de Sorte")

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Concursos Analisados", f"{len(df_sorte):,}")
    col2.metric("Universo de Dezenas", "31")
    col3.metric("Pares Possíveis", "465")
    col4.metric("Maior Força Detectada", f"{df_pares['Força (Real/Esperado)'].max():.2f}x")

    tab1, tab2, tab3 = st.tabs(["Análise de Força (Pares)", "Heatmap de Coocorrência", "Base de Dados"])

    with tab1:
        st.subheader("Top 15 Pares com Maior Anomalia Estatística")
        top_pares = df_pares.head(15)
        fig_bar = px.bar(
            top_pares, x="Par", y="Força (Real/Esperado)",
            text="Força (Real/Esperado)", template=template_grafico,
            labels={"Força (Real/Esperado)": "Força (Multiplicador)"}
        )
        fig_bar.update_traces(marker_color=cor_grafico, textposition='outside')
        st.plotly_chart(fig_bar, use_container_width=True)
        
        st.dataframe(df_pares.head(50), use_container_width=True)

    with tab2:
        st.subheader("Matriz de Coocorrência (Frequência Real)")
        # Fatiar a matriz para ignorar o índice 0 (dezenas vão de 1 a 31)
        matriz_plot = matriz_real[1:, 1:]
        fig_heat = px.imshow(
            matriz_plot, 
            x=list(range(1, 32)), y=list(range(1, 32)),
            color_continuous_scale="Blues" if tema_nome == "Tema Branco" else "Teal",
            template=template_grafico
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    with tab3:
        st.subheader("Histórico de Sorteios (Amostra)")
        st.dataframe(df_sorte, use_container_width=True)

# ==========================================
# APP ROUTER
# ==========================================
def main():
    st.sidebar.title("⚙️ Configurações")
    escolha_tema = st.sidebar.selectbox("Tema visual", ["Tema Branco", "Tema Azul Corporativo"])
    
    with st.spinner("Carregando dados e rodando Monte Carlo..."):
        df_sorte = carregar_dados_dia_de_sorte()
        matriz_real, matriz_esperada, matriz_forca = analisar_dia_de_sorte(df_sorte)
        df_pares = preparar_df_pares(matriz_real, matriz_esperada, matriz_forca)
        
    render_dashboard(escolha_tema, df_sorte, matriz_real, matriz_forca, df_pares)

if __name__ == "__main__":
    st.set_page_config(page_title="Motor Dia de Sorte", layout="wide")
    main()
