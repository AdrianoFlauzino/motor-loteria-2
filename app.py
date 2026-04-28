import streamlit as st
import pandas as pd
import filtros
import estatisticas
import gerador
import backtesting

# Configuração da página
st.set_page_config(page_title="Motor Loteria 2.0", page_icon="🎰", layout="wide")

st.title("🎰 Motor Loteria 2.0")

# Inicialização do estado da sessão para os dados
if 'df' not in st.session_state:
    st.session_state.df = None

# Menu lateral
page = st.sidebar.selectbox("Navegação", ["Análise", "Gerar Bilhetes", "Backtesting", "Configurações"])

if page == "Análise":
    st.header("Análise Estatística")
    # Upload de arquivo CSV
    uploaded_file = st.file_uploader("Carregue o arquivo CSV com resultados da loteria", type="csv")
    if uploaded_file is not None:
        st.session_state.df = pd.read_csv(uploaded_file)
        df = st.session_state.df
        st.success(f"Dados carregados: {len(df)} sorteios.")
        # Abas para exibir estatísticas
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Frequência", "Atraso", "Quadrantes", "Soma", "Paridade"])
        with tab1:
            st.dataframe(estaticas.frequencia(df))
        with tab2:
            st.dataframe(estaticas.atraso(df))
        with tab3:
            st.dataframe(estaticas.quadrantes(df))
        with tab4:
            st.dataframe(estaticas.soma(df))
        with tab5:
            st.dataframe(estaticas.paridade(df))
    else:
        st.info("\u2699️ Faça upload de um arquivo CSV para visualizar as análises.")

elif page == "Gerar Bilhetes":
    st.header("Gerador de Bilhetes")
    df = st.session_state.df
    if df is not None:
        estrategia = st.selectbox("Escolha a estratégia", ["conservador", "agressivo", "híbrido", "ponderado"])
        quantidade = st.number_input("Quantidade de bilhetes", min_value=1, max_value=100, value=10)
        if st.button("Gerar Bilhetes", type="primary"):
            with st.spinner("Gerando bilhetes..."):
                bilhetes = gerador.gerar_bilhetes(estrategia, quantidade, df)
            st.success(f"{len(bilhetes)} bilhetes gerados!")
            st.dataframe(bilhetes)
    else:
        st.warning("⚠️ Carregue os dados históricos na página 'Análise' primeiro.")

elif page == "Backtesting":
    st.header("Backtesting")
    df = st.session_state.df
    if df is not None:
        if st.button("Executar Backtesting", type="primary"):
            with st.spinner("Executando backtesting..."):
                resultado = backtesting.resumo_backtesting(df)
            st.subheader("Resultados do Backtesting")
            st.dataframe(resultado)
            # Exibe métricas básicas (assumindo colunas no resultado)
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Acertos Totais", resultado['acertos'].sum() if 'acertos' in resultado.columns else 0)
            with col2:
                st.metric("Taxa de Sucesso", f"{resultado['sucesso'].mean():.2%}" if 'sucesso' in resultado.columns else "0%")
            with col3:
                st.metric("ROI Médio", f"R$ {resultado['roi'].mean():.2f}" if 'roi' in resultado.columns else "R$ 0.00")
            with col4:
                st.metric("Melhor Desempenho", resultado['melhor'].max() if 'melhor' in resultado.columns else 0)
    else:
        st.warning("⚠️ Carregue os dados históricos na página 'Análise' primeiro.")

elif page == "Configurações":
    st.header("Configurações")
    st.markdown("""
    ## Parâmetros Disponíveis
    
    ### Estratégias de Geração
    - **Conservador**: Prioriza números frêcos e atrasados.
    - **Agressivo**: Foca em números quentes e frequentes.
    - **Híbrido**: Combina quente/frio e atraso.
    - **Ponderado**: Usa pesos estatísticos avançados.
    
    ### Outras Configurações
    - Quantidade de bilhetes: 1 a 100.
    - Dados: CSV com colunas de números (ex: n1 a n6).
    
    *Nota: Alterações dinâmicas não implementadas. Edite os módulos para customizações.*
    """)
