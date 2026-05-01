#=== app.py ===
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import itertools
import math
from io import BytesIO

st.set_page_config(page_title="Loterias PRO MAX", page_icon="🎰", layout="wide")

LOTERIAS = {
    'Mega-Sena': {'numeros': 60, 'dezenas': 6, 'preco': 5.0, 'tiers': [6,5,4], 'default_prizes': {6: 10000000.0, 5: 50000.0, 4: 1000.0}},
    'Quina': {'numeros': 80, 'dezenas': 5, 'preco': 3.0, 'tiers': [5,4,3,2], 'default_prizes': {5: 1000000.0, 4: 10000.0, 3: 1000.0, 2: 10.0}},
    'Lotofácil': {'numeros': 25, 'dezenas': 15, 'preco': 3.0, 'tiers': [15,14,13,12,11], 'default_prizes': {15: 2000000.0, 14: 20000.0, 13: 3000.0, 12: 30.0, 11: 6.0}},
    'Dia de Sorte': {'numeros': 31, 'dezenas': 7, 'preco': 2.5, 'tiers': [7,6,5,4], 'default_prizes': {7: 500000.0, 6: 10000.0, 5: 1000.0, 4: 10.0}},
    '+Milionária': {'numeros': 50, 'dezenas': 6, 'preco': 6.0, 'tiers': [6,5,4], 'default_prizes': {6: 100000000.0, 5: 1000000.0, 4: 10000.0}}
}

def compute_stats(historical, config):
    all_nums = np.concatenate(historical)
    freq = np.bincount(all_nums, minlength=config['numeros'] + 1)[1:]
    hot = np.argsort(-freq)[:15] + 1
    cold = np.argsort(freq)[:15] + 1
    cooc = np.zeros((config['numeros'], config['numeros']))
    for draw in historical:
        for i, j in itertools.combinations(draw, 2):
            cooc[i-1, j-1] += 1
            cooc[j-1, i-1] += 1
    return freq, hot, cold, cooc

def get_pool(strategy, hot, cold, freq, config):
    if strategy == "Aleatória":
        return list(range(1, config['numeros'] + 1))
    elif strategy == "Hot Numbers":
        n_pool = max(config['dezenas'] * 3, config['dezenas'] + 10)
        pool_idx = np.argsort(-freq)[:n_pool]
        return (pool_idx + 1).tolist()
    elif strategy == "Cold Numbers":
        n_pool = max(config['dezenas'] * 3, config['dezenas'] + 10)
        pool_idx = np.argsort(freq)[:n_pool]
        return (pool_idx + 1).tolist()
    elif strategy == "Balanceada":
        n_pool = max(config['dezenas'] * 3, config['dezenas'] + 10)
        half = n_pool // 2
        hot_pool = np.argsort(-freq)[:half]
        cold_pool = np.argsort(freq)[:half]
        pool_idx = np.unique(np.concatenate([hot_pool, cold_pool]))
        return sorted((pool_idx + 1).tolist())

def generate_bets(n_bets, pool, dezenas):
    bets = []
    for _ in range(n_bets):
        bet = np.random.choice(pool, dezenas, replace=False)
        bets.append(sorted(bet))
    return np.array(bets)

@st.cache_data
def load_historical(_loteria: str, _n_hist: int) -> np.ndarray:
    config = LOTERIAS[_loteria]
    historical_list = [sorted(np.random.choice(np.arange(1, config['numeros'] + 1), config['dezenas'], replace=False)) for _ in range(_n_hist)]
    return np.array(historical_list)

@st.cache_data
def gen_draws(_loteria: str, _n_sims: int) -> np.ndarray:
    config = LOTERIAS[_loteria]
    draws_list = [sorted(np.random.choice(np.arange(1, config['numeros'] + 1), config['dezenas'], replace=False)) for _ in range(_n_sims)]
    return np.array(draws_list)

