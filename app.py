import streamlit as st
import pandas as pd
import numpy as np
import json
import requests
import base64
from datetime import date
from macros import run_macro_stats
from squadre import run_team_stats
from pre_match_with_correct_score import run_pre_match
from utils import load_data_from_supabase, load_data_from_file, label_match
from supabase import create_client
from api_football_utils import get_fixtures_today_for_countries
from ai_inference import run_ai_inference


# -------------------------------------------------------
# CONFIGURAZIONE PAGINA
# -------------------------------------------------------
st.set_page_config(
    page_title="Trading Dashboard",
    layout="wide"
)

st.sidebar.title("📊 Trading Dashboard")

# -------------------------------------------------------
# MENU PRINCIPALE
# -------------------------------------------------------

menu_option = st.sidebar.radio(
    "Naviga tra le sezioni:",
    [
        "Macro Stats per Campionato",
        "Statistiche per Squadre",
        "Confronto Pre Match",
	"Domande AI",
        "Partite del Giorno",
        "Scarica Mappatura Leghe da API",
        "Correct Score EV"
    ]
)

# -------------------------------------------------------
# SELEZIONE ORIGINE DATI
# -------------------------------------------------------

origine_dati = st.sidebar.radio(
    "Seleziona origine dati:",
    ["Supabase", "Upload Manuale"]
)

if origine_dati == "Supabase":
    df, db_selected = load_data_from_supabase()
else:
    df, db_selected = load_data_from_file()

# -------------------------------------------------------
# SESSION STATE PER SELEZIONE SQUADRE
# -------------------------------------------------------

if "squadra_casa" not in st.session_state:
    st.session_state["squadra_casa"] = ""

if "squadra_ospite" not in st.session_state:
    st.session_state["squadra_ospite"] = ""

if "campionato_corrente" not in st.session_state:
    st.session_state["campionato_corrente"] = db_selected
else:
    if st.session_state["campionato_corrente"] != db_selected:
        st.session_state["squadra_casa"] = ""
        st.session_state["squadra_ospite"] = ""
        st.session_state["campionato_corrente"] = db_selected

# -------------------------------------------------------
# MAPPING COLONNE COMPLETO
# -------------------------------------------------------

col_map = {
    "country": "country",
    "sezonul": "Stagione",
    "datameci": "Data",
    "orameci": "Orario",
    "etapa": "Round",
    "txtechipa1": "Home",
    "txtechipa2": "Away",
    "scor1": "Home Goal FT",
    "scor2": "Away Goal FT",
    "scorp1": "Home Goal 1T",
    "scorp2": "Away Goal 1T",
    "place1": "Posizione Classifica Generale",
    "place1a": "Posizione Classifica Home",
    "place2": "Posizione Classifica Away Generale",
    "place2d": "Posizione classifica away",
    "cotaa": "Odd home",
    "cotad": "Odd Away",
    "cotae": "Odd Draw",
    "cotao0": "odd over 0,5",
    "cotao1": "odd over 1,5",
    "cotao": "odd over 2,5",
    "cotao3": "odd over 3,5",
    "cotao4": "odd over 4,5",
    "cotau0": "odds under 0,5",
    "cotau1": "odd under 1,5",
    "cotau": "odd under 2,5",
    "cotau3": "odd under 3,5",
    "cotau4": "odd under 4,5",
    "gg": "gg",
    "ng": "ng",
    "elohomeo": "elohomeo",
    "eloawayo": "eloawayo",
    "formah": "form h",
    "formaa": "form a",
    "suth": "Tiri totali squadra HOME (full time)",
    "suth1": "Tiri squadra HOME 1 tempo",
    "suth2": "Tiri squadra HOME 2 tempo",
    "suta": "Tiri totali squadra AWAY (full time)",
    "suta1": "Tiri squadra AWAY 1 tempo",
    "suta2": "Tiri squadra AWAY 2 tempo",
    "sutht": "Tiri in porta squadra HOME (full time)",
    "sutht1": "Tiri in porta squadra HOME 1 tempo",
    "sutht2": "Tiri in porta squadra HOME 2 tempo",
    "sutat": "Tiri in porta squadra AWAY (full time)",
    "sutat1": "Tiri in porta squadra AWAY 1 tempo",
    "sutat2": "Tiri in porta squadra AWAY 2 tempo",
    "mgolh": "minuti goal segnato home",
    "gh1": "home 1 goal segnato (min)",
    "gh2": "home 2 goal segnato(min)",
    "gh3": "home 3 goal segnato(min)",
    "gh4": "home 4 goal segnato(min)",
    "gh5": "home 5 goal segnato(min)",
    "gh6": "home 6 goal segnato(min)",
    "gh7": "home 7 goal segnato(min)",
    "gh8": "home 8 goal segnato(min)",
    "gh9": "home 9 goal segnato(min)",
    "mgola": "minuti goal segnato away",
    "ga1": "1 goal away (min)",
    "ga2": "2 goal away (min)",
    "ga3": "3 goal away (min)",
    "ga4": "4 goal away (min)",
    "ga5": "5 goal away (min)",
    "ga6": "6 goal away (min)",
    "ga7": "7 goal away (min)",
    "ga8": "8 goal away (min)",
    "ga9": "9 goal away (min)",
    "stare": "stare",
    "codechipa1": "codechipa1",
    "codechipa2": "codechipa2"
}

