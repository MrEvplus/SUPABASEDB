
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
    st.markdown(f"🔖 **Label identificato**: `{label}`")

    df["Label"] = df.apply(label_match, axis=1)
    df_filtrato = df[df["Label"] == label].copy()
    df_filtrato["goals_home"] = df_filtrato["Home Goal FT"]
    df_filtrato["goals_away"] = df_filtrato["Away Goal FT"]
    df_filtrato["score_ft"] = df_filtrato["goals_home"].astype(int).astype(str) + "-" + df_filtrato["goals_away"].astype(int).astype(str)

    df_minuto = df_filtrato[
        (df_filtrato["Home Goal FT"] >= goal_home) &
        (df_filtrato["Away Goal FT"] >= goal_away)
    ]

    st.markdown("### 📊 Analisi Storica dal Minuto Selezionato")
    st.write(f"⚙️ Partite analizzate con Label `{label}` e risultato parziale ≥ {goal_home}-{goal_away}: {len(df_minuto)}")

    goal_dopo_minuto = 0
    for idx, row in df_minuto.iterrows():
        min_h = extract_minutes(pd.Series([row["minuti goal segnato home"]]))
        min_a = extract_minutes(pd.Series([row["minuti goal segnato away"]]))
        all_minuti = min_h + min_a
        if any(m > minuto_corrente for m in all_minuti):
            goal_dopo_minuto += 1

    pct = round(goal_dopo_minuto / len(df_minuto) * 100, 2) if len(df_minuto) > 0 else 0
    st.success(f"📍 Nel {pct}% dei casi c'è stato un goal dopo il minuto {minuto_corrente}")

    df_minuto["TotGol"] = df_minuto["Home Goal FT"] + df_minuto["Away Goal FT"]
    for soglia in [1.5, 2.5, 3.5, 4.5]:
        pct_over = round((df_minuto["TotGol"] > soglia).mean() * 100, 2)
        st.markdown(f"📈 % OVER {soglia}: **{pct_over}%**")

    top_scores = df_minuto["score_ft"].value_counts().head(5)
    st.markdown("### 🔚 Risultati Finali più frequenti")
    st.dataframe(top_scores.rename("Occorrenze"))

    df_squadre = df[
        ((df["Home"] == squadra_casa) & (df["Away"] == squadra_ospite)) |
        ((df["Home"] == squadra_ospite) & (df["Away"] == squadra_casa))
    ]
    df_squadre = df_squadre[
        (df_squadre["Home Goal FT"] >= goal_home) &
        (df_squadre["Away Goal FT"] >= goal_away)
    ]

    st.markdown("---")
    st.markdown("## 🧠 Analisi Specifica per le Squadre Selezionate")

    if df_squadre.empty:
        st.warning("⚠️ Nessun match storico trovato tra le due squadre con quel risultato parziale.")
    else:
        goal_squadre = 0
        for idx, row in df_squadre.iterrows():
            min_h = extract_minutes(pd.Series([row["minuti goal segnato home"]]))
            min_a = extract_minutes(pd.Series([row["minuti goal segnato away"]]))
            all_minuti = min_h + min_a
            if any(m > minuto_corrente for m in all_minuti):
                goal_squadre += 1

        pct_goal = round(goal_squadre / len(df_squadre) * 100, 2)
        st.markdown(f"📊 % goal dopo il {minuto_corrente}': **{pct_goal}%**")

        df_squadre["TotGol"] = df_squadre["Home Goal FT"] + df_squadre["Away Goal FT"]
        for soglia in [1.5, 2.5, 3.5, 4.5]:
            pct_over_sq = round((df_squadre["TotGol"] > soglia).mean() * 100, 2)
            st.markdown(f"📈 [SQUADRE] % OVER {soglia}: **{pct_over_sq}%**")

    st.markdown("---")
    st.markdown("## 🤖 Sintesi Probabilistica")

    if goal_dopo_minuto > 0:
        st.markdown("✅ **Goal probabile nel finale** in base a storico generale e matchup.")
    else:
        st.markdown("⚠️ **Match storicamente bloccato dopo questo momento.**")
