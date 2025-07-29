import streamlit as st
import pandas as pd
from supabase import create_client
from utils import load_data_from_supabase, load_data_from_file, SUPABASE_URL, SUPABASE_KEY

def run_mappa_leghe_supabase():
    st.set_page_config(page_title="Mappa Leghe Supabase", layout="wide")
    st.title("🗺️ Mappatura Manuale Campionati su Supabase")

    # Connessione Supabase
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Origine dati
    origine = st.radio("Origine dati:", ["Supabase", "Upload Manuale"])

    if origine == "Supabase":
        df, _ = load_data_from_supabase(parquet_label="🗺️ URL Parquet (Mappatura Leghe)")
    else:
        df, _ = load_data_from_file()

    if "country" not in df.columns:
        st.error("❌ Il file caricato non contiene la colonna 'country'.")
        st.stop()

    # Codici unici
    codici = sorted(df["country"].dropna().unique().tolist())

    # Leggi mappatura esistente da Supabase
    try:
        response = supabase.table("league_mapping").select("*").execute()
        existing_rows = response.data if response.data else []
    except Exception as e:
        st.error(f"Errore nel recupero dati da Supabase: {e}")
        existing_rows = []

    # Costruisci DataFrame modificabile
    existing_dict = {r["code"]: r["league_name"] for r in existing_rows}
    data = [{"code": code, "league_name": existing_dict.get(code, "")} for code in codici]

    df_edit = pd.DataFrame(data)
    st.markdown("✏️ Inserisci il nome reale dei campionati corrispondenti ai codici nel tuo file Parquet.")
    edited = st.data_editor(df_edit, num_rows="dynamic", use_container_width=True)

    if st.button("💾 Salva mappatura su Supabase"):
        supabase.table("league_mapping").delete().neq("code", "").execute()
        supabase.table("league_mapping").insert(edited.to_dict(orient="records")).execute()
        st.success("✅ Mappatura aggiornata con successo!")