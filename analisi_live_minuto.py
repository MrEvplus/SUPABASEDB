import streamlit as st
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

                                                                                                        # Correggiamo % calcolate per Goal post-minuto (Campionato)
                                                                                                        with left:
                                                                                                            st.markdown("### 🕰️ Goal post-minuto (Campionato)")
                                                                                                            intervalli = [(0,15), (16,30), (31,45), (46,60), (61,75), (76,90)]
                                                                                                            goal_count = {f"{i[0]}-{i[1]}":0 for i in intervalli}
                                                                                                            match_con_goal_post = 0
                                                                                                            for _, row in df_matched.iterrows():
                                                                                                                home_goals = extract_minutes(pd.Series([row["minuti goal segnato home"]]))
                                                                                                                away_goals = extract_minutes(pd.Series([row["minuti goal segnato away"]]))
                                                                                                                post_goals = [m for m in home_goals + away_goals if m > current_min]
                                                                                                                if post_goals:
                                                                                                                    match_con_goal_post += 1
                                                                                                                    for g in post_goals:
                                                                                                                        for i in intervalli:
                                                                                                                            if i[0] <= g <= i[1]:
                                                                                                                                goal_count[f"{i[0]}-{i[1]}"] += 1
                                                                                                                                df_goal_post = pd.DataFrame([
                                                                                                                                [k, goal_count[k], f"{(goal_count[k]/match_con_goal_post*100):.2f}%" if match_con_goal_post > 0 else "0.00%"]
                                                                                                                                for k in goal_count
                                                                                                                                ], columns=["Intervallo", "Goal", "%"])
                                                                                                                                st.dataframe(df_goal_post, use_container_width=True)
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

                                                                                                                                            st.markdown(f"### 📊 OVER dal minuto live (Squadra - {team})")
                                                                                                                                            extra_goals = (df_team["Home Goal FT"] + df_team["Away Goal FT"] - (live_h + live_a)).fillna(0)
                                                                                                                                            for thr in [0.5, 1.5, 2.5, 3.5, 4.5]:
                                                                                                                                                st.markdown(f"- **OVER {thr}:** {(extra_goals > thr).mean() * 100:.2f}%")

                                                                                                                                                st.markdown(f"### 📄 Risultati finali (Squadra - {team})")
                                                                                                                                                freq = df_team["Home Goal FT"].astype(str) + "-" + df_team["Away Goal FT"].astype(str)
                                                                                                                                                freq_df = freq.value_counts().rename_axis("Risultato").reset_index(name="Occorrenze")
                                                                                                                                                freq_df["%"] = (freq_df["Occorrenze"] / len(df_team) * 100).round(2)
                                                                                                                                                st.dataframe(freq_df.style.format({"%": "{:.2f}%"}).apply(color_stat_rows, axis=1), use_container_width=True)

                                                                                                                                                with right:
                                                                                                                                                    st.markdown(f"### 🕰️ Goal post-minuto (Squadra - {team})")
                                                                                                                                                    intervalli = [(0,15), (16,30), (31,45), (46,60), (61,75), (76,90)]
                                                                                                                                                    goal_count = {f"{i[0]}-{i[1]}":0 for i in intervalli}
                                                                                                                                                    match_con_goal_post = 0
                                                                                                                                                    for _, row in df_team.iterrows():
                                                                                                                                                        squadra = team.lower()
                                                                                                                                                        avversario = team2.lower()
                                                                                                                                                        home_goals = extract_minutes(pd.Series([row["minuti goal segnato home"]]))
                                                                                                                                                        away_goals = extract_minutes(pd.Series([row["minuti goal segnato away"]]))
                                                                                                                                                        if row["txtechipa1"].lower() == squadra:
                                                                                                                                                            goals = [m for m in home_goals + away_goals if m > current_min]
                                                                                                                                                            else:
                                                                                                                                                                goals = [m for m in away_goals + home_goals if m > current_min]
                                                                                                                                                                if goals:
                                                                                                                                                                    match_con_goal_post += 1
                                                                                                                                                                    for g in goals:
                                                                                                                                                                        for i in intervalli:
                                                                                                                                                                            if i[0] <= g <= i[1]:
                                                                                                                                                                                goal_count[f"{i[0]}-{i[1]}"] += 1
                                                                                                                                                                                df_goal_post_team = pd.DataFrame([
                                                                                                                                                                                [k, goal_count[k], f"{(goal_count[k]/match_con_goal_post*100):.2f}%" if match_con_goal_post > 0 else "0.00%"]
                                                                                                                                                                                for k in goal_count
                                                                                                                                                                                ], columns=["Intervallo", "Goal", "%"])
                                                                                                                                                                                st.dataframe(df_goal_post_team, use_container_width=True)
                                                                                                                                                                                with left:
                                                                                                                                                                                    st.markdown("### 🥅 Primo Goal post-minuto (Campionato)")
                                                                                                                                                                                    st.markdown(f"<i>📌 Analisi basata su partite con risultato {current_result} al minuto {current_min}</i>", unsafe_allow_html=True)
                                                                                                                                                                                    first_goal = {"Home": 0, "Away": 0, "No Goal": 0}
                                                                                                                                                                                    for _, row in df_matched.iterrows():
                                                                                                                                                                                        home_goals = extract_minutes(pd.Series([row["minuti goal segnato home"]]))
                                                                                                                                                                                        away_goals = extract_minutes(pd.Series([row["minuti goal segnato away"]]))
                                                                                                                                                                                        future_home = [m for m in home_goals if m > current_min]
                                                                                                                                                                                        future_away = [m for m in away_goals if m > current_min]
                                                                                                                                                                                        if not future_home and not future_away:
                                                                                                                                                                                            first_goal["No Goal"] += 1
                                                                                                                                                                                            elif future_home and (not future_away or min(future_home) < min(future_away)):
                                                                                                                                                                                                first_goal["Home"] += 1
                                                                                                                                                                                                elif future_away and (not future_home or min(future_away) < min(future_home)):
                                                                                                                                                                                                    first_goal["Away"] += 1
                                                                                                                                                                                                    total = sum(first_goal.values())
                                                                                                                                                                                                    df_first = pd.DataFrame([
                                                                                                                                                                                                    {"Chi Segna": k, "Occorrenze": v, "%": v / total * 100 if total else 0}
                                                                                                                                                                                                    for k, v in first_goal.items()
                                                                                                                                                                                                    ])
                                                                                                                                                                                                    st.dataframe(df_first.style.format({"%": "{:.2f}%"}).apply(color_stat_rows, axis=1), use_container_width=True)

                                                                                                                                                                                                    # 🔍 Sezione: Chi segna per primo dopo questo momento? (Squadra)
                                                                                                                                                                                                    with right:
                                                                                                                                                                                                        st.markdown(f"### 🏟️ Primo Goal post-minuto (Squadra - {team})")
                                                                                                                                                                                                        first_goal = {"Squadra": 0, "Avversario": 0, "No Goal": 0}
                                                                                                                                                                                                        for _, row in df_team.iterrows():
                                                                                                                                                                                                            home_goals = extract_minutes(pd.Series([row["minuti goal segnato home"]]))
                                                                                                                                                                                                            away_goals = extract_minutes(pd.Series([row["minuti goal segnato away"]]))
                                                                                                                                                                                                            future_home = [m for m in home_goals if m > current_min]
                                                                                                                                                                                                            future_away = [m for m in away_goals if m > current_min]
                                                                                                                                                                                                            if not future_home and not future_away:
                                                                                                                                                                                                                first_goal["No Goal"] += 1
                                                                                                                                                                                                                elif future_home and (not future_away or min(future_home) < min(future_away)):
                                                                                                                                                                                                                    primo = "Squadra" if row["Home"] == team else "Avversario"
                                                                                                                                                                                                                    first_goal[primo] += 1
                                                                                                                                                                                                                    elif future_away and (not future_home or min(future_away) < min(future_home)):
                                                                                                                                                                                                                        primo = "Avversario" if row["Home"] == team else "Squadra"
                                                                                                                                                                                                                        first_goal[primo] += 1
                                                                                                                                                                                                                        total = sum(first_goal.values())
                                                                                                                                                                                                                        df_first = pd.DataFrame([
                                                                                                                                                                                                                        {"Chi Segna": k, "Occorrenze": v, "%": v / total * 100 if total else 0}
                                                                                                                                                                                                                        for k, v in first_goal.items()
                                                                                                                                                                                                                        ])
                                                                                                                                                                                                                        st.dataframe(df_first.style.format({"%": "{:.2f}%"}).apply(color_stat_rows, axis=1), use_container_width=True)

                                                                                                                                                                                                                        st.dataframe(tf_df.style.format({"%": "{:.2f}%"}).apply(color_stat_rows, axis=1), use_container_width=True)
                                                                                                                                                                                                                        # ⏱️ Tempo medio del primo goal post-minuto (Campionato)
                                                                                                                                                                                                                        with left:
                                                                                                                                                                                                                            st.markdown("### ⏱️ Tempo medio al primo goal (Campionato)")
                                                                                                                                                                                                                            st.markdown(f"<i>📌 Analisi basata su partite con risultato {current_result} al minuto {current_min}</i>", unsafe_allow_html=True)
                                                                                                                                                                                                                            goal_minutes = []
                                                                                                                                                                                                                            for _, row in df_matched.iterrows():
                                                                                                                                                                                                                                home_goals = extract_minutes(pd.Series([row["minuti goal segnato home"]]))
                                                                                                                                                                                                                                away_goals = extract_minutes(pd.Series([row["minuti goal segnato away"]]))
                                                                                                                                                                                                                                future = sorted([m for m in home_goals + away_goals if m > current_min])
                                                                                                                                                                                                                                if future:
                                                                                                                                                                                                                                    goal_minutes.append(future[0] - current_min)
                                                                                                                                                                                                                                    if goal_minutes:
                                                                                                                                                                                                                                        avg_min = sum(goal_minutes) / len(goal_minutes)
                                                                                                                                                                                                                                        st.write(f"📌 In media, il primo goal arriva dopo **{avg_min:.1f} minuti**")
                                                                                                                                                                                                                                        else:
                                                                                                                                                                                                                                            st.write("⚠️ Nessun goal registrato dopo questo minuto.")

                                                                                                                                                                                                                                            # 📈 Over attesi nei prossimi 15 minuti (Campionato)
                                                                                                                                                                                                                                            with left:
                                                                                                                                                                                                                                                st.markdown("### 📈 Over attesi nei prossimi 15 minuti (Campionato)")
                                                                                                                                                                                                                                                st.markdown(f"<i>📌 Analisi basata su partite con risultato {current_result} al minuto {current_min}</i>", unsafe_allow_html=True)
                                                                                                                                                                                                                                                over_1 = 0
                                                                                                                                                                                                                                                over_2 = 0
                                                                                                                                                                                                                                                for _, row in df_matched.iterrows():
                                                                                                                                                                                                                                                    home_goals = extract_minutes(pd.Series([row["minuti goal segnato home"]]))
                                                                                                                                                                                                                                                    away_goals = extract_minutes(pd.Series([row["minuti goal segnato away"]]))
                                                                                                                                                                                                                                                    future_goals = [m for m in home_goals + away_goals if current_min < m <= current_min + 15]
                                                                                                                                                                                                                                                    if len(future_goals) >= 1:
                                                                                                                                                                                                                                                        over_1 += 1
                                                                                                                                                                                                                                                        if len(future_goals) >= 2:
                                                                                                                                                                                                                                                            over_2 += 1
                                                                                                                                                                                                                                                            total_matches = len(df_matched)
                                                                                                                                                                                                                                                            df_over = pd.DataFrame({
                                                                                                                                                                                                                                                            "Over 0.5 Goal": [over_1, over_1 / total_matches * 100 if total_matches else 0],
                                                                                                                                                                                                                                                            "Over 1.5 Goal": [over_2, over_2 / total_matches * 100 if total_matches else 0],
                                                                                                                                                                                                                                                        }, index=["Occorrenze", "%"])
                                                                                                                                                                                                                                                        st.dataframe(df_over.T.style.format({"%": "{:.2f}"}), use_container_width=True)