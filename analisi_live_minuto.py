import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder
from utils import label_match, extract_minutes


def run_live_minute_analysis(df):
    # Page config
    st.set_page_config(
        page_title="Analisi Live Minuto",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    # Sidebar inputs
    st.sidebar.header("🔍 Selezione Scenario Live")
    home_team = st.sidebar.selectbox("🏠 Squadra Casa", sorted(df["Home"].dropna().unique()), key="home_live")
    away_team = st.sidebar.selectbox("🚪 Squadra Trasferta", sorted(df["Away"].dropna().unique()), key="away_live")
    odd_home = st.sidebar.number_input("Quota Home", 1.01, 10.0, 2.00, key="odd_h")
    odd_draw = st.sidebar.number_input("Quota Pareggio", 1.01, 10.0, 3.20, key="odd_d")
    odd_away = st.sidebar.number_input("Quota Away", 1.01, 10.0, 3.80, key="odd_a")
    current_min = st.sidebar.slider("Minuto live", 1, 120, 45, key="minlive")
    live_score = st.sidebar.text_input("Risultato live (es. 1-1)", "1-1", key="scorelive")
    
    # Title
    st.title("⏱️ Analisi Live - Cosa succede da questo minuto?")
    
    # Parse live score
    try:
        live_h, live_a = map(int, live_score.split("-"))
    except:
        st.error("⚠️ Formato risultato non valido. Usa es. '1-1'.")
        return

    # Determine label and filter
    label = label_match({"Odd home": odd_home, "Odd Away": odd_away})
    st.markdown(f"**Label identificato:** `{label}`")
    champ = st.session_state.get("campionato_corrente", df["country"].iloc[0])
    df = df.copy()
    df["Label"] = df.apply(label_match, axis=1)
    df_league = df[(df["country"] == champ) & (df["Label"] == label)]
    if df_league.empty:
        st.warning("⚠️ Nessuna partita per questo scenario nel campionato.")
        return
    
    # Match historical games
    matched = []
    for _, r in df_league.iterrows():
        mh = extract_minutes(pd.Series([r.get("minuti goal segnato home", "")]))
        ma = extract_minutes(pd.Series([r.get("minuti goal segnato away", "")]))
        gh = sum(1 for m in mh if m <= current_min)
        ga = sum(1 for m in ma if m <= current_min)
        if gh == live_h and ga == live_a:
            matched.append(r)
    df_matched = pd.DataFrame(matched)
    n_matched = len(df_matched)

    # Metrics row
    m1, m2, m3 = st.columns([1,1,1])
    m1.metric("Partite trovate", f"{n_matched}")
    over_probs = {}
    thresholds = [0.5,1.5,2.5,3.5,4.5]
    extra = (df_matched["Home Goal FT"] + df_matched["Away Goal FT"] - (live_h + live_a)).fillna(0)
    for thr in thresholds:
        over_probs[thr] = (extra > thr).mean()*100 if n_matched>0 else 0
    m2.metric("% OVER 2.5 storico", f"{over_probs[2.5]:.1f}%")
    m3.metric("% OVER 3.5 storico", f"{over_probs[3.5]:.1f}%")

    # League: expandable table
    with st.expander("📑 Dettaglio partite (campionato)"):
        if n_matched>0:
            gb = GridOptionsBuilder.from_dataframe(
                df_matched[["Stagione","Data","Home","Away","Home Goal FT","Away Goal FT",
                            "minuti goal segnato home","minuti goal segnato away"]]
                .sort_values(["Stagione","Data"], ascending=False)
            )
            gb.configure_pagination()
            gb.configure_side_bar()
            AgGrid(df_matched, gridOptions=gb.build(), enable_enterprise_modules=True)
        else:
            st.write("Nessuna partita.")

    # League: frequency of final results
    freq = (df_matched["Home Goal FT"].astype(int).astype(str) + "-" + df_matched["Away Goal FT"].astype(int).astype(str))
    freq_df = freq.value_counts().rename_axis("Risultato").reset_index(name="Occorrenze")
    freq_df["%"] = (freq_df["Occorrenze"]/n_matched*100).round(2)
    fig_freq = px.bar(freq_df, x="Risultato", y="Occorrenze", text="%", title="📋 Risultati Finali (Campionato)")
    fig_freq.update_traces(textposition="outside", marker_color="#636efa")
    st.plotly_chart(fig_freq, use_container_width=True)

    # League: interval distribution
    tf_bands = [(0,15),(16,30),(31,45),(46,60),(61,75),(76,90)]
    labels = [f"{a}-{b}" for a,b in tf_bands]
    data = []
    for lbl,(a,b) in zip(labels,tf_bands):
        fatti = sum(a< m <=b for r in df_matched.itertuples() for m in extract_minutes(pd.Series([r._asdict()["minuti goal segnato home"]])))
        sub = sum(a< m <=b for r in df_matched.itertuples() for m in extract_minutes(pd.Series([r._asdict()["minuti goal segnato away"]])))
        data.append({"Intervallo":lbl,"Fatti":fatti,"Subiti":sub})
    df_tf = pd.DataFrame(data)
    fig_int = px.bar(df_tf, x="Intervallo", y=["Fatti","Subiti"], barmode="stack",
                     title="⏱️ Distribuzione Goal per Intervallo (Campionato)")
    fig_int.update_layout(plot_bgcolor="white")
    st.plotly_chart(fig_int, use_container_width=True)

    # Team-level analysis
    team = home_team if label.startswith("H_") else away_team
    df_team = df_matched[(df_matched["Home"]==home_team)|(df_matched["Away"]==away_team)]
    n_team = len(df_team)
    st.markdown(f"---\n**Analisi per squadra: {team}**")
    t1, t2 = st.columns(2)
    t1.metric("Partite {team}", f"{n_team}")
    t2.metric("% OVER 2.5 {team}", f"{(extra.loc[df_team.index]>2.5).mean()*100 if n_team>0 else 0:.1f}%")

    # Pronostico intelligente
    st.header("🤖 Pronostico consigliato")
    col1, col2, col3 = st.columns(3)
    odds = {}
    for i,thr in enumerate(thresholds[1:4]):  # consider over1.5,2.5,3.5
        odds[thr] = col1 if i==0 else (col2 if i==1 else col3)
        odds[thr] = st.number_input(f"Quota LIVE OVER {live_h+live_a+thr}?", 1.01, 10.0, 2.00, key=f"odd_dyn_{thr}")
    evs = {thr:over_probs[thr]/100*odd-1 for thr,odd in odds.items()}
    best_thr, best_ev = max(evs.items(), key=lambda x: x[1])
    if best_ev>0:
        st.success(f"💡 Scommetti OVER {best_thr} → EV: {best_ev:.2%}")
    else:
        st.info("ℹ️ Nessun valore positivo di EV trovato.")

# Usage example:
# df = pd.read_csv("partite.csv")
# run_live_minute_analysis(df)
