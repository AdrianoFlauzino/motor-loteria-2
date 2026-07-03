import io
import hashlib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Lottery Analyzer", page_icon="🎲", layout="wide")

LOTERIAS = {
    "Mega-Sena": {
        "nome": "Mega-Sena",
        "dezenas_total": 60,
        "dezenas_min": 6,
        "dezenas_max": 15,
        "colunas": ["bola1", "bola2", "bola3", "bola4", "bola5", "bola6"],
        "extras": [],
    },
    "Lotofácil": {
        "nome": "Lotofácil",
        "dezenas_total": 25,
        "dezenas_min": 15,
        "dezenas_max": 20,
        "colunas": [f"bola{i}" for i in range(1, 16)],
        "extras": [],
    },
    "Quina": {
        "nome": "Quina",
        "dezenas_total": 80,
        "dezenas_min": 5,
        "dezenas_max": 15,
        "colunas": ["bola1", "bola2", "bola3", "bola4", "bola5"],
        "extras": [],
    },
    "+Milionária": {
        "nome": "+Milionária",
        "dezenas_total": 50,
        "dezenas_min": 6,
        "dezenas_max": 10,
        "colunas": [f"bola{i}" for i in range(1, 7)],
        "extras": [
            {"nome": "Trevos", "total": 6, "min": 2, "max": 2, "colunas": ["trevo1", "trevo2"]},
        ],
    },
    "Dia de Sorte": {
        "nome": "Dia de Sorte",
        "dezenas_total": 31,
        "dezenas_min": 7,
        "dezenas_max": 15,
        "colunas": [f"bola{i}" for i in range(1, 8)],
        "extras": [
            {"nome": "Mês de Sorte", "total": 12, "min": 1, "max": 1, "colunas": ["mes_sorte"]},
        ],
    },
}

ESTRATEGIAS = ["Aleatório", "Mais Frequentes", "Pares Fortes", "Dezenas Atrasadas"]


def aplicar_tema():
    tema = st.session_state.get("tema", "Escuro")
    if tema == "Escuro":
        st.markdown(
            """
            <style>
            .stApp { background-color: #0e1117; color: #fafafa; }
            .stSidebar { background-color: #161b22; }
            section[data-testid="stSidebar"] { background-color: #161b22; }
            .stTabs [data-baseweb="tab"] { color: #c9d1d9; }
            .stTabs [aria-selected="true"] { color: #58a6ff !important; }
            </style>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <style>
            .stApp { background-color: #ffffff; color: #1f2328; }
            .stSidebar { background-color: #f6f8fa; }
            section[data-testid="stSidebar"] { background-color: #f6f8fa; }
            </style>
            """,
            unsafe_allow_html=True,
        )


def hash_arquivo(uploaded_file):
    if uploaded_file is None:
        return None
    try:
        uploaded_file.seek(0)
        conteudo = uploaded_file.read()
        uploaded_file.seek(0)
        return hashlib.md5(conteudo).hexdigest()
    except Exception:
        return None


def carregar_dados(uploaded_file, loteria_cfg):
    if uploaded_file is None:
        return None
    try:
        df = pd.read_csv(uploaded_file, sep=None, engine="python")
    except Exception:
        try:
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file)
        except Exception:
            return None
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def extrair_dezenas(df, loteria_cfg):
    cols = [c for c in loteria_cfg["colunas"] if c in df.columns]
    if not cols:
        return pd.DataFrame()
    sub = df[cols].copy()
    for c in sub.columns:
        sub[c] = pd.to_numeric(sub[c], errors="coerce")
    return sub


def calcular_frequencia(dezenas_df):
    if dezenas_df.empty:
        return pd.DataFrame(columns=["dezena", "frequencia"])
    valores = dezenas_df.values.flatten()
    valores = valores[~pd.isna(valores)]
    serie = pd.Series(valores).astype(int)
    contagem = serie.value_counts().reset_index()
    contagem.columns = ["dezena", "frequencia"]
    contagem = contagem.sort_values("dezena").reset_index(drop=True)
    return contagem


def calcular_atrasos(dezenas_df, total_dezenas):
    if dezenas_df.empty:
        return pd.DataFrame(columns=["dezena", "atraso"])
    n_conc = len(dezenas_df)
    atrasos = []
    for d in range(1, total_dezenas + 1):
        presente = dezenas_df.isin([d]).any(axis=1)
        if presente.empty or not presente.any():
            atrasos.append({"dezena": d, "atraso": n_conc})
        else:
            idx = presente[presente].index
            ultimo = idx.max()
            atrasos.append({"dezena": d, "atraso": int(n_conc - 1 - ultimo)})
    return pd.DataFrame(atrasos).sort_values("dezena").reset_index(drop=True)


