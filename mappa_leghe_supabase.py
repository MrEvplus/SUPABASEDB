
import streamlit as st
import pandas as pd
from supabase import create_client
from utils import SUPABASE_URL, SUPABASE_KEY, load_data_from_supabase

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def run_mappa_leghe_supabase():
    st.header("🗺️ Mappatura Manuale Campionati su Supabase")

    origine = st.radio("Origine dati:", ["Supabase", "Upload Manuale"], index=0)

    if origine == "Supabase":
        try:
            response = supabase.table("league_mapping").select("*").execute()
            records = response.data
            df = pd.DataFrame(records)

            if df.empty or "country" not in df.columns or "league" not in df.columns:
                st.error("❌ Il file deve contenere le colonne 'country' e 'league'.")
                return

            st.success("✅ Dati correttamente caricati da Supabase.")
            st.dataframe(df)

        except Exception as e:
            st.error(f"Errore durante il recupero dei dati da Supabase: {e}")

    else:
        uploaded_file = st.file_uploader("Carica un file CSV con colonne 'country' e 'league':", type="csv")
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                if "country" not in df.columns or "league" not in df.columns:
                    st.error("❌ Il file deve contenere le colonne 'country' e 'league'.")
                    return

                st.success("✅ File caricato correttamente.")
                st.dataframe(df)

                if st.button("📤 Salva su Supabase"):
                    # Cancella prima i dati esistenti (opzionale)
                    supabase.table("league_mapping").delete().neq("code", "").execute()

                    # Inserisci nuovi dati
                    insert_data = df.to_dict(orient="records")
                    for chunk in [insert_data[i:i + 50] for i in range(0, len(insert_data), 50)]:
                        supabase.table("league_mapping").insert(chunk).execute()

                    st.success("✅ Dati salvati correttamente su Supabase.")

            except Exception as e:
                st.error(f"Errore durante la lettura o il salvataggio del file: {e}")
