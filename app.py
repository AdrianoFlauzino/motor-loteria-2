import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from itertools import combinations
from collections import Counter
from datetime import datetime, timedelta
import random

# ============================================================
# CONFIG DAS LOTERIAS
# ============================================================
LOTERIAS = {
    "Mega Sena": {
        "dezenas": 60,
        "tamanho_aposta": 6,
        "min_aposta": 6,
        "max_aposta": 20,
        "extras": None,
        "cor": "green",
    },
    "Lotofácil": {
        "dezenas": 25,
        "tamanho_aposta": 15,
        "min_aposta": 15,
        "max_aposta": 20,
        "extras": None,
        "cor": "purple",
    },
    "Quina": {
        "dezenas": 80,
        "tamanho_aposta": 5,
        "min_aposta": 5,
        "max_aposta": 15,
        "extras": None,
        "cor": "blue",
    },
    "+Milionária": {
        "dezenas": 50,
        "tamanho_aposta": 6,
        "min_aposta": 6,
        "max_aposta": 12,
        "extras": {"nome": "Trevos", "quantidade": 2, "universo": 6},
        "cor": "orange",
    },
    "Dia de Sorte": {
        "dezenas": 31,
        "tamanho_aposta": 7,
        "min_aposta": 7,
        "max_aposta": 15,
        "extras": {"nome": "Mês de Sorte", "quantidade": 1, "universo": 12},
        "cor": "pink",
    },
}

MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

# ============================================================
# CAMADA DE DADOS (GERADOR DE HISTÓRICO SIMULADO)
# ============================================================
@st.cache_data(show_spinner=False)
def gerar_historico(nome_loteria: str, n_concursos: int = 300) -> pd.DataFrame:
    """Gera um histórico simulado de concursos para a loteria escolhida."""
    cfg = LOTERIAS[nome_loteria]
    total_dezenas = cfg["dezenas"]
    tamanho = cfg["tamanho_aposta"]
    extras_cfg = cfg.get("extras")

    rng = np.random.default_rng(seed=hash(nome_loteria) % (2**32))
    linhas = []
    data_base = datetime(2023, 1, 1)

    for i in range(1, n_concursos + 1):
        dezenas = sorted(rng.choice(range(1, total_dezenas + 1), size=tamanho, replace=False).tolist())
        linha = {"concurso": i, "data": data_base + timedelta(days=i * 2)}
        for j, d in enumerate(dezenas, start=1):
            linha[f"d{j}"] = d
        if extras_cfg:
            if extras_cfg["nome"] == "Mês de Sorte":
                linha["extra"] = rng.integers(1, extras_cfg["universo"] + 1)
            elif extras_cfg["nome"] == "Trevos":
                linha["extra"] = ",".join(
                    map(str, sorted(rng.choice(range(1, extras_cfg["universo"] + 1), size=extras_cfg["quantidade"], replace=False).tolist()))
                )
        linhas.append(linha)

    df = pd.DataFrame(linhas)
    return df


def obter_dezenas_df(df: pd.DataFrame) -> list[list[int]]:
    """Extrai a lista de dezenas de cada concurso a partir do DataFrame."""
    cols = [c for c in df.columns if c.startswith("d") and c[1:].isdigit()]
    return df[cols].values.tolist()


