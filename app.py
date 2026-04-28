import streamlit as st
import pandas as pd
import numpy as np
from estatisticas import (
    calcular_frequencia,
    calcular_atraso,
    calcular_pares_correlacao,
    calcular_distribuicao_quadrante,
    calcular_estatisticas_soma,
    calcular_estatisticas_paridade,
    calcular_estatisticas_primos,
    calcular_estatisticas_altas_baixas
)

def padronizar_colunas(df):
    """
    Padroniza as colunas do DataFrame, detectando exatamente 6 colunas numéricas
    e renomeando para n1 a n6. Inverte a ordem para exibir o mais recente primeiro.
    """
    colunas_numericas = df.select_dtypes(include=['number']).columns.tolist()
    if len(colunas_numericas) != 6:
        return None, f"Erro: O arquivo deve conter exatamente 6 colunas numéricas. Encontradas {len(colunas_numericas)} colunas: {colunas_numericas}"
    
    mapeamento = {colunas_numericas[i]: f'n{i+1}' for i in range(6)}
    df = df.rename(columns=mapeamento).copy()
    
    # Inverte a ordem das linhas (mais recente primeiro)
    df = df.iloc[::-1].reset_index(drop=True)
    
    return df, None

# Configuração da página
st.set_page_config(
    page_title="Analisador de Loterias",
    page_icon="🔮",
    layout="wide"
)

# Título e descrição
st.title("🔮 Analisador de Estatísticas de Loterias")
st.markdown("*Carregue um arquivo CSV com os resultados (6 colunas numéricas por sorteio) e explore as estatísticas detalhadas.*")
st.markdown("---")

# Upload do arquivo
uploaded_file = st.file_uploader(
    "**Escolha um arquivo CSV**",
    type="csv",
    help="O arquivo deve ter pelo menos 6 colunas numéricas representando os números sorteados."
)

if uploaded_file is not None:
    try:
        # Leitura do CSV
        df = pd.read_csv(uploaded_file)
        
        if df.empty:
            st.error("O arquivo CSV está vazio.")
            st.stop()
        
        # Padronização das colunas
        df_padronizado, erro_padrao = padronizar_colunas(df)
        if erro_padrao:
            st.error(erro_padrao)
            st.stop()
        
        st.success("✅ Arquivo carregado e padronizado com sucesso!")
        
        # Exibe preview do DataFrame
        st.markdown("### 📋 Preview dos Dados Padronizados")
        st.dataframe(df_padronizado.head(10), use_container_width=True)
        
        # Botão para baixar modelo CSV (após upload)
        st.markdown("---")
        cols_modelo = [f'n{i+1}' for i in range(6)]
        modelo_df = pd.DataFrame(
            np.random.randint(1, 61, size=(10, 6)),
            columns=cols_modelo
        )
        csv_modelo = modelo_df.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="📥 Baixar modelo CSV",
            data=csv_modelo,
            file_name="modelo_loteria.csv",
            mime="text/csv",
            help="Baixe este modelo, preencha com seus dados e faça upload."
        )
        
        # Abas para as estatísticas
        st.markdown("---")
        tabs = st.tabs([
            "📊 Frequência",
            "⏱️ Atraso",
            "🧩 Quadrantes",
            "➕ Soma",
            "⚖️ Paridade",
            "🔢 Primos",
            "📈 Altas/Baixas"
        ])
        
        with tabs[0]:  # Frequência
            st.subheader("Frequência dos Números")
            freq_data = calcular_frequencia(df_padronizado)
            st.dataframe(freq_data, use_container_width=True)
            
        with tabs[1]:  # Atraso
            st.subheader("Atraso dos Números")
            atraso_data = calcular_atraso(df_padronizado)
            st.dataframe(atraso_data, use_container_width=True)
            
        with tabs[2]:  # Quadrantes
            st.subheader("Distribuição por Quadrantes")
            quad_data = calcular_distribuicao_quadrante(df_padronizado)
            st.dataframe(quad_data, use_container_width=True)
            
            st.subheader("Pares de Correlação")
            corr_data = calcular_pares_correlacao(df_padronizado)
            st.dataframe(corr_data, use_container_width=True)
            
        with tabs[3]:  # Soma
            st.subheader("Estatísticas de Soma")
            soma_data = calcular_estatisticas_soma(df_padronizado)
            st.dataframe(soma_data, use_container_width=True)
            
        with tabs[4]:  # Paridade
            st.subheader("Estatísticas de Paridade")
            paridade_data = calcular_estatisticas_paridade(df_padronizado)
            st.dataframe(paridade_data, use_container_width=True)
            
        with tabs[5]:  # Primos
            st.subheader("Estatísticas de Números Primos")
            primos_data = calcular_estatisticas_primos(df_padronizado)
            st.dataframe(primos_data, use_container_width=True)
            
        with tabs[6]:  # Altas/Baixas
            st.subheader("Estatísticas Altas / Baixas")
            altas_baixas_data = calcular_estatisticas_altas_baixas(df_padronizado)
            st.dataframe(altas_baixas_data, use_container_width=True)
            
    except Exception as e:
        st.error(f"❌ Erro ao processar o arquivo: {str(e)}")
        st.info("Verifique se o arquivo é um CSV válido com dados numéricos.")
else:
    st.info("👆 **Carregue um arquivo CSV para iniciar a análise!**")
    st.markdown("*Dica: Use o botão \"Baixar modelo CSV\" após o primeiro upload para obter um template.*")

st.markdown("---")
st.markdown("*Desenvolvido para análise de loterias como Mega-Sena. Pronto para deploy no Streamlit Cloud.*")
