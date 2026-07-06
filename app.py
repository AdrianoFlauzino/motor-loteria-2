import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import itertools
import random
import json
from io import BytesIO
from collections import Counter
from datetime import datetime, timedelta

try:
    import requests
except ImportError:
    requests = None

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# ============================================================
# CONFIGURAÇÃO DAS LOTERIAS
# ============================================================
LOTTERIES = {
    "Mega Sena": {
        "slug": "megasena",
        "dezenas_total": 60,
        "dezenas_aposta": 6,
        "max_acertos": 6,
        "premios": {4: "Quadra", 5: "Quina", 6: "Sena"},
        "premios_estimados": {
            "Quadra": 1000.00,
            "Quina": 50000.00,
            "Sena": 30000000.00,
        },
        "custo_aposta": 5.00,
        "color": "green",
    },
    "Lotofácil": {
        "slug": "lotofacil",
        "dezenas_total": 25,
        "dezenas_aposta": 15,
        "max_acertos": 15,
        "premios": {11: "11 Acertos", 12: "12 Acertos", 13: "13 Acertos", 14: "14 Acertos", 15: "15 Acertos"},
        "premios_estimados": {
            "11 Acertos": 8.00,
            "12 Acertos": 20.00,
            "13 Acertos": 60.00,
            "14 Acertos": 2000.00,
            "15 Acertos": 2000000.00,
        },
        "custo_aposta": 3.00,
        "color": "purple",
    },
    "Quina": {
        "slug": "quina",
        "dezenas_total": 80,
        "dezenas_aposta": 5,
        "max_acertos": 5,
        "premios": {2: "Duque", 3: "Terno", 4: "Quadra", 5: "Quina"},
        "premios_estimados": {
            "Duque": 2.00,
            "Terno": 15.00,
            "Quadra": 3000.00,
            "Quina": 500000.00,
        },
        "custo_aposta": 2.50,
        "color": "blue",
    },
    "+Milionária": {
        "slug": "maismilionaria",
        "dezenas_total": 50,
        "dezenas_aposta": 6,
        "max_acertos": 6,
        "premios": {4: "Quadra", 5: "Quina", 6: "Sena"},
        "premios_estimados": {
            "Quadra": 2000.00,
            "Quina": 30000.00,
            "Sena": 100000000.00,
        },
        "custo_aposta": 6.00,
        "color": "orange",
    },
    "Dia de Sorte": {
        "slug": "diadesorte",
        "dezenas_total": 31,
        "dezenas_aposta": 7,
        "max_acertos": 7,
        "premios": {4: "4 Acertos", 5: "5 Acertos", 6: "6 Acertos", 7: "7 Acertos + Mês de Sorte"},
        "premios_estimados": {
            "4 Acertos": 20.00,
            "5 Acertos": 500.00,
            "6 Acertos": 10000.00,
            "7 Acertos + Mês de Sorte": 500000.00,
        },
        "custo_aposta": 3.00,
        "color": "pink",
    },
}

THEME_COLORS = {
    "Branco": {"bg": "#FFFFFF", "text": "#1E3A5F", "accent": "#1E90FF", "card": "#F0F8FF"},
    "Azul": {"bg": "#0A1628", "text": "#E6F0FF", "accent": "#00BFFF", "card": "#13294B"},
}

# ============================================================
# DIMENSÕES DO VOLANTE (GEOMETRIA ESPACIAL)
# ============================================================
VOLANTE_DIMS = {
    "Mega Sena": {"rows": 6, "cols": 10},       # 6x10 = 60
    "Lotofácil": {"rows": 5, "cols": 5},         # 5x5 = 25
    "Quina": {"rows": 8, "cols": 10},            # 8x10 = 80
    "+Milionária": {"rows": 10, "cols": 5},      # 10x5 = 50
    "Dia de Sorte": {"rows": 7, "cols": 5},      # 7x5 = 35 (31 usadas)
}

# ============================================================
# UTILITÁRIOS
# ============================================================

def is_prime(n):
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(np.sqrt(n)) + 1, 2):
        if n % i == 0:
            return False
    return True


def max_consecutivos(combo):
    """Calcula a maior sequência de números consecutivos em uma combinação."""
    if not combo:
        return 0
    ordenado = sorted(combo)
    max_seq = 1
    atual = 1
    for i in range(1, len(ordenado)):
        if ordenado[i] == ordenado[i - 1] + 1:
            atual += 1
            if atual > max_seq:
                max_seq = atual
        else:
            atual = 1
    return max_seq


def get_theme():
    if "theme" not in st.session_state:
        st.session_state["theme"] = "Branco"
    return THEME_COLORS[st.session_state["theme"]]


def apply_theme_css():
    theme = get_theme()
    st.markdown(f"""
    <style>
    .stApp {{ background-color: {theme['bg']}; color: {theme['text']}; }}
    .stTabs [data-baseweb="tab"] {{ color: {theme['text']}; }}
    .stTabs [aria-selected="true"] {{ color: {theme['accent']}; border-bottom-color: {theme['accent']}; }}
    .metric-card {{
        background-color: {theme['card']};
        border-radius: 12px; padding: 18px; margin: 6px 0;
        border-left: 4px solid {theme['accent']};
    }}
    .section-title {{ color: {theme['accent']}; font-weight: 700; font-size: 1.3rem; }}
    </style>
    """, unsafe_allow_html=True)


def metric_card(label, value, sub=""):
    theme = get_theme()
    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size:0.8rem;opacity:0.8;">{label}</div>
        <div style="font-size:1.6rem;font-weight:700;color:{theme['accent']};">{value}</div>
        <div style="font-size:0.75rem;opacity:0.6;">{sub}</div>
    </div>
    """, unsafe_allow_html=True)


def format_brl(value):
    """Formata um valor numérico no padrão de moeda brasileira (R$ 1.500,00)."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.0
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ============================================================
# GERAÇÃO DE DADOS MOCKADOS
# ============================================================

@st.cache_data(show_spinner=False)
def generate_mock_data(lottery_name, n_draws=300):
    cfg = LOTTERIES[lottery_name]
    total = cfg["dezenas_total"]
    pick = cfg["dezenas_aposta"]
    rows = []
    base_date = datetime.now() - timedelta(days=n_draws * 3)
    for i in range(n_draws):
        nums = sorted(random.sample(range(1, total + 1), pick))
        row = {"concurso": n_draws - i, "data": (base_date + timedelta(days=i * 3)).strftime("%d/%m/%Y")}
        for j, n in enumerate(nums):
            row[f"d{j+1}"] = n
        rows.append(row)
    return pd.DataFrame(rows)

# ============================================================
# API PÚBLICA DE LOTERIAS
# ============================================================
def fetch_latest_results(lottery_name):
    """
    Busca o último resultado da loteria via API pública.
    Utiliza a API loteriascaixa-api.herokuapp.com
    Retorna um DataFrame no formato esperado ou None em caso de erro.
    """
    if requests is None:
        st.error("A biblioteca 'requests' não está instalada no ambiente. Instale com `pip install requests` para buscar resultados online.")
        return None

    slug = LOTTERIES.get(lottery_name, {}).get("slug")
    if not slug:
        st.error(f"Loteria não suportada para busca online: {lottery_name}")
        return None
    url = f"https://loteriascaixa-api.herokuapp.com/api/{slug}/latest"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Estrutura esperada: { "concurso": 1234, "data": "01/01/2025", "dezenas": [1,2,3,4,5,6] }
        if not all(k in data for k in ("concurso", "data", "dezenas")):
            st.error("Formato inesperado da resposta da API.")
            return None
        dezenas = data["dezenas"]
        if len(dezenas) < LOTTERIES[lottery_name]["dezenas_aposta"]:
            st.warning(f"Número de dezenas retornado incompatível com {lottery_name}.")
            return None
        row = {"concurso": data["concurso"], "data": data["data"]}
        for i, d in enumerate(dezenas[:LOTTERIES[lottery_name]["dezenas_aposta"]], start=1):
            row[f"d{i}"] = d
        df = pd.DataFrame([row])
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao acessar API: {e}")
        return None
    except Exception as e:
        st.error(f"Erro inesperado: {e}")
        return None

# ============================================================
# INGESTÃO DE DADOS
# ============================================================

def infer_dezena_columns(df):
    candidates = [c for c in df.columns if str(c).lower().startswith("d") or str(c).lower().startswith("bola")]
    numeric_candidates = []
    for c in candidates:
        try:
            vals = pd.to_numeric(df[c], errors="coerce").dropna()
            if len(vals) > 0 and vals.min() >= 1 and vals.max() <= 100:
                numeric_candidates.append(c)
        except Exception:
            pass
    if numeric_candidates:
        return numeric_candidates
    # fallback: any numeric columns excluding concurso/data
    skip = {"concurso", "data", "arrecadacao", "ganhadores"}
    numeric_cols = []
    for c in df.columns:
        if str(c).lower() in skip:
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            numeric_cols.append(c)
    return numeric_cols


