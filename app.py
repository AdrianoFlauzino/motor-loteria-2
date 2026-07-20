import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import itertools
import random
import time
import json
import requests
from io import BytesIO
from collections import Counter
from datetime import datetime, timedelta

try:
    from math import comb
except ImportError:
    from math import factorial
    def comb(n, k):
        if k < 0 or k > n:
            return 0
        return factorial(n) // (factorial(k) * factorial(n - k))

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

LOTTERIES = {
    "Mega Sena": {
        "dezenas_total": 60, "dezenas_aposta": 6, "max_acertos": 6,
        "premios": {4: "Quadra", 5: "Quina", 6: "Sena"},
        "color": "green", "api_slug": "megasena",
        "tem_trevos": False, "tem_mes": False, "custo_aposta": 6.00,
        "max_dezenas_aposta": 15,
    },
    "Lotofácil": {
        "dezenas_total": 25, "dezenas_aposta": 15, "max_acertos": 15,
        "premios": {11: "Loteria", 12: "Loteria", 13: "Loteria", 14: "Quina", 15: "Sena"},
        "color": "purple", "api_slug": "lotofacil",
        "tem_trevos": False, "tem_mes": False, "custo_aposta": 3.50,
        "max_dezenas_aposta": 20,
    },
    "Quina": {
        "dezenas_total": 80, "dezenas_aposta": 5, "max_acertos": 5,
        "premios": {2: "Duque", 3: "Terno", 4: "Quadra", 5: "Quina"},
        "color": "blue", "api_slug": "quina",
        "tem_trevos": False, "tem_mes": False, "custo_aposta": 3.00,
        "max_dezenas_aposta": 15,
    },
    "+Milionária": {
        "dezenas_total": 50, "dezenas_aposta": 6, "max_acertos": 6,
        "premios": {4: "Quadra", 5: "Quina", 6: "Sena"},
        "color": "orange", "api_slug": "maismilionaria",
        "tem_trevos": True, "trevos_total": 6, "trevos_aposta": 2,
        "tem_mes": False, "custo_aposta": 6.00,
        "max_dezenas_aposta": 15,
    },
    "Dia de Sorte": {
        "dezenas_total": 31, "dezenas_aposta": 7, "max_acertos": 7,
        "premios": {4: "Quadra", 5: "Quina", 6: "Sena", 7: "Sena+Mês"},
        "color": "pink", "api_slug": "diadesorte",
        "tem_trevos": False,
        "tem_mes": True, "meses_total": 12,
        "meses_lista": ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
                        "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"],
        "custo_aposta": 2.50,
        "max_dezenas_aposta": 15,
    },
}

PREMIOS_ESTIMADOS = {
    "Mega Sena": {"Sena": 50_000_000, "Quina": 50_000, "Quadra": 1500},
    "Lotofácil": {"Sena": 2_000_000, "Quina": 1000, "Loteria": 25},
    "Quina": {"Quina": 1_000_000, "Quadra": 10_000, "Terno": 200, "Duque": 5},
    "+Milionária": {"Sena": 100_000_000, "Quina": 30_000, "Quadra": 1000},
    "Dia de Sorte": {"Sena+Mês": 500_000, "Sena": 50_000, "Quina": 3000, "Quadra": 100},
}

THEME_COLORS = {
    "Branco": {"bg": "#FFFFFF", "text": "#1E3A5F", "accent": "#1E90FF", "card": "#F0F8FF"},
    "Azul": {"bg": "#0A1628", "text": "#E6F0FF", "accent": "#00BFFF", "card": "#13294B"},
}

API_BASE = "https://servicebus2.caixa.gov.br/portaldeloterias/api"

def fetch_caixa_latest(lottery_name):
    cfg = LOTTERIES[lottery_name]
    url = f"{API_BASE}/{cfg['api_slug']}"
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Erro ao buscar dados da Caixa: {e}")
        return None

def fetch_caixa_concurso(lottery_name, concurso):
    cfg = LOTTERIES[lottery_name]
    url = f"{API_BASE}/{cfg['api_slug']}/{concurso}"
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None

def parse_caixa_json(data, lottery_name):
    if not data:
        return None
    cfg = LOTTERIES[lottery_name]
    pick = cfg["dezenas_aposta"]
    dezenas = []
    if "dezenasSorteadasOrdemSorteio" in data:
        dezenas = [int(d) for d in data["dezenasSorteadasOrdemSorteio"]]
    elif "listaDezenas" in data:
        dezenas = [int(d) for d in data["listaDezenas"]]
    elif "dezenas" in data:
        dezenas = [int(d) for d in data["dezenas"]]
    if len(dezenas) < pick:
        return None
    row = {"concurso": data.get("numero", 0), "data": data.get("dataApuracao", "")}
    for j, n in enumerate(sorted(dezenas[:pick])):
        row[f"d{j+1}"] = n
    if cfg.get("tem_trevos"):
        trevos = []
        if "dezenasSorteadasSegundoSorteio" in data:
            trevos = [int(t) for t in data["dezenasSorteadasSegundoSorteio"]]
        elif "trevos" in data:
            trevos = [int(t) for t in data["trevos"]]
        elif "listaDezenasSegundoSorteio" in data:
            trevos = [int(t) for t in data["listaDezenasSegundoSorteio"]]
        for j, t in enumerate(sorted(trevos[:cfg["trevos_aposta"]])):
            row[f"t{j+1}"] = t
    if cfg.get("tem_mes"):
        mes = None
        if "mesSorteado" in data and data["mesSorteado"]:
            mes_str = str(data["mesSorteado"])
            for i, m in enumerate(cfg["meses_lista"]):
                if m.lower() == mes_str.lower():
                    mes = i + 1
                    break
            if mes is None:
                try:
                    mes = int(mes_str)
                except ValueError:
                    mes = None
        elif "nomeMesSorteado" in data:
            mes_str = str(data["nomeMesSorteado"])
            for i, m in enumerate(cfg["meses_lista"]):
                if m.lower() == mes_str.lower():
                    mes = i + 1
                    break
        if mes is None:
            mes = random.randint(1, 12)
        row["mes"] = mes
    return row

@st.cache_data(show_spinner="Buscando histórico na Caixa...", ttl=3600)
def fetch_caixa_history(lottery_name, n_concursos=50):
    latest = fetch_caixa_latest(lottery_name)
    if not latest:
        return None
    latest_num = latest.get("numero", 0)
    if latest_num == 0:
        return None
    rows = []
    parsed = parse_caixa_json(latest, lottery_name)
    if parsed:
        rows.append(parsed)
    start = latest_num - 1
    end = max(1, latest_num - n_concursos + 1)
    for concurso_num in range(start, end - 1, -1):
        data = fetch_caixa_concurso(lottery_name, concurso_num)
        if data:
            parsed = parse_caixa_json(data, lottery_name)
            if parsed:
                rows.append(parsed)
        time.sleep(0.15)
    return pd.DataFrame(rows) if rows else None

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
    css = f"""
    <style>
    .stApp {{ background-color: {theme['bg']}; color: {theme['text']}; }}
    .stTabs [data-baseweb="tab"] {{ color: {theme['text']}; }}
    .stTabs [aria-selected="true"] {{ color: {theme['accent']}; border-bottom-color: {theme['accent']}; }}
    .main-header {{
        background: linear-gradient(135deg, {theme['card']}, {theme['bg']});
        border-radius: 16px; padding: 24px 28px; margin-bottom: 16px;
        border: 1px solid {theme['accent']}33;
    }}
    .main-title {{ font-size: 1.8rem; font-weight: 800; color: {theme['text']}; margin: 0; line-height: 1.2; }}
    .main-subtitle {{ font-size: 0.85rem; color: {theme['accent']}; font-weight: 600; margin-top: 6px; letter-spacing: 0.3px; }}
    .metric-card {{
        background-color: {theme['card']}; border-radius: 14px; padding: 20px 16px; margin: 4px 0;
        border: 1px solid {theme['accent']}22; box-shadow: 0 2px 8px rgba(0,0,0,0.04); text-align: center;
    }}
    .metric-label {{ font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.7; font-weight: 600; margin-bottom: 8px; }}
    .metric-value {{ font-size: 1.75rem; font-weight: 800; color: {theme['accent']}; line-height: 1; margin-bottom: 4px; }}
    .metric-sub {{ font-size: 0.7rem; opacity: 0.6; font-weight: 500; }}
    .section-title {{ color: {theme['accent']}; font-weight: 700; font-size: 1.3rem; }}
    </style>
    """
    try:
        st.html(css)
    except AttributeError:
        st.markdown(css, unsafe_allow_html=True)

def metric_card(label, value, sub=""):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)

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
        if cfg.get("tem_trevos"):
            trevos = sorted(random.sample(range(1, cfg["trevos_total"] + 1), cfg["trevos_aposta"]))
            for j, t in enumerate(trevos):
                row[f"t{j+1}"] = t
        if cfg.get("tem_mes"):
            row["mes"] = random.randint(1, cfg["meses_total"])
        rows.append(row)
    return pd.DataFrame(rows)

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
        if str(c).lower() in skip or str(c).lower().startswith("t"):
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
        if str(c).lower() in ("mes", "mês"):
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
        if cfg.get("tem_trevos"):
            trevo_cols = infer_trevo_columns(df)
            if len(trevo_cols) >= cfg["trevos_aposta"]:
                for j in range(cfg["trevos_aposta"]):
                    df_out[f"t{j+1}"] = pd.to_numeric(df[trevo_cols[j]], errors="coerce")
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

@st.cache_data(show_spinner=False)
def compute_frequency(draws_matrix, total_numbers):
    flat = draws_matrix.flatten()
    freq = Counter(flat.tolist())
    return {n: freq.get(n, 0) for n in range(1, total_numbers + 1)}

@st.cache_data(show_spinner=False)
def compute_weighted_frequency(draws_matrix, total_numbers, decay=0.95):
    n_draws = len(draws_matrix)
    weights = np.array([decay ** (n_draws - 1 - i) for i in range(n_draws)])
    w_freq = {n: 0.0 for n in range(1, total_numbers + 1)}
    for i, row in enumerate(draws_matrix):
        w = weights[i]
        for num in row:
            w_freq[int(num)] += w
    return w_freq