# ============================================================
# CAMADA ANALÍTICA
# ============================================================
@st.cache_data(show_spinner=False)
def calcular_frequencia(dezenas_lista: list[list[int]], total_dezenas: int) -> pd.DataFrame:
    """Calcula a frequência absoluta de cada dezena."""
    contagem = Counter()
    for aposta in dezenas_lista:
        contagem.update(aposta)
    dados = [{"dezena": d, "frequencia": contagem.get(d, 0)} for d in range(1, total_dezenas + 1)]
    return pd.DataFrame(dados).sort_values("frequencia", ascending=False).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def calcular_atraso(dezenas_lista: list[list[int]], total_dezenas: int) -> pd.DataFrame:
    """Calcula o atraso de cada dezena (concursos desde a última aparição)."""
    n = len(dezenas_lista)
    ultima_aparicao = {d: -1 for d in range(1, total_dezenas + 1)}
    for idx, aposta in enumerate(dezenas_lista):
        for d in aposta:
            ultima_aparicao[d] = idx
    dados = []
    for d in range(1, total_dezenas + 1):
        if ultima_aparicao[d] == -1:
            atraso = n
        else:
            atraso = n - 1 - ultima_aparicao[d]
        dados.append({"dezena": d, "atraso": atraso})
    return pd.DataFrame(dados).sort_values("atraso", ascending=False).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def matriz_coocorrencia(dezenas_lista: list[list[int]], total_dezenas: int) -> np.ndarray:
    """Matriz de coocorrência otimizada com itertools.combinations."""
    matriz = np.zeros((total_dezenas, total_dezenas), dtype=int)
    for aposta in dezenas_lista:
        for a, b in combinations(sorted(aposta), 2):
            matriz[a - 1, b - 1] += 1
            matriz[b - 1, a - 1] += 1
    np.fill_diagonal(matriz, 0)
    return matriz


