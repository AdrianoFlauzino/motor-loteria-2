import streamlit as st
import numpy as np
import pandas as pd
import random
from collections import Counter, defaultdict
import json
from datetime import datetime

st.set_page_config(page_title="MultiLoterias Enterprise Premium", page_icon="🤑", layout="wide")

# Configurações das Loterias
LOTTERIES = {
    "Mega-Sena": {"nums": 6, "min": 1, "max": 60},
    "Quina": {"nums": 5, "min": 1, "max": 80},
    "Lotofácil": {"nums": 15, "min": 1, "max": 25},
    "Lotomania": {"nums": 50, "min": 0, "max": 99},
    "Dupla Sena": {"nums": 6, "min": 1, "max": 50},
    "Timemania": {"nums": 7, "min": 1, "max": 80}
}

# Inicializar estado da sessão
if 'bets' not in st.session_state:
    st.session_state.bets = []
if 'results' not in st.session_state:
    st.session_state.results = {}
if 'stats' not in st.session_state:
    st.session_state.stats = defaultdict(int)

st.sidebar.title("🤑 MultiLoterias Enterprise Premium")
st.sidebar.markdown("**Modo B2 Didático**")

lottery = st.sidebar.selectbox("Selecione a Loteria:", list(LOTTERIES.keys()))
rules = LOTTERIES[lottery]

# Cabeçalho principal
col1, col2 = st.columns([3,1])
with col1:
    st.title(f"{lottery} - Gerenciador Premium")
with col2:
    st.metric("Jogos Salvos", len(st.session_state.bets))

# Abas principais
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Gerar Jogos", "Verificar Resultados", "Estatísticas", "Meus Jogos", "Configurações"])

with tab1:
    st.header("Gerador de Jogos")
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Aleatório Simples")
        num_games = st.slider("Número de Jogos", 1, 50, 5)
        if st.button("Gerar Aleatório", key="random"):
            for i in range(num_games):
                game = sorted(random.sample(range(rules["min"], rules["max"]+1), rules["nums"]))
                st.write(f"**Jogo {i+1}:** {' | '.join(f'{n:02d}' for n in game)}")
                if st.button(f"Salvar Jogo {i+1}", key=f"save_{i}"):
                    st.session_state.bets.append({"lottery": lottery, "game": game, "date": datetime.now().strftime("%d/%m/%Y %H:%M")})
                    st.success("Jogo salvo!")
    with col_b:
        st.subheader("Sistema de Fechamento (Wheeling)")
        nums_select = st.multiselect("Escolha números base:", range(rules["min"], rules["max"]+1), max_selections=15)
        if len(nums_select) >= rules["nums"] and st.button("Gerar Fechamento"):
            # Simulação simples de fechamento
            games = []
            for _ in range(min(10, 2**len(nums_select)//10)):
                game = sorted(random.sample(nums_select, rules["nums"]))
                games.append(game)
            for i, game in enumerate(games):
                st.write(f"Fech. {i+1}: {' | '.join(f'{n:02d}' for n in game)}")

with tab2:
    st.header("Verificar Resultados")
    result_input = st.text_input("Digite o resultado do concurso (números separados por vírgula):")
    if st.button("Salvar Resultado") and result_input:
        try:
            nums = [int(x.strip()) for x in result_input.split(',')]
            st.session_state.results[lottery] = sorted(nums)
            st.success("Resultado salvo!")
        except:
            st.error("Formato inválido!")
    if st.session_state.results.get(lottery):
        st.info(f"**Resultado Atual ({lottery}):** {' | '.join(f'{n:02d}' for n in st.session_state.results[lottery])}")
        # Verificar jogos salvos
        for bet in st.session_state.bets:
            if bet["lottery"] == lottery:
                hits = len(set(bet["game"]) & set(st.session_state.results[lottery]))
                st.metric(f"Jogo: {' | '.join(f'{n:02d}' for n in bet['game'])}", hits)

with tab3:
    st.header("Estatísticas e Análises")
    expander1 = st.expander("Números Mais Sorteados (Simulação)")
    with expander1:
        sim_games = 1000
        all_nums = []
        for _ in range(sim_games):
            all_nums.extend(random.sample(range(rules["min"], rules["max"]+1), rules["nums"]))
        freq = Counter(all_nums)
        df_freq = pd.DataFrame([{"Num": k, "Freq": v} for k,v in freq.most_common(20)])
        st.bar_chart(df_freq.set_index("Num"))
    expander2 = st.expander("Números Frios")
    with expander2:
        least_freq = Counter(all_nums).most_common()[-20:]
        df_cold = pd.DataFrame([{"Num": k, "Freq": v} for k,v in least_freq])
        st.bar_chart(df_cold.set_index("Num"))

with tab4:
    st.header("Meus Jogos Salvos")
    if st.session_state.bets:
        df_bets = pd.DataFrame(st.session_state.bets)
        st.dataframe(df_bets)
        if st.button("Limpar Todos"):
            st.session_state.bets = []
            st.rerun()
    else:
        st.info("Nenhum jogo salvo.")

with tab5:
    st.header("Exportar / Importar")
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        if st.button("Exportar JSON"):
            data = {"bets": st.session_state.bets, "results": st.session_state.results}
            st.download_button("Baixar dados.json", json.dumps(data, indent=2, ensure_ascii=False), "data.json")
    with col_exp2:
        uploaded = st.file_uploader("Importar JSON")
        if uploaded:
            data = json.load(uploaded)
            st.session_state.bets = data.get("bets", [])
            st.session_state.results = data.get("results", {})
            st.success("Dados importados!")

# Rodapé
st.markdown("---")
st.markdown("*MultiLoterias Enterprise Premium - Modo B2 Didático | Para fins educacionais.*")