@st.cache_data(show_spinner=False)
def compute_hot_cold(draws_matrix, total_numbers, recent_n=20):
    recent = draws_matrix[-recent_n:] if len(draws_matrix) >= recent_n else draws_matrix
    flat = recent.flatten()
    freq_recent = Counter(flat.tolist())
    all_nums = list(range(1, total_numbers + 1))
    freq_list = [(n, freq_recent.get(n, 0)) for n in all_nums]
    freq_list.sort(key=lambda x: x[1], reverse=True)
    n_hot = max(1, total_numbers // 4)
    n_cold = max(1, total_numbers // 4)
    hot_set = set(n for n, _ in freq_list[:n_hot])
    cold_set = set(n for n, _ in freq_list[-n_cold:])
    return {
        "hot_set": hot_set,
        "cold_set": cold_set,
        "freq_recent": {n: freq_recent.get(n, 0) for n in all_nums},
        "freq_list": freq_list,
        "recent_n": len(recent),
    }

@st.cache_data(show_spinner=False)
def compute_gap_analysis(draws_matrix, total_numbers):
    n_draws = len(draws_matrix)
    draw_sets = [set(row.tolist()) for row in draws_matrix]
    gaps = {}
    for num in range(1, total_numbers + 1):
        appearances = []
        for i in range(n_draws):
            if num in draw_sets[i]:
                appearances.append(i)
        if len(appearances) == 0:
            gaps[num] = {"mean_gap": n_draws, "std_gap": 0, "current_gap": n_draws, "z_score": 0, "overdue": False, "appearances": [], "prob_next": 0.0}
            continue
        intervals = []
        for i in range(1, len(appearances)):
            intervals.append(appearances[i] - appearances[i - 1])
        if not intervals:
            intervals = [appearances[0]] if appearances[0] > 0 else [n_draws]
        mean_gap = float(np.mean(intervals))
        std_gap = float(np.std(intervals)) if len(intervals) > 1 else 0.0
        last_pos = appearances[-1]
        current_gap = n_draws - 1 - last_pos
        z_score = ((current_gap - mean_gap) / std_gap) if std_gap > 0 else 0.0
        overdue = current_gap > mean_gap + 2 * std_gap and std_gap > 0
        prob_next = max(0.0, min(1.0, 1.0 / (mean_gap + 1) + (z_score * 0.05) if z_score > 0 else 1.0 / (mean_gap + 1)))
        gaps[num] = {"mean_gap": round(mean_gap, 2), "std_gap": round(std_gap, 2), "current_gap": current_gap, "z_score": round(z_score, 2), "overdue": overdue, "appearances": appearances, "prob_next": round(prob_next * 100, 1)}
    return gaps

@st.cache_data(show_spinner=False)
def compute_markov_chain(draws_matrix, total_numbers):
    n_draws = len(draws_matrix)
    if n_draws < 2:
        return None
    trans = np.zeros((total_numbers + 1, total_numbers + 1))
    for i in range(n_draws - 1):
        current = set(int(x) for x in draws_matrix[i])
        nxt = set(int(x) for x in draws_matrix[i + 1])
        for x in current:
            for y in nxt:
                trans[x][y] += 1
    row_sums = trans.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    prob = trans / row_sums
    last_draw = set(int(x) for x in draws_matrix[-1])
    next_probs = np.zeros(total_numbers + 1)
    for x in last_draw:
        next_probs += prob[x]
    next_probs /= max(1, len(last_draw))
    return {"transition_matrix": prob, "next_probs": {n: round(float(next_probs[n]) * 100, 2) for n in range(1, total_numbers + 1)}, "last_draw": sorted(last_draw), "n_transitions": int(trans.sum())}

@st.cache_data(show_spinner=False)
def compute_delays(draws_matrix, total_numbers):
    n_draws = len(draws_matrix)
    draw_sets = [set(row.tolist()) for row in draws_matrix]
    delays = {}
    for num in range(1, total_numbers + 1):
        last_seen = None
        for i in range(n_draws - 1, -1, -1):
            if num in draw_sets[i]:
                last_seen = i
                break
        delays[num] = n_draws if last_seen is None else (n_draws - 1) - last_seen
    return delays

@st.cache_data(show_spinner=False)
def monte_carlo_pairs(draws_matrix, total_numbers, iterations=1500):
    rng = np.random.default_rng(42)
    samples = rng.choice(total_numbers, size=(iterations, 2), replace=True)
    pair_counts = Counter()
    for s in samples:
        if s[0] != s[1]:
            pair = tuple(sorted(s.tolist()))
            pair_counts[pair] += 1
    real_pairs = Counter()
    for row in draws_matrix:
        for combo in itertools.combinations(sorted(row.tolist()), 2):
            real_pairs[combo] += 1
    return pair_counts, real_pairs

@st.cache_data(show_spinner=False)
def compute_patterns(draws_matrix, total_numbers):
    arr = np.array(draws_matrix)
    impares = (arr % 2 != 0).sum(axis=1)
    impar_ratios = (impares / arr.shape[1]).tolist()
    sums = arr.sum(axis=1).tolist()
    prime_set = {x for x in range(2, total_numbers + 1) if all(x % i != 0 for i in range(2, int(np.sqrt(x)) + 1))}
    prime_counts = [sum(1 for x in row if int(x) in prime_set) for row in arr]
    return {"impar_ratio_mean": float(np.mean(impar_ratios)), "impar_ratios": impar_ratios, "prime_mean": float(np.mean(prime_counts)), "prime_counts": prime_counts, "sums": sums, "sum_mean": float(np.mean(sums)), "sum_std": float(np.std(sums))}

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
    draw_sets = [set(row.tolist()) for row in trevos_matrix]
    delays = {}
    for num in range(1, trevos_total + 1):
        last_seen = None
        for i in range(n_draws - 1, -1, -1):
            if num in draw_sets[i]:
                last_seen = i
                break
        delays[num] = n_draws if last_seen is None else (n_draws - 1) - last_seen
    return delays

@st.cache_data(show_spinner=False)
def compute_meses_frequency(meses_series, meses_total):
    if meses_series is None:
        return {}
    freq = Counter(meses_series.tolist())
    return {n: freq.get(n, 0) for n in range(1, meses_total + 1)}

@st.cache_data(show_spinner=False)
def compute_quadrants(total_numbers, n_quadrants=4):
    size = total_numbers // n_quadrants
    quadrants = {}
    for q in range(n_quadrants):
        start = q * size + 1
        end = (q + 1) * size if q < n_quadrants - 1 else total_numbers
        quadrants[q + 1] = list(range(start, end + 1))
    return quadrants

def get_quadrant(num, quadrants):
    for q, nums in quadrants.items():
        if num in nums:
            return q
    return 0

def count_quadrant_distribution(bet, quadrants):
    dist = {q: 0 for q in quadrants}
    for n in bet:
        q = get_quadrant(n, quadrants)
        dist[q] = dist.get(q, 0) + 1
    return dist

@st.cache_data(show_spinner=False)
def compute_cycle_completion(draws_matrix, total_numbers):
    seen = set()
    cycle_start = 0
    for i in range(len(draws_matrix) - 1, -1, -1):
        for n in draws_matrix[i]:
            seen.add(int(n))
        if len(seen) == total_numbers:
            cycle_start = i
            seen = set()
            for n in draws_matrix[i]:
                seen.add(int(n))
    missing = [n for n in range(1, total_numbers + 1) if n not in seen]
    completion = (len(seen) / total_numbers) * 100
    return {"seen": sorted(seen), "missing": sorted(missing), "completion_pct": round(completion, 1), "total_unique": len(seen), "total_numbers": total_numbers, "cycle_start_idx": cycle_start}

def compute_alerts(total_numbers, gap_data, cycle):
    alerts = []
    for num in range(1, total_numbers + 1):
        g = gap_data[num]
        if g["mean_gap"] > 0 and g["current_gap"] > g["mean_gap"] * 2:
            appearances = g["appearances"]
            if len(appearances) >= 2:
                intervals = [appearances[i] - appearances[i-1] for i in range(1, len(appearances))]
                max_interval = max(intervals) if intervals else 0
            elif len(appearances) == 1:
                max_interval = appearances[0]
            else:
                max_interval = 0
            if g["current_gap"] > max_interval and g["current_gap"] >= 5:
                alerts.append({"tipo": "recorde_atraso", "severidade": "alta", "icone": "🔴", "titulo": f"Dezena {num} em recorde de atraso", "detalhe": f"Gap atual: {g['current_gap']} concursos (máx. histórico: {max_interval}, média: {g['mean_gap']:.1f})"})
    if cycle["completion_pct"] >= 99.9:
        alerts.append({"tipo": "ciclo_completo", "severidade": "alta", "icone": "🟢", "titulo": "Ciclo de Completude atingiu 100%", "detalhe": f"Todas as {total_numbers} dezenas já foram vistas no ciclo atual"})
    elif cycle["completion_pct"] >= 90:
        alerts.append({"tipo": "ciclo_quase", "severidade": "media", "icone": "🟡", "titulo": f"Ciclo quase completo: {cycle['completion_pct']}%", "detalhe": f"Faltam {len(cycle['missing'])} dezenas para completar o ciclo"})
    overdue_count = sum(1 for n in range(1, total_numbers + 1) if gap_data[n]["overdue"])
    if overdue_count >= 5:
        alerts.append({"tipo": "multiplas_overdue", "severidade": "media", "icone": "🟡", "titulo": f"{overdue_count} dezenas overdue simultaneamente", "detalhe": "Dezenas com gap > média + 2σ"})
    if cycle["completion_pct"] > 70 and len(cycle["missing"]) <= 5 and cycle["missing"]:
        alerts.append({"tipo": "ciclo_faltando_poucas", "severidade": "media", "icone": "🟡", "titulo": f"Apenas {len(cycle['missing'])} dezenas faltando no ciclo", "detalhe": f"Dezenas: {', '.join(str(m) for m in cycle['missing'])} recebem +15% no score"})
    return alerts

def is_bet_valid(bet, patterns, lottery_name, quadrants):
    pick = len(bet)
    impares = sum(1 for x in bet if x % 2 != 0)
    if impares == 0 or impares == pick:
        return False, "Todos pares ou ímpares"
    soma = sum(bet)
    mean = patterns["sum_mean"]
    std = patterns["sum_std"]
    if std > 0 and abs(soma - mean) > 2.5 * std:
        return False, "Soma fora de 2.5σ"
    sorted_bet = sorted(bet)
    max_consec = 1
    current_consec = 1
    for i in range(1, len(sorted_bet)):
        if sorted_bet[i] == sorted_bet[i-1] + 1:
            current_consec += 1
            max_consec = max(max_consec, current_consec)
        else:
            current_consec = 1
    if max_consec > 3:
        return False, "Mais de 3 consecutivos"
    qdist = count_quadrant_distribution(bet, quadrants)
    if any(v > 4 for v in qdist.values()):
        return False, "Quadrante sobrecarregado"
    return True, "Válido"

def compute_bet_score(bet, freq, delays, pair_score_map, patterns, quadrants, total, max_freq, max_delay, max_pair_score):
    freq_score = sum(freq.get(n, 0) for n in bet) / (max_freq * len(bet)) if max_freq > 0 else 0
    delay_score = sum(delays.get(n, 0) for n in bet) / (max_delay * len(bet)) if max_delay > 0 else 0
    qdist = count_quadrant_distribution(bet, quadrants)
    n_quads = len(quadrants)
    ideal = len(bet) / n_quads
    quad_penalty = sum(abs(v - ideal) for v in qdist.values())
    quad_score = max(0, 1 - quad_penalty / len(bet))
    soma = sum(bet)
    std = patterns["sum_std"]
    if std > 0:
        z = abs(soma - patterns["sum_mean"]) / std
        sum_score = max(0, 1 - z / 3)
    else:
        sum_score = 0.5
    pair_score = sum(pair_score_map.get(n, 0) for n in bet) / (max_pair_score * len(bet)) if max_pair_score > 0 else 0
    score = (0.30 * freq_score + 0.20 * delay_score + 0.20 * quad_score + 0.15 * sum_score + 0.15 * pair_score) * 100
    return min(100, max(0, round(score)))

def generate_bets(lottery_name, draws_matrix, n_bets=10, strategy="híbrido", weight_freq=0.4, weight_delay=0.3, weight_pairs=0.3, trevos_matrix=None, meses_series=None, decay=0.95, min_hot=0, exclude_cold=False, hot_set=None, cold_set=None):
    cfg = LOTTERIES[lottery_name]
    total = cfg["dezenas_total"]
    pick = cfg["dezenas_aposta"]
    freq = compute_frequency(draws_matrix, total)
    freq_weighted = compute_weighted_frequency(draws_matrix, total, decay=decay)
    delays = compute_delays(draws_matrix, total)
    mc_pairs, real_pairs = monte_carlo_pairs(draws_matrix, total, iterations=1000)
    patterns = compute_patterns(draws_matrix, total)
    quadrants = compute_quadrants(total, 4)
    cycle = compute_cycle_completion(draws_matrix, total)
    gap_data = compute_gap_analysis(draws_matrix, total)
    markov_data = compute_markov_chain(draws_matrix, total)
    max_freq = max(freq.values()) if max(freq.values()) > 0 else 1
    max_freq_w = max(freq_weighted.values()) if max(freq_weighted.values()) > 0 else 1
    max_delay = max(delays.values()) if max(delays.values()) > 0 else 1
    pair_score_map = {num: 0.0 for num in range(1, total + 1)}
    for (a, b), cnt in real_pairs.items():
        pair_score_map[a] += cnt
        pair_score_map[b] += cnt
    max_pair = max(pair_score_map.values()) if max(pair_score_map.values()) > 0 else 1
    scores = {}
    for num in range(1, total + 1):
        f_score = freq.get(num, 0) / max_freq
        fw_score = freq_weighted.get(num, 0) / max_freq_w
        blended_freq = 0.5 * f_score + 0.5 * fw_score
        d_score = delays.get(num, 0) / max_delay
        scores[num] = weight_freq * blended_freq + weight_delay * d_score
        if num in cycle["missing"] and cycle["completion_pct"] > 70:
            scores[num] *= 1.15
        if gap_data[num]["overdue"]:
            scores[num] *= 1.20
        if markov_data and markov_data["next_probs"].get(num, 0) > 0:
            mk_prob = markov_data["next_probs"][num] / 100.0
            if mk_prob > 0.3:
                scores[num] *= 1.10
    for num in pair_score_map:
        scores[num] += weight_pairs * (pair_score_map[num] / max_pair)
    seed_base = int(time.time() * 1000) % (2**32)
    rng = random.Random(seed_base)
    bets = []
    scores_list = []
    rejection_reasons = []
    existing_bets = set()
    max_attempts = n_bets * 5
    nums_list = list(scores.keys())
    weights_list = [scores[n] + 0.01 for n in nums_list]
    attempts = 0
    while len(bets) < n_bets and attempts < max_attempts:
        attempts += 1
        if strategy == "frequentes":
            top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:pick * 3]
            chosen = rng.sample([x[0] for x in top], pick)
        elif strategy == "atrasadas":
            top = sorted(delays.items(), key=lambda x: x[1], reverse=True)[:pick * 3]
            chosen = rng.sample([x[0] for x in top], pick)
        elif strategy == "aleatória":
            chosen = rng.sample(range(1, total + 1), pick)
        else:
            chosen = set()
            while len(chosen) < pick:
                chosen.add(rng.choices(nums_list, weights=weights_list, k=1)[0])
            chosen = list(chosen)
        chosen = sorted(chosen)
        chosen_tuple = tuple(chosen)
        valid, reason = is_bet_valid(chosen, patterns, lottery_name, quadrants)
        if not valid:
            rejection_reasons.append(reason)
            continue
        if chosen_tuple in existing_bets:
            continue
        if min_hot > 0 and hot_set:
            hot_count = len([n for n in chosen if n in hot_set])
            if hot_count < min_hot:
                rejection_reasons.append(f"Poucos hot numbers ({hot_count}<{min_hot})")
                continue
        if exclude_cold and cold_set:
            cold_in_bet = [n for n in chosen if n in cold_set]
            if cold_in_bet:
                rejection_reasons.append(f"Cold numbers presentes ({len(cold_in_bet)})")
                continue
        score = compute_bet_score(chosen, freq, delays, pair_score_map, patterns, quadrants, total, max_freq, max_delay, max_pair)
        if score < 35:
            rejection_reasons.append(f"Score baixo ({score})")
            continue
        bets.append(chosen)
        scores_list.append(score)
        existing_bets.add(chosen_tuple)
    while len(bets) < n_bets:
        chosen = sorted(rng.sample(range(1, total + 1), pick))
        chosen_tuple = tuple(chosen)
        if chosen_tuple in existing_bets:
            continue
        valid, _ = is_bet_valid(chosen, patterns, lottery_name, quadrants)
        if valid:
            if exclude_cold and cold_set:
                if any(n in cold_set for n in chosen):
                    continue
            score = compute_bet_score(chosen, freq, delays, pair_score_map, patterns, quadrants, total, max_freq, max_delay, max_pair)
            bets.append(chosen)
            scores_list.append(score)
            existing_bets.add(chosen_tuple)
    trevos_bets = []
    if cfg.get("tem_trevos") and trevos_matrix is not None:
        tf = compute_trevos_frequency(trevos_matrix, cfg["trevos_total"])
        td = compute_trevos_delays(trevos_matrix, cfg["trevos_total"])
        max_tf = max(tf.values()) if max(tf.values()) > 0 else 1
        max_td = max(td.values()) if max(td.values()) > 0 else 1
        t_scores = {t: 0.5 * tf.get(t, 0) / max_tf + 0.5 * td.get(t, 0) / max_td for t in range(1, cfg["trevos_total"] + 1)}
        for _ in range(len(bets)):
            t_nums = list(t_scores.keys())
            t_weights = [t_scores[t] + 0.01 for t in t_nums]
            t_chosen = set()
            while len(t_chosen) < cfg["trevos_aposta"]:
                t_chosen.add(rng.choices(t_nums, weights=t_weights, k=1)[0])
            trevos_bets.append(sorted(t_chosen))
    mes_bets = []
    if cfg.get("tem_mes") and meses_series is not None:
        mf = compute_meses_frequency(meses_series, cfg["meses_total"])
        max_mf = max(mf.values()) if max(mf.values()) > 0 else 1
        m_scores = {m: mf.get(m, 0) / max_mf for m in range(1, cfg["meses_total"] + 1)}
        for _ in range(len(bets)):
            m_nums = list(m_scores.keys())
            m_weights = [m_scores[m] + 0.01 for m in m_nums]
            mes_bets.append(rng.choices(m_nums, weights=m_weights, k=1)[0])
    return bets, scores_list, freq, delays, real_pairs, patterns, quadrants, cycle, trevos_bets, mes_bets, rejection_reasons

def find_strong_pairs(real_pairs, top_n=20):
    return real_pairs.most_common(top_n)

def bets_are_unique(new_bets, old_bets):
    if not old_bets:
        return True
    old_set = {tuple(b) for b in old_bets}
    return all(tuple(b) not in old_set for b in new_bets)

def apply_progressive_filters(combinations, filters, freq=None, delays=None, strong_pairs=None, hot_set=None, cold_set=None, quadrants=None, custo_unit=5.0):
    steps = []
    current = list(combinations)
    total_original = len(current)
    steps.append({"filtro": "Combinações iniciais", "restantes": total_original, "reduzidas": 0, "redução_pct": 0.0, "economia": 0.0})
    def apply_filter(combos, f):
        result = []
        for c in combos:
            c_sorted = sorted(c)
            if f.get("soma_min") is not None and sum(c_sorted) < f["soma_min"]: continue
            if f.get("soma_max") is not None and sum(c_sorted) > f["soma_max"]: continue
            imp = sum(1 for x in c_sorted if x % 2 != 0)
            if f.get("min_impares") is not None and imp < f["min_impares"]: continue
            if f.get("max_impares") is not None and imp > f["max_impares"]: continue
            max_consec = cur = 1
            for i in range(1, len(c_sorted)):
                if c_sorted[i] == c_sorted[i-1] + 1: cur += 1; max_consec = max(max_consec, cur)
                else: cur = 1
            if f.get("max_consecutivos") is not None and max_consec > f["max_consecutivos"]: continue
            if quadrants and f.get("max_por_quad") is not None:
                qdist = count_quadrant_distribution(c_sorted, quadrants)
                if any(v > f["max_por_quad"] for v in qdist.values()): continue
            if hot_set and f.get("min_hot") is not None and f["min_hot"] > 0:
                hot_count = len([n for n in c_sorted if n in hot_set])
                if hot_count < f["min_hot"]: continue
            if cold_set and f.get("excluir_cold") and f["excluir_cold"]:
                if any(n in cold_set for n in c_sorted): continue
            if strong_pairs and f.get("min_pares_fortes") is not None and f["min_pares_fortes"] > 0:
                top_pairs_set = set(tuple(sorted(p)) for p, _ in strong_pairs[:20])
                pair_hits = sum(1 for combo in itertools.combinations(c_sorted, 2) if tuple(sorted(combo)) in top_pairs_set)
                if pair_hits < f["min_pares_fortes"]: continue
            result.append(c_sorted)
        return result
    filter_defs = [
        ("soma_ativo", {"soma_min": "soma_min", "soma_max": "soma_max"}, lambda v: f"Soma entre {v.get('soma_min')} e {v.get('soma_max')}"),
        ("impares_ativo", {"min_impares": "min_impares", "max_impares": "max_impares"}, lambda v: f"Ímpares: {v.get('min_impares')}–{v.get('max_impares')}"),
        ("consec_ativo", {"max_consecutivos": "max_consecutivos"}, lambda v: f"Máx. {v.get('max_consecutivos')} consecutivos"),
        ("quad_ativo", {"max_por_quad": "max_por_quad"}, lambda v: f"Máx. {v.get('max_por_quad')} por quadrante"),
        ("hot_ativo", {"min_hot": "min_hot"}, lambda v: f"Mín. {v.get('min_hot')} hot numbers"),
        ("cold_ativo", {"excluir_cold": True}, lambda v: "Excluir cold numbers"),
        ("pares_ativo", {"min_pares_fortes": "min_pares_fortes"}, lambda v: f"Mín. {v.get('min_pares_fortes')} pares fortes"),
    ]
    for key, params, label_fn in filter_defs:
        if filters.get(key) or (key == "cold_ativo" and filters.get("cold_ativo")):
            f_params = {k: filters.get(k2) if k != "excluir_cold" else True for k, k2 in params.items()}
            if key == "quad_ativo" and not quadrants: continue
            if key == "hot_ativo" and not hot_set: continue
            if key == "cold_ativo" and not cold_set: continue
            if key == "pares_ativo" and not strong_pairs: continue
            prev = len(current)
            current = apply_filter(current, f_params)
            reduzidas = prev - len(current)
            steps.append({"filtro": label_fn(filters), "restantes": len(current), "reduzidas": reduzidas, "redução_pct": (1 - len(current) / total_original) * 100 if total_original > 0 else 0, "economia": reduzidas * custo_unit})
    return current, steps

def calculate_coverage_table(n_numbers, pick, premios):
    coverage = []
    for j in range(pick, n_numbers + 1):
        row = {"acertadas": j}
        total_bets = 0
        for t in range(pick, max(0, j - (n_numbers - pick)) - 1, -1):
            if t > j or t > pick:
                continue
            count = comb(j, t) * comb(n_numbers - j, pick - t)
            label = premios.get(t, f"{t} acertos")
            row[f"{t}_count"] = count
            row[f"{t}_label"] = label
            total_bets += count
        row["total_bets"] = total_bets
        coverage.append(row)
    return coverage

def calculate_desdobramento_cost(n_numbers, pick, custo_unit):
    total_bets = comb(n_numbers, pick)
    return total_bets, total_bets * custo_unit

def generate_full_desdobramento(numbers, pick):
    return [sorted(combo) for combo in itertools.combinations(sorted(numbers), pick)]

def plot_coverage_chart(coverage_data, pick, premios, theme):
    acertadas = [r["acertadas"] for r in coverage_data]
    fig = go.Figure()
    prize_levels = sorted([t for t in premios.keys()], reverse=True)
    colors = ["#FFD700", "#28a745", "#17a2b8", "#6c757d"]
    for idx, t in enumerate(prize_levels):
        vals = [r.get(f"{t}_count", 0) for r in coverage_data]
        if any(v > 0 for v in vals):
            fig.add_trace(go.Bar(x=acertadas, y=vals, name=premios[t], marker_color=colors[idx % len(colors)], text=vals, textposition="auto"))
    fig.update_layout(title="Garantia de Prêmios por Número de Acertos", xaxis_title="Se X de suas dezenas forem sorteadas", yaxis_title="Quantidade de apostas premiadas", template="plotly_white", height=400, barmode="group", paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def plot_cost_vs_numbers(cfg, theme):
    pick = cfg["dezenas_aposta"]
    custo_unit = cfg.get("custo_aposta", 5.0)
    max_nums = cfg.get("max_dezenas_aposta", min(cfg["dezenas_total"], pick + 10))
    nums = list(range(pick, max_nums + 1))
    costs = [comb(n, pick) * custo_unit for n in nums]
    bets = [comb(n, pick) for n in nums]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[f"{n} dezenas" for n in nums], y=costs, marker_color=theme["accent"], text=[f"R$ {c:,.2f}\n({b} apostas)" for c, b in zip(costs, bets)], textposition="auto"))
    fig.update_layout(title=f"Custo Total do Desdobramento — {pick}+ dezenas (R$ {custo_unit:.2f}/aposta)", xaxis_title="Número de dezenas jogadas", yaxis_title="Custo total (R$)", template="plotly_white", height=400, paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def run_backtest(bets, draws_matrix, lottery_name):
    cfg = LOTTERIES[lottery_name]
    premios = cfg["premios"]
    custo_unit = cfg.get("custo_aposta", 5.0)
    premios_est = PREMIOS_ESTIMADOS.get(lottery_name, {})
    n_concursos = len(draws_matrix)
    n_bets = len(bets)
    custo_total = n_bets * custo_unit * n_concursos
    results = {label: 0 for label in set(premios.values())}
    results["Nenhum"] = 0
    premios_total = 0.0
    detail_rows = []
    bet_sets = [set(b) for b in bets]
    for draw_idx, row in enumerate(draws_matrix):
        draw_set = set(int(x) for x in row)
        for bet_idx, bset in enumerate(bet_sets):
            hits = len(bset & draw_set)
            label = premios.get(hits, None)
            if label:
                results[label] = results.get(label, 0) + 1
                valor_est = premios_est.get(label, 0)
                premios_total += valor_est
                detail_rows.append({"Concurso": draw_idx + 1, "Aposta #": bet_idx + 1, "Acertos": hits, "Prêmio": label, "Valor Est. (R$)": valor_est})
            elif hits >= 3:
                results["Nenhum"] += 1
    roi = ((premios_total - custo_total) / custo_total * 100) if custo_total > 0 else 0
    roi_data = {"custo_total": custo_total, "premios_total": premios_total, "roi_pct": roi, "lucro_liquido": premios_total - custo_total, "n_bets": n_bets, "n_concursos": n_concursos}
    return results, pd.DataFrame(detail_rows), roi_data

def compare_strategies(lottery_name, draws_matrix, n_bets=10, weight_freq=0.4, weight_delay=0.3, weight_pairs=0.3, trevos_matrix=None, meses_series=None, decay=0.95):
    strategies = ["híbrido", "frequentes", "atrasadas", "aleatória"]
    comparison = []
    for strat in strategies:
        bets, scores_list, freq, delays, real_pairs, patterns, quadrants, cycle, trevos_bets, mes_bets, rej = generate_bets(lottery_name, draws_matrix, n_bets=n_bets, strategy=strat, weight_freq=weight_freq, weight_delay=weight_delay, weight_pairs=weight_pairs, trevos_matrix=trevos_matrix, meses_series=meses_series, decay=decay, min_hot=0, exclude_cold=False, hot_set=None, cold_set=None)
        results, df_detail, roi_data = run_backtest(bets, draws_matrix, lottery_name)
        total_premios = sum(v for k, v in results.items() if k != "Nenhum")
        comparison.append({"Estratégia": strat.capitalize(), "Apostas": len(bets), "Prêmios Ganhos": total_premios, "Custo Total (R$)": roi_data["custo_total"], "Prêmios Total (R$)": roi_data["premios_total"], "ROI %": roi_data["roi_pct"], "Lucro/Prejuízo (R$)": roi_data["lucro_liquido"]})
    return pd.DataFrame(comparison)

def conferir_apostas(bets, resultado_sort, lottery_name, trevos_bets=None, mes_bets=None, trevos_sort=None, mes_sort=None):
    cfg = LOTTERIES[lottery_name]
    premios = cfg["premios"]
    sort_set = set(resultado_sort)
    resultados = []
    for i, bet in enumerate(bets):
        bet_set = set(bet)
        hits = len(bet_set & sort_set)
        numeros_acertados = sorted(bet_set & sort_set)
        label = premios.get(hits, "")
        trevo_hits = 0
        if trevos_bets and trevos_sort:
            trevo_set = set(trevos_sort)
            bet_trevo_set = set(trevos_bets[i])
            trevo_hits = len(bet_trevo_set & trevo_set)
        mes_acertou = False
        if mes_bets and mes_sort:
            mes_acertou = (mes_bets[i] == mes_sort)
        resultados.append({"Aposta #": i + 1, "Dezenas": " - ".join(f"{n:02d}" for n in bet), "Acertos": hits, "Números Acertados": " - ".join(f"{n:02d}" for n in numeros_acertados) if numeros_acertados else "-", "Prêmio": label if label else "-", "Trevo Hits": trevo_hits if trevos_bets else "-", "Mês?": "✅" if mes_acertou else ("❌" if mes_bets else "-")})
    return pd.DataFrame(resultados)

def export_to_excel(bets, freq, delays, strong_pairs, lottery_name, trevos_bets=None, mes_bets=None, scores_list=None):
    cfg = LOTTERIES[lottery_name]
    total = cfg["dezenas_total"]
    df_bets = pd.DataFrame(bets, columns=[f"d{i+1}" for i in range(len(bets[0]))])
    df_bets.insert(0, "Aposta", range(1, len(bets) + 1))
    if scores_list:
        df_bets.insert(1, "Score", scores_list)
    if trevos_bets:
        for j in range(cfg["trevos_aposta"]):
            df_bets[f"Trevo {j+1}"] = [t[j] for t in trevos_bets]
    if mes_bets:
        df_bets["Mês"] = [cfg["meses_lista"][m - 1] for m in mes_bets]
    df_freq = pd.DataFrame([{"Dezena": n, "Frequência": freq.get(n, 0)} for n in range(1, total + 1)]).sort_values("Frequência", ascending=False)
    df_delays = pd.DataFrame([{"Dezena": n, "Atraso": delays.get(n, 0)} for n in range(1, total + 1)]).sort_values("Atraso", ascending=False)
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
        for sheet_name in writer.sheets:
            writer.sheets[sheet_name].set_column(0, 10, 18)
    output.seek(0)
    return output

def plot_frequency_bar(freq, total, theme):
    nums = list(range(1, total + 1))
    vals = [freq.get(n, 0) for n in nums]
    fig = go.Figure(data=[go.Bar(x=nums, y=vals, marker_color=theme["accent"])])
    fig.update_layout(title="Frequência de Dezenas", xaxis_title="Dezena", yaxis_title="Frequência", template="plotly_white", height=400, paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def plot_hot_cold(hot_cold_data, total, theme):
    nums = list(range(1, total + 1))
    vals = [hot_cold_data["freq_recent"].get(n, 0) for n in nums]
    colors = ["#FF4444" if n in hot_cold_data["hot_set"] else "#4488FF" if n in hot_cold_data["cold_set"] else "#CCCCCC" for n in nums]
    fig = go.Figure(data=[go.Bar(x=nums, y=vals, marker_color=colors, text=vals, textposition="auto")])
    fig.update_layout(title=f"Hot / Cold Numbers (últimos {hot_cold_data['recent_n']} sorteios)", xaxis_title="Dezena", yaxis_title="Frequência", template="plotly_white", height=400, paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def plot_weighted_vs_simple(freq_simple, freq_weighted, total, theme):
    nums = list(range(1, total + 1))
    vals_s = [freq_simple.get(n, 0) for n in nums]
    vals_w = [freq_weighted.get(n, 0) for n in nums]
    max_s = max(vals_s) if max(vals_s) > 0 else 1
    max_w = max(vals_w) if max(vals_w) > 0 else 1
    fig = go.Figure()
    fig.add_trace(go.Bar(x=nums, y=[v / max_s for v in vals_s], marker_color="#CCCCCC", name="Frequência Simples", opacity=0.6))
    fig.add_trace(go.Bar(x=nums, y=[v / max_w for v in vals_w], marker_color=theme["accent"], name="Frequência Ponderada", opacity=0.8))
    fig.update_layout(title="Frequência Simples vs Ponderada (normalizada)", xaxis_title="Dezena", yaxis_title="Frequência Normalizada", template="plotly_white", height=400, barmode="group", paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def plot_gap_analysis(gap_data, total, theme):
    nums = list(range(1, total + 1))
    current_gaps = [gap_data[n]["current_gap"] for n in nums]
    mean_gaps = [gap_data[n]["mean_gap"] for n in nums]
    colors = ["#FF4444" if gap_data[n]["overdue"] else "#FFA500" if gap_data[n]["z_score"] > 1 else theme["accent"] for n in nums]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=nums, y=current_gaps, marker_color=colors, name="Gap Atual", text=[f"{g}" for g in current_gaps], textposition="auto"))
    fig.add_trace(go.Scatter(x=nums, y=mean_gaps, mode="lines+markers", line=dict(color="#FF0000", dash="dash", width=2), marker=dict(size=5), name="Média Histórica"))
    fig.update_layout(title="Gap Analysis: Intervalo Atual vs Média Histórica", xaxis_title="Dezena", yaxis_title="Concursos sem aparecer", template="plotly_white", height=450, paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]), showlegend=True)
    return fig

