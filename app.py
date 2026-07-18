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
    import xlsxwriter
except ImportError:
    xlsxwriter = None

LOTTERIES = {
    "Mega Sena": {
        "dezenas_total": 60, "dezenas_aposta": 6, "max_acertos": 6,
        "premios": {4: "Quadra", 5: "Quina", 6: "Sena"},
        "color": "green", "api_slug": "megasena",
        "tem_trevos": False, "tem_mes": False, "custo_aposta": 5.00,
    },
    "Lotofácil": {
        "dezenas_total": 25, "dezenas_aposta": 15, "max_acertos": 15,
        "premios": {11: "Loteria", 12: "Loteria", 13: "Loteria", 14: "Quina", 15: "Sena"},
        "color": "purple", "api_slug": "lotofacil",
        "tem_trevos": False, "tem_mes": False, "custo_aposta": 3.00,
    },
    "Quina": {
        "dezenas_total": 80, "dezenas_aposta": 5, "max_acertos": 5,
        "premios": {2: "Duque", 3: "Terno", 4: "Quadra", 5: "Quina"},
        "color": "blue", "api_slug": "quina",
        "tem_trevos": False, "tem_mes": False, "custo_aposta": 2.50,
    },
    "+Milionária": {
        "dezenas_total": 50, "dezenas_aposta": 6, "max_acertos": 6,
        "premios": {4: "Quadra", 5: "Quina", 6: "Sena"},
        "color": "orange", "api_slug": "maismilionaria",
        "tem_trevos": True, "trevos_total": 6, "trevos_aposta": 2,
        "tem_mes": False, "custo_aposta": 5.00,
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
            gaps[num] = {
                "mean_gap": n_draws, "std_gap": 0, "current_gap": n_draws,
                "z_score": 0, "overdue": False, "appearances": [],
                "prob_next": 0.0,
            }
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
        gaps[num] = {
            "mean_gap": round(mean_gap, 2),
            "std_gap": round(std_gap, 2),
            "current_gap": current_gap,
            "z_score": round(z_score, 2),
            "overdue": overdue,
            "appearances": appearances,
            "prob_next": round(prob_next * 100, 1),
        }
    return gaps

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
    return {
        "seen": sorted(seen),
        "missing": sorted(missing),
        "completion_pct": round(completion, 1),
        "total_unique": len(seen),
        "total_numbers": total_numbers,
        "cycle_start_idx": cycle_start,
    }

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

def generate_bets(lottery_name, draws_matrix, n_bets=10, strategy="híbrido",
                  weight_freq=0.4, weight_delay=0.3, weight_pairs=0.3,
                  trevos_matrix=None, meses_series=None,
                  min_hot=0, exclude_cold=False, hot_set=None, cold_set=None):
    cfg = LOTTERIES[lottery_name]
    total = cfg["dezenas_total"]
    pick = cfg["dezenas_aposta"]
    freq = compute_frequency(draws_matrix, total)
    delays = compute_delays(draws_matrix, total)
    mc_pairs, real_pairs = monte_carlo_pairs(draws_matrix, total, iterations=1000)
    patterns = compute_patterns(draws_matrix, total)
    quadrants = compute_quadrants(total, 4)
    cycle = compute_cycle_completion(draws_matrix, total)
    gap_data = compute_gap_analysis(draws_matrix, total)
    max_freq = max(freq.values()) if max(freq.values()) > 0 else 1
    max_delay = max(delays.values()) if max(delays.values()) > 0 else 1
    pair_score_map = {num: 0.0 for num in range(1, total + 1)}
    for (a, b), cnt in real_pairs.items():
        pair_score_map[a] += cnt
        pair_score_map[b] += cnt
    max_pair = max(pair_score_map.values()) if max(pair_score_map.values()) > 0 else 1
    scores = {}
    for num in range(1, total + 1):
        f_score = freq.get(num, 0) / max_freq
        d_score = delays.get(num, 0) / max_delay
        scores[num] = weight_freq * f_score + weight_delay * d_score
        if num in cycle["missing"] and cycle["completion_pct"] > 70:
            scores[num] *= 1.15
        if gap_data[num]["overdue"]:
            scores[num] *= 1.20
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
                detail_rows.append({
                    "Concurso": draw_idx + 1,
                    "Aposta #": bet_idx + 1,
                    "Acertos": hits,
                    "Prêmio": label,
                    "Valor Est. (R$)": valor_est,
                })
            elif hits >= 3:
                results["Nenhum"] += 1
    roi = ((premios_total - custo_total) / custo_total * 100) if custo_total > 0 else 0
    roi_data = {
        "custo_total": custo_total,
        "premios_total": premios_total,
        "roi_pct": roi,
        "lucro_liquido": premios_total - custo_total,
        "n_bets": n_bets,
        "n_concursos": n_concursos,
    }
    return results, pd.DataFrame(detail_rows), roi_data

def compare_strategies(lottery_name, draws_matrix, n_bets=10, weight_freq=0.4, weight_delay=0.3, weight_pairs=0.3, trevos_matrix=None, meses_series=None):
    strategies = ["híbrido", "frequentes", "atrasadas", "aleatória"]
    comparison = []
    for strat in strategies:
        bets, scores_list, freq, delays, real_pairs, patterns, quadrants, cycle, trevos_bets, mes_bets, rej = generate_bets(
            lottery_name, draws_matrix, n_bets=n_bets, strategy=strat,
            weight_freq=weight_freq, weight_delay=weight_delay, weight_pairs=weight_pairs,
            trevos_matrix=trevos_matrix, meses_series=meses_series,
            min_hot=0, exclude_cold=False, hot_set=None, cold_set=None,
        )
        results, df_detail, roi_data = run_backtest(bets, draws_matrix, lottery_name)
        total_premios = sum(v for k, v in results.items() if k != "Nenhum")
        comparison.append({
            "Estratégia": strat.capitalize(),
            "Apostas": len(bets),
            "Prêmios Ganhos": total_premios,
            "Custo Total (R$)": roi_data["custo_total"],
            "Prêmios Total (R$)": roi_data["premios_total"],
            "ROI %": roi_data["roi_pct"],
            "Lucro/Prejuízo (R$)": roi_data["lucro_liquido"],
        })
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
        resultados.append({
            "Aposta #": i + 1,
            "Dezenas": " - ".join(f"{n:02d}" for n in bet),
            "Acertos": hits,
            "Números Acertados": " - ".join(f"{n:02d}" for n in numeros_acertados) if numeros_acertados else "-",
            "Prêmio": label if label else "-",
            "Trevo Hits": trevo_hits if trevos_bets else "-",
            "Mês?": "✅" if mes_acertou else ("❌" if mes_bets else "-"),
        })
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
        "loteria": loteria_slug, "loteria_nome": lottery_name,
        "dezenas_aposta": cfg["dezenas_aposta"], "total_apostas": len(bets),
        "apostas": apostas_list, "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    if cfg.get("tem_trevos"):
        data["trevos_aposta"] = cfg["trevos_aposta"]
    if cfg.get("tem_mes"):
        data["tem_mes"] = True
    return data

def plot_frequency_bar(freq, total, theme):
    nums = list(range(1, total + 1))
    vals = [freq.get(n, 0) for n in nums]
    fig = go.Figure(data=[go.Bar(x=nums, y=vals, marker_color=theme["accent"])])
    fig.update_layout(title="Frequência de Dezenas", xaxis_title="Dezena", yaxis_title="Frequência",
        template="plotly_white", height=400, paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def plot_hot_cold(hot_cold_data, total, theme):
    nums = list(range(1, total + 1))
    vals = [hot_cold_data["freq_recent"].get(n, 0) for n in nums]
    colors = []
    for n in nums:
        if n in hot_cold_data["hot_set"]:
            colors.append("#FF4444")
        elif n in hot_cold_data["cold_set"]:
            colors.append("#4488FF")
        else:
            colors.append("#CCCCCC")
    fig = go.Figure(data=[go.Bar(x=nums, y=vals, marker_color=colors, text=vals, textposition="auto")])
    fig.update_layout(
        title=f"Hot / Cold Numbers (últimos {hot_cold_data['recent_n']} sorteios)",
        xaxis_title="Dezena", yaxis_title="Frequência",
        template="plotly_white", height=400,
        paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"],
        font=dict(color=theme["text"]),
    )
    return fig

def plot_gap_analysis(gap_data, total, theme):
    nums = list(range(1, total + 1))
    current_gaps = [gap_data[n]["current_gap"] for n in nums]
    mean_gaps = [gap_data[n]["mean_gap"] for n in nums]
    colors = []
    for n in nums:
        if gap_data[n]["overdue"]:
            colors.append("#FF4444")
        elif gap_data[n]["z_score"] > 1:
            colors.append("#FFA500")
        else:
            colors.append(theme["accent"])
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=nums, y=current_gaps,
        marker_color=colors, name="Gap Atual",
        text=[f"{g}" for g in current_gaps], textposition="auto",
    ))
    fig.add_trace(go.Scatter(
        x=nums, y=mean_gaps,
        mode="lines+markers", line=dict(color="#FF0000", dash="dash", width=2),
        marker=dict(size=5), name="Média Histórica",
    ))
    fig.update_layout(
        title="Gap Analysis: Intervalo Atual vs Média Histórica",
        xaxis_title="Dezena", yaxis_title="Concursos sem aparecer",
        template="plotly_white", height=450,
        paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"],
        font=dict(color=theme["text"]), showlegend=True,
    )
    return fig

def plot_gap_timeline(gap_data, num, n_draws, theme):
    appearances = gap_data[num]["appearances"]
    fig = go.Figure()
    x_vals = list(range(n_draws))
    y_vals = [1 if i in set(appearances) else 0 for i in range(n_draws)]
    colors = ["#FF4444" if v == 1 else "#EEEEEE" for v in y_vals]
    fig.add_trace(go.Bar(
        x=x_vals, y=y_vals,
        marker_color=colors, name=f"Dezena {num}",
    ))
    fig.update_layout(
        title=f"Timeline de Aparições — Dezena {num}",
        xaxis_title="Concurso (índice)", yaxis_title="Apareceu?",
        template="plotly_white", height=250,
        paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"],
        font=dict(color=theme["text"]), showlegend=False,
    )
    return fig

def plot_prob_ranking(gap_data, total, theme):
    nums = list(range(1, total + 1))
    probs = [gap_data[n]["prob_next"] for n in nums]
    sorted_idx = sorted(range(len(probs)), key=lambda i: probs[i], reverse=True)
    sorted_nums = [nums[i] for i in sorted_idx]
    sorted_probs = [probs[i] for i in sorted_idx]
    colors = ["#FF4444" if gap_data[n]["overdue"] else theme["accent"] for n in sorted_nums]
    fig = go.Figure(data=[go.Bar(
        x=[str(n) for n in sorted_nums], y=sorted_probs,
        marker_color=colors, text=[f"{p}%" for p in sorted_probs],
        textposition="auto",
    )])
    fig.update_layout(
        title="Ranking de Probabilidade para o Próximo Sorteio",
        xaxis_title="Dezena (rank)", yaxis_title="Probabilidade Estimada (%)",
        template="plotly_white", height=400,
        paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"],
        font=dict(color=theme["text"]),
    )
    return fig

def plot_delays_bar(delays, total, theme, title_suffix=""):
    nums = list(range(1, total + 1))
    vals = [delays.get(n, 0) for n in nums]
    fig = go.Figure(data=[go.Bar(x=nums, y=vals, marker_color=theme["accent"], opacity=0.8)])
    fig.update_layout(title=f"Atraso de Dezenas{title_suffix}", xaxis_title="Dezena", yaxis_title="Atraso",
        template="plotly_white", height=400, paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def plot_trevos_frequency(freq, total, theme):
    nums = list(range(1, total + 1))
    vals = [freq.get(n, 0) for n in nums]
    fig = go.Figure(data=[go.Bar(x=nums, y=vals, marker_color="#FF8C00")])
    fig.update_layout(title="Frequência de Trevos", xaxis_title="Trevo", yaxis_title="Frequência",
        template="plotly_white", height=350, paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def plot_meses_frequency(freq, meses_lista, theme):
    vals = [freq.get(i + 1, 0) for i in range(len(meses_lista))]
    fig = go.Figure(data=[go.Bar(x=meses_lista, y=vals, marker_color="#FF69B4")])
    fig.update_layout(title="Frequência de Meses Sorteados", xaxis_title="Mês", yaxis_title="Frequência",
        template="plotly_white", height=350, paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def plot_patterns(patterns, theme):
    fig = make_subplots(rows=2, cols=2,
        subplot_titles=("Proporção Ímpar/Par", "Números Primos", "Distribuição da Soma", "Resumo Médias"),
        specs=[[{"type":"histogram"},{"type":"histogram"}],[{"type":"histogram"},{"type":"indicator"}]])
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
    fig.update_layout(title="Histograma da Soma das Dezenas", xaxis_title="Soma", yaxis_title="Frequência",
        template="plotly_white", height=420, paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def plot_prime_impar_summary(patterns, theme):
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Média Ímpar/Par", "Média Primos"),
                        specs=[[{"type":"pie"},{"type":"indicator"}]])
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
    fig.update_layout(title="Resultado do Backtesting (Ordem Crescente)", xaxis_title="Categoria de Prêmio",
        yaxis_title="Ocorrências", template="plotly_white", height=400,
        paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def plot_scores_bar(scores_list, theme):
    fig = go.Figure(data=[go.Bar(x=list(range(1, len(scores_list)+1)), y=scores_list, marker_color=theme["accent"], text=scores_list, textposition="auto")])
    fig.update_layout(title="Score de Confiança por Aposta", xaxis_title="Aposta #", yaxis_title="Score (0-100)",
        template="plotly_white", height=350, paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def plot_cycle_completion(cycle, total, theme):
    seen = len(cycle["seen"])
    missing = len(cycle["missing"])
    fig = go.Figure(data=[go.Pie(labels=["Vistas no ciclo", "Faltando"], values=[seen, missing],
        marker_colors=[theme["accent"], "#FF6B6B"], hole=0.4)])
    fig.update_layout(title=f"Ciclo de Completude: {cycle['completion_pct']}%", height=350,
        template="plotly_white", paper_bgcolor=theme["bg"], plot_bgcolor=theme["bg"], font=dict(color=theme["text"]))
    return fig

def render_caixa_export(bets, lottery_name, trevos_bets=None, mes_bets=None, download_key="caixa"):
    cfg = LOTTERIES[lottery_name]
    json_data = export_to_caixa_json(bets, lottery_name, trevos_bets, mes_bets)
    json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
    st.markdown("#### 🛒 Exportação para Carrinho da Caixa")
    st.download_button(
        label="📥 Baixar JSON (formato Caixa)",
        data=json_str.encode("utf-8"),
        file_name=f"apostas_caixa_{lottery_name.lower().replace(' ','_').replace('+','mais')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        key=f"download_json_{download_key}",
    )
    st.markdown("##### 📋 Carrinho de Apostas")
    carrinho_rows = []
    for i, bet in enumerate(bets):
        row = {"#": i + 1, "Dezenas": " - ".join(f"{n:02d}" for n in bet)}
        if trevos_bets:
            row["Trevos"] = " - ".join(f"🍀{t}" for t in trevos_bets[i])
        if mes_bets:
            row["Mês"] = cfg["meses_lista"][mes_bets[i] - 1]
        carrinho_rows.append(row)
    st.dataframe(pd.DataFrame(carrinho_rows), use_container_width=True, hide_index=True)

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
        st.markdown("**🌐 API da Caixa** (dados reais)")
        n_concursos_api = st.slider("Quantos concursos buscar da Caixa?", 10, 100, 30, key="n_concursos_slider_api")
        if st.button("🔄 Buscar dados da Caixa", key="fetch_caixa_button", type="secondary"):
            with st.spinner(f"Buscando {n_concursos_api} concursos da {lottery_name} na Caixa..."):
                df_caixa = fetch_caixa_history(lottery_name, n_concursos_api)
                if df_caixa is not None and len(df_caixa) > 0:
                    st.session_state["df_caixa"] = df_caixa
                    st.session_state["data_source"] = "caixa"
                    st.sidebar.success(f"✅ {len(df_caixa)} concursos reais carregados!")
                else:
                    st.sidebar.error("❌ Não foi possível buscar dados da Caixa. Usando fallback.")
        st.divider()
        st.markdown("**📁 Ou suba um arquivo**")
        uploaded_file = st.file_uploader("CSV ou Excel", type=["csv","xlsx","xls"], key="file_uploader")
        use_mock = st.checkbox("Usar dados mockados como fallback", value=True, key="use_mock_checkbox")
        st.divider()
        st.subheader("🎲 Gerador de Apostas")
        n_bets = st.slider("Número de apostas", 1, 50, 10, key="n_bets_slider")
        strategy = st.selectbox("Estratégia", ["híbrido","frequentes","atrasadas","aleatória"], index=0, key="strategy_select")
        w_freq = st.slider("Peso Frequência", 0.0, 1.0, 0.4, 0.05, key="weight_freq_slider")
        w_delay = st.slider("Peso Atraso", 0.0, 1.0, 0.3, 0.05, key="weight_delay_slider")
        w_pairs = st.slider("Peso Pares Fortes", 0.0, 1.0, 0.3, 0.05, key="weight_pairs_slider")
        st.divider()
        st.subheader("🔥 Hot / Cold Numbers")
        min_hot = st.slider("Mín. de Hot Numbers na aposta", 0, cfg["dezenas_aposta"], 0, key="min_hot_slider")
        exclude_cold = st.checkbox("Excluir Cold Numbers", value=False, key="exclude_cold_checkbox")

    df_data = None
    if "df_caixa" in st.session_state and st.session_state["df_caixa"] is not None and st.session_state.get("data_source") == "caixa":
        df_data = st.session_state["df_caixa"]
        st.sidebar.info(f"🌐 Dados da API Caixa: {len(df_data)} concursos")
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
    st.sidebar.caption(f"🔴 Hot = top 25% mais sorteados nos últimos {hot_cold_data['recent_n']} concursos")
    st.sidebar.caption(f"🔵 Cold = bottom 25% menos sorteados")

    st.markdown(f"""
    <div class="main-header">
        <div class="main-title">🎲 Motor Analítico & Gerador de Apostas</div>
        <div class="main-subtitle">API Caixa · Quadrantes · Score · Ciclo · Hot/Cold · Gap Analysis · ROI · Conferidor</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Sorteios Analisados", n_draws, "Histórico")
    with col2:
        metric_card("Dezenas / Aposta", cfg["dezenas_aposta"], lottery_name)
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
        metric_card("Dezena + Frequente", f"{top_num}", f"{freq[top_num]}x no histórico")

    st.divider()

    tab_gerador, tab_conferidor, tab_fechamento, tab_padroes, tab_backtest, tab_dados = st.tabs([
        "🎰 Gerador", "✅ Conferidor", "🔢 Fechamento", "📊 Padrões", "🔬 Backtesting", "📋 Dados"
    ])

    with tab_gerador:
        st.header("🎰 Gerador de Apostas Otimizado")
        st.markdown("Combina **frequência**, **atraso**, **pares fortes**, **quadrantes**, **score**, **ciclo**, **hot/cold** e **gap analysis**.")
        if st.session_state["gen_counter"] > 0:
            st.caption(f"🔄 Geração #{st.session_state['gen_counter']}")
        if st.button("⚡ Gerar Apostas", type="primary", key="gerar_apostas_button"):
            with st.spinner("Gerando apostas otimizadas..."):
                max_attempts = 3
                for attempt in range(max_attempts):
                    bets, scores_list, freq, delays, real_pairs, patterns, quadrants, cycle, trevos_bets, mes_bets, rejection_reasons = generate_bets(
                        lottery_name, draws_matrix, n_bets=n_bets,
                        strategy=strategy, weight_freq=w_freq, weight_delay=w_delay, weight_pairs=w_pairs,
                        trevos_matrix=trevos_matrix, meses_series=meses_series,
                        min_hot=min_hot, exclude_cold=exclude_cold,
                        hot_set=hot_cold_data["hot_set"], cold_set=hot_cold_data["cold_set"],
                    )
                    old_bets = st.session_state.get("bets", [])
                    if bets_are_unique(bets, old_bets) or attempt == max_attempts - 1:
                        break
                    time.sleep(0.01)
                strong_pairs = find_strong_pairs(real_pairs, top_n=20)
                st.session_state["bets"] = bets
                st.session_state["scores_list"] = scores_list
                st.session_state["freq"] = freq
                st.session_state["delays"] = delays
                st.session_state["strong_pairs"] = strong_pairs
                st.session_state["trevos_bets"] = trevos_bets
                st.session_state["mes_bets"] = mes_bets
                st.session_state["patterns"] = patterns
                st.session_state["quadrants"] = quadrants
                st.session_state["cycle"] = cycle
                st.session_state["rejection_reasons"] = rejection_reasons
                st.session_state["gen_counter"] += 1

        if "bets" in st.session_state and st.session_state["bets"]:
            bets = st.session_state["bets"]
            scores_list = st.session_state.get("scores_list", [])
            freq = st.session_state["freq"]
            delays = st.session_state["delays"]
            strong_pairs = st.session_state["strong_pairs"]
            trevos_bets = st.session_state.get("trevos_bets", [])
            mes_bets = st.session_state.get("mes_bets", [])
            patterns = st.session_state.get("patterns", {})
            quadrants = st.session_state.get("quadrants", {})
            cycle = st.session_state.get("cycle", {})
            rejection_reasons = st.session_state.get("rejection_reasons", [])
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
            if cycle:
                col_cyc1, col_cyc2 = st.columns([1, 2])
                with col_cyc1:
                    st.plotly_chart(plot_cycle_completion(cycle, cfg["dezenas_total"], theme), use_container_width=True)
                with col_cyc2:
                    st.markdown(f"### 🔄 Ciclo de Completude")
                    st.markdown(f"**{cycle['completion_pct']}%** do universo já foi sorteado no ciclo atual.")
                    st.markdown(f"**{cycle['total_unique']}** de **{cycle['total_numbers']}** dezenas vistas.")
                    if cycle["missing"]:
                        missing_str = ", ".join(str(m) for m in cycle["missing"][:20])
                        st.markdown(f"**Dezenas faltando:** {missing_str}{'...' if len(cycle['missing']) > 20 else ''}")
                        st.caption("Dezenas faltando no ciclo recebem +15% no score quando o ciclo > 70%.")
            if rejection_reasons:
                with st.expander(f"📊 Estatísticas de Validação ({len(rejection_reasons)} apostas rejeitadas)"):
                    reason_counts = Counter(rejection_reasons)
                    df_rej = pd.DataFrame([{"Motivo": k, "Quantidade": v} for k, v in reason_counts.most_common()])
                    st.dataframe(df_rej, use_container_width=True, hide_index=True)
                    st.caption("Apostas rejeitadas não chegam ao resultado final — o gerador cria novas até passar em todos os critérios.")
            st.markdown("### Visualização")
            cols = st.columns(min(len(bets), 5))
            for i, bet in enumerate(bets[:10]):
                with cols[i % len(cols)]:
                    balls_html = " ".join([
                        f"<span style='display:inline-block;width:28px;height:28px;line-height:28px;text-align:center;border-radius:50%;background:{'#FF4444' if n in hot_cold_data['hot_set'] else ('#4488FF' if n in hot_cold_data['cold_set'] else theme['accent'])};color:white;font-weight:bold;margin:2px;font-size:0.75rem;'>{n}</span>"
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
                    score_badge = f"<span style='display:inline-block;padding:2px 8px;border-radius:6px;background:#28a745;color:white;font-weight:bold;font-size:0.7rem;margin-left:6px;'>Score: {scores_list[i]}</span>" if scores_list else ""
                    st.markdown(f"<div style='padding:8px;background:{theme['card']};border-radius:10px;margin:4px 0;'><b>Aposta {i+1}</b>{score_badge}<br>{balls_html}{extra_html}</div>", unsafe_allow_html=True)
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.plotly_chart(plot_frequency_bar(freq, cfg["dezenas_total"], theme), use_container_width=True)
            with col_g2:
                st.plotly_chart(plot_delays_bar(delays, cfg["dezenas_total"], theme), use_container_width=True)
            if cfg.get("tem_trevos") and trevos_matrix is not None:
                tf = compute_trevos_frequency(trevos_matrix, cfg["trevos_total"])
                td = compute_trevos_delays(trevos_matrix, cfg["trevos_total"])
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    st.plotly_chart(plot_trevos_frequency(tf, cfg["trevos_total"], theme), use_container_width=True)
                with col_t2:
                    st.plotly_chart(plot_delays_bar(td, cfg["trevos_total"], theme, " (Trevos)"), use_container_width=True)
            if cfg.get("tem_mes") and meses_series is not None:
                mf = compute_meses_frequency(meses_series, cfg["meses_total"])
                st.plotly_chart(plot_meses_frequency(mf, cfg["meses_lista"], theme), use_container_width=True)
            st.subheader("🔗 Pares Fortes (Monte Carlo + Histórico)")
            df_pairs = pd.DataFrame(strong_pairs, columns=["Par","Ocorrências"])
            df_pairs["Dezena_A"] = df_pairs["Par"].apply(lambda x: x[0])
            df_pairs["Dezena_B"] = df_pairs["Par"].apply(lambda x: x[1])
            st.dataframe(df_pairs[["Dezena_A","Dezena_B","Ocorrências"]].head(15), use_container_width=True, hide_index=True)
            st.subheader("📥 Exportação")
            excel_data = export_to_excel(bets, freq, delays, strong_pairs, lottery_name, trevos_bets, mes_bets, scores_list)
            st.download_button(
                label="📊 Baixar Excel (.xlsx)",
                data=excel_data,
                file_name=f"apostas_{lottery_name.replace(' ','_').replace('+','mais')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel_apostas",
            )
            st.divider()
            render_caixa_export(bets, lottery_name, trevos_bets, mes_bets, download_key="gerador")
        else:
            st.info("Clique em **⚡ Gerar Apostas** para criar combinações otimizadas.")

    with tab_conferidor:
        st.header("✅ Conferidor de Resultados")
        st.markdown("Confere suas apostas geradas contra o **último sorteio real** da Caixa.")
        col_conf1, col_conf2 = st.columns([2, 1])
        with col_conf2:
            if st.button("🔄 Buscar último sorteio", key="fetch_ultimo_button", type="secondary"):
                with st.spinner("Buscando último sorteio da Caixa..."):
                    latest_data = fetch_caixa_latest(lottery_name)
                    if latest_data:
                        parsed = parse_caixa_json(latest_data, lottery_name)
                        if parsed:
                            st.session_state["ultimo_sorteio"] = parsed
                            st.session_state["ultimo_sorteio_raw"] = latest_data
                            st.success("✅ Sorteio carregado!")
                        else:
                            st.error("Não foi possível processar o sorteio.")
                    else:
                        st.error("Erro ao buscar sorteio da Caixa.")
        if "ultimo_sorteio" in st.session_state:
            sorteio = st.session_state["ultimo_sorteio"]
            with col_conf1:
                concurso_num = sorteio.get("concurso", "?")
                data_sorteio = sorteio.get("data", "?")
                st.markdown(f"### 🏆 Concurso {concurso_num} — {data_sorteio}")
                pick = cfg["dezenas_aposta"]
                dezenas_sort = [sorteio.get(f"d{i+1}") for i in range(pick) if sorteio.get(f"d{i+1}") is not None]
                dezenas_html = " ".join([
                    f"<span style='display:inline-block;width:36px;height:36px;line-height:36px;text-align:center;border-radius:50%;background:#28a745;color:white;font-weight:bold;margin:3px;font-size:1rem;'>{n:02d}</span>"
                    for n in dezenas_sort
                ])
                st.markdown(f"<div style='padding:12px;background:{theme['card']};border-radius:12px;margin:8px 0;'>{dezenas_html}</div>", unsafe_allow_html=True)
                trevos_sort = None
                if cfg.get("tem_trevos"):
                    trevos_sort = [sorteio.get(f"t{i+1}") for i in range(cfg["trevos_aposta"]) if sorteio.get(f"t{i+1}") is not None]
                    if trevos_sort:
                        trevos_html = " ".join([
                            f"<span style='display:inline-block;width:36px;height:36px;line-height:36px;text-align:center;border-radius:50%;background:#FF8C00;color:white;font-weight:bold;margin:3px;font-size:1rem;'>🍀{t}</span>"
                            for t in trevos_sort
                        ])
                        st.markdown(f"<div style='padding:8px;'>{trevos_html}</div>", unsafe_allow_html=True)
                mes_sort = None
                if cfg.get("tem_mes"):
                    mes_sort = sorteio.get("mes")
                    if mes_sort and 1 <= mes_sort <= 12:
                        mes_nome = cfg["meses_lista"][mes_sort - 1]
                        st.markdown(f"<div style='padding:8px;'><span style='display:inline-block;padding:6px 16px;border-radius:8px;background:#FF69B4;color:white;font-weight:bold;font-size:1rem;'>📅 {mes_nome}</span></div>", unsafe_allow_html=True)
            if "bets" in st.session_state and st.session_state["bets"] and dezenas_sort:
                bets = st.session_state["bets"]
                trevos_bets = st.session_state.get("trevos_bets", [])
                mes_bets = st.session_state.get("mes_bets", [])
                st.divider()
                st.subheader("🎯 Conferência das suas Apostas")
                df_conf = conferir_apostas(
                    bets, dezenas_sort, lottery_name,
                    trevos_bets if trevos_bets else None,
                    mes_bets if mes_bets else None,
                    trevos_sort, mes_sort,
                )
                st.dataframe(df_conf, use_container_width=True, hide_index=True)
                tem_premio = df_conf[df_conf["Prêmio"] != "-"]
                if not tem_premio.empty:
                    st.success(f"🎉 **{len(tem_premio)} aposta(s) premiada(s)!**")
                    st.dataframe(tem_premio, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhuma aposta premiada neste sorteio. Tente gerar novas apostas!")
                col_c1, col_c2, col_c3 = st.columns(3)
                with col_c1:
                    max_hits = df_conf["Acertos"].max()
                    metric_card("Máximo de Acertos", max_hits, f"em {len(bets)} apostas")
                with col_c2:
                    avg_hits = df_conf["Acertos"].mean()
                    metric_card("Média de Acertos", f"{avg_hits:.1f}", "por aposta")
                with col_c3:
                    total_premios = len(tem_premio)
                    metric_card("Apostas Premiadas", total_premios, "neste sorteio")
            else:
                st.info("Gere apostas na aba **Gerador** primeiro para conferir com este sorteio.")
        else:
            st.info("Clique em **🔄 Buscar último sorteio** para carregar o resultado mais recente da Caixa.")

    with tab_fechamento:
        st.header("🔢 Fechamento Matemático")
        st.markdown("Gera combinações matemáticas a partir de dezenas escolhidas, com filtros opcionais.")
        dezenas_input = st.text_area("Digite as dezenas separadas por vírgula (ex: 5, 12, 23, 34, 47, 58)", value="", height=80, key="dezenas_textarea")
        st.markdown("**Filtros (opcionais):**")
        usar_filtros = st.checkbox("Ativar filtros", value=False, key="ativar_filtros_checkbox")
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            qtd_impares = st.slider("Qtd. ímpares", 0, cfg["dezenas_aposta"], cfg["dezenas_aposta"]//2, key="qtd_impares_slider") if usar_filtros else cfg["dezenas_aposta"]//2
        with col_f2:
            soma_min = int(cfg["dezenas_total"]*cfg["dezenas_aposta"]*0.3)
            soma_max = int(cfg["dezenas_total"]*cfg["dezenas_aposta"]*0.7)
            soma_intervalo = st.slider("Intervalo da soma", 1, cfg["dezenas_total"]*cfg["dezenas_aposta"], (soma_min, soma_max), key="soma_intervalo_slider") if usar_filtros else (1, cfg["dezenas_total"]*cfg["dezenas_aposta"])
        with col_f3:
            max_consec = st.slider("Máx. consecutivos", 1, cfg["dezenas_aposta"], cfg["dezenas_aposta"], key="max_consec_slider") if usar_filtros else cfg["dezenas_aposta"]
        if st.button("🔢 Gerar Fechamento", type="primary", key="gerar_fechamento_button"):
            try:
                dezenas_list = sorted(set(int(x.strip()) for x in dezenas_input.split(",") if x.strip()))
                pick = cfg["dezenas_aposta"]
                if len(dezenas_list) < pick:
                    st.warning(f"Você precisa de pelo menos {pick} dezenas.")
                else:
                    total_combinations = list(itertools.combinations(dezenas_list, pick))
                    filtered = []
                    for combo in total_combinations:
                        if usar_filtros:
                            if sum(1 for x in combo if x%2!=0) != qtd_impares:
                                continue
                            if not (soma_intervalo[0] <= sum(combo) <= soma_intervalo[1]):
                                continue
                            consec = max_consec_found = 1
                            for i in range(1, len(combo)):
                                if combo[i] == combo[i-1]+1:
                                    consec += 1
                                    max_consec_found = max(max_consec_found, consec)
                                else:
                                    consec = 1
                            if max_consec_found > max_consec:
                                continue
                        filtered.append(sorted(combo))
                    if not filtered:
                        st.warning("Nenhuma combinação passou nos filtros.")
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
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                metric_card("Combinações Originais", total_orig, "Fechamento total")
            with col_r2:
                metric_card("Após Filtros", total_filt, "Combinações válidas")
            with col_r3:
                reducao = total_orig - total_filt
                perc = (reducao/total_orig*100) if total_orig > 0 else 0
                metric_card("Redução", f"{reducao} ({perc:.1f}%)", "Economia de apostas")
            df_fech = pd.DataFrame(f_bets, columns=[f"d{i+1}" for i in range(cfg["dezenas_aposta"])])
            df_fech.insert(0, "#", range(1, len(f_bets)+1))
            st.dataframe(df_fech, use_container_width=True, hide_index=True)
            freq_local = st.session_state.get("freq", {})
            delays_local = st.session_state.get("delays", {})
            strong_pairs_local = st.session_state.get("strong_pairs", [])
            excel_fech = export_to_excel(f_bets, freq_local, delays_local, strong_pairs_local, lottery_name)
            st.download_button(
                label="📊 Baixar Fechamento em Excel",
                data=excel_fech,
                file_name=f"fechamento_{lottery_name.replace(' ','_').replace('+','mais')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel_fechamento",
            )
            st.divider()
            render_caixa_export(f_bets, lottery_name, download_key="fechamento")
        else:
            st.info("Digite suas dezenas acima e clique em **🔢 Gerar Fechamento**.")

    with tab_padroes:
        st.header("📊 Padrões Comportamentais")
        patterns = compute_patterns(draws_matrix, cfg["dezenas_total"])
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            metric_card("Média Ímpar/Par", f"{patterns['impar_ratio_mean']:.1%}", "Proporção ímpares")
        with col_p2:
            metric_card("Média Primos", f"{patterns['prime_mean']:.2f}", "Por sorteio")
        with col_p3:
            metric_card("Média da Soma", f"{patterns['sum_mean']:.1f}", f"σ = {patterns['sum_std']:.1f}")
        st.plotly_chart(plot_prime_impar_summary(patterns, theme), use_container_width=True)
        st.plotly_chart(plot_sum_distribution(patterns, theme), use_container_width=True)
        st.plotly_chart(plot_patterns(patterns, theme), use_container_width=True)
        st.divider()
        st.subheader("🔥 Hot / Cold Numbers")
        st.plotly_chart(plot_hot_cold(hot_cold_data, cfg["dezenas_total"], theme), use_container_width=True)
        col_hc1, col_hc2 = st.columns(2)
        with col_hc1:
            hot_nums = sorted(list(hot_cold_data["hot_set"]))
            st.markdown(f"**🔴 Hot Numbers:** {', '.join(str(n) for n in hot_nums)}")
        with col_hc2:
            cold_nums = sorted(list(hot_cold_data["cold_set"]))
            st.markdown(f"**🔵 Cold Numbers:** {', '.join(str(n) for n in cold_nums)}")
        st.divider()
        st.subheader("📏 Gap Analysis (Análise de Intervalos)")
        gap_data = compute_gap_analysis(draws_matrix, cfg["dezenas_total"])
        st.plotly_chart(plot_gap_analysis(gap_data, cfg["dezenas_total"], theme), use_container_width=True)
        overdue_nums = [n for n in range(1, cfg["dezenas_total"] + 1) if gap_data[n]["overdue"]]
        if overdue_nums:
            st.markdown(f"**🔴 Dezenas Overdue (gap > média + 2σ):** {', '.join(str(n) for n in sorted(overdue_nums))}")
            st.caption("Dezenas overdue recebem +20% no score do gerador.")
        col_gap1, col_gap2 = st.columns(2)
        with col_gap1:
            st.markdown("##### 📊 Tabela de Gaps")
            gap_rows = []
            for n in range(1, cfg["dezenas_total"] + 1):
                g = gap_data[n]
                gap_rows.append({
                    "Dezena": n,
                    "Gap Atual": g["current_gap"],
                    "Média": g["mean_gap"],
                    "σ": g["std_gap"],
                    "Z-Score": g["z_score"],
                    "Overdue": "🔴" if g["overdue"] else "",
                    "Prob %": g["prob_next"],
                })
            df_gaps = pd.DataFrame(gap_rows)
            df_gaps = df_gaps.sort_values("Z-Score", ascending=False).reset_index(drop=True)
            st.dataframe(df_gaps, use_container_width=True, hide_index=True)
        with col_gap2:
            st.markdown("##### 🎯 Ranking de Probabilidade")
            st.plotly_chart(plot_prob_ranking(gap_data, cfg["dezenas_total"], theme), use_container_width=True)
        st.markdown("##### 🔍 Timeline Individual")
        selected_num = st.selectbox("Selecione uma dezena para ver o timeline", range(1, cfg["dezenas_total"] + 1), key="gap_timeline_select")
        st.plotly_chart(plot_gap_timeline(gap_data, selected_num, len(draws_matrix), theme), use_container_width=True)
        g_sel = gap_data[selected_num]
        st.caption(f"Dezena {selected_num}: média a cada {g_sel['mean_gap']:.1f} concursos | gap atual: {g_sel['current_gap']} | z-score: {g_sel['z_score']} | prob: {g_sel['prob_next']}%")

    with tab_backtest:
        st.header("🔬 Backtesting & Análise de ROI")
        if "bets" not in st.session_state or not st.session_state["bets"]:
            st.warning("Gere apostas primeiro na aba **Gerador**.")
        else:
            bets = st.session_state["bets"]
            st.info(f"**{len(bets)} apostas** contra **{n_draws} sorteios** do histórico.")
            col_bt1, col_bt2 = st.columns([1, 1])
            with col_bt1:
                if st.button("🧪 Testar no Histórico", type="primary", key="testar_historico_button"):
                    with st.spinner("Executando backtesting com cálculo de ROI..."):
                        results, df_detail, roi_data = run_backtest(bets, draws_matrix, lottery_name)
                        st.session_state["backtest_results"] = results
                        st.session_state["backtest_detail"] = df_detail
                        st.session_state["backtest_roi"] = roi_data
            with col_bt2:
                if st.button("📊 Comparar Estratégias", type="secondary", key="comparar_estrategias_button"):
                    with st.spinner("Comparando as 4 estratégias..."):
                        df_comp = compare_strategies(
                            lottery_name, draws_matrix, n_bets=n_bets,
                            weight_freq=w_freq, weight_delay=w_delay, weight_pairs=w_pairs,
                            trevos_matrix=trevos_matrix, meses_series=meses_series,
                        )
                        st.session_state["df_comparacao"] = df_comp

            if "backtest_results" in st.session_state:
                results = st.session_state["backtest_results"]
                df_detail = st.session_state["backtest_detail"]
                roi_data = st.session_state.get("backtest_roi", {})

                st.plotly_chart(plot_backtest_results(results, theme), use_container_width=True)

                if roi_data:
                    st.markdown("### 💰 Análise Financeira (ROI)")
                    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                    with col_r1:
                        custo_fmt = f"R$ {roi_data['custo_total']:,.2f}"
                        metric_card("Custo Total", custo_fmt, f"{roi_data['n_bets']} ap x {roi_data['n_concursos']} concursos")
                    with col_r2:
                        premios_fmt = f"R$ {roi_data['premios_total']:,.2f}"
                        metric_card("Prêmios Estimados", premios_fmt, "Valores médios históricos")
                    with col_r3:
                        roi_val = roi_data['roi_pct']
                        roi_color = "#28a745" if roi_val >= 0 else "#dc3545"
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-label">ROI</div>
                            <div class="metric-value" style="color:{roi_color};">{roi_val:+.1f}%</div>
                            <div class="metric-sub">Retorno sobre investimento</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_r4:
                        lucro = roi_data['lucro_liquido']
                        lucro_color = "#28a745" if lucro >= 0 else "#dc3545"
                        lucro_fmt = f"R$ {lucro:,.2f}"
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-label">Lucro / Prejuízo</div>
                            <div class="metric-value" style="color:{lucro_color};">{lucro_fmt}</div>
                            <div class="metric-sub">Prêmios - Custo</div>
                        </div>
                        """, unsafe_allow_html=True)
                    st.caption("⚠️ Valores de prêmios são **estimativas médias** baseadas em sorteios históricos. Prêmios reais variam conforme acúmulo e número de ganhadores.")

                col_b1, col_b2 = st.columns([1, 2])
                with col_b1:
                    st.subheader("📊 Resumo de Prêmios")
                    df_res = pd.DataFrame([
                        {"Prêmio": k, "Ocorrências": v}
                        for k, v in results.items() if v > 0
                    ])
                    if not df_res.empty:
                        df_res = df_res.sort_values("Ocorrências", ascending=False).reset_index(drop=True)
                        st.dataframe(df_res, use_container_width=True, hide_index=True)
                    else:
                        st.info("Nenhum prêmio encontrado.")

                with col_b2:
                    st.subheader("📋 Detalhamento")
                    if not df_detail.empty:
                        df_detail_display = df_detail.sort_values(
                            ["Acertos", "Concurso"], ascending=[False, True]
                        ).reset_index(drop=True)
                        st.dataframe(df_detail_display.head(50), use_container_width=True, hide_index=True)
                    else:
                        st.info("Nenhum prêmio encontrado no histórico.")

            if "df_comparacao" in st.session_state:
                st.divider()
                st.markdown("### ⚔️ Comparação de Estratégias (ROI)")
                df_comp = st.session_state["df_comparacao"]
                df_comp_display = df_comp.copy()
                df_comp_display["Custo Total (R$)"] = df_comp_display["Custo Total (R$)"].apply(lambda x: f"R$ {x:,.2f}")
                df_comp_display["Prêmios Total (R$)"] = df_comp_display["Prêmios Total (R$)"].apply(lambda x: f"R$ {x:,.2f}")
                df_comp_display["Lucro/Prejuízo (R$)"] = df_comp_display["Lucro/Prejuízo (R$)"].apply(lambda x: f"R$ {x:,.2f}")
                df_comp_display["ROI %"] = df_comp_display["ROI %"].apply(lambda x: f"{x:+.1f}%")
                st.dataframe(df_comp_display, use_container_width=True, hide_index=True)

                fig_comp = go.Figure()
                colors = ["#28a745" if v >= 0 else "#dc3545" for v in df_comp["ROI %"]]
                fig_comp.add_trace(go.Bar(
                    x=df_comp["Estratégia"],
                    y=df_comp["ROI %"],
                    marker_color=colors,
                    text=[f"{v:+.1f}%" for v in df_comp["ROI %"]],
                    textposition="auto",
                ))
                fig_comp.update_layout(
                    title="ROI por Estratégia (%)",
                    xaxis_title="Estratégia",
                    yaxis_title="ROI %",
                    template="plotly_white",
                    height=350,
                    paper_bgcolor=theme["bg"],
                    plot_bgcolor=theme["bg"],
                    font=dict(color=theme["text"]),
                )
                st.plotly_chart(fig_comp, use_container_width=True)
                st.caption("Verde = ROI positivo (lucro). Vermelho = ROI negativo (prejuízo). Prêmios estimados com valores médios históricos.")

    with tab_dados:
        st.header("📋 Dados do Histórico")
        fonte = st.session_state.get("data_source", "mock/upload")
        st.caption(f"Fonte: {'API Caixa (real)' if fonte == 'caixa' else 'Upload/Mock'} | {len(df_data)} sorteios")
        st.dataframe(df_data.head(100), use_container_width=True)
        if st.checkbox("Mostrar estatísticas descritivas", key="mostrar_estatisticas_check"):
            st.dataframe(df_data.describe(), use_container_width=True)

    st.divider()
    st.markdown(
        f"<div style='text-align:center;opacity:0.6;font-size:0.8rem;'>"
        f"Motor Analítico de Loterias · API Caixa · Quadrantes · Score · Ciclo · Hot/Cold · Gap Analysis · ROI · "
        f"{datetime.now().year} · Jogue com responsabilidade.</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
