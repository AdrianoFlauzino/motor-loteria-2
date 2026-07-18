import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import itertools
import random
import time
from io import BytesIO
from collections import Counter
from datetime import datetime, timedelta

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

# ============================================================
# CONFIGURAÇÃO DAS LOTERIAS
# ============================================================
LOTTERIES = {
    "Mega Sena": {
        "dezenas_total": 60,
        "dezenas_aposta": 6,
        "max_acertos": 6,
        "premios": {4: "Quadra", 5: "Quina", 6: "Sena"},
        "color": "green",
        "tem_trevos": False,
        "tem_mes": False,
    },
    "Lotofácil": {
        "dezenas_total": 25,
        "dezenas_aposta": 15,
        "max_acertos": 15,
        "premios": {11: "Loteria", 12: "Loteria", 13: "Loteria", 14: "Quina", 15: "Sena"},
        "color": "purple",
        "tem_trevos": False,
        "tem_mes": False,
    },
    "Quina": {
        "dezenas_total": 80,
        "dezenas_aposta": 5,
        "max_acertos": 5,
        "premios": {2: "Duque", 3: "Terno", 4: "Quadra", 5: "Quina"},
        "color": "blue",
        "tem_trevos": False,
        "tem_mes": False,
    },
    "+Milionária": {
        "dezenas_total": 50,
        "dezenas_aposta": 6,
        "max_acertos": 6,
        "premios": {4: "Quadra", 5: "Quina", 6: "Sena"},
        "color": "orange",
        "tem_trevos": True,
        "trevos_total": 6,
        "trevos_aposta": 2,
        "tem_mes": False,
    },
    "Dia de Sorte": {
        "dezenas_total": 31,
        "dezenas_aposta": 7,
        "max_acertos": 7,
        "premios": {4: "Quadra", 5: "Quina", 6: "Sena", 7: "Sena+Mês"},
        "color": "pink",
        "tem_trevos": False,
        "tem_mes": True,
        "meses_total": 12,
        "meses_lista": [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
        ],
    },
}

THEME_COLORS = {
    "Branco": {"bg": "#FFFFFF", "text": "#1E3A5F", "accent": "#1E90FF", "card": "#F0F8FF"},
    "Azul": {"bg": "#0A1628", "text": "#E6F0FF", "accent": "#00BFFF", "card": "#13294B"},
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

        # Trevos para +Milionária
        if cfg.get("tem_trevos"):
            trevos = sorted(random.sample(range(1, cfg["trevos_total"] + 1), cfg["trevos_aposta"]))
            for j, t in enumerate(trevos):
                row[f"t{j+1}"] = t

        # Mês para Dia de Sorte
        if cfg.get("tem_mes"):
            row["mes"] = random.randint(1, cfg["meses_total"])

        rows.append(row)
    return pd.DataFrame(rows)

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
    skip = {"concurso", "data", "arrecadacao", "ganhadores", "mes"}
    numeric_cols = []
    for c in df.columns:
        if str(c).lower() in skip:
            continue
        if str(c).lower().startswith("t"):
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            numeric_cols.append(c)
    return numeric_cols

def infer_trevo_columns(df):
    candidates = [c for c in df.columns if str(c).lower().startswith("t")]
    numeric_candidates = []
    for c in candidates:
        try:
            vals = pd.to_numeric(df[c], errors="coerce").dropna()
            if len(vals) > 0 and vals.min() >= 1 and vals.max() <= 6:
                numeric_candidates.append(c)
        except Exception:
            pass
    return numeric_candidates

def infer_mes_column(df):
    for c in df.columns:
        if str(c).lower() == "mes" or str(c).lower() == "mês":
            return c
    return None

def process_uploaded_file(uploaded_file, lottery_name):
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file, sep=None, engine="python")
        else:
            df = pd.read_excel(uploaded_file)

        dezena_cols = infer_dezena_columns(df)
        if len(dezena_cols) < LOTTERIES[lottery_name]["dezenas_aposta"]:
            st.warning("Não foi possível identificar colunas de dezenas suficientes. Usando dados mockados.")
            return None

        pick = LOTTERIES[lottery_name]["dezenas_aposta"]
        keep = dezena_cols[:pick]
        df_out = df[keep].copy()
        df_out.columns = [f"d{i+1}" for i in range(pick)]

        if "concurso" in [str(c).lower() for c in df.columns]:
            for c in df.columns:
                if str(c).lower() == "concurso":
                    df_out.insert(0, "concurso", df[c])
        if "data" in [str(c).lower() for c in df.columns]:
            for c in df.columns:
                if str(c).lower() == "data":
                    df_out.insert(1, "data", df[c])

        cfg = LOTTERIES[lottery_name]

        # Preservar trevos se existirem
        if cfg.get("tem_trevos"):
            trevo_cols = infer_trevo_columns(df)
            if len(trevo_cols) >= cfg["trevos_aposta"]:
                for j in range(cfg["trevos_aposta"]):
                    df_out[f"t{j+1}"] = pd.to_numeric(df[trevo_cols[j]], errors="coerce")

        # Preservar mês se existir
        if cfg.get("tem_mes"):
            mes_col = infer_mes_column(df)
            if mes_col:
                df_out["mes"] = pd.to_numeric(df[mes_col], errors="coerce")

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

