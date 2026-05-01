import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
import json
from datetime import datetime
from itertools import combinations

st.set_page_config(page_title="MultiLoterias Analyzer", page_icon="🎰", layout="wide")

# Configurações das loterias
configs = {
    "Mega-Sena": {"lottery": "megasena", "max_num": 60, "bolas": 6, "max_concurso_start": 2800},
    "Quina": {"lottery": "quina", "max_num": 80, "bolas": 5, "max_concurso_start": 6600},
    "Lotofácil": {"lottery": "lotofacil", "max_num": 25, "bolas": 15, "max_concurso_start": 3200}
}

@st.cache_data(ttl=3600)
def fetch_results(lottery_key, max_concursos=500):
    config = next(c for c in configs.values() if c["lottery"] == lottery_key)
    base_url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{lottery_key}/"
    concurso = config["max_concurso_start"]
    results = []
    while len(results) < max_concursos and concurso > 0:
        url = base_url + str(concurso)
        try:
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data and data.get('listaDezenas') and len(data['listaDezenas']) == config['bolas']:
                    dezenas = sorted([int(d) for d in data['listaDezenas']])
                    dt_str = data.get('dataApuracao', '')
                    if dt_str:
                        dt = datetime.strptime(dt_str, '%d/%m/%Y')
                        results.append({'concurso': data.get('numero', concurso), 'data': dt, 'dezenas': dezenas})
            concurso -= 1
        except:
            concurso -= 1
    df = pd.DataFrame(results).sort_values('concurso', ascending=False).reset_index(drop=True)
    return df

def hot_cold(df, max_num, period=None):
    if period:
        df = df.head(period)
    freq = np.zeros(max_num)
    for row in df.itertuples():
        for num in row.dezenas:
            freq[num - 1] += 1
    hot_idx = np.argsort(freq)[-10:][::-1] + 1
    cold_idx = np.argsort(freq)[:10] + 1
    return list(hot_idx), list(cold_idx)

def coocorrencia(df, max_num, top_n=20):
    matrix = np.zeros((max_num, max_num))
    for row in df.itertuples():
        nums = row.dezenas
        for i in range(len(nums)):
            for j in range(i + 1, len(nums)):
                matrix[nums[i] - 1][nums[j] - 1] += 1
    pairs = []
    for i in range(max_num):
        for j in range(i + 1, max_num):
            count = matrix[i][j]
            if count > 0:
                pairs.append((i + 1, j + 1, count))
    pairs.sort(key=lambda x: x[2], reverse=True)
    return pairs[:top_n]

def get_sim_freq(df, n_sim, bolas, max_num):
    total_bolas = len(df) * bolas
    hist_freq = np.zeros(max_num)
    for row in df.itertuples():
        for num in row.dezenas:
            hist_freq[num - 1] += 1
    probs = hist_freq / total_bolas
    probs[probs == 0] = 1e-6
    probs = probs / probs.sum()
    sim_freq = np.zeros(max_num)
    for _ in range(n_sim):
        draw = np.random.choice(range(1, max_num + 1), size=bolas, replace=False, p=probs)
        for num in draw:
            sim_freq[num - 1] += 1
    return sim_freq

# Sidebar para configurações
st.sidebar.title("🎰 Configurações")
dark_mode = st.sidebar.toggle("Tema Dark", value=False)

