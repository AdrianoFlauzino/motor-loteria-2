import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.io as pio

# 
# TEMA BRANCO EXECUTIVO
# 

def apply_white_theme():
    pio.templates.default = "plotly_white"
    st.markdown('''
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
    * {
        font-family: 'Inter', 'Segoe UI', sans-serif !important;
    }
    .stApp {
        background-color: #FFFFFF;
    }
    .main .block-container {
        padding-top: 3rem;
        padding-bottom: 3rem;
        padding-left: 3rem;
        padding-right: 3rem;
        max-width: 1400px;
        margin: auto;
    }
    [data-testid="stSidebar"] > div:first-child {
        background-color: #FFFFFF;
    }
    h1, h2, h3, h4 {
        color: #0A2342 !important;
    }
    .stMarkdown p, .stText {
        color: #333333;
    }
    [data-testid="metric-container"] .stMetricValue {
        font-size: 3rem !important;
        font-weight: 700 !important;
        color: #0066CC !important;
    }
    [data-testid="metric-container"] .stMetricLabel {
        font-size: 1.0rem !important;
        color: #333333 !important;
    }
    hr {
        border: none;
        height: 1px;
        background-color: #E0E0E0;
        margin: 2.5rem 0;
    }
    .stButton > button {
        background-color: #0066CC;
        color: white;
        border-radius: 6px;
        font-weight: 500;
    }
    .stButton > button:hover {
        background-color: #0052A3;
    }
    </style>
    ''', unsafe_allow_html=True)

# 
# TEMA AZUL CORPORATIVO
# 

def apply_blue_theme():
    pio.templates.default = "plotly_dark"
    st.markdown('''
    <style>
    .stApp {
        background-color: #001F3F;
    }
    h1, h2 {
        color: #00A6FB !important;
    }
    .stMarkdown p {
        color: #BBE1FA !important;
    }
    [data-testid="metric-container"] .stMetricValue {
        color: #00A6FB !important;
        font-size: 3rem !important;
        font-weight: 700 !important;
    }
    [data-testid="metric-container"] .stMetricLabel {
        color: #D0E8FF !important;
    }
    .stButton > button {
        background-color: #003B73 !important;
        color: white !important;
        border-radius: 6px;
    }
    .stButton > button:hover {
        background-color: #00A6FB !important;
    }
    </style>
    ''', unsafe_allow_html=True)

# 
# DATA LAYER
# 

def load_sample_data():
    dates = pd.date_range("2024-01-01", periods=100)
    df = pd.DataFrame({
        "data": dates,
        "receita": np.random.randn(100).cumsum() + 1000,
        "vendas": np.random.randint(50, 200, 100),
        "clientes": np.random.randint(100, 500, 100),
        "regiao": np.random.choice(
            ["Sul", "Sudeste", "Nordeste", "Norte", "Centro-Oeste"], 100
        )
    })
    return df

# 
# UI LAYER — BRANCO
# 

def render_ui_white(package):
    apply_white_theme()
    st.title("📊 Dashboard Executivo — Tema Branco")

    df = load_sample_data()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Receita Total", f"R$ {df['receita'].sum():,.0f}")
    col2.metric("Vendas", f"{df['vendas'].sum():,}")
    col3.metric("Clientes", f"{df['clientes'].sum():,}")
    col4.metric("Média Receita", f"R$ {df['receita'].mean():,.0f}")

    st.sidebar.header("Filtros")
    regioes = st.sidebar.multiselect(
        "Regiões", df["regiao"].unique(), default=df["regiao"].unique()
    )
    df = df[df["regiao"].isin(regioes)]

    tab1, tab2, tab3 = st.tabs(["Gráficos", "Tabela", "Detalhes"])

    with tab1:
        fig = px.line(df, x="data", y="receita", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

        fig2 = px.bar(
            df.groupby("regiao")["vendas"].sum().reset_index(),
            x="regiao", y="vendas",
            template="plotly_white"
        )
        st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        st.dataframe(df, use_container_width=True)

    with tab3:
        st.json({"package": package})

# 
# UI LAYER — AZUL
# 

def render_ui_blue(package):
    apply_blue_theme()
    st.title("📊 Dashboard Executivo — Tema Azul Corporativo")

    df = load_sample_data()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Receita Total", f"R$ {df['receita'].sum():,.0f}")
    col2.metric("Vendas", f"{df['vendas'].sum():,}")
    col3.metric("Clientes", f"{df['clientes'].sum():,}")
    col4.metric("Média Receita", f"R$ {df['receita'].mean():,.0f}")

    st.sidebar.header("Filtros")
    regioes = st.sidebar.multiselect(
        "Regiões", df["regiao"].unique(), default=df["regiao"].unique()
    )
    df = df[df["regiao"].isin(regioes)]

    tab1, tab2, tab3 = st.tabs(["Gráficos", "Tabela", "Detalhes"])

    with tab1:
        fig = px.line(df, x="data", y="receita")
        fig.update_layout(colorway=["#00A6FB"])
        st.plotly_chart(fig, use_container_width=True)

        fig2 = px.bar(
            df.groupby("regiao")["vendas"].sum().reset_index(),
            x="regiao", y="vendas"
        )
        fig2.update_layout(colorway=["#003B73", "#00A6FB"])
        st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        st.dataframe(df, use_container_width=True)

    with tab3:
        st.json({"package": package})

# 
# UI ROUTER
# 

def route_ui(package):
    escolha = st.sidebar.selectbox(
        "Tema visual",
        ["Tema Branco", "Tema Azul Corporativo"]
    )
    if escolha == "Tema Branco":
        render_ui_white(package)
    else:
        render_ui_blue(package)

# 
# APP
# 

def load_and_analyze():
    return {"status": "ok", "info": "package carregado"}

package = load_and_analyze()
route_ui(package)