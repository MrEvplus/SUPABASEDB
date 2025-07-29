import streamlit as st
import pandas as pd
from supabase import create_client
from utils import load_data_from_supabase, load_data_from_file, SUPABASE_URL, SUPABASE_KEY

def run_mappa_leghe_supabase():
    st.set_page_config(page_title="Mappa Leghe Supabase", layout="wide")
    st.title("🗺️ Mappatura Manuale Campionati su Supabase")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    origine = st.radio("Origine dati:", ["Supabase", "Upload Manuale"])

    if origine == "Supabase":
        df, _ = load_data_from_supabase(parquet_label="🗺️ URL Parquet (Mappatura Leghe)", selectbox_key="selectbox_campionato_mappa_leghe")
    else:
        df, _ = load_data_from_file()

    if not all(col in df.columns for col in ["country", "league"]):
        st.error("❌ Il file deve contenere le colonne 'country' e 'league'.")
        st.stop()

    df_unique = df[["country", "league"]].drop_duplicates().reset_index(drop=True)

    # Leggi mappatura esistente da Supabase
    try:
        response = supabase.table("league_mapping").select("*").execute()
        existing = pd.DataFrame(response.data) if response.data else pd.DataFrame(columns=["code", "country", "league"])
    except Exception as e:
        st.error(f"Errore nel recupero dati da Supabase: {e}")
        existing = pd.DataFrame(columns=["code", "country", "league"])

    # Merge tra dati da mappare e mappatura esistente
    df_merge = df_unique.merge(existing, on=["country", "league"], how="left")

    # Mostra editor
    st.markdown("✏️ Inserisci o modifica il codice identificativo `code` per ciascun campionato (es. IT1, BR2, ecc.).")
    edited = st.data_editor(df_merge[["code", "country", "league"]], num_rows="dynamic", use_container_width=True)

    if st.button("💾 Salva mappatura su Supabase"):
        # Elimina tutto e reinserisci la nuova mappatura
        supabase.table("league_mapping").delete().neq("code", "").execute()
        supabase.table("league_mapping").insert(edited.dropna(subset=["code"]).to_dict(orient="records")).execute()
        st.success("✅ Mappatura aggiornata con successo!")