def get_trevos_matrix(df, lottery_name):
    cfg = LOTTERIES[lottery_name]
    if not cfg.get("tem_trevos"):
        return None
    pick = cfg["trevos_aposta"]
    cols = [f"t{i+1}" for i in range(pick)]
    existing = [c for c in cols if c in df.columns]
    if len(existing) < pick:
        return None
    mat = df[existing].apply(pd.to_numeric, errors="coerce").dropna()
    return mat.values.astype(int)

def get_meses_series(df, lottery_name):
    cfg = LOTTERIES[lottery_name]
    if not cfg.get("tem_mes"):
        return None
    if "mes" not in df.columns:
        return None
    return pd.to_numeric(df["mes"], errors="coerce").dropna()

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
    real_pairs = Counter()
    for row in draws_matrix:
        for combo in itertools.combinations(sorted(row.tolist()), 2):
            real_pairs[combo] += 1
    return pair_counts, real_pairs

@st.cache_data(show_spinner=False)
def compute_patterns(draws_matrix, total_numbers):
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
def compute_trevos_frequency(trevos_matrix, trevos_total):
    if trevos_matrix is None:
        return {}
    flat = trevos_matrix.flatten()
    freq = Counter(flat.tolist())
    return {n: freq.get(n, 0) for n in range(1, trevos_total + 1)}

@st.cache_data(show_spinner=False)
def compute_trevos_delays(trevos_matrix, trevos_total):
    if trevos_matrix is None:
        return {}
    n_draws = len(trevos_matrix)
    delays = {}
    for num in range(1, trevos_total + 1):
        last_seen = None
        for i in range(n_draws - 1, -1, -1):
            if num in trevos_matrix[i]:
                last_seen = i
                break
        if last_seen is None:
            delays[num] = n_draws
        else:
            delays[num] = (n_draws - 1) - last_seen
    return delays

@st.cache_data(show_spinner=False)
def compute_meses_frequency(meses_series, meses_total):
    if meses_series is None:
        return {}
    freq = Counter(meses_series.tolist())
    return {n: freq.get(n, 0) for n in range(1, meses_total + 1)}

# ============================================================
# GERADOR DE APOSTAS (SEED DINÂMICO)
# ============================================================
def generate_bets(lottery_name, draws_matrix, n_bets=10, strategy="híbrido",
                  weight_freq=0.4, weight_delay=0.3, weight_pairs=0.3,
                  trevos_matrix=None, meses_series=None):
    cfg = LOTTERIES[lottery_name]
    total = cfg["dezenas_total"]
    pick = cfg["dezenas_aposta"]
    freq = compute_frequency(draws_matrix, total)
    delays = compute_delays(draws_matrix, total)
    mc_pairs, real_pairs = monte_carlo_pairs(draws_matrix, total, iterations=3000)

    max_freq = max(freq.values()) if max(freq.values()) > 0 else 1
    max_delay = max(delays.values()) if max(delays.values()) > 0 else 1
    scores = {}
    for num in range(1, total + 1):
        f_score = freq.get(num, 0) / max_freq
        d_score = delays.get(num, 0) / max_delay
        scores[num] = weight_freq * f_score + weight_delay * d_score

    pair_score_map = {num: 0.0 for num in range(1, total + 1)}
    for (a, b), cnt in real_pairs.items():
        pair_score_map[a] += cnt
        pair_score_map[b] += cnt
    max_pair = max(pair_score_map.values()) if max(pair_score_map.values()) > 0 else 1
    for num in pair_score_map:
        scores[num] += weight_pairs * (pair_score_map[num] / max_pair)

    # SEED DINÂMICO: usa timestamp + contador para garantir unicidade
    seed_base = int(time.time() * 1000) % (2**32)
    rng = random.Random(seed_base)

    bets = []
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
            nums = list(scores.keys())
            weights = [scores[n] + 0.01 for n in nums]
            chosen = set()
            while len(chosen) < pick:
                selected = rng.choices(nums, weights=weights, k=1)[0]
                chosen.add(selected)
            chosen = list(chosen)
        bets.append(sorted(chosen))

    # Gerar trevos para +Milionária
    trevos_bets = []
    if cfg.get("tem_trevos") and trevos_matrix is not None:
        trevos_freq = compute_trevos_frequency(trevos_matrix, cfg["trevos_total"])
        trevos_delays = compute_trevos_delays(trevos_matrix, cfg["trevos_total"])
        max_t_freq = max(trevos_freq.values()) if max(trevos_freq.values()) > 0 else 1
        max_t_delay = max(trevos_delays.values()) if max(trevos_delays.values()) > 0 else 1
        t_scores = {}
        for t in range(1, cfg["trevos_total"] + 1):
            t_scores[t] = (0.5 * trevos_freq.get(t, 0) / max_t_freq) + (0.5 * trevos_delays.get(t, 0) / max_t_delay)

        for _ in range(n_bets):
            t_nums = list(t_scores.keys())
            t_weights = [t_scores[t] + 0.01 for t in t_nums]
            t_chosen = set()
            while len(t_chosen) < cfg["trevos_aposta"]:
                t_sel = rng.choices(t_nums, weights=t_weights, k=1)[0]
                t_chosen.add(t_sel)
            trevos_bets.append(sorted(t_chosen))

    # Gerar mês para Dia de Sorte
    mes_bets = []
    if cfg.get("tem_mes") and meses_series is not None:
        meses_freq = compute_meses_frequency(meses_series, cfg["meses_total"])
        max_m_freq = max(meses_freq.values()) if max(meses_freq.values()) > 0 else 1
        m_scores = {m: meses_freq.get(m, 0) / max_m_freq for m in range(1, cfg["meses_total"] + 1)}

        for _ in range(n_bets):
            m_nums = list(m_scores.keys())
            m_weights = [m_scores[m] + 0.01 for m in m_nums]
            m_chosen = rng.choices(m_nums, weights=m_weights, k=1)[0]
            mes_bets.append(m_chosen)

    return bets, freq, delays, real_pairs, trevos_bets, mes_bets

