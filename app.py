import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter, defaultdict
import itertools
import json
from datetime import datetime, timedelta
import base64

# Configurações das loterias
LOTTERIES = {
    'Mega-Sena': {'nums': list(range(1, 61)), 'pick': 6, 'extra': None, 'repeats': False, 'name': 'mega'},
    'Quina': {'nums': list(range(1, 81)), 'pick': 5, 'extra': None, 'repeats': False, 'name': 'quina'},
    'Lotofácil': {'nums': list(range(1, 26)), 'pick': 15, 'extra': None, 'repeats': False, 'name': 'lotofacil'},
    'Dia de Sorte': {'nums': list(range(1, 32)), 'pick': 7, 'meses': list(range(1, 13)), 'extra': 'mes', 'repeats': False, 'name': 'diadesorte'},
    'Super Sete': {'nums': list(range(10)), 'pick': 7, 'extra': None, 'repeats': True, 'name': 'super_sete'}
}

@st.cache_data
def load_historical(lottery_name):
    config = LOTTERIES[lottery_name]
    data = []
    for i in range(200):  # 200 concursos simulados
        if config['repeats']:
            draw = np.random.choice(config['nums'], config['pick'], replace=True).tolist()
        else:
            draw = sorted(np.random.choice(config['nums'], config['pick'], replace=False))
        extra = None
        if config.get('meses'):
            extra = np.random.choice(config['meses'])
        date = (datetime.now() - timedelta(days=i*3)).strftime('%d/%m/%Y')
        data.append({
            'Concurso': i+1,
            'Data': date,
            'Números': ' | '.join(map(str, draw)),
            'Extra': extra if extra else ''
        })
    df = pd.DataFrame(data)
    return df

@st.cache_data
def analyze_hot_cold(df, config):
    all_numbers = []
    for nums_str in df['Números'].str.split(' | '):
        all_numbers.extend([int(n) for n in nums_str])
    freq = Counter(all_numbers)
    hot = pd.DataFrame(freq.most_common(10), columns=['Número', 'Frequência']).head(10)
    cold = pd.DataFrame(freq.most_common()[-10:], columns=['Número', 'Frequência']).tail(10)
    return hot, cold

def analyze_cooccurrence(df, config):
    pairs_count = defaultdict(int)
    for nums_str in df['Números'].str.split(' | '):
        nums = [int(n) for n in nums_str]
        for pair in itertools.combinations(sorted(nums), 2):
            pairs_count[pair] += 1
    top_pairs = sorted(pairs_count.items(), key=lambda x: x[1], reverse=True)[:20]
    pair_df = pd.DataFrame(top_pairs, columns=['Par', 'Frequência'])
    pair_df['Par'] = pair_df['Par'].apply(lambda p: f"{p[0]}-{p[1]}")
    return pair_df

def monte_carlo_sim(config, n_sims=10000):
    results = []
    for _ in range(n_sims):
        if config['repeats']:
            sim = np.random.choice(config['nums'], config['pick'], replace=True)
        else:
            sim = sorted(np.random.choice(config['nums'], config['pick'], replace=False))
        results.append(sim)
    flat_sims = [num for draw in results for num in draw]
    sim_freq = Counter(flat_sims)
    return pd.DataFrame(sim_freq.most_common(20), columns=['Número', 'Frequência Simulada'])

def generate_combinations(config, max_combos=50):
    base_set = sorted(np.random.choice(config['nums'], config['pick'] + 2, replace=False))
    combos = list(itertools.combinations(base_set, config['pick']))[:max_combos]
    return [list(c) for c in combos]

def kpis(df, config):
    all_sums = []
    for nums_str in df['Números'].str.split(' | '):
        nums = [int(n) for n in nums_str]
        all_sums.append(sum(nums))
    return {
        'Média Soma': np.mean(all_sums),
        'Mediana Soma': np.median(all_sums),
        'Soma Máx': np.max(all_sums),
        'Soma Mín': np.min(all_sums),
        'Concursos': len(df)
    }

def csv_download(df, filename):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}.csv">Baixar CSV</a>'
    return href

st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    .stMetric > label {
        color: #fafafa;
    }
    h1, h2, h3 {
        color: #fafafa;
    }
</style>
""", unsafe_allow_html=True)

st.set_page_config(
    page_title="MultiLoterias",
    page_icon="🎰",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🎰 MultiLoterias - Análises Avançadas")

# Sidebar
lottery = st.sidebar.selectbox("Selecione a Loteria:", list(LOTTERIES.keys()))
config = LOTTERIES[lottery]

# Load data
df_hist = load_historical(lottery)

# Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["Gerador", "Histórico", "Hot/Cold", "Coocorrência", "Monte Carlo", "Fechamentos", "KPIs"])

with tab1:
    st.header("Gerador de Jogos")
    if st.button("Gerar Jogo"):
        if config['repeats']:
            jogo = np.random.choice(config['nums'], config['pick'], replace=True).tolist()
        else:
            jogo = sorted(np.random.choice(config['nums'], config['pick'], replace=False))
        st.success(f"Jogo: {' | '.join(map(str, jogo))}")

with tab2:
    st.header("Histórico de Sorteios")
    st.dataframe(df_hist, use_container_width=True)

with tab3:
    st.header("Hot / Cold")
    hot, cold = analyze_hot_cold(df_hist, config)
    st.subheader("🔥 Hot")
    st.dataframe(hot)
    st.subheader("❄️ Cold")
    st.dataframe(cold)

with tab4:
    st.header("Coocorrência")
    cooc = analyze_cooccurrence(df_hist, config)
    st.dataframe(cooc)
    fig = px.bar(cooc, x="Par", y="Frequência")
    st.plotly_chart(fig)

with tab5:
    st.header("Monte Carlo")
    sims = monte_carlo_sim(config)
    st.dataframe(sims)
    fig = px.bar(sims, x="Número", y="Frequência Simulada")
    st.plotly_chart(fig)

with tab6:
    st.header("Fechamentos")
    num_combos = st.slider("Combos", 5, 50, 10)
    combos = generate_combinations(config, max_combos=num_combos)
    for i, c in enumerate(combos):
        st.write(f"{i+1} - {' | '.join(map(str, c))}")

with tab7:
    st.header("KPIs")
    k = kpis(df_hist, config)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Concursos", k['Concursos'])
    col2.metric("Média Soma", f"{k['Média Soma']:.2f}")
    col3.metric("Mediana Soma", f"{k['Mediana Soma']:.2f}")
    col4.metric("Range Soma", f"{k['Soma Mín']} - {k['Soma Máx']}")
