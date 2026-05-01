import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
from collections import Counter
import itertools

st.set_page_config(
    page_title="MultiLoterias Enterprise",
    page_icon="🎀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Tema Dark
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
    }
    .css-1d391kg {
        background-color: #1f2937;
    }
    .stMetric > label {
        color: #e5e7eb;
    }
    .stMetric > div > div {
        color: #f9fafb;
    }
    [data-testid="stSidebar"] {
        background-color: #111827;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=86400)  # Cache por 24h
def fetch_megasena_data():
    try:
        latest_url = "https://loteriascaixa-api.herokuapp.com/api/mega-sena/latest"
        latest_resp = requests.get(latest_url, timeout=10)
        latest_pos = latest_resp.json()['concursoId']
        data_list = []
        for pos in range(latest_pos, max(1, latest_pos - 499), -1):
            url = f"https://loteriascaixa-api.herokuapp.com/api/mega-sena/{pos}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                d = resp.json()
                dezenas = [int(z.strip()) for z in d['dezenas'].split(',')]
                data_list.append({
                    'concurso': int(d['concursoId']),
                    'data': d['dataSorteio'],
                    'dezenas': dezenas
                })
        df = pd.DataFrame(data_list)
        return df.sort_values('concurso', ascending=False).reset_index(drop=True)
    except Exception as e:
        return pd.DataFrame(columns=['concurso', 'data', 'dezenas'])

# Carregar dados
if 'df' not in st.session_state:
    with st.spinner('Carregando dados oficiais da Caixa...'):
        st.session_state.df = fetch_megasena_data()

df = st.session_state.df
if df.empty:
    st.error("Falha ao carregar dados. Verifique conexão.")
    st.stop()

# Sidebar
st.sidebar.title("🎀 MultiLoterias")
st.sidebar.info(f"Dados: {len(df)} concursos Mega-Sena")
if st.sidebar.button("🔄 Atualizar Dados"):
    st.cache_data.clear()
    st.rerun()

top_n = st.sidebar.slider("Top N", 5, 20, 10)
sims_n = st.sidebar.slider("Simulações", 1000, 50000, 10000, 1000)

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "🔥 Hot/Cold", "🔗 Coocorrência", "🎲 Monte Carlo", "⚙️ Fechamentos"])

with tab1:
    st.header("📊 Dashboard Executivo")
    col1, col2, col3, col4, col5 = st.columns(5)
    all_nums = [n for row in df['dezenas'] for n in row]
    sums_list = [sum(row) for row in df['dezenas']]
    even_ratio = np.mean([sum(1 for n in row if n % 2 == 0) / 6 for row in df['dezenas']]) * 100

    with col1:
        st.metric("Concursos", len(df))
    with col2:
        st.metric("Soma Média", f"{np.mean(sums_list):.0f}")
    with col3:
        st.metric("% Pares", f"{even_ratio:.0f}%")
    with col4:
        counter = Counter(all_nums)
        st.metric("Hot Máx", counter.most_common(1)[0][1])
    with col5:
        st.metric("Cold Mín", counter.most_common()[-1][1])

    col_a, col_b = st.columns(2)
    with col_a:
        hot_df = pd.DataFrame(counter.most_common(15), columns=['Número', 'Freq'])
        fig = px.bar(hot_df.head(10), x='Número', y='Freq', title="Hot Numbers")
        st.plotly_chart(fig, theme="plotly_dark", use_container_width=True)
    with col_b:
        fig_c = px.bar(hot_df.tail(10), x='Número', y='Freq', title="Cold Numbers")
        st.plotly_chart(fig_c, theme="plotly_dark", use_container_width=True)

with tab2:
    st.header("🔥 Hot / Cold Numbers")
    counter = Counter(all_nums)
    hot = pd.DataFrame(counter.most_common(top_n), columns=['Número', 'Frequência'])
    cold = pd.DataFrame(counter.most_common()[-top_n:], columns=['Número', 'Frequência'])

    col1, col2 = st.columns(2)
    with col1:
        fig_h = px.bar(hot, x='Número', y='Frequência', title="Hot")
        st.plotly_chart(fig_h, theme="plotly_dark")
    with col2:
        fig_c = px.bar(cold, x='Número', y='Frequência', title="Cold")
        st.plotly_chart(fig_c, theme="plotly_dark")

with tab3:
    st.header("🔗 Análise de Coocorrência")
    pairs = [tuple(sorted(comb)) for row in df['dezenas'] for comb in itertools.combinations(row, 2)]
    pair_counter = Counter(pairs)
    top_pairs = pd.DataFrame(pair_counter.most_common(20), columns=['Par', 'Frequência'])
    top_pairs['Par'] = top_pairs['Par'].apply(lambda p: f"{p[0]:02d}-{p[1]:02d}")

    fig_p = px.bar(top_pairs, x='Par', y='Frequência', title="Top Pares")
    st.plotly_chart(fig_p, theme="plotly_dark")

with tab4:
    st.header("🎲 Simulação Monte Carlo")

    @st.cache_data()
    def monte_carlo(n_sims):
        draws = [sorted(np.random.choice(range(1, 61), 6, replace=False)) for _ in range(n_sims)]
        sim_nums = [n for draw in draws for n in draw]
        return Counter(sim_nums)

    sim_counter = monte_carlo(sims_n)
    sim_df = pd.DataFrame(sim_counter.most_common(20), columns=['Número', 'Frequência'])

    fig_sim = px.bar(sim_df, x='Número', y='Frequência', title=f"Simulações ({sims_n:,})")
    st.plotly_chart(fig_sim, theme="plotly_dark")

    col_sim, col_real = st.columns(2)
    with col_sim:
        st.subheader("Simulado")
        st.plotly_chart(fig_sim, theme="plotly_dark")
    with col_real:
        st.subheader("Real (Histórico)")
        real_top = pd.DataFrame(counter.most_common(10), columns=['Número', 'Frequência'])
        fig_real = px.bar(real_top, x='Número', y='Frequência')
        st.plotly_chart(fig_real, theme="plotly_dark")

with tab5:
    st.header("⚙️ Fechamentos Combinatórios")
    counter = Counter(all_nums)
    hot_list = [k for k, _ in counter.most_common(15)]
    selected_nums = st.multiselect("Selecione números", range(1,61), default=hot_list[:12])

    if st.button("Gerar Fechamentos") and len(selected_nums) >= 7:
        n_jogo = st.selectbox("Jogos de", [6,7], index=0)
        combos = list(itertools.combinations(sorted(selected_nums), n_jogo))
        st.success(f"Gerados {len(combos)} jogos!")

        for i, comb in enumerate(combos[:100]):
            st.caption(f"{i+1:3d}: {list(comb)}")

        if len(combos) > 100:
            st.info(f"... e mais {len(combos)-100} jogos.")
    else:
        st.warning("Escolha pelo menos 7 números para gerar fechamentos.")

st.markdown("---")
st.markdown("**MultiLoterias Enterprise** | Dados oficiais via API Caixa | Produção-ready 🎰")
