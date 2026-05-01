import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime
from itertools import combinations

# ------------------------------
# TEMA DARK (opcional)
# ------------------------------
st.set_page_config(page_title="MultiLoterias Analyzer", page_icon="🎰", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    .stMetric > label { color: #fafafa; }
    h1, h2, h3 { color: #fafafa; }
</style>
""", unsafe_allow_html=True)

# ------------------------------
# CONFIGURAÇÃO CENTRAL DE LOTERIAS
# ------------------------------
LOTTERIES = {
    "Mega-Sena": {"key": "megasena", "max": 60, "numbers": 6},
    "Quina": {"key": "quina", "max": 80, "numbers": 5},
    "Lotofácil": {"key": "lotofacil", "max": 25, "numbers": 15}
}

# ------------------------------
# FUNÇÕES
# ------------------------------
@st.cache_data(ttl=3600)
def fetch_latest(lottery_key):
    """Busca o último concurso oficial"""
    url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{lottery_key}"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if resp.status_code != 200:
        return None
    return resp.json()

@st.cache_data(ttl=3600)
def fetch_concurso(lottery_key, concurso):
    """Busca concurso específico"""
    url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{lottery_key}/{concurso}"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if resp.status_code != 200:
        return None
    return resp.json()

@st.cache_data(ttl=3600)
def load_history(lottery_key, draws=50):
    """Carrega histórico real dos últimos X concursos"""
    latest = fetch_latest(lottery_key)
    if not latest:
        return []
    last_n = latest.get("numero", 0)
    history = []
    for c in range(last_n, last_n - draws, -1):
        data = fetch_concurso(lottery_key, c)
        if data and data.get("listaDezenas"):
            dezenas = [int(x) for x in data["listaDezenas"]]
            history.append({
                "concurso": data.get("numero"),
                "data": data.get("dataApuracao"),
                "dezenas": dezenas
            })
    return history

def hot_cold(history, max_num):
    """Retorna os 10 mais frequentes e 10 menos frequentes"""
    freq = np.zeros(max_num)
    for h in history:
        for n in h["dezenas"]:
            freq[n-1] += 1
    hot = np.argsort(freq)[-10:][::-1] + 1
    cold = np.argsort(freq)[:10] + 1
    return list(hot), list(cold), freq

def coocorrencia(history, max_num):
    """Calcula pares mais frequentes"""
    matrix = np.zeros((max_num, max_num))
    for h in history:
        nums = sorted(h["dezenas"])
        for i in range(len(nums)):
            for j in range(i+1, len(nums)):
                matrix[nums[i]-1][nums[j]-1] += 1
    pares = []
    for i in range(max_num):
        for j in range(i+1, max_num):
            if matrix[i][j] > 0:
                pares.append((i+1, j+1, matrix[i][j]))
    pares.sort(key=lambda x: x[2], reverse=True)
    return pares[:20]

def monte_carlo(freq_hist, max_num, qt_numbers, sims=20000):
    """Simulação ponderada pela frequência histórica"""
    probs = freq_hist / freq_hist.sum()
    results = np.zeros(max_num)
    for _ in range(sims):
        draw = np.random.choice(range(1, max_num+1), qt_numbers, replace=False, p=probs)
        for d in draw:
            results[d-1] += 1
    return results

# ------------------------------
# INTERFACE
# ------------------------------
st.title("🎰 MultiLoterias Analyzer — Versão Revisada e Estável")

choice = st.sidebar.selectbox("Selecione a loteria", list(LOTTERIES.keys()))
cfg = LOTTERIES[choice]

draws = st.sidebar.slider("Concursos históricos", 10, 200, 50)
history = load_history(cfg["key"], draws)

if not history:
    st.error("Não foi possível carregar dados da Caixa.")
    st.stop()

latest = history[0]
st.subheader(f"📌 Último concurso ({choice})")
st.write(f"**Concurso:** {latest['concurso']}")
st.write(f"**Data:** {latest['data']}")
st.write(f"**Dezenas:** {', '.join(map(str, latest['dezenas']))}")

# ------------------------------
# HOT/COLD
# ------------------------------
st.markdown("## 🔥 Hot / ❄️ Cold Numbers")
hot, cold, freq_hist = hot_cold(history, cfg["max"])

col1, col2 = st.columns(2)
with col1:
    st.write("🔥 **Mais frequentes:**")
    st.write(" | ".join(map(str, hot)))
with col2:
    st.write("❄️ **Menos frequentes:**")
    st.write(" | ".join(map(str, cold)))

fig_freq = px.bar(x=list(range(1, cfg["max"]+1)), y=freq_hist, title="Frequência Histórica")
st.plotly_chart(fig_freq, use_container_width=True)

# ------------------------------
# COOCORRÊNCIA
# ------------------------------
st.markdown("## 🔗 Coocorrência de Pares")
pares = coocorrencia(history, cfg["max"])
df_pares = pd.DataFrame(pares, columns=["Num1", "Num2", "Frequência"])
st.dataframe(df_pares, use_container_width=True)

# ------------------------------
# MONTE CARLO
# ------------------------------
st.markdown("## 🎲 Simulação Monte Carlo")
sims = st.slider("Simulações", 5000, 50000, 20000, 5000)
sim_freq = monte_carlo(freq_hist, cfg["max"], cfg["numbers"], sims)

fig_sim = px.bar(x=list(range(1, cfg["max"]+1)), y=sim_freq, title="Monte Carlo — Frequência Projetada")
st.plotly_chart(fig_sim, use_container_width=True)

# ------------------------------
# FECHAMENTOS
# ------------------------------
st.markdown("## 🧩 Fechamentos")
nums_escolhidos = st.multiselect("Escolha números", list(range(1, cfg["max"]+1)))
if len(nums_escolhidos) >= cfg["numbers"]:
    combs = list(combinations(sorted(nums_escolhidos), cfg["numbers"]))
    st.write(f"Total de combinações: {len(combs)}")
    if len(combs) <= 50:
        for c in combs:
            st.write(c)
    else:
        st.write("Mostrando apenas as 50 primeiras:")
        for c in combs[:50]:
            st.write(c)
else:
    st.info(f"Selecione pelo menos {cfg['numbers']} números.")

st.markdown("---")
st.caption("Dados oficiais da Caixa Econômica Federal. App revisado e otimizado.")