def make_excel(config, historical, freq, hot, cold, cooc):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pd.DataFrame(historical).to_excel(writer, sheet_name='Sorteios_Historicos', index=False)
        df_freq = pd.DataFrame({'Numero': range(1, len(freq)+1), 'Frequencia': freq, 'Porcentagem': freq / len(historical) * 100})
        df_freq.to_excel(writer, sheet_name='Frequencia', index=False)
        pd.DataFrame({'Hot': hot}).to_excel(writer, sheet_name='Hot_Numbers', index=False)
        pd.DataFrame({'Cold': cold}).to_excel(writer, sheet_name='Cold_Numbers', index=False)
        df_cooc = pd.DataFrame(cooc, columns=[f'Num_{i}' for i in range(1, config['numeros']+1)], index=[f'Num_{i}' for i in range(1, config['numeros']+1)])
        df_cooc.to_excel(writer, sheet_name='Coocorrencia')
    output.seek(0)
    return output.getvalue()

st.title("🎰 Simulador Loterias PRO MAX - Monte Carlo Vetorizado")
st.markdown("---")

with st.sidebar:
    st.header("⚙️ Configurações")
    loteria = st.selectbox("Selecione a Loteria", options=list(LOTERIAS.keys()))
    config = LOTERIAS[loteria]
    n_hist = st.slider("Tamanho do histórico simulado", 100, 5000, 1000)
    st.info(f"**{loteria}:** 1-{config['numeros']}\nDezenas: {config['dezenas']}\nPreço: R$ {config['preco']:.2f}")

historical = load_historical(loteria, n_hist)
freq, hot, cold, cooc = compute_stats(historical, config)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Estatísticas", "🎲 Simulador Monte Carlo", "🔢 Fechamentos", "📈 KPIs Executivo", "📥 Download Excel"])

with tab1:
    col_freq, col_list = st.columns([2,1])
    with col_freq:
        st.subheader("Frequência dos Números")
        df_freq_plot = pd.DataFrame({'Numero': range(1, len(freq)+1), 'Frequencia': freq})
        fig_freq = px.bar(df_freq_plot, x='Numero', y='Frequencia', title="Frequência Absoluta")
        st.plotly_chart(fig_freq, use_container_width=True)
    with col_list:
        st.subheader("Hot / Cold")
        st.markdown(f"**Hot Top 10:** {hot[:10]}")
        st.markdown(f"**Cold Top 10:** {cold[:10]}")
    st.subheader("Matriz de Coocorrência")
    fig_cooc = px.imshow(cooc, color_continuous_scale='YlOrRd', title="Coocorrências de Pares", labels={'color': 'Contagem'})
    st.plotly_chart(fig_cooc, use_container_width=True)

