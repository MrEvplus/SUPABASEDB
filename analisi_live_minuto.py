
import streamlit as st
import pandas as pd
from utils import label_match, extract_minutes

def run_live_minute_analysis(df):
    st.title("⏱️ Analisi Live - Cosa è successo da questo minuto in poi?")

    squadra_casa = st.selectbox("🏠 Squadra in casa", sorted(df["Home"].dropna().unique()), key="home_team_live")
    squadra_ospite = st.selectbox("🚪 Squadra fuori casa", sorted(df["Away"].dropna().unique()), key="away_team_live")

    col1, col2, col3 = st.columns(3)
    with col1:
        quota_home = st.number_input("Quota Home", min_value=1.01, step=0.01, value=2.00)
    with col2:
        quota_draw = st.number_input("Quota Draw", min_value=1.01, step=0.01, value=3.20)
    with col3:
        quota_away = st.number_input("Quota Away", min_value=1.01, step=0.01, value=3.80)

    minuto_corrente = st.slider("⏱️ Minuto attuale", min_value=1, max_value=120, value=60)
    risultato_live = st.text_input("📟 Risultato live (es. 1-1)", value="1-1")

    try:
        goal_home_live, goal_away_live = map(int, risultato_live.strip().split("-"))
    except:
        st.error("⚠️ Inserisci un risultato valido (es. 1-1).")
        return

    label = label_match({"Odd home": quota_home, "Odd Away": quota_away})
    st.markdown(f"🔖 **Label identificato:** `{label}`")

    db_selected = st.session_state.get("campionato_corrente")
    if not db_selected:
        st.warning("⚠️ Nessun campionato selezionato.")
        return

    df["Label"] = df.apply(label_match, axis=1)
    df_filtered = df[(df["Label"] == label) & (df["country"] == db_selected)].copy()

    if df_filtered.empty:
        st.warning("⚠️ Nessuna partita trovata con questo Label e campionato.")
        return

    matched_rows = []
    for _, row in df_filtered.iterrows():
        home_goals = extract_minutes(pd.Series([row.get("minuti goal segnato home", "")]))
        away_goals = extract_minutes(pd.Series([row.get("minuti goal segnato away", "")]))
        goals_home_up_to = sum(1 for m in home_goals if m <= minuto_corrente)
        goals_away_up_to = sum(1 for m in away_goals if m <= minuto_corrente)

        if goals_home_up_to == goal_home_live and goals_away_up_to == goal_away_live:
            matched_rows.append(row)

    if not matched_rows:
        st.warning("❌ Nessuna partita storica trovata con questo punteggio live al minuto selezionato.")
        return

    df_matched = pd.DataFrame(matched_rows)
    st.success(f"✅ Trovate {len(df_matched)} partite con punteggio {goal_home_live}-{goal_away_live} al minuto {minuto_corrente}")

    goal_dopo = 0
    over_stats = {1.5: 0, 2.5: 0, 3.5: 0, 4.5: 0}
    final_scores = []
    tf_bands = [(0,15), (16,30), (31,45), (46,60), (61,75), (76,90)]
    tf_labels = [f"{a}-{b}" for a,b in tf_bands[:-1]] + ["76-90+"]
    tf_counts = {k:0 for k in tf_labels}
    tf_fatti = {k:0 for k in tf_labels}
    tf_subiti = {k:0 for k in tf_labels}

    for _, row in df_matched.iterrows():
        home_goals = extract_minutes(pd.Series([row.get("minuti goal segnato home", "")]))
        away_goals = extract_minutes(pd.Series([row.get("minuti goal segnato away", "")]))

        post_goals = [m for m in home_goals + away_goals if m > minuto_corrente]
        if post_goals:
            goal_dopo += 1

        for m in home_goals:
            for i, (a, b) in enumerate(tf_bands):
                if a < m <= b:
                    tf_counts[tf_labels[i]] += 1
                    tf_fatti[tf_labels[i]] += 1
                    break
        for m in away_goals:
            for i, (a, b) in enumerate(tf_bands):
                if a < m <= b:
                    tf_counts[tf_labels[i]] += 1
                    tf_subiti[tf_labels[i]] += 1
                    break
            for i, (a, b) in enumerate(tf_bands):
                if a < m <= b:
                    tf_counts[tf_labels[i]] += 1
                    break

        total_goals = row["Home Goal FT"] + row["Away Goal FT"]
        for soglia in over_stats:
            if total_goals > soglia:
                over_stats[soglia] += 1

        final_scores.append(f"{int(row['Home Goal FT'])}-{int(row['Away Goal FT'])}")

    st.markdown(f"📊 **% Partite con almeno 1 goal dopo il minuto {minuto_corrente}:** `{round(goal_dopo/len(df_matched)*100,2)}%`")

    for soglia in over_stats:
        pct = round(over_stats[soglia] / len(df_matched) * 100, 2)
        st.markdown(f"📈 OVER {soglia}: **{pct}%**")

    st.markdown("### 🧾 Risultati Finali più frequenti")
    final_series = pd.Series(final_scores).value_counts().reset_index()
    final_series.columns = ["Risultato", "Occorrenze"]
    st.dataframe(final_series)

    st.markdown("### ⏱️ Distribuzione Goal per Time Frame")
    tf_df = pd.DataFrame({
        "Time Frame": list(tf_counts.keys()),
        "Goal Totali": list(tf_counts.values()),
        "Goal Fatti": list(tf_fatti.values()),
        "Goal Subiti": list(tf_subiti.values())
    })
    tf_df["%"] = round((tf_df["Goal Totali"] / tf_df["Goal Totali"].sum()) * 100, 2)
    st.dataframe(tf_df)

    # 📊 Grafico a barre con percentuali
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(tf_df["Time Frame"], tf_df["Goal Totali"], color='skyblue')
    for i, val in enumerate(tf_df["%"]):
        ax.text(i, tf_df["Goal Totali"][i] + 0.3, f"{val}%", ha='center', fontsize=9, fontweight='bold')

    ax.set_title("Distribuzione Goal per Time Frame", fontsize=13)
    ax.set_ylabel("Goal Segnati")
    ax.set_ylim(0, tf_df["Goal Totali"].max() + 2)
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    st.pyplot(fig)

    # 📊 Grafico doppio Fatti/Subiti
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    x = tf_df["Time Frame"]
    ax2.bar(x, tf_df["Goal Fatti"], label="Fatti", color='green', alpha=0.7)
    ax2.bar(x, tf_df["Goal Subiti"], bottom=tf_df["Goal Fatti"], label="Subiti", color='red', alpha=0.5)
    ax2.set_title("Distribuzione Goal per Time Frame (Fatti + Subiti)")
    ax2.set_ylabel("Goal Totali")
    ax2.legend()
    st.pyplot(fig2)


    # 👇 Partite della squadra selezionata
    st.markdown("### 📋 Partite storiche con stesso scenario")
    squadra_target = squadra_casa if label.startswith("H_") else squadra_ospite
    df_squadra = df_matched[
        (df_matched["Home"] == squadra_target) | (df_matched["Away"] == squadra_target)
    ].copy()
    df_squadra["Risultato"] = df_squadra["Home Goal FT"].astype(str) + "-" + df_squadra["Away Goal FT"].astype(str)
    st.dataframe(df_squadra.sort_values(by="Stagione", ascending=False).reset_index(drop=True))

    # 🔍 Statistiche solo sulle partite della squadra selezionata
    st.markdown("### 📊 Statistiche Partite Squadra Selezionata (post-minuto selezionato)")
    post_goals_sq = 0
    over_stats_sq = {1.5: 0, 2.5: 0, 3.5: 0, 4.5: 0}
    final_scores_sq = []
    tf_counts_sq = {k:0 for k in tf_labels}
    tf_fatti_sq = {k:0 for k in tf_labels}
    tf_subiti_sq = {k:0 for k in tf_labels}

    for _, row in df_squadra.iterrows():
        home_goals = extract_minutes(pd.Series([row.get("minuti goal segnato home", "")]))
        away_goals = extract_minutes(pd.Series([row.get("minuti goal segnato away", "")]))
        all_goals = home_goals + away_goals

        post_goals_m45 = [m for m in all_goals if m > 45]
        if post_goals_m45:
            post_goals_sq += 1

        total_goals = row["Home Goal FT"] + row["Away Goal FT"]
        for soglia in over_stats_sq:
            if total_goals > soglia:
                over_stats_sq[soglia] += 1

        for m in home_goals:
            for i, (a, b) in enumerate(tf_bands):
                if a < m <= b:
                    tf_counts_sq[tf_labels[i]] += 1
                    tf_fatti_sq[tf_labels[i]] += 1
                    break
        for m in away_goals:
            for i, (a, b) in enumerate(tf_bands):
                if a < m <= b:
                    tf_counts_sq[tf_labels[i]] += 1
                    tf_subiti_sq[tf_labels[i]] += 1
                    break
            for i, (a, b) in enumerate(tf_bands):
                if a < m <= b:
                    tf_counts_sq[tf_labels[i]] += 1
                    break

        final_scores_sq.append(f"{int(row['Home Goal FT'])}-{int(row['Away Goal FT'])}")

    n_sq = len(df_squadra)
    st.markdown(f"📊 % Partite con almeno 1 goal dopo il minuto 45: **{round(post_goals_sq / n_sq * 100, 2)}%**")
    for soglia in over_stats_sq:
        pct = round(over_stats_sq[soglia] / n_sq * 100, 2)
        st.markdown(f"📈 OVER {soglia}: **{pct}%**")

    st.markdown("### 🧾 Risultati Finali più frequenti")
    final_sq = pd.Series(final_scores_sq).value_counts().reset_index()
    final_sq.columns = ["Risultato", "Occorrenze"]
    st.dataframe(final_sq)

    st.markdown("### ⏱️ Distribuzione Goal per Time Frame")
    tf_df_sq = pd.DataFrame({
        "Time Frame": list(tf_counts_sq.keys()),
        "Goal Totali": list(tf_counts_sq.values()),
        "Goal Fatti": list(tf_fatti_sq.values()),
        "Goal Subiti": list(tf_subiti_sq.values())
    })
    tf_df_sq["%"] = round((tf_df_sq["Goal Totali"] / tf_df_sq["Goal Totali"].sum()) * 100, 2)
    st.dataframe(tf_df_sq)

    # 📊 Grafico a barre anche per la squadra selezionata
    import matplotlib.pyplot as plt
    fig_sq, ax_sq = plt.subplots(figsize=(10, 4))
    bars_sq = ax_sq.bar(tf_df_sq["Time Frame"], tf_df_sq["Goal Totali"], color='salmon')
    for i, val in enumerate(tf_df_sq["%"]):
        ax_sq.text(i, tf_df_sq["Goal Totali"][i] + 0.3, f"{val}%", ha='center', fontsize=9, fontweight='bold')

    ax_sq.set_title("Distribuzione Goal per Time Frame - Squadra", fontsize=13)
    ax_sq.set_ylabel("Goal Segnati")
    ax_sq.set_ylim(0, tf_df_sq["Goal Totali"].max() + 2)
    ax_sq.grid(axis='y', linestyle='--', alpha=0.5)
    st.pyplot(fig_sq)

    # 📊 Grafico doppio Fatti/Subiti - Squadra
    fig3, ax3 = plt.subplots(figsize=(10, 5))
    x_sq = tf_df_sq["Time Frame"]
    ax3.bar(x_sq, tf_df_sq["Goal Fatti"], label="Fatti", color='green', alpha=0.7)
    ax3.bar(x_sq, tf_df_sq["Goal Subiti"], bottom=tf_df_sq["Goal Fatti"], label="Subiti", color='red', alpha=0.5)
    ax3.set_title("Distribuzione Goal Squadra per Time Frame (Fatti + Subiti)")
    ax3.set_ylabel("Goal Totali")
    ax3.legend()
    st.pyplot(fig3)
