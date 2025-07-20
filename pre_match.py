import streamlit as st
import pandas as pd
from utils import label_match
from squadre import compute_team_macro_stats
from macros import run_macro_stats

# --------------------------------------------------------
# FUNZIONE PER OTTENERE LEAGUE DATA BY LABEL
# --------------------------------------------------------
def get_league_data_by_label(df, label):
    if "Label" not in df.columns:
        df = df.copy()
        df["Label"] = df.apply(label_match, axis=1)

    df["match_result"] = df.apply(
        lambda row: "Home Win" if row["Home Goal FT"] > row["Away Goal FT"]
        else "Away Win" if row["Home Goal FT"] < row["Away Goal FT"]
        else "Draw",
        axis=1
    )

    group_label = df.groupby("Label").agg(
        Matches=("Home", "count"),
        HomeWin_pct=("match_result", lambda x: (x == "Home Win").mean() * 100),
        Draw_pct=("match_result", lambda x: (x == "Draw").mean() * 100),
        AwayWin_pct=("match_result", lambda x: (x == "Away Win").mean() * 100)
    ).reset_index()

    row = group_label[group_label["Label"] == label]
    if not row.empty:
        return row.iloc[0].to_dict()
    else:
        return None

# --------------------------------------------------------
# LABEL FROM ODDS
# --------------------------------------------------------
def label_from_odds(home_odd, away_odd):
    fake_row = {
        "Odd home": home_odd,
        "Odd Away": away_odd
    }
    return label_match(fake_row)

# --------------------------------------------------------
# DETERMINA TIPO DI LABEL
# --------------------------------------------------------
def get_label_type(label):
    if label and label.startswith("H_"):
        return "Home"
    elif label and label.startswith("A_"):
        return "Away"
    else:
        return "Both"

# --------------------------------------------------------
# FORMATTING COLORE
# --------------------------------------------------------
def format_value(val, is_roi=False):
    if val is None:
        val = 0
    suffix = "%" if is_roi else ""
    if val > 0:
        return f"🟢 +{val:.2f}{suffix}"
    elif val < 0:
        return f"🔴 {val:.2f}{suffix}"
    else:
        return f"0.00{suffix}"

# --------------------------------------------------------
# CALCOLO BACK / LAY STATS (con commissione e filtro quote)
# --------------------------------------------------------
def calculate_back_lay(filtered_df):
    commission = 0.045
    profits_back = {"HOME": 0, "DRAW": 0, "AWAY": 0}
    profits_lay = {"HOME": 0, "DRAW": 0, "AWAY": 0}
    matches = 0
    excluded = 0

    for _, row in filtered_df.iterrows():
        odds = {
            "HOME": row.get("Odd home", None),
            "DRAW": row.get("Odd Draw", None),
            "AWAY": row.get("Odd Away", None)
        }

        if any(pd.isna(odds[o]) or odds[o] <= 1.01 for o in odds):
            excluded += 1
            continue

        h_goals = row["Home Goal FT"]
        a_goals = row["Away Goal FT"]

        result = (
            "HOME" if h_goals > a_goals else
            "AWAY" if h_goals < a_goals else
            "DRAW"
        )

        matches += 1

        for outcome in ["HOME", "DRAW", "AWAY"]:
            price = odds[outcome]
            if result == outcome:
                profit = price - 1
                net_profit = profit * (1 - commission)
                profits_back[outcome] += net_profit
            else:
                profits_back[outcome] -= 1

            stake = 1 / (price - 1)
            if result != outcome:
                profits_lay[outcome] += stake
            else:
                profits_lay[outcome] -= 1

    rois_back = {}
    rois_lay = {}
    for outcome in ["HOME", "DRAW", "AWAY"]:
        if matches > 0:
            rois_back[outcome] = round((profits_back[outcome] / matches) * 100, 2)
            rois_lay[outcome] = round((profits_lay[outcome] / matches) * 100, 2)
        else:
            rois_back[outcome] = 0
            rois_lay[outcome] = 0

    if excluded > 0:
        st.info(f"ℹ️ {excluded} partite escluse dal calcolo ROI per quote nulle o <= 1.01")

    return profits_back, rois_back, profits_lay, rois_lay, matches

# --------------------------------------------------------
# ROI Over/Under 2.5 per Label
# --------------------------------------------------------
def calculate_over_under_roi(df, label, over_quote, under_quote):
    commission = 0.045
    filtered = df[df["Label"] == label].copy()
    filtered = filtered[(filtered["Home Goal FT"].notna()) & (filtered["Away Goal FT"].notna())]

    total = 0
    profit_over = 0
    profit_under = 0
    over_hits = 0
    under_hits = 0

    for _, row in filtered.iterrows():
        goals = row["Home Goal FT"] + row["Away Goal FT"]
        if over_quote <= 1.01 or under_quote <= 1.01:
            continue
        total += 1
        if goals > 2.5:
            over_hits += 1
            profit_over += (over_quote - 1) * (1 - commission)
            profit_under -= 1
        else:
            under_hits += 1
            profit_under += (under_quote - 1) * (1 - commission)
            profit_over -= 1

    if total == 0:
        return None

    return {
        "Matches": total,
        "% Over": round((over_hits / total) * 100, 2),
        "% Under": round((under_hits / total) * 100, 2),
        "ROI Over": round((profit_over / total) * 100, 2),
        "ROI Under": round((profit_under / total) * 100, 2),
        "Profit Over": round(profit_over, 2),
        "Profit Under": round(profit_under, 2),
    }