def process_uploaded_file(uploaded_file, lottery_name):
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file, sep=None, engine="python")
        else:
            df = pd.read_excel(uploaded_file)
        dezena_cols = infer_dezena_columns(df)
        if len(dezena_cols) < LOTTERIES[lottery_name]["dezenas_aposta"]:
            st.warning(f"Não foi possível identificar colunas de dezenas suficientes. Usando dados mockados.")
            return None
        # normalizar nomes das colunas de dezenas para d1, d2, ...
        pick = LOTTERIES[lottery_name]["dezenas_aposta"]
        keep = []
        for i in range(pick):
            if i < len(dezena_cols):
                keep.append(dezena_cols[i])
        df_out = df[keep].copy()
        df_out.columns = [f"d{i+1}" for i in range(pick)]
        # preservar concurso/data se existirem
        if "concurso" in [str(c).lower() for c in df.columns]:
            for c in df.columns:
                if str(c).lower() == "concurso":
                    df_out.insert(0, "concurso", df[c])
        if "data" in [str(c).lower() for c in df.columns]:
            for c in df.columns:
                if str(c).lower() == "data":
                    df_out.insert(1, "data", df[c])
        return df_out
    except Exception as e:
        st.error(f"Erro ao processar arquivo: {e}")
        return None


def get_dezenas_matrix(df, lottery_name):
    pick = LOTTERIES[lottery_name]["dezenas_aposta"]
    cols = [f"d{i+1}" for i in range(pick)]
    existing = [c for c in cols if c in df.columns]
    if len(existing) < pick:
        existing = infer_dezena_columns(df)[:pick]
    mat = df[existing].apply(pd.to_numeric, errors="coerce").dropna()
    return mat.values.astype(int)

# ============================================================
# ANÁLISES ESTATÍSTICAS
# ============================================================

@st.cache_data(show_spinner=False)
def compute_frequency(draws_matrix, total_numbers):
    flat = draws_matrix.flatten()
    freq = Counter(flat.tolist())
    return {n: freq.get(n, 0) for n in range(1, total_numbers + 1)}


@st.cache_data(show_spinner=False)
def compute_delays(draws_matrix, total_numbers):
    n_draws = len(draws_matrix)
    delays = {}
    for num in range(1, total_numbers + 1):
        last_seen = None
        for i in range(n_draws - 1, -1, -1):
            if num in draws_matrix[i]:
                last_seen = i
                break
        if last_seen is None:
            delays[num] = n_draws
        else:
            delays[num] = (n_draws - 1) - last_seen
    return delays


@st.cache_data(show_spinner=False)
def monte_carlo_pairs(draws_matrix, total_numbers, iterations=5000):
    rng = np.random.default_rng(42)
    pair_counts = Counter()
    for _ in range(iterations):
        sample = rng.choice(total_numbers, size=2, replace=False)
        pair = tuple(sorted(sample.tolist()))
        pair_counts[pair] += 1
    # também pares reais do histórico
    real_pairs = Counter()
    for row in draws_matrix:
        for combo in itertools.combinations(sorted(row.tolist()), 2):
            real_pairs[combo] += 1
    return pair_counts, real_pairs


@st.cache_data(show_spinner=False)
def compute_patterns(draws_matrix, total_numbers):
    n = len(draws_matrix)
    impar_ratios = []
    prime_counts = []
    sums = []
    for row in draws_matrix:
        nums = row.tolist()
        impares = sum(1 for x in nums if x % 2 != 0)
        impar_ratios.append(impares / len(nums))
        prime_counts.append(sum(1 for x in nums if is_prime(int(x))))
        sums.append(sum(nums))
    return {
        "impar_ratio_mean": float(np.mean(impar_ratios)),
        "impar_ratios": impar_ratios,
        "prime_mean": float(np.mean(prime_counts)),
        "prime_counts": prime_counts,
        "sums": sums,
        "sum_mean": float(np.mean(sums)),
        "sum_std": float(np.std(sums)),
    }


@st.cache_data(show_spinner=False)
def compute_spatial_analysis(draws_matrix, lottery_name):
    """
    Calcula a análise espacial do volante para cada sorteio:
    - Linhas preenchidas
    - Colunas preenchidas
    - Distribuição por quadrante (4 quadrantes)
    - Borda vs Miolo
    """
    dims = VOLANTE_DIMS.get(lottery_name, {"rows": 10, "cols": 10})
    rows = dims["rows"]
    cols = dims["cols"]

    linhas_preenchidas = []
    colunas_preenchidas = []
    quadrante_counts = {"Top-Left": [], "Top-Right": [], "Bottom-Left": [], "Bottom-Right": []}
    borda_counts = []
    miolo_counts = []

    mid_row = rows // 2
    mid_col = cols // 2

    for draw in draws_matrix:
        draw_nums = set(int(x) for x in draw)
        linhas = set()
        colunas = set()
        quad = {"Top-Left": 0, "Top-Right": 0, "Bottom-Left": 0, "Bottom-Right": 0}
        borda = 0
        miolo = 0

        for n in draw_nums:
            r = (n - 1) // cols
            c = (n - 1) % cols
            linhas.add(r)
            colunas.add(c)

            if r < mid_row and c < mid_col:
                quad["Top-Left"] += 1
            elif r < mid_row and c >= mid_col:
                quad["Top-Right"] += 1
            elif r >= mid_row and c < mid_col:
                quad["Bottom-Left"] += 1
            else:
                quad["Bottom-Right"] += 1

            if r == 0 or r == rows - 1 or c == 0 or c == cols - 1:
                borda += 1
            else:
                miolo += 1

        linhas_preenchidas.append(len(linhas))
        colunas_preenchidas.append(len(colunas))
        for k in quadrante_counts:
            quadrante_counts[k].append(quad[k])
        borda_counts.append(borda)
        miolo_counts.append(miolo)

    total_dezenas_mean = float(np.mean(borda_counts) + np.mean(miolo_counts)) if len(draws_matrix) > 0 else 0.0

    return {
        "linhas_mean": float(np.mean(linhas_preenchidas)) if linhas_preenchidas else 0.0,
        "linhas_dist": linhas_preenchidas,
        "colunas_mean": float(np.mean(colunas_preenchidas)) if colunas_preenchidas else 0.0,
        "colunas_dist": colunas_preenchidas,
        "quadrante_means": {k: float(np.mean(v)) if v else 0.0 for k, v in quadrante_counts.items()},
        "quadrante_dist": quadrante_counts,
        "borda_mean": float(np.mean(borda_counts)) if borda_counts else 0.0,
        "miolo_mean": float(np.mean(miolo_counts)) if miolo_counts else 0.0,
        "borda_pct": (float(np.mean(borda_counts)) / total_dezenas_mean * 100.0) if total_dezenas_mean > 0 else 0.0,
        "miolo_pct": (float(np.mean(miolo_counts)) / total_dezenas_mean * 100.0) if total_dezenas_mean > 0 else 0.0,
        "rows": rows,
        "cols": cols,
    }

# ============================================================
# MACHINE LEARNING (FASE 3)
# ============================================================

def extract_features(draws_matrix, lottery_name, total_numbers):
    """
    Extrai features para cada dezena do universo da loteria.
    Retorna um array numpy de shape (total_numbers, 7) com as features:
    [freq, atraso, pair_score, linha, coluna, is_primo, is_impar]
    """
    freq = compute_frequency(draws_matrix, total_numbers)
    delays = compute_delays(draws_matrix, total_numbers)
    _, real_pairs = monte_carlo_pairs(draws_matrix, total_numbers, iterations=3000)

    dims = VOLANTE_DIMS.get(lottery_name, {"rows": 10, "cols": 10})
    cols_dim = dims["cols"]

    # pair_score por dezena
    pair_score_map = {num: 0.0 for num in range(1, total_numbers + 1)}
    for (a, b), cnt in real_pairs.items():
        pair_score_map[a] += cnt
        pair_score_map[b] += cnt

    max_freq = max(freq.values()) if max(freq.values()) > 0 else 1
    max_delay = max(delays.values()) if max(delays.values()) > 0 else 1
    max_pair = max(pair_score_map.values()) if max(pair_score_map.values()) > 0 else 1

    features = []
    for num in range(1, total_numbers + 1):
        f_freq = freq.get(num, 0) / max_freq
        f_atraso = delays.get(num, 0) / max_delay
        f_pair = pair_score_map[num] / max_pair
        linha = (num - 1) // cols_dim
        coluna = (num - 1) % cols_dim
        f_primo = 1 if is_prime(num) else 0
        f_impar = 1 if num % 2 != 0 else 0
        features.append([f_freq, f_atraso, f_pair, linha, coluna, f_primo, f_impar])

    return np.array(features, dtype=float)


