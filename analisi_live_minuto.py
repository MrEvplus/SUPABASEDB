import streamlit as st
import pandas as pd
from utils import label_match, extract_minutes
import matplotlib.pyplot as plt

def run_live_minute_analysis(df):
    st.set_page_config(layout="wide")
    st.title("⏱️ Analisi Live - Cosa è successo da questo minuto in poi?")

    # Selezione squadre e quote
    squadra_casa = st.selectbox("🏠 Squadra in casa", sorted(df["Home"].dropna().unique()), key="home_team_live")
    squadra_ospite = st.selectbox("🚪 Squadra fuori casa", sorted(df["Away"].dropna().unique()), key="away_team_live")
    col1, col2, col3 = st.columns(3)
    with col1:
        quota_home = st.number_input("Quota Home", min_value=1.01, step=0.01, value=2.00)
    with col2:
        quota_draw = st.number_input("Quota Draw", min_value=1.01, step=0.01, value=3.20)
    with col3:
        quota_away = st.number_input("Quota Away", min_value=1.01, step=0.01, value=3.80)

    # Minuto e risultato live
    minuto_corrente = st.slider("⏱️ Minuto attuale", min_value=1, max_value=120, value=60)
    risultato_live = st.text_input("📟 Risultato live (es. 1-1)", value="1-1")
    try:
        goal_home_live, goal_away_live = map(int, risultato_live.strip().split("-"))
    except:
        st.error("⚠️ Inserisci un risultato valido (es. 1-1).")
        return

    # Label e filtro campionato
    label = label_match({"Odd home": quota_home, "Odd Away": quota_away})
    st.markdown(f"🔖 **Label identificato:** `{label}`")
    db_selected = st.session_state.get("campionato_corrente")
    if not db_selected:
        st.warning("⚠️ Nessun campionato selezionato.")
        return
    df["Label"] = df.apply(label_match, axis=1)
    df_filtered = df[(df["Label"] == label) & (df["country"] == db_selected)]
    if df_filtered.empty:
        st.warning("⚠️ Nessuna partita trovata con questo Label e campionato.")
        return

    # Filtra per live score al minuto
    matched = []
    for _, row in df_filtered.iterrows():
        home_goals = extract_minutes(pd.Series([row.get("minuti goal segnato home", "")]))
        away_goals = extract_minutes(pd.Series([row.get("minuti goal segnato away", "")]))
        if sum(m <= minuto_corrente for m in home_goals) == goal_home_live and \
           sum(m <= minuto_corrente for m in away_goals) == goal_away_live:
            matched.append(row)
    df_matched = pd.DataFrame(matched)
    st.success(f"✅ Trovate {len(df_matched)} partite con punteggio {goal_home_live}-{goal_away_live} al minuto {minuto_corrente}")

    # Definisci soglie ALL over
    soglie = [0.5, 1.5, 2.5, 3.5, 4.5]
    over_counts = {x: 0 for x in soglie}
    after1 = 0
    final_scores = []
    for _, row in df_matched.iterrows():
        total_goals = row['Home Goal FT'] + row['Away Goal FT']
        home_goals = extract_minutes(pd.Series([row.get("minuti goal segnato home", "")]))
        away_goals = extract_minutes(pd.Series([row.get("minuti goal segnato away", "")]))
        # almeno 1 goal dopo
        if any(m > minuto_corrente for m in home_goals + away_goals):
            after1 += 1
        # over X
        for x in soglie:
            if total_goals - (goal_home_live + goal_away_live) > x:
                over_counts[x] += 1
        final_scores.append(f"{int(row['Home Goal FT'])}-{int(row['Away Goal FT'])}")

    # Statistiche campionato
    st.markdown("### 📊 Statistiche Campionato (post-minuto selezionato)")
    st.markdown(f"% Partite con almeno 1 goal dopo minuto {minuto_corrente}: **{after1/len(df_matched)*100:.2f}%**")
    for x in soglie:
        st.markdown(f"OVER {x}: **{over_counts[x]/len(df_matched)*100:.2f}%**")

    st.markdown("### 🧾 Risultati Finali più frequenti")
    df_scores = pd.Series(final_scores).value_counts().reset_index()
    df_scores.columns = ['Risultato','Occorrenze']
    st.table(df_scores.head(6))

    # Grafici time frame campionato
    tf_bands = [(0,15),(16,30),(31,45),(46,60),(61,75),(76,90)]
    tf_labels = [f"{a}-{b}" for a,b in tf_bands]
    tf_counts = dict.fromkeys(tf_labels,0)
    for _, row in df_matched.iterrows():
        minutes = extract_minutes(pd.Series([row.get("minuti goal segnato home", "")])) + \
                  extract_minutes(pd.Series([row.get("minuti goal segnato away", "")]))
        for m in minutes:
            if m>minuto_corrente:
                for (a,b),lab in zip(tf_bands,tf_labels):
                    if a < m <= b:
                        tf_counts[lab] += 1
                        break
    df_tf = pd.DataFrame.from_dict(tf_counts, orient='index', columns=['Goal']).reset_index().rename(columns={'index':'TimeFrame'})

    c1,c2 = st.columns(2)
    with c1:
        fig1, ax1 = plt.subplots()
        ax1.bar(df_tf['TimeFrame'], df_tf['Goal']); ax1.set_title('Goal rimanenti per Time Frame')
        plt.xticks(rotation=45);
        st.pyplot(fig1)

    # Sezione squadra selezionata
    st.markdown("---")
    st.markdown("### 📊 Statistiche Squadra Selezionata")
    df_squadra = df_matched[(df_matched['Home']==squadra_casa)|(df_matched['Away']==squadra_ospite)]
    after1_sq=0; over_counts_sq={x:0 for x in soglie}; final_sq=[]
    for _,row in df_squadra.iterrows():
        tot=row['Home Goal FT']+row['Away Goal FT']
        mins=extract_minutes(pd.Series([row.get("minuti goal segnato home","")]))+ \
             extract_minutes(pd.Series([row.get("minuti goal segnato away","")]))
        if any(m>minuto_corrente for m in mins): after1_sq+=1
        for x in soglie:
            if tot-(goal_home_live+goal_away_live)>x: over_counts_sq[x]+=1
        final_sq.append(f"{int(row['Home Goal FT'])}-{int(row['Away Goal FT'])}")
    st.markdown(f"% Squadra con almeno 1 goal dopo minuto {minuto_corrente}: **{after1_sq/len(df_squadra)*100:.2f}%**")
    for x in soglie:
        st.markdown(f"OVER {x}: **{over_counts_sq[x]/len(df_squadra)*100:.2f}%**")
    st.markdown("#### Risultati Squadra più frequenti")
    df_freq_sq=pd.Series(final_sq).value_counts().reset_index(); df_freq_sq.columns=['Risultato','Occorrenze']
    st.table(df_freq_sq.head(6))

    with c2:
        fig2, ax2 = plt.subplots()
        ax2.bar(df_tf['TimeFrame'], df_tf['Goal'], color='teal')
        ax2.set_title('Distribuzione Squadra per Time Frame')
        plt.xticks(rotation=45)
        st.pyplot(fig2)

# Fine modulo