df.rename(columns=col_map, inplace=True)

# Pulizia colonne
df.columns = (
    df.columns
    .astype(str)
    .str.strip()
    .str.replace(r"[\n\r\t]", "", regex=True)
    .str.replace(r"\s+", " ", regex=True)
)

# Crea colonna Label se non presente
if "Label" not in df.columns:
    df["Label"] = df.apply(label_match, axis=1)

# Filtro multi-stagione
if "Stagione" in df.columns:
    stagioni_disponibili = sorted(df["Stagione"].dropna().unique())
    stagioni_scelte = st.sidebar.multiselect(
        "Seleziona le stagioni da includere nell'analisi:",
        options=stagioni_disponibili,
        default=stagioni_disponibili
    )
    if stagioni_scelte:
        df = df[df["Stagione"].isin(stagioni_scelte)]

# Debug colonne
st.write("✅ Colonne presenti nel dataset:")
st.write(list(df.columns))

# Controllo colonna essenziale "Home"
if "Home" not in df.columns:
    st.error("⚠️ La colonna 'Home' non esiste nel dataset selezionato.")
    st.stop()

# Eventuale filtro sulla data
if "Data" in df.columns:
    df["Data"] = pd.to_datetime(df["Data"], format="%Y-%m-%d", errors='coerce')
    today = pd.Timestamp.today().normalize()
    df = df[(df["Data"].isna()) | (df["Data"] <= today)]

# -------------------------------------------------------
# CHIAMATA MODULI
# -------------------------------------------------------

if menu_option == "Macro Stats per Campionato":
    run_macro_stats(df, db_selected)

elif menu_option == "Statistiche per Squadre":
    run_team_stats(df, db_selected)

elif menu_option == "Confronto Pre Match":
    run_pre_match(df, db_selected)

elif menu_option == "Domande AI":
    run_ai_inference(df, db_selected)  # ✅ aggiunto per attivare l'intelligenza artificiale

elif menu_option == "Scarica Mappatura Leghe da API":
    st.title("🔎 Scarica Mappatura Leghe da API-FOOTBALL")

    if st.button("Scarica elenco leghe da API-FOOTBALL"):
        API_KEY = st.secrets["API_FOOTBALL_KEY"]
        st.write("✅ Chiave API caricata:", API_KEY)

        url = "https://v3.football.api-sports.io/leagues"

        headers = {
            'x-rapidapi-host': "v3.football.api-sports.io",
            'x-rapidapi-key': API_KEY
        }

        response = requests.get(url, headers=headers)

        st.write("✅ Status code API:", response.status_code)

        data = response.json()
        st.write("✅ JSON restituito dalla API:")
        st.json(data)

        if "response" not in data or len(data["response"]) == 0:
            st.warning("⚠️ Nessuna lega trovata o errore nella risposta API.")
        else:
            leagues = []

            for l in data.get("response", []):
                country_name = l["country"]["name"]
                league_name = l["league"]["name"]
                league_id = l["league"]["id"]

                leagues.append({
                    "Country": country_name,
                    "League": league_name,
                    "LeagueID": league_id
                })

            df_leagues = pd.DataFrame(leagues)

            st.success(f"Scaricate {len(df_leagues)} leghe.")
            st.dataframe(df_leagues, use_container_width=True)

            csv = df_leagues.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="💾 Scarica CSV mapping leghe",
                data=csv,
                file_name="leagues_mapping.csv",
                mime="text/csv"
            )

elif menu_option == "Partite del Giorno":
    st.title("📅 Partite del Giorno - Campionati presenti nel Database")

    campionati_db = sorted(df["country"].dropna().unique().tolist())
    st.info(f"Campionati presenti nel DB: {campionati_db}")

    country_mapping = {
        "Ita1": "Italy",
        "Spa1": "Spain",
        "Ger1": "Germany",
        "Fra1": "France",
        "Eng1": "England",
        "Ice1": "Iceland",
    }

    campionati_api = [
        country_mapping.get(c, None) for c in campionati_db
    ]
    campionati_api = [c for c in campionati_api if c is not None]

    st.info(f"Campionati convertiti per API Football: {campionati_api}")

    if st.button("Carica Partite di Oggi"):
        df_matches = get_fixtures_today_for_countries(campionati_api)

        if df_matches.empty:
            st.info("⚠️ Nessuna partita trovata per oggi nei campionati presenti nel database.")
        else:
            st.success(f"Trovate {len(df_matches)} partite nei campionati presenti nel DB.")
            st.dataframe(df_matches, use_container_width=True)

            csv = df_matches.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="💾 Scarica CSV",
                data=csv,
                file_name="partite_oggi.csv",
                mime="text/csv"
            )


elif menu_option == "Correct Score EV":
    from correct_score_ev_sezione import run_correct_score_ev
    run_correct_score_ev(df)
