import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime, timedelta
import hashlib
import json

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Analisador de Loterias",
    page_icon="🎲",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# DEFINIÇÃO DE LOTERIAS (Multi-loteria)
# ============================================================
LOTTERIES = {
    "Mega-Sena": {
        "num_dezenas": 6,
        "max_numero": 60,
        "faixa_premios": [6, 5, 4],
        "cor": "green",
    },
    "Quina": {
        "num_dezenas": 5,
        "max_numero": 80,
        "faixa_premios": [5, 4, 3, 2],
        "cor": "purple",
    },
    "Lotofácil": {
        "num_dezenas": 15,
        "max_numero": 25,
        "faixa_premios": [15, 14, 13, 12, 11],
        "cor": "orange",
    },
    "Lotomania": {
        "num_dezenas": 20,
        "max_numero": 100,
        "faixa_premios": [20, 19, 18, 17, 16, 15, 0],
        "cor": "blue",
    },
    "Dia de Sorte": {
        "num_dezenas": 7,
        "max_numero": 31,
        "faixa_premios": [7, 6, 5, 4],
        "cor": "pink",
    },
}

# ============================================================
# DEFINIÇÃO DE TEMAS
# ============================================================
THEMES = {
    "Escuro": {
        "bg": "#0e1117",
        "card_bg": "#1e1e2e",
        "text": "#ffffff",
        "accent": "#00d4ff",
        "plotly_template": "plotly_dark",
    },
    "Claro": {
        "bg": "#ffffff",
        "card_bg": "#f0f2f6",
        "text": "#000000",
        "accent": "#1f77b4",
        "plotly_template": "plotly_white",
    },
    "Oceano": {
        "bg": "#001f3f",
        "card_bg": "#003366",
        "text": "#e0e0e0",
        "accent": "#39cccc",
        "plotly_template": "plotly_dark",
    },
    "Floresta": {
        "bg": "#0d2818",
        "card_bg": "#1a3a2a",
        "text": "#e0e0e0",
        "accent": "#2ecc40",
        "plotly_template": "plotly_dark",
    },
}