def train_predictive_model(draws_matrix, lottery_name):
    """
    Treina um RandomForestClassifier para prever se uma dezena será sorteada
    no próximo concurso. Retorna dict com model, probs, accuracy, features.
    """
    if not SKLEARN_AVAILABLE:
        return None

    cfg = LOTTERIES[lottery_name]
    total_numbers = cfg["dezenas_total"]

    features = extract_features(draws_matrix, lottery_name, total_numbers)

    # Construir dataset: para cada sorteio (exceto o primeiro),
    # X = features das dezenas, y = 1 se a dezena foi sorteada naquele concurso
    X = []
    y = []

    for i in range(1, len(draws_matrix)):
        drawn_set = set(int(x) for x in draws_matrix[i])
        for num in range(1, total_numbers + 1):
            X.append(features[num - 1])
            y.append(1 if num in drawn_set else 0)

    X = np.array(X)
    y = np.array(y)

    if len(X) == 0 or len(np.unique(y)) < 2:
        return None

    # Divisão temporal: 80% treino, 20% teste
    split_idx = int(len(draws_matrix) * 0.8) - 1
    n_per_draw = total_numbers
    train_end = split_idx * n_per_draw

    X_train, X_test = X[:train_end], X[train_end:]
    y_train, y_test = y[:train_end], y[train_end:]

    if len(X_train) == 0 or len(X_test) == 0 or len(np.unique(y_train)) < 2 or len(np.unique(y_test)) < 2:
        # fallback: divisão simples
        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

    model = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    # Probabilidades para todas as dezenas (usando features atuais)
    probs = model.predict_proba(features)[:, 1]

    feature_names = ["freq", "atraso", "pair_score", "linha", "coluna", "is_primo", "is_impar"]

    return {
        "model": model,
        "probs": probs,
        "accuracy": float(accuracy),
        "features": features,
        "feature_names": feature_names,
        "feature_importances": model.feature_importances_,
    }


def generate_bets_ml(lottery_name, draws_matrix, n_bets, model_data):
    """
    Gera apostas via roleta ponderada usando as probabilidades do modelo ML.
    """
    cfg = LOTTERIES[lottery_name]
    total = cfg["dezenas_total"]
    pick = cfg["dezenas_aposta"]

    if model_data is None or model_data.get("probs") is None:
        return []

    probs = model_data["probs"]
    nums = list(range(1, total + 1))
    weights = [max(probs[n - 1], 0.001) for n in nums]

    rng = random.Random(42)
    bets = []

    for _ in range(n_bets):
        chosen = set()
        temp_weights = list(weights)
        temp_nums = list(nums)
        while len(chosen) < pick:
            selected = rng.choices(temp_nums, weights=temp_weights, k=1)[0]
            chosen.add(selected)
            idx = temp_nums.index(selected)
            temp_nums.pop(idx)
            temp_weights.pop(idx)
        bets.append(sorted(chosen))

    return bets


def render_caixa_export(bets, lottery_name, download_key="download_json_caixa_default"):
    """
    Renderiza a seção de exportação no formato da Caixa:
    - Download JSON
    - Snippet JS para integração
    - Tabela do carrinho de apostas
    """
    cfg = LOTTERIES[lottery_name]
    slug = cfg.get("slug", lottery_name.lower().replace(" ", "_").replace("+", "mais"))
    pick = cfg["dezenas_aposta"]

    st.markdown("### 🛒 Exportação no formato Caixa")

    # Estrutura JSON
    payload = {
        "loteria": slug,
        "loteria_nome": lottery_name,
        "dezenas_aposta": pick,
        "total_apostas": len(bets),
        "apostas": [
            {"id": i + 1, "dezenas": bet}
            for i, bet in enumerate(bets)
        ],
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    json_str = json.dumps(payload, ensure_ascii=False, indent=2)

    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        st.download_button(
            label="📥 Baixar JSON (formato Caixa)",
            data=json_str.encode("utf-8"),
            file_name=f"apostas_caixa_{slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            key=download_key,
        )
    with col_exp2:
        st.caption(f"{len(bets)} apostas · {pick} dezenas cada · slug: `{slug}`")

    # Snippet JS
    st.markdown("#### Snippet JavaScript (integração)")
    js_snippet = f"""// Integração - Loteria: {lottery_name} (slug: {slug})
const apostas = {json_str};

// Exemplo: enviar apostas para API de carrinho
async function enviarCarrinho() {{
  const response = await fetch('/api/carrinho/{slug}', {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify(apostas)
  }});
  return await response.json();
}}

// Exemplo: renderizar apostas no DOM
apostas.apostas.forEach(a => {{
  console.log(`Aposta #${{a.id}}: ${{a.dezenas.join(', ')}}`);
}});
"""
    st.code(js_snippet, language="javascript")

    # Tabela do carrinho
    st.markdown("#### Carrinho de Apostas")
    df_cart = pd.DataFrame(bets, columns=[f"d{i+1}" for i in range(len(bets[0]) if bets else pick)])
    df_cart.insert(0, "#", range(1, len(bets) + 1))
    df_cart["Dezenas"] = df_cart.apply(lambda r: " - ".join(str(int(r[f"d{i+1}"])) for i in range(pick)), axis=1)
    df_cart_display = df_cart[["#", "Dezenas"]].copy()
    st.dataframe(df_cart_display, use_container_width=True, hide_index=True)

# ============================================================
# GERADOR DE APOSTAS
# ============================================================

def generate_bets(lottery_name, draws_matrix, n_bets=10, strategy="híbrido", weight_freq=0.4, weight_delay=0.3, weight_pairs=0.3):
    cfg = LOTTERIES[lottery_name]
    total = cfg["dezenas_total"]
    pick = cfg["dezenas_aposta"]

    freq = compute_frequency(draws_matrix, total)
    delays = compute_delays(draws_matrix, total)
    mc_pairs, real_pairs = monte_carlo_pairs(draws_matrix, total, iterations=3000)

    # Normalizar frequências e atrasos
    max_freq = max(freq.values()) if max(freq.values()) > 0 else 1
    max_delay = max(delays.values()) if max(delays.values()) > 0 else 1

    scores = {}
    for num in range(1, total + 1):
        f_score = freq.get(num, 0) / max_freq
        d_score = delays.get(num, 0) / max_delay
        scores[num] = weight_freq * f_score + weight_delay * d_score

    # Score de pares: soma das médias de pares reais
    pair_score_map = {num: 0.0 for num in range(1, total + 1)}
    for (a, b), cnt in real_pairs.items():
        pair_score_map[a] += cnt
        pair_score_map[b] += cnt
    max_pair = max(pair_score_map.values()) if max(pair_score_map.values()) > 0 else 1
    for num in pair_score_map:
        scores[num] += weight_pairs * (pair_score_map[num] / max_pair)

    bets = []
    rng = random.Random(42)

    for _ in range(n_bets):
        if strategy == "frequentes":
            top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:pick * 3]
            chosen = rng.sample([x[0] for x in top], pick)
        elif strategy == "atrasadas":
            top = sorted(delays.items(), key=lambda x: x[1], reverse=True)[:pick * 3]
            chosen = rng.sample([x[0] for x in top], pick)
        elif strategy == "aleatória":
            chosen = rng.sample(range(1, total + 1), pick)
        else:  # híbrido
            # roleta ponderada
            nums = list(scores.keys())
            weights = [scores[n] + 0.01 for n in nums]
            chosen = set()
            while len(chosen) < pick:
                selected = rng.choices(nums, weights=weights, k=1)[0]
                chosen.add(selected)
            chosen = list(chosen)
        bets.append(sorted(chosen))

    return bets, freq, delays, real_pairs


def find_strong_pairs(real_pairs, top_n=20):
    return real_pairs.most_common(top_n)

# ============================================================
# FECHAMENTO REDUZIDO (MATRIZ DE GARANTIA)
# ============================================================

def get_garantia_options(lottery_name):
    """
    Gera opções dinâmicas de garantia baseadas no max_acertos da loteria.
    Retorna uma lista de tuplas: (garantir_acertos, se_acertar, label)
    """
    cfg = LOTTERIES[lottery_name]
    max_acertos = cfg["max_acertos"]
    min_premio = min(cfg["premios"].keys())

    options = []
    # Garantir min_premio se acertar min_premio
    options.append((min_premio, min_premio, f"Garantir {min_premio} se acertar {min_premio}"))
    # Para cada nível de prêmio p de min_premio até max_acertos-1: garantir p se acertar p+1
    for p in range(min_premio, max_acertos):
        options.append((p, p + 1, f"Garantir {p} se acertar {p + 1}"))

    return options


