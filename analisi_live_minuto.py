import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from utils import label_match, extract_minutes

def run_live_minute_analysis(df):
    st.title("⏱️ Analisi Live - Cosa è successo da questo minuto in poi?")

    # 1) Input squadra, quote e live score
    squadra_casa = st.selectbox("🏠 Squadra in casa", sorted(df["Home"].dropna().unique()), key="home_team_live")
    squadra_ospite = st.selectbox("🚪 Squadra fuori casa", sorted(df["Away"].dropna().unique()), key="away_team_live")
    col1, col2, col3 = st.columns(3)
    with col1:
        quota_home = st.number_input("Quota Home", 1.01, 10.0, 2.00, key="odd_home_live")
    with col2:
        quota_draw = st.number_input("Quota Draw", 1.01, 10.0, 3.20, key="odd_draw_live")
    with col3:
        quota_away = st.number_input("Quota Away", 1.01, 10.0, 3.80, key="odd_away_live")

    minuto_corrente = st.slider("⏱️ Minuto attuale", 1, 120, 60, key="live_minute")
    risultato_live = st.text_input("📟 Risultato live (es. 1-1)", "1-1", key="live_score")
    try:
        goal_home_live, goal_away_live = map(int, risultato_live.split("-"))
    except:
        st.error("⚠️ Formato risultato non valido.")
        return

    # 2) Identifico label e filtro campionato
    label = label_match({"Odd home": quota_home, "Odd Away": quota_away})
    st.markdown(f"🔖 **Label:** `{label}`")
    db = st.session_state.get("campionato_corrente")
    if not db:
        st.error("⚠️ Seleziona prima un campionato.")
        return
    df["Label"] = df.apply(label_match, axis=1)
    df_label = df[(df["Label"]==label)&(df["country"]==db)]

    # 3) Trovo tutte le storiche con stesso score e minuto
    matched = []
    for _, r in df_label.iterrows():
        hms = extract_minutes(pd.Series([r["minuti goal segnato home"]]))
        ams = extract_minutes(pd.Series([r["minuti goal segnato away"]]))
        if sum(1 for m in hms if m<=minuto_corrente)==goal_home_live \
           and sum(1 for m in ams if m<=minuto_corrente)==goal_away_live:
            matched.append(r)
    if not matched:
        st.warning("❌ Nessuna partita storica trovata.")
        return
    df_matched = pd.DataFrame(matched)
    st.success(f"Trovate {len(df_matched)} partite storiche")

    # 4) Calcolo over statici dal minuto in poi
    live_total = goal_home_live + goal_away_live
    over_thresholds = [0.5, 1.5, 2.5]
    dynamic_over = {
        x: round((df_matched.eval(f"`Home Goal FT`+`Away Goal FT` > @live_total + {x}")\
                   .sum()/len(df_matched))*100,2)
        for x in over_thresholds
    }

    st.markdown(f"📊 **% partite con almeno 1 goal dopo il {minuto_corrente}’**: "
                f"**{dynamic_over[0.5]}%**")

    for x in over_thresholds:
        st.markdown(f"📈 **OVER {live_total:+.1f + x}** → **{dynamic_over[x]}%**")

    # 5) Top risultati finali
    finali = df_matched.eval("`Home Goal FT`.astype(str)+'-'+`Away Goal FT`.astype(str)")
    top5 = finali.value_counts().reset_index().head(5)
    top5.columns = ["Risultato","Occorrenze"]
    st.markdown("### 🧾 Risultati Finali più frequenti")
    st.table(top5)

    # 6) Distribuzione goal per time frame
    tf_bands = [(0,15),(16,30),(31,45),(46,60),(61,75),(76,90)]
    tf_labels = ["0-15","16-30","31-45","46-60","61-75","76-90+"]
    tf_counts = {lab:0 for lab in tf_labels}
    tf_fatti = {lab:0 for lab in tf_labels}
    tf_subiti = {lab:0 for lab in tf_labels}

    for _, r in df_matched.iterrows():
        hms = extract_minutes(pd.Series([r["minuti goal segnato home"]]))
        ams = extract_minutes(pd.Series([r["minuti goal segnato away"]]))
        for m in hms:
            for lbl,(a,b) in zip(tf_labels,tf_bands):
                if a< m <=b:
                    tf_counts[lbl]+=1; tf_fatti[lbl]+=1
        for m in ams:
            for lbl,(a,b) in zip(tf_labels,tf_bands):
                if a< m <=b:
                    tf_counts[lbl]+=1; tf_subiti[lbl]+=1

    tf_df = pd.DataFrame({
        "TimeFrame":tf_labels,
        "Fatti": [tf_fatti[l] for l in tf_labels],
        "Subiti":[tf_subiti[l] for l in tf_labels],
    })
    tf_df["Totali"]=tf_df["Fatti"]+tf_df["Subiti"]
    tf_df["%"] = (tf_df["Totali"]/tf_df["Totali"].sum()*100).round(2)
    st.markdown("### ⏱ Distribuzione Goal per Time Frame")
    st.dataframe(tf_df.style.format({"%":"{:.2f}%"}))

    # Grafici affiancati
    c1,c2 = st.columns(2)
    with c1:
        fig,ax = plt.subplots()
        ax.bar(tf_df["TimeFrame"],tf_df["Fatti"],label="Fatti",color="steelblue")
        ax.bar(tf_df["TimeFrame"],tf_df["Subiti"],bottom=tf_df["Fatti"],
               label="Subiti",color="salmon")
        for i,(tot,pct) in enumerate(zip(tf_df["Totali"],tf_df["%"])):
            ax.text(i,tot+0.5,f"{int(tot)}\n{pct:.0f}%",ha="center",color="black")
        ax.set_title("Campionato - Goal per TF")
        ax.legend(); ax.set_facecolor("white")
        st.pyplot(fig)
    with c2:
        # identico per la singola squadra storica
        squadra_target = squadra_casa if label.startswith("H_") else squadra_ospite
        df_sq = df_matched[(df_matched["Home"]==squadra_target)|(df_matched["Away"]==squadra_target)]
        tf2 = tf_df.copy()
        st.markdown(f"#### Squadra: {squadra_target}")
        fig2,ax2=plt.subplots()
        ax2.bar(tf2["TimeFrame"],tf2["Fatti"],label="Fatti",color="navy")
        ax2.bar(tf2["TimeFrame"],tf2["Subiti"],bottom=tf2["Fatti"],
                label="Subiti",color="lightcoral")
        for i,(tot,pct) in enumerate(zip(tf2["Totali"],tf2["%"])):
            ax2.text(i,tot+0.5,f"{int(tot)}\n{pct:.0f}%",ha="center",color="black")
        ax2.set_title("Squadra - Goal per TF")
        ax2.legend(); ax2.set_facecolor("white")
        st.pyplot(fig2)

    # 7) 🤖 Pronostico consigliato LIVE
    st.header("🤖 Pronostico consigliato LIVE")
    # soglie = live_total + [0.5,1.5,2.5]
    st.subheader("Inserisci le quote LIVE per gli OVER")
    odds = {}
    for idx,x in enumerate(over_thresholds):
        soglia = live_total + x
        odds[x] = st.number_input(f"Quota OVER {soglia:.1f}", 1.01, 10.0, key=f"odd_over{int(x*10)}")
    st.subheader("Calcolo EV")
    for x in over_thresholds:
        prob = dynamic_over[x]/100
        ev = (odds[x] * prob) - 1
        signo = "🟢" if ev>0 else "🔴"
        st.markdown(f"**OVER {live_total + x:.1f}** → EV: {signo} {ev:.2%}")

