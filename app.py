import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter, defaultdict
from itertools import combinations
from datetime import datetime

st.set_page_config(page_title="MultiLoterias Enterprise", layout="wide")

# ================================
# THEME DARK
# ================================
st.markdown("""
<style>
.stApp {background-color:#0e1117;color:#e8e8e8;}
h1,h2,h3,h4,h5,p,span,div {color:#e8e8e8 !important;}
.dataframe {color:black !important;}
</style>
""", unsafe_allow_html=True)

# ================================
# CONFIG Loterias
# ================================
LOTTERIES = {
    "megasena": {"name": "Mega-Sena", "max_concurso": 2950, "draw": 6, "nums": list(range(1,61))},
    "quina": {"name": "Quina", "max_concurso": 6600, "draw": 5, "nums": list(range(1,81))},
    "lotofacil": {"name": "Lotofácil", "max_concurso": 3200, "draw": 15, "nums": list(range(1,26))}
}

API_BASE = "https://servicebus2.caixa.gov.br/portaldeloterias/api"

# ================================
# FETCH DATA
# ================================
@st.cache_data(ttl=3600)
def fetch_caixa(lottery, limit=80):
    conf = LOTTERIES[lottery]
    max_c = conf["max_concurso"]
    out=[]
    while len(out)<limit and max_c>0:
        url=f"{API_BASE}/{lottery}/{max_c}"
        try:
            r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=10)
            if r.status_code==200:
                j=r.json()
                if "listaDezenas" in j and j["listaDezenas"]:
                    nums=[int(x) for x in j["listaDezenas"]]
                    if len(nums)==conf["draw"]:
                        out.append({
                            "concurso":j["numero"],
                            "data":j["dataApuracao"],
                            "nums":nums
                        })
        except:
            pass
        max_c-=1
    return sorted(out,key=lambda x:x["concurso"], reverse=True)

# ================================
# ANALYTICS
# ================================
def analyze_hotcold(results, top=10):
    all_nums=[n for r in results for n in r["nums"]]
    freq=Counter(all_nums)
    hot=freq.most_common(top)
    cold=freq.most_common()[-top:]
    return hot, cold, freq

def analyze_coocorrencia(results, top=20):
    c=Counter()
    for r in results:
        nums=r["nums"]
        for a,b in combinations(nums,2):
            c[(a,b)]+=1
    return c.most_common(top)

def monte_carlo(results, lottery, sims=20000):
    conf=LOTTERIES[lottery]
    base_nums=conf["nums"]
    all_nums=[n for r in results for n in r["nums"]]
    hist=Counter(all_nums)
    p=np.array([hist.get(n,1) for n in base_nums],dtype=float)
    p/=p.sum()
    simc=Counter()
    for _ in range(sims):
        d=np.random.choice(base_nums,size=conf["draw"],replace=False,p=p)
        for n in d: simc[n]+=1
    return simc.most_common(20)

def kpis(results):
    sums=[sum(r["nums"]) for r in results]
    even=[sum(1 for x in r["nums"] if x%2==0) for r in results]
    return {
        "mean_sum":np.mean(sums),
        "min_sum":min(sums),
        "max_sum":max(sums),
        "mean_even":np.mean(even),
        "count":len(results)
    }

def generate_fechamentos(user_nums, qtd, limit=50):
    user_nums=sorted(list(user_nums))
    c=list(combinations(user_nums,qtd))
    return c[:limit] if len(c)>limit else c

# ================================
# UI
# ================================
st.title("🎰 MultiLoterias Enterprise – Dashboards Premium")
st.markdown("Análises profissionais com dados oficiais da Caixa Econômica Federal.")

lottery=st.sidebar.selectbox(
    "Selecione a loteria:",
    list(LOTTERIES.keys()),
    format_func=lambda x:LOTTERIES[x]["name"]
)

limit=st.sidebar.slider("Concursos analisados",20,200,80)
refresh=st.sidebar.button("🔄 Atualizar")

if refresh:
    st.cache_data.clear()
    st.rerun()

results=fetch_caixa(lottery,limit)
if not results:
    st.error("Falha ao obter dados da Caixa.")
    st.stop()

conf=LOTTERIES[lottery]
last=results[0]

# ================================
# HEADER
# ================================
col1,col2,col3=st.columns(3)
col1.metric("Último concurso",last["concurso"])
col2.metric("Data",last["data"])
col3.metric("Números",", ".join(map(str,last["nums"])))

# ================================
# TABS
# ================================
tab1,tab2,tab3,tab4,tab5=st.tabs([
    "Histórico",
    "Hot/Cold",
    "Coocorrência",
    "Monte Carlo",
    "Fechamentos"
])

# ================================
# HISTÓRICO
# ================================
with tab1:
    st.subheader("📋 Histórico recente")
    df=pd.DataFrame([{
        "Concurso":r["concurso"],
        "Data":r["data"],
        "Dezenas":", ".join(map(str,r["nums"]))
    } for r in results])
    st.dataframe(df,use_container_width=True)

    st.subheader("📈 KPIs")
    k=kpis(results)
    c1,c2,c3,c4,c5=st.columns(5)
    c1.metric("Concursos",k["count"])
    c2.metric("Soma média",f"{k['mean_sum']:.1f}")
    c3.metric("Soma min",k["min_sum"])
    c4.metric("Soma max",k["max_sum"])
    c5.metric("Pares médios",f"{k['mean_even']:.1f}")

# ================================
# HOT/COLD
# ================================
with tab2:
    hot,cold,freq=analyze_hotcold(results)
    st.subheader("🔥 Hot")
    st.write(hot)
    st.subheader("❄️ Cold")
    st.write(cold)

    freq_df=pd.DataFrame({"Número":list(freq.keys()),"Frequência":list(freq.values())})
    freq_df=freq_df.sort_values("Número")
    fig=px.bar(freq_df,x="Número",y="Frequência",title="Frequência geral")
    st.plotly_chart(fig,use_container_width=True)

# ================================
# COOCORRÊNCIA
# ================================
with tab3:
    st.subheader("🔗 Pares mais frequentes")
    pairs=analyze_coocorrencia(results)
    dfp=pd.DataFrame([{"Par":f"{a}-{b}","Frequência":c} for (a,b),c in pairs])
    st.dataframe(dfp,use_container_width=True)
    fig=px.bar(dfp,x="Par",y="Frequência")
    st.plotly_chart(fig,use_container_width=True)

# ================================
# MONTE CARLO
# ================================
with tab4:
    st.subheader("🎲 Simulação Monte Carlo")
    sims=st.slider("Simulações",5000,50000,20000,5000)
    if st.button("Executar"):
        m=monte_carlo(results,lottery,sims)
        mdf=pd.DataFrame(m,columns=["Número","Frequência"])
        fig=px.bar(mdf,x="Número",y="Frequência",title="Frequência projetada")
        st.plotly_chart(fig,use_container_width=True)
        st.dataframe(mdf)

# ================================
# FECHAMENTOS
# ================================
with tab5:
    st.subheader("⚙️ Fechamentos combinatórios")
    sel=st.multiselect("Escolha números",conf["nums"])
    if len(sel)>=conf["draw"]:
        combos=generate_fechamentos(sel,conf["draw"])
        st.success(f"{len(combos)} apostas geradas")
        for i,cmb in enumerate(combos):
            st.caption(f"Aposta {i+1}: {cmb}")
    else:
        st.info(f"Selecione pelo menos {conf['draw']} números.")
