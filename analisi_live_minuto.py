mport streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from utils import label_match, extract_minutes

def color_stat_rows(row):
    if row.name == "Matches":
        return ["font-weight: bold; color: black; background-color: transparent"] * len(row)
    return [color_pct(v) for v in row]


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
    live_score = st.text_input("📟 Risultato live (es. 1-1)", "1-1", key="scorelive")
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

    with st.expander("📑 Partite campionato considerate per l'analisi"):
        if not df_matched.empty:
            st.dataframe(
                df_matched[["Stagione", "Data", "Home", "Away", "Home Goal FT", "Away Goal FT",
                            "minuti goal segnato home", "minuti goal segnato away"]]
                .sort_values(["Stagione", "Data"], ascending=[False, False])
                .reset_index(drop=True),
                use_container_width=True
            )

    team = home_team if label.startswith("H_") else away_team
    df_team = df_matched[(df_matched["Home"] == team) | (df_matched["Away"] == team)]

    tf_bands = [(0, 15), (16, 30), (31, 45), (46, 60), (61, 75), (76, 90)]
    tf_labels = [f"{a}-{b}" for a, b in tf_bands]

    left, right = st.columns(2)

    with left:
        st.markdown("### 📊 Statistiche Campionato")
        matches = len(df_matched)
        home_w = (df_matched["Home Goal FT"] > df_matched["Away Goal FT"]).mean() * 100
        draw = (df_matched["Home Goal FT"] == df_matched["Away Goal FT"]).mean() * 100
        loss = (df_matched["Home Goal FT"] < df_matched["Away Goal FT"]).mean() * 100
        df_league_stats = pd.DataFrame({"Campionato": [matches, home_w, draw, loss]}, index=["Matches", "Win %", "Draw %", "Loss %"])
        st.dataframe(df_league_stats.style.format("{:.2f}").apply(color_stat_rows, axis=1), use_container_width=True)

        st.markdown("### 📈 OVER dal minuto live (Campionato)")
        extra_goals = (df_matched["Home Goal FT"] + df_matched["Away Goal FT"] - (live_h + live_a)).fillna(0)
        for thr in [0.5, 1.5, 2.5, 3.5, 4.5]:
            st.markdown(f"- **OVER {thr}:** {(extra_goals > thr).mean() * 100:.2f}%")

        st.markdown("### 📋 Risultati finali (Campionato)")
        freq = df_matched["Home Goal FT"].astype(str) + "-" + df_matched["Away Goal FT"].astype(str)
        freq_df = freq.value_counts().rename_axis("Risultato").reset_index(name="Occorrenze")
        freq_df["%"] = (freq_df["Occorrenze"] / len(df_matched) * 100).round(2)
        st.dataframe(freq_df.style.format({"%": "{:.2f}%"}).apply(color_stat_rows, axis=1), use_container_width=True)

        st.markdown("### ⏱️ Goal post-minuto (Campionato)")
        tf_data = {lbl: 0 for lbl in tf_labels}
        for _, row in df_matched.iterrows():
            for val in extract_minutes(pd.Series([row["minuti goal segnato home"], row["minuti goal segnato away"]])):
                if val > current_min:
                    for lbl, (a, b) in zip(tf_labels, tf_bands):
                        if a < val <= b:
                            tf_data[lbl] += 1
        total = sum(tf_data.values())
        tf_df = pd.DataFrame([{"Intervallo": k, "Goal": v, "%": v / total * 100 if total else 0} for k, v in tf_data.items()])
        st.dataframe(tf_df.style.format({"%": "{:.2f}%"}).apply(color_stat_rows, axis=1), use_container_width=True)

    
