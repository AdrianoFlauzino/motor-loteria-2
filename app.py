## requirements.txt
streamlit>=1.28.0
pandas>=2.0.0
numpy>=1.24.0
plotly>=5.15.0
requests>=2.31.0

## app_enterprise.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta

@st.cache_data(ttl=3600)
def fetch_lottery_data(lottery, concurso=None):
    base_url = "https://servicebus2.caixa.gov.br/portaldeloterias/api"
    if concurso:
        url = f"{base_url}/{lottery}/{concurso}"
    else:
        url = f"{base_url}/{lottery}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Erro ao buscar dados de {lottery}: {str(e)}")
        return None

@st.cache_data(ttl=86400)
def get_lottery_history(lottery, n_draws=20):
    latest = fetch_lottery_data(lottery)
    if not latest:
        return []
    last_concurso = latest.get('numero', 0)
    history = []
    start_concurso = max(1, last_concurso - n_draws + 1)
    for num in range(start_concurso, last_concurso + 1):
        data = fetch_lottery_data(lottery, num)
        if data:
            history.append(data)
    return history[::-1]  # Mais recente primeiro

@st.cache_data
def parse_numbers(data):
    if not data:
        return []
    dezenas_str = data.get('listaDezenas', '')
    return [int(d.strip()) for d in dezenas_str.split(',') if d.strip().isdigit()]

def create_freq_df(history, lottery):
    all_numbers = []
    for draw in history:
        nums = parse_numbers(draw)
        all_numbers.extend(nums)
    freq = pd.Series(all_numbers).value_counts().sort_index().reset_index()
    freq.columns = ['numero', 'frequencia']
    return freq

def get_max_ball(lottery):
    max_balls = {'megasena': 60, 'quina': 80, 'lotofacil': 25, 'lotomania': 100,
                 'duplasena': 50, 'timemania': 80, 'diadesorte': 31}
    return max_balls.get(lottery, 100)

st.set_page_config(
    page_title="MultiLoterias Enterprise",
    page_icon="🎰",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🎰 MultiLoterias Enterprise - Dashboards Premium")

lotteries = ['megasena', 'quina', 'lotofacil', 'lotomania', 'duplasena', 'timemania', 'diadesorte']

# Sidebar
st.sidebar.header("Configurações")
selected_lottery = st.sidebar.selectbox("Selecione a Loteria", lotteries, index=0)
n_draws = st.sidebar.slider("Nº de Concursos Históricos", 5, 50, 20)
refresh = st.sidebar.button("🔄 Atualizar Dados")
if refresh:
    st.cache_data.clear()
    st.rerun()

# Tabs
if 'tab1' not in st.session_state:
    st.session_state.tab1, st.session_state.tab2 = st.tabs(["📊 Visão Geral", f"{selected_lottery.upper()} - Dashboard Executivo"])
else:
    st.session_state.tab1, st.session_state.tab2 = st.tabs(["📊 Visão Geral", f"{selected_lottery.upper()} - Dashboard Executivo"])

with st.session_state.tab1:
    st.header("Visão Geral - Últimos Resultados")
    cols = st.columns(len(lotteries))
    for i, lot in enumerate(lotteries):
        with cols[i]:
            latest = fetch_lottery_data(lot)
            if latest:
                nums = parse_numbers(latest)
                st.metric(f"{lot.title()}", f"Nº {latest.get('numero', 'N/A')}", delta=latest.get('dataApuracao', ''))
                st.caption(', '.join(map(str, nums[:6])))
                estimativa = latest.get('estimativaProximoConcurso', 'N/A')
                if estimativa != 'N/A':
                    st.caption(f"Próximo: R$ {estimativa:,.0f}")

with st.session_state.tab2:
    st.header(f"{selected_lottery.upper()} - Análises Avançadas")
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    history = get_lottery_history(selected_lottery, n_draws)
    if history:
        latest = history[0]
        nums = parse_numbers(latest)
        with col1:
            st.metric("Último Concurso", latest['numero'])
        with col2:
            st.metric("Data", latest['dataApuracao'])
        with col3:
            st.metric("Números", ', '.join(map(str, nums)))
        with col4:
            estimativa = latest.get('estimativaProximoConcurso', 0)
            st.metric("Próximo Prêmio", f"R$ {estimativa:,.0f}" if estimativa else "N/A")
        
        # Tabela Histórico
        st.subheader("📋 Histórico Recente")
        df_hist = pd.DataFrame([{
            'Concurso': d['numero'],
            'Data': d['dataApuracao'],
            'Dezenas': ', '.join(map(str, parse_numbers(d))),
            'Arrecadacao': d.get('arrecadacaoTotal', 'N/A'),
            'Premiacao': d.get('valorPremio', [{}])[0].get('valorPremio', 'N/A') if d.get('valorPremio') else 'N/A'
        } for d in history[:10]])
        st.dataframe(df_hist, use_container_width=True, height=300)
        
        # CSV Download
        csv = df_hist.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", csv, f"{selected_lottery}_historico.csv", "text/csv")
        
        # Gráficos
        st.subheader("📈 Visualizações Executivas")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            # Frequência de Números
            freq_df = create_freq_df(history, selected_lottery)
            max_ball = get_max_ball(selected_lottery)
            fig_freq = px.bar(freq_df, x='numero', y='frequencia', title="Frequência de Números",
                              range_x=[1, max_ball])
            fig_freq.update_layout(showlegend=False)
            st.plotly_chart(fig_freq, use_container_width=True)
            
            # Números Mais/Menos Frequentes
            hot = freq_df.nlargest(5, 'frequencia')
            cold = freq_df.nsmallest(5, 'frequencia')
            st.subheader("🔥 Números Quentes / ❄️ Frios")
            col_h, col_c = st.columns(2)
            with col_h:
                st.metric("Quentes", hot['numero'].tolist())
            with col_c:
                st.metric("Frios", cold['numero'].tolist())
        
        with col_b:
            # Soma das Dezenas ao Longo do Tempo
            sums = [sum(parse_numbers(d)) for d in history]
            fig_sum = px.line(x=range(len(sums)), y=sums, title="Evolução da Soma das Dezenas")
            st.plotly_chart(fig_sum, use_container_width=True)
            
            # Distribuição por Paridade
            all_nums = [n for d in history for n in parse_numbers(d)]
            parity = ['Par' if n % 2 == 0 else 'Ímpar' for n in all_nums]
            fig_par = px.pie(values=parity, names=parity, title="Distribuição Par/Ímpar")
            st.plotly_chart(fig_par, use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.caption("App Enterprise | Dados da Caixa Econômica Federal")
