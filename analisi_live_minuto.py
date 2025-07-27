import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from utils import label_match, extract_minutes

def run_live_minute_analysis(df):
    st.title("⏱️ Analisi Live - Cosa è successo da questo minuto in poi?")
    # --- Input utente ---
    squadra_casa = st.selectbox("🏠 Squadra in casa", sorted(df["Home"].dropna().unique()), key="home_team_live")
    squadra_ospite = st.selectbox("🚪 Squadra fuori casa", sorted(df["Away"].dropna().unique()), key="away_team_live")

    col1, col2, col3 = st.columns(3)
    with col1:
        quota_home = st.number_input("Quota Home", min_value=1.01, step=0.01, value=2.00)
    with col2:
        quota_draw = st.number_input("Quota Draw", min_value=1.01, step=0.01, value=3.20)
    with col3:
        quota_away = st.number_input("Quota Away", min_value=1.01, step=0.01, value=3.80)

    minuto = st.slider("⏱️ Minuto attuale", 1, 120, 60)
    risultato_live = st.text_input("📟 Risultato live (es. 1-1)", "1-1")
    try:
        gh_live, ga_live = map(int, risultato_live.split("-"))
    except:
        st.error("Inserisci un risultato valido, es. 1-1")
        return

    # --- Filtri di base ---
    label = label_match({"Odd home": quota_home, "Odd Away": quota_away})
    st.markdown(f"🔖 **Label:** `{label}`")
    campionato = st.session_state.get("campionato_corrente")
    if not campionato:
        st.warning("Nessun campionato selezionato.")
        return

    df["Label"] = df.apply(label_match, axis=1)
    df0 = df[(df["Label"] == label) & (df["country"] == campionato)].copy()
    if df0.empty:
        st.warning("Nessuna partita trovata per questo Label+Campionato.")
        return

    # --- Match storici con stesso live score al minuto dato ---
    matched = []
    for _, row in df0.iterrows():
        home_goals = extract_minutes(pd.Series([row.get("minuti goal segnato home", "")]))
        away_goals = extract_minutes(pd.Series([row.get("minuti goal segnato away", "")]))
        if sum(m <= minuto for m in home_goals) == gh_live and \
           sum(m <= minuto for m in away_goals) == ga_live:
            matched.append(row)
    if not matched:
        st.warning("Nessun match storico trovato con quel punteggio/minuto.")
        return
    dfm = pd.DataFrame(matched)
    st.success(f"Trovati {len(dfm)} match con punteggio {gh_live}-{ga_live} al {minuto}'")

    # --- Statistiche OVER ---
    thresholds = [0.5, 1.5, 2.5, 3.5, 4.5]
    over_counts = {}
    for t in thresholds:
        over_counts[t] = ( (dfm["Home Goal FT"] + dfm["Away Goal FT"]) - (gh_live + ga_live) > t ).sum()
    st.markdown(f"### 📈 Probabilità OVER dal {minuto}' in poi")
    for t in thresholds:
        pct = round(over_counts[t] / len(dfm) * 100, 2)
        st.markdown(f"- OVER **{t}**: {pct}%")

    # --- Risultati finali più frequenti (campionato) ---
    st.markdown("### 🧾 Risultati Finali più frequenti (campionato)")
    freq = dfm.groupby(["Home Goal FT", "Away Goal FT"]).size().reset_index(name="Occorrenze")
    freq["Risultato"] = freq["Home Goal FT"].astype(str) + "-" + freq["Away Goal FT"].astype(str)
    freq = freq.sort_values("Occorrenze", ascending=False)
    total = freq["Occorrenze"].sum()
    freq["%"] = (freq["Occorrenze"] / total * 100).round(2)
    tab1 = freq[["Risultato", "Occorrenze", "%"]].reset_index(drop=True)
    st.dataframe(tab1.style.format({"%": "{:.2f}%"}), height=300)

    # --- Distribuzione goal per time frame (campionato) ---
    st.markdown("### 📊 Distribuzione Goal per Time Frame (campionato)")
    tf_bands = [(0,15), (16,30), (31,45), (46,60), (61,75), (76,90)]
    labels = [f"{a}-{b}" for a,b in tf_bands]
    counts = {lbl:0 for lbl in labels}
    for _, row in dfm.iterrows():
        all_goals = extract_minutes(pd.Series([row["minuti goal segnato home"]])) + \
                    extract_minutes(pd.Series([row["minuti goal segnato away"]]))
        for m in all_goals:
            if m > minuto:
                for (a,b),lbl in zip(tf_bands, labels):
                    if a < m <= b:
                        counts[lbl] += 1
                        break
    dftf = pd.DataFrame({
        "Time Frame": list(counts.keys()),
        "Goal dopo": list(counts.values())
    })
    dftf["%"] = (dftf["Goal dopo"] / dftf["Goal dopo"].sum() * 100).round(2)
    st.dataframe(dftf.style.format({"%": "{:.2f}%"}), height=300)

    # --- Grafici affiancati ---
    colA, colB = st.columns(2)
    with colA:
        fig1, ax1 = plt.subplots(figsize=(4,3))
        ax1.bar(dftf["Time Frame"], dftf["Goal dopo"], color="skyblue")
        ax1.set_xticklabels(dftf["Time Frame"], rotation=45, ha="right")
        ax1.set_title("Goal per TF (campionato)")
        st.pyplot(fig1)
    with colB:
        fig2, ax2 = plt.subplots(figsize=(4,3))
        ax2.bar(tab1["Risultato"], tab1["Occorrenze"], color="salmon")
        ax2.set_xticklabels(tab1["Risultato"], rotation=45, ha="right")
        ax2.set_title("Freq Risultati (campionato)")
        st.pyplot(fig2)

    # =============================================================================
    # ‼️ Ripeti tutto in verticale per la SQUADRA SELEZIONATA
    # =============================================================================
    st.markdown("---")
    st.markdown(f"## ⚔️ Analisi specifica per **{squadra_casa if label.startswith('H_') else squadra_ospite}**")
    target = squadra_casa if label.startswith("H_") else squadra_ospite
    df_team = dfm[(dfm["Home"]==target) | (dfm["Away"]==target)].copy()
    if df_team.empty:
        st.info("Nessuna partita per la squadra selezionata in questo scenario.")
        return

    # -- OVER per squadra
    oc = {}
    for t in thresholds:
        oc[t] = ((df_team["Home Goal FT"] + df_team["Away Goal FT"]) - (gh_live + ga_live) > t).sum()
    st.markdown(f"### 📈 OVER dal {minuto}' per {target}")
    for t in thresholds:
        pct = round(oc[t] / len(df_team) * 100, 2)
        st.markdown(f"- OVER **{t}**: {pct}%")

    # -- Tabella risultati (squadra)
    st.markdown(f"### 🧾 Risultati Finali più frequenti ({target})")
    fr = df_team.groupby(["Home Goal FT", "Away Goal FT"]).size().reset_index(name="Occorrenze")
    fr["Risultato"] = fr["Home Goal FT"].astype(str) + "-" + fr["Away Goal FT"].astype(str)
    fr = fr.sort_values("Occorrenze", ascending=False)
    tot2 = fr["Occorrenze"].sum()
    fr["%"] = (fr["Occorrenze"]/tot2 *100).round(2)
    tab2 = fr[["Risultato","Occorrenze","%"]].reset_index(drop=True)
    st.dataframe(tab2.style.format({"%":"{:.2f}%"}), height=300)

    # -- Distribuzione TF (squadra)
    st.markdown(f"### 📊 Distribuzione Goal per TF ({target})")
    cnt2 = {lbl:0 for lbl in labels}
    for _, row in df_team.iterrows():
        ag = extract_minutes(pd.Series([row["minuti goal segnato home"]])) + \
             extract_minutes(pd.Series([row["minuti goal segnato away"]]))
        for m in ag:
            if m > minuto:
                for (a,b),lbl in zip(tf_bands, labels):
                    if a < m <= b:
                        cnt2[lbl]+=1; break
    dft2 = pd.DataFrame({
        "Time Frame": labels,
        "Goal dopo": [cnt2[l] for l in labels]
    })
    dft2["%"] = (dft2["Goal dopo"]/dft2["Goal dopo"].sum()*100).round(2)
    st.dataframe(dft2.style.format({"%":"{:.2f}%"}), height=300)

    # -- Grafici affiancati per squadra
    colC, colD = st.columns(2)
    with colC:
        fig3, ax3 = plt.subplots(figsize=(4,3))
        ax3.bar(dft2["Time Frame"], dft2["Goal dopo"], color="lightgreen")
        ax3.set_xticklabels(dft2["Time Frame"], rotation=45, ha="right")
        ax3.set_title(f"TF per {target}")
        st.pyplot(fig3)
    with colD:
        fig4, ax4 = plt.subplots(figsize=(4,3))
        ax4.bar(tab2["Risultato"], tab2["Occorrenze"], color="orange")
        ax4.set_xticklabels(tab2["Risultato"], rotation=45, ha="right")
        ax4.set_title(f"Risultati {target}")
        st.pyplot(fig4)