def gerar_fechamento_reduzido(chosen_numbers, aposta_size, garantir_acertos, limite_jogos):
    """
    Implementa o algoritmo de fechamento reduzido por garantia (greedy set-cover).

    - Gera todas as combinações de `aposta_size` dezenas das `chosen_numbers`.
    - Gera todas as combinações de `garantir_acertos` dezenas das `chosen_numbers`.
    - Usa greedy set-cover: itera sobre as combinações de tamanho `aposta_size`,
      e para cada uma, marca quais combinações de tamanho `garantir_acertos`
      ela "cobre" (subconjunto). Se uma combinação `aposta_size` cobre pelo
      menos uma combinação `garantir_acertos` ainda não coberta, adiciona ela
      ao resultado e marca as cobertas. Continua até todas as combinações de
      `garantir_acertos` estarem cobertas ou o limite ser atingido.

    Retorna: (lista de apostas, total de combinações de garantia)
    """
    chosen_numbers = sorted(chosen_numbers)

    # Gera todas as combinações de aposta_size dezenas
    todas_apostas = list(itertools.combinations(chosen_numbers, aposta_size))

    # Gera todas as combinações de garantir_acertos dezenas
    todas_garantias = list(itertools.combinations(chosen_numbers, garantir_acertos))
    total_garantias = len(todas_garantias)

    # Converte garantias para sets para verificação de subconjunto
    garantias_sets = [set(g) for g in todas_garantias]
    cobertas = [False] * total_garantias
    num_cobertas = 0

    resultado = []

    for aposta in todas_apostas:
        # Verifica limite de jogos
        if limite_jogos > 0 and len(resultado) >= limite_jogos:
            break
        # Verifica se todas as garantias já foram cobertas
        if num_cobertas >= total_garantias:
            break

        aposta_set = set(aposta)
        novas_cobertas = []

        for j, gset in enumerate(garantias_sets):
            if not cobertas[j] and gset.issubset(aposta_set):
                novas_cobertas.append(j)

        if novas_cobertas:
            resultado.append(sorted(aposta))
            for j in novas_cobertas:
                cobertas[j] = True
            num_cobertas += len(novas_cobertas)

    return resultado, total_garantias

# ============================================================
# BACKTESTING
# ============================================================

def run_backtest(bets, draws_matrix, lottery_name):
    cfg = LOTTERIES[lottery_name]
    premios = cfg["premios"]
    premios_estimados = cfg.get("premios_estimados", {})
    custo_aposta = cfg.get("custo_aposta", 0.0)

    results = {label: 0 for label in set(premios.values())}
    results["Nenhum"] = 0
    detail_rows = []

    bet_sets = [set(b) for b in bets]
    n_bets = len(bets)
    n_draws = len(draws_matrix)

    retorno_total = 0.0

    for draw_idx, row in enumerate(draws_matrix):
        draw_set = set(int(x) for x in row)
        for bet_idx, bset in enumerate(bet_sets):
            hits = len(bset & draw_set)
            label = premios.get(hits, None)
            if label:
                results[label] = results.get(label, 0) + 1
                valor = premios_estimados.get(label, 0.0)
                retorno_total += valor
                detail_rows.append({
                    "Concurso": draw_idx + 1,
                    "Aposta #": bet_idx + 1,
                    "Acertos": hits,
                    "Prêmio": label,
                    "Valor Estimado": valor,
                })
            elif hits >= 3:
                results["Nenhum"] += 1

    custo_total = n_bets * custo_aposta * n_draws
    saldo = retorno_total - custo_total
    roi = (saldo / custo_total * 100.0) if custo_total > 0 else 0.0

    financeiro = {
        "custo_total": custo_total,
        "retorno_total": retorno_total,
        "saldo": saldo,
        "roi": roi,
    }

    return results, pd.DataFrame(detail_rows), financeiro

# ============================================================
# EXPORTAÇÃO EXCEL
# ============================================================

def export_to_excel(bets, freq, delays, strong_pairs, lottery_name):
    cfg = LOTTERIES[lottery_name]
    total = cfg["dezenas_total"]

    df_bets = pd.DataFrame(bets, columns=[f"d{i+1}" for i in range(len(bets[0]))])
    df_bets.insert(0, "Aposta", range(1, len(bets) + 1))

    df_freq = pd.DataFrame([
        {"Dezena": n, "Frequência": freq.get(n, 0)} for n in range(1, total + 1)
    ]).sort_values("Frequência", ascending=False)

    df_delays = pd.DataFrame([
        {"Dezena": n, "Atraso (concursos)": delays.get(n, 0)} for n in range(1, total + 1)
    ]).sort_values("Atraso (concursos)", ascending=False)

    df_pairs = pd.DataFrame(strong_pairs, columns=["Par", "Ocorrências"])
    df_pairs["Dezena_A"] = df_pairs["Par"].apply(lambda x: x[0])
    df_pairs["Dezena_B"] = df_pairs["Par"].apply(lambda x: x[1])
    df_pairs = df_pairs[["Dezena_A", "Dezena_B", "Ocorrências"]]

    output = BytesIO()
    if xlsxwriter is not None:
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df_bets.to_excel(writer, sheet_name="Apostas", index=False)
            df_freq.to_excel(writer, sheet_name="Frequência", index=False)
            df_delays.to_excel(writer, sheet_name="Atrasos", index=False)
            df_pairs.to_excel(writer, sheet_name="Pares Fortes", index=False)

            wb = writer.book
            header_fmt = wb.add_format({"bold": True, "bg_color": "#1E90FF", "font_color": "white", "border": 1})
            for sheet_name in ["Apostas", "Frequência", "Atrasos", "Pares Fortes"]:
                ws = writer.sheets[sheet_name]
                ws.set_column(0, 10, 18)
    else:
        # Fallback: ExcelWriter padrão (openpyxl) sem engine='xlsxwriter'
        with pd.ExcelWriter(output) as writer:
            df_bets.to_excel(writer, sheet_name="Apostas", index=False)
            df_freq.to_excel(writer, sheet_name="Frequência", index=False)
            df_delays.to_excel(writer, sheet_name="Atrasos", index=False)
            df_pairs.to_excel(writer, sheet_name="Pares Fortes", index=False)

    output.seek(0)
    return output

# ============================================================
# GRÁFICOS PLOTLY
# ============================================================

def plot_frequency_bar(freq, total, theme):
    nums = list(range(1, total + 1))
    vals = [freq.get(n, 0) for n in nums]
    fig = go.Figure(data=[go.Bar(x=nums, y=vals, marker_color=theme["accent"])])
    fig.update_layout(
        title="Frequência de Dezenas",
        xaxis_title="Dezena", yaxis_title="Frequência",
        template="plotly_white", height=400,
        paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"],
        font=dict(color=theme["text"]),
    )
    return fig


def plot_delays_bar(delays, total, theme):
    nums = list(range(1, total + 1))
    vals = [delays.get(n, 0) for n in nums]
    fig = go.Figure(data=[go.Bar(x=nums, y=vals, marker_color=theme["accent"], opacity=0.8)])
    fig.update_layout(
        title="Atraso de Dezenas (concursos sem aparecer)",
        xaxis_title="Dezena", yaxis_title="Atraso",
        template="plotly_white", height=400,
        paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"],
        font=dict(color=theme["text"]),
    )
    return fig


def plot_patterns(patterns, theme):
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Proporção Ímpar/Par por Sorteio", "Números Primos por Sorteio",
                        "Distribuição da Soma das Dezenas", "Resumo Médias"),
        specs=[[{"type": "histogram"}, {"type": "histogram"}],
               [{"type": "histogram"}, {"type": "indicator"}]],
    )

    fig.add_trace(go.Histogram(x=patterns["impar_ratios"], nbinsx=20, marker_color=theme["accent"], name="Ímpar/Par"), row=1, col=1)
    fig.add_trace(go.Histogram(x=patterns["prime_counts"], nbinsx=20, marker_color="#FF6B6B", name="Primos"), row=1, col=2)
    fig.add_trace(go.Histogram(x=patterns["sums"], nbinsx=30, marker_color="#4ECDC4", name="Soma"), row=2, col=1)

    fig.add_trace(go.Indicator(
        mode="number",
        value=patterns["impar_ratio_mean"],
        title={"text": "Média Ímpar/Par"},
        number={"valueformat": ".2%"},
    ), row=2, col=2)

    fig.update_layout(
        height=600, showlegend=False,
        template="plotly_white",
        paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"],
        font=dict(color=theme["text"]),
        title_text="Padrões Comportamentais",
    )
    return fig


def plot_sum_distribution(patterns, theme):
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=patterns["sums"], nbinsx=35, marker_color=theme["accent"], opacity=0.7, name="Soma"))
    mean = patterns["sum_mean"]
    std = patterns["sum_std"]
    fig.add_vline(x=mean, line_dash="dash", line_color="red", annotation_text=f"Média: {mean:.1f}")
    fig.add_vline(x=mean + std, line_dash="dot", line_color="orange", annotation_text=f"+1σ")
    fig.add_vline(x=mean - std, line_dash="dot", line_color="orange", annotation_text=f"-1σ")
    fig.update_layout(
        title="Histograma da Soma das Dezenas (Curva de Distribuição)",
        xaxis_title="Soma", yaxis_title="Frequência",
        template="plotly_white", height=420,
        paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"],
        font=dict(color=theme["text"]),
    )
    return fig


