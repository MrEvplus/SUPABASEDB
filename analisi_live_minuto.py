
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

    minuto_corrente = st.slider("⏱️ Minuto attuale", min_value=1, max_value=120, value=5)
    risultato_live = st.text_input("📟 Risultato live (es. 1-0)", value="1-0")

    try:
        goal_home, goal_away = map(int, risultato_live.strip().split("-"))
    except:
        st.error("⚠️ Inserisci un risultato valido (es. 1-0).")
        return

    label = label_match({"Odd home": quota_home, "Odd Away": quota_away})
    st.markdown(f"🔖 **Label identificato:** `{label}`")

    db_selected = st.session_state.get("campionato_corrente")
    if not db_selected:
        st.warning("⚠️ Nessun campionato selezionato.")
        return

    df["Label"] = df.apply(label_match, axis=1)
    df_filtered = df[(df["Label"] == label) & (df["country"] == db_selected)].copy()

    is_away_fav = label.startswith("A_")
    is_home_fav = label.startswith("H_")

    if is_home_fav:
        df_filtered = df_filtered[
            (df_filtered["Home"] == squadra_casa) &
            (df_filtered["Home Goal FT"] == goal_home)
        ]
    elif is_away_fav:
        df_filtered = df_filtered[
            (df_filtered["Away"] == squadra_ospite) &
            (df_filtered["Away Goal FT"] == goal_away)
        ]
    else:
        df_filtered = df_filtered[
            (df_filtered["Home Goal FT"] == goal_home) &
            (df_filtered["Away Goal FT"] == goal_away)
        ]

    st.markdown("## 🔎 Analisi Storica - Campionato, Label e Gol esatti nel minuto selezionato")
    st.write(f"📂 Partite trovate: {len(df_filtered)}")

    partite_con_goal_dopo = 0
    for _, row in df_filtered.iterrows():
        minuti = extract_minutes(pd.Series([row["minuti goal segnato home"]])) + extract_minutes(pd.Series([row["minuti goal segnato away"]]))
        if any(m > minuto_corrente for m in minuti):
            partite_con_goal_dopo += 1

    pct_goal_dopo = round(partite_con_goal_dopo / len(df_filtered) * 100, 2) if len(df_filtered) > 0 else 0
    st.success(f"📍 Nel {pct_goal_dopo}% dei casi c'è stato un goal DOPO il minuto {minuto_corrente}")

    df_filtered["TotGol"] = df_filtered["Home Goal FT"] + df_filtered["Away Goal FT"]
    for soglia in [1.5, 2.5, 3.5, 4.5]:
        pct_over = round((df_filtered["TotGol"] > soglia).mean() * 100, 2)
        st.markdown(f"📈 OVER {soglia}: **{pct_over}%**")

    tf_bands = [(0,15), (16,30), (31,45), (46,60), (61,75), (76,120)]
    tf_labels = [f"{a}-{b}" for a,b in tf_bands]
    tf_counts = {k:0 for k in tf_labels}

    for _, row in df_filtered.iterrows():
        minuti = extract_minutes(pd.Series([row["minuti goal segnato home"]])) + extract_minutes(pd.Series([row["minuti goal segnato away"]]))
        for m in minuti:
            for a,b in tf_bands:
                if a < m <= b:
                    tf_counts[f"{a}-{b}"] += 1
                    break

    tf_df = pd.DataFrame(list(tf_counts.items()), columns=["Time Frame", "Goal Segnati"])
    st.markdown("### 🧮 Distribuzione Goal per Time Frame")
    st.dataframe(tf_df)
