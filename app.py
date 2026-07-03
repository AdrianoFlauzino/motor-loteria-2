import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import hashlib

# ============================================================
# CONFIGURAÇÃO DA PÁGINA E TEMA (ÚNICA VEZ)
# ============================================================
st.set_page_config(
    page_title="Análise de Loterias",
    page_icon="🎲",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Tema base definido uma única vez
THEME_PRIMARY = "#1f77b4"
THEME_SECONDARY = "#ff7f0e"
THEME_BG = "#0e1117"
THEME_CARD = "#161b22"
THEME_TEXT = "#e6edf3"

# Injeção de CSS UMA ÚNICA VEZ (após definição do tema)
st.markdown(
    f"""
    <style>
        .stApp {{
            background-color: {THEME_BG};
            color: {THEME_TEXT};
        }}
        .main .block-container {{
            padding-top: 1.5rem;
            max-width: 1200px;
        }}
        h1, h2, h3, h4 {{
            color: {THEME_TEXT};
        }}
        .stMetric {{
            background-color: {THEME_CARD};
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 12px 16px;
        }}
        .stMetric label {{
            color: #8b949e !important;
        }}
        .stMetricValue {{
            color: {THEME_TEXT} !important;
        }}
        .stButton > button, .stDownloadButton > button {{
            background-color: {THEME_PRIMARY};
            color: white;
            border: none;
            border-radius: 6px;
        }}
        .stButton > button:hover, .stDownloadButton > button:hover {{
            background-color: {THEME_SECONDARY};
            color: white;
        }}
        .stSelectbox label, .stFileUploader label, .stSlider label, .stNumberInput label {{
            color: #c9d1d9 !important;
        }}
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
        }}
        .stTabs [data-baseweb="tab"] {{
            background-color: {THEME_CARD};
            border-radius: 6px 6px 0 0;
            color: {THEME_TEXT};
        }}
        .stTabs [aria-selected="true"] {{
            background-color: {THEME_PRIMARY};
            color: white !important;
        }}
        div[data-testid="stSidebar"] {{
            background-color: {THEME_CARD};
        }}
        .pattern-card {{
            background-color: {THEME_CARD};
            border-left: 4px solid {THEME_PRIMARY};
            padding: 10px 14px;
            border-radius: 6px;
            margin-bottom: 8px;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# CONFIGURAÇÃO DAS LOTERIAS
# ============================================================
LOTTERIES = {
    "Mega-Sena": {
        "dezenas": 6,
        "min": 1,
        "max": 60,
        "colunas": ["bola1", "bola2", "bola3", "bola4", "bola5", "bola6"],
    },
    "Quina": {
        "dezenas": 5,
        "min": 1,
        "max": 80,
        "colunas": ["bola1", "bola2", "bola3", "bola4", "bola5"],
    },
    "Lotofácil": {
        "dezenas": 15,
        "min": 1,
        "max": 25,
        "colunas": [f"bola{i}" for i in range(1, 16)],
    },
    "Lotomania": {
        "dezenas": 20,
        "min": 1,
        "max": 100,
        "colunas": [f"bola{i}" for i in range(1, 21)],
    },
}

# ============================================================
# FUNÇÕES UTILITÁRIAS
# ============================================================
@st.cache_data(show_spinner=False)
def gerar_dados_sinteticos(loteria: str, n_concursos: int = 500) -> pd.DataFrame:
    """Gera dados sintéticos quando não há upload."""
    cfg = LOTTERIES[loteria]
    rng = np.random.default_rng(seed=42)
    dados = []
    for concurso in range(1, n_concursos + 1):
        dezenas = sorted(rng.choice(range(cfg["min"], cfg["max"] + 1), size=cfg["dezenas"], replace=False))
        row = {"concurso": concurso, "data_sorteio": pd.Timestamp("2020-01-01") + pd.Timedelta(days=concurso * 7)}
        for i, d in enumerate(dezenas):
            row[cfg["colunas"][i]] = int(d)
        dados.append(row)
    return pd.DataFrame(dados)


def normalizar_dataframe(df: pd.DataFrame, loteria: str) -> pd.DataFrame:
    """Garante que o DataFrame tenha as colunas esperadas."""
    cfg = LOTTERIES[loteria]
    colunas_esperadas = cfg["colunas"]
    # Tenta encontrar colunas de bolas mesmo com nomes diferentes
    if not all(c in df.columns for c in colunas_esperadas):
        # Procura colunas numéricas extras
        candidatas = [c for c in df.columns if c not in ("concurso", "data_sorteio")]
        if len(candidatas) >= cfg["dezenas"]:
            df = df.rename(columns={candidatas[i]: colunas_esperadas[i] for i in range(cfg["dezenas"])})
    for c in colunas_esperadas:
        if c not in df.columns:
            df[c] = np.nan
    if "concurso" not in df.columns:
        df["concurso"] = range(1, len(df) + 1)
    return df


def extrair_dezenas(df: pd.DataFrame, loteria: str) -> pd.DataFrame:
    """Retorna DataFrame apenas com as colunas de dezenas."""
    cfg = LOTTERIES[loteria]
    return df[cfg["colunas"]].copy()


def calcular_frequencia(df: pd.DataFrame, loteria: str) -> pd.DataFrame:
    """Calcula frequência de cada dezena."""
    dezenas_df = extrair_dezenas(df, loteria)
    todos = dezenas_df.values.flatten()
    todos = todos[~pd.isna(todos)]
    contagem = pd.Series(todos).value_counts().reset_index()
    contagem.columns = ["dezena", "frequencia"]
    contagem["dezena"] = contagem["dezena"].astype(int)
    contagem = contagem.sort_values("dezena").reset_index(drop=True)
    contagem["percentual"] = (contagem["frequencia"] / contagem["frequencia"].sum() * 100).round(2)
    return contagem


def detectar_padroes(df: pd.DataFrame, loteria: str) -> dict:
    """Detecta padrões nas dezenas sorteadas."""
    dezenas_df = extrair_dezenas(df, loteria)
    padroes = {
        "pares": 0,
        "impares": 0,
        "soma_media": 0.0,
        "soma_min": 0,
        "soma_max": 0,
        "sequencias": 0,
        "repeticoes_consecutivas": 0,
        "top_combinacoes": [],
    }
    todas_somas = []
    concursos_anteriores = None
    for _, row in dezenas_df.iterrows():
        vals = row.dropna().astype(int).tolist()
        if len(vals) == 0:
            continue
        pares = sum(1 for v in vals if v % 2 == 0)
        impares = len(vals) - pares
        padroes["pares"] += pares
        padroes["impares"] += impares
        soma = sum(vals)
        todas_somas.append(soma)
        # Sequências consecutivas dentro do concurso
        ordenados = sorted(vals)
        for i in range(len(ordenados) - 1):
            if ordenados[i + 1] - ordenados[i] == 1:
                padroes["sequencias"] += 1
        # Repetição em relação ao concurso anterior
        if concursos_anteriores is not None:
            repetidas = set(vals) & set(concursos_anteriores)
            padroes["repeticoes_consecutivas"] += len(repetidas)
        concursos_anteriores = vals
    if todas_somas:
        padroes["soma_media"] = round(np.mean(todas_somas), 2)
        padroes["soma_min"] = int(min(todas_somas))
        padroes["soma_max"] = int(max(todas_somas))
    # Top combinações de pares
    combinacoes = []
    for _, row in dezenas_df.iterrows():
        vals = tuple(sorted(row.dropna().astype(int).tolist()))
        if len(vals) == LOTTERIES[loteria]["dezenas"]:
            combinacoes.append(vals)
    if combinacoes:
        serie_comb = pd.Series(combinacoes)
        top = serie_comb.value_counts().head(5)
        padroes["top_combinacoes"] = [(list(k), int(v)) for k, v in top.items()]
    return padroes


def backtesting(df: pd.DataFrame, loteria: str, janela: int = 50) -> pd.DataFrame:
    """Simula backtesting: usa frequência dos últimos N concursos para prever próximos."""
    cfg = LOTTERIES[loteria]
    dezenas_df = extrair_dezenas(df, loteria)
    resultados = []
    for i in range(janela, len(df)):
        historico = dezenas_df.iloc[i - janela:i]
        todos = historico.values.flatten()
        todos = todos[~pd.isna(todos)]
        freq = pd.Series(todos).value_counts()
        # Top dezenas mais frequentes
        top_dezenas = freq.head(cfg["dezenas"]).index.tolist()
        top_dezenas = sorted([int(d) for d in top_dezenas])
        # Concurso atual (real)
        atual = sorted(dezenas_df.iloc[i].dropna().astype(int).tolist())
        acertos = len(set(top_dezenas) & set(atual))
        resultados.append({
            "concurso": int(df.iloc[i]["concurso"]) if "concurso" in df.columns else i,
            "acertos": acertos,
            "previstas": str(top_dezenas),
            "sorteadas": str(atual),
        })
    return pd.DataFrame(resultados)


def exportar_excel(df: pd.DataFrame) -> bytes:
    """Exporta DataFrame para Excel em memória."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Resultado")
    return output.getvalue()


def exportar_csv(df: pd.DataFrame) -> bytes:
    """Exporta DataFrame para CSV."""
    return df.to_csv(index=False).encode("utf-8")


def file_hash(uploaded_file) -> str:
    """Calcula hash do arquivo para detectar mudanças."""
    if uploaded_file is None:
        return ""
    uploaded_file.seek(0)
    content = uploaded_file.read()
    uploaded_file.seek(0)
    return hashlib.md5(content).hexdigest()


# ============================================================
# ESTADO DA SESSÃO
# ============================================================
if "lottery" not in st.session_state:
    st.session_state["lottery"] = "Mega-Sena"
if "uploaded_hash" not in st.session_state:
    st.session_state["uploaded_hash"] = ""
if "df_cache" not in st.session_state:
    st.session_state["df_cache"] = None
if "backtest_window" not in st.session_state:
    st.session_state["backtest_window"] = 50

# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.title("🎲 Análise de Loterias")

# CORREÇÃO 1: selectbox apenas com key, sem dupla atribuição
st.sidebar.markdown("### Selecione a Loteria")
opcoes_loteria = list(LOTTERIES.keys())
st.sidebar.selectbox("Loteria", opcoes_loteria, key="lottery")

loteria_selecionada = st.session_state["lottery"]
cfg_loteria = LOTTERIES[loteria_selecionada]

st.sidebar.markdown("---")
st.sidebar.markdown("### Upload de Planilha")
st.sidebar.caption(f"Colunas esperadas: {', '.join(cfg_loteria['colunas'][:3])}...")

# CORREÇÃO 4: processa apenas se for arquivo novo
uploaded_file = st.sidebar.file_uploader(
    "Envie sua planilha (.xlsx, .csv)",
    type=["xlsx", "xls", "csv"],
    key="file_uploader",
)

current_hash = file_hash(uploaded_file)
if uploaded_file is not None and current_hash != st.session_state["uploaded_hash"]:
    with st.spinner("Processando planilha..."):
        try:
            if uploaded_file.name.endswith(".csv"):
                df_upload = pd.read_csv(uploaded_file)
            else:
                df_upload = pd.read_excel(uploaded_file)
            df_upload = normalizar_dataframe(df_upload, loteria_selecionada)
            st.session_state["df_cache"] = df_upload
            st.session_state["uploaded_hash"] = current_hash
            st.sidebar.success(f"✅ Arquivo carregado: {len(df_upload)} concursos")
        except Exception as e:
            st.sidebar.error(f"❌ Erro ao processar: {e}")
            st.session_state["df_cache"] = None
            st.session_state["uploaded_hash"] = current_hash
elif uploaded_file is None and st.session_state["df_cache"] is not None:
    # Arquivo removido
    st.session_state["df_cache"] = None
    st.session_state["uploaded_hash"] = ""

st.sidebar.markdown("---")
st.sidebar.markdown("### Backtesting")
st.sidebar.slider(
    "Janela de análise (concursos)",
    min_value=10,
    max_value=200,
    value=50,
    step=10,
    key="backtest_window",
)

st.sidebar.markdown("---")
st.sidebar.info(
    f"**{loteria_selecionada}**\n\n"
    f"Dezenas por concurso: {cfg_loteria['dezenas']}\n\n"
    f"Faixa: {cfg_loteria['min']} a {cfg_loteria['max']}"
)

# ============================================================
# CARREGAMENTO DE DADOS
# ============================================================
if st.session_state["df_cache"] is not None:
    df = st.session_state["df_cache"]
    fonte = "Upload"
else:
    df = gerar_dados_sinteticos(loteria_selecionia if False else loteria_selecionada, n_concursos=500)
    fonte = "Dados sintéticos"

# ============================================================
# HEADER
# ============================================================
st.title(f"📊 Análise — {loteria_selecionada}")
st.caption(f"Fonte dos dados: {fonte} | Total de concursos: {len(df)}")

# ============================================================
# MÉTRICAS PRINCIPAIS
# ============================================================
freq = calcular_frequencia(df, loteria_selecionada)
padroes = detectar_padroes(df, loteria_selecionada)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Concursos analisados", len(df))
with col2:
    st.metric("Dezena mais frequente", int(freq.iloc[freq["frequencia"].idxmax()]["dezena"]))
with col3:
    st.metric("Dezena menos frequente", int(freq.iloc[freq["frequencia"].idxmin()]["dezena"]))
with col4:
    st.metric("Soma média (dezenas)", padroes["soma_media"])

st.markdown("---")

# ============================================================
# TABS
# ============================================================
tab_freq, tab_padroes, tab_backtest, tab_export = st.tabs([
    "📈 Frequência",
    "🎯 Padrões",
    "🔬 Backtesting",
    "💾 Exportação",
])

# ----------------------------------------------------------
# TAB: FREQUÊNCIA
# ----------------------------------------------------------
with tab_freq:
    st.subheader("Frequência das Dezenas")

    col_a, col_b = st.columns([2, 1])

    with col_a:
        # CORREÇÃO 2: px.bar com dados pré-agregados via value_counts
        freq_ordenada = freq.sort_values("frequencia", ascending=False).head(20)
        fig_bar = px.bar(
            freq_ordenada,
            x="dezena",
            y="frequencia",
            title="Top 20 Dezenas Mais Frequentes",
            color="frequencia",
            color_continuous_scale="Blues",
            labels={"dezena": "Dezena", "frequencia": "Frequência"},
        )
        fig_bar.update_layout(
            template="plotly_dark",
            paper_bgcolor=THEME_BG,
            plot_bgcolor=THEME_BG,
            font=dict(color=THEME_TEXT),
        )
        fig_bar.update_traces(texttemplate="%{y}", textposition="outside")
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_b:
        st.markdown("#### Distribuição Par/Ímpar")
        par_impar = pd.DataFrame({
            "tipo": ["Pares", "Ímpares"],
            "quantidade": [padroes["pares"], padroes["impares"]],
        })
        fig_pi = px.bar(
            par_impar,
            x="tipo",
            y="quantidade",
            color="tipo",
            color_discrete_map={"Pares": THEME_PRIMARY, "Ímpares": THEME_SECONDARY},
            labels={"tipo": "", "quantidade": "Quantidade"},
        )
        fig_pi.update_layout(
            template="plotly_dark",
            paper_bgcolor=THEME_BG,
            plot_bgcolor=THEME_BG,
            font=dict(color=THEME_TEXT),
            showlegend=False,
        )
        st.plotly_chart(fig_pi, use_container_width=True)

    st.markdown("#### Tabela Completa de Frequência")
    st.dataframe(
        freq.sort_values("frequencia", ascending=False),
        use_container_width=True,
        height=400,
    )

# ----------------------------------------------------------
# TAB: PADRÕES
# ----------------------------------------------------------
with tab_padroes:
    st.subheader("Padrões Identificados")

    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        st.metric("Soma mínima", padroes["soma_min"])
    with pc2:
        st.metric("Soma máxima", padroes["soma_max"])
    with pc3:
        st.metric("Sequências consecutivas", padroes["sequencias"])

    st.markdown("#### Distribuição da Soma das Dezenas")
    dezenas_df = extrair_dezenas(df, loteria_selecionada)
    somas = dezenas_df.sum(axis=1).dropna().astype(int)
    # CORREÇÃO 2: agregar com value_counts antes do px.bar
    soma_dist = somas.value_counts().reset_index()
    soma_dist.columns = ["soma", "frequencia"]
    soma_dist = soma_dist.sort_values("soma")

    fig_soma = px.bar(
        soma_dist,
        x="soma",
        y="frequencia",
        title="Distribuição da Soma por Concurso",
        labels={"soma": "Soma das Dezenas", "frequencia": "Frequência"},
        color="frequencia",
        color_continuous_scale="Viridis",
    )
    fig_soma.update_layout(
        template="plotly_dark",
        paper_bgcolor=THEME_BG,
        plot_bgcolor=THEME_BG,
        font=dict(color=THEME_TEXT),
    )
    st.plotly_chart(fig_soma, use_container_width=True)

    st.markdown("#### Repetições entre Concursos Consecutivos")
    rep_data = pd.DataFrame({
        "categoria": ["Repetições totais", "Concursos analisados"],
        "valor": [padroes["repeticoes_consecutivas"], len(df) - 1],
    })
    fig_rep = px.bar(
        rep_data,
        x="categoria",
        y="valor",
        color="categoria",
        color_discrete_sequence=[THEME_PRIMARY, THEME_SECONDARY],
        labels={"categoria": "", "valor": "Quantidade"},
    )
    fig_rep.update_layout(
        template="plotly_dark",
        paper_bgcolor=THEME_BG,
        plot_bgcolor=THEME_BG,
        font=dict(color=THEME_TEXT),
        showlegend=False,
    )
    st.plotly_chart(fig_rep, use_container_width=True)

    st.markdown("#### Top 5 Combinações Mais Sorteadas")
    if padroes["top_combinacoes"]:
        for combinacao, count in padroes["top_combinacoes"]:
            st.markdown(
                f'<div class="pattern-card">'
                f'<strong>Combinação:</strong> {combinacao} — '
                f'<strong>Ocorrências:</strong> {count}'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("Nenhuma combinação repetida encontrada.")

# ----------------------------------------------------------
# TAB: BACKTESTING
# ----------------------------------------------------------
with tab_backtest:
    st.subheader("🔬 Backtesting de Estratégia")
    st.caption(
        "A estratégia utiliza as dezenas mais frequentes dos últimos N concursos "
        "para prever o próximo sorteio e compara com o resultado real."
    )

    janela = st.session_state["backtest_window"]

    if len(df) <= janela:
        st.warning(f"São necessários mais de {janela} concursos para o backtesting. Total atual: {len(df)}.")
    else:
        bt = backtesting(df, loteria_selecionada, janela=janela)

        bc1, bc2, bc3 = st.columns(3)
        with bc1:
            st.metric("Concursos testados", len(bt))
        with bc2:
            st.metric("Média de acertos", round(bt["acertos"].mean(), 2))
        with bc3:
            st.metric("Máximo de acertos", int(bt["acertos"].max()))

        st.markdown("#### Distribuição de Acertos")
        # CORREÇÃO 2: agregar com value_counts antes do px.bar
        acertos_dist = bt["acertos"].value_counts().reset_index()
        acertos_dist.columns = ["acertos", "frequencia"]
        acertos_dist = acertos_dist.sort_values("acertos")

        fig_bt = px.bar(
            acertos_dist,
            x="acertos",
            y="frequencia",
            title="Distribuição de Acertos no Backtesting",
            labels={"acertos": "Número de Acertos", "frequencia": "Frequência"},
            color="frequencia",
            color_continuous_scale="Sunset",
        )
        fig_bt.update_layout(
            template="plotly_dark",
            paper_bgcolor=THEME_BG,
            plot_bgcolor=THEME_BG,
            font=dict(color=THEME_TEXT),
        )
        st.plotly_chart(fig_bt, use_container_width=True)

        st.markdown("#### Detalhes do Backtesting")
        st.dataframe(bt, use_container_width=True, height=400)

# ----------------------------------------------------------
# TAB: EXPORTAÇÃO
# ----------------------------------------------------------
with tab_export:
    st.subheader("💾 Exportação de Dados")

    st.markdown("#### Exportar Frequência")
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        st.download_button(
            label="📥 Baixar Frequência (Excel)",
            data=exportar_excel(freq),
            file_name=f"frequencia_{loteria_selecionada.lower().replace('-', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with col_exp2:
        st.download_button(
            label="📥 Baixar Frequência (CSV)",
            data=exportar_csv(freq),
            file_name=f"frequencia_{loteria_selecionada.lower().replace('-', '_')}.csv",
            mime="text/csv",
        )

    st.markdown("#### Exportar Dados Completos")
    col_exp3, col_exp4 = st.columns(2)
    with col_exp3:
        st.download_button(
            label="📥 Baixar Dados (Excel)",
            data=exportar_excel(df),
            file_name=f"dados_{loteria_selecionada.lower().replace('-', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with col_exp4:
        st.download_button(
            label="📥 Baixar Dados (CSV)",
            data=exportar_csv(df),
            file_name=f"dados_{loteria_selecionada.lower().replace('-', '_')}.csv",
            mime="text/csv",
        )

    if len(df) > st.session_state["backtest_window"]:
        st.markdown("#### Exportar Backtesting")
        bt = backtesting(df, loteria_selecionada, janela=st.session_state["backtest_window"])
        col_exp5, col_exp6 = st.columns(2)
        with col_exp5:
            st.download_button(
                label="📥 Baixar Backtesting (Excel)",
                data=exportar_excel(bt),
                file_name=f"backtesting_{loteria_selecionada.lower().replace('-', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        with col_exp6:
            st.download_button(
                label="📥 Baixar Backtesting (CSV)",
                data=exportar_csv(bt),
                file_name=f"backtesting_{loteria_selecionada.lower().replace('-', '_')}.csv",
                mime="text/csv",
            )

    st.markdown("---")
    st.caption("Todos os dados exportados refletem o estado atual da análise.")