with tab2:
    st.subheader("Simulador Monte Carlo Vetorizado")
    col1, col2 = st.columns(2)
    with col1:
        strategy = st.selectbox("Estratégia", ["Aleatória", "Hot Numbers", "Cold Numbers", "Balanceada"])
        n_bets = st.slider("Apostas por sorteio", 1, 200, 10)
        n_sims = st.slider("Simulações (sorteios)", 1000, 1000000, 100000, step=10000)
    with col2:
        st.info("⚡ Otimizado com matrizes booleanas (bet_inds @ draw_inds.T)")
    prize_values = []
    for tier in config['tiers']:
        default_p = config['default_prizes'].get(tier, 0.0)
        p = st.number_input(f"Prêmio {tier} acertos", value=float(default_p), min_value=0.0, step=100.0)
        prize_values.append(p)
    if st.button("🚀 Executar Simulação", type="primary"):
        with st.spinner(f"Simulando {n_sims:,} sorteios..."):
            draws = gen_draws(loteria, n_sims)
            pool = get_pool(strategy, hot, cold, freq, config)
            if len(pool) < config['dezenas']:
                st.error(f"❌ Pool pequeno: {len(pool)} < {config['dezenas']}")
                st.stop()
            bets = generate_bets(n_bets, pool, config['dezenas'])
            df_bets = pd.DataFrame(bets)
            st.subheader("Apostas Geradas")
            st.dataframe(df_bets, use_container_width=True)
            bet_inds = np.zeros((n_bets, config['numeros']), dtype=bool)
            for i, bet in enumerate(bets):
                bet_inds[i, bet - 1] = True
            draw_inds = np.zeros((n_sims, config['numeros']), dtype=bool)
            for i, draw in enumerate(draws):
                draw_inds[i, draw - 1] = True
            matches = bet_inds @ draw_inds.T
            prizes_dict = dict(zip(config['tiers'], prize_values))
            total_hits = {k: int(np.sum(matches == k)) for k in range(config['dezenas'] + 1)}
            total_winnings = sum(prizes_dict.get(k, 0.0) * total_hits[k] for k in range(config['dezenas'] + 1))
            total_cost = n_bets * n_sims * config['preco']
            roi_pct = ((total_winnings - total_cost) / total_cost * 100) if total_cost > 0 else 0.0
            ev_per_bet = total_winnings / (n_bets * n_sims) - config['preco']
            payoff_ratio = total_winnings / total_cost if total_cost > 0 else 0.0
            col_roi, col_ev, col_pay, col_hits = st.columns(4)
            col_roi.metric("ROI (%)", f"{roi_pct:.4f}%")
            col_ev.metric("EV / Aposta (R$)", f"{ev_per_bet:.4f}")
            col_pay.metric("Payoff", f"{payoff_ratio:.4f}")
            col_hits.metric("Total Acertos", f"{int(np.sum(matches)):,}")
            df_hit_dist = pd.DataFrame([
                {'Acertos': k, 'Qtd': total_hits[k], '%': total_hits[k] / (n_bets * n_sims) * 100}
                for k in range(config['dezenas'] + 1)
            ])
            st.subheader("Distribuição de Acertos")
            st.dataframe(df_hit_dist)
            fig_dist = px.bar(df_hit_dist, x='Acertos', y='%', title="% Acertos por Nível")
            st.plotly_chart(fig_dist, use_container_width=True)
            high_hits_per_bet = np.sum(matches >= min(config['tiers'] or [0]), axis=1)
            best_idx = np.argmax(high_hits_per_bet)
            st.success(f"🏆 **Melhor Aposta:** **{list(bets[best_idx])}** \n( {int(high_hits_per_bet[best_idx]):,} prêmios altos )")

with tab3:
    st.subheader("Fechamentos Matemáticos Combinatórios")
    selected_nums = st.multiselect("Números base", options=list(range(1, config['numeros'] + 1)), max_selections=20)
    if selected_nums:
        selected_nums = sorted(selected_nums)
        total_combs = math.comb(len(selected_nums), config['dezenas'])
        st.info(f"Total combinações: **{total_combs:,}**")
        if total_combs <= 20000:
            fechamento = list(itertools.combinations(selected_nums, config['dezenas']))
            df_fech = pd.DataFrame(fechamento)
            st.dataframe(df_fech, use_container_width=True)
            csv = df_fech.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", csv, f"fechamento_{loteria}.csv", "text/csv")
        else:
            st.warning("🔴 Muitas combinações! Escolha menos números base.")

with tab4:
    st.subheader("Painel Executivo - KPIs")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Média Frequência", f"{np.mean(freq):.1f}")
    col2.metric("Hot #1", hot[0])
    col3.metric("Cold #1", cold[0])
    col4.metric("Sorteios", f"{len(historical):,}")
    col_h, col_c = st.columns(2)
    with col_h:
        st.subheader("Top Hot")
        st.write(hot[:10].tolist())
    with col_c:
        st.subheader("Top Cold")
        st.write(cold[:10].tolist())
    fig_kpi_freq = px.histogram(x=freq, nbins=20, title="Distribuição Frequências")
    st.plotly_chart(fig_kpi_freq, use_container_width=True)

with tab5:
    st.subheader("Download Excel Consolidado")
    excel_data = make_excel(config, historical, freq, hot, cold, cooc)
    st.download_button(
        label="📥 Baixar Relatório Completo",
        data=excel_data,
        file_name=f"loterias_pro_{loteria.lower().replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.markdown("---")
st.markdown("*App PRO MAX: 100% vetorizado, sem deps extras. Funciona no Streamlit Cloud.*")

#=== requirements.txt ===
streamlit
pandas
numpy
plotly
openpyxl
