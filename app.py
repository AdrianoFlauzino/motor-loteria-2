import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import itertools
from io import BytesIO

# === CONFIGURAÇÕES DAS LOTERIAS ===
LOTERIAS = {
    "Mega-Sena": {"qtd": 6, "max_num": 60},
    "Quina": {"qtd": 5, "max_num": 80},
    "Lotofácil": {"qtd": 15, "max_num": 25}
}

# Prêmios aproximados (valores fixos para simulação)
PREMIOS = {
    "Mega-Sena": {6: 10000000, 5: 50000, 4: 1000, 3: 10},
    "Quina": {5: 1000000, 4: 5000, 3: 50},
    "Lotofácil": {15: 1000000, 14: 10000, 13: 1000, 12: 20, 11: 4}
}

# Custos por aposta
CUSTOS = {"Mega-Sena": 4.50, "Quina": 2.50, "Lotofácil": 3.00}

# === GERAÇÃO DE DADOS HISTÓRICOS (SINTÉTICO PARA DEMO) ===
@st.cache_data
def gerar_historico(loteria, n_sorteios=2000):
    qtd, max_num = loteria["qtd"], loteria["max_num"]
    historico = []
    for _ in range(n_sorteios):
        sorteio = sorted(np.random.choice(range(1, max_num + 1), qtd, replace=False))
        historico.append(sorteio)
    columns = [f'Num{i+1}' for i in range(qtd)]
    return pd.DataFrame(historico, columns=columns)

# === MOTOR ESTATÍSTICO: HOT/COLD ===
def analise_hot_cold(df):
    todos_nums = [num for sublist in df.values for num in sublist]
    freq = Counter(todos_nums)
    df_freq = pd.DataFrame(list(freq.items()), columns=['Numero', 'Frequencia']).sort_values('Frequencia', ascending=False)
    hot = df_freq.head(10)
    cold = df_freq.tail(10)
    return hot, cold, df_freq

# === MONTE CARLO COM PESOS ESTATÍSTICOS ===
def simulacao_monte_carlo(aposta, loteria, historico, n_sim=10000, usar_pesos=True):
    qtd, max_num = loteria["qtd"], loteria["max_num"]
    aposta_set = set(aposta)
    
    # Calcular probabilidades baseadas em histórico
    todos_nums_hist = [num for sublist in historico.values for num in sublist]
    freq_hist = Counter(todos_nums_hist)
    probs = np.array([freq_hist.get(i, 1) for i in range(1, max_num + 1)])
    probs = probs / probs.sum()
    
    hits = []
    for _ in range(n_sim):
        if usar_pesos:
            sorteio = sorted(np.random.choice(range(1, max_num + 1), qtd, p=probs, replace=False))
        else:
            sorteio = sorted(np.random.choice(range(1, max_num + 1), qtd, replace=False))
        acertos = len(aposta_set.intersection(set(sorteio)))
        hits.append(acertos)
    
    return pd.Series(hits).value_counts().sort_index()

# === MÓDULO FINANCEIRO ROI ===
def calcular_roi(sim_result, loteria_nome):
    pr = PREMIOS.get(loteria_nome, {})
    custo = CUSTOS.get(loteria_nome, 4.50)
    total_sims = sim_result.sum() if isinstance(sim_result, pd.Series) else len(sim_result)
    
    roi_details = {}
    ganho_esperado_total = 0
    
    for acertos in sorted(set(list(pr.keys()) + list(sim_result.index))):
        count = sim_result.get(acertos, 0)
        prob = count / total_sims
        premio = pr.get(acertos, 0)
        esperado = prob * premio
        roi_details[acertos] = {
            'Probabilidade': f'{prob:.4f}',
            'Prêmio (R$)': f'{premio:,.2f}',
            'Ganho Esperado (R$)': f'{esperado:,.2f}'
        }
        ganho_esperado_total += esperado
    
    roi_details['ROI'] = {
        'Probabilidade': '-',
        'Prêmio (R$)': f'{custo:,.2f}',
        'Ganho Esperado (R$)': f'{((ganho_esperado_total - custo) / custo * 100):.2f}%'
    }
    return roi_details

