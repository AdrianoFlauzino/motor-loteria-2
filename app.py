# === app.py ===
import streamlit as st
import random

st.set_page_config(page_title="Motor Loteria 2", page_icon="🎰", layout="wide")

st.title("🎰 Motor Loteria 2")
st.markdown("---")

# Limpa session state ao recarregar
if 'clear' not in st.session_state:
    st.session_state.clear()
    st.session_state.clear = True

tab1, tab2, tab3 = st.tabs(["Mega-Sena", "Quina", "Lotofácil"])

with tab1:
    st.header("Mega-Sena (6 números de 1 a 60)")
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🎲 Gerar Jogo", key="mega"):
            st.session_state.mega_numbers = sorted(random.sample(range(1, 61), 6))
            st.rerun()
    with col2:
        if 'mega_numbers' in st.session_state:
            st.success(f"✅ Números gerados: **{', '.join(map(str, st.session_state.mega_numbers))}**")
        else:
            st.info("Clique no botão para gerar um jogo!")

with tab2:
    st.header("Quina (5 números de 1 a 80)")
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🎲 Gerar Jogo", key="quina"):
            st.session_state.quina_numbers = sorted(random.sample(range(1, 81), 5))
            st.rerun()
    with col2:
        if 'quina_numbers' in st.session_state:
            st.success(f"✅ Números gerados: **{', '.join(map(str, st.session_state.quina_numbers))}**")
        else:
            st.info("Clique no botão para gerar um jogo!")

with tab3:
    st.header("Lotofácil (15 números de 1 a 25)")
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🎲 Gerar Jogo", key="lotofacil"):
            st.session_state.lotofacil_numbers = sorted(random.sample(range(1, 26), 15))
            st.rerun()
    with col2:
        if 'lotofacil_numbers' in st.session_state:
            st.success(f"✅ Números gerados: **{', '.join(map(str, st.session_state.lotofacil_numbers))}**")
        else:
            st.info("Clique no botão para gerar um jogo!")

st.markdown("---")
st.caption("Motor Loteria 2 - Gerador de jogos para loterias brasileiras. Boa sorte! 🍀")

# === requirements.txt ===
streamlit