def find_strong_pairs(real_pairs, top_n=20):
    return real_pairs.most_common(top_n)

# ============================================================
# VERIFICAÇÃO DE UNICIDADE DAS APOSTAS
# ============================================================
def bets_are_unique(new_bets, old_bets):
    if not old_bets:
        return True
    old_set = {tuple(b) for b in old_bets}
    for b in new_bets:
        if tuple(b) in old_set:
            return False
    return True

# ============================================================
# BACKTESTING
# ============================================================
def run_backtest(bets, draws_matrix, lottery_name):
    cfg = LOTTERIES[lottery_name]
    premios = cfg["premios"]
    results = {label: 0 for label in set(premios.values())}
    results["Nenhum"] = 0
    detail_rows = []
    bet_sets = [set(b) for b in bets]
    for draw_idx, row in enumerate(draws_matrix):
        draw_set = set(int(x) for x in row)
        for bet_idx, bset in enumerate(bet_sets):
            hits = len(bset & draw_set)
            label = premios.get(hits, None)
            if label:
                results[label] = results.get(label, 0) + 1
                detail_rows.append({
                    "Concurso": draw_idx + 1,
                    "Aposta #": bet_idx + 1,
                    "Acertos": hits,
                    "Prêmio": label,
                })
            elif hits >= 3:
                results["Nenhum"] += 1
    return results, pd.DataFrame(detail_rows)

# ============================================================
# EXPORTAÇÃO EXCEL
# ============================================================
def export_to_excel(bets, freq, delays, strong_pairs, lottery_name, trevos_bets=None, mes_bets=None):
    cfg = LOTTERIES[lottery_name]
    total = cfg["dezenas_total"]

    # DataFrame de apostas
    df_bets = pd.DataFrame(bets, columns=[f"d{i+1}" for i in range(len(bets[0]))])
    df_bets.insert(0, "Aposta", range(1, len(bets) + 1))

    # Adicionar trevos
    if trevos_bets:
        for j in range(cfg["trevos_aposta"]):
            df_bets[f"Trevo {j+1}"] = [t[j] for t in trevos_bets]

    # Adicionar mês
    if mes_bets:
        df_bets["Mês"] = [cfg["meses_lista"][m - 1] for m in mes_bets]

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
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_bets.to_excel(writer, sheet_name="Apostas", index=False)
        df_freq.to_excel(writer, sheet_name="Frequência", index=False)
        df_delays.to_excel(writer, sheet_name="Atrasos", index=False)
        df_pairs.to_excel(writer, sheet_name="Pares Fortes", index=False)

        # Aba de trevos se existir
        if trevos_bets and cfg.get("tem_trevos"):
            trevos_freq = compute_trevos_frequency(
                get_trevos_matrix(st.session_state.get("df_data", pd.DataFrame()), lottery_name),
                cfg["trevos_total"]
            ) if "df_data" in st.session_state else {}
            df_trevos = pd.DataFrame([
                {"Trevo": n, "Frequência": trevos_freq.get(n, 0)} for n in range(1, cfg["trevos_total"] + 1)
            ]).sort_values("Frequência", ascending=False)
            df_trevos.to_excel(writer, sheet_name="Trevos", index=False)

        # Aba de meses se existir
        if mes_bets and cfg.get("tem_mes"):
            df_meses = pd.DataFrame([
                {"Mês #": i + 1, "Mês": cfg["meses_lista"][i], "Frequência": 0}
                for i in range(cfg["meses_total"])
            ])
            df_meses.to_excel(writer, sheet_name="Meses", index=False)

        wb = writer.book
        header_fmt = wb.add_format({"bold": True, "bg_color": "#1E90FF", "font_color": "white", "border": 1})
        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]
            ws.set_column(0, 10, 18)

    output.seek(0)
    return output

