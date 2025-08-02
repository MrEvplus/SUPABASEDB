
import streamlit as st
import pandas as pd
from datetime import datetime
from utils import label_match
from reverse_batch import run_reverse_batch
from pattern_analysis import run_pattern_analysis

def run_single_analysis(df):
    from pre_match import run_pre_match

    df["Data"] = pd.to_datetime(df["Data"], errors="coerce").dt.normalize()
    selected_date = st.date_input("📅 Seleziona una data passata (singola partita):", value=datetime.today().date())

    df_giocate = df[df["Data"] == pd.to_datetime(selected_date)]
    if df_giocate.empty:
        st.warning("⚠️ Nessuna partita trovata in quella data.")
        return

    # Colonne dinamiche per evitare KeyError
    columns_to_show = [
        "Home", "Away", "Odd home", "Odd Draw", "Odd Away",
        "odd over 2,5", "odd under 2,5", "Home Goal FT", "Away Goal FT"
    ]
    columns_available = [col for col in columns_to_show if col in df_giocate.columns]
    st.dataframe(df_giocate[columns_available], use_container_width=True)

    partita_selezionata = st.selectbox("🎯 Seleziona una partita per analisi retrospettiva:",
                                       [f"{row['Home']} vs {row['Away']}" for _, row in df_giocate.iterrows()])

    selected_row = df_giocate.iloc[
        [i for i, r in enumerate(df_giocate.itertuples()) if f"{r.Home} vs {r.Away}" == partita_selezionata][0]
    ]

    # Prepara dataset pre-gara
    df_passato = df[df["Data"] < selected_row["Data"]].copy()
    if df_passato.empty:
        st.error("❌ Nessun dato disponibile fino al giorno prima.")
        return

    st.subheader("🔍 Simulazione pre-match con dati fino al giorno prima")

    # Set variabili in sessione
    st.session_state["squadra_casa"] = selected_row["Home"]
    st.session_state["squadra_ospite"] = selected_row["Away"]
    st.session_state["quota_home"] = selected_row.get("Odd home", 2.00)
    st.session_state["quota_draw"] = selected_row.get("Odd Draw", 3.20)
    st.session_state["quota_away"] = selected_row.get("Odd Away", 3.00)
    st.session_state["quota_over"] = selected_row.get("odd over 2,5", 2.00)
    st.session_state["quota_under"] = selected_row.get("odd under 2,5", 1.80)
    st.session_state["label_corrente"] = label_match(selected_row)

    st.markdown(f"**🎯 Label calcolata:** `{st.session_state['label_corrente']}`")

    run_pre_match(df_passato, db_selected=selected_row["country"])

    # Esito reale
    st.markdown("---")
    st.subheader("📈 Esito Reale")
    st.write(f"🏠 {selected_row['Home']} {selected_row['Home Goal FT']} - {selected_row['Away Goal FT']} {selected_row['Away']}")

def run_reverse_engineering(df):
    st.title("🧠 Reverse Engineering EV+")

    tab1, tab2, tab3 = st.tabs(["📅 Analisi Singola", "📦 Batch Giornaliero", "🔍 Pattern Ricorrenti"])

    with tab1:
        run_single_analysis(df)

    with tab2:
        run_reverse_batch(df)

    with tab3:
        run_pattern_analysis()