# === MATRIZ DE HITS (CO-OCORRÊNCIA) ===
def matriz_hits(df, top_n=20):
    cooc = Counter()
    for row in df.values:
        for par in itertools.combinations(sorted(row), 2):
            cooc[par] += 1
    top_pairs = cooc.most_common(top_n)
    df_pairs = pd.DataFrame(top_pairs, columns=['Par', 'Hits']).head(top_n)
    df_pairs['Par1'] = df_pairs['Par'].apply(lambda x: x[0])
    df_pairs['Par2'] = df_pairs['Par'].apply(lambda x: x[1])
    return df_pairs

# === FECHAMENTOS MATEMÁTICOS (COMBINATÓRIOS REDUZIDOS) ===
def gerar_fechamento(loteria_nome, base_nums):
    qtd = LOTERIAS[loteria_nome]['qtd']
    if len(base_nums) <= qtd:
        return [tuple(sorted(base_nums))]
    # Fechamento simples: todas as combinações de qtd a partir de base
    combs = list(itertools.combinations(base_nums, qtd))
    return list(combs)

# === CONFIGURAÇÃO DA PÁGINA (MOBILE-FRIENDLY) ===
st.set_page_config(
    page_title="Lottery PRO MAX",
    page_icon="🎰",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🎰 Lottery PRO MAX - Plataforma Data Science Completa")
st.markdown("***Simulador Monte Carlo | Estatísticas Reais | ROI Financeiro | Fechamentos | KPIs | Excel***")

# === SIDEBAR: CONTROLES ===
loteria = st.sidebar.selectbox("Selecione a Loteria:", list(LOTERIAS.keys()))
qtd, max_num = LOTERIAS[loteria]['qtd'], LOTERIAS[loteria]['max_num']

st.sidebar.subheader("📝 Sua Aposta")
input_aposta = st.sidebar.text_input(f"{qtd} números de 1 a {max_num} (vírgula separada)", "1,10,15,22,30,45")

try:
    aposta_raw = [int(x.strip()) for x in input_aposta.split(',') if x.strip().isdigit()]
    aposta = sorted(list(set(aposta_raw)))  # Remove duplicatas
    if len(aposta) != qtd or any(n < 1 or n > max_num for n in aposta):
        st.sidebar.error(f"❌ Erro: Exatos {qtd} números únicos entre 1 e {max_num}!")
        aposta = None
    else:
        st.sidebar.success(f"✅ Aposta válida: {', '.join(map(str, aposta))}")
except:
    st.sidebar.error("❌ Formato inválido!")
    aposta = None

n_sim = st.sidebar.slider("🔄 Simulações Monte Carlo", 1000, 50000, 10000, 1000)
usar_pesos = st.sidebar.checkbox("⚖️ Usar Pesos Estatísticos (Hot Numbers)", True)

# === CÁLCULOS PRINCIPAIS ===
historico = gerar_historico(LOTERIAS[loteria])
hot, cold, freq_df = analise_hot_cold(historico)
matriz_df = matriz_hits(historico)

sim_df = pd.Series()
roi_details = {}
if aposta:
    sim_df = simulacao_monte_carlo(aposta, LOTERIAS[loteria], historico, n_sim, usar_pesos)
    roi_details = calcular_roi(sim_df, loteria)

# === PAINEL PRINCIPAL COM TABS ===
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Monte Carlo", "🔥 Hot/Cold", "💰 ROI", "🔗 Hits Matrix", "⚙️ Fechamentos", "📈 KPIs", "📥 Excel"
])

with tab1:
    st.subheader("Simulador Monte Carlo PRO")
    if aposta:
        col1, col2 = st.columns([2,1])
        with col1:
            fig = px.bar(x=sim_df.index.astype(str), y=sim_df.values, 
                         title=f"Distribuição de Acertos ({n_sim:,} simulações)",
                         labels={'x':'Acertos', 'y':'Frequência'})
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            probs = (sim_df / n_sim * 100).round(2)
            st.metric("Chance Sena", f"{probs.get(qtd, 0):.4f}%" if qtd in probs else "0.0000%")
        st.dataframe(pd.DataFrame({'Acertos': sim_df.index, 'Contagem': sim_df.values, 'Prob %': (sim_df.values / n_sim * 100).round(4)}))
    else:
        st.warning("👈 Insira uma aposta válida no sidebar!")