def plot_gap_timeline(gap_data, num, n_draws, theme):
    appearances = gap_data[num]["appearances"]
    fig = go.Figure()
    x_vals = list(range(n_draws))
    y_vals = [1 if i in set(appearances) else 0 for i in range(n_draws)]
    colors = ["#FF4444" if v == 1 else "#EEEEEE" for v in y_vals]
    fig.add_trace(go.Bar(x=x_vals, y=y_vals, marker_color=colors, name=f"Dezena {num}"))
    fig.update_layout(title=f"Timeline de Aparições — Dezena {num}", xaxis_title="Concurso (índice)", yaxis_title="Apareceu?", template="plotly_white", height=250, paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]), showlegend=False)
    return fig

def plot_prob_ranking(gap_data, total, theme):
    nums = list(range(1, total + 1))
    probs = [gap_data[n]["prob_next"] for n in nums]
    sorted_idx = sorted(range(len(probs)), key=lambda i: probs[i], reverse=True)
    sorted_nums = [nums[i] for i in sorted_idx]
    sorted_probs = [probs[i] for i in sorted_idx]
    colors = ["#FF4444" if gap_data[n]["overdue"] else theme["accent"] for n in sorted_nums]
    fig = go.Figure(data=[go.Bar(x=[str(n) for n in sorted_nums], y=sorted_probs, marker_color=colors, text=[f"{p}%" for p in sorted_probs], textposition="auto")])
    fig.update_layout(title="Ranking de Probabilidade para o Próximo Sorteio", xaxis_title="Dezena (rank)", yaxis_title="Probabilidade Estimada (%)", template="plotly_white", height=400, paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def plot_markov_heatmap(markov_data, total, theme):
    matrix = markov_data["transition_matrix"][1:total+1, 1:total+1]
    fig = go.Figure(data=go.Heatmap(z=matrix, x=list(range(1, total + 1)), y=list(range(1, total + 1)), colorscale="Blues", colorbar=dict(title="P(Y|X)")))
    fig.update_layout(title="Heatmap da Matriz de Transição de Markov P[Y aparecer | X apareceu antes]", xaxis_title="Dezena Y (próximo sorteio)", yaxis_title="Dezena X (sorteio anterior)", template="plotly_white", height=500, paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def plot_markov_ranking(markov_data, total, theme):
    probs = markov_data["next_probs"]
    sorted_items = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    nums = [str(n) for n, _ in sorted_items[:30]]
    vals = [v for _, v in sorted_items[:30]]
    fig = go.Figure(data=[go.Bar(x=nums, y=vals, marker_color=theme["accent"], text=[f"{v}%" for v in vals], textposition="auto")])
    fig.update_layout(title="Top 30 Dezenas por Probabilidade de Markov", xaxis_title="Dezena", yaxis_title="Probabilidade (%)", template="plotly_white", height=400, paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def plot_delays_bar(delays, total, theme, title_suffix=""):
    nums = list(range(1, total + 1))
    vals = [delays.get(n, 0) for n in nums]
    fig = go.Figure(data=[go.Bar(x=nums, y=vals, marker_color=theme["accent"], opacity=0.8)])
    fig.update_layout(title=f"Atraso de Dezenas{title_suffix}", xaxis_title="Dezena", yaxis_title="Atraso", template="plotly_white", height=400, paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def plot_trevos_frequency(freq, total, theme):
    nums = list(range(1, total + 1))
    vals = [freq.get(n, 0) for n in nums]
    fig = go.Figure(data=[go.Bar(x=nums, y=vals, marker_color="#FF8C00")])
    fig.update_layout(title="Frequência de Trevos", xaxis_title="Trevo", yaxis_title="Frequência", template="plotly_white", height=350, paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def plot_meses_frequency(freq, meses_lista, theme):
    vals = [freq.get(i + 1, 0) for i in range(len(meses_lista))]
    fig = go.Figure(data=[go.Bar(x=meses_lista, y=vals, marker_color="#FF69B4")])
    fig.update_layout(title="Frequência de Meses Sorteados", xaxis_title="Mês", yaxis_title="Frequência", template="plotly_white", height=350, paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def plot_patterns(patterns, theme):
    fig = make_subplots(rows=2, cols=2, subplot_titles=("Proporção Ímpar/Par", "Números Primos", "Distribuição da Soma", "Resumo Médias"), specs=[[{"type":"histogram"},{"type":"histogram"}],[{"type":"histogram"},{"type":"indicator"}]])
    fig.add_trace(go.Histogram(x=patterns["impar_ratios"], nbinsx=20, marker_color=theme["accent"], name="Ímpar/Par"), row=1, col=1)
    fig.add_trace(go.Histogram(x=patterns["prime_counts"], nbinsx=20, marker_color="#FF6B6B", name="Primos"), row=1, col=2)
    fig.add_trace(go.Histogram(x=patterns["sums"], nbinsx=30, marker_color="#4ECDC4", name="Soma"), row=2, col=1)
    fig.add_trace(go.Indicator(mode="number", value=patterns["impar_ratio_mean"], title={"text":"Média Ímpar/Par"}, number={"valueformat":".2%"}), row=2, col=2)
    fig.update_layout(height=600, showlegend=False, template="plotly_white", paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]), title_text="Padrões Comportamentais")
    return fig

def plot_sum_distribution(patterns, theme):
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=patterns["sums"], nbinsx=35, marker_color=theme["accent"], opacity=0.7, name="Soma"))
    mean = patterns["sum_mean"]
    std = patterns["sum_std"]
    fig.add_vline(x=mean, line_dash="dash", line_color="red", annotation_text=f"Média: {mean:.1f}")
    fig.add_vline(x=mean + std, line_dash="dot", line_color="orange", annotation_text="+1σ")
    fig.add_vline(x=mean - std, line_dash="dot", line_color="orange", annotation_text="-1σ")
    fig.update_layout(title="Histograma da Soma das Dezenas", xaxis_title="Soma", yaxis_title="Frequência", template="plotly_white", height=420, paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def plot_prime_impar_summary(patterns, theme):
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Média Ímpar/Par", "Média Primos"), specs=[[{"type":"pie"},{"type":"indicator"}]])
    imp = patterns["impar_ratio_mean"]
    fig.add_trace(go.Pie(labels=["Ímpares","Pares"], values=[imp, 1-imp], marker_colors=[theme["accent"],"#FF6B6B"], hole=0.4), row=1, col=1)
    fig.add_trace(go.Indicator(mode="number", value=patterns["prime_mean"], title={"text":"Primos/sorteio"}, number={"valueformat":".2f"}), row=1, col=2)
    fig.update_layout(height=380, template="plotly_white", paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def plot_backtest_results(results, theme):
    pairs = [(k, v) for k, v in results.items() if v > 0 or k != "Nenhum"]
    pairs.sort(key=lambda x: x[1])
    labels = [p[0] for p in pairs]
    values = [p[1] for p in pairs]
    fig = go.Figure(data=[go.Bar(x=labels, y=values, marker_color=theme["accent"], text=values, textposition="auto")])
    fig.update_layout(title="Resultado do Backtesting", xaxis_title="Categoria de Prêmio", yaxis_title="Ocorrências", template="plotly_white", height=400, paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def plot_scores_bar(scores_list, theme):
    fig = go.Figure(data=[go.Bar(x=list(range(1, len(scores_list)+1)), y=scores_list, marker_color=theme["accent"], text=scores_list, textposition="auto")])
    fig.update_layout(title="Score de Confiança por Aposta", xaxis_title="Aposta #", yaxis_title="Score (0-100)", template="plotly_white", height=350, paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def plot_cycle_completion(cycle, total, theme):
    seen = len(cycle["seen"])
    missing = len(cycle["missing"])
    fig = go.Figure(data=[go.Pie(labels=["Vistas no ciclo", "Faltando"], values=[seen, missing], marker_colors=[theme["accent"], "#FF6B6B"], hole=0.4)])
    fig.update_layout(title=f"Ciclo de Completude: {cycle['completion_pct']}%", height=350, template="plotly_white", paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def plot_reduction_steps(steps, theme):
    labels = [s["filtro"] for s in steps]
    restantes = [s["restantes"] for s in steps]
    reduzidas = [s["reduzidas"] for s in steps]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=restantes, marker_color=theme["accent"], name="Restantes", text=restantes, textposition="auto"))
    fig.add_trace(go.Bar(x=labels, y=reduzidas, marker_color="#FF6B6B", name="Reduzidas", text=reduzidas, textposition="auto"))
    fig.update_layout(title="Redução Progressiva de Combinações", xaxis_title="Filtro aplicado", yaxis_title="Quantidade", template="plotly_white", height=400, barmode="stack", paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]), showlegend=True)
    return fig

def main():
    st.set_page_config(page_title="Motor Analítico de Loterias", page_icon="🎲", layout="wide")
    apply_theme_css()
    theme = get_theme()
    if "gen_counter" not in st.session_state:
        st.session_state["gen_counter"] = 0

    with st.sidebar:
        st.header("⚙️ Configurações")
        st.session_state["theme"] = st.radio("Tema", ["Branco","Azul"], index=0 if st.session_state.get("theme","Branco")=="Branco" else 1, key="theme_radio")
        theme = get_theme()
        apply_theme_css()
        st.divider()
        lottery_name = st.selectbox("🎯 Loteria", list(LOTTERIES.keys()), index=0, key="lottery_select")
        cfg = LOTTERIES[lottery_name]
        st.divider()
        st.subheader("📁 Fonte de Dados")
        st.markdown("**🌐 API da Caixa**")
        n_concursos_api = st.slider("Concursos da Caixa?", 10, 100, 30, key="n_concursos_slider_api")
        if st.button("🔄 Buscar dados da Caixa", key="fetch_caixa_button", type="secondary"):
            with st.spinner(f"Buscando {n_concursos_api} concursos..."):
                df_caixa = fetch_caixa_history(lottery_name, n_concursos_api)
                if df_caixa is not None and len(df_caixa) > 0:
                    st.session_state["df_caixa"] = df_caixa
                    st.session_state["data_source"] = "caixa"
                    st.sidebar.success(f"✅ {len(df_caixa)} concursos carregados!")
                else:
                    st.sidebar.error("❌ Erro ao buscar dados. Usando fallback.")
        st.divider()
        st.markdown("**📁 Ou suba um arquivo**")
        uploaded_file = st.file_uploader("CSV ou Excel", type=["csv","xlsx","xls"], key="file_uploader")
        use_mock = st.checkbox("Usar dados mockados", value=True, key="use_mock_checkbox")
        st.divider()
        st.subheader("🎲 Gerador de Apostas")
        n_bets = st.slider("Número de apostas", 1, 50, 10, key="n_bets_slider")
        strategy = st.selectbox("Estratégia", ["híbrido","frequentes","atrasadas","aleatória"], index=0, key="strategy_select")
        w_freq = st.slider("Peso Frequência", 0.0, 1.0, 0.4, 0.05, key="weight_freq_slider")
        w_delay = st.slider("Peso Atraso", 0.0, 1.0, 0.3, 0.05, key="weight_delay_slider")
        w_pairs = st.slider("Peso Pares Fortes", 0.0, 1.0, 0.3, 0.05, key="weight_pairs_slider")
        st.divider()
        st.subheader("🔥 Hot / Cold Numbers")
        min_hot = st.slider("Mín. Hot Numbers", 0, cfg["dezenas_aposta"], 0, key="min_hot_slider")
        exclude_cold = st.checkbox("Excluir Cold Numbers", value=False, key="exclude_cold_checkbox")
        st.divider()
        st.subheader("⚖️ Janela Deslizante")
        decay_factor = st.slider("Fator de decaimento", 0.80, 0.99, 0.95, 0.01, key="decay_slider")

    df_data = None
    if "df_caixa" in st.session_state and st.session_state["df_caixa"] is not None and st.session_state.get("data_source") == "caixa":
        df_data = st.session_state["df_caixa"]
        st.sidebar.info(f"🌐 API Caixa: {len(df_data)} concursos")
    elif uploaded_file is not None:
        processed = process_uploaded_file(uploaded_file, lottery_name)
        if processed is not None:
            df_data = processed
            st.sidebar.success(f"✅ Arquivo: {len(df_data)} sorteios")
    if df_data is None and use_mock:
        df_data = generate_mock_data(lottery_name, n_draws=300)
        st.sidebar.info(f"📊 Dados mockados: {len(df_data)} sorteios")
    if df_data is None:
        st.warning("Suba um arquivo, busque da Caixa, ou ative os dados mockados.")
        return

    st.session_state["df_data"] = df_data
    draws_matrix = get_dezenas_matrix(df_data, lottery_name)
    n_draws = len(draws_matrix)
    trevos_matrix = get_trevos_matrix(df_data, lottery_name) if cfg.get("tem_trevos") else None
    meses_series = get_meses_series(df_data, lottery_name) if cfg.get("tem_mes") else None
    hot_cold_data = compute_hot_cold(draws_matrix, cfg["dezenas_total"])
    freq_weighted = compute_weighted_frequency(draws_matrix, cfg["dezenas_total"], decay=decay_factor)
    gap_data = compute_gap_analysis(draws_matrix, cfg["dezenas_total"])
    cycle = compute_cycle_completion(draws_matrix, cfg["dezenas_total"])
    alerts = compute_alerts(cfg["dezenas_total"], gap_data, cycle)
    markov_data = compute_markov_chain(draws_matrix, cfg["dezenas_total"])
    freq = compute_frequency(draws_matrix, cfg["dezenas_total"])
    delays = compute_delays(draws_matrix, cfg["dezenas_total"])
    st.sidebar.caption(f"🔴 Hot = top 25% nos últimos {hot_cold_data['recent_n']} concursos")
    st.sidebar.caption(f"🔵 Cold = bottom 25%")

    st.markdown(f"""<div class="main-header"><div class="main-title">🎲 Motor Analítico & Gerador de Apostas</div><div class="main-subtitle">API Caixa · Score · Ciclo · Hot/Cold · Gap Analysis · Janela Deslizante · Alertas · ROI · Line Reduction · Markov · Desdobramento</div></div>""", unsafe_allow_html=True)

    if alerts:
        alert_colors = {"alta": "#dc3545", "media": "#ffc107"}
        for a in alerts:
            color = alert_colors.get(a["severidade"], "#6c757d")
            st.markdown(f"""<div style='background:{theme['card']};border-left:4px solid {color};border-radius:8px;padding:12px 16px;margin:6px 0;display:flex;align-items:center;'><span style='font-size:1.2rem;margin-right:10px;'>{a['icone']}</span><div><div style='font-weight:700;color:{color};font-size:0.9rem;'>{a['titulo']}</div><div style='font-size:0.8rem;opacity:0.7;'>{a['detalhe']}</div></div></div>""", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Sorteios", n_draws, "Analisados")
    with col2:
        metric_card("Dezenas/Aposta", cfg["dezenas_aposta"], lottery_name)
    with col3:
        extra = f" + {cfg['trevos_aposta']} trevos" if cfg.get("tem_trevos") else (" + 1 mês" if cfg.get("tem_mes") else "")
        metric_card("Universo", f"{cfg['dezenas_total']}{extra}", "")
    with col4:
        top_num = max(freq, key=freq.get)
        metric_card("Top Dezena", f"{top_num}", f"{freq[top_num]}x")

    st.divider()

    tab_gerador, tab_conferidor, tab_fechamento, tab_multipla, tab_padroes, tab_backtest, tab_dados = st.tabs([
        "🎰 Gerador", "✅ Conferidor", "🔢 Line Reduction", "🎲 Apostas Múltiplas", "📊 Padrões", "🔬 Backtesting", "📋 Dados"
    ])

    with tab_gerador:
        st.header("🎰 Gerador de Apostas Otimizado")
        if st.session_state["gen_counter"] > 0:
            st.caption(f"🔄 Geração #{st.session_state['gen_counter']}")
        if st.button("⚡ Gerar Apostas", type="primary", key="gerar_apostas_button"):
            with st.spinner("Gerando apostas..."):
                for attempt in range(3):
                    bets, scores_list, freq_g, delays_g, real_pairs, patterns, quadrants, cycle_g, trevos_bets, mes_bets, rejection_reasons = generate_bets(
                        lottery_name, draws_matrix, n_bets=n_bets, strategy=strategy, weight_freq=w_freq, weight_delay=w_delay, weight_pairs=w_pairs,
                        trevos_matrix=trevos_matrix, meses_series=meses_series, decay=decay_factor, min_hot=min_hot, exclude_cold=exclude_cold,
                        hot_set=hot_cold_data["hot_set"], cold_set=hot_cold_data["cold_set"])
                    old_bets = st.session_state.get("bets", [])
                    if bets_are_unique(bets, old_bets) or attempt == 2:
                        break
                    time.sleep(0.01)
                strong_pairs = find_strong_pairs(real_pairs, top_n=20)
                st.session_state["bets"] = bets
                st.session_state["scores_list"] = scores_list
                st.session_state["freq"] = freq_g
                st.session_state["delays"] = delays_g
                st.session_state["strong_pairs"] = strong_pairs
                st.session_state["trevos_bets"] = trevos_bets
                st.session_state["mes_bets"] = mes_bets
                st.session_state["patterns"] = patterns
                st.session_state["quadrants"] = quadrants
                st.session_state["cycle"] = cycle_g
                st.session_state["rejection_reasons"] = rejection_reasons
                st.session_state["gen_counter"] += 1

        if "bets" in st.session_state and st.session_state["bets"]:
            bets = st.session_state["bets"]
            scores_list = st.session_state.get("scores_list", [])
            freq_disp = st.session_state.get("freq", freq)
            delays_disp = st.session_state.get("delays", delays)
            strong_pairs = st.session_state.get("strong_pairs", [])
            trevos_bets = st.session_state.get("trevos_bets", [])
            mes_bets = st.session_state.get("mes_bets", [])
            cycle_disp = st.session_state.get("cycle", cycle)
            st.subheader(f"{len(bets)} Apostas Geradas")
            df_bets = pd.DataFrame(bets, columns=[f"d{i+1}" for i in range(len(bets[0]))])
            df_bets.insert(0, "#", range(1, len(bets) + 1))
            if scores_list:
                df_bets.insert(1, "Score", scores_list)
            if trevos_bets:
                for j in range(cfg["trevos_aposta"]):
                    df_bets[f"t{j+1}"] = [t[j] for t in trevos_bets]
            if mes_bets:
                df_bets["Mês"] = [cfg["meses_lista"][m - 1] for m in mes_bets]
            st.dataframe(df_bets, use_container_width=True, hide_index=True)
            if scores_list:
                st.plotly_chart(plot_scores_bar(scores_list, theme), use_container_width=True)
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.plotly_chart(plot_frequency_bar(freq_disp, cfg["dezenas_total"], theme), use_container_width=True)
            with col_g2:
                st.plotly_chart(plot_delays_bar(delays_disp, cfg["dezenas_total"], theme), use_container_width=True)
            st.subheader("🔗 Pares Fortes")
            df_pairs = pd.DataFrame(strong_pairs, columns=["Par","Ocorrências"])
            df_pairs["Dezena_A"] = df_pairs["Par"].apply(lambda x: x[0])
            df_pairs["Dezena_B"] = df_pairs["Par"].apply(lambda x: x[1])
            st.dataframe(df_pairs[["Dezena_A","Dezena_B","Ocorrências"]].head(15), use_container_width=True, hide_index=True)
            st.subheader("📥 Exportação")
            excel_data = export_to_excel(bets, freq_disp, delays_disp, strong_pairs, lottery_name, trevos_bets, mes_bets, scores_list)
            st.download_button(label="📊 Baixar Excel", data=excel_data, file_name=f"apostas_{lottery_name.replace(' ','_').replace('+','mais')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="download_excel_apostas")

    with tab_conferidor:
        st.header("✅ Conferidor de Resultados")
        col_conf1, col_conf2 = st.columns([2, 1])
        with col_conf2:
            if st.button("🔄 Buscar último sorteio", key="fetch_ultimo_button", type="secondary"):
                with st.spinner("Buscando..."):
                    latest_data = fetch_caixa_latest(lottery_name)
                    if latest_data:
                        parsed = parse_caixa_json(latest_data, lottery_name)
                        if parsed:
                            st.session_state["ultimo_sorteio"] = parsed
                            st.success("✅ Sorteio carregado!")
        if "ultimo_sorteio" in st.session_state:
            sorteio = st.session_state["ultimo_sorteio"]
            with col_conf1:
                st.markdown(f"### 🏆 Concurso {sorteio.get('concurso','?')} — {sorteio.get('data','?')}")
                dezenas_sort = [sorteio.get(f"d{i+1}") for i in range(cfg["dezenas_aposta"]) if sorteio.get(f"d{i+1}") is not None]
                if dezenas_sort:
                    dezenas_html = " ".join([f"<span style='display:inline-block;width:36px;height:36px;line-height:36px;text-align:center;border-radius:50%;background:#28a745;color:white;font-weight:bold;margin:3px;font-size:1rem;'>{n:02d}</span>" for n in dezenas_sort])
                    st.markdown(f"<div style='padding:12px;background:{theme['card']};border-radius:12px;margin:8px 0;'>{dezenas_html}</div>", unsafe_allow_html=True)
            if "bets" in st.session_state and st.session_state["bets"] and dezenas_sort:
                bets = st.session_state["bets"]
                df_conf = conferir_apostas(bets, dezenas_sort, lottery_name)
                st.divider()
                st.subheader("🎯 Conferência")
                st.dataframe(df_conf, use_container_width=True, hide_index=True)
                tem_premio = df_conf[df_conf["Prêmio"] != "-"]
                if not tem_premio.empty:
                    st.success(f"🎉 {len(tem_premio)} aposta(s) premiada(s)!")

    with tab_fechamento:
        st.header("🔢 Line Reduction")
        dezenas_input = st.text_area("Digite as dezenas separadas por vírgula", value="", height=80, key="dezenas_textarea_lr")
        pick = cfg["dezenas_aposta"]
        custo_unit = cfg.get("custo_aposta", 5.0)
        try:
            dezenas_list = sorted(set(int(x.strip()) for x in dezenas_input.split(",") if x.strip()))
        except ValueError:
            dezenas_list = []
        if len(dezenas_list) >= pick:
            all_combos = list(itertools.combinations(dezenas_list, pick))
            total_orig = len(all_combos)
            st.markdown(f"### 📊 {total_orig:,} combinações com {len(dezenas_list)} dezenas")
            st.divider()
            filters = {}
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filters["soma_ativo"] = st.checkbox("Soma", value=False, key="lr_soma_check")
                if filters["soma_ativo"]:
                    filters["soma_min"] = st.number_input("Mínima", value=int(np.mean(dezenas_list)*pick*0.7), key="lr_soma_min")
                    filters["soma_max"] = st.number_input("Máxima", value=int(np.mean(dezenas_list)*pick*1.3), key="lr_soma_max")
                filters["impares_ativo"] = st.checkbox("Ímpar/Par", value=False, key="lr_impares_check")
                if filters["impares_ativo"]:
                    filters["min_impares"] = st.number_input("Mín. ímpares", 0, pick, pick//2, key="lr_min_imp")
                    filters["max_impares"] = st.number_input("Máx. ímpares", 0, pick, pick-1, key="lr_max_imp")
                filters["consec_ativo"] = st.checkbox("Consecutivos", value=False, key="lr_consec_check")
                if filters["consec_ativo"]:
                    filters["max_consecutivos"] = st.slider("Máx.", 1, pick, 2, key="lr_max_consec")
            with col_f2:
                filters["hot_ativo"] = st.checkbox("Mín. Hot", value=False, key="lr_hot_check")
                if filters["hot_ativo"]:
                    filters["min_hot"] = st.slider("Mín. hot", 0, pick, 2, key="lr_min_hot")
                filters["cold_ativo"] = st.checkbox("Excluir Cold", value=False, key="lr_cold_check")
                filters["pares_ativo"] = st.checkbox("Pares Fortes", value=False, key="lr_pares_check")
                if filters["pares_ativo"]:
                    filters["min_pares_fortes"] = st.slider("Mín. pares", 0, 10, 2, key="lr_min_pares")
            quadrants_lr = compute_quadrants(cfg["dezenas_total"], 4)
            strong_pairs_lr = st.session_state.get("strong_pairs", [])
            filtered_combos, steps = apply_progressive_filters(all_combos, filters, freq=st.session_state.get("freq", freq), delays=st.session_state.get("delays", delays), strong_pairs=strong_pairs_lr, hot_set=hot_cold_data["hot_set"], cold_set=hot_cold_data["cold_set"], quadrants=quadrants_lr, custo_unit=custo_unit)
            final_count = len(filtered_combos)
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                metric_card("Iniciais", f"{total_orig:,}", "")
            with col_m2:
                metric_card("Finais", f"{final_count:,}", f"{(1-final_count/total_orig)*100:.1f}%" if total_orig > 0 else "")
            with col_m3:
                metric_card("Reduzidas", f"{total_orig-final_count:,}", "")
            with col_m4:
                metric_card("Economia", f"R$ {(total_orig-final_count)*custo_unit:,.2f}", "")
            if len(steps) > 1:
                st.plotly_chart(plot_reduction_steps(steps, theme), use_container_width=True)
            if final_count > 0:
                if final_count <= 500:
                    df_final = pd.DataFrame(filtered_combos, columns=[f"d{i+1}" for i in range(pick)])
                    df_final.insert(0, "#", range(1, len(df_final)+1))
                    st.dataframe(df_final, use_container_width=True, hide_index=True)
                excel_lr = export_to_excel(filtered_combos, st.session_state.get("freq", freq), st.session_state.get("delays", delays), strong_pairs_lr, lottery_name)
                st.download_button(label="📊 Baixar Excel", data=excel_lr, file_name=f"line_reduction_{lottery_name.replace(' ','_').replace('+','mais')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="download_excel_lr")
        else:
            st.info(f"Digite pelo menos {pick} dezenas.")

    with tab_multipla:
        st.header("🎲 Apostas Múltiplas (Desdobramento)")
        pick = cfg["dezenas_aposta"]
        custo_unit = cfg.get("custo_aposta", 5.0)
        max_nums = cfg.get("max_dezenas_aposta", min(cfg["dezenas_total"], pick + 10))
        st.subheader("📊 Tabela de Custos")
        st.plotly_chart(plot_cost_vs_numbers(cfg, theme), use_container_width=True)
        cost_rows = []
        for n in range(pick, max_nums + 1):
            total_bets, total_cost = calculate_desdobramento_cost(n, pick, custo_unit)
            cost_rows.append({"Dezenas": n, "Apostas": f"{total_bets:,}", "Custo": f"R$ {total_cost:,.2f}"})
        st.dataframe(pd.DataFrame(cost_rows), use_container_width=True, hide_index=True)
        st.divider()
        st.subheader("🔧 Montar Desdobramento")
        col_m1, col_m2, col_m3 = st.columns([2, 1, 1])
        with col_m1:
            n_dezenas = st.slider(f"Qtde de dezenas ({pick} a {max_nums})", min_value=pick, max_value=max_nums, value=pick+2, key="n_dezenas_multipla")
        with col_m2:
            st.markdown(f"**R$ {custo_unit:.2f}/aposta**")
        total_bets_possible, _ = calculate_desdobramento_cost(n_dezenas, pick, custo_unit)
        with col_m3:
            max_bets = min(total_bets_possible, 5000)
            n_apostas = st.number_input("Qtde apostas", 1, int(max_bets), min(int(total_bets_possible), 50), key="n_apostas_multipla")
        total_cost = n_apostas * custo_unit
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            metric_card("Dezenas", n_dezenas, f"{cfg['dezenas_total']} possíveis")
        with col_c2:
            metric_card("Apostas", f"{n_apostas:,}", f"{total_bets_possible:,} possíveis")
        with col_c3:
            metric_card("Custo", f"R$ {total_cost:,.2f}", f"R$ {custo_unit:.2f} cada")

        # Gerar dezenas
        col_d1, col_d2 = st.columns([3, 1])
        with col_d1:
            dezenas_input_m = st.text_area(f"Digite {n_dezenas} dezenas ou gere abaixo", height=60, key="dezenas_multipla_input")
        with col_d2:
            gerar_tipo = st.selectbox("Tipo", ["Sugeridas", "Aleatórias", "Hot Numbers", "Atrasadas"], key="gerar_tipo_multipla")
            if st.button("Gerar", key="gerar_dezenas_btn", type="primary"):
                if gerar_tipo == "Sugeridas":
                    if "bets" in st.session_state and st.session_state["bets"]:
                        all_nums = [n for bet in st.session_state["bets"] for n in bet]
                        suggested = sorted([n for n, _ in Counter(all_nums).most_common(n_dezenas)])
                    else:
                        suggested = sorted([n for n, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:n_dezenas]])
                elif gerar_tipo == "Hot Numbers":
                    hot_sorted = sorted(hot_cold_data["hot_set"])
                    if len(hot_sorted) < n_dezenas:
                        extras = [n for n, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True) if n not in set(hot_sorted)]
                        suggested = sorted((hot_sorted + extras)[:n_dezenas])
                    else:
                        suggested = sorted(hot_sorted[:n_dezenas])
                elif gerar_tipo == "Atrasadas":
                    suggested = sorted([n for n, _ in sorted(delays.items(), key=lambda x: x[1], reverse=True)[:n_dezenas]])
                else:
                    suggested = sorted(random.sample(range(1, cfg["dezenas_total"]+1), n_dezenas))
                st.session_state["dezenas_multipla_suggested"] = suggested
            if "dezenas_multipla_suggested" in st.session_state:
                st.info(f"Geradas: {', '.join(str(n) for n in st.session_state['dezenas_multipla_suggested'])}")

        try:
            if dezenas_input_m.strip():
                dezenas_m = sorted(set(int(x.strip()) for x in dezenas_input_m.split(",") if x.strip()))
            elif "dezenas_multipla_suggested" in st.session_state:
                dezenas_m = st.session_state["dezenas_multipla_suggested"]
            else:
                dezenas_m = []
        except ValueError:
            dezenas_m = []
        if len(dezenas_m) >= pick:
            if len(dezenas_m) != n_dezenas:
                n_dezenas = len(dezenas_m)
                total_bets_possible, _ = calculate_desdobramento_cost(n_dezenas, pick, custo_unit)
            if total_bets_possible <= 5000:
                todas_combos = generate_full_desdobramento(dezenas_m, pick)
                if n_apostas < len(todas_combos):
                    random.seed(42)
                    final_multipla = sorted(random.sample(todas_combos, int(n_apostas)))
                else:
                    final_multipla = todas_combos
                st.markdown(f"#### ✅ {len(final_multipla):,} Apostas")
                st.markdown(f"**Custo:** R$ {len(final_multipla)*custo_unit:,.2f}")
                df_m = pd.DataFrame(final_multipla, columns=[f"d{i+1}" for i in range(pick)])
                df_m.insert(0, "#", range(1, len(df_m)+1))
                st.dataframe(df_m, use_container_width=True, hide_index=True)
            else:
                st.error("Muitas combinações. Use menos dezenas.")

    with tab_padroes:
        st.header("📊 Padrões")
        patterns = compute_patterns(draws_matrix, cfg["dezenas_total"])
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            metric_card("Ímpar/Par", f"{patterns['impar_ratio_mean']:.1%}", "")
        with col_p2:
            metric_card("Primos/sorteio", f"{patterns['prime_mean']:.2f}", "")
        with col_p3:
            metric_card("Média Soma", f"{patterns['sum_mean']:.1f}", f"σ={patterns['sum_std']:.1f}")
        st.plotly_chart(plot_prime_impar_summary(patterns, theme), use_container_width=True)
        st.plotly_chart(plot_sum_distribution(patterns, theme), use_container_width=True)
        st.plotly_chart(plot_patterns(patterns, theme), use_container_width=True)
        st.divider()
        st.subheader("🔥 Hot / Cold")
        st.plotly_chart(plot_hot_cold(hot_cold_data, cfg["dezenas_total"], theme), use_container_width=True)
        col_hc1, col_hc2 = st.columns(2)
        with col_hc1:
            st.markdown(f"**🔴 Hot:** {', '.join(str(n) for n in sorted(hot_cold_data['hot_set']))}")
        with col_hc2:
            st.markdown(f"**🔵 Cold:** {', '.join(str(n) for n in sorted(hot_cold_data['cold_set']))}")
        st.divider()
        st.subheader("⚖️ Janela Deslizante")
        freq_simple = freq
        st.plotly_chart(plot_weighted_vs_simple(freq_simple, freq_weighted, cfg["dezenas_total"], theme), use_container_width=True)
        st.caption(f"Decaimento: {decay_factor}")
        col_w1, col_w2 = st.columns(2)
        with col_w1:
            top_w = sorted(freq_weighted.items(), key=lambda x: x[1], reverse=True)[:10]
            st.markdown("**Ponderada:** " + ", ".join(f"{n}({v:.1f})" for n, v in top_w))
        with col_w2:
            top_s = sorted(freq_simple.items(), key=lambda x: x[1], reverse=True)[:10]
            st.markdown("**Simples:** " + ", ".join(f"{n}({v})" for n, v in top_s))
        st.divider()
        st.subheader("📏 Gap Analysis")
        st.plotly_chart(plot_gap_analysis(gap_data, cfg["dezenas_total"], theme), use_container_width=True)
        overdue_nums = [n for n in range(1, cfg["dezenas_total"]+1) if gap_data[n]["overdue"]]
        if overdue_nums:
            st.markdown(f"**🔴 Overdue:** {overdue_nums}")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            gap_rows = [{"Dezena": n, "Gap": gap_data[n]["current_gap"], "Média": gap_data[n]["mean_gap"], "Z": gap_data[n]["z_score"], "Prob": f"{gap_data[n]['prob_next']}%"} for n in range(1, cfg["dezenas_total"]+1)]
            st.dataframe(pd.DataFrame(gap_rows).sort_values("Z", ascending=False).head(10), use_container_width=True, hide_index=True)
        with col_g2:
            st.plotly_chart(plot_prob_ranking(gap_data, cfg["dezenas_total"], theme), use_container_width=True)
        st.divider()
        st.subheader("🔗 Markov")
        if markov_data:
            st.markdown(f"**Último:** {', '.join(str(n) for n in markov_data['last_draw'])}")
            col_m1, col_m2 = st.columns([2, 1])
            with col_m1:
                st.plotly_chart(plot_markov_heatmap(markov_data, cfg["dezenas_total"], theme), use_container_width=True)
            with col_m2:
                top_mk = sorted(markov_data["next_probs"].items(), key=lambda x: x[1], reverse=True)[:15]
                st.dataframe(pd.DataFrame(top_mk, columns=["Dezena", "Prob%"]), use_container_width=True, hide_index=True)

    with tab_backtest:
        st.header("🔬 Backtesting & ROI")
        if "bets" not in st.session_state or not st.session_state["bets"]:
            st.warning("Gere apostas na aba Gerador.")
        else:
            bets = st.session_state["bets"]
            st.info(f"**{len(bets)} apostas × {n_draws} sorteios**")
            col_bt1, col_bt2 = st.columns(2)
            with col_bt1:
                if st.button("🧪 Testar", type="primary", key="testar_historico_button"):
                    with st.spinner("Executando..."):
                        results, df_detail, roi_data = run_backtest(bets, draws_matrix, lottery_name)
                        st.session_state["backtest_results"] = results
                        st.session_state["backtest_detail"] = df_detail
                        st.session_state["backtest_roi"] = roi_data
            with col_bt2:
                if st.button("📊 Comparar Estratégias", key="comparar_estrategias_button"):
                    with st.spinner("Comparando..."):
                        df_comp = compare_strategies(lottery_name, draws_matrix, n_bets=n_bets, weight_freq=w_freq, weight_delay=w_delay, weight_pairs=w_pairs, trevos_matrix=trevos_matrix, meses_series=meses_series, decay=decay_factor)
                        st.session_state["df_comparacao"] = df_comp
            if "backtest_results" in st.session_state:
                results = st.session_state["backtest_results"]
                roi_data = st.session_state.get("backtest_roi", {})
                st.plotly_chart(plot_backtest_results(results, theme), use_container_width=True)
                if roi_data:
                    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                    with col_r1:
                        metric_card("Custo", f"R$ {roi_data['custo_total']:,.2f}", f"{roi_data['n_bets']}ap")
                    with col_r2:
                        metric_card("Prêmios", f"R$ {roi_data['premios_total']:,.2f}", "estimados")
                    with col_r3:
                        roi_color = "#28a745" if roi_data['roi_pct'] >= 0 else "#dc3545"
                        st.markdown(f"""<div class="metric-card"><div class="metric-label">ROI</div><div class="metric-value" style="color:{roi_color};">{roi_data['roi_pct']:+.1f}%</div></div>""", unsafe_allow_html=True)
                    with col_r4:
                        lucro_color = "#28a745" if roi_data['lucro_liquido'] >= 0 else "#dc3545"
                        st.markdown(f"""<div class="metric-card"><div class="metric-label">Lucro/Prej.</div><div class="metric-value" style="color:{lucro_color};">R$ {roi_data['lucro_liquido']:,.2f}</div></div>""", unsafe_allow_html=True)
                df_res = pd.DataFrame([{"Prêmio": k, "Qtd": v} for k, v in results.items() if v > 0])
                if not df_res.empty:
                    st.dataframe(df_res, use_container_width=True, hide_index=True)
            if "df_comparacao" in st.session_state:
                st.divider()
                st.markdown("### ⚔️ Comparação")
                df_comp = st.session_state["df_comparacao"]
                df_comp["ROI %"] = df_comp["ROI %"].apply(lambda x: f"{x:+.1f}%")
                st.dataframe(df_comp, use_container_width=True, hide_index=True)

    with tab_dados:
        st.header("📋 Dados")
        st.dataframe(df_data.head(100), use_container_width=True)
        if st.checkbox("Estatísticas descritivas", key="mostrar_estatisticas_check"):
            st.dataframe(df_data.describe(), use_container_width=True)

    st.divider()
    st.markdown(f"<div style='text-align:center;opacity:0.6;font-size:0.8rem;'>Motor Analítico de Loterias · {datetime.now().year} · Jogue com responsabilidade · Ligue 188 (CVV).</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