if dark_mode:
    st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
    }
    .stMarkdown {
        color: white;
    }
    .stMetric > label {
        color: white;
    }
    .stMetric > div > div {
        color: white;
    }
    section[data-testid="stSidebar"] div[role="button"] {
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎰 MultiLoterias Analyzer")
st.markdown("*Análise completa de Mega-Sena, Quina e Lotofácil com dados oficiais da Caixa.*")

# Tabs
tabs = st.tabs(list(configs.keys()))

for name, tab in zip(configs.keys(), tabs):
    with tab:
        config = configs[name]
        st.markdown(f"### {name}")
        df = fetch_results(config['lottery'])
        if df.empty:
            st.error("❌ Não foi possível carregar os dados históricos. Tente novamente mais tarde.")
            continue

        # Último resultado
        col1, col2, col3 = st.columns(3)
        last = df.iloc[0]
        with col1:
            st.metric("Último Concurso", last.concurso)
        with col2:
            st.metric("Data", last.data.strftime("%d/%m/%Y"))
        with col3:
            st.metric("Dezenas", ', '.join(map(str, last.dezenas)))

        # Resultados recentes
        st.subheader("📊 Resultados Recentes")
        recent_df = df.head(20).copy()
        recent_df['data'] = recent_df['data'].dt.strftime("%d/%m/%Y")
        recent_df['dezenas'] = recent_df['dezenas'].apply(lambda x: ', '.join(map(str, x)))
        st.dataframe(recent_df[['concurso', 'data', 'dezenas']], use_container_width=True)

        # Hot / Cold
        period = st.slider("Período para Hot/Cold", 10, min(200, len(df)), 50)
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🔥 Números Quentes")
            hot = hot_cold(df, config['max_num'] + 1, period)[0]
            st.write(" | ".join(map(str, hot)))
        with col2:
            st.subheader("❄️ Números Frios")
            cold = hot_cold(df, config['max_num'] + 1, period)[1]
            st.write(" | ".join(map(str, cold)))

        # Coocorrência
        st.subheader("🔗 Coocorrências (Pares Mais Frequentes)")
        pairs = coocorrencia(df, config['max_num'] + 1)
        pair_df = pd.DataFrame(pairs, columns=['Num1', 'Num2', 'Frequência'])
        fig_pairs = px.bar(pair_df, x='Num1', y='Frequência', color='Num2', title="Top 20 Pares")
        st.plotly_chart(fig_pairs, use_container_width=True)

        # KPIs
        st.subheader("📈 KPIs")
        kpi_data = df.to_dict('records')
        sums = [sum(d['dezenas']) for d in kpi_data]
        avg_sum = np.mean(sums)
        min_sum, max_sum = min(sums), max(sums)
        even_counts = [sum(1 for n in d['dezenas'] if n % 2 == 0) for d in kpi_data]
        avg_even = np.mean(even_counts)
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        with kpi_col1:
            st.metric("Soma Média", f"{avg_sum:.1f}")
        with kpi_col2:
            st.metric("Soma Mín/Máx", f"{min_sum} / {max_sum}")
        with kpi_col3:
            st.metric("Pares Médios", f"{avg_even:.1f}")
        with kpi_col4:
            st.metric("Total Concursos", f"{len(df):,}")

        # Monte Carlo
        st.subheader("🎲 Simulação Monte Carlo")
        n_sim = st.slider("Número de Simulações", 1000, 50000, 10000, 1000)
        if st.button("Executar Simulação", key=f"mc_{name}"):
            with st.spinner('Simulando...'):
                sim_freq = get_sim_freq(df, n_sim, config['bolas'], config['max_num'])
            fig_sim = px.bar(x=range(1, config['max_num'] + 1), y=sim_freq, title="Frequência Projetada")
            st.plotly_chart(fig_sim, use_container_width=True)

        # Fechamentos
        st.subheader("⚙️ Gerador de Fechamentos")
        user_nums = st.multiselect("Escolha seus números", options=range(1, config['max_num'] + 1),
                                   max_selections=config['bolas'] + 5, key=f"nums_{name}")
        if len(user_nums) >= config['bolas']:
            bets = list(combinations(sorted(user_nums), config['bolas']))
            st.success(f"✅ Geradas **{len(bets)}** apostas!")
            custo = len(bets) * 5.00  # Aproximado R$5 por aposta
            st.info(f"💰 Custo estimado: **R$ {custo:.2f}**")
            if len(bets) <= 20:
                for i, bet in enumerate(bets, 1):
                    st.caption(f"Aposta {i}: {list(bet)}")
            else:
                st.write("**Primeiras 10 apostas:**")
                for bet in bets[:10]:
                    st.caption(list(bet))
        else:
            st.warning(f"⚠️ Escolha pelo menos {config['bolas']} números (recomendado {config['bolas'] + 2} para fechamento).")

st.markdown("---")
st.markdown("*Dados oficiais da Caixa Econômica Federal. Este app é para análise e entretenimento. Jogue com responsabilidade.*")
