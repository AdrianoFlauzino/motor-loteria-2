import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import random
import io
from datetime import datetime, timedelta

# ============================================================
# CONFIGURAÇÃO DAS LOTERIAS
# ============================================================

MESES_SORTE = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

LOTERIAS = {
    "Mega Sena": {
        "universo": 60,
        "dezenas_sorteio": 6,
        "min_aposta": 6,
        "max_aposta": 20,
        "extras": None,
    },
    "Lotofácil": {
        "universo": 25,
        "dezenas_sorteio": 15,
        "min_aposta": 15,
        "max_aposta": 20,
        "extras": None,
    },
    "Quina": {
        "universo": 80,
        "dezenas_sorteio": 5,
        "min_aposta": 5,
        "max_aposta": 15,
        "extras": None,
    },
    "+Milionária": {
        "universo": 50,
        "dezenas_sorteio": 6,
        "min_aposta": 6,
        "max_aposta": 12,
        "extras": {
            "tipo": "Trevos",
            "universo": 6,
            "quantidade": 2,
            "nome_coluna": "Trevos",
        },
    },
    "Dia de Sorte": {
        "universo": 31,
        "dezenas_sorteio": 7,
        "min_aposta": 7,
        "max_aposta": 15,
        "extras": {
            "tipo": "Mês_Sorte",
            "universo": 12,
            "quantidade": 1,
            "nome_coluna": "Mes_Sorte",
        },
    },
}


# ============================================================
# TEMAS
# ============================================================

