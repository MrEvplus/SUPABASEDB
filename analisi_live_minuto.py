import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from utils import label_match, extract_minutes

def run_live_minute_analysis(df):
    st.set_page_config(page_title="Analisi Live Minuto", layout="wide")
    st.title("⏱️ Analisi Live - Cosa succede da questo minuto in poi?")

    # --- Selezione squadre ---
    col1, col2 = st.columns(2)
    with col1:
        home_team = st.selectbox("🏠 Squadra in casa", sorted(df["Home"].dropna().unique()), key="home_live")
    with col2:
        away_team = st.selectbox("🚪 Squadra in trasferta", sorted(df["Away"].dropna().unique()), key="away_live")

    # --- Inserimento quote ---
    col1, col2, col3 = st.columns(3)
    with col1:
        odd_home = st.number_input("📈 Quota Home", min_value=1.01, step=0.01, value=2.00)
    with col2:
        odd_draw = st.number_input("⚖️ Quota Pareggio", min_value=1.01, step=0.01, value=3.20)
    with col3:
        odd_away = st.number_input("📉 Quota Away", min_value=1.01, step=0.01, value=3.80)

    # --- Minuto e risultato live ---
    current_min = st.slider("⏲️ Minuto attuale", 1, 120, 45, key="current_min")
    live_score = st.text_input("📟 Risultato live (es. 1-1)", "1-1", key="live_score")
    try:
        live_h, live_a = map(int, live_score.split("-"))
    except:
        st.error("⚠️ Formato risultato non valido. Usa ad esempio `1-1`.")
        return

    label = label_match({"Odd home": odd_home, "Odd Away": odd_away})
    st.markdown(f"🔖 **Label identificato:** `{label}`")

    # --- Filtra per campionato e label ---
    champ = st.session_state.get("campionato_corrente", df["country"].iloc[0])
    df["Label"] = df.apply(label_match, axis=1)
    df_league = df[(df["country"] == champ) & (df["Label"] == label)]
    if df_league.empty:
        st.warning("⚠️ Nessuna partita per questo Label nel campionato selezionato.")
        return

    # --- Match storici con lo stesso punteggio al minuto scelto ---
    matched = []
    for _, row in df_league.iterrows():
        mh = extract_minutes(pd.Series([row.get("minuti goal segnato home","")]))
        ma = extract_minutes(pd.Series([row.get("minuti goal segnato away","")]))
        gh = sum(1 for m in mh if m <= current_min)
        ga = sum(1 for m in ma if m <= current_min)
        if gh == live_h and ga == live_a:
            matched.append(row)
    df_matched = pd.DataFrame(matched)
    st.success(f"✅ Trovate {len(df_matched)} partite con punteggio {live_h}-{live_a} al minuto {current_min}")

    # --- Calcolo OVER aggiuntivi (campionato) ---
    st.subheader("📊 Probabilità OVER (dal minuto live) - Campionato")
    extra_goals = df_matched["Home Goal FT"] + df_matched["Away Goal FT"] - (live_h + live_a)
    thresholds = [0.5, 1.5, 2.5, 3.5, 4.5]
    cols_stat = st.columns(2)
    for i, thr in enumerate(thresholds):
        pct = round((extra_goals > thr).mean() * 100, 2)
        with cols_stat[i % 2]:
            st.markdown(f"• **OVER {thr}:** {pct}%")

    # --- Frequenza risultati finali (campionato) ---
    freq = (df_matched["Home Goal FT"].astype(int).astype(str) + "-" +
            df_matched["Away Goal FT"].astype(int).astype(str))
    freq_df = freq.value_counts().reset_index()
    freq_df.columns = ["Risultato", "Occorrenze"]
    freq_df["%"] = (freq_df["Occorrenze"] / len(df_matched) * 100).round(2)
    st.subheader("📋 Risultati finali più frequenti (Campionato)")
    st.dataframe(freq_df.style.format({"%":"{:.2f}%"}))

    # --- Distribuzione goal per intervallo (campionato) ---
    st.subheader("⏱️ Distribuzione Goal per Intervallo (Campionato)")
    tf_bands = [(0,15),(16,30),(31,45),(46,60),(61,75),(76,90)]
    tf_labels = [f"{a}-{b}" for a,b in tf_bands]
    data = []
    for lbl,(a,b) in zip(tf_labels, tf_bands):
        cnt_h = sum(a < m <= b for row in df_matched
                    for m in extract_minutes(pd.Series([row.get("minuti goal segnato home","")])))
        cnt_a = sum(a < m <= b for row in df_matched
                    for m in extract_minutes(pd.Series([row.get("minuti goal segnato away","")])))
        data.append((lbl, cnt_h, cnt_a))
    tf_df = pd.DataFrame(data, columns=["Intervallo","Fatti","Subiti"])
    tf_df["Totale"] = tf_df["Fatti"] + tf_df["Subiti"]
    tf_df["% Totale"] = (tf_df["Totale"] / tf_df["Totale"].sum() * 100).round(2)
    st.dataframe(tf_df.style.format({"% Totale":"{:.2f}%"}))

    # --- Grafico goal fatti/subiti per intervallo (campionato) ---
    fig, ax = plt.subplots(figsize=(8,4))
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    ax.bar(tf_df["Intervallo"], tf_df["Fatti"],
           label="Fatti", color="#1f77b4", alpha=0.8)
    ax.bar(tf_df["Intervallo"], tf_df["Subiti"],
           bottom=tf_df["Fatti"], label="Subiti",
           color="#ff7f0e", alpha=0.8)
    for i,(tot,pct) in enumerate(zip(tf_df["Totale"], tf_df["% Totale"])):
        ax.text(i, tot+0.3, f"{tot} ({pct}%)",
                ha="center", va="bottom",
                color="black", fontweight="bold")
    ax.set_title("Goal Fatti/Subiti per Intervallo (Campionato)")
    ax.set_ylabel("Numero di goal")
    ax.legend(); ax.grid(axis="y", linestyle="--", alpha=0.3)
    st.pyplot(fig)

    st.markdown("---")

    # --- Stesse statistiche ma su squadra selezionata ---
    team = home_team if label.startswith("H_") else away_team
    df_team = df_matched[(df_matched["Home"]==home_team)|(df_matched["Away"]==away_team)]

    st.subheader(f"📊 Probabilità OVER (dal minuto live) - {team}")
    extra_t = df_team["Home Goal FT"] + df_team["Away Goal FT"] - (live_h + live_a)
    for thr in thresholds:
        pct_t = round((extra_t > thr).mean()*100,2)
        st.markdown(f"• **OVER {thr}:** {pct_t}%")

    freq_t = freq[df_matched.index.isin(df_team.index)]
    freq_df_t = freq_t.value_counts().reset_index()
    freq_df_t.columns = ["Risultato","Occorrenze"]
    freq_df_t["%"] = (freq_df_t["Occorrenze"] / len(df_team) * 100).round(2)
    st.subheader(f"📋 Risultati finali più frequenti - {team}")
    st.dataframe(freq_df_t.style.format({"%":"{:.2f}%"}))

    st.subheader(f"⏱️ Distribuzione Goal per Intervallo - {team}")
    data_t = []
    for lbl,(a,b) in zip(tf_labels, tf_bands):
        cnt_ht = sum(a < m <= b for row in df_team
                     for m in extract_minutes(pd.Series([row.get("minuti goal segnato home","")])))
        cnt_at = sum(a < m <= b for row in df_team
                     for m in extract_minutes(pd.Series([row.get("minuti goal segnato away","")])))
        data_t.append((lbl, cnt_ht, cnt_at))
    tf_df_t = pd.DataFrame(data_t, columns=["Intervallo","Fatti","Subiti"])
    tf_df_t["Totale"] = tf_df_t["Fatti"] + tf_df_t["Subiti"]
    tf_df_t["% Totale"] = (tf_df_t["Totale"] / tf_df_t["Totale"].sum() * 100).round(2)
    st.dataframe(tf_df_t.style.format({"% Totale":"{:.2f}%"}))

    fig2, ax2 = plt.subplots(figsize=(8,4))
    fig2.patch.set_facecolor("white"); ax2.set_facecolor("white")
    ax2.bar(tf_df_t["Intervallo"], tf_df_t["Fatti"],
            label="Fatti", color="#1f77b4", alpha=0.8)
    ax2.bar(tf_df_t["Intervallo"], tf_df_t["Subiti"],
            bottom=tf_df_t["Fatti"], label="Subiti",
            color="#ff7f0e", alpha=0.8)
    for i,(tot,pct) in enumerate(zip(tf_df_t["Totale"], tf_df_t["% Totale"])):
        ax2.text(i, tot+0.3, f"{tot} ({pct}%)",
                 ha="center", va="bottom",
                 color="black", fontweight="bold")
    ax2.set_title(f"Goal Fatti/Subiti per Intervallo ({team})")
    ax2.set_ylabel("Numero di goal")
    ax2.legend(); ax2.grid(axis="y", linestyle="--", alpha=0.3)
    st.pyplot(fig2)
