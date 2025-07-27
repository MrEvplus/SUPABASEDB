import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from utils import label_match, extract_minutes

def run_live_minute_analysis(df):
    st.set_page_config(page_title="Analisi Live Minuto", layout="wide")
    st.title("⏱️ Analisi Live - Cosa succede da questo minuto?")

    # --- Selezione squadre ---
    col1, col2 = st.columns(2)
    with col1:
        home_team = st.selectbox("🏠 Squadra in casa", sorted(df["Home"].dropna().unique()), key="home_live")
    with col2:
        away_team = st.selectbox("🚪 Squadra in trasferta", sorted(df["Away"].dropna().unique()), key="away_live")

    # --- Inserimento quote ---
    c1, c2, c3 = st.columns(3)
    with c1:
        odd_home = st.number_input("📈 Quota Home", 1.01, 10.0, 2.00, key="odd_h")
    with c2:
        odd_draw = st.number_input("⚖️ Quota Pareggio", 1.01, 10.0, 3.20, key="odd_d")
    with c3:
        odd_away = st.number_input("📉 Quota Away", 1.01, 10.0, 3.80, key="odd_a")

    # --- Minuto e punteggio live ---
    current_min = st.slider("⏲️ Minuto attuale", 1, 120, 45, key="minlive")
    live_score = st.text_input("📟 Risultato live (es. 1-1)", "1-1", key="scorelive")
    try:
        live_h, live_a = map(int, live_score.split("-"))
    except:
        st.error("⚠️ Formato risultato non valido. Usa es. `1-1`.")
        return

    # --- Label e filtraggio campionato+label ---
    label = label_match({"Odd home": odd_home, "Odd Away": odd_away})
    st.markdown(f"🔖 **Label:** `{label}`")
    champ = st.session_state.get("campionato_corrente", df["country"].iloc[0])
    df["Label"] = df.apply(label_match, axis=1)
    df_league = df[(df["country"] == champ) & (df["Label"] == label)]
    if df_league.empty:
        st.warning("⚠️ Nessuna partita per questo label nel campionato.")
        return

    # --- Partite storiche con stesso live score al minuto ---
    matched = []
    for _, r in df_league.iterrows():
        mh = extract_minutes(pd.Series([r.get("minuti goal segnato home","")]))
        ma = extract_minutes(pd.Series([r.get("minuti goal segnato away","")]))
        gh = sum(m<=current_min for m in mh)
        ga = sum(m<=current_min for m in ma)
        if gh==live_h and ga==live_a:
            matched.append(r)
    df_matched = pd.DataFrame(matched)
    st.success(f"✅ {len(df_matched)} partite trovate a {live_h}-{live_a}′{current_min}’")

    # --- OVER 0.5→4.5 Campionato ---
    st.subheader("📊 OVER dal minuto live (Campionato)")
    extra = df_matched["Home Goal FT"] + df_matched["Away Goal FT"] - (live_h+live_a)
    thresholds = [0.5,1.5,2.5,3.5,4.5]
    cols = st.columns(2)
    for i, thr in enumerate(thresholds):
        pct = (extra>thr).mean()*100 if len(extra)>0 else 0
        with cols[i%2]:
            st.markdown(f"• **OVER {thr}:** {pct:.2f}%")

    # --- Risultati frequenti Campionato ---
    freq = (df_matched["Home Goal FT"].astype(int).astype(str)
            + "-" + df_matched["Away Goal FT"].astype(int).astype(str))
    freq_df = freq.value_counts().rename_axis("Risultato").reset_index(name="Occorrenze")
    freq_df["%"] = freq_df["Occorrenze"]/len(df_matched)*100
    freq_df["%"] = freq_df["%"].round(2)
    st.subheader("📋 Risultati finali (Campionato)")
    st.dataframe(
        freq_df.style
        .format({"%":"{:.2f}%"})
        .set_properties(**{"text-align":"center"})
        .set_table_styles([{"selector":"th","props":[("text-align","center")]}])
    )

    # --- Distribuzione goal per intervallo Campionato ---
    st.subheader("⏱️ Goal per intervallo (Campionato)")
    tf_bands = [(0,15),(16,30),(31,45),(46,60),(61,75),(76,90)]
    tf_labels = [f"{a}-{b}" for a,b in tf_bands]
    # ricava tf_counts, tf_fatti, tf_subiti nella prima scansione
    tf_counts, tf_fatti, tf_subiti = {}, {}, {}
    for lbl in tf_labels:
        tf_counts[lbl]=tf_fatti[lbl]=tf_subiti[lbl]=0
    for _, r in df_matched.iterrows():
        mh = extract_minutes(pd.Series([r.get("minuti goal segnato home","")]))
        ma = extract_minutes(pd.Series([r.get("minuti goal segnato away","")]))
        for m in mh:
            for lbl,(a,b) in zip(tf_labels,tf_bands):
                if a<m<=b:
                    tf_counts[lbl]+=1
                    tf_fatti[lbl]+=1
                    break
        for m in ma:
            for lbl,(a,b) in zip(tf_labels,tf_bands):
                if a<m<=b:
                    tf_counts[lbl]+=1
                    tf_subiti[lbl]+=1
                    break
    df_tf = pd.DataFrame([
        {"Intervallo":lbl, "Fatti":tf_fatti[lbl], "Subiti":tf_subiti[lbl]}
        for lbl in tf_labels
    ])
    df_tf["Totale"] = df_tf["Fatti"]+df_tf["Subiti"]
    df_tf["% Totale"] = (df_tf["Totale"]/df_tf["Totale"].sum()*100).round(2)

    st.dataframe(
        df_tf.style
        .format({"% Totale":"{:.2f}%"})
        .set_properties(**{"text-align":"center"})
        .set_table_styles([{"selector":"th","props":[("text-align","center")]}])
    )

    # --- Grafico intervalli Campionato ---
    fig, ax = plt.subplots(figsize=(8,4))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.bar(df_tf["Intervallo"], df_tf["Fatti"], color="#1f77b4", label="Fatti", alpha=0.8)
    ax.bar(df_tf["Intervallo"], df_tf["Subiti"], bottom=df_tf["Fatti"],
           color="#ff7f0e", label="Subiti", alpha=0.8)
    for i,row in df_tf.iterrows():
        ax.text(i, row.Totale+0.3, f'{row.Totale} ({row["% Totale"]}%)',
                ha="center", va="bottom", color="black", fontweight="bold")
    ax.set_title("Campionato: goal per intervallo")
    ax.set_ylabel("N° goal")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    # --- Statistiche e grafici squadra selezionata affiancati ---
    team = home_team if label.startswith("H_") else away_team
    df_team = df_matched[
        (df_matched["Home"]==home_team)|(df_matched["Away"]==away_team)
    ]

    # OVER per squadra
    extra_t = df_team["Home Goal FT"]+df_team["Away Goal FT"]-(live_h+live_a)
    st.subheader(f"📊 OVER dal minuto live - {team}")
    for thr in thresholds:
        pctt = (extra_t>thr).mean()*100 if len(extra_t)>0 else 0
        st.markdown(f"• **OVER {thr}:** {pctt:.2f}%")

    # Risultati squadra
    freq_t = freq.loc[df_team.index]
    freq_df_t = freq_t.value_counts().rename_axis("Risultato").reset_index(name="Occorrenze")
    freq_df_t["%"] = (freq_df_t["Occorrenze"]/len(df_team)*100).round(2)
    st.subheader(f"📋 Risultati finali - {team}")
    st.dataframe(
        freq_df_t.style
        .format({"%":"{:.2f}%"})
        .set_properties(**{"text-align":"center"})
        .set_table_styles([{"selector":"th","props":[("text-align","center")]}])
    )

    # Distribuzione intervalli squadra
    tf_counts_t, tf_fatti_t, tf_subiti_t = {},{},{}
    for lbl in tf_labels:
        tf_counts_t[lbl]=tf_fatti_t[lbl]=tf_subiti_t[lbl]=0
    for _, r in df_team.iterrows():
        mh = extract_minutes(pd.Series([r.get("minuti goal segnato home","")]))
        ma = extract_minutes(pd.Series([r.get("minuti goal segnato away","")]))
        for m in mh:
            for lbl,(a,b) in zip(tf_labels,tf_bands):
                if a<m<=b:
                    tf_counts_t[lbl]+=1; tf_fatti_t[lbl]+=1; break
        for m in ma:
            for lbl,(a,b) in zip(tf_labels,tf_bands):
                if a<m<=b:
                    tf_counts_t[lbl]+=1; tf_subiti_t[lbl]+=1; break
    df_t = pd.DataFrame([
        {"Intervallo":lbl, "Fatti":tf_fatti_t[lbl], "Subiti":tf_subiti_t[lbl]}
        for lbl in tf_labels
    ])
    df_t["Totale"]=df_t["Fatti"]+df_t["Subiti"]
    df_t["% Totale"]=(df_t["Totale"]/df_t["Totale"].sum()*100).round(2)

    st.subheader(f"⏱️ Goal per intervallo - {team}")
    st.dataframe(
        df_t.style
        .format({"% Totale":"{:.2f}%"})
        .set_properties(**{"text-align":"center"})
        .set_table_styles([{"selector":"th","props":[("text-align","center")]}])
    )

    fig2, ax2 = plt.subplots(figsize=(8,4))
    fig2.patch.set_facecolor("white"); ax2.set_facecolor("white")
    ax2.bar(df_t["Intervallo"], df_t["Fatti"], color="#1f77b4", label="Fatti", alpha=0.8)
    ax2.bar(df_t["Intervallo"], df_t["Subiti"], bottom=df_t["Fatti"],
            color="#ff7f0e", label="Subiti", alpha=0.8)
    for i,row in df_t.iterrows():
        ax2.text(i, row.Totale+0.3, f'{row.Totale} ({row["% Totale"]}%)',
                 ha="center", va="bottom", color="black", fontweight="bold")
    ax2.set_title(f"{team}: goal per intervallo")
    ax2.set_ylabel("N° goal"); ax2.legend()
    ax2.grid(axis="y", linestyle="--", alpha=0.3)

    st.pyplot(fig)
    st.pyplot(fig2)

    st.markdown("---")
    # Pronostico intelligente
    st.header("🤖 Pronostico consigliato")
    evs = {}
    for thr in thresholds:
        colnm = f"odd over {str(thr).replace('.',',')}"
        if colnm in df_matched:
            ev = (extra>thr).mean()*df_matched[colnm].mean() - 1
            evs[thr]=ev
    if evs:
        best, best_ev = max(evs.items(), key=lambda x:x[1])
        if best_ev>0:
            st.success(f"💡**OVER {best}**  → EV: {best_ev:.2%}")
        else:
            st.info("ℹ️ Nessun EV positivo trovato.")
    else:
        st.info("ℹ️ Quote OVER non disponibili per EV.")