# ============================================================
# EXPORTAÇÃO JSON PARA CARRINHO DA CAIXA
# ============================================================
def export_to_caixa_json(bets, lottery_name, trevos_bets=None, mes_bets=None):
    cfg = LOTTERIES[lottery_name]
    loteria_slug = lottery_name.lower().replace(" ", "").replace("+", "").replace("á", "a").replace("í", "i")

    apostas_list = []
    for i, bet in enumerate(bets):
        aposta = {"id": i + 1, "dezenas": bet}
        if trevos_bets:
            aposta["trevos"] = trevos_bets[i]
        if mes_bets:
            aposta["mes"] = mes_bets[i]
            aposta["mes_nome"] = cfg["meses_lista"][mes_bets[i] - 1]
        apostas_list.append(aposta)

    data = {
        "loteria": loteria_slug,
        "loteria_nome": lottery_name,
        "dezenas_aposta": cfg["dezenas_aposta"],
        "total_apostas": len(bets),
        "apostas": apostas_list,
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    if cfg.get("tem_trevos"):
        data["trevos_aposta"] = cfg["trevos_aposta"]
    if cfg.get("tem_mes"):
        data["tem_mes"] = True

    return data

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

def plot_trevos_frequency(freq, total, theme):
    nums = list(range(1, total + 1))
    vals = [freq.get(n, 0) for n in nums]
    fig = go.Figure(data=[go.Bar(x=nums, y=vals, marker_color="#FF8C00")])
    fig.update_layout(
        title="Frequência de Trevos",
        xaxis_title="Trevo", yaxis_title="Frequência",
        template="plotly_white", height=350,
        paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"],
        font=dict(color=theme["text"]),
    )
    return fig

def plot_meses_frequency(freq, meses_lista, theme):
    labels = meses_lista
    vals = [freq.get(i + 1, 0) for i in range(len(labels))]
    fig = go.Figure(data=[go.Bar(x=labels, y=vals, marker_color="#FF69B4")])
    fig.update_layout(
        title="Frequência de Meses Sorteados",
        xaxis_title="Mês", yaxis_title="Frequência",
        template="plotly_white", height=350,
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
    # Ordenar por valor crescente
    pairs = [(k, v) for k, v in results.items() if v > 0 or k != "Nenhum"]
    pairs.sort(key=lambda x: x[1])
    labels = [p[0] for p in pairs]
    values = [p[1] for p in pairs]
    fig = go.Figure(data=[go.Bar(x=labels, y=values, marker_color=theme["accent"], text=values, textposition="auto")])
    fig.update_layout(
        title="Resultado do Backtesting",
        xaxis_title="Categoria de Prêmio", yaxis_title="Ocorrências",
        template="plotly_white", height=400,
        paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"],
        font=dict(color=theme["text"]),
    )
    return fig

# ============================================================
# RENDERIZAÇÃO DE EXPORTAÇÃO CAIXA
# ============================================================
def render_caixa_export(bets, lottery_name, trevos_bets=None, mes_bets=None, download_key="caixa"):
    cfg = LOTTERIES[lottery_name]
    import json

    json_data = export_to_caixa_json(bets, lottery_name, trevos_bets, mes_bets)
    json_str = json.dumps(json_data, ensure_ascii=False, indent=2)

    st.markdown("#### 🛒 Exportação para Carrinho da Caixa")

    # Download JSON
    st.download_button(
        label="📥 Baixar JSON (formato Caixa)",
        data=json_str.encode("utf-8"),
        file_name=f"apostas_caixa_{lottery_name.lower().replace(' ', '_').replace('+', 'mais')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        key=f"download_json_{download_key}",
    )

    # Tabela visual do carrinho
    st.markdown("##### 📋 Carrinho de Apostas")
    carrinho_rows = []
    for i, bet in enumerate(bets):
        row = {"#": i + 1, "Dezenas": " - ".join(f"{n:02d}" for n in bet)}
        if trevos_bets:
            row["Trevos"] = " - ".join(f"🍀{t}" for t in trevos_bets[i])
        if mes_bets:
            row["Mês"] = cfg["meses_lista"][mes_bets[i] - 1]
        carrinho_rows.append(row)
    df_carrinho = pd.DataFrame(carrinho_rows)
    st.dataframe(df_carrinho, use_container_width=True, hide_index=True)

    # Snippet JavaScript
    with st.expander("🔧 Snippet JavaScript (para colar no console do navegador)"):
        st.code(f"""
const apostas = {json_str};

console.log(`Lotaria: ${{apostas.loteria_nome}}`);
console.log(`Total de apostas: ${{apostas.total_apostas}}`);
apostas.apostas.forEach(a => {{
    console.log(`Aposta #${{a.id}}: ${{a.dezenas.join('-')}}` +
        (a.trevos ? ` | Trevos: ${{a.trevos.join('-')}}` : '') +
        (a.mes_nome ? ` | Mês: ${{a.mes_nome}}` : ''));
}});
        """, language="javascript")

# ============================================================
# APP PRINCIPAL
# ============================================================
def main():
    st.set_page_config(page_title="Motor Analítico de Loterias", page_icon="🎲", layout="wide")
    apply_theme_css()
    theme = get_theme()
    st.title("🎲 Motor Analítico & Gerador de Apostas Multi-Loteria")
    st.markdown("<span class='section-title'>Análise estatística avançada · Monte Carlo · Backtesting · Exportação Excel + Caixa</span>", unsafe_allow_html=True)

    # Inicializar contador de geração
    if "gen_counter" not in st.session_state:
        st.session_state["gen_counter"] = 0

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
        st.caption("Colunas de dezenas devem começar com 'd' ou 'bola'. Trevos com 't'. Mês como 'mes'.")
        use_mock = st.checkbox("Usar dados mockados como fallback", value=True, key="use_mock_checkbox")
        st.divider()
        st.subheader("🎲 Gerador de Apostas")
        n_bets = st.slider("Número de apostas", 1, 50, 10, key="n_bets_slider")
        strategy = st.selectbox("Estratégia", ["híbrido", "frequentes", "atrasadas", "aleatória"], index=0, key="strategy_select")
        w_freq = st.slider("Peso Frequência", 0.0, 1.0, 0.4, 0.05, key="weight_freq_slider")
        w_delay = st.slider("Peso Atraso", 0.0, 1.0, 0.3, 0.05, key="weight_delay_slider")
        w_pairs = st.slider("Peso Pares Fortes", 0.0, 1.0, 0.3, 0.05, key="weight_pairs_slider")

    # ---------- CARREGAR DADOS ----------
    df_data = None
    if uploaded_file is not None:
        processed = process_uploaded_file(uploaded_file, lottery_name)
        if processed is not None:
            df_data = processed
            st.sidebar.success(f"✅ Arquivo carregado: {len(df_data)} sorteios")
    if df_data is None and use_mock:
        df_data = generate_mock_data(lottery_name, n_draws=300)
        st.sidebar.info(f"📊 Dados mockados: {len(df_data)} sorteios")
    if df_data is None:
        st.warning("Suba um arquivo ou ative os dados mockados para começar.")
        return

    st.session_state["df_data"] = df_data
    draws_matrix = get_dezenas_matrix(df_data, lottery_name)
    n_draws = len(draws_matrix)

    # Matrizes extras
    trevos_matrix = get_trevos_matrix(df_data, lottery_name) if cfg.get("tem_trevos") else None
    meses_series = get_meses_series(df_data, lottery_name) if cfg.get("tem_mes") else None

    # ---------- MÉTRICAS GERAIS ----------
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Sorteios Analisados", n_draws, "Histórico")
    with col2:
        metric_card("Dezenas por Aposta", cfg["dezenas_aposta"], lottery_name)
    with col3:
        extra = ""
        if cfg.get("tem_trevos"):
            extra = f" + {cfg['trevos_aposta']} trevos"
        elif cfg.get("tem_mes"):
            extra = " + 1 mês"
        metric_card("Universo", f"{cfg['dezenas_total']}{extra}", "Total de dezenas")
    with col4:
        freq = compute_frequency(draws_matrix, cfg["dezenas_total"])
        top_num = max(freq, key=freq.get)
        metric_card("Dezena + Frequente", f"{top_num} ({freq[top_num]}x)", "No histórico")

    st.divider()

    # ---------- TABS ----------
    tab_gerador, tab_fechamento, tab_padroes, tab_backtest, tab_dados = st.tabs([
        "🎰 Gerador de Apostas", "🔢 Fechamento Matemático", "📊 Padrões", "🔬 Backtesting", "📋 Dados"
    ])

    # ===== TAB: GERADOR =====
    with tab_gerador:
        st.header("🎰 Gerador de Apostas Otimizado")
        st.markdown("Combina **frequência**, **atraso** e **pares fortes (Monte Carlo)** com seed dinâmico para apostas únicas a cada clique.")

        # Mostrar contador de geração
        if st.session_state["gen_counter"] > 0:
            st.caption(f"🔄 Geração #{st.session_state['gen_counter']}")

        if st.button("⚡ Gerar Apostas", type="primary", key="gerar_apostas_button"):
            with st.spinner("Gerando apostas otimizadas..."):
                # Garantir unicidade: tentar até 3 vezes se as apostas forem idênticas às anteriores
                max_attempts = 3
                for attempt in range(max_attempts):
                    bets, freq, delays, real_pairs, trevos_bets, mes_bets = generate_bets(
                        lottery_name, draws_matrix, n_bets=n_bets,
                        strategy=strategy, weight_freq=w_freq, weight_delay=w_delay, weight_pairs=w_pairs,
                        trevos_matrix=trevos_matrix, meses_series=meses_series,
                    )
                    old_bets = st.session_state.get("bets", [])
                    if bets_are_unique(bets, old_bets) or attempt == max_attempts - 1:
                        break
                    time.sleep(0.01)  # Pequeno delay para mudar a seed

                strong_pairs = find_strong_pairs(real_pairs, top_n=20)
                st.session_state["bets"] = bets
                st.session_state["freq"] = freq
                st.session_state["delays"] = delays
                st.session_state["strong_pairs"] = strong_pairs
                st.session_state["trevos_bets"] = trevos_bets
                st.session_state["mes_bets"] = mes_bets
                st.session_state["gen_counter"] += 1

        if "bets" in st.session_state and st.session_state["bets"]:
            bets = st.session_state["bets"]
            freq = st.session_state["freq"]
            delays = st.session_state["delays"]
            strong_pairs = st.session_state["strong_pairs"]
            trevos_bets = st.session_state.get("trevos_bets", [])
            mes_bets = st.session_state.get("mes_bets", [])

            st.subheader(f"{len(bets)} Apostas Geradas")

            # DataFrame com apostas
            df_bets = pd.DataFrame(bets, columns=[f"d{i+1}" for i in range(len(bets[0]))])
            df_bets.insert(0, "#", range(1, len(bets) + 1))
            if trevos_bets:
                for j in range(cfg["trevos_aposta"]):
                    df_bets[f"t{j+1}"] = [t[j] for t in trevos_bets]
            if mes_bets:
                df_bets["Mês"] = [cfg["meses_lista"][m - 1] for m in mes_bets]
            st.dataframe(df_bets, use_container_width=True, hide_index=True)

            # Visualização colorida
            st.markdown("### Visualização")
            cols = st.columns(min(len(bets), 5))
            for i, bet in enumerate(bets[:10]):
                with cols[i % len(cols)]:
                    balls_html = " ".join([
                        f"<span style='display:inline-block;width:28px;height:28px;line-height:28px;text-align:center;border-radius:50%;background:{theme['accent']};color:white;font-weight:bold;margin:2px;font-size:0.75rem;'>{n}</span>"
                        for n in bet
                    ])
                    extra_html = ""
                    if trevos_bets:
                        trevos_html = " ".join([
                            f"<span style='display:inline-block;width:28px;height:28px;line-height:28px;text-align:center;border-radius:50%;background:#FF8C00;color:white;font-weight:bold;margin:2px;font-size:0.75rem;'>🍀{t}</span>"
                            for t in trevos_bets[i]
                        ])
                        extra_html = f"<br>{trevos_html}"
                    if mes_bets:
                        mes_nome = cfg["meses_lista"][mes_bets[i] - 1]
                        extra_html += f"<br><span style='display:inline-block;padding:4px 10px;border-radius:8px;background:#FF69B4;color:white;font-weight:bold;margin:2px;font-size:0.75rem;'>📅 {mes_nome}</span>"

                    st.markdown(
                        f"<div style='padding:8px;background:{theme['card']};border-radius:10px;margin:4px 0;'>"
                        f"<b>Aposta {i+1}</b><br>{balls_html}{extra_html}</div>",
                        unsafe_allow_html=True
                    )

            # Gráficos de frequência e atraso
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.plotly_chart(plot_frequency_bar(freq, cfg["dezenas_total"], theme), use_container_width=True)
            with col_g2:
                st.plotly_chart(plot_delays_bar(delays, cfg["dezenas_total"], theme), use_container_width=True)

            # Gráficos de trevos se existir
            if cfg.get("tem_trevos") and trevos_matrix is not None:
                trevos_freq = compute_trevos_frequency(trevos_matrix, cfg["trevos_total"])
                trevos_delays = compute_trevos_delays(trevos_matrix, cfg["trevos_total"])
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    st.plotly_chart(plot_trevos_frequency(trevos_freq, cfg["trevos_total"], theme), use_container_width=True)
                with col_t2:
                    st.plotly_chart(plot_delays_bar(trevos_delays, cfg["trevos_total"], theme), use_container_width=True)

            # Gráfico de meses se existir
            if cfg.get("tem_mes") and meses_series is not None:
                meses_freq = compute_meses_frequency(meses_series, cfg["meses_total"])
                st.plotly_chart(plot_meses_frequency(meses_freq, cfg["meses_lista"], theme), use_container_width=True)

            # Pares fortes
            st.subheader("🔗 Pares Fortes (Monte Carlo + Histórico)")
            df_pairs = pd.DataFrame(strong_pairs, columns=["Par", "Ocorrências"])
            df_pairs["Dezena_A"] = df_pairs["Par"].apply(lambda x: x[0])
            df_pairs["Dezena_B"] = df_pairs["Par"].apply(lambda x: x[1])
            st.dataframe(df_pairs[["Dezena_A", "Dezena_B", "Ocorrências"]].head(15), use_container_width=True, hide_index=True)

            # Exportação Excel
            st.subheader("📥 Exportação Excel")
            excel_data = export_to_excel(bets, freq, delays, strong_pairs, lottery_name, trevos_bets, mes_bets)
            st.download_button(
                label="📊 Baixar Apostas em Excel (.xlsx)",
                data=excel_data,
                file_name=f"apostas_{lottery_name.replace(' ', '_').replace('+', 'mais')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel_apostas",
            )
            st.caption("O arquivo Excel contém abas: **Apostas**, **Frequência**, **Atrasos**, **Pares Fortes**" +
                       (" e **Trevos**" if cfg.get("tem_trevos") else "") +
                       (" e **Meses**" if cfg.get("tem_mes") else "") + ".")

            # Exportação Caixa
            st.divider()
            render_caixa_export(bets, lottery_name, trevos_bets, mes_bets, download_key="gerador")
        else:
            st.info("Clique em **⚡ Gerar Apostas** para criar combinações otimizadas.")

    # ===== TAB: FECHAMENTO MATEMÁTICO =====
    with tab_fechamento:
        st.header("🔢 Fechamento Matemático")
        st.markdown("Gera combinações matemáticas a partir de dezenas escolhidas, com filtros opcionais.")

        dezenas_input = st.text_area(
            "Digite as dezenas separadas por vírgula (ex: 5, 12, 23, 34, 47, 58)",
            value="",
            height=80,
            key="dezenas_textarea"
        )

        st.markdown("**Filtros (opcionais):**")
        usar_filtros = st.checkbox("Ativar filtros para reduzir apostas", value=False, key="ativar_filtros_checkbox")

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            qtd_impares = st.slider("Qtd. de ímpares (exato)", 0, cfg["dezenas_aposta"], cfg["dezenas_aposta"] // 2, key="qtd_impares_slider") if usar_filtros else cfg["dezenas_aposta"] // 2
        with col_f2:
            soma_min = int(cfg["dezenas_total"] * cfg["dezenas_aposta"] * 0.3)
            soma_max = int(cfg["dezenas_total"] * cfg["dezenas_aposta"] * 0.7)
            soma_intervalo = st.slider("Intervalo da soma", 1, cfg["dezenas_total"] * cfg["dezenas_aposta"], (soma_min, soma_max), key="soma_intervalo_slider") if usar_filtros else (1, cfg["dezenas_total"] * cfg["dezenas_aposta"])
        with col_f3:
            max_consec = st.slider("Máx. números consecutivos", 1, cfg["dezenas_aposta"], cfg["dezenas_aposta"], key="max_consec_slider") if usar_filtros else cfg["dezenas_aposta"]

        if st.button("🔢 Gerar Fechamento", type="primary", key="gerar_fechamento_button"):
            try:
                dezenas_list = [int(x.strip()) for x in dezenas_input.split(",") if x.strip()]
                dezenas_list = sorted(set(dezenas_list))
                pick = cfg["dezenas_aposta"]

                if len(dezenas_list) < pick:
                    st.warning(f"Você precisa de pelo menos {pick} dezenas para gerar combinações.")
                else:
                    total_combinations = list(itertools.combinations(dezenas_list, pick))
                    filtered = []

                    for combo in total_combinations:
                        if usar_filtros:
                            # Filtro de ímpares
                            impares = sum(1 for x in combo if x % 2 != 0)
                            if impares != qtd_impares:
                                continue
                            # Filtro de soma
                            soma = sum(combo)
                            if soma < soma_intervalo[0] or soma > soma_intervalo[1]:
                                continue
                            # Filtro de consecutivos
                            consec = 1
                            max_consec_found = 1
                            for i in range(1, len(combo)):
                                if combo[i] == combo[i-1] + 1:
                                    consec += 1
                                    max_consec_found = max(max_consec_found, consec)
                                else:
                                    consec = 1
                            if max_consec_found > max_consec:
                                continue
                        filtered.append(sorted(combo))

                    if not filtered:
                        st.warning("Nenhuma combinação passou nos filtros. Tente afrouxar os critérios.")
                    else:
                        st.session_state["fechamento_bets"] = filtered
                        st.session_state["fechamento_total_original"] = len(total_combinations)
                        st.session_state["fechamento_total_filtrado"] = len(filtered)
            except ValueError:
                st.error("Digite apenas números separados por vírgula.")

        if "fechamento_bets" in st.session_state and st.session_state["fechamento_bets"]:
            f_bets = st.session_state["fechamento_bets"]
            total_orig = st.session_state["fechamento_total_original"]
            total_filt = st.session_state["fechamento_total_filtrado"]

            st.subheader(f"{len(f_bets)} Combinações Geradas")

            # Métricas de redução
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                metric_card("Combinações Originais", total_orig, "Fechamento total")
            with col_r2:
                metric_card("Após Filtros", total_filt, "Combinações válidas")
            with col_r3:
                reducao = total_orig - total_filt
                perc = (reducao / total_orig * 100) if total_orig > 0 else 0
                metric_card("Redução", f"{reducao} ({perc:.1f}%)", "Economia de apostas")

            # DataFrame
            df_fech = pd.DataFrame(f_bets, columns=[f"d{i+1}" for i in range(cfg["dezenas_aposta"])])
            df_fech.insert(0, "#", range(1, len(f_bets) + 1))
            st.dataframe(df_fech, use_container_width=True, hide_index=True)

            # Exportação Excel
            excel_fech = export_to_excel(f_bets, freq, delays, strong_pairs if "strong_pairs" in st.session_state else [], lottery_name)
            st.download_button(
                label="📊 Baixar Fechamento em Excel (.xlsx)",
                data=excel_fech,
                file_name=f"fechamento_{lottery_name.replace(' ', '_').replace('+', 'mais')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel_fechamento",
            )

            # Exportação Caixa
            st.divider()
            render_caixa_export(f_bets, lottery_name, download_key="fechamento")
        else:
            st.info("Digite suas dezenas acima e clique em **🔢 Gerar Fechamento**.")

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

    # ===== TAB: BACKTESTING =====
    with tab_backtest:
        st.header("🔬 Backtesting no Histórico")
        st.markdown("Cruza as apostas geradas com todo o histórico para verificar quantas vezes teriam ganho prêmios.")
        if "bets" not in st.session_state or not st.session_state["bets"]:
            st.warning("Gere apostas primeiro na aba **Gerador de Apostas**.")
        else:
            bets = st.session_state["bets"]
            st.info(f"{len(bets)} apostas carregadas para backtesting contra {n_draws} sorteios.")
            if st.button("🧪 Testar no Histórico", type="primary", key="testar_historico_button"):
                with st.spinner("Executando backtesting..."):
                    results, df_detail = run_backtest(bets, draws_matrix, lottery_name)
                    st.session_state["backtest_results"] = results
                    st.session_state["backtest_detail"] = df_detail
            if "backtest_results" in st.session_state:
                results = st.session_state["backtest_results"]
                df_detail = st.session_state["backtest_detail"]
                st.plotly_chart(plot_backtest_results(results, theme), use_container_width=True)

                col_b1, col_b2 = st.columns([1, 2])
                with col_b1:
                    st.subheader("Resumo de Prêmios")
                    df_res = pd.DataFrame([{"Prêmio": k, "Ocorrências": v} for k, v in results.items() if v > 0])
                    df_res = df_res.sort_values("Ocorrências", ascending=False)
                    st.dataframe(df_res, use_container_width=True, hide_index=True)
                with col_b2:
                    st.subheader("Detalhamento de Acertos")
                    if not df_detail.empty:
                        df_detail_display = df_detail.sort_values("Acertos", ascending=False)
                        st.dataframe(df_detail_display.head(50), use_container_width=True, hide_index=True)
                    else:
                        st.info("Nenhum prêmio encontrado. Tente outra estratégia.")

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
        f"Motor Analítico de Loterias · Streamlit + Plotly + xlsxwriter · "
        f"{datetime.now().year} · Jogue com responsabilidade.</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
