import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc

# ============================================================
# Configurações do App
# ============================================================

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Motor Dia de Sorte"

THEMES = {
    "Branco": {
        "bg": "#FFFFFF",
        "card_bg": "#F8F9FA",
        "text": "#212529",
        "primary": "#007BFF",
        "accent": "#17A2B8",
    },
    "Azul": {
        "bg": "#0B1D3A",
        "card_bg": "#13284C",
        "text": "#E9ECEF",
        "primary": "#4DA3FF",
        "accent": "#28A745",
    },
}

MESES_PT = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}

# ============================================================
# Funções de Dados
# ============================================================

def carregar_dados_dia_de_sorte(caminho_arquivo=None):
    """
    Carrega os dados dos concursos Dia de Sorte.
    Se nenhum arquivo for fornecido, gera dados simulados.
    Retorna um DataFrame com as colunas:
      - Concurso
      - Data
      - N1..N7 (dezenas sorteadas)
      - Mes_Sorte (1 a 12)
    """
    if caminho_arquivo:
        df = pd.read_csv(caminho_arquivo)
    else:
        # Dados simulados para demonstração
        np.random.seed(42)
        num_concursos = 200
        concursos = list(range(1, num_concursos + 1))
        datas = pd.date_range(start="2018-01-15", periods=num_concursos, freq="W").strftime("%d/%m/%Y")

        dezenas = []
        for _ in range(num_concursos):
            nums = sorted(np.random.choice(range(1, 32), 7, replace=False))
            dezenas.append(nums)

        df = pd.DataFrame(dezenas, columns=[f"N{i}" for i in range(1, 8)])
        df.insert(0, "Concurso", concursos)
        df.insert(1, "Data", datas)

    # Gera array de meses (1 a 12) e adiciona como coluna 'Mes_Sorte'
    if "Mes_Sorte" not in df.columns:
        if "Mes" in df.columns:
            df["Mes_Sorte"] = df["Mes"]
        else:
            # Se não houver coluna de mês, gera aleatoriamente entre 1 e 12
            np.random.seed(99)
            df["Mes_Sorte"] = np.random.randint(1, 13, size=len(df))

    # Garante que Mes_Sorte seja inteiro entre 1 e 12
    df["Mes_Sorte"] = df["Mes_Sorte"].astype(int).clip(1, 12)

    return df


def analisar_frequencia_numeros(df_sorte):
    """Calcula a frequência de cada dezena (1 a 31)."""
    dezenas_cols = [c for c in df_sorte.columns if c.startswith("N") and c[1:].isdigit()]
    todos_numeros = df_sorte[dezenas_cols].values.flatten()
    contagem = pd.Series(todos_numeros).value_counts().reindex(range(1, 32), fill_value=0)

    total_sorteios = len(df_sorte)
    esperado = (total_sorteios * 7) / 31

    resultado = pd.DataFrame({
        "Dezena": contagem.index,
        "Frequência": contagem.values,
        "Esperado": esperado,
    })
    resultado["Força (Real/Esperado)"] = resultado["Frequência"] / resultado["Esperado"]
    resultado = resultado.sort_values("Frequência", ascending=False).reset_index(drop=True)
    return resultado


def analisar_mes_de_sorte(df_sorte):
    """
    Calcula a frequência real de cada mês sorteado (1 a 12),
    compara com a frequência esperada (total de concursos / 12)
    e calcula a 'Força (Real/Esperado)'.
    Mapeia os números para os nomes dos meses em português.
    """
    total_concursos = len(df_sorte)
    esperado = total_concursos / 12

    contagem = df_sorte["Mes_Sorte"].value_counts().reindex(range(1, 13), fill_value=0)

    resultado = pd.DataFrame({
        "Mês": list(range(1, 13)),
        "Nome do Mês": [MESES_PT[m] for m in range(1, 13)],
        "Frequência": contagem.values,
        "Esperado": [esperado] * 12,
    })
    resultado["Força (Real/Esperado)"] = resultado["Frequência"] / resultado["Esperado"]
    resultado = resultado.sort_values("Força (Real/Esperado)", ascending=False).reset_index(drop=True)

    return resultado


