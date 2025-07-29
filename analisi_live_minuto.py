import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from utils import label_match, extract_minutes

def color_pct(val):
    try:
        v = float(val)
    except:
        return ""
    if v < 50:
        return "background-color: red; color: black;"
    elif v < 70:
        return "background-color: yellow; color: black;"
    else:
        return "background-color: green; color: black;"

def color_stat_rows(row):
    styles = []
    for col, val in row.items():
        if col == "Matches" and row.name == "Matches":
            styles.append("font-weight: bold; color: black; background-color: transparent")
        elif isinstance(val, float) and ("%" in col or row.name.endswith("%") or col == "%"):
            styles.append(color_pct(val))
        else:
            styles.append("")
    return styles

def run_live_minute_analysis(df):
    st.set_page_config(page_title="Analisi Live Minuto", layout="wide")
    st.title("⏱️ Analisi Live - Cosa succede da questo minuto?")

    col1, col2 = st.columns(2)
    with col1:
        home_team = st.selectbox("🏠 Squadra in casa", sorted(df["Home"].dropna().unique()), key="home_live")
    with col2:
        away_team = st.selectbox("🚪 Squadra in trasferta", sorted(df["Away"].dropna().unique()), key="away_live")

    c1, c2, c3 = st.columns(3)
    with c1:
        odd_home = st.number_input("📈 Quota Home", 1.01, 10.0, 2.00, key="odd_h")
    with c2:
        odd_draw = st.number_input("⚖️ Quota Pareggio", 1.01, 10.0, 3.20, key="odd_d")
    with c3:
        odd_away = st.number_input("📉 Quota Away", 1.01, 10.0, 3.80, key="odd_a")

    current_min = st.slider("⏲️ Minuto attuale", 1, 120, 45, key="minlive")
    live_score = st.text_input("📿 Risultato live (es. 1-1)", "1-1", key="scorelive")
    try:
        live_h, live_a = map(int, live_score.split("-"))
    except:
        st.error("⚠️ Formato risultato non valido. Usa es. `1-1`.")
        return

    label = label_match({"Odd home": odd_home, "Odd Away": odd_away})
    st.markdown(f"🔖 **Label:** `{label}`")
    champ = st.session_state.get("campionato_corrente", df["country"].iloc[0])
    df["Label"] = df.apply(label_match, axis=1)
    df_league = df[(df["country"] == champ) & (df["Label"] == label)]

    matched = []
    for _, r in df_league.iterrows():
        mh = extract_minutes(pd.Series([r.get("minuti goal segnato home", "")]))
        ma = extract_minutes(pd.Series([r.get("minuti goal segnato away", "")]))
        gh = sum(m <= current_min for m in mh)
        ga = sum(m <= current_min for m in ma)
        if gh == live_h and ga == live_a:
            matched.append(r)
    df_matched = pd.DataFrame(matched)
    st.success(f"✅ {len(df_matched)} partite trovate a {live_h}-{live_a}′ al minuto {current_min}’")

    tf_bands = [(0, 15), (16, 30), (31, 45), (46, 60), (61, 75), (76, 90)]
    tf_labels = [f"{a}-{b}" for a, b in tf_bands]

    with st.expander("📁 Partite campionato considerate per l'analisi"):
        if not df_matched.empty:
            st.dataframe(
                df_matched[["Stagione", "Data", "Home", "Away", "Home Goal FT", "Away Goal FT",
                            "minuti goal segnato home", "minuti goal segnato away"]]
                .sort_values(["Stagione", "Data"], ascending=[False, False])
                .reset_index(drop=True),
                use_container_width=True
            )

    team = home_team if label.startswith("H_") else away_team
    matched_team = []
    for _, r in df_league.iterrows():
        if r["Home"] != team and r["Away"] != team:
            continue
        mh = extract_minutes(pd.Series([r.get("minuti goal segnato home", "")]))
        ma = extract_minutes(pd.Series([r.get("minuti goal segnato away", "")]))
        gh = sum(m <= current_min for m in mh)
        ga = sum(m <= current_min for m in ma)
        if gh == live_h and ga == live_a:
            matched_team.append(r)
    df_team = pd.DataFrame(matched_team)

    def generate_post_minute_stats(df_matches, team=None):
        tf_stats = []
        for lbl, (a, b) in zip(tf_labels, tf_bands):
            gf = gs = tf_count = match_with_goal = 0
            for _, row in df_matches.iterrows():
                home = row["Home"]
                away = row["Away"]
                mh = extract_minutes(pd.Series([row["minuti goal segnato home"]]))
                ma = extract_minutes(pd.Series([row["minuti goal segnato away"]]))
                goals = [(m, 'home') for m in mh if m > current_min and a < m <= b] + \
                        [(m, 'away') for m in ma if m > current_min and a < m <= b]
                if goals:
                    tf_count += 1
                gf += sum(1 for m, t in goals if (t == 'home' and (not team or home == team)))
                gs += sum(1 for m, t in goals if (t == 'away' and (not team or home == team)))
                if len(goals) >= 2:
                    match_with_goal += 1
            tf_stats.append({
                "Intervallo": lbl,
                "Goal Fatti": gf,
                "Goal Subiti": gs,
                "% Partite con Goal": round(tf_count / len(df_matches) * 100, 2) if len(df_matches) else 0,
                "Match con ≥2 goal": match_with_goal
            })
        return pd.DataFrame(tf_stats)

    left, right = st.columns(2)
    with left:
        st.markdown("### ⏱️ Goal post-minuto (Campionato)")
        df_stats = generate_post_minute_stats(df_matched)
        st.dataframe(df_stats.style.format({"% Partite con Goal": "{:.2f}%"}).apply(color_stat_rows, axis=1), use_container_width=True)

    with right:
        st.markdown(f"### ⏱️ Goal post-minuto ({team})")
        df_stats_team = generate_post_minute_stats(df_team, team=team)
        st.dataframe(df_stats_team.style.format({"% Partite con Goal": "{:.2f}%"}).apply(color_stat_rows, axis=1), use_container_width=True)
