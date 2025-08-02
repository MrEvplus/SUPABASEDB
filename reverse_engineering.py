
import streamlit as st
import pandas as pd
from pre_match import run_pre_match
from utils import label_match

def run_reverse_engineering(df):
    st.title("🧠 Reverse Engineering da Calendario")

    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    selected_date = st.date_input("📅 Seleziona una data già passata:", value=pd.Timestamp.today().date() - pd.Timedelta(days=1))

    df_giocate = df[df["Data"] == pd.Timestamp(selected_date)]
    if df_giocate.empty:
        st.warning("⚠️ Nessuna partita trovata in quella data.")
        return

    st.markdown("### 📋 Partite giocate in quella giornata:")
    st.dataframe(df_giocate[["Home", "Away", "Odd home", "Odd Draw", "Odd Away", "Home Goal FT", "Away Goal FT"]], use_container_width=True)

    partita_selezionata = st.selectbox("🎯 Seleziona una partita per analisi retrospettiva:",
                                       [f"{row['Home']} vs {row['Away']}" for _, row in df_giocate.iterrows()])

    selected_row = df_giocate.iloc[
        [i for i, r in enumerate(df_giocate.itertuples()) if f"{r.Home} vs {r.Away}" == partita_selezionata][0]
    ]

    # Filtra il DB solo con partite <= giorno prima
    df_passato = df[df["Data"] < selected_row["Data"]].copy()

    if df_passato.empty:
        st.error("❌ Nessun dato disponibile fino al giorno prima.")
        return

    st.subheader("🔍 Simulazione pre-match con dati fino al giorno prima")

    # Imposta session state
    st.session_state["squadra_casa"] = selected_row["Home"]
    st.session_state["squadra_ospite"] = selected_row["Away"]
    st.session_state["quota_home"] = selected_row.get("Odd home", 2.00)
    st.session_state["quota_away"] = selected_row.get("Odd Away", 3.00)
    st.session_state["label_corrente"] = label_match(selected_row)

    st.markdown(f"**🎯 Label calcolata:** `{st.session_state['label_corrente']}`")

    # Mostra l'analisi pre-match
    run_pre_match(df_passato, db_selected=selected_row["country"])

    # Confronto con risultato reale
    st.markdown("---")
    st.subheader("📈 Esito Reale")
    st.write(f"🏠 {selected_row['Home']} {selected_row['Home Goal FT']} - {selected_row['Away Goal FT']} {selected_row['Away']}")