def plot_prime_impar_summary(patterns, theme):
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Média Ímpar/Par", "Média Primos por Sorteio"),
                        specs=[[{"type": "pie"}, {"type": "indicator"}]])
    imp = patterns["impar_ratio_mean"]
    fig.add_trace(go.Pie(
        labels=["Ímpares", "Pares"], values=[imp, 1 - imp],
        marker_colors=[theme["accent"], "#FF6B6B"], hole=0.4,
    ), row=1, col=1)
    fig.add_trace(go.Indicator(
        mode="number", value=patterns["prime_mean"],
        title={"text": "Primos/sorteio"},
        number={"valueformat": ".2f"},
    ), row=1, col=2)
    fig.update_layout(
        height=380, template="plotly_white",
        paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"],
        font=dict(color=theme["text"]),
    )
    return fig


def plot_backtest_results(results, theme):
    labels = [k for k, v in results.items() if v > 0 or k != "Nenhum"]
    values = [results[k] for k in labels]
    # Criar pares (label, value) e ordenar por value crescente (do menor para o maior)
    pares = list(zip(labels, values))
    pares.sort(key=lambda x: x[1])
    labels_sorted = [p[0] for p in pares]
    values_sorted = [p[1] for p in pares]
    fig = go.Figure(data=[go.Bar(x=labels_sorted, y=values_sorted, marker_color=theme["accent"], text=values_sorted, textposition="auto")])
    fig.update_layout(
        title="Resultado do Backtesting",
        xaxis_title="Categoria de Prêmio", yaxis_title="Ocorrências",
        template="plotly_white", height=400,
        paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"],
        font=dict(color=theme["text"]),
    )
    return fig


def plot_spatial_quadrants(spatial, theme):
    """Pie chart da distribuição dos 4 quadrantes (média de dezenas por quadrante)."""
    labels = list(spatial["quadrante_means"].keys())
    values = list(spatial["quadrante_means"].values())
    colors = [theme["accent"], "#FF6B6B", "#4ECDC4", "#FFD93D"]
    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values, hole=0.4,
        marker_colors=colors,
        textinfo="label+percent",
    )])
    fig.update_layout(
        title="Distribuição por Quadrante (média de dezenas por sorteio)",
        template="plotly_white", height=420,
        paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"],
        font=dict(color=theme["text"]),
    )
    return fig


def plot_spatial_linhas(spatial, theme):
    """Histograma da distribuição de linhas preenchidas por sorteio."""
    fig = go.Figure(data=[go.Histogram(
        x=spatial["linhas_dist"],
        nbinsx=spatial["rows"],
        marker_color=theme["accent"],
        opacity=0.8,
    )])
    fig.update_layout(
        title="Distribuição de Linhas Preenchidas por Sorteio",
        xaxis_title="Número de Linhas Preenchidas",
        yaxis_title="Frequência",
        template="plotly_white", height=420,
        paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"],
        font=dict(color=theme["text"]),
    )
    return fig


def plot_ml_probabilities(probs, total, theme):
    """Gráfico de barras das probabilidades ML por dezena."""
    nums = list(range(1, total + 1))
    fig = go.Figure(data=[go.Bar(
        x=nums, y=probs,
        marker_color=theme["accent"],
        text=[f"{p:.3f}" for p in probs],
        textposition="outside",
        textfont=dict(size=8),
    )])
    fig.update_layout(
        title="Probabilidades por Dezena (Random Forest)",
        xaxis_title="Dezena", yaxis_title="Probabilidade",
        template="plotly_white", height=450,
        paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"],
        font=dict(color=theme["text"]),
    )
    return fig


def plot_feature_importances(importances, feature_names, theme):
    """Gráfico de barras horizontais das importâncias das features."""
    sorted_idx = np.argsort(importances)
    fig = go.Figure(data=[go.Bar(
        x=importances[sorted_idx],
        y=[feature_names[i] for i in sorted_idx],
        orientation="h",
        marker_color=theme["accent"],
        text=[f"{v:.4f}" for v in importances[sorted_idx]],
        textposition="auto",
    )])
    fig.update_layout(
        title="Importância das Features (Random Forest)",
        xaxis_title="Importância", yaxis_title="Feature",
        template="plotly_white", height=400,
        paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"],
        font=dict(color=theme["text"]),
    )
    return fig

# ============================================================
# APP PRINCIPAL
# ============================================================