with right:
    if label == "SuperCompetitive H<=3 A<=3":
        st.markdown("### 📊 Statistiche Squadre SuperCompetitive (Home vs Away)")
        for team, perspective in [(home_team, "Home"), (away_team, "Away")]:
            df_team = df_matched[(df_matched["Home"] == team) | (df_matched["Away"] == team)]
            t_matches = len(df_team)
            if perspective == "Home":
                win = (df_team["Home Goal FT"] > df_team["Away Goal FT"]).mean() * 100
                draw = (df_team["Home Goal FT"] == df_team["Away Goal FT"]).mean() * 100
                loss = (df_team["Home Goal FT"] < df_team["Away Goal FT"]).mean() * 100
            else:
                win = (df_team["Away Goal FT"] > df_team["Home Goal FT"]).mean() * 100
                draw = (df_team["Away Goal FT"] == df_team["Home Goal FT"]).mean() * 100
                loss = (df_team["Away Goal FT"] < df_team["Home Goal FT"]).mean() * 100
            df_team_stats = pd.DataFrame({team: [t_matches, win, draw, loss]}, index=["Matches", "Win %", "Draw %", "Loss %"])
            st.markdown(f"**{perspective} - {team}**")
            st.dataframe(df_team_stats.style.format("{:.2f}").apply(color_stat_rows, axis=1), use_container_width=True)
    else:
with right:
        st.markdown(f"### 📊 Statistiche Squadra - {team}")
        t_matches = len(df_team)
        if label.startswith("H_"):
            win = (df_team["Home Goal FT"] > df_team["Away Goal FT"]).mean() * 100
            draw = (df_team["Home Goal FT"] == df_team["Away Goal FT"]).mean() * 100
            loss = (df_team["Home Goal FT"] < df_team["Away Goal FT"]).mean() * 100
        else:
            win = (df_team["Away Goal FT"] > df_team["Home Goal FT"]).mean() * 100
            draw = (df_team["Away Goal FT"] == df_team["Home Goal FT"]).mean() * 100
            loss = (df_team["Away Goal FT"] < df_team["Home Goal FT"]).mean() * 100
        df_team_stats = pd.DataFrame({team: [t_matches, win, draw, loss]}, index=["Matches", "Win %", "Draw %", "Loss %"])
        st.dataframe(df_team_stats.style.format("{:.2f}").apply(color_stat_rows, axis=1), use_container_width=True)

        st.markdown("### 📈 OVER dal minuto live (Squadra)")
        extra_goals = (df_team["Home Goal FT"] + df_team["Away Goal FT"] - (live_h + live_a)).fillna(0)
        for thr in [0.5, 1.5, 2.5, 3.5, 4.5]:
            st.markdown(f"- **OVER {thr}:** {(extra_goals > thr).mean() * 100:.2f}%")

        st.markdown("### 📋 Risultati finali (Squadra)")
        freq = df_team["Home Goal FT"].astype(str) + "-" + df_team["Away Goal FT"].astype(str)
        freq_df = freq.value_counts().rename_axis("Risultato").reset_index(name="Occorrenze")
        freq_df["%"] = (freq_df["Occorrenze"] / len(df_team) * 100).round(2)
        st.dataframe(freq_df.style.format({"%": "{:.2f}%"}).apply(color_stat_rows, axis=1), use_container_width=True)

        st.markdown("### ⏱️ Goal post-minuto (Squadra)")
        tf_data = {lbl: 0 for lbl in tf_labels}
        for _, row in df_team.iterrows():
            for val in extract_minutes(pd.Series([row["minuti goal segnato home"], row["minuti goal segnato away"]])):
                if val > current_min:
                    for lbl, (a, b) in zip(tf_labels, tf_bands):
                        if a < val <= b:
                            tf_data[lbl] += 1
        total = sum(tf_data.values())
        tf_df = pd.DataFrame([{"Intervallo": k, "Goal": v, "%": v / total * 100 if total else 0} for k, v in tf_data.items()])
        st.dataframe(tf_df.style.format({"%": "{:.2f}%"}).apply(color_stat_rows, axis=1), use_container_width=True)