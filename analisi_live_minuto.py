import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_aggrid import AgGrid, GridOptionsBuilder
from utils import label_match, extract_minutes

def run_live_minute_analysis(df):
    st.set_page_config(page_title="Analisi Live Minuto", layout="wide")
    
    # Sidebar per tutti gli input
    with st.sidebar:
        st.header("⚙️ Configurazione Live")
        squadra_casa = st.selectbox("🏠 Squadra in casa", sorted(df["Home"].dropna().unique()), key="home_team_live")
        squadra_ospite = st.selectbox("🚪 Squadra fuori casa", sorted(df["Away"].dropna().unique()), key="away_team_live")
        quota_home = st.number_input("Quota Home", 1.01, 10.0, 2.00, step=0.01)
        quota_draw = st.number_input("Quota Draw", 1.01, 10.0, 3.20, step=0.01)
        quota_away = st.number_input("Quota Away", 1.01, 10.0, 3.80, step=0.01)
        minuto_corrente = st.slider("⏱️ Minuto attuale", 1, 120, 60)
        risultato_live = st.text_input("📟 Risultato live (es. 1-1)", "1-1")
        st.markdown("---")

    # Titolo
    st.title("⏱️ Analisi Live - Cosa succede dopo il minuto selezionato?")
    
    # Calcoli preliminari (come già in precedenza)
    try:
        goal_home_live, goal_away_live = map(int, risultato_live.split("-"))
    except:
        st.error("⚠️ Inserisci un risultato valido (es. 1-1).")
        return
    label = label_match({"Odd home": quota_home, "Odd Away": quota_away})
    st.markdown(f"**🔖 Label identificato:** `{label}`")
    
    # Filtri database
    db_selected = st.session_state.get("campionato_corrente")
    df["Label"] = df.apply(label_match, axis=1)
    df_label = df[(df["Label"]==label)&(df["country"]==db_selected)]
    if df_label.empty:
        st.warning("⚠️ Nessuna partita per questo Label in campionato.")
        return
    
    # Match storici con stesso score al minuto
    matched = []
    for _, r in df_label.iterrows():
        h = extract_minutes(pd.Series([r["minuti goal segnato home"]]))
        a = extract_minutes(pd.Series([r["minuti goal segnato away"]]))
        if sum(m<=minuto_corrente for m in h)==goal_home_live and sum(m<=minuto_corrente for m in a)==goal_away_live:
            matched.append(r)
    if not matched:
        st.warning("❌ Nessun storico trovato.")
        return
    df_matched = pd.DataFrame(matched)
    
    # Calcolo metriche
    total = len(df_matched)
    goal_after = sum(bool([m for m in extract_minutes(pd.Series([r["minuti goal segnato home"]]))+
                               extract_minutes(pd.Series([r["minuti goal segnato away"]])) if m>minuto_corrente])
                     for _,r in df_matched.iterrows())
    over = {}
    for soglia in [0.5,1.5,2.5,3.5,4.5]:
        over[soglia] = round((df_matched.eval(f"(Home Goal FT+Away Goal FT) - ({goal_home_live}+{goal_away_live}) > {soglia}").sum()/total)*100,2)
    
    # Sezione metriche
    with st.container():
        st.subheader("📊 Metriche principali")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Match Analizzati", total)
        c2.metric(f"% con ≥1 goal dopo {minuto_corrente}'", f"{round(goal_after/total*100,2)}%")
        c3.metric(f"OVER 0.5", f"{over[0.5]}%")
        c4.metric(f"OVER 1.5", f"{over[1.5]}%")
        c5.metric(f"OVER 2.5", f"{over[2.5]}%")
        # (aggiungi altre colonne se ti servono)
    
    # Tab per Campionato vs Squadra
    tab1, tab2 = st.tabs(["🏆 Campionato","🤼 Squadra Selezionata"])
    
    # --- Tab Campionato ---
    with tab1:
        st.markdown("### 🧾 Risultati Finali più frequenti")
        freq = df_matched["Home Goal FT"].astype(str)+"-"+df_matched["Away Goal FT"].astype(str)
        df_freq = freq.value_counts().reset_index().rename(columns={"index":"Risultato",0:"Occorrenze"})
        st.dataframe(df_freq, use_container_width=True)
        
        # Time Frame distribution
        tf_bands = [(0,15),(16,30),(31,45),(46,60),(61,75),(76,90)]
        tf_labels = [f"{a}-{b}" for a,b in tf_bands[:-1]]+["76-90+"]
        data = []
        for a,b,label_tf in zip([x[0] for x in tf_bands],[x[1] for x in tf_bands],tf_labels):
            cnt_tot = sum(a<m<=b for _,r in df_matched.iterrows() for m in extract_minutes(pd.Series([r["minuti goal segnato home"]]))+extract_minutes(pd.Series([r["minuti goal segnato away"]])))
            cnt_f = sum(a<m<=b for _,r in df_matched.iterrows() for m in extract_minutes(pd.Series([r["minuti goal segnato home"]])))
            cnt_s = sum(a<m<=b for _,r in df_matched.iterrows() for m in extract_minutes(pd.Series([r["minuti goal segnato away"]])))
            data.append({"Time Frame":label_tf, "Totali":cnt_tot, "Fatti":cnt_f, "Subiti":cnt_s, "%":round(cnt_tot/sum(d["Totali"] for d in data)*100,2) if data else 0})
        df_tf = pd.DataFrame(data)
        
        # Plotly bar
        fig1 = px.bar(df_tf, x="Time Frame", y=["Fatti","Subiti"], text_auto=True,
                      title="⏱️ Distribuzione Goal per Time Frame",
                      template="plotly_white")
        fig1.update_layout(barmode="group", legend_title="", font_color="black")
        st.plotly_chart(fig1, use_container_width=True)
    
    # --- Tab Squadra ---
    with tab2:
        squadra = squadra_casa if label.startswith("H_") else squadra_ospite
        st.markdown(f"### 📋 Partite storiche per **{squadra}**")
        gb = GridOptionsBuilder.from_dataframe(df_matched[["Stagione","Data","Home","Away","Home Goal FT","Away Goal FT","minuti goal segnato home","minuti goal segnato away"]])
        gb.configure_pagination(pageSize=10)
        gb.configure_default_column(sortable=True, filter=True, resizable=True)
        AgGrid(df_matched, gridOptions=gb.build(), height=300)
        
        st.markdown("### 📊 Statistiche post-minuto")
        # (stessa logica over, risultati, tf ma filtrata su df_squadra)
        # …
        # usa fig2, fig3 analoghi con px.bar e template bianco
        
    # Pronostico intelligente
    st.header("🤖 Pronostico consigliato")
    st.markdown("Inserisci adesso manualmente le **quote LIVE** per OVER in base al risultato corrente")
    live_home, live_away = goal_home_live, goal_away_live
    ov05 = st.number_input(f"Quota LIVE OVER {live_home+live_away+0.5}",1.01,10.0,2.00,step=0.01)
    ov15 = st.number_input(f"Quota LIVE OVER {live_home+live_away+1.5}",1.01,10.0,2.50,step=0.01)
    ov25 = st.number_input(f"Quota LIVE OVER {live_home+live_away+2.5}",1.01,10.0,3.00,step=0.01)
    # Calcolo EV
    evs = {
        live_home+live_away+0.5: ov05*over[0.5]/100 - 1,
        live_home+live_away+1.5: ov15*over[1.5]/100 - 1,
        live_home+live_away+2.5: ov25*over[2.5]/100 - 1,
    }
    best = max(evs, key=lambda k: evs[k])
    st.markdown(f"**👍 Miglior EV:** OVER {best} → EV = {evs[best]:.2%}")
