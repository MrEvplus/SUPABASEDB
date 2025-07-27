import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from utils import label_match, extract_minutes

def run_live_minute_analysis(df):
    st.title("⏱️ Analisi Live dal Minuto Selezionato")
    # -----------------------------
    # Input utente
    # -----------------------------
    home = st.selectbox("🏠 Squadra in casa", sorted(df["Home"].dropna().unique()), key="home_live")
    away = st.selectbox("🚪 Squadra fuori casa", sorted(df["Away"].dropna().unique()), key="away_live")

    c1, c2, c3 = st.columns(3)
    with c1:
        odd_h = st.number_input("Quota Home", 1.01, 10.0, 2.00)
    with c2:
        odd_d = st.number_input("Quota Draw", 1.01, 10.0, 3.20)
    with c3:
        odd_a = st.number_input("Quota Away", 1.01, 10.0, 3.80)

    minute = st.slider("⏱️ Minuto attuale", 1, 120, 60)
    live_score = st.text_input("📟 Risultato live (es. 1-1)", "1-1")
    try:
        gh_live, ga_live = map(int, live_score.split("-"))
    except:
        st.error("⚠️ Formato risultato non valido!")
        return

    label = label_match({"Odd home": odd_h, "Odd Away": odd_a})
    st.markdown(f"🔖 **Label individuato:** `{label}`")
    league = st.session_state.get("campionato_corrente")
    if not league:
        st.warning("Seleziona un campionato prima")
        return

    df["Label"] = df.apply(label_match, axis=1)
    df0 = df[(df["Label"]==label) & (df["country"]==league)].copy()
    if df0.empty:
        st.warning("Nessuna partita storica trovata per questo scenario.")
        return

    # -----------------------------
    # Filtra match con lo stesso live score
    # -----------------------------
    matches = []
    for _, row in df0.iterrows():
        hg = extract_minutes(pd.Series([row["minuti goal segnato home"]]))
        ag = extract_minutes(pd.Series([row["minuti goal segnato away"]]))
        if sum(m<=minute for m in hg)==gh_live and sum(m<=minute for m in ag)==ga_live:
            matches.append(row)
    if not matches:
        st.warning("Nessun storico con quel punteggio/minuto.")
        return

    dfm = pd.DataFrame(matches)
    st.success(f"Trovati **{len(dfm)}** match con `{gh_live}-{ga_live}` al **{minute}'**")

    # soglie di OVER
    thresholds = [0.5, 1.5, 2.5, 3.5, 4.5]
    st.markdown("### 📈 % OVER dal minuto selezionato (Campionato)")
    for t in thresholds:
        cnt = ((dfm["Home Goal FT"]+dfm["Away Goal FT"]) - (gh_live+ga_live) > t).sum()
        pct = round(cnt/len(dfm)*100,2)
        st.write(f"- OVER {t}: **{pct}%**")

    # -----------------------------
    # Tabella "Risultati Finali più frequenti" (Campionato)
    # -----------------------------
    freq = (dfm
            .groupby(["Home Goal FT","Away Goal FT"])
            .size()
            .reset_index(name="Count"))
    freq["Risultato"] = freq["Home Goal FT"].astype(str) + "-" + freq["Away Goal FT"].astype(str)
    freq = freq.sort_values("Count", ascending=False)
    total = freq["Count"].sum()
    freq["%"] = (freq["Count"]/total*100).round(2)
    st.markdown("### 🧾 Risultati Finali più frequenti (Campionato)")
    st.dataframe(
        freq[["Risultato","Count","%"]]
        .rename(columns={"Count":"Occorrenze"})
        .style.format({"%":"{:.2f}%"}),
        height=250
    )

    # -----------------------------
    # Distribuzione goal per Time Frame (Campionato)
    # -----------------------------
    st.markdown("### ⏱️ Distribuzione Goal per Intervallo di Minuti (Campionato)")
    bands = [(0,15),(16,30),(31,45),(46,60),(61,75),(76,90)]
    labels = [f"{a}-{b}" for a,b in bands]
    df_tf = pd.DataFrame(0, index=labels, columns=["Fatti","Subiti"])
    for _, row in dfm.iterrows():
        hg = extract_minutes(pd.Series([row["minuti goal segnato home"]]))
        ag = extract_minutes(pd.Series([row["minuti goal segnato away"]]))
        for m in hg:
            if m>minute:
                for (a,b),lbl in zip(bands,labels):
                    if a< m <= b:
                        df_tf.at[lbl,"Fatti"] +=1
                        break
        for m in ag:
            if m>minute:
                for (a,b),lbl in zip(bands,labels):
                    if a< m <= b:
                        df_tf.at[lbl,"Subiti"] +=1
                        break
    df_tf["% Totale"] = ( (df_tf.sum(axis=1) / df_tf.sum(axis=1).sum())*100 ).round(2)
    st.dataframe(df_tf.reset_index().rename(columns={"index":"Intervallo"}),
                 height=250,
                 use_container_width=True,
                 )

    # -----------------------------
    # Grafici affiancati (Campionato)
    # -----------------------------
    colA, colB = st.columns(2)
    with colA:
        fig, ax = plt.subplots(figsize=(5,3))
        df_tf[["Fatti","Subiti"]].plot.bar(ax=ax)
        for i,(f,s) in enumerate(zip(df_tf["Fatti"],df_tf["Subiti"])):
            ax.text(i, f/2, str(f), ha="center", va="center", color="white", fontweight="bold")
            ax.text(i, f+s/2, str(s), ha="center", va="center", color="white", fontweight="bold")
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.set_title("Goal Fatti vs Subiti per Intervallo (Campionato)")
        ax.set_ylabel("Numero di goal")
        st.pyplot(fig)
    with colB:
        fig2, ax2 = plt.subplots(figsize=(5,3))
        bars = ax2.bar(labels, df_tf["% Totale"], color="teal")
        for i,val in enumerate(df_tf["% Totale"]):
            ax2.text(i, val+0.5, f"{val}%", ha="center", va="bottom", fontweight="bold")
        ax2.set_xticklabels(labels, rotation=45, ha="right")
        ax2.set_title("% Goal totali per Intervallo (Campionato)")
        ax2.set_ylabel("% del totale")
        st.pyplot(fig2)

    # =============================================================================
    # Ripeti ora per la squadra specifica
    # =============================================================================
    st.markdown("---")
    team = home if label.startswith("H_") else away
    st.header(f"⚽ Dettaglio per squadra: {team}")
    dft = dfm[(dfm["Home"]==team)|(dfm["Away"]==team)].copy()
    if dft.empty:
        st.info("Nessun match per questa squadra nello scenario.")
        return

    # OVER per squadra
    st.markdown(f"### 📈 % OVER dal {minute}' per {team}")
    for t in thresholds:
        cnt = ((dft["Home Goal FT"]+dft["Away Goal FT"]) - (gh_live+ga_live) > t).sum()
        pct = round(cnt/len(dft)*100,2)
        st.write(f"- OVER {t}: **{pct}%**")

    # Tabella risultati squadra
    fr2 = (dft
           .groupby(["Home Goal FT","Away Goal FT"])
           .size().reset_index(name="Occorrenze"))
    fr2["Risultato"] = fr2["Home Goal FT"].astype(str) + "-" + fr2["Away Goal FT"].astype(str)
    fr2 = fr2.sort_values("Occorrenze", ascending=False)
    tot2 = fr2["Occorrenze"].sum()
    fr2["%"] = (fr2["Occorrenze"]/tot2*100).round(2)
    st.markdown(f"### 🧾 Risultati Finali più frequenti ({team})")
    st.dataframe(
        fr2[["Risultato","Occorrenze","%"]]
        .style
          .set_properties(**{"background-color":"white","color":"#333","border":"1px solid #ddd"})
          .format({"%":"{:.2f}%"}),
        height=250
    )

    # Distribuzione TF per squadra
    st.markdown(f"### ⏱️ Distribuzione Goal per Intervallo ({team})")
    df_tf2 = pd.DataFrame(0, index=labels, columns=["Fatti","Subiti"])
    for _, row in dft.iterrows():
        hg = extract_minutes(pd.Series([row["minuti goal segnato home"]]))
        ag = extract_minutes(pd.Series([row["minuti goal segnato away"]]))
        for m in hg:
            if m>minute:
                for (a,b),lbl in zip(bands,labels):
                    if a< m <= b:
                        df_tf2.at[lbl,"Fatti"] +=1; break
        for m in ag:
            if m>minute:
                for (a,b),lbl in zip(bands,labels):
                    if a< m <= b:
                        df_tf2.at[lbl,"Subiti"] +=1; break
    df_tf2["% Totale"] = ((df_tf2.sum(axis=1)/df_tf2.sum(axis=1).sum())*100).round(2)
    st.dataframe(
        df_tf2.reset_index().rename(columns={"index":"Intervallo"}),
        height=250,
        use_container_width=True
    )

    # Grafici affiancati (squadra)
    colC, colD = st.columns(2)
    with colC:
        fig3, ax3 = plt.subplots(figsize=(5,3))
        fig3.patch.set_facecolor("white")
        ax3.set_facecolor("white")
        df_tf2[["Fatti","Subiti"]].plot.bar(ax=ax3, color=["#1f77b4","#ff7f0e"])
        for i,(f,s) in enumerate(zip(df_tf2["Fatti"],df_tf2["Subiti"])):
            ax3.text(i, f/2, str(f), ha="center", va="center", color="white", fontweight="bold")
            ax3.text(i, f+s/2, str(s), ha="center", va="center", color="white", fontweight="bold")
        ax3.set_xticklabels(labels, rotation=45, ha="right")
        ax3.set_title(f"Goal Fatti vs Subiti per Intervallo ({team})", pad=15)
        ax3.set_ylabel("Numero di goal")
        ax3.grid(axis="y", linestyle="--", alpha=0.3)
        st.pyplot(fig3)

    with colD:
        fig4, ax4 = plt.subplots(figsize=(5,3))
        fig4.patch.set_facecolor("white")
        ax4.set_facecolor("white")
        bars4 = ax4.bar(labels, df_tf2["% Totale"], color="#2ca02c")
        for i,v in enumerate(df_tf2["% Totale"]):
            ax4.text(i, v+0.5, f"{v}%", ha="center", va="bottom", fontweight="bold")
        ax4.set_xticklabels(labels, rotation=45, ha="right")
        ax4.set_title(f"% Goal per Intervallo ({team})", pad=15)
        ax4.set_ylabel("% del totale")
        ax4.grid(axis="y", linestyle="--", alpha=0.3)
        st.pyplot(fig4)
