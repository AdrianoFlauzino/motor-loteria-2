import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime, timedelta
import hashlib
import json
import re

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Lottery Analyzer Pro",
    page_icon="🎲",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CONSTANTES E CONFIGURAÇÕES DE LOTERIAS
# ============================================================
LOTTERIES = {
    "Mega-Sena": {
        "numbers": 6,
        "min": 1,
        "max": 60,
        "color": "#209869",
    },
    "Quina": {
        "numbers": 5,
        "min": 1,
        "max": 80,
        "color": "#260085",
    },
    "Lotofácil": {
        "numbers": 15,
        "min": 1,
        "max": 25,
        "color": "#930989",
    },
    "Lotomania": {
        "numbers": 20,
        "min": 1,
        "max": 100,
        "color": "#F78100",
    },
    "Dia de Sorte": {
        "numbers": 7,
        "min": 1,
        "max": 31,
        "color": "#CB8B25",
    },
    "Super Sete": {
        "numbers": 7,
        "min": 0,
        "max": 9,
        "color": "#A71D32",
    },
}

THEMES = {
    "Escuro": {
        "bg": "#0E1117",
        "card_bg": "#1E1E1E",
        "text": "#FFFFFF",
        "accent": "#00B4D8",
        "plotly_template": "plotly_dark",
    },
    "Claro": {
        "bg": "#FFFFFF",
        "card_bg": "#F0F2F6",
        "text": "#000000",
        "accent": "#0077B6",
        "plotly_template": "plotly_white",
    },
    "Azul Oceano": {
        "bg": "#001233",
        "card_bg": "#023E7D",
        "text": "#FFFFFF",
        "accent": "#00B4D8",
        "plotly_template": "plotly_dark",
    },
}

# ============================================================
# ESTADO DA SESSÃO
# ============================================================
def init_session_state():
    if "theme" not in st.session_state:
        st.session_state.theme = "Escuro"
    if "lottery" not in st.session_state:
        st.session_state.lottery = "Mega-Sena"
    if "uploaded_data" not in st.session_state:
        st.session_state.uploaded_data = None
    if "generated_bets" not in st.session_state:
        st.session_state.generated_bets = None
    if "backtest_results" not in st.session_state:
        st.session_state.backtest_results = None
    if "history_data" not in st.session_state:
        st.session_state.history_data = None

init_session_state()

# ============================================================
# FUNÇÕES UTILITÁRIAS
# ============================================================
def get_theme():
    return THEMES.get(st.session_state.theme, THEMES["Escuro"])