def gerar_jogo(loteria_cfg, tamanho, estrategia, freq_df, atraso_df, rng):
    total = loteria_cfg["dezenas_total"]
    if estrategia == "Aleatório":
        return sorted(rng.sample(range(1, total + 1), tamanho))
    if estrategia == "Mais Frequentes" and not freq_df.empty:
        top = freq_df.sort_values("frequencia", ascending=False)["dezena"].tolist()
        pool = top[: max(tamanho * 3, tamanho)]
        return sorted(rng.sample(pool, tamanho))
    if estrategia == "Dezenas Atrasadas" and not atraso_df.empty:
        top = atraso_df.sort_values("atraso", ascending=False)["dezena"].tolist()
        pool = top[: max(tamanho * 3, tamanho)]
        return sorted(rng.sample(pool, tamanho))
    if estrategia == "Pares Fortes":
        pares = [d for d in range(1, total + 1) if d % 2 == 0]
        impares = [d for d in range(1, total + 1) if d % 2 != 0]
        n_pares = max(1, tamanho // 2)
        n_impares = tamanho - n_pares
        if n_pares > len(pares):
            n_pares = len(pares)
            n_impares = tamanho - n_pares
        return sorted(rng.sample(pares, n_pares) + rng.sample(impares, n_impares))
    return sorted(rng.sample(range(1, total + 1), tamanho))


def gerar_extras(loteria_cfg, rng):
    extras = {}
    for ex in loteria_cfg.get("extras", []):
        if ex["nome"] == "Mês de Sorte":
            extras["mes_sorte"] = rng.randint(1, ex["total"])
        elif ex["nome"] == "Trevos":
            extras["trevos"] = sorted(rng.sample(range(1, ex["total"] + 1), ex["min"]))
    return extras


def backtest(jogos, dezenas_df, loteria_cfg, extras_df=None):
    if dezenas_df.empty or not jogos:
        return pd.DataFrame()
    resultados = []
    for _, row in dezenas_df.iterrows():
        sorteadas = set(int(x) for x in row.tolist() if pd.notna(x))
        for j_idx, jogo in enumerate(jogos):
            acertos = len(set(jogo) & sorteadas)
            linha = {"concurso": _, "jogo": j_idx + 1, "acertos": acertos}
            if extras_df is not None and "mes_sorte" in extras_df.columns:
                linha["mes_sorte"] = extras_df.loc[_, "mes_sorte"]
            resultados.append(linha)
    return pd.DataFrame(resultados)


def main():
    st.title("🎲 Lottery Analyzer")
    st.caption("Análise de loterias, frequências, padrões, gerador de apostas e backtesting.")

    with st.sidebar:
        st.header("⚙️ Configurações")
        temas = ["Escuro", "Claro"]
        idx_tema = temas.index(st.session_state.get("tema", "Escuro")) if st.session_state.get("tema", "Escuro") in temas else 0
        tema = st.selectbox("Tema", temas, index=idx_tema, key="select_tema")
        st.session_state["tema"] = tema

        loteria_nomes = list(LOTERIAS.keys())
        loteria_sel = st.session_state.get("loteria", loteria_nomes[0])
        idx_lot = loteria_nomes.index(loteria_sel) if loteria_sel in loteria_nomes else 0
        loteria_nome = st.selectbox("Loteria", loteria_nomes, index=idx_lot, key="select_loteria")
        st.session_state["loteria"] = loteria_nome
        loteria_cfg = LOTERIAS[loteria_nome]

        st.divider()
        st.subheader("📂 Upload de Arquivo")
        uploaded_file = st.file_uploader("Envie o histórico (CSV/XLSX)", type=["csv", "xlsx"], key="file_uploader")

        hash_atual = hash_arquivo(uploaded_file)
        if hash_atual != st.session_state.get("hash_arquivo"):
            st.session_state["hash_arquivo"] = hash_atual
            st.session_state["dados_df"] = None
            st.session_state["dezenas_df"] = None
            st.session_state["extras_df"] = None

        if uploaded_file is not None and st.session_state.get("dados_df") is None:
            with st.spinner("Carregando dados..."):
                df = carregar_dados(uploaded_file, loteria_cfg)
                if df is not None and not df.empty:
                    st.session_state["dados_df"] = df
                    st.session_state["dezenas_df"] = extrair_dezenas(df, loteria_cfg)
                    extras_cols = []
                    for ex in loteria_cfg.get("extras", []):
                        extras_cols.extend([c for c in ex["colunas"] if c in df.columns])
                    if extras_cols:
                        st.session_state["extras_df"] = df[extras_cols].copy()
                    else:
                        st.session_state["extras_df"] = None
                    st.success(f"{len(df)} registros carregados.")
                else:
                    st.error("Não foi possível carregar os dados.")

    aplicar_tema()

    dados_df = st.session_state.get("dados_df")
    dezenas_df = st.session_state.get("dezenas_df")
    extras_df = st.session_state.get("extras_df")

    abas = st.tabs([
        "📋 Dados",
        "📈 Frequência & Atrasos",
        "🧩 Padrões",
        "🎰 Gerador de Apostas",
        "🔬 Backtesting",
        "📤 Exportação",
    ])

    with abas[0]:
        st.subheader(f"📋 Dados - {loteria_nome}")
        if dados_df is None:
            st.info("Envie um arquivo na sidebar para visualizar os dados.")
        else:
            st.metric("Total de concursos", len(dados_df))
            st.dataframe(dados_df.head(100), key="df_dados_head")
            st.dataframe(dados_df.describe(include="all"), key="df_dados_describe")

    with abas[1]:
        st.subheader(f"📈 Frequência & Atrasos - {loteria_nome}")
        if dezenas_df is None or dezenas_df.empty:
            st.info("Sem dados de dezenas disponíveis.")
        else:
            freq_df = calcular_frequencia(dezenas_df)
            atraso_df = calcular_atrasos(dezenas_df, loteria_cfg["dezenas_total"])

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Frequência de Dezenas**")
                fig = px.bar(freq_df, x="dezena", y="frequencia", title="Frequência")
                st.plotly_chart(fig, use_container_width=True, key="chart_freq")
                st.dataframe(freq_df, key="df_freq")
            with c2:
                st.markdown("**Atrasos de Dezenas**")
                fig2 = px.bar(atraso_df, x="dezena", y="atraso", title="Atraso")
                st.plotly_chart(fig2, use_container_width=True, key="chart_atraso")
                st.dataframe(atraso_df, key="df_atraso")

    with abas[2]:
        st.subheader(f"🧩 Padrões - {loteria_nome}")
        if dezenas_df is None or dezenas_df.empty:
            st.info("Sem dados para análise de padrões.")
        else:
            freq_df = calcular_frequencia(dezenas_df)
            matriz = []
            total = loteria_cfg["dezenas_total"]
            cols = 10 if total >= 25 else 6
            linhas = (total + cols - 1) // cols
            freq_map = dict(zip(freq_df["dezena"], freq_df["frequencia"]))
            for i in range(linhas):
                linha = []
                for j in range(cols):
                    d = i * cols + j + 1
                    if d <= total:
                        linha.append(freq_map.get(d, 0))
                    else:
                        linha.append(0)
                matriz.append(linha)
            fig3 = go.Figure(data=go.Heatmap(z=matriz, colorscale="Viridis"))
            fig3.update_layout(title="Mapa de Calor - Frequência")
            st.plotly_chart(fig3, use_container_width=True, key="chart_heatmap")

            st.markdown("**Pares vs Ímpares (média por concurso)**")
            pares = (dezenas_df % 2 == 0).sum(axis=1).mean()
            impares = (dezenas_df % 2 != 0).sum(axis=1).mean()
            st.metric("Média de Pares", round(float(pares), 2))
            st.metric("Média de Ímpares", round(float(impares), 2))

    with abas[3]:
        st.subheader(f"🎰 Gerador de Apostas - {loteria_nome}")
        c1, c2, c3 = st.columns(3)
        with c1:
            qtd_jogos = st.number_input("Quantidade de jogos", min_value=1, max_value=50, value=5, step=1, key="num_qtd_jogos")
        with c2:
            tamanho = st.number_input(
                f"Tamanho da aposta ({loteria_cfg['dezenas_min']}-{loteria_cfg['dezenas_max']})",
                min_value=loteria_cfg["dezenas_min"],
                max_value=loteria_cfg["dezenas_max"],
                value=loteria_cfg["dezenas_min"],
                step=1,
                key="num_tamanho",
            )
        with c3:
            estrategia = st.selectbox("Estratégia", ESTRATEGIAS, key="select_estrategia")

        seed = st.number_input("Seed (0 = aleatório)", min_value=0, value=0, step=1, key="num_seed")
        rng = np.random.default_rng(seed if seed > 0 else None)

        freq_df = calcular_frequencia(dezenas_df) if dezenas_df is not None and not dezenas_df.empty else pd.DataFrame()
        atraso_df = calcular_atrasos(dezenas_df, loteria_cfg["dezenas_total"]) if dezenas_df is not None and not dezenas_df.empty else pd.DataFrame()

        if st.button("🎯 Gerar Apostas", key="btn_gerar"):
            jogos = []
            for _ in range(int(qtd_jogos)):
                jogo = gerar_jogo(loteria_cfg, int(tamanho), estrategia, freq_df, atraso_df, rng)
                extras = gerar_extras(loteria_cfg, rng)
                jogos.append({"jogo": jogo, "extras": extras})
            st.session_state["jogos_gerados"] = jogos
            st.success(f"{len(jogos)} jogos gerados!")

        jogos = st.session_state.get("jogos_gerados", [])
        if jogos:
            st.markdown("**Apostas Geradas**")
            linhas = []
            for i, j in enumerate(jogos, 1):
                linha = {"#": i, "Dezenas": " ".join(f"{d:02d}" for d in j["jogo"])}
                for k, v in j["extras"].items():
                    if isinstance(v, list):
                        linha[k] = " ".join(f"{x:02d}" for x in v)
                    else:
                        linha[k] = v
                linhas.append(linha)
            st.dataframe(pd.DataFrame(linhas), key="df_jogos_gerados")

    with abas[4]:
        st.subheader(f"🔬 Backtesting - {loteria_nome}")
        jogos = st.session_state.get("jogos_gerados", [])
        if dezenas_df is None or dezenas_df.empty:
            st.info("Sem dados para backtesting.")
        elif not jogos:
            st.info("Gere apostas na aba 'Gerador de Apostas' primeiro.")
        else:
            jogos_dezenas = [j["jogo"] for j in jogos]
            bt = backtest(jogos_dezenas, dezenas_df, loteria_cfg, extras_df)
            if bt.empty:
                st.warning("Nenhum resultado de backtesting.")
            else:
                st.metric("Total de comparações", len(bt))
                resumo = bt.groupby("acertos").size().reset_index(name="quantidade")
                fig4 = px.bar(resumo, x="acertos", y="quantidade", title="Distribuição de Acertos")
                st.plotly_chart(fig4, use_container_width=True, key="chart_backtest")
                st.dataframe(bt.head(200), key="df_backtest")
                st.markdown("**Resumo por jogo**")
                resumo_jogo = bt.groupby("jogo")["acertos"].agg(["min", "mean", "max"]).reset_index()
                st.dataframe(resumo_jogo, key="df_backtest_resumo")

    with abas[5]:
        st.subheader(f"📤 Exportação - {loteria_nome}")
        if dados_df is None:
            st.info("Carregue dados para exportar.")
        else:
            freq_df = calcular_frequencia(dezenas_df) if dezenas_df is not None and not dezenas_df.empty else pd.DataFrame()
            atraso_df = calcular_atrasos(dezenas_df, loteria_cfg["dezenas_total"]) if dezenas_df is not None and not dezenas_df.empty else pd.DataFrame()
            jogos = st.session_state.get("jogos_gerados", [])

            if st.button("⬇️ Gerar Excel", key="btn_exportar"):
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    dados_df.to_excel(writer, sheet_name="Dados", index=False)
                    if not freq_df.empty:
                        freq_df.to_excel(writer, sheet_name="Frequencia", index=False)
                    if not atraso_df.empty:
                        atraso_df.to_excel(writer, sheet_name="Atrasos", index=False)
                    if jogos:
                        linhas = []
                        for i, j in enumerate(jogos, 1):
                            linha = {"#": i, "Dezenas": " ".join(str(d) for d in j["jogo"])}
                            for k, v in j["extras"].items():
                                linha[k] = " ".join(str(x) for x in v) if isinstance(v, list) else v
                            linhas.append(linha)
                        pd.DataFrame(linhas).to_excel(writer, sheet_name="Apostas", index=False)
                output.seek(0)
                st.download_button(
                    label="📥 Baixar Excel",
                    data=output,
                    file_name=f"lottery_{loteria_nome.lower().replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="btn_download_excel",
                )
                st.success("Excel gerado com sucesso!")


if __name__ == "__main__":
    main()
