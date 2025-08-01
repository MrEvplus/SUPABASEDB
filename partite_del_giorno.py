import streamlit as st
import pandas as pd
import numpy as np
from utils import load_supabase_table


def run_partite_del_giorno(df, db_selected):
    st.title("Partite del Giorno - Upload File")

    if df is None or df.empty:
        st.warning("⚠️ Nessun file caricato o file vuoto.")
        return

    st.success("✅ Colonne presenti nel dataset")
    st.write(df.columns.tolist())

    # Caricamento mappatura campionati da Supabase
    try:
        df_map = load_supabase_table("league_mapping")
        df_map["lookup_key"] = (
            df_map["excel_country"].astype(str).str.upper().str.strip()
            + "__"
            + df_map["excel_league"].astype(str).str.upper().str.strip()
        )
        league_dict = dict(zip(df_map["lookup_key"], df_map["db_league_code"]))
    except Exception as e:
        st.error(f"Errore caricamento mapping: {e}")
        return

    unique_matches = df[["match", "country", "league"]].drop_duplicates()
    selected_match = st.selectbox("Seleziona la partita:", unique_matches["match"])
    match_row = unique_matches[unique_matches["match"] == selected_match].iloc[0]

    excel_country = str(match_row["country"]).strip().upper()
    excel_league = str(match_row["league"]).strip().upper()
    lookup_key = f"{excel_country}__{excel_league}"

    match_db = league_dict.get(lookup_key)

    if not match_db:
        st.warning(f"⚠️ Mapping non trovato per: {excel_country} / {excel_league}")
        return

    # 🔁 Sovrascrive la selezione del campionato per visualizzare le macro stats corrette
    if match_db != db_selected:
        db_selected = match_db

    st.info(f"Campionato matchato: {db_selected}")

    # Mostra statistiche legate al campionato selezionato (da db_selected)
    st.subheader(f"Statistiche per {selected_match} ({db_selected})")
    # Qui puoi inserire le sezioni successive che caricano le statistiche da supabase/database

    # Placeholder per sezioni successive
    st.success("✅ Placeholder sezioni statistiche macro / team / confronto")