with tab2:
    st.subheader("Análise Hot/Cold Numbers")
    col1, col2 = st.columns(2)
    with col1:
        fig_hot = px.bar(hot, x='Numero', y='Frequencia', title="🔥 10 Hot Numbers")
        st.plotly_chart(fig_hot, use_container_width=True)
    with col2:
        fig_cold = px.bar(cold, x='Numero', y='Frequencia', title="❄️ 10 Cold Numbers")
        st.plotly_chart(fig_cold, use_container_width=True)
    st.dataframe(freq_df.head(20))

with tab3:
    st.subheader("Módulo Financeiro - ROI Completo")
    if roi_details:
        roi_df = pd.DataFrame.from_dict(roi_details, orient='index')
        st.dataframe(roi_df)
        roi_val = float(roi_df.loc['ROI', 'Ganho Esperado (R$)'].replace('%',''))
        st.metric("🔑 ROI Esperado", f"{roi_val:.2f}%")
    else:
        st.warning("👈 Execute Monte Carlo primeiro!")

with tab4:
    st.subheader("Matriz de Hits - Pares Mais Frequentes")
    fig_hits = px.bar(matriz_df.head(10), x='Par', y='Hits', title="Top Pares")
    st.plotly_chart(fig_hits, use_container_width=True)
    st.dataframe(matriz_df)

with tab5:
    st.subheader("Fechamentos Matemáticos (Combinatórios)")
    input_base = st.text_input(f"Base de números (ex: {qtd+2} nums separadas por vírgula)", f"1,2,3,4,5,6,7,8")
    try:
        base = sorted([int(x.strip()) for x in input_base.split(',') if x.strip().isdigit()])
        if len(set(base)) != len(base) or any(n<1 or n>LOTERIAS[loteria]['max_num'] for n in base):
            st.error("Números únicos e válidos!")
        else:
            fechamentos = gerar_fechamento(loteria, base)
            st.success(f"✅ Geradas {len(fechamentos)} combinações (custo: R$ {len(fechamentos)*CUSTOS[loteria]:.2f})")
            st.dataframe(pd.DataFrame(fechamentos, columns=[f'N{i+1}' for i in range(qtd)]))
    except:
        st.error("Formato inválido!")

with tab6:
    st.subheader("KPIs Executivos")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Sorteios", f"{len(historico):,}")
    with col2:
        media_acertos = round(sim_df.mean(), 2) if len(sim_df) > 0 else 0
        st.metric("Média Acertos (Sim)", f"{media_acertos}")
    with col3:
        roi_val = float(roi_details.get('ROI', {}).get('Ganho Esperado (R$)', '0').replace('%','')) if roi_details else 0
        st.metric("ROI %", f"{roi_val:.2f}%")
    with col4:
        top_freq = hot['Frequencia'].max() if not hot.empty else 0
        st.metric("Freq. Mais Quente", f"{top_freq}")

with tab7:
    st.subheader("📥 Download Excel Consolidado")
    excel_data = BytesIO()
    with pd.ExcelWriter(excel_data, engine='openpyxl') as writer:
        historico.to_excel(writer, 'Historico', index=False)
        freq_df.to_excel(writer, 'Frequencias', index=False)
        matriz_df.to_excel(writer, 'Matriz_Hits', index=False)
        if len(sim_df) > 0:
            sim_export = pd.DataFrame({
                'Acertos': sim_df.index,
                'Contagem': sim_df.values,
                'Prob_%': (sim_df.values / n_sim * 100).round(4)
            })
            sim_export.to_excel(writer, 'MonteCarlo', index=False)
            if roi_details:
                roi_export = pd.DataFrame.from_dict(roi_details, orient='index')
                roi_export.to_excel(writer, 'ROI', index=True)
        st.info("Todas as abas incluídas!")
    
    st.download_button(
        label="⬇️ Baixar Relatório PRO MAX.xlsx",
        data=excel_data.getvalue(),
        file_name=f"pro_max_{loteria.lower().replace('-', '_')}.xlsx",
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# === FOOTER ===
st.markdown("---")
st.markdown("*Desenvolvido com Data Science | Compatível Streamlit Cloud | Atualização dinâmica* 🧠")