# ============================================================
# INICIALIZAÇÃO DE SESSION STATE
# ============================================================
def init_session_state():
    defaults = {
        "lottery": "Mega-Sena",
        "theme": "Escuro",
        "uploaded_data": None,
        "df_historico": None,
        "backtest_results": None,
        "last_analysis": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session_state()

# ============================================================
# FUNÇÕES UTILITÁRIAS
# ============================================================
def apply_theme(theme_name):
    theme = THEMES.get(theme_name, THEMES["Escuro"])
    st.markdown(
        f"""
        <style>
        .stApp {{ background-color: {theme['bg']}; color: {theme['text']}; }}
        .stSidebar {{ background-color: {theme['card_bg']}; }}
        .metric-card {{
            background-color: {theme['card_bg']};
            border-radius: 10px;
            padding: 15px;
            margin: 5px 0;
            border-left: 4px solid {theme['accent']};
        }}
        .section-header {{
            color: {theme['accent']};
            font-size: 1.4em;
            font-weight: bold;
            margin: 20px 0 10px 0;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    return theme

def generate_unique_key(*parts):
    raw = "_".join(str(p) for p in parts)
    return hashlib.md5(raw.encode()).hexdigest()[:10]

def process_uploaded_file(uploaded_file, lottery_name):
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
        elif uploaded_file.name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file)
        elif uploaded_file.name.endswith('.json'):
            df = pd.read_json(uploaded_file)
        else:
            st.error("Formato de arquivo não suportado. Use CSV, Excel ou JSON.")
            return None
        st.success(f"Arquivo '{uploaded_file.name}' carregado com {len(df)} registros.")
        return df
    except Exception as e:
        st.error(f"Erro ao processar arquivo: {e}")
        return None

def generate_sample_data(lottery_name, num_concursos=100):
    cfg = LOTTERIES[lottery_name]
    max_n = cfg["max_numero"]
    num_dezenas = cfg["num_dezenas"]
    data = []
    base_date = datetime.now() - timedelta(days=num_concursos * 3)
    for i in range(1, num_concursos + 1):
        dezenas = sorted(np.random.choice(range(1, max_n + 1), num_dezenas, replace=False))
        row = {"Concurso": i, "Data": (base_date + timedelta(days=i * 3)).strftime("%d/%m/%Y")}
        for j, d in enumerate(dezenas):
            row[f"D{j+1}"] = d
        data.append(row)
    return pd.DataFrame(data)

def extract_dezenas(df, lottery_name):
    cfg = LOTTERIES[lottery_name]
    num_dezenas = cfg["num_dezenas"]
    dezena_cols = [f"D{i+1}" for i in range(num_dezenas)]
    existing_cols = [c for c in dezena_cols if c in df.columns]
    if not existing_cols:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        existing_cols = numeric_cols[:num_dezenas]
    if not existing_cols:
        return None
    return df[existing_cols].values

def calcular_frequencias(df, lottery_name):
    dezenas = extract_dezenas(df, lottery_name)
    if dezenas is None:
        return None
    cfg = LOTTERIES[lottery_name]
    max_n = cfg["max_numero"]
    freq = np.zeros(max_n + 1, dtype=int)
    for row in dezenas:
        for val in row:
            try:
                idx = int(val)
                if 1 <= idx <= max_n:
                    freq[idx] += 1
            except (ValueError, TypeError):
                continue
    freq_df = pd.DataFrame({
        "Numero": range(1, max_n + 1),
        "Frequencia": freq[1:max_n + 1],
    })
    freq_df["Percentual"] = (freq_df["Frequencia"] / freq_df["Frequencia"].sum() * 100).round(2)
    return freq_df

def analisar_padroes_comportamentais(df, lottery_name):
    dezenas = extract_dezenas(df, lottery_name)
    if dezenas is None:
        return None
    cfg = LOTTERIES[lottery_name]
    max_n = cfg["max_numero"]
    num_dezenas = cfg["num_dezenas"]
    padroes = {}
    # Pares e ímpares
    pares_impares = []
    for row in dezenas:
        pares = sum(1 for v in row if int(v) % 2 == 0)
        impares = num_dezenas - pares
        pares_impares.append((pares, impares))
    padroes["pares_impares"] = pares_impares
    # Soma das dezenas
    somas = [sum(int(v) for v in row) for row in dezenas]
    padroes["somas"] = somas
    # Sequências consecutivas
    consecutivos = []
    for row in dezenas:
        sorted_row = sorted(int(v) for v in row)
        max_seq = 1
        cur_seq = 1
        for i in range(1, len(sorted_row)):
            if sorted_row[i] == sorted_row[i-1] + 1:
                cur_seq += 1
                max_seq = max(max_seq, cur_seq)
            else:
                cur_seq = 1
        consecutivos.append(max_seq)
    padroes["consecutivos"] = consecutivos
    # Distribuição por quadrantes
    quadrante_size = max_n // 4
    quadrantes = []
    for row in dezenas:
        q = [0, 0, 0, 0]
        for v in row:
            idx = min(int((int(v) - 1) / quadrante_size), 3)
            q[idx] += 1
        quadrantes.append(q)
    padroes["quadrantes"] = quadrantes
    # Números quentes e frios (últimos 20 sorteios)
    recent = dezenas[-20:] if len(dezenas) >= 20 else dezenas
    recent_freq = np.zeros(max_n + 1, dtype=int)
    for row in recent:
        for v in row:
            idx = int(v)
            if 1 <= idx <= max_n:
                recent_freq[idx] += 1
    quentes = np.argsort(recent_freq[1:max_n+1])[-10:][::-1] + 1
    frios = np.argsort(recent_freq[1:max_n+1])[:10] + 1
    padroes["quentes"] = quentes.tolist()
    padroes["frios"] = frios.tolist()
    return padroes

def gerar_palpites(lottery_name, freq_df, padroes, num_palpites=5):
    cfg = LOTTERIES[lottery_name]
    max_n = cfg["max_numero"]
    num_dezenas = cfg["num_dezenas"]
    palpites = []
    if freq_df is not None and not freq_df.empty:
        pesos = freq_df["Frequencia"].values.astype(float)
        pesos = pesos / pesos.sum()
    else:
        pesos = np.ones(max_n) / max_n
    for _ in range(num_palpites):
        numeros = np.random.choice(range(1, max_n + 1), num_dezenas, replace=False, p=pesos)
        palpites.append(sorted(numeros.tolist()))
    return palpites

def run_backtest(df, lottery_name, num_palpites=5, window=50):
    dezenas = extract_dezenas(df, lottery_name)
    if dezenas is None or len(dezenas) < window + 10:
        return None
    cfg = LOTTERIES[lottery_name]
    faixa_premios = cfg["faixa_premios"]
    results = []
    for start in range(0, len(dezenas) - window, max(1, window // 5)):
        train = dezenas[start:start + window]
        test = dezenas[start + window:start + window + 1]
        if len(test) == 0:
            break
        # Frequência de treino
        freq = np.zeros(cfg["max_numero"] + 1, dtype=int)
        for row in train:
            for v in row:
                idx = int(v)
                if 1 <= idx <= cfg["max_numero"]:
                    freq[idx] += 1
        pesos = freq[1:cfg["max_numero"]+1].astype(float)
        if pesos.sum() == 0:
            pesos = np.ones_like(pesos)
        pesos = pesos / pesos.sum()
        # Gerar palpites
        acertos_max = 0
        for _ in range(num_palpites):
            palpite = set(np.random.choice(range(1, cfg["max_numero"]+1), cfg["num_dezenas"], replace=False, p=pesos))
            sorteio = set(int(v) for v in test[0])
            acertos = len(palpite & sorteio)
            acertos_max = max(acertos_max, acertos)
        results.append({
            "Concurso": start + window + 1,
            "Acertos": acertos_max,
            "Premio": acertos_max in faixa_premios,
        })
    return pd.DataFrame(results)

def export_to_excel(df_list, sheet_names):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for df, name in zip(df_list, sheet_names):
            if df is not None and not df.empty:
                df.to_excel(writer, sheet_name=name[:31], index=False)
    output.seek(0)
    return output

# ============================================================
# SIDEBAR
# ============================================================
theme = apply_theme(st.session_state.theme)

st.sidebar.markdown("## 🎲 Configurações")

# --- CORREÇÃO APLICADA: Verificação segura do índice para 'Loteria' ---
lottery_options = list(LOTTERIES.keys())
lottery_idx = (
    lottery_options.index(st.session_state.lottery)
    if st.session_state.lottery in lottery_options
    else 0
)
st.session_state.lottery = st.selectbox(
    "Loteria",
    lottery_options,
    index=lottery_idx,
    key="sidebar_lottery_select",
)

# --- CORREÇÃO APLICADA: Verificação segura do índice para 'Tema' ---
theme_options = list(THEMES.keys())
theme_idx = (
    theme_options.index(st.session_state.theme)
    if st.session_state.theme in theme_options
    else 0
)
st.session_state.theme = st.selectbox(
    "Tema",
    theme_options,
    index=theme_idx,
    key="sidebar_theme_select",
)

# Reaplicar tema caso tenha mudado
theme = apply_theme(st.session_state.theme)

current_lottery = st.session_state.lottery
cfg = LOTTERIES[current_lottery]

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Configuração:** {current_lottery}")
st.sidebar.markdown(f"- Dezenas por sorteio: **{cfg['num_dezenas']}**")
st.sidebar.markdown(f"- Maior número: **{cfg['max_numero']}**")
st.sidebar.markdown(f"- Faixas de prêmio: **{cfg['faixa_premios']}**")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📁 Upload de Arquivo")
uploaded_file = st.sidebar.file_uploader(
    "Carregar histórico de sorteios",
    type=["csv", "xlsx", "xls", "json"],
    key=generate_unique_key("uploader", current_lottery),
)

if uploaded_file is not None:
    df = process_uploaded_file(uploaded_file, current_lottery)
    if df is not None:
        st.session_state.df_historico = df
        st.session_state.uploaded_data = True

st.sidebar.markdown("---")
use_sample = st.sidebar.checkbox("Usar dados de exemplo", value=st.session_state.df_historico is None)

if st.sidebar.button("🔄 Carregar/Recarregar Dados", key=generate_unique_key("btn_load", current_lottery)):
    if use_sample or st.session_state.df_historico is None:
        st.session_state.df_historico = generate_sample_data(current_lottery, 200)
        st.sidebar.success("Dados de exemplo gerados!")
    else:
        st.sidebar.success("Dados carregados do arquivo!")

st.sidebar.markdown("---")
num_palpites = st.sidebar.slider("Número de palpites", 1, 20, 5, key=generate_unique_key("slider_palpites", current_lottery))
backtest_window = st.sidebar.slider("Janela de Backtesting", 20, 150, 50, key=generate_unique_key("slider_backtest", current_lottery))

# ============================================================
# CONTEÚDO PRINCIPAL
# ============================================================
st.markdown(f"<div class='section-header'>📊 Analisador de Loterias — {current_lottery}</div>", unsafe_allow_html=True)

df = st.session_state.df_historico

if df is None:
    st.info("👈 Carregue um arquivo ou clique em 'Carregar/Recarregar Dados' na barra lateral para iniciar.")
    st.stop()

# Exibir dados
st.markdown("<div class='section-header'>📋 Histórico de Sorteios</div>", unsafe_allow_html=True)
st.dataframe(df.head(50), use_container_width=True)

# Métricas gerais
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"<div class='metric-card'><b>Total de Concursos</b><br><span style='font-size:1.8em'>{len(df)}</span></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='metric-card'><b>Dezenas por Sorteio</b><br><span style='font-size:1.8em'>{cfg['num_dezenas']}</span></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='metric-card'><b>Maior Número</b><br><span style='font-size:1.8em'>{cfg['max_numero']}</span></div>", unsafe_allow_html=True)
with col4:
    st.markdown(f"<div class='metric-card'><b>Faixas de Prêmio</b><br><span style='font-size:1.8em'>{len(cfg['faixa_premios'])}</span></div>", unsafe_allow_html=True)

# ============================================================
# ANÁLISE DE FREQUÊNCIAS
# ============================================================
st.markdown("<div class='section-header'>🔥 Análise de Frequências</div>", unsafe_allow_html=True)

freq_df = calcular_frequencias(df, current_lottery)

if freq_df is not None:
    col_freq1, col_freq2 = st.columns(2)

    with col_freq1:
        fig_bar = px.bar(
            freq_df,
            x="Numero",
            y="Frequencia",
            title=f"Frequência dos Números — {current_lottery}",
            template=theme["plotly_template"],
            color="Frequencia",
            color_continuous_scale="Viridis",
        )
        fig_bar.update_layout(
            xaxis_title="Número",
            yaxis_title="Frequência",
            height=400,
        )
        st.plotly_chart(fig_bar, use_container_width=True, key=generate_unique_key("chart_freq_bar", current_lottery))

    with col_freq2:
        top_n = 15
        top_freq = freq_df.nlargest(top_n, "Frequencia")
        fig_top = px.bar(
            top_freq,
            x="Numero",
            y="Frequencia",
            title=f"Top {top_n} Números Mais Sorteados",
            template=theme["plotly_template"],
            color="Frequencia",
            color_continuous_scale="Inferno",
        )
        fig_top.update_layout(
            xaxis_title="Número",
            yaxis_title="Frequência",
            height=400,
        )
        st.plotly_chart(fig_top, use_container_width=True, key=generate_unique_key("chart_freq_top", current_lottery))

    st.markdown("#### 📊 Tabela de Frequências")
    st.dataframe(freq_df.sort_values("Frequencia", ascending=False), use_container_width=True)

# ============================================================
# PADRÕES COMPORTAMENTAIS
# ============================================================
st.markdown("<div class='section-header'>🧠 Padrões Comportamentais</div>", unsafe_allow_html=True)

padroes = analisar_padroes_comportamentais(df, current_lottery)

if padroes is not None:
    col_p1, col_p2 = st.columns(2)

    with col_p1:
        # Pares e Ímpares
        pi_df = pd.DataFrame(padroes["pares_impares"], columns=["Pares", "Ímpares"])
        fig_pi = px.histogram(
            pi_df,
            x="Pares",
            title="Distribuição de Pares por Sorteio",
            template=theme["plotly_template"],
            color_discrete_sequence=[theme["accent"]],
            nbins=cfg["num_dezenas"] + 1,
        )
        fig_pi.update_layout(height=350, xaxis_title="Quantidade de Pares", yaxis_title="Frequência")
        st.plotly_chart(fig_pi, use_container_width=True, key=generate_unique_key("chart_pares", current_lottery))

    with col_p2:
        # Soma das dezenas
        soma_df = pd.DataFrame({"Soma": padroes["somas"]})
        fig_soma = px.histogram(
            soma_df,
            x="Soma",
            title="Distribuição da Soma das Dezenas",
            template=theme["plotly_template"],
            color_discrete_sequence=[theme["accent"]],
            nbins=30,
        )
        fig_soma.update_layout(height=350, xaxis_title="Soma", yaxis_title="Frequência")
        st.plotly_chart(fig_soma, use_container_width=True, key=generate_unique_key("chart_soma", current_lottery))

    col_p3, col_p4 = st.columns(2)

    with col_p3:
        # Consecutivos
        cons_df = pd.DataFrame({"Máx. Consecutivos": padroes["consecutivos"]})
        fig_cons = px.histogram(
            cons_df,
            x="Máx. Consecutivos",
            title="Sequências Consecutivas Máximas",
            template=theme["plotly_template"],
            color_discrete_sequence=[theme["accent"]],
            nbins=10,
        )
        fig_cons.update_layout(height=350, xaxis_title="Máx. Consecutivos", yaxis_title="Frequência")
        st.plotly_chart(fig_cons, use_container_width=True, key=generate_unique_key("chart_cons", current_lottery))

    with col_p4:
        # Quadrantes
        quad_df = pd.DataFrame(
            padroes["quadrantes"],
            columns=["Q1", "Q2", "Q3", "Q4"],
        )
        quad_mean = quad_df.mean().reset_index()
        quad_mean.columns = ["Quadrante", "Média"]
        fig_quad = px.bar(
            quad_mean,
            x="Quadrante",
            y="Média",
            title="Distribuição Média por Quadrante",
            template=theme["plotly_template"],
            color="Média",
            color_continuous_scale="Plasma",
        )
        fig_quad.update_layout(height=350)
        st.plotly_chart(fig_quad, use_container_width=True, key=generate_unique_key("chart_quad", current_lottery))

    # Números quentes e frios
    st.markdown("#### 🔥 Números Quentes (últimos 20 sorteios) e ❄️ Números Frios")
    col_q, col_f = st.columns(2)
    with col_q:
        st.markdown(f"**Quentes:** {', '.join(str(n) for n in padroes['quentes'])}")
    with col_f:
        st.markdown(f"**Frios:** {', '.join(str(n) for n in padroes['frios'])}")

# ============================================================
# GERAÇÃO DE PALPITES
# ============================================================
st.markdown("<div class='section-header'>🎯 Geração de Palpites</div>", unsafe_allow_html=True)

if st.button("🎲 Gerar Palpites", key=generate_unique_key("btn_palpites", current_lottery)):
    palpites = gerar_palpites(current_lottery, freq_df, padroes, num_palpites)
    st.session_state.last_analysis = palpites

if st.session_state.last_analysis is not None:
    palpites = st.session_state.last_analysis
    for i, palpite in enumerate(palpites):
        st.markdown(
            f"<div class='metric-card'><b>Palpite {i+1}:</b> "
            + " - ".join(f"<span style='font-size:1.3em;color:{theme['accent']}'>{n:02d}</span>" for n in palpite)
            + "</div>",
            unsafe_allow_html=True,
        )

# ============================================================
# BACKTESTING
# ============================================================
st.markdown("<div class='section-header'>📈 Backtesting</div>", unsafe_allow_html=True)

if st.button("▶️ Executar Backtesting", key=generate_unique_key("btn_backtest", current_lottery)):
    with st.spinner("Executando backtesting..."):
        bt_df = run_backtest(df, current_lottery, num_palpites=num_palpites, window=backtest_window)
        st.session_state.backtest_results = bt_df

bt_df = st.session_state.backtest_results

if bt_df is not None and not bt_df.empty:
    col_bt1, col_bt2, col_bt3 = st.columns(3)
    with col_bt1:
        st.metric("Total de Testes", len(bt_df))
    with col_bt2:
        premios = bt_df["Premio"].sum()
        st.metric("Prêmios Ganhos", int(premios))
    with col_bt3:
        taxa = (premios / len(bt_df) * 100) if len(bt_df) > 0 else 0
        st.metric("Taxa de Acerto", f"{taxa:.1f}%")

    fig_bt = px.line(
        bt_df,
        x="Concurso",
        y="Acertos",
        title="Acertos por Concurso (Backtesting)",
        template=theme["plotly_template"],
        color_discrete_sequence=[theme["accent"]],
    )
    fig_bt.update_layout(height=400, xaxis_title="Concurso", yaxis_title="Acertos")
    st.plotly_chart(fig_bt, use_container_width=True, key=generate_unique_key("chart_backtest", current_lottery))

    st.dataframe(bt_df, use_container_width=True)
else:
    st.info("Clique em 'Executar Backtesting' para simular palpites contra o histórico.")

# ============================================================
# EXPORTAÇÃO EXCEL
# ============================================================
st.markdown("<div class='section-header'>📤 Exportação Excel</div>", unsafe_allow_html=True)

export_dfs = []
export_names = []

if freq_df is not None:
    export_dfs.append(freq_df.sort_values("Frequencia", ascending=False))
    export_names.append("Frequencias")

if padroes is not None:
    pi_export = pd.DataFrame(padroes["pares_impares"], columns=["Pares", "Ímpares"])
    export_dfs.append(pi_export)
    export_names.append("Pares_Impares")

    soma_export = pd.DataFrame({"Soma": padroes["somas"]})
    export_dfs.append(soma_export)
    export_names.append("Somas")

if st.session_state.last_analysis is not None:
    palpites_export = pd.DataFrame(st.session_state.last_analysis, columns=[f"D{i+1}" for i in range(cfg["num_dezenas"])])
    export_dfs.append(palpites_export)
    export_names.append("Palpites")

if bt_df is not None and not bt_df.empty:
    export_dfs.append(bt_df)
    export_names.append("Backtesting")

export_dfs.append(df.head(200))
export_names.append("Historico")

if export_dfs:
    excel_data = export_to_excel(export_dfs, export_names)
    st.download_button(
        label="📥 Baixar Relatório Excel",
        data=excel_data,
        file_name=f"relatorio_{current_lottery.replace('-', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=generate_unique_key("btn_export", current_lottery),
    )
else:
    st.info("Não há dados para exportar ainda.")

# ============================================================
# RODAPÉ
# ============================================================
st.markdown("---")
st.markdown(
    f"<div style='text-align:center;color:{theme['text']};opacity:0.6;'>"
    f"🎲 Analisador de Loterias — Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    f"</div>",
    unsafe_allow_html=True,
)
