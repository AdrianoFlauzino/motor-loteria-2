import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from itertools import combinations
import math
import io

st.set_page_config(
    page_title="Dark Trader PRO MAX",
    page_icon="🖤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Tema Dark
st.markdown """
    <style>
    .stApp {
        background-color: #0e1117;
    }
    .stMetric > label {
        color: white;
    }
    .stMetric > div > div {
        color: white;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    </style>
""", unsafe_allow_html=True

st.title("🖤 Dark Trader - Análise Loterias PRO MAX")

# Sidebar
st.sidebar.header("⚙️ Configurações")
lottery = st.sidebar.selectbox("Loteria", ["Mega-Sena"])
MIN_NUM, MAX_NUM, N_NUMS = 1, 60, 6

n_historical = st.sidebar.slider("Nº Sorteios Históricos", 100, 2000, 500)
n_montecarlo = st.sidebar.slider("Simulações Monte Carlo", 1000, 100000, 10000)

@st.cache_data
def generate_historical_data(n_draws, min_num, max_num, n_nums):
    data = np.random.choice(range(min_num, max_num+1), size=(n_draws, n_nums), replace=True)
    data = np.sort(data, axis=1)
    return pd.DataFrame(data, columns=[f'Bola_{i+1}' for i in range(n_nums)])

historical_df = generate_historical_data(n_historical, MIN_NUM, MAX_NUM, N_NUMS)

# Computações principais
def hot_cold_stats(df, min_num, max_num):
    freq = np.bincount(df.values.flatten() - 1, minlength=max_num)
    hot_idx = np.argsort(freq)[-10:][::-1] + 1
    cold_idx = np.argsort(freq)[:10][::-1] + 1
    return hot_idx, cold_idx, freq

hot, cold, hist_freq = hot_cold_stats(historical_df, MIN_NUM, MAX_NUM)

def cooccurrence_matrix(df, max_num):
    cooc = np.zeros((max_num, max_num))
    for _, row in df.iterrows():
        nums = row.values.astype(int)
        for i, j in combinations(nums, 2):
            cooc[i-1, j-1] += 1
            cooc[j-1, i-1] += 1
    return cooc

cooc_hist = cooccurrence_matrix(historical_df, MAX_NUM)

# Monte Carlo
mc_sim = np.random.choice(range(MIN_NUM, MAX_NUM+1), size=(n_montecarlo, N_NUMS), replace=True)
mc_sim = np.sort(mc_sim, axis=1)
mc_freq = np.bincount(mc_sim.flatten() - 1, minlength=MAX_NUM)

total_combos = math.comb(MAX_NUM, N_NUMS)

# Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["📊 Estatísticas", "🎲 Monte Carlo", "💰 Financeiro", "🔒 Fechamentos", "📈 KPIs", "🏛️ Painel Executivo", "📋 Excel"])

with tab1:
    st.header("Hot/Cold & Coocorrência")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔥 Top 10 Hot")
        hot_df = pd.DataFrame({"Número": hot, "Frequência": hist_freq[hot-1]})
        st.dataframe(hot_df)
        st.subheader("❄️ Top 10 Cold")
        cold_df = pd.DataFrame({"Número": cold, "Frequência": hist_freq[cold-1]})
        st.dataframe(cold_df)
    with col2:
        st.subheader("Matriz de Coocorrência (Top 20)")
        fig_heat = px.imshow(cooc_hist[:20, :20], color_continuous_scale='Viridis', title="Coocorrência")
        st.plotly_chart(fig_heat, use_container_width=True)

with tab2:
    st.header("🎲 Simulação Monte Carlo Vetorizada")
    fig_mc = px.bar(x=range(1, MAX_NUM+1), y=mc_freq, title=f"Frequência em {n_montecarlo:,} Simulações")
    st.plotly_chart(fig_mc, use_container_width=True)
    
    st.subheader("Probabilidade de Combo Específico")
    target_input = st.text_input("Digite 6 números (separados por vírgula):", "5,10,15,20,25,30")
    try:
        target_list = [int(x.strip()) for x in target_input.split(',') if x.strip()]
        if len(target_list) == N_NUMS:
            target = np.sort(np.array(target_list))
            if np.all((target >= MIN_NUM) & (target <= MAX_NUM)):
                matches = np.sum(np.all(mc_sim == target[None, :], axis=1))
                prob = matches / n_montecarlo
                st.success(f"Combo {list(target)}: **{prob:.2%}** ({matches:,}/{n_montecarlo:,})")
            else:
                st.error("Números fora do intervalo 1-60")
        else:
            st.error("Exatamente 6 números")
    except ValueError:
        st.error("Números inválidos")

with tab3:
    st.header("💰 Módulo Financeiro")
    col1, col2, col3 = st.columns(3)
    cost = st.number_input("Custo por aposta (R$)", 5.0, key="cost")
    prize = st.number_input("Prêmio estimado Sena (R$)", 50000000.0, key="prize")
    
    prob_win = 1.0 / total_combos
    ev = prize * prob_win - cost
    roi = (ev / cost) * 100
    payoff = prize / cost
    
    col1.metric("EV", f"R$ {ev:,.2f}")
    col2.metric("ROI", f"{roi:.4f}%")
    col3.metric("Payoff", f"{payoff:,.0f}x")
    
    st.info(f"Probabilidade Sena: 1 em {total_combos:,}")

with tab4:
    st.header("🔒 Fechamentos Combinatórios")
    nums_str = st.text_area("Números base (vírgula separada):", "1,2,3,4,5,6,7,8,9,10,11,12")
    try:
        base_nums = sorted(set(int(x.strip()) for x in nums_str.split(',') if x.strip()))
        k = st.slider("Tamanho das combinações", 3, min(N_NUMS, len(base_nums)), N_NUMS)
        combs = list(combinations(base_nums, k))
        st.info(f"{len(combs):,} combinações geradas de {len(base_nums)} números.")
        if len(combs) <= 500:
            combs_df = pd.DataFrame(combs, columns=[f"Bola{i+1}" for i in range(k)])
            st.dataframe(combs_df)
        else:
            st.dataframe(pd.DataFrame(list(combs[:100])))
            st.info("Amostra de 100 mostrada.")
    except:
        st.error("Erro nos números.")

with tab5:
    st.header("📈 KPIs Executivos")
    sums = historical_df.sum(axis=1)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Sorteios", f"{len(historical_df):,}")
    col2.metric("Soma Média", f"{sums.mean():.1f}")
    col3.metric("Soma DP", f"{sums.std():.1f}")
    col4.metric("Hot Máx", f"{hist_freq.max()}")
    
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Simulações", f"{n_montecarlo:,}")
    col6.metric("MC Média", f"{mc_freq.mean():.1f}")
    col7.metric("Combinações Totais", f"{total_combos:,}")
    col8.metric("EV Ref", f"R$ {(50000000 * (1/total_combos) - 5):,.2f}")

with tab6:
    st.header("🏛️ Painel Executivo Dark Trader")
    fig = make_subplots(rows=2, cols=2,
                        subplot_titles=('Hot Numbers', 'Cold Numbers', 'Freq Histórica', 'Freq Monte Carlo'),
                        specs=[[{}, {}], [{'secondary_y': False}, {'secondary_y': False}]])
    
    fig.add_trace(go.Bar(x=hot, y=hist_freq[hot-1], name='Hot', marker_color='red'), row=1, col=1)
    fig.add_trace(go.Bar(x=cold, y=hist_freq[cold-1], name='Cold', marker_color='blue'), row=1, col=2)
    fig.add_trace(go.Scatter(x=range(1,MAX_NUM+1), y=hist_freq, mode='lines', name='Hist', line=dict(color='orange')), row=2, col=1)
    fig.add_trace(go.Scatter(x=range(1,MAX_NUM+1), y=mc_freq, mode='lines', name='MC', line=dict(color='green')), row=2, col=2)
    
    fig.update_layout(height=700, showlegend=True, template='plotly_dark', title_text="Dark Trader Overview")
    st.plotly_chart(fig, use_container_width=True)

with tab7:
    st.header("📋 Exportar para Excel")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        historical_df.to_excel(writer, sheet_name='Historico', index=False)
        freq_df = pd.DataFrame({
            'Numero': range(1, MAX_NUM+1),
            'Freq_Hist': hist_freq,
            'Freq_MC': mc_freq
        })
        freq_df.to_excel(writer, sheet_name='Frequencias', index=False)
        hc_df = pd.DataFrame({
            'Hot': hot,
            'Freq_Hot': hist_freq[hot-1],
            'Cold': cold,
            'Freq_Cold': hist_freq[cold-1]
        })
        hc_df.to_excel(writer, sheet_name='HotCold', index=False)
    output.seek(0)
    st.download_button(
        label="📥 Baixar Relatório Completo.xlsx",
        data=output.getvalue(),
        file_name="dark_trader_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.sidebar.markdown("---")
st.sidebar.markdown("🖤 **Dark Trader PRO MAX** - Pronto para Streamlit Cloud")