def apply_white_theme():
    st.markdown(
        """
        <style>
            .stApp { background-color: #ffffff; color: #1f2933; }
            .stSidebar { background-color: #f7f9fb; }
            h1, h2, h3 { color: #1f2933; }
            .stButton>button { background-color: #2563eb; color: white; border-radius: 8px; }
            .stTabs [data-baseweb="tab"] { color: #1f2933; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_blue_theme():
    st.markdown(
        """
        <style>
            .stApp { background-color: #0f172a; color: #e2e8f0; }
            .stSidebar { background-color: #1e293b; }
            h1, h2, h3 { color: #38bdf8; }
            .stButton>button { background-color: #0ea5e9; color: white; border-radius: 8px; }
            .stTabs [data-baseweb="tab"] { color: #e2e8f0; }
            .stTabs [aria-selected="true"] { color: #38bdf8 !important; }
            .stDataFrame, .stTable { color: #e2e8f0; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# DATA LAYER
# ============================================================

def gerar_dados_mockados(nome_loteria: str, n_concursos: int) -> pd.DataFrame:
    """Gera dados mockados baseados nas regras da loteria selecionada."""
    config = LOTERIAS[nome_loteria]
    universo = config["universo"]
    dezenas = config["dezenas_sorteio"]
    extras_cfg = config["extras"]

    registros = []
    data_base = datetime.now() - timedelta(days=n_concursos * 7)

    for i in range(1, n_concursos + 1):
        numeros = sorted(random.sample(range(1, universo + 1), dezenas))
        linha = {"Concurso": i, "Data": (data_base + timedelta(days=i * 7)).strftime("%d/%m/%Y")}
        for idx, num in enumerate(numeros, start=1):
            linha[f"D{idx:02d}"] = num

        if extras_cfg is not None:
            if extras_cfg["tipo"] == "Trevos":
                trevos = sorted(random.sample(range(1, extras_cfg["universo"] + 1), extras_cfg["quantidade"]))
                linha[extras_cfg["nome_coluna"]] = "-".join(str(t) for t in trevos)
            elif extras_cfg["tipo"] == "Mês_Sorte":
                mes_idx = random.randint(1, extras_cfg["universo"])
                linha[extras_cfg["nome_coluna"]] = MESES_SORTE[mes_idx - 1]

        registros.append(linha)

    return pd.DataFrame(registros)


def extrair_dezenas(df: pd.DataFrame) -> pd.DataFrame:
    """Extrai apenas as colunas de dezenas (D01, D02, ...)."""
    cols = [c for c in df.columns if c.startswith("D") and c[1:].isdigit()]
    return df[cols]


# ============================================================
# DOMAIN LAYER
# ============================================================

def matriz_coocorrencia(df: pd.DataFrame, universo: int) -> pd.DataFrame:
    """Constrói matriz de coocorrência adaptada ao universo da loteria."""
    dezenas_df = extrair_dezenas(df)
    matriz = np.zeros((universo, universo), dtype=int)

    for _, row in dezenas_df.iterrows():
        nums = [int(v) for v in row.values if pd.notna(v)]
        for i in range(len(nums)):
            for j in range(len(nums)):
                if i != j:
                    matriz[nums[i] - 1][nums[j] - 1] += 1

    labels = [f"{i:02d}" for i in range(1, universo + 1)]
    return pd.DataFrame(matriz, index=labels, columns=labels)


def monte_carlo(df: pd.DataFrame, universo: int, dezenas_sorteio: int, simulacoes: int = 10000) -> pd.DataFrame:
    """Simulação de Monte Carlo adaptada ao universo e dezenas_sorteio."""
    dezenas_df = extrair_dezenas(df)
    todas_dezenas = dezenas_df.values.flatten()
    todas_dezenas = todas_dezenas[pd.notna(todas_dezenas)].astype(int)

    contagem = pd.Series(todas_dezenas).value_counts().reindex(range(1, universo + 1), fill_value=0)
    freq = contagem / contagem.sum()
    prob = freq.values / freq.values.sum()

    contagem_sim = np.zeros(universo, dtype=int)
    for _ in range(simulacoes):
        jogo = np.random.choice(range(1, universo + 1), size=dezenas_sorteio, replace=False, p=prob)
        for n in jogo:
            contagem_sim[n - 1] += 1

    resultado = pd.DataFrame({
        "Dezena": [f"{i:02d}" for i in range(1, universo + 1)],
        "Freq_Historica": contagem.values,
        "Freq_Simulada": contagem_sim,
        "Prob_Simulada": contagem_sim / (simulacoes * dezenas_sorteio),
    })
    return resultado.sort_values("Freq_Simulada", ascending=False).reset_index(drop=True)


def analisar_extras(df: pd.DataFrame, extras_cfg: dict) -> pd.DataFrame:
    """Calcula a força dos extras (Mês de Sorte ou Trevos)."""
    if extras_cfg is None:
        return pd.DataFrame()

    coluna = extras_cfg["nome_coluna"]
    if coluna not in df.columns:
        return pd.DataFrame()

    if extras_cfg["tipo"] == "Mês_Sorte":
        contagem = df[coluna].value_counts()
        resultado = pd.DataFrame({
            "Mês": contagem.index,
            "Frequência": contagem.values,
        })
        resultado["Força"] = resultado["Frequência"] / resultado["Frequência"].sum()
        return resultado.sort_values("Frequência", ascending=False).reset_index(drop=True)

    elif extras_cfg["tipo"] == "Trevos":
        todos_trevos = []
        for val in df[coluna].dropna():
            for t in str(val).split("-"):
                t = t.strip()
                if t.isdigit():
                    todos_trevos.append(int(t))
        contagem = pd.Series(todos_trevos).value_counts().reindex(range(1, extras_cfg["universo"] + 1), fill_value=0)
        resultado = pd.DataFrame({
            "Trevo": [f"{i:02d}" for i in range(1, extras_cfg["universo"] + 1)],
            "Frequência": contagem.values,
        })
        resultado["Força"] = resultado["Frequência"] / resultado["Frequência"].sum()
        return resultado.sort_values("Frequência", ascending=False).reset_index(drop=True)

    return pd.DataFrame()


def gerar_apostas(
    nome_loteria: str,
    df: pd.DataFrame,
    n_apostas: int,
    qtd_dezenas: int,
    estrategia: str,
    extras_cfg: dict,
) -> pd.DataFrame:
    """Gera apostas respeitando min/max da loteria, incluindo extras."""
    config = LOTERIAS[nome_loteria]
    universo = config["universo"]
    min_aposta = config["min_aposta"]
    max_aposta = config["max_aposta"]

    if qtd_dezenas < min_aposta:
        qtd_dezenas = min_aposta
    if qtd_dezenas > max_aposta:
        qtd_dezenas = max_aposta

    dezenas_df = extrair_dezenas(df)
    todas_dezenas = dezenas_df.values.flatten()
    todas_dezenas = todas_dezenas[pd.notna(todas_dezenas)].astype(int)
    contagem = pd.Series(todas_dezenas).value_counts().reindex(range(1, universo + 1), fill_value=0)

    matriz_co = matriz_coocorrencia(df, universo)

    apostas = []
    for i in range(1, n_apostas + 1):
        if estrategia == "Aleatório":
            numeros = sorted(random.sample(range(1, universo + 1), qtd_dezenas))

        elif estrategia == "Mais Frequentes":
            top = contagem.sort_values(ascending=False).head(qtd_dezenas * 3).index.tolist()
            numeros = sorted(random.sample(top, qtd_dezenas))

        elif estrategia == "Pares Fortes":
            # Seleciona dezena inicial mais frequente e expande por coocorrência
            ordenadas = contagem.sort_values(ascending=False).index.tolist()
            numeros = [ordenadas[0]]
            candidatos = list(range(1, universo + 1))
            while len(numeros) < qtd_dezenas:
                melhor = None
                melhor_score = -1
                for c in candidatos:
                    if c in numeros:
                        continue
                    score = sum(matriz_co.loc[f"{n:02d}", f"{c:02d}"] for n in numeros)
                    if score > melhor_score:
                        melhor_score = score
                        melhor = c
                if melhor is None:
                    break
                numeros.append(melhor)
            numeros = sorted(numeros)

        else:
            numeros = sorted(random.sample(range(1, universo + 1), qtd_dezenas))

        linha = {"Aposta": i}
        for idx, num in enumerate(numeros, start=1):
            linha[f"D{idx:02d}"] = num
        for idx in range(len(numeros) + 1, max_aposta + 1):
            linha[f"D{idx:02d}"] = ""

        if extras_cfg is not None:
            if extras_cfg["tipo"] == "Trevos":
                trevos = sorted(random.sample(range(1, extras_cfg["universo"] + 1), extras_cfg["quantidade"]))
                linha[extras_cfg["nome_coluna"]] = "-".join(f"{t:02d}" for t in trevos)
            elif extras_cfg["tipo"] == "Mês_Sorte":
                mes_idx = random.randint(1, extras_cfg["universo"])
                linha[extras_cfg["nome_coluna"]] = MESES_SORTE[mes_idx - 1]

        apostas.append(linha)

    return pd.DataFrame(apostas)


# ============================================================
# UI LAYER
# ============================================================

def main():
    st.set_page_config(page_title="Motor Analítico de Loterias", layout="wide", page_icon="🎲")

    # ---------- Sidebar ----------
    with st.sidebar:
        st.title("⚙️ Configurações")
        tema = st.selectbox("🎨 Tema", ["Branco", "Azul"])
        if tema == "Branco":
            apply_white_theme()
        else:
            apply_blue_theme()

        st.divider()
        nome_loteria = st.selectbox("🎰 Loteria", list(LOTERIAS.keys()))
        config = LOTERIAS[nome_loteria]

        n_concursos = st.slider(
            "📊 Nº de concursos (mock)",
            min_value=50,
            max_value=1000,
            value=300,
            step=50,
        )

        st.divider()
        st.caption(f"Universo: **{config['universo']}** | Sorteio: **{config['dezenas_sorteio']}**")
        st.caption(f"Aposta mín: **{config['min_aposta']}** | máx: **{config['max_aposta']}**")
        if config["extras"]:
            st.caption(f"Extras: **{config['extras']['tipo']}**")
        else:
            st.caption("Extras: **Nenhum**")

    # ---------- Header ----------
    st.title(f"🎲 Motor Analítico — {nome_loteria}")
    st.markdown("Análise estatística, simulação de Monte Carlo e geração inteligente de apostas.")

    # ---------- Dados ----------
    df = gerar_dados_mockados(nome_loteria, n_concursos)
    extras_cfg = config["extras"]

    # ---------- Tabs dinâmicas ----------
    nomes_tabs = ["Análise de Força (Pares)", "Heatmap de Coocorrência", "Base de Dados", "Gerador de Apostas"]
    if extras_cfg is not None:
        nomes_tabs.insert(3, "Análise Extra")

    tabs = st.tabs(nomes_tabs)

    # --- Tab 1: Análise de Força (Pares) ---
    with tabs[0]:
        st.subheader("🔥 Análise de Força — Pares mais coocorrentes")
        matriz = matriz_coocorrencia(df, config["universo"])

        pares = []
        labels = [f"{i:02d}" for i in range(1, config["universo"] + 1)]
        for i in range(config["universo"]):
            for j in range(i + 1, config["universo"]):
                pares.append({"Par": f"{labels[i]}-{labels[j]}", "Coocorrência": int(matriz.iloc[i, j])})
        df_pares = pd.DataFrame(pares).sort_values("Coocorrência", ascending=False).head(30).reset_index(drop=True)

        col1, col2 = st.columns([2, 3])
        with col1:
            st.dataframe(df_pares, use_container_width=True, height=500)
        with col2:
            fig, ax = plt.subplots(figsize=(8, 6))
            top_pares = df_pares.head(15)
            ax.barh(top_pares["Par"][::-1], top_pares["Coocorrência"][::-1], color="#2563eb")
            ax.set_xlabel("Coocorrência")
            ax.set_title("Top 15 Pares Fortes")
            st.pyplot(fig)

        st.markdown("---")
        st.subheader("🎯 Simulação de Monte Carlo")
        sim = monte_carlo(df, config["universo"], config["dezenas_sorteio"], simulacoes=5000)
        st.dataframe(sim.head(20), use_container_width=True)

    # --- Tab 2: Heatmap ---
    with tabs[1]:
        st.subheader("🌡️ Heatmap de Coocorrência")
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(matriz, cmap="YlGnBu", ax=ax, cbar_kws={"label": "Coocorrência"})
        ax.set_title(f"Matriz de Coocorrência — {nome_loteria}")
        ax.set_xlabel("Dezena")
        ax.set_ylabel("Dezena")
        st.pyplot(fig)

    # --- Tab 3: Base de Dados ---
    with tabs[2]:
        st.subheader("📋 Base de Dados (Mock)")
        st.dataframe(df, use_container_width=True)
        csv_base = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Baixar base (CSV)",
            data=csv_base,
            file_name=f"base_{nome_loteria.lower().replace(' ', '_')}.csv",
            mime="text/csv",
        )

    # --- Tab Extra (se aplicável) ---
    tab_idx_extra = 3 if extras_cfg is not None else None
    tab_idx_gerador = 4 if extras_cfg is not None else 3

    if extras_cfg is not None:
        with tabs[tab_idx_extra]:
            st.subheader(f"🌟 Análise Extra — {extras_cfg['tipo']}")
            df_extras = analisar_extras(df, extras_cfg)
            if df_extras.empty:
                st.warning("Nenhum dado extra disponível.")
            else:
                col_a, col_b = st.columns([2, 3])
                with col_a:
                    st.dataframe(df_extras, use_container_width=True)
                with col_b:
                    fig, ax = plt.subplots(figsize=(8, 5))
                    label_col = "Mês" if extras_cfg["tipo"] == "Mês_Sorte" else "Trevo"
                    ax.bar(df_extras[label_col], df_extras["Frequência"], color="#0ea5e9")
                    ax.set_ylabel("Frequência")
                    ax.set_title(f"Força dos {extras_cfg['tipo']}")
                    if extras_cfg["tipo"] == "Mês_Sorte":
                        ax.set_xticklabels(df_extras[label_col], rotation=45, ha="right")
                    st.pyplot(fig)

    # --- Tab Gerador de Apostas ---
    with tabs[tab_idx_gerador]:
        st.subheader("🎰 Gerador de Apostas")

        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1:
            estrategia = st.selectbox("🧠 Estratégia", ["Aleatório", "Mais Frequentes", "Pares Fortes"])
        with col_g2:
            n_apostas = st.number_input("🎟️ Nº de apostas", min_value=1, max_value=50, value=5, step=1)
        with col_g3:
            qtd_dezenas = st.slider(
                "🔢 Dezenas por aposta",
                min_value=config["min_aposta"],
                max_value=config["max_aposta"],
                value=config["min_aposta"],
                step=1,
            )

        if st.button("⚡ Gerar Apostas", type="primary"):
            with st.spinner("Gerando apostas..."):
                apostas_df = gerar_apostas(
                    nome_loteria=nome_loteria,
                    df=df,
                    n_apostas=int(n_apostas),
                    qtd_dezenas=int(qtd_dezenas),
                    estrategia=estrategia,
                    extras_cfg=extras_cfg,
                )
            st.session_state["apostas_df"] = apostas_df

        if "apostas_df" in st.session_state:
            apostas_df = st.session_state["apostas_df"]
            st.success(f"{len(apostas_df)} aposta(s) gerada(s) com estratégia **{estrategia}**.")
            st.dataframe(apostas_df, use_container_width=True)

            csv_apostas = apostas_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Baixar apostas (CSV)",
                data=csv_apostas,
                file_name=f"apostas_{nome_loteria.lower().replace(' ', '_')}_{estrategia.lower().replace(' ', '_')}.csv",
                mime="text/csv",
            )

    st.divider()
    st.caption("Motor Analítico de Loterias • Dados mockados para fins educacionais • Jogue com responsabilidade.")


if __name__ == "__main__":
    main()
