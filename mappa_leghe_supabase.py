import streamlit as st
import pandas as pd
from utils import load_data_from_supabase, load_data_from_file
from supabase import create_client

st.set_page_config(page_title="Mappa Leghe Supabase", layout="wide")
st.title("🗺️ Mappatura Manuale Campionati su Supabase")

# Connessione Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# Origine dati
origine = st.radio("Origine dati:", ["Supabase", "Upload Manuale"])

if origine == "Supabase":
    df, _ = load_data_from_supabase()
else:
    df, _ = load_data_from_file()

if "country" not in df.columns:
    st.error("❌ Il file caricato non contiene la colonna 'country'.")
    st.stop()

# Codici unici
codici = sorted(df["country"].dropna().unique().tolist())

# Leggi mappatura esistente da Supabase
response = supabase.table("league_mapping").select("*").execute()
existing_rows = response.data if response.data else []
existing_dict = {r["code"]: r["league_name"] for r in existing_rows}

# Costruisci editor
rows = []
for code in codici:
    league_name = existing_dict.get(code, "")
    rows.append({"code": code, "league_name": league_name})

df_editor = pd.DataFrame(rows)

st.markdown("### ✏️ Modifica i nomi reali dei campionati")
df_edited = st.data_editor(df_editor, num_rows="dynamic", use_container_width=True)

# Salvataggio in Supabase
if st.button("💾 Salva mappatura su Supabase"):
    try:
        # Cancella vecchi valori
        for code in codici:
            supabase.table("league_mapping").delete().eq("code", code).execute()

        # Inserisci nuovi valori
        data = df_edited.to_dict(orient="records")
        supabase.table("league_mapping").insert(data).execute()
        st.success("✅ Mappatura salvata correttamente su Supabase!")
    except Exception as e:
        st.error(f"❌ Errore durante il salvataggio: {e}")

# Preview
if st.checkbox("👁️ Visualizza mappatura salvata su Supabase"):
    st.dataframe(df_edited, use_container_width=True)
