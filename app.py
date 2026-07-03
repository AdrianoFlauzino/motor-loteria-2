import io
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


# -----------------------------------------------------------------------------
# Theme Layer
# -----------------------------------------------------------------------------

def apply_white_theme():
    st.markdown(
        """
        <style>
            .stApp { background-color: #ffffff; color: #1f2933; }
            h1, h2, h3, h4 { color: #0b3d91; }
            .stTabs [data-baseweb="tab"] {
                color: #0b3d91;
                border-bottom: 3px solid transparent;
            }
            .stTabs [aria-selected="true"] {
                border-bottom: 3px solid #0b3d91;
                color: #0b3d91;
                font-weight: bold;
            }
            .metric-card {
                background-color: #f4f7fb;
                border-left: 5px solid #0b3d91;
                padding: 12px 16px;
                border-radius: 8px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_blue_theme():
    st.markdown(
        """
        <style>
            .stApp { background-color: #0b3d91; color: #ffffff; }
            h1, h2, h3, h4 { color: #ffd166; }
            .stTabs [data-baseweb="tab"] {
                color: #ffffff;
                border-bottom: 3px solid transparent;
            }
            .stTabs [aria-selected="true"] {
                border-bottom: 3px solid #ffd166;
                color: #ffd166;
                font-weight: bold;
            }
            .stSidebar { background-color: #072c6b; }
            .metric-card {
                background-color: #072c6b;
                border-left: 5px solid #ffd166;
                padding: 12px 16px;
                border-radius: 8px;
                color: #ffffff;
            }
            .stDataFrame { color: #0b3d91; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# Data Layer
# -----------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def carregar_dados_dia_de_sorte(n_concursos: int = 500, seed: int = 42) -> pd.DataFrame:
    """Gera dados sinteticos da loteria Dia de Sorte.

    Cada concurso possui 7 dezenas (1 a 31) e um Mes da Sorte (1 a 12).
    """
    rng = np.random.default_rng(seed)
    dezenas = []
    meses = []
    for _ in range(n_concursos):
        numeros = sorted(rng.choice(range(1, 32), size=7, replace=False).tolist())
        dezenas.append(numeros)
        meses.append(int(rng.integers(1, 13)))

    df = pd.DataFrame(dezenas, columns=[f"D{i}" for i in range(1, 8)])
    df.insert(0, "Concurso", range(1, n_concursos + 1))
    df["Mes_Sorte"] = meses
    return df


# -----------------------------------------------------------------------------
# Domain Layer
# -----------------------------------------------------------------------------

def matriz_coocorrencia(df: pd.DataFrame) -> pd.DataFrame:
    """Constroi a matriz de coocorrencia 31x31 entre as dezenas."""
    dezena_cols = [f"D{i}" for i in range(1, 8)]
    total = 31
    matriz = np.zeros((total, total), dtype=int)

    for _, row in df.iterrows():
        nums = row[dezena_cols].tolist()
        for i in nums:
            for j in nums:
                matriz[i - 1, j - 1] += 1

    labels = list(range(1, total + 1))
    return pd.DataFrame(matriz, index=labels, columns=labels)


def monte_carlo_dia_de_sorte(
    df: pd.DataFrame,
    n_simulacoes: int = 1000,
    seed: int = 7,
) -> pd.DataFrame:
    """Simula sorteios aleatorios para estimar a coocorrencia esperada."""
    rng = np.random.default_rng(seed)
    total = 31
    matriz = np.zeros((total, total), dtype=int)
    n_concursos = len(df)

    for _ in range(n_simulacoes):
        for _ in range(n_concursos):
            nums = rng.choice(range(1, total + 1), size=7, replace=False)
            for i in nums:
                for j in nums:
                    matriz[i - 1, j - 1] += 1

    matriz = matriz / n_simulacoes
    labels = list(range(1, total + 1))
    return pd.DataFrame(matriz, index=labels, columns=labels)


def analisar_dia_de_sorte(df: pd.DataFrame, n_simulacoes: int = 1000) -> pd.DataFrame:
    """Calcula a Forca (Real / Esperado) para cada par de dezenas."""
    real = matriz_coocorrencia(df)
    esperado = monte_carlo_dia_de_sorte(df, n_simulacoes=n_simulacoes)

    registros = []
    for i in range(1, 32):
        for j in range(i + 1, 32):
            r = real.loc[i, j]
            e = esperado.loc[i, j]
            forca = r / e if e > 0 else 0.0
            registros.append(
                {
                    "Dezena_A": i,
                    "Dezena_B": j,
                    "Coocorrencia_Real": int(r),
                    "Coocorrencia_Esperada": round(float(e), 2),
                    "Forca": round(float(forca), 3),
                }
            )

    return pd.DataFrame(registros).sort_values("Forca", ascending=False).reset_index(drop=True)


def analisar_mes_de_sorte(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula a Forca (Real / Esperado) para cada Mes da Sorte.

    Real  -> frequencia observada do mes nos concursos.
    Esperado -> frequencia esperada se a distribuicao fosse uniforme (1/12).
    """
    n_concursos = len(df)
    esperado_por_mes = n_concursos / 12.0

    contagem = df["Mes_Sorte"].value_counts().reindex(range(1, 13), fill_value=0)

    resultado = pd.DataFrame(
        {
            "Mes": list(range(1, 13)),
            "Nome_Mes": [
                "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
            ],
            "Frequencia_Real": contagem.values.astype(int),
            "Frequencia_Esperada": round(esperado_por_mes, 2),
        }
    )
    resultado["Forca"] = (
        resultado["Frequencia_Real"] / resultado["Frequencia_Esperada"]
    ).round(3)
    return resultado.sort_values("Forca", ascending=False).reset_index(drop=True)


def _frequencia_dezenas(df: pd.DataFrame) -> pd.Series:
    """Retorna a frequencia de cada dezena (1 a 31) no historico."""
    dezena_cols = [f"D{i}" for i in range(1, 8)]
    todas = df[dezena_cols].values.flatten()
    contagem = pd.Series(todas).value_counts().reindex(range(1, 32), fill_value=0)
    return contagem


def _frequencia_meses(df: pd.DataFrame) -> pd.Series:
    """Retorna a frequencia de cada mes (1 a 12) no historico."""
    return df["Mes_Sorte"].value_counts().reindex(range(1, 13), fill_value=0)


def gerar_apostas(
    df: pd.DataFrame,
    qtd_jogos: int,
    dezenas_por_jogo: int,
    estrategia: str,
) -> pd.DataFrame:
    """Gera jogos para a loteria Dia de Sorte.

    Estrategias:
      - "Aleatorio": dezenas e mes 100% aleatorios.
      - "Mais Frequentes": pondera dezenas e meses pela frequencia historica.
      - "Pares Fortes": garante o par mais forte da estatistica no jogo.

    Retorna um DataFrame com colunas: Jogo, Dezenas, Mes de Sorte.
    """
    rng = np.random.default_rng()
    universo = np.arange(1, 32)
    meses = np.arange(1, 13)

    freq_dez = _frequencia_dezenas(df).astype(float)
    freq_mes = _frequencia_meses(df).astype(float)

    pesos_dez = freq_dez.to_numpy()
    pesos_mes = freq_mes.to_numpy()

    if pesos_dez.sum() == 0:
        pesos_dez = np.ones_like(pesos_dez, dtype=float)
    if pesos_mes.sum() == 0:
        pesos_mes = np.ones_like(pesos_mes, dtype=float)

    prob_dez = pesos_dez / pesos_dez.sum()
    prob_mes = pesos_mes / pesos_mes.sum()

    par_forte = None
    if estrategia == "Pares Fortes":
        analise_pares = analisar_dia_de_sorte(df, n_simulacoes=100)
        if not analise_pares.empty:
            linha = analise_pares.iloc[0]
            par_forte = (int(linha["Dezena_A"]), int(linha["Dezena_B"]))

    jogos = []
    for idx in range(1, qtd_jogos + 1):
        if estrategia == "Aleatorio":
            escolhidas = rng.choice(
                universo, size=dezenas_por_jogo, replace=False
            )
            mes = int(rng.choice(meses))

        elif estrategia == "Mais Frequentes":
            escolhidas = rng.choice(
                universo,
                size=dezenas_por_jogo,
                replace=False,
                p=prob_dez,
            )
            mes = int(rng.choice(meses, p=prob_mes))

        elif estrategia == "Pares Fortes":
            if par_forte is not None:
                base = set(par_forte)
                restantes = [d for d in universo if d not in base]
                qtd_restante = dezenas_por_jogo - len(base)
                complemento = rng.choice(
                    restantes, size=qtd_restante, replace=False
                )
                escolhidas = np.array(sorted(list(base) + complemento.tolist()))
            else:
                escolhidas = rng.choice(
                    universo, size=dezenas_por_jogo, replace=False
                )
            mes = int(rng.choice(meses))

        else:
            raise ValueError(f"Estrategia desconhecida: {estrategia}")

        dezenas_ordenadas = sorted(int(d) for d in escolhidas)
        jogos.append(
            {
                "Jogo": idx,
                "Dezenas": ", ".join(f"{d:02d}" for d in dezenas_ordenadas),
                "Mes de Sorte": mes,
            }
        )

    return pd.DataFrame(jogos, columns=["Jogo", "Dezenas", "Mes de Sorte"])


# -----------------------------------------------------------------------------
# UI Layer
# -----------------------------------------------------------------------------

def render_dashboard(df: pd.DataFrame):
    st.title("Dia de Sorte - Analise Estatistica")
    st.caption("Analise de pares, coocorrencia, base de dados, Mes da Sorte e gerador de apostas.")

    with st.spinner("Processando analises..."):
        analise_pares = analisar_dia_de_sorte(df, n_simulacoes=200)
        matriz = matriz_coocorrencia(df)
        analise_mes = analisar_mes_de_sorte(df)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "Analise de Forca (Pares)",
            "Heatmap de Coocorrencia",
            "Base de Dados",
            "Mes de Sorte",
            "Gerador de Apostas",
        ]
    )

    # --- Tab 1: Forca de Pares ---
    with tab1:
        st.subheader("Top Pares por Forca (Real / Esperado)")
        st.markdown(
            "<div class='metric-card'>"
            "Forca > 1 indica que o par aparece mais do que o esperado pelo acaso."
            "</div>",
            unsafe_allow_html=True,
        )
        st.write("")

        top_n = st.slider("Numero de pares a exibir:", 10, 100, 30, key="slider_pares")
        top_pares = analise_pares.head(top_n)

        col1, col2, col3 = st.columns(3)
        col1.metric("Pares analisados", len(analise_pares))
        col2.metric("Maior Forca", f"{analise_pares['Forca'].max():.3f}")
        col3.metric("Forca media", f"{analise_pares['Forca'].mean():.3f}")

        st.dataframe(top_pares, use_container_width=True, hide_index=True)

        fig_pares = px.bar(
            top_pares,
            x="Forca",
            y=top_pares.apply(lambda r: f"{int(r['Dezena_A']):02d}-{int(r['Dezena_B']):02d}", axis=1),
            orientation="h",
            color="Forca",
            color_continuous_scale="Blues",
            title=f"Top {top_n} Pares por Forca",
            labels={"y": "Par de Dezenas", "Forca": "Forca (Real/Esperado)"},
        )
        fig_pares.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_pares, use_container_width=True)

    # --- Tab 2: Heatmap ---
    with tab2:
        st.subheader("Matriz de Coocorrencia (31x31)")
        st.markdown(
            "<div class='metric-card'>"
            "Contagem de vezes que duas dezenas apareceram no mesmo concurso."
            "</div>",
            unsafe_allow_html=True,
        )
        st.write("")

        fig_heat = px.imshow(
            matriz,
            labels=dict(x="Dezena B", y="Dezena A", color="Coocorrencia"),
            x=matriz.columns,
            y=matriz.index,
            color_continuous_scale="Blues",
            title="Heatmap de Coocorrencia",
            aspect="auto",
        )
        fig_heat.update_layout(height=650)
        st.plotly_chart(fig_heat, use_container_width=True)

    # --- Tab 3: Base de Dados ---
    with tab3:
        st.subheader("Base de Dados - Dia de Sorte")
        st.markdown(
            f"<div class='metric-card'>"
            f"Total de concursos: <b>{len(df)}</b> | Dezenas por concurso: 7 | Mes da Sorte: 1-12"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.write("")

        filtro_mes = st.multiselect(
            "Filtrar por Mes da Sorte:",
            options=list(range(1, 13)),
            format_func=lambda m: [
                "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
            ][m - 1],
            key="filtro_mes",
        )

        df_exibir = df.copy()
        if filtro_mes:
            df_exibir = df_exibir[df_exibir["Mes_Sorte"].isin(filtro_mes)]

        st.dataframe(df_exibir, use_container_width=True, hide_index=True)
        st.download_button(
            label="Baixar base filtrada (CSV)",
            data=df_exibir.to_csv(index=False).encode("utf-8"),
            file_name="dia_de_sorte_dados.csv",
            mime="text/csv",
        )

    # --- Tab 4: Mes de Sorte ---
    with tab4:
        st.subheader("Analise do Mes da Sorte")
        st.markdown(
            "<div class='metric-card'>"
            "Forca = Frequencia Real / Frequencia Esperada (uniforme 1/12). "
            "Valores > 1 indicam meses sorteados acima do esperado."
            "</div>",
            unsafe_allow_html=True,
        )
        st.write("")

        col1, col2, col3 = st.columns(3)
        col1.metric("Mes mais forte", analise_mes.iloc[0]["Nome_Mes"])
        col2.metric("Maior Forca", f"{analise_mes['Forca'].max():.3f}")
        col3.metric("Forca media", f"{analise_mes['Forca'].mean():.3f}")

        st.dataframe(analise_mes, use_container_width=True, hide_index=True)

        fig_mes = px.bar(
            analise_mes,
            x="Nome_Mes",
            y="Forca",
            color="Forca",
            color_continuous_scale="Blues",
            text="Forca",
            title="Forca dos Meses da Sorte (Real / Esperado)",
            labels={"Nome_Mes": "Mes", "Forca": "Forca"},
        )
        fig_mes.update_traces(texttemplate="%{text:.3f}", textposition="outside")
        fig_mes.add_hline(
            y=1.0,
            line_dash="dash",
            line_color="red",
            annotation_text="Esperado (Forca = 1)",
            annotation_position="top left",
        )
        fig_mes.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_mes, use_container_width=True)

    # --- Tab 5: Gerador de Apostas ---
    with tab5:
        st.subheader("Gerador de Apostas - Dia de Sorte")
        st.markdown(
            "<div class='metric-card'>"
            "Gere jogos personalizados usando diferentes estrategias baseadas no historico."
            "</div>",
            unsafe_allow_html=True,
        )
        st.write("")

        col_sel1, col_sel2, col_sel3 = st.columns(3)
        with col_sel1:
            qtd_jogos = st.number_input(
                "Quantidade de Jogos:",
                min_value=1,
                max_value=100,
                value=5,
                step=1,
                key="qtd_jogos",
            )
        with col_sel2:
            dezenas_por_jogo = st.number_input(
                "Dezenas por Jogo:",
                min_value=7,
                max_value=15,
                value=7,
                step=1,
                key="dezenas_por_jogo",
            )
        with col_sel3:
            estrategia = st.selectbox(
                "Estrategia:",
                options=["Aleatorio", "Mais Frequentes", "Pares Fortes"],
                index=0,
                key="estrategia_apostas",
            )

        st.write("")
        if st.button("Gerar Apostas", key="btn_gerar_apostas", type="primary"):
            with st.spinner("Gerando apostas..."):
                apostas = gerar_apostas(
                    df=df,
                    qtd_jogos=int(qtd_jogos),
                    dezenas_por_jogo=int(dezenas_por_jogo),
                    estrategia=estrategia,
                )

            st.session_state["apostas_geradas"] = apostas

        if "apostas_geradas" in st.session_state:
            apostas = st.session_state["apostas_geradas"]
            st.success(f"{len(apostas)} jogo(s) gerado(s) com a estrategia '{estrategia}'.")
            st.dataframe(apostas, use_container_width=True, hide_index=True)

            csv_buffer = io.StringIO()
            apostas.to_csv(csv_buffer, index=False)
            st.download_button(
                label="Baixar apostas (CSV)",
                data=csv_buffer.getvalue().encode("utf-8"),
                file_name="apostas_dia_de_sorte.csv",
                mime="text/csv",
            )


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title="Dia de Sorte - Streamlit",
        page_icon="🍀",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    with st.sidebar:
        st.header("Configuracoes")
        tema = st.radio(
            "Escolha o tema:",
            options=["Branco", "Azul Corporativo"],
            index=0,
            key="tema_selecionado",
        )

        n_concursos = st.slider(
            "Numero de concursos simulados:",
            min_value=100,
            max_value=2000,
            value=500,
            step=100,
            key="slider_concursos",
        )

        st.markdown("---")
        st.caption("App construido exclusivamente com Streamlit.")

    if tema == "Branco":
        apply_white_theme()
    else:
        apply_blue_theme()

    df = carregar_dados_dia_de_sorte(n_concursos=n_concursos)
    render_dashboard(df)


if __name__ == "__main__":
    main()