@st.cache_data(show_spinner=False)
def monte_carlo_pares(
    dezenas_lista: list[list[int]],
    total_dezenas: int,
    tamanho_aposta: int,
    n_sim: int = 500,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Monte Carlo: simula concursos aleatórios e calcula a matriz esperada de pares.
    Retorna (matriz_real, matriz_esperada) e a força Real/Esperado é derivada.
    """
    matriz_real = matriz_coocorrencia(dezenas_lista, total_dezenas)
    matriz_esperada = np.zeros((total_dezenas, total_dezenas), dtype=float)

    rng = np.random.default_rng(seed=42)
    for _ in range(n_sim):
        simulado = rng.choice(range(1, total_dezenas + 1), size=tamanho_aposta, replace=False)
        for a, b in combinations(sorted(simulado), 2):
            matriz_esperada[a - 1, b - 1] += 1
            matriz_esperada[b - 1, a - 1] += 1
    matriz_esperada /= n_sim

    # Probabilidade teórica de um par aparecer em uma aposta
    p_par = tamanho_aposta * (tamanho_aposta - 1) / (total_dezenas * (total_dezenas - 1))
    n_concursos = len(dezenas_lista)
    matriz_esperada_teorica = np.full((total_dezenas, total_dezenas), p_par * n_concursos, dtype=float)
    np.fill_diagonal(matriz_esperada_teorica, 0)

    return matriz_real, matriz_esperada_teorica


@st.cache_data(show_spinner=False)
def forca_pares(
    dezenas_lista: list[list[int]],
    total_dezenas: int,
    tamanho_aposta: int,
    n_sim: int = 500,
) -> pd.DataFrame:
    """Calcula a força (Real/Esperado) de cada par de dezenas."""
    matriz_real, matriz_esperada = monte_carlo_pares(dezenas_lista, total_dezenas, tamanho_aposta, n_sim)
    registros = []
    for a, b in combinations(range(total_dezenas), 2):
        real = matriz_real[a, b]
        esperado = matriz_esperada[a, b]
        forca = (real / esperado) if esperado > 0 else 0.0
        registros.append({
            "par": f"{a + 1:02d}-{b + 1:02d}",
            "d1": a + 1,
            "d2": b + 1,
            "real": int(real),
            "esperado": float(esperado),
            "forca": float(forca),
        })
    df = pd.DataFrame(registros)
    return df.sort_values("forca", ascending=False).reset_index(drop=True)


# ============================================================
# GERADOR DE APOSTAS
# ============================================================
def gerar_aposta_aleatoria(total_dezenas: int, tamanho: int, rng: random.Random) -> list[int]:
    return sorted(rng.sample(range(1, total_dezenas + 1), tamanho))


def gerar_aposta_frequentes(df_freq: pd.DataFrame, tamanho: int) -> list[int]:
    return sorted(df_freq.head(tamanho)["dezena"].tolist())


def gerar_aposta_pares_fortes(df_pares: pd.DataFrame, tamanho: int, total_dezenas: int) -> list[int]:
    """Constrói aposta a partir dos pares mais fortes (greedy)."""
    selecionadas: set[int] = set()
    for _, row in df_pares.iterrows():
        if len(selecionadas) >= tamanho:
            break
        selecionadas.add(int(row["d1"]))
        if len(selecionadas) < tamanho:
            selecionadas.add(int(row["d2"]))
    if len(selecionadas) < tamanho:
        restantes = [d for d in range(1, total_dezenas + 1) if d not in selecionadas]
        selecionadas.update(restantes[: tamanho - len(selecionadas)])
    return sorted(selecionadas)[:tamanho]


def gerar_aposta_atrasadas(df_atraso: pd.DataFrame, tamanho: int) -> list[int]:
    """Estratégia: dezenas mais atrasadas."""
    return sorted(df_atraso.head(tamanho)["dezena"].tolist())


def gerar_aposta(
    estrategia: str,
    cfg: dict,
    df_freq: pd.DataFrame,
    df_atraso: pd.DataFrame,
    df_pares: pd.DataFrame,
    tamanho: int,
    seed: int | None = None,
) -> list[int]:
    rng = random.Random(seed)
    total = cfg["dezenas"]
    if estrategia == "Aleatório":
        return gerar_aposta_aleatoria(total, tamanho, rng)
    if estrategia == "Mais Frequentes":
        return gerar_aposta_frequentes(df_freq, tamanho)
    if estrategia == "Pares Fortes":
        return gerar_aposta_pares_fortes(df_pares, tamanho, total)
    if estrategia == "Dezenas Atrasadas":
        return gerar_aposta_atrasadas(df_atraso, tamanho)
    return gerar_aposta_aleatoria(total, tamanho, rng)


def gerar_extras(cfg: dict, seed: int | None = None) -> str | None:
    extras_cfg = cfg.get("extras")
    if not extras_cfg:
        return None
    rng = random.Random(seed)
    if extras_cfg["nome"] == "Mês de Sorte":
        return MESES[rng.randint(0, 11)]
    if extras_cfg["nome"] == "Trevos":
        return ", ".join(map(str, sorted(rng.sample(range(1, extras_cfg["universo"] + 1), extras_cfg["quantidade"]))))
    return None


# ============================================================
# VISUALIZAÇÃO (PLOTLY)
# ============================================================
def plot_heatmap_coocorrencia(matriz: np.ndarray, tema: str) -> go.Figure:
    total = matriz.shape[0]
    fig = px.imshow(
        matriz,
        labels=dict(x="Dezena", y="Dezena", color="Coocorrência"),
        x=[str(i) for i in range(1, total + 1)],
        y=[str(i) for i in range(1, total + 1)],
        color_continuous_scale="Blues" if tema == "Azul" else "Viridis",
        aspect="auto",
    )
    fig.update_layout(
        title="Matriz de Coocorrência (Interativa)",
        template="plotly_white" if tema == "Branco" else "plotly_dark",
        height=600,
    )
    return fig


def plot_frequencia_bar(df_freq: pd.DataFrame, tema: str, cor: str = "green") -> go.Figure:
    fig = px.bar(
        df_freq.sort_values("dezena"),
        x="dezena",
        y="frequencia",
        labels={"dezena": "Dezena", "frequencia": "Frequência"},
        color_discrete_sequence=[cor],
    )
    fig.update_layout(
        title="Frequência de Dezenas",
        template="plotly_white" if tema == "Branco" else "plotly_dark",
        height=450,
    )
    return fig


def plot_atraso_bar(df_atraso: pd.DataFrame, tema: str, cor: str = "orange") -> go.Figure:
    fig = px.bar(
        df_atraso.sort_values("dezena"),
        x="dezena",
        y="atraso",
        labels={"dezena": "Dezena", "atraso": "Atraso (concursos)"},
        color_discrete_sequence=[cor],
    )
    fig.update_layout(
        title="Atraso de Dezenas",
        template="plotly_white" if tema == "Branco" else "plotly_dark",
        height=450,
    )
    return fig


def plot_forca_pares_bar(df_pares: pd.DataFrame, tema: str, top_n: int = 20) -> go.Figure:
    top = df_pares.head(top_n)
    fig = px.bar(
        top,
        x="par",
        y="forca",
        labels={"par": "Par", "forca": "Força (Real/Esperado)"},
        color="forca",
        color_continuous_scale="Inferno",
    )
    fig.update_layout(
        title=f"Top {top_n} Pares mais Fortes (Real/Esperado)",
        template="plotly_white" if tema == "Branco" else "plotly_dark",
        height=450,
    )
    return fig


# ============================================================
# UI LAYER
# ============================================================
def main():
    st.set_page_config(page_title="Motor Analítico de Loterias", page_icon="🎲", layout="wide")
    st.title("🎲 Motor Analítico & Gerador de Apostas Multi-Loteria")
    st.caption("Análise estatística, coocorrência, Monte Carlo e geração de apostas.")

    # Barra lateral
    with st.sidebar:
        st.header("⚙️ Configurações")
        nome_loteria = st.selectbox("Loteria", list(LOTERIAS.keys()), index=0)
        cfg = LOTERIAS[nome_loteria]
        tema = st.radio("Tema", ["Branco", "Azul"], index=0)
        n_concursos = st.slider("Histórico (concursos simulados)", 50, 500, 300, step=50)
        n_sim_mc = st.slider("Simulações Monte Carlo", 100, 2000, 500, step=100)
        st.markdown("---")
        st.markdown(f"**Dezenas:** {cfg['dezenas']}  \n**Aposta padrão:** {cfg['tamanho_aposta']}")
        if cfg.get("extras"):
            st.markdown(f"**Extra:** {cfg['extras']['nome']}")

    # Carrega dados
    df = gerar_historico(nome_loteria, n_concursos)
    dezenas_lista = obter_dezenas_df(df)

    df_freq = calcular_frequencia(dezenas_lista, cfg["dezenas"])
    df_atraso = calcular_atraso(dezenas_lista, cfg["dezenas"])
    matriz = matriz_coocorrencia(dezenas_lista, cfg["dezenas"])
    df_pares = forca_pares(dezenas_lista, cfg["dezenas"], cfg["tamanho_aposta"], n_sim=n_sim_mc)

    # Abas
    tab_resumo, tab_freq, tab_atraso, tab_cooc, tab_mc, tab_gerador = st.tabs([
        "📋 Resumo", "📊 Frequência", "⏳ Atraso", "🔥 Coocorrência", "🎯 Monte Carlo", "🎟️ Gerador",
    ])

    with tab_resumo:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Concursos analisados", len(df))
        col2.metric("Dezena + frequente", int(df_freq.iloc[0]["dezena"]), f"{int(df_freq.iloc[0]['frequencia'])}x")
        col3.metric("Dezena + atrasada", int(df_atraso.iloc[0]["dezena"]), f"{int(df_atraso.iloc[0]['atraso'])} concursos")
        col4.metric("Par + forte", df_pares.iloc[0]["par"], f"{df_pares.iloc[0]['forca']:.2f}x")
        st.markdown("### Últimos concursos")
        st.dataframe(df.tail(10), use_container_width=True, hide_index=True)

    with tab_freq:
        st.plotly_chart(plot_frequencia_bar(df_freq, tema, cfg["cor"]), use_container_width=True)
        st.markdown("### Tabela de Frequência")
        st.dataframe(df_freq, use_container_width=True, hide_index=True)

    with tab_atraso:
        st.plotly_chart(plot_atraso_bar(df_atraso, tema, "orange"), use_container_width=True)
        st.markdown("### Tabela de Atraso")
        st.dataframe(df_atraso, use_container_width=True, hide_index=True)

    with tab_cooc:
        st.markdown("### Heatmap Interativo de Coocorrência")
        st.plotly_chart(plot_heatmap_coocorrencia(matriz, tema), use_container_width=True)
        st.markdown("### Top 20 Pares mais Frequentes")
        top_pares = (
            pd.DataFrame([
                {"par": f"{i+1:02d}-{j+1:02d}", "d1": i + 1, "d2": j + 1, "coocorrencia": int(matriz[i, j])}
                for i, j in combinations(range(cfg["dezenas"]), 2)
            ])
            .sort_values("coocorrencia", ascending=False)
            .head(20)
            .reset_index(drop=True)
        )
        st.dataframe(top_pares, use_container_width=True, hide_index=True)

    with tab_mc:
        st.markdown("### Análise Monte Carlo — Força dos Pares (Real/Esperado)")
        st.caption(f"Simulações: {n_sim_mc} | Tamanho aposta: {cfg['tamanho_aposta']} | Universo: {cfg['dezenas']}")
        st.plotly_chart(plot_forca_pares_bar(df_pares, tema, top_n=25), use_container_width=True)
        st.markdown("### Tabela de Força dos Pares")
        st.dataframe(df_pares.head(50), use_container_width=True, hide_index=True)

    with tab_gerador:
        st.markdown("### 🎟️ Gerador de Apostas")
        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1:
            estrategia = st.selectbox(
                "Estratégia",
                ["Aleatório", "Mais Frequentes", "Pares Fortes", "Dezenas Atrasadas"],
                index=0,
            )
        with col_g2:
            tamanho = st.slider(
                "Tamanho da aposta",
                min_value=cfg["min_aposta"],
                max_value=cfg["max_aposta"],
                value=cfg["tamanho_aposta"],
            )
        with col_g3:
            qtd_apostas = st.number_input("Quantidade de apostas", 1, 20, 5)

        if st.button("🎲 Gerar Apostas", type="primary"):
            st.markdown("### Apostas Geradas")
            apostas_geradas = []
            for k in range(int(qtd_apostas)):
                seed = random.randint(0, 10**9) if estrategia == "Aleatório" else None
                aposta = gerar_aposta(
                    estrategia, cfg, df_freq, df_atraso, df_pares, tamanho, seed=seed
                )
                extra = gerar_extras(cfg, seed=random.randint(0, 10**9))
                apostas_geradas.append({
                    "#": k + 1,
                    "Estratégia": estrategia,
                    "Dezenas": " - ".join(f"{d:02d}" for d in aposta),
                    cfg["extras"]["nome"] if cfg.get("extras") else "Extra": extra if extra else "-",
                })
            st.dataframe(pd.DataFrame(apostas_geradas), use_container_width=True, hide_index=True)

            # Visualização da primeira aposta
            st.markdown("### Visualização da Primeira Aposta")
            primeira = [int(x) for x in apostas_geradas[0]["Dezenas"].split(" - ")]
            mask = pd.DataFrame({
                "dezena": range(1, cfg["dezenas"] + 1),
                "selecionada": [1 if d in primeira else 0 for d in range(1, cfg["dezenas"] + 1)],
            })
            fig = px.bar(
                mask,
                x="dezena",
                y="selecionada",
                color="selecionada",
                color_continuous_scale=["#cccccc", cfg["cor"]],
                labels={"dezena": "Dezena", "selecionada": "Selecionada"},
            )
            fig.update_layout(
                template="plotly_white" if tema == "Branco" else "plotly_dark",
                height=300,
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