def apply_custom_css():
    theme = get_theme()
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {theme['bg']};
            color: {theme['text']};
        }}
        .stSidebar .sidebar-content {{
            background-color: {theme['card_bg']};
        }}
        div[data-testid="stMetric"] {{
            background-color: {theme['card_bg']};
            border-radius: 10px;
            padding: 15px;
            border: 1px solid {theme['accent']};
        }}
        .stTabs [data-baseweb="tab-list"] {{
            gap: 10px;
        }}
        .stTabs [data-baseweb="tab"] {{
            padding: 10px 20px;
            border-radius: 8px;
            background-color: {theme['card_bg']};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

apply_custom_css()


def generate_sample_data(lottery_name, num_draws=100):
    """Gera dados simulados de sorteios para a loteria selecionada."""
    cfg = LOTTERIES[lottery_name]
    draws = []
    base_date = datetime.now() - timedelta(days=num_draws * 3)
    for i in range(num_draws):
        row = {
            "Concurso": num_draws - i,
            "Data": (base_date + timedelta(days=i * 3)).strftime("%d/%m/%Y"),
        }
        numbers = sorted(np.random.choice(range(cfg["min"], cfg["max"] + 1), cfg["numbers"], replace=False))
        for j, n in enumerate(numbers):
            row[f"Bola{j+1}"] = int(n)
        draws.append(row)
    return pd.DataFrame(draws)


def parse_uploaded_file(uploaded_file):
    """Faz o parse de um arquivo CSV/Excel enviado pelo usuário."""
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(".xlsx") or uploaded_file.name.endswith(".xls"):
            df = pd.read_excel(uploaded_file)
        else:
            st.error("Formato de arquivo não suportado. Use CSV ou Excel (.xlsx).")
            return None
        return df
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")
        return None


def extract_number_columns(df, lottery_name):
    """Extrai as colunas que contêm os números sorteados."""
    cfg = LOTTERIES[lottery_name]
    number_cols = []
    for col in df.columns:
        if re.match(r"bola\d+", str(col), re.IGNORECASE) or re.match(r"dezena\d+", str(col), re.IGNORECASE):
            number_cols.append(col)
    if len(number_cols) < cfg["numbers"]:
        numeric_cols = [c for c in df.columns if df[c].dtype in [np.int64, np.float64] and c not in ["Concurso"]]
        number_cols = numeric_cols[:cfg["numbers"]]
    return number_cols[:cfg["numbers"]]


def get_history_data():
    """Retorna os dados de histórico (upload ou simulado)."""
    if st.session_state.uploaded_data is not None:
        return st.session_state.uploaded_data
    if st.session_state.history_data is None:
        st.session_state.history_data = generate_sample_data(st.session_state.lottery, 200)
    return st.session_state.history_data


def analyze_frequency(df, lottery_name):
    """Analisa a frequência de cada número."""
    cfg = LOTTERIES[lottery_name]
    number_cols = extract_number_columns(df, lottery_name)
    all_numbers = []
    for _, row in df.iterrows():
        for col in number_cols:
            val = row[col]
            if pd.notna(val):
                all_numbers.append(int(val))
    freq = pd.Series(all_numbers).value_counts().reset_index()
    freq.columns = ["Número", "Frequência"]
    freq = freq.sort_values("Número")
    full_range = pd.DataFrame({"Número": range(cfg["min"], cfg["max"] + 1)})
    freq = full_range.merge(freq, on="Número", how="left").fillna(0)
    freq["Frequência"] = freq["Frequência"].astype(int)
    return freq


def analyze_patterns(df, lottery_name):
    """Analisa padrões comportamentais nos sorteios."""
    cfg = LOTTERIES[lottery_name]
    number_cols = extract_number_columns(df, lottery_name)
    results = {
        "pares": [],
        "impares": [],
        "soma": [],
        "sequencias": [],
        "repeticao_concurso": [],
    }
    prev_numbers = None
    for _, row in df.iterrows():
        numbers = sorted([int(row[col]) for col in number_cols if pd.notna(row[col])])
        if len(numbers) < cfg["numbers"]:
            continue
        pares = sum(1 for n in numbers if n % 2 == 0)
        impares = cfg["numbers"] - pares
        soma = sum(numbers)
        seqs = 0
        for i in range(len(numbers) - 1):
            if numbers[i + 1] - numbers[i] == 1:
                seqs += 1
        results["pares"].append(pares)
        results["impares"].append(impares)
        results["soma"].append(soma)
        results["sequencias"].append(seqs)
        if prev_numbers is not None:
            rep = len(set(numbers) & set(prev_numbers))
            results["repeticao_concurso"].append(rep)
        prev_numbers = numbers
    return results


def generate_bets(df, lottery_name, num_bets=10, strategy="random"):
    """Gera apostas baseadas em diferentes estratégias."""
    cfg = LOTTERIES[lottery_name]
    freq = analyze_frequency(df, lottery_name)
    bets = []
    if strategy == "hot":
        hot_numbers = freq.nlargest(cfg["numbers"] * 3, "Frequência")["Número"].tolist()
        for _ in range(num_bets):
            bet = sorted(np.random.choice(hot_numbers, cfg["numbers"], replace=False))
            bets.append(bet)
    elif strategy == "cold":
        cold_numbers = freq.nsmallest(cfg["numbers"] * 3, "Frequência")["Número"].tolist()
        for _ in range(num_bets):
            bet = sorted(np.random.choice(cold_numbers, cfg["numbers"], replace=False))
            bets.append(bet)
    elif strategy == "mixed":
        hot = freq.nlargest(cfg["numbers"], "Frequência")["Número"].tolist()
        cold = freq.nsmallest(cfg["numbers"], "Frequência")["Número"].tolist()
        pool = hot[:cfg["numbers"] // 2] + cold[:cfg["numbers"] // 2 + cfg["numbers"] % 2]
        for _ in range(num_bets):
            bet = sorted(np.random.choice(pool, cfg["numbers"], replace=False))
            bets.append(bet)
    else:
        for _ in range(num_bets):
            bet = sorted(np.random.choice(range(cfg["min"], cfg["max"] + 1), cfg["numbers"], replace=False))
            bets.append(bet)
    bet_rows = []
    for i, bet in enumerate(bets):
        row = {"Aposta": i + 1}
        for j, n in enumerate(bet):
            row[f"Bola{j+1}"] = int(n)
        row["Estratégia"] = strategy
        bet_rows.append(row)
    return pd.DataFrame(bet_rows)


def run_backtest(df, lottery_name, strategy="random", num_bets=10, window=50):
    """Executa backtesting da estratégia escolhida."""
    cfg = LOTTERIES[lottery_name]
    number_cols = extract_number_columns(df, lottery_name)
    results = []
    total_draws = len(df)
    if total_draws < window + 10:
        window = max(10, total_draws // 3)
    for start in range(0, total_draws - window, max(1, window // 4)):
        train_df = df.iloc[start:start + window]
        test_df = df.iloc[start + window:start + window + 1]
        if test_df.empty:
            continue
        bets_df = generate_bets(train_df, lottery_name, num_bets=num_bets, strategy=strategy)
        bet_cols = [c for c in bets_df.columns if c.startswith("Bola")]
        test_numbers = set()
        for _, row in test_df.iterrows():
            for col in number_cols:
                if pd.notna(row[col]):
                    test_numbers.add(int(row[col]))
        hits = []
        for _, bet_row in bets_df.iterrows():
            bet_numbers = set(int(bet_row[c]) for c in bet_cols)
            match_count = len(bet_numbers & test_numbers)
            hits.append(match_count)
        results.append({
            "Concurso": int(test_df.iloc[0].get("Concurso", start + window)),
            "Acertos_Máx": max(hits),
            "Acertos_Méd": round(np.mean(hits), 2),
            "Acertos_Min": min(hits),
            "Estratégia": strategy,
        })
    return pd.DataFrame(results)


def export_to_excel(df_dict):
    """Exporta DataFrames para um arquivo Excel em memória."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, df in df_dict.items():
            safe_name = sheet_name[:31]
            df.to_excel(writer, sheet_name=safe_name, index=False)
    output.seek(0)
    return output


def make_key(prefix, *parts):
    """Gera uma chave única e determinística para widgets Streamlit."""
    raw = f"{prefix}_{'_'.join(str(p) for p in parts)}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.title("🎲 Lottery Analyzer Pro")
    st.markdown("---")

    st.subheader("⚙️ Configurações")
    st.session_state.lottery = st.selectbox(
        "Loteria",
        list(LOTTERIES.keys()),
        index=list(LOTTERIES.keys()).index(st.session_state.lottery),
        key="sidebar_lottery_select",
    )

    st.session_state.theme = st.selectbox(
        "Tema",
        list(THEMES.keys()),
        index=list(THEMES.keys()).index(st.session_state.theme),
        key="sidebar_theme_select",
    )

    st.markdown("---")
    st.subheader("📁 Upload de Arquivos")
    uploaded_file = st.file_uploader(
        "Carregar histórico de sorteios (CSV/Excel)",
        type=["csv", "xlsx", "xls"],
        key="sidebar_file_uploader",
    )
    if uploaded_file is not None:
        parsed = parse_uploaded_file(uploaded_file)
        if parsed is not None:
            st.session_state.uploaded_data = parsed
            st.success(f"Arquivo carregado: {len(parsed)} registros")
    else:
        if st.button("🗑️ Limpar upload e usar dados simulados", key="sidebar_clear_upload"):
            st.session_state.uploaded_data = None
            st.session_state.history_data = None
            st.rerun()

    st.markdown("---")
    cfg = LOTTERIES[st.session_state.lottery]
    st.info(
        f"**{st.session_state.lottery}**\n\n"
        f"• Números por aposta: {cfg['numbers']}\n"
        f"• Faixa: {cfg['min']} a {cfg['max']}"
    )

# ============================================================
# CONTEÚDO PRINCIPAL
# ============================================================
theme = get_theme()
plotly_template = theme["plotly_template"]
lottery_name = st.session_state.lottery
cfg = LOTTERIES[lottery_name]

df_history = get_history_data()

st.title(f"📊 Análise — {lottery_name}")
st.markdown(f"Dados de histórico: **{len(df_history)}** sorteios")

# ============================================================
# ABAS
# ============================================================
tab_overview, tab_freq, tab_patterns, tab_generator, tab_backtest, tab_export = st.tabs([
    "📋 Visão Geral",
    "📈 Frequências",
    "🧩 Padrões Comportamentais",
    "🎰 Gerador de Apostas",
    "🔬 Backtesting",
    "📤 Exportação Excel",
])

# --------------------------------------------------------------
# ABA: Visão Geral
# --------------------------------------------------------------
with tab_overview:
    st.subheader("Resumo dos Dados")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total de Sorteios", len(df_history))
    with col2:
        st.metric("Números por Sorteio", cfg["numbers"])
    with col3:
        st.metric("Faixa", f"{cfg['min']}–{cfg['max']}")
    with col4:
        st.metric("Tema Atual", st.session_state.theme)

    st.markdown("---")
    st.subheader("Prévia dos Dados")
    st.dataframe(
        df_history.head(20),
        use_container_width=True,
        hide_index=True,
        key="df_overview_preview",
    )

    st.markdown("---")
    st.subheader("Evolução da Soma dos Números")
    number_cols = extract_number_columns(df_history, lottery_name)
    if number_cols:
        soma_series = df_history[number_cols].sum(axis=1)
        fig_soma = go.Figure()
        fig_soma.add_trace(go.Scatter(
            y=soma_series.values,
            mode="lines+markers",
            name="Soma",
            line=dict(color=theme["accent"], width=2),
        ))
        fig_soma.update_layout(template=plotly_template, title="Soma dos Números por Sorteio")
        st.plotly_chart(fig_soma, use_container_width=True, key="chart_overview_soma")

# --------------------------------------------------------------
# ABA: Frequências
# --------------------------------------------------------------
with tab_freq:
    st.subheader("Frequência de Números Sorteados")
    freq_df = analyze_frequency(df_history, lottery_name)

    col_f1, col_f2 = st.columns([3, 2])
    with col_f1:
        fig_freq = px.bar(
            freq_df,
            x="Número",
            y="Frequência",
            template=plotly_template,
            color="Frequência",
            color_continuous_scale=[theme["accent"], cfg["color"]],
            title=f"Frequência — {lottery_name}",
        )
        st.plotly_chart(fig_freq, use_container_width=True, key="chart_freq_bar")

    with col_f2:
        st.markdown("**Top 10 Mais Sorteados**")
        top_hot = freq_df.nlargest(10, "Frequência")
        st.dataframe(
            top_hot,
            use_container_width=True,
            hide_index=True,
            key="df_freq_top_hot",
        )
        st.markdown("**Top 10 Menos Sorteados**")
        top_cold = freq_df.nsmallest(10, "Frequência")
        st.dataframe(
            top_cold,
            use_container_width=True,
            hide_index=True,
            key="df_freq_top_cold",
        )

    st.markdown("---")
    st.subheader("Mapa de Calor de Frequência")
    heat_data = freq_df.set_index("Número")["Frequência"].values.reshape(1, -1)
    fig_heat = go.Figure(data=go.Heatmap(
        z=heat_data,
        x=freq_df["Número"].tolist(),
        colorscale=[[0, "#1a1a2e"], [1, theme["accent"]]],
        showscale=True,
    ))
    fig_heat.update_layout(template=plotly_template, title="Mapa de Calor", height=250)
    st.plotly_chart(fig_heat, use_container_width=True, key="chart_freq_heatmap")

# --------------------------------------------------------------
# ABA: Padrões Comportamentais
# --------------------------------------------------------------
with tab_patterns:
    st.subheader("Análise de Padrões Comportamentais")
    patterns = analyze_patterns(df_history, lottery_name)

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown("**Distribuição Pares vs Ímpares**")
        pares_impares_df = pd.DataFrame({
            "Pares": patterns["pares"],
            "Ímpares": patterns["impares"],
        })
        fig_pi = px.histogram(
            pares_impares_df.melt(var_name="Tipo", value_name="Quantidade"),
            x="Quantidade",
            color="Tipo",
            barmode="group",
            template=plotly_template,
            title="Pares vs Ímpares",
        )
        st.plotly_chart(fig_pi, use_container_width=True, key="chart_patterns_pares_impares")

    with col_p2:
        st.markdown("**Distribuição da Soma**")
        soma_df = pd.DataFrame({"Soma": patterns["soma"]})
        fig_soma = px.histogram(
            soma_df,
            x="Soma",
            template=plotly_template,
            title="Distribuição da Soma",
            color_discrete_sequence=[theme["accent"]],
        )
        st.plotly_chart(fig_soma, use_container_width=True, key="chart_patterns_soma")

    st.markdown("---")
    col_p3, col_p4 = st.columns(2)
    with col_p3:
        st.markdown("**Sequências Consecutivas por Sorteio**")
        seq_df = pd.DataFrame({"Sequências": patterns["sequencias"]})
        fig_seq = px.histogram(
            seq_df,
            x="Sequências",
            template=plotly_template,
            title="Sequências Consecutivas",
            color_discrete_sequence=[cfg["color"]],
        )
        st.plotly_chart(fig_seq, use_container_width=True, key="chart_patterns_sequencias")

    with col_p4:
        st.markdown("**Repetição entre Concursos Seguintes**")
        rep_df = pd.DataFrame({"Repetições": patterns["repeticao_concurso"]})
        fig_rep = px.histogram(
            rep_df,
            x="Repetições",
            template=plotly_template,
            title="Repetição vs Concurso Anterior",
            color_discrete_sequence=[theme["accent"]],
        )
        st.plotly_chart(fig_rep, use_container_width=True, key="chart_patterns_repeticao")

    st.markdown("---")
    st.subheader("Tabela Resumo de Padrões")
    summary_data = {
        "Métrica": ["Pares (média)", "Ímpares (média)", "Soma (média)", "Soma (mín)", "Soma (máx)", "Sequências (média)", "Repetição (média)"],
        "Valor": [
            round(np.mean(patterns["pares"]), 2),
            round(np.mean(patterns["impares"]), 2),
            round(np.mean(patterns["soma"]), 2),
            int(np.min(patterns["soma"])),
            int(np.max(patterns["soma"])),
            round(np.mean(patterns["sequencias"]), 2),
            round(np.mean(patterns["repeticao_concurso"]), 2) if patterns["repeticao_concurso"] else 0,
        ],
    }
    st.dataframe(
        pd.DataFrame(summary_data),
        use_container_width=True,
        hide_index=True,
        key="df_patterns_summary",
    )

# --------------------------------------------------------------
# ABA: Gerador de Apostas
# --------------------------------------------------------------
with tab_generator:
    st.subheader("🎰 Gerador de Apostas")

    col_g1, col_g2, col_g3 = st.columns(3)
    with col_g1:
        strategy = st.selectbox(
            "Estratégia",
            ["random", "hot", "cold", "mixed"],
            format_func=lambda x: {"random": "Aleatória", "hot": "Números Quentes", "cold": "Números Frios", "mixed": "Mista"}[x],
            key="generator_strategy_select",
        )
    with col_g2:
        num_bets = st.number_input("Número de Apostas", min_value=1, max_value=100, value=10, step=1, key="generator_num_bets")
    with col_g3:
        generate_btn = st.button("🎲 Gerar Apostas", key="generator_btn", use_container_width=True)

    if generate_btn or st.session_state.generated_bets is not None:
        if generate_btn:
            st.session_state.generated_bets = generate_bets(
                df_history, lottery_name, num_bets=int(num_bets), strategy=strategy
            )

        if st.session_state.generated_bets is not None:
            bets_df = st.session_state.generated_bets
            st.markdown(f"**{len(bets_df)} apostas geradas — Estratégia: {strategy}**")

            st.dataframe(
                bets_df,
                use_container_width=True,
                hide_index=True,
                key="df_generator_bets",
            )

            st.markdown("---")
            st.subheader("Distribuição dos Números Gerados")
            bet_cols = [c for c in bets_df.columns if c.startswith("Bola")]
            all_bet_numbers = []
            for _, row in bets_df.iterrows():
                for c in bet_cols:
                    all_bet_numbers.append(int(row[c]))
            bet_freq = pd.Series(all_bet_numbers).value_counts().reset_index()
            bet_freq.columns = ["Número", "Frequência"]
            bet_freq = bet_freq.sort_values("Número")

            fig_bet_dist = px.bar(
                bet_freq,
                x="Número",
                y="Frequência",
                template=plotly_template,
                color="Frequência",
                color_continuous_scale=[theme["accent"], cfg["color"]],
                title="Distribuição nas Apostas Geradas",
            )
            st.plotly_chart(fig_bet_dist, use_container_width=True, key="chart_generator_bet_dist")

            st.markdown("---")
            st.subheader("Soma de Cada Aposta")
            soma_bets = bets_df[bet_cols].sum(axis=1)
            fig_bet_soma = go.Figure()
            fig_bet_soma.add_trace(go.Bar(
                x=list(range(1, len(soma_bets) + 1)),
                y=soma_bets.values,
                marker_color=theme["accent"],
                name="Soma",
            ))
            fig_bet_soma.update_layout(template=plotly_template, title="Soma por Aposta", xaxis_title="Aposta", yaxis_title="Soma")
            st.plotly_chart(fig_bet_soma, use_container_width=True, key="chart_generator_bet_soma")

# --------------------------------------------------------------
# ABA: Backtesting
# --------------------------------------------------------------
with tab_backtest:
    st.subheader("🔬 Backtesting de Estratégias")

    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        bt_strategy = st.selectbox(
            "Estratégia para Backtest",
            ["random", "hot", "cold", "mixed"],
            format_func=lambda x: {"random": "Aleatória", "hot": "Números Quentes", "cold": "Números Frios", "mixed": "Mista"}[x],
            key="backtest_strategy_select",
        )
    with col_b2:
        bt_num_bets = st.number_input("Apostas por Teste", min_value=1, max_value=50, value=10, step=1, key="backtest_num_bets")
    with col_b3:
        bt_window = st.number_input("Janela de Treino", min_value=10, max_value=200, value=50, step=10, key="backtest_window")

    bt_btn = st.button("▶️ Executar Backtesting", key="backtest_btn", use_container_width=True)

    if bt_btn or st.session_state.backtest_results is not None:
        if bt_btn:
            with st.spinner("Executando backtesting..."):
                st.session_state.backtest_results = run_backtest(
                    df_history, lottery_name, strategy=bt_strategy, num_bets=int(bt_num_bets), window=int(bt_window)
                )

        if st.session_state.backtest_results is not None and not st.session_state.backtest_results.empty:
            bt_df = st.session_state.backtest_results

            col_bt1, col_bt2, col_bt3 = st.columns(3)
            with col_bt1:
                st.metric("Acerto Máximo (geral)", int(bt_df["Acertos_Máx"].max()))
            with col_bt2:
                st.metric("Acerto Médio (geral)", round(bt_df["Acertos_Méd"].mean(), 2))
            with col_bt3:
                st.metric("Testes Executados", len(bt_df))

            st.markdown("---")
            st.subheader("Evolução dos Acertos")
            fig_bt = go.Figure()
            fig_bt.add_trace(go.Scatter(
                x=bt_df["Concurso"],
                y=bt_df["Acertos_Máx"],
                mode="lines+markers",
                name="Acerto Máx",
                line=dict(color=theme["accent"], width=2),
            ))
            fig_bt.add_trace(go.Scatter(
                x=bt_df["Concurso"],
                y=bt_df["Acertos_Méd"],
                mode="lines+markers",
                name="Acerto Médio",
                line=dict(color=cfg["color"], width=2, dash="dash"),
            ))
            fig_bt.add_trace(go.Scatter(
                x=bt_df["Concurso"],
                y=bt_df["Acertos_Min"],
                mode="lines+markers",
                name="Acerto Mín",
                line=dict(color="#FF6B6B", width=1, dash="dot"),
            ))
            fig_bt.update_layout(template=plotly_template, title="Evolução de Acertos no Backtesting", xaxis_title="Concurso", yaxis_title="Acertos")
            st.plotly_chart(fig_bt, use_container_width=True, key="chart_backtest_results")

            st.markdown("---")
            st.subheader("Distribuição de Acertos")
            fig_bt_dist = px.histogram(
                bt_df.melt(id_vars=["Concurso"], value_vars=["Acertos_Máx", "Acertos_Méd", "Acertos_Min"], var_name="Tipo", value_name="Acertos"),
                x="Acertos",
                color="Tipo",
                barmode="group",
                template=plotly_template,
                title="Distribuição de Acertos",
            )
            st.plotly_chart(fig_bt_dist, use_container_width=True, key="chart_backtest_dist")

            st.markdown("---")
            st.subheader("Detalhe do Backtesting")
            st.dataframe(
                bt_df,
                use_container_width=True,
                hide_index=True,
                key="df_backtest_detail",
            )

            st.markdown("---")
            st.subheader("Acertos por Estratégia")
            strategy_summary = bt_df.groupby("Estratégia").agg(
                Acerto_Máx=("Acertos_Máx", "max"),
                Acerto_Méd=("Acertos_Méd", "mean"),
                Acerto_Min=("Acertos_Min", "min"),
            ).reset_index()
            st.dataframe(
                strategy_summary,
                use_container_width=True,
                hide_index=True,
                key="df_backtest_strategy_summary",
            )
        else:
            st.info("Nenhum resultado de backtesting disponível. Clique em 'Executar Backtesting'.")

# --------------------------------------------------------------
# ABA: Exportação Excel
# --------------------------------------------------------------
with tab_export:
    st.subheader("📤 Exportação para Excel")
    st.markdown("Selecione os dados que deseja exportar:")

    export_options = {
        "Histórico": df_history,
        "Frequências": analyze_frequency(df_history, lottery_name),
    }

    if st.session_state.generated_bets is not None:
        export_options["Apostas Geradas"] = st.session_state.generated_bets
    if st.session_state.backtest_results is not None and not st.session_state.backtest_results.empty:
        export_options["Backtesting"] = st.session_state.backtest_results

    selected_sheets = st.multiselect(
        "Planilhas para exportar",
        list(export_options.keys()),
        default=list(export_options.keys()),
        key="export_sheets_multiselect",
    )

    if st.button("📥 Gerar Excel", key="export_btn", use_container_width=True):
        if selected_sheets:
            df_dict = {name: export_options[name] for name in selected_sheets}
            excel_data = export_to_excel(df_dict)
            st.download_button(
                label="⬇️ Baixar arquivo Excel",
                data=excel_data,
                file_name=f"lottery_analysis_{lottery_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="export_download_btn",
            )
            st.success("Arquivo gerado! Clique no botão acima para baixar.")
        else:
            st.warning("Selecione ao menos uma planilha para exportar.")

    st.markdown("---")
    st.subheader("Prévia dos Dados Selecionados")
    if selected_sheets:
        for sheet in selected_sheets:
            st.markdown(f"**{sheet}**")
            preview_key = make_key("df_export_preview", sheet)
            st.dataframe(
                export_options[sheet].head(15),
                use_container_width=True,
                hide_index=True,
                key=f"df_export_preview_{preview_key}",
            )
    else:
        st.info("Nenhuma planilha selecionada.")

# ============================================================
# RODAPÉ
# ============================================================
st.markdown("---")
st.caption(f"Lottery Analyzer Pro — {datetime.now().year} | Tema: {st.session_state.theme} | Loteria: {lottery_name}")