def analisar_atraso_numeros(df_sorte):
    """Calcula o atraso (quantos concursos desde a última aparição) de cada dezena."""
    dezenas_cols = [c for c in df_sorte.columns if c.startswith("N") and c[1:].isdigit()]
    ultimo_concurso = df_sorte["Concurso"].max()

    atrasos = {}
    for num in range(1, 32):
        aparicoes = df_sorte[df_sorte[dezenas_cols].apply(lambda row: num in row.values, axis=1)]
        if len(aparicoes) > 0:
            ultimo = aparicoes["Concurso"].max()
            atrasos[num] = ultimo_concurso - ultimo
        else:
            atrasos[num] = ultimo_concurso

    resultado = pd.DataFrame({
        "Dezena": list(atrasos.keys()),
        "Atraso": list(atrasos.values()),
    })
    resultado = resultado.sort_values("Atraso", ascending=False).reset_index(drop=True)
    return resultado


# ============================================================
# Layout do Dashboard
# ============================================================

def render_dashboard(df_sorte):
    """
    Renderiza o dashboard completo com abas:
      1. Visão Geral
      2. Frequência de Números
      3. Atraso de Números
      4. Mês de Sorte
    Mantém os temas Branco e Azul intactos.
    """
    freq_df = analisar_frequencia_numeros(df_sorte)
    atraso_df = analisar_atraso_numeros(df_sorte)
    mes_df = analisar_mes_de_sorte(df_sorte)

    total_concursos = len(df_sorte)

    # --- Gráficos ---

    # Gráfico de frequência de números
    fig_freq = px.bar(
        freq_df,
        x="Dezena",
        y="Frequência",
        title="Frequência das Dezenas",
        color="Força (Real/Esperado)",
        color_continuous_scale="Viridis",
    )
    fig_freq.update_layout(template="plotly_white")

    # Gráfico de atraso
    fig_atraso = px.bar(
        atraso_df,
        x="Dezena",
        y="Atraso",
        title="Atraso das Dezenas (concursos sem aparecer)",
        color="Atraso",
        color_continuous_scale="Inferno",
    )
    fig_atraso.update_layout(template="plotly_white")

    # Gráfico do Mês de Sorte
    fig_mes = px.bar(
        mes_df,
        x="Nome do Mês",
        y="Força (Real/Esperado)",
        title="Força do Mês de Sorte (Real / Esperado)",
        color="Força (Real/Esperado)",
        color_continuous_scale="Blues",
        text=mes_df["Força (Real/Esperado)"].round(3),
    )
    fig_mes.update_layout(
        template="plotly_white",
        xaxis_title="Mês",
        yaxis_title="Força (Real/Esperado)",
        xaxis={"categoryorder": "array", "categoryarray": mes_df["Nome do Mês"].tolist()},
    )
    fig_mes.update_traces(textposition="outside")

    # --- Layout ---

    layout = dbc.Container(
        [
            # Seletor de tema
            dbc.Row(
                [
                    dbc.Col(
                        html.H1("🎯 Motor Dia de Sorte", className="mt-4 mb-2"),
                        width="auto",
                    ),
                    dbc.Col(
                        dcc.Dropdown(
                            id="theme-selector",
                            options=[{"label": t, "value": t} for t in THEMES.keys()],
                            value="Branco",
                            clearable=False,
                            style={"width": "150px", "marginTop": "30px"},
                        ),
                        width="auto",
                        className="ms-auto",
                    ),
                ],
                className="mb-4",
            ),

            # Cards de resumo
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody([
                                html.H5("Total de Concursos", className="card-title"),
                                html.H2(str(total_concursos), className="card-text"),
                            ]),
                            id="card-total",
                            className="mb-3",
                        ),
                        width=3,
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody([
                                html.H5("Dezena Mais Frequente", className="card-title"),
                                html.H2(f"{freq_df.iloc[0]['Dezena']:.0f}", className="card-text"),
                            ]),
                            id="card-freq",
                            className="mb-3",
                        ),
                        width=3,
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody([
                                html.H5("Mês Mais Sorteado", className="card-title"),
                                html.H2(mes_df.iloc[0]["Nome do Mês"], className="card-text"),
                            ]),
                            id="card-mes",
                            className="mb-3",
                        ),
                        width=3,
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody([
                                html.H5("Dezena Mais Atrasada", className="card-title"),
                                html.H2(f"{atraso_df.iloc[0]['Dezena']:.0f}", className="card-text"),
                            ]),
                            id="card-atraso",
                            className="mb-3",
                        ),
                        width=3,
                    ),
                ],
                className="mb-4",
            ),

            # Abas
            dcc.Tabs(
                id="tabs",
                value="tab-visao",
                children=[
                    dcc.Tab(
                        label="Visão Geral",
                        value="tab-visao",
                        children=[
                            dbc.Row(
                                [
                                    dbc.Col(dcc.Graph(figure=fig_freq), width=6),
                                    dbc.Col(dcc.Graph(figure=fig_atraso), width=6),
                                ],
                                className="mt-4",
                            ),
                        ],
                    ),
                    dcc.Tab(
                        label="Frequência de Números",
                        value="tab-freq",
                        children=[
                            html.Div(
                                [
                                    dcc.Graph(figure=fig_freq, className="mt-4"),
                                    html.H4("Tabela de Frequência", className="mt-4 mb-3"),
                                    dash_table.DataTable(
                                        data=freq_df.to_dict("records"),
                                        columns=[
                                            {"name": c, "id": c} for c in freq_df.columns
                                        ],
                                        style_table={"overflowX": "auto"},
                                        style_cell={
                                            "textAlign": "center",
                                            "padding": "8px",
                                        },
                                        style_header={
                                            "backgroundColor": "#007BFF",
                                            "color": "white",
                                            "fontWeight": "bold",
                                        },
                                        style_data_conditional=[
                                            {
                                                "if": {"row_index": "odd"},
                                                "backgroundColor": "#F8F9FA",
                                            }
                                        ],
                                    ),
                                ],
                                className="mt-2",
                            ),
                        ],
                    ),
                    dcc.Tab(
                        label="Atraso de Números",
                        value="tab-atraso",
                        children=[
                            html.Div(
                                [
                                    dcc.Graph(figure=fig_atraso, className="mt-4"),
                                    html.H4("Tabela de Atraso", className="mt-4 mb-3"),
                                    dash_table.DataTable(
                                        data=atraso_df.to_dict("records"),
                                        columns=[
                                            {"name": c, "id": c} for c in atraso_df.columns
                                        ],
                                        style_table={"overflowX": "auto"},
                                        style_cell={
                                            "textAlign": "center",
                                            "padding": "8px",
                                        },
                                        style_header={
                                            "backgroundColor": "#007BFF",
                                            "color": "white",
                                            "fontWeight": "bold",
                                        },
                                        style_data_conditional=[
                                            {
                                                "if": {"row_index": "odd"},
                                                "backgroundColor": "#F8F9FA",
                                            }
                                        ],
                                    ),
                                ],
                                className="mt-2",
                            ),
                        ],
                    ),
                    dcc.Tab(
                        label="Mês de Sorte",
                        value="tab-mes",
                        children=[
                            html.Div(
                                [
                                    dcc.Graph(figure=fig_mes, className="mt-4"),
                                    html.H4("Tabela do Mês de Sorte", className="mt-4 mb-3"),
                                    dash_table.DataTable(
                                        data=mes_df.to_dict("records"),
                                        columns=[
                                            {"name": c, "id": c} for c in mes_df.columns
                                        ],
                                        style_table={"overflowX": "auto"},
                                        style_cell={
                                            "textAlign": "center",
                                            "padding": "8px"},
                                        style_header={
                                            "backgroundColor": "#007BFF",
                                            "color": "white",
                                            "fontWeight": "bold",
                                        },
                                        style_data_conditional=[
                                            {
                                                "if": {"row_index": "odd"},
                                                "backgroundColor": "#F8F9FA",
                                            }
                                        ],
                                    ),
                                ],
                                className="mt-2",
                            ),
                        ],
                    ),
                ],
                className="mt-2",
            ),
        ],
        fluid=True,
        id="main-container",
    )

    return layout


# ============================================================
# Callbacks de Tema
# ============================================================

@app.callback(
    [
        Output("main-container", "style"),
        Output("card-total", "style"),
        Output("card-freq", "style"),
        Output("card-mes", "style"),
        Output("card-atraso", "style"),
    ],
    [Input("theme-selector", "value")],
)
def atualizar_tema(tema_nome):
    """Atualiza as cores do dashboard conforme o tema selecionado."""
    t = THEMES.get(tema_nome, THEMES["Branco"])

    main_style = {
        "backgroundColor": t["bg"],
        "color": t["text"],
        "minHeight": "100vh",
        "padding": "20px",
    }

    card_style = {
        "backgroundColor": t["card_bg"],
        "color": t["text"],
        "border": f"1px solid {t['primary']}",
    }

    return main_style, card_style, card_style, card_style, card_style


# ============================================================
# Inicialização
# ============================================================

# Carrega os dados
df_dia_sorte = carregar_dados_dia_de_sorte()

# Define o layout
app.layout = render_dashboard(df_dia_sorte)


if __name__ == "__main__":
    app.run(debug=True, port=8050)
