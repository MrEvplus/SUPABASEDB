
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
        goal_home, goal_away = map(int, risultato_live.strip().split("-"))
    except:
        st.error("⚠️ Inserisci un risultato valido (es. 1-1).")
        return

    label = label_match({"Odd home": quota_home, "Odd Away": quota_away})
    st.markdown(f"🔖 **Label identificato:** `{label}`")

    st.markdown("## 🔎 1. Analisi Storica - Campionato & Label")
    df["Label"] = df.apply(label_match, axis=1)
    df_filtrato = df[df["Label"] == label].copy()
    df_filtrato["TotGol"] = df_filtrato["Home Goal FT"] + df_filtrato["Away Goal FT"]
    df_filtrato["score_ft"] = df_filtrato["Home Goal FT"].astype(int).astype(str) + "-" + df_filtrato["Away Goal FT"].astype(int).astype(str)

    df_minuto = df_filtrato[
        (df_filtrato["Home Goal FT"] >= goal_home) &
        (df_filtrato["Away Goal FT"] >= goal_away)
    ]

    st.write(f"🧮 Partite storiche filtrate per questo Label: {len(df_minuto)}")

    # Calcolo % goal dopo il minuto corrente
    partite_con_goal_dopo = 0
    for _, row in df_minuto.iterrows():
        minuti = extract_minutes(pd.Series([row["minuti goal segnato home"]])) + extract_minutes(pd.Series([row["minuti goal segnato away"]]))
        if any(m > minuto_corrente for m in minuti):
            partite_con_goal_dopo += 1
    pct_goal_dopo = round(partite_con_goal_dopo / len(df_minuto) * 100, 2) if len(df_minuto) > 0 else 0
    st.success(f"📍 Nel {pct_goal_dopo}% dei casi c'è stato un goal dopo il minuto {minuto_corrente}")

    for soglia in [1.5, 2.5, 3.5, 4.5]:
        pct_over = round((df_minuto["TotGol"] > soglia).mean() * 100, 2)
        st.markdown(f"📈 OVER {soglia}: **{pct_over}%**")

    # Tabella risultati finali
    st.markdown("### 🧾 Risultati Finali più frequenti")
    st.dataframe(df_minuto["score_ft"].value_counts().head(10).rename("Occorrenze"))

    # Time Frame Table
    st.markdown("### ⏲️ Distribuzione Goal per Time Frame (Campionato & Label)")
    tf_bands = [(0,15), (16,30), (31,45), (46,60), (61,75), (76,120)]
    tf_labels = [f"{a}-{b}" for a,b in tf_bands]
    tf_counts = {k:0 for k in tf_labels}

    for _, row in df_minuto.iterrows():
        minutes = extract_minutes(pd.Series([row["minuti goal segnato home"]])) + extract_minutes(pd.Series([row["minuti goal segnato away"]]))
        for m in minutes:
            for a,b in tf_bands:
                if a < m <= b:
                    tf_counts[f"{a}-{b}"] += 1
                    break
    tf_df = pd.DataFrame(list(tf_counts.items()), columns=["Time Frame", "Goal Segnati"])
    st.dataframe(tf_df)

    # Analisi squadre
    st.markdown("## 🧠 2. Analisi per Squadre Selezionate")
    df_squadre = df[
        ((df["Home"] == squadra_casa) & (df["Away"] == squadra_ospite)) |
        ((df["Home"] == squadra_ospite) & (df["Away"] == squadra_casa))
    ]
    df_squadre = df_squadre[df_squadre["Label"] == label]
    df_squadre = df_squadre[
        (df_squadre["Home Goal FT"] >= goal_home) &
        (df_squadre["Away Goal FT"] >= goal_away)
    ]

    if df_squadre.empty:
        st.warning("⚠️ Nessun match storico trovato tra le due squadre con questo Label e parziale.")
    else:
        st.write(f"🎯 Match filtrati tra le due squadre con Label `{label}`: {len(df_squadre)}")
        count_goal_late = 0
        for _, row in df_squadre.iterrows():
            minuti = extract_minutes(pd.Series([row["minuti goal segnato home"]])) + extract_minutes(pd.Series([row["minuti goal segnato away"]]))
            if any(m > minuto_corrente for m in minuti):
                count_goal_late += 1
        pct_squadre = round(count_goal_late / len(df_squadre) * 100, 2)
        st.markdown(f"📊 % match con goal dopo il {minuto_corrente}: **{pct_squadre}%**")

        df_squadre["TotGol"] = df_squadre["Home Goal FT"] + df_squadre["Away Goal FT"]
        for soglia in [1.5, 2.5, 3.5, 4.5]:
            pct = round((df_squadre["TotGol"] > soglia).mean() * 100, 2)
            st.markdown(f"📈 OVER {soglia} [solo squadre]: **{pct}%**")

    # Sintesi
    st.markdown("## 🧮 3. Sintesi Probabilistica")
    if pct_goal_dopo >= 60 or (df_squadre is not None and not df_squadre.empty and pct_squadre >= 60):
        st.success("✅ Goal probabile nel finale, in base a storico campionato + matchup squadre.")
    else:
        st.warning("⚠️ Match spesso bloccato dopo questo momento nei dati storici.")