def main():
    st.set_page_config(page_title="Motor Analítico de Loterias", page_icon="🎲", layout="wide")
    apply_theme_css()
    theme = get_theme()

    st.title("🎲 Motor Analítico & Gerador de Apostas Multi-Loteria")
    st.markdown("<span class='section-title'>Análise estatística avançada · Monte Carlo · Backtesting · ML Preditivo · Exportação Excel</span>", unsafe_allow_html=True)

    # ---------- SIDEBAR ----------
    with st.sidebar:
        st.header("⚙️ Configurações")
        st.session_state["theme"] = st.radio("Tema", ["Branco", "Azul"], index=0 if st.session_state.get("theme", "Branco") == "Branco" else 1, key="theme_radio")
        theme = get_theme()
        apply_theme_css()

        st.divider()
        lottery_name = st.selectbox("🎯 Loteria", list(LOTTERIES.keys()), index=0, key="lottery_select")
        cfg = LOTTERIES[lottery_name]

        st.divider()
        st.subheader("📁 Ingestão de Dados")
        uploaded_file = st.file_uploader("Subir CSV ou Excel", type=["csv", "xlsx", "xls"], key="file_uploader")
        st.caption("Colunas de dezenas devem começar com 'd' ou 'bola'. Caso contrário, serão inferidas.")

        use_mock = st.checkbox("Usar dados mockados como fallback", value=True, key="use_mock_checkbox")

        st.divider()
        st.subheader("🌐 Atualização Online")
        if st.button("Buscar últimos resultados online", key="fetch_online_button"):
            with st.spinner("Buscando dados da API pública..."):
                online_df = fetch_latest_results(lottery_name)
                if online_df is not None:
                    st.session_state["df_online"] = online_df
                    st.session_state["use_online"] = True
                    st.success(f"Último resultado carregado: concurso {online_df['concurso'].iloc[0]}")
                else:
                    st.session_state["use_online"] = False
        if st.session_state.get("use_online"):
            st.info("Usando dados do último sorteio online.")

        st.divider()
        st.subheader("🎲 Gerador de Apostas")
        n_bets = st.slider("Número de apostas", 1, 50, 10, key="n_bets_slider")

        strategy_options = ["híbrido", "frequentes", "atrasadas", "aleatória"]
        if SKLEARN_AVAILABLE:
            strategy_options.append("ML Preditivo (Random Forest)")
        strategy = st.selectbox("Estratégia", strategy_options, index=0, key="strategy_select")
        w_freq = st.slider("Peso Frequência", 0.0, 1.0, 0.4, 0.05, key="weight_freq_slider")
        w_delay = st.slider("Peso Atraso", 0.0, 1.0, 0.3, 0.05, key="weight_delay_slider")
        w_pairs = st.slider("Peso Pares Fortes", 0.0, 1.0, 0.3, 0.05, key="weight_pairs_slider")

        if not SKLEARN_AVAILABLE:
            st.caption("⚠️ scikit-learn não instalado. ML Preditivo indisponível. Instale com `pip install scikit-learn`.")

    # ---------- CARREGAR DADOS ----------
    df_data = None
    # Prioridade: arquivo enviado > dados online > mock
    if uploaded_file is not None:
        processed = process_uploaded_file(uploaded_file, lottery_name)
        if processed is not None:
            df_data = processed
            st.sidebar.success(f"✅ Arquivo carregado: {len(df_data)} sorteios")
            st.session_state["use_online"] = False  # desativa online se arquivo é carregado
    elif st.session_state.get("use_online") and "df_online" in st.session_state:
        df_data = st.session_state["df_online"]
        st.sidebar.info(f"📡 Dados online: {len(df_data)} sorteio(s)")
    elif use_mock:
        df_data = generate_mock_data(lottery_name, n_draws=300)
        st.sidebar.info(f"📊 Dados mockados: {len(df_data)} sorteios")
    else:
        st.warning("Suba um arquivo, busque online ou ative os dados mockados para começar.")
        return

    draws_matrix = get_dezenas_matrix(df_data, lottery_name)
    n_draws = len(draws_matrix)

    # ---------- MÉTRICAS GERAIS ----------
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Sorteios Analisados", n_draws, "Histórico")
    with col2:
        metric_card("Dezenas por Aposta", cfg["dezenas_aposta"], lottery_name)
    with col3:
        metric_card("Universo", cfg["dezenas_total"], "Total de dezenas")
    with col4:
        freq = compute_frequency(draws_matrix, cfg["dezenas_total"])
        top_num = max(freq, key=freq.get)
        metric_card("Dezena + Frequente", f"{top_num} ({freq[top_num]}x)", "No histórico")

    st.divider()

    # ---------- TABS ----------
    tab_gerador, tab_padroes, tab_backtest, tab_fechamento, tab_dados = st.tabs([
        "🎰 Gerador de Apostas", "📊 Padrões", "🔬 Backtesting", "🔢 Fechamento Matemático", "📋 Dados"
    ])

    # ===== TAB: GERADOR =====
    with tab_gerador:
        st.header("🎰 Gerador de Apostas Otimizado")
        st.markdown("Combina **frequência**, **atraso** e **pares fortes (Monte Carlo)** com otimização via `itertools`.")

        is_ml_strategy = (strategy == "ML Preditivo (Random Forest)")

        if is_ml_strategy:
            st.info("🤖 Estratégia **ML Preditivo (Random Forest)** selecionada. O modelo será treinado com o histórico disponível.")

        if st.button("⚡ Gerar Apostas", type="primary", key="gerar_apostas_button"):
            with st.spinner("Gerando apostas otimizadas..."):
                if is_ml_strategy:
                    if not SKLEARN_AVAILABLE:
                        st.error("scikit-learn não está disponível. Não é possível usar ML Preditivo.")
                    else:
                        with st.spinner("Treinando modelo Random Forest..."):
                            model_data = train_predictive_model(draws_matrix, lottery_name)
                            st.session_state["ml_model_data"] = model_data

                        if model_data is not None:
                            bets = generate_bets_ml(lottery_name, draws_matrix, n_bets, model_data)
                            freq = compute_frequency(draws_matrix, cfg["dezenas_total"])
                            delays = compute_delays(draws_matrix, cfg["dezenas_total"])
                            _, real_pairs = monte_carlo_pairs(draws_matrix, cfg["dezenas_total"], iterations=3000)
                            strong_pairs = find_strong_pairs(real_pairs, top_n=20)
                            st.session_state["bets"] = bets
                            st.session_state["freq"] = freq
                            st.session_state["delays"] = delays
                            st.session_state["strong_pairs"] = strong_pairs
                        else:
                            st.error("Não foi possível treinar o modelo. Verifique se há dados suficientes.")
                else:
                    bets, freq, delays, real_pairs = generate_bets(
                        lottery_name, draws_matrix, n_bets=n_bets,
                        strategy=strategy, weight_freq=w_freq, weight_delay=w_delay, weight_pairs=w_pairs
                    )
                    strong_pairs = find_strong_pairs(real_pairs, top_n=20)
                    st.session_state["bets"] = bets
                    st.session_state["freq"] = freq
                    st.session_state["delays"] = delays
                    st.session_state["strong_pairs"] = strong_pairs

        # ---------- EXIBIÇÃO ML: ACCURACY + FEATURE IMPORTANCES + PROBS ----------
        if is_ml_strategy and "ml_model_data" in st.session_state and st.session_state["ml_model_data"] is not None:
            model_data = st.session_state["ml_model_data"]
            st.markdown("---")
            st.subheader("🤖 Resultados do Modelo ML")

            col_ml1, col_ml2 = st.columns(2)
            with col_ml1:
                metric_card("Acurácia do Modelo", f"{model_data['accuracy']:.2%}", "Random Forest")
            with col_ml2:
                metric_card("Features Utilizadas", len(model_data["feature_names"]), "7 atributos por dezena")

            # Feature importances
            st.markdown("#### Importância das Features")
            st.plotly_chart(
                plot_feature_importances(
                    model_data["feature_importances"],
                    model_data["feature_names"],
                    theme
                ),
                use_container_width=True
            )

            # Gráfico de probabilidades
            st.markdown("#### Probabilidades por Dezena")
            st.plotly_chart(
                plot_ml_probabilities(model_data["probs"], cfg["dezenas_total"], theme),
                use_container_width=True
            )

        if "bets" in st.session_state and st.session_state["bets"]:
            bets = st.session_state["bets"]
            freq = st.session_state["freq"]
            delays = st.session_state["delays"]
            strong_pairs = st.session_state["strong_pairs"]

            st.subheader(f"{len(bets)} Apostas Geradas")
            df_bets = pd.DataFrame(bets, columns=[f"d{i+1}" for i in range(len(bets[0]))])
            df_bets.insert(0, "#", range(1, len(bets) + 1))
            st.dataframe(df_bets, use_container_width=True, hide_index=True)

            # Visualização colorida
            st.markdown("### Visualização")
            cols = st.columns(min(len(bets), 5))
            for i, bet in enumerate(bets[:10]):
                with cols[i % len(cols)]:
                    balls = " ".join([f"<span style='display:inline-block;width:28px;height:28px;line-height:28px;text-align:center;border-radius:50%;background:{theme['accent']};color:white;font-weight:bold;margin:2px;font-size:0.75rem;'>{n}</span>" for n in bet])
                    st.markdown(f"<div style='padding:8px;background:{theme['card']};border-radius:10px;margin:4px 0;'><b>Aposta {i+1}</b><br>{balls}</div>", unsafe_allow_html=True)

            # Gráficos de frequência e atraso
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.plotly_chart(plot_frequency_bar(freq, cfg["dezenas_total"], theme), use_container_width=True)
            with col_g2:
                st.plotly_chart(plot_delays_bar(delays, cfg["dezenas_total"], theme), use_container_width=True)

            # Pares fortes
            st.subheader("🔗 Pares Fortes (Monte Carlo + Histórico)")
            df_pairs = pd.DataFrame(strong_pairs, columns=["Par", "Ocorrências"])
            df_pairs["Dezena_A"] = df_pairs["Par"].apply(lambda x: x[0])
            df_pairs["Dezena_B"] = df_pairs["Par"].apply(lambda x: x[1])
            st.dataframe(df_pairs[["Dezena_A", "Dezena_B", "Ocorrências"]].head(15), use_container_width=True, hide_index=True)

            # Exportação Excel
            st.subheader("📥 Exportação Excel")
            excel_data = export_to_excel(bets, freq, delays, strong_pairs, lottery_name)
            st.download_button(
                label="📊 Baixar Apostas em Excel (.xlsx)",
                data=excel_data,
                file_name=f"apostas_{lottery_name.replace(' ', '_').replace('+', 'mais')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel_apostas",
            )
            st.caption("O arquivo Excel contém 4 abas: **Apostas**, **Frequência**, **Atrasos** e **Pares Fortes**.")

            # ---------- EXPORTAÇÃO CAIXA (FASE 3) ----------
            st.markdown("---")
            render_caixa_export(bets, lottery_name, download_key="download_json_caixa_gerador")
        else:
            st.info("Clique em **⚡ Gerar Apostas** para criar combinações otimizadas.")

    # ===== TAB: PADRÕES =====
    with tab_padroes:
        st.header("📊 Padrões Comportamentais")
        st.markdown("Análise estatística do histórico: proporção ímpar/par, números primos e distribuição da soma.")

        patterns = compute_patterns(draws_matrix, cfg["dezenas_total"])

        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            metric_card("Média Ímpar/Par", f"{patterns['impar_ratio_mean']:.1%}", "Proporção de ímpares")
        with col_p2:
            metric_card("Média Primos", f"{patterns['prime_mean']:.2f}", "Por sorteio")
        with col_p3:
            metric_card("Média da Soma", f"{patterns['sum_mean']:.1f}", f"σ = {patterns['sum_std']:.1f}")

        st.plotly_chart(plot_prime_impar_summary(patterns, theme), use_container_width=True)
        st.plotly_chart(plot_sum_distribution(patterns, theme), use_container_width=True)
        st.plotly_chart(plot_patterns(patterns, theme), use_container_width=True)

        # ---------- ANÁLISE ESPACIAL DO VOLANTE ----------
        st.markdown("---")
        st.markdown("### 📐 Análise Espacial do Volante")
        st.markdown("Distribuição geométrica das dezenas sorteadas no volante: linhas, colunas, quadrantes e moldura (borda vs miolo).")

        spatial = compute_spatial_analysis(draws_matrix, lottery_name)
        volante_dims = VOLANTE_DIMS.get(lottery_name, {"rows": 10, "cols": 10})

        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        with col_s1:
            metric_card(
                "Média de Linhas Preenchidas",
                f"{spatial['linhas_mean']:.2f}",
                f"de {volante_dims['rows']} linhas"
            )
        with col_s2:
            metric_card(
                "Média de Colunas Preenchidas",
                f"{spatial['colunas_mean']:.2f}",
                f"de {volante_dims['cols']} colunas"
            )
        with col_s3:
            quad_text = " · ".join([f"{k}: {v:.1f}" for k, v in spatial["quadrante_means"].items()])
            metric_card(
                "Distribuição por Quadrante",
                f"{spatial['quadrante_means']['Top-Left']:.1f} / {spatial['quadrante_means']['Top-Right']:.1f} / {spatial['quadrante_means']['Bottom-Left']:.1f} / {spatial['quadrante_means']['Bottom-Right']:.1f}",
                "TL / TR / BL / BR"
            )
        with col_s4:
            metric_card(
                "% Borda vs Miolo",
                f"{spatial['borda_pct']:.1f}% / {spatial['miolo_pct']:.1f}%",
                f"Borda: {spatial['borda_mean']:.1f} · Miolo: {spatial['miolo_mean']:.1f}"
            )

        col_sp1, col_sp2 = st.columns(2)
        with col_sp1:
            st.plotly_chart(plot_spatial_quadrants(spatial, theme), use_container_width=True)
        with col_sp2:
            st.plotly_chart(plot_spatial_linhas(spatial, theme), use_container_width=True)

    # ===== TAB: BACKTESTING =====
    with tab_backtest:
        st.header("🔬 Backtesting no Histórico")
        st.markdown("Cruza as apostas geradas com todo o histórico para verificar quantas vezes teriam ganho prêmios.")

        if "bets" not in st.session_state or not st.session_state["bets"]:
            st.warning("Gere apostas primeiro na aba **Gerador de Apostas** ou **Fechamento Matemático**.")
        else:
            bets = st.session_state["bets"]
            st.info(f"{len(bets)} apostas carregadas para backtesting contra {n_draws} sorteios.")

            if st.button("🧪 Testar no Histórico", type="primary", key="testar_historico_button"):
                with st.spinner("Executando backtesting..."):
                    results, df_detail, financeiro = run_backtest(bets, draws_matrix, lottery_name)
                    st.session_state["backtest_results"] = results
                    st.session_state["backtest_detail"] = df_detail
                    st.session_state["backtest_financeiro"] = financeiro

            if "backtest_results" in st.session_state:
                results = st.session_state["backtest_results"]
                df_detail = st.session_state["backtest_detail"]
                financeiro = st.session_state.get("backtest_financeiro", {})

                st.plotly_chart(plot_backtest_results(results, theme), use_container_width=True)

                # ---------- ANÁLISE FINANCEIRA (ROI) ----------
                st.markdown("### 💰 Análise Financeira (ROI)")
                st.markdown("Cálculo baseado no custo da aposta e prêmios estimados médios de cada loteria.")

                saldo = financeiro.get("saldo", 0.0)
                roi = financeiro.get("roi", 0.0)
                cor_saldo = "#2ECC40" if saldo >= 0 else "#FF4136"
                cor_roi = "#2ECC40" if roi >= 0 else "#FF4136"

                col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                with col_f1:
                    metric_card("Custo Total", format_brl(financeiro.get("custo_total", 0.0)), f"{len(bets)} apostas × {n_draws} sorteios")
                with col_f2:
                    metric_card("Retorno Estimado", format_brl(financeiro.get("retorno_total", 0.0)), "Prêmios estimados")
                with col_f3:
                    st.markdown(f"""
                    <div class="metric-card" style="border-left: 4px solid {cor_saldo};">
                        <div style="font-size:0.8rem;opacity:0.8;">Saldo</div>
                        <div style="font-size:1.6rem;font-weight:700;color:{cor_saldo};">{format_brl(saldo)}</div>
                        <div style="font-size:0.75rem;opacity:0.6;">{'Lucro' if saldo >= 0 else 'Prejuízo'}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_f4:
                    st.markdown(f"""
                    <div class="metric-card" style="border-left: 4px solid {cor_roi};">
                        <div style="font-size:0.8rem;opacity:0.8;">ROI (%)</div>
                        <div style="font-size:1.6rem;font-weight:700;color:{cor_roi};">{roi:.2f}%</div>
                        <div style="font-size:0.75rem;opacity:0.6;">{'Positivo' if roi >= 0 else 'Negativo'}</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.divider()

                df_res = pd.DataFrame([{"Prêmio": k, "Ocorrências": v} for k, v in results.items() if v > 0])
                df_res = df_res.sort_values("Ocorrências", ascending=False).reset_index(drop=True)

                if not df_detail.empty:
                    # Formatar coluna Valor Estimado para exibição
                    df_detail_display = df_detail.copy()
                    df_detail_display["Valor Estimado"] = df_detail_display["Valor Estimado"].apply(format_brl)
                    df_detail_display = df_detail_display.sort_values("Acertos", ascending=False).reset_index(drop=True)

                    col_b1, col_b2 = st.columns([1, 2])
                    with col_b1:
                        st.subheader("Resumo de Prêmios")
                        st.dataframe(df_res, use_container_width=True, hide_index=True)
                    with col_b2:
                        st.subheader("Detalhamento de Acertos")
                        st.dataframe(df_detail_display.head(50), use_container_width=True, hide_index=True)
                else:
                    st.subheader("Resumo de Prêmios")
                    st.dataframe(df_res, use_container_width=True, hide_index=True)
                    st.info("Nenhum prêmio encontrado no histórico com as apostas atuais. Tente gerar mais apostas ou outra estratégia.")

    # ===== TAB: FECHAMENTO MATEMÁTICO =====
    with tab_fechamento:
        st.header("🔢 Fechamento Matemático")
        st.markdown("Selecione um conjunto maior de dezenas (ex: 10 a 15) e o sistema gerará combinações para o tamanho da aposta da loteria selecionada.")

        total_dezenas = cfg["dezenas_total"]
        aposta_size = cfg["dezenas_aposta"]

        # ---------- SELEÇÃO DO TIPO DE FECHAMENTO ----------
        st.markdown("---")
        st.subheader("📋 Tipo de Fechamento")
        tipo_fechamento = st.radio(
            "Escolha o tipo de fechamento:",
            options=["Fechamento Total", "Fechamento Reduzido (Garantia)"],
            index=0,
            horizontal=True,
            key="tipo_fechamento_radio",
        )

        # ---------- PARÂMETROS DO FECHAMENTO REDUZIDO ----------
        garantir_acertos = None
        limite_jogos = 0
        if tipo_fechamento == "Fechamento Reduzido (Garantia)":
            st.markdown("---")
            st.subheader("🎯 Configuração de Garantia")
            garantia_options = get_garantia_options(lottery_name)
            garantia_labels = [opt[2] for opt in garantia_options]
            selected_garantia_idx = st.selectbox(
                "Garantia",
                options=range(len(garantia_labels)),
                format_func=lambda i: garantia_labels[i],
                index=len(garantia_labels) - 1 if len(garantia_labels) > 0 else 0,
                help="Define o nível de garantia do fechamento reduzido. Ex: 'Garantir 4 se acertar 5' significa que se 5 das dezenas escolhidas forem sorteadas, pelo menos um bilhete terá 4 acertos.",
                key="garantia_select",
            )
            garantir_acertos = garantia_options[selected_garantia_idx][0]
            se_acertar = garantia_options[selected_garantia_idx][1]
            st.info(f"Garantia selecionada: **{garantia_labels[selected_garantia_idx]}** (garantir_acertos = {garantir_acertos})")

            limite_jogos = st.number_input(
                "Quantidade de jogos limite (0 = sem limite)",
                min_value=0,
                max_value=100000,
                value=0,
                step=10,
                help="Define o número máximo de bilhetes a serem gerados. 0 significa sem limite (gera até cobrir todas as garantias).",
                key="limite_jogos_number",
            )

        # ---------- ENTRADA DO USUÁRIO: ESCOLHER DEZENAS ----------
        st.markdown("---")
        st.markdown(f"Escolha de **{aposta_size + 1}** a **{min(15, total_dezenas)}** dezenas entre 1 e {total_dezenas}.")
        # Usamos um text_area para entrada manual
        default_numbers = list(range(1, aposta_size + 2))  # exemplo inicial
        user_input = st.text_area(
            "Digite as dezenas separadas por vírgula ou espaço:",
            value=",".join(map(str, default_numbers)),
            height=80,
            help="Ex: 1,2,3,4,5,6,7",
            key="dezenas_textarea",
        )
        # Processar entrada
        import re
        numbers_str = re.split(r"[,\s]+", user_input.strip())
        chosen_numbers = []
        try:
            chosen_numbers = sorted(set(int(n) for n in numbers_str if n))
        except ValueError:
            st.error("Entrada inválida. Certifique-se de digitar apenas números.")
            chosen_numbers = []

        valid = False
        if chosen_numbers:
            if any(n < 1 or n > total_dezenas for n in chosen_numbers):
                st.error(f"Todas as dezenas devem estar entre 1 e {total_dezenas}.")
            elif len(chosen_numbers) < aposta_size + 1:
                st.warning(f"Escolha pelo menos {aposta_size + 1} dezenas para gerar combinações de {aposta_size}.")
            else:
                valid = True

        if valid:
            # Calcular número total de combinações
            total_combos = len(list(itertools.combinations(chosen_numbers, aposta_size)))
            st.info(f"Você selecionou **{len(chosen_numbers)}** dezenas. Fechamento total geraria **{total_combos}** apostas (combinações de {aposta_size}).")

            # ---------- FILTROS AVANÇADOS ----------
            st.markdown("---")
            st.subheader("⚙️ Filtros Avançados")
            ativar_filtros = st.checkbox("Ativar filtros para reduzir o número de apostas", value=False, key="ativar_filtros_checkbox")

            filtros_params = None
            if ativar_filtros:
                # Calcular limites para o slider de soma
                sorted_nums = sorted(chosen_numbers)
                soma_min = sum(sorted_nums[:aposta_size])
                soma_max = sum(sorted_nums[-aposta_size:])

                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    qtd_impares = st.slider(
                        "Quantidade de Ímpares",
                        min_value=0,
                        max_value=aposta_size,
                        value=aposta_size // 2,
                        help=f"Quantidade exata de números ímpares na aposta (0 a {aposta_size}).",
                        key="qtd_impares_slider",
                    )
                with col_f2:
                    soma_intervalo = st.slider(
                        "Intervalo da Soma",
                        min_value=int(soma_min),
                        max_value=int(soma_max),
                        value=(int(soma_min), int(soma_max)),
                        help=f"Soma mínima: {soma_min} (menores) | Soma máxima: {soma_max} (maiores).",
                        key="soma_intervalo_slider",
                    )
                with col_f3:
                    max_consec = st.slider(
                        "Máx. Números Consecutivos",
                        min_value=1,
                        max_value=aposta_size,
                        value=aposta_size,
                        help=f"Máximo de números consecutivos permitidos (1 a {aposta_size}).",
                        key="max_consec_slider",
                    )

                filtros_params = {
                    "qtd_impares": qtd_impares,
                    "soma_min": soma_intervalo[0],
                    "soma_max": soma_intervalo[1],
                    "max_consec": max_consec,
                }

            # ---------- BOTÃO GERAR FECHAMENTO ----------
            if st.button("Gerar Fechamento", type="primary", key="gerar_fechamento_button"):
                with st.spinner("Calculando combinações..."):
                    if tipo_fechamento == "Fechamento Reduzido (Garantia)":
                        # ---------- FECHAMENTO REDUZIDO ----------
                        with st.spinner(f"Gerando fechamento reduzido (garantir {garantir_acertos})..."):
                            bets, total_garantias = gerar_fechamento_reduzido(
                                chosen_numbers, aposta_size, garantir_acertos, limite_jogos
                            )

                            # Aplicar filtros se ativados
                            if filtros_params is not None and bets:
                                bets_filtradas = []
                                for combo in bets:
                                    qtd_imp = sum(1 for x in combo if x % 2 != 0)
                                    if qtd_imp != filtros_params["qtd_impares"]:
                                        continue
                                    soma_combo = sum(combo)
                                    if soma_combo < filtros_params["soma_min"] or soma_combo > filtros_params["soma_max"]:
                                        continue
                                    if max_consecutivos(combo) > filtros_params["max_consec"]:
                                        continue
                                    bets_filtradas.append(combo)
                                bets = bets_filtradas

                            st.session_state["bets"] = bets

                            # Recalcular análises estatísticas para exportação
                            freq_session = compute_frequency(draws_matrix, total_dezenas)
                            delays_session = compute_delays(draws_matrix, total_dezenas)
                            _, real_pairs_session = monte_carlo_pairs(draws_matrix, total_dezenas, iterations=3000)
                            strong_pairs_session = find_strong_pairs(real_pairs_session, top_n=20)
                            st.session_state["freq"] = freq_session
                            st.session_state["delays"] = delays_session
                            st.session_state["strong_pairs"] = strong_pairs_session

                            st.success(f"{len(bets)} apostas geradas com fechamento reduzido!")

                            col_rf1, col_rf2, col_rf3 = st.columns(3)
                            with col_rf1:
                                metric_card("Apostas Geradas", f"{len(bets)}", f"de {total_combos} possíveis")
                            with col_rf2:
                                metric_card("Combinações de Garantia", f"{total_garantias}", f"garantir {garantir_acertos}")
                            with col_rf3:
                                reducao = total_combos - len(bets)
                                pct_reducao = (reducao / total_combos * 100) if total_combos > 0 else 0
                                metric_card("Redução", f"{reducao} ({pct_reducao:.1f}%)", "vs Fechamento Total")

                    else:
                        # ---------- FECHAMENTO TOTAL (ATUAL) ----------
                        total_original = 0
                        bets = []
                        for combo in itertools.combinations(chosen_numbers, aposta_size):
                            total_original += 1
                            if filtros_params is not None:
                                # Filtro de ímpares
                                qtd_imp = sum(1 for x in combo if x % 2 != 0)
                                if qtd_imp != filtros_params["qtd_impares"]:
                                    continue
                                # Filtro de soma
                                soma_combo = sum(combo)
                                if soma_combo < filtros_params["soma_min"] or soma_combo > filtros_params["soma_max"]:
                                    continue
                                # Filtro de consecutivos
                                if max_consecutivos(combo) > filtros_params["max_consec"]:
                                    continue
                            bets.append(sorted(combo))

                        st.session_state["bets"] = bets
                        # As análises de freq/delays/real_pairs são do histórico, mas para exportação precisamos delas.
                        # Podemos recalcular ou usar as da última geração, mas não temos garantia. Vamos recalcular.
                        freq_session = compute_frequency(draws_matrix, total_dezenas)
                        delays_session = compute_delays(draws_matrix, total_dezenas)
                        _, real_pairs_session = monte_carlo_pairs(draws_matrix, total_dezenas, iterations=3000)
                        strong_pairs_session = find_strong_pairs(real_pairs_session, top_n=20)
                        st.session_state["freq"] = freq_session
                        st.session_state["delays"] = delays_session
                        st.session_state["strong_pairs"] = strong_pairs_session

                        if filtros_params is not None:
                            total_filtrado = len(bets)
                            reducao = total_original - total_filtrado
                            pct_reducao = (reducao / total_original * 100) if total_original > 0 else 0
                            st.success(f"{total_filtrado} apostas geradas com sucesso!")
                            col_rf1, col_rf2, col_rf3 = st.columns(3)
                            with col_rf1:
                                metric_card("Combinações Originais", f"{total_original}", "Sem filtros")
                            with col_rf2:
                                metric_card("Após Filtragem", f"{total_filtrado}", "Com filtros aplicados")
                            with col_rf3:
                                metric_card("Redução", f"{reducao} ({pct_reducao:.1f}%)", "Combinações descartadas")
                        else:
                            st.success(f"{len(bets)} apostas geradas com sucesso!")

        # Exibição das apostas geradas por fechamento (se existirem)
        if "bets" in st.session_state and st.session_state["bets"]:
            bets = st.session_state["bets"]
            # Verificar se o tamanho da aposta bate (pode ser de fechamento ou gerador)
            if len(bets[0]) == aposta_size:
                st.subheader(f"{len(bets)} Apostas do Fechamento")
                df_bets = pd.DataFrame(bets, columns=[f"d{i+1}" for i in range(aposta_size)])
                df_bets.insert(0, "#", range(1, len(bets) + 1))
                st.dataframe(df_bets.head(100), use_container_width=True, hide_index=True)
                if len(bets) > 100:
                    st.caption(f"Mostrando as primeiras 100 de {len(bets)} apostas.")

                # Exportação (reutiliza a função existente)
                if "freq" in st.session_state and "delays" in st.session_state and "strong_pairs" in st.session_state:
                    st.subheader("📥 Exportação Excel")
                    excel_data = export_to_excel(
                        bets,
                        st.session_state["freq"],
                        st.session_state["delays"],
                        st.session_state["strong_pairs"],
                        lottery_name
                    )
                    st.download_button(
                        label="📊 Baixar Fechamento em Excel (.xlsx)",
                        data=excel_data,
                        file_name=f"fechamento_{lottery_name.replace(' ', '_').replace('+', 'mais')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_excel_fechamento",
                    )
                else:
                    st.info("As análises estatísticas não estão disponíveis. Gere as apostas primeiro.")

                # ---------- EXPORTAÇÃO CAIXA (FASE 3) ----------
                st.markdown("---")
                render_caixa_export(bets, lottery_name, download_key="download_json_caixa_fechamento")
            else:
                st.info("As apostas atuais foram geradas pelo Gerador de Apostas (tamanho diferente). Para usar o fechamento, gere novamente nesta aba.")

    # ===== TAB: DADOS =====
    with tab_dados:
        st.header("📋 Dados do Histórico")
        st.dataframe(df_data.head(100), use_container_width=True)
        st.caption(f"Total: {len(df_data)} sorteios | Loteria: {lottery_name}")

        if st.checkbox("Mostrar estatísticas descritivas", key="mostrar_estatisticas_check"):
            st.dataframe(df_data.describe(), use_container_width=True)

    # ---------- FOOTER ----------
    st.divider()
    st.markdown(
        f"<div style='text-align:center;opacity:0.6;font-size:0.8rem;'>"
        f"Motor Analítico de Loterias · Streamlit + Plotly + xlsxwriter + scikit-learn · "
        f"{datetime.now().year} · Jogue com responsabilidade.</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
