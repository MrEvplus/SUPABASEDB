import streamlit as st
from utils import SUPABASE_URL, SUPABASE_KEY
import pandas as pd
import numpy as np
import json
import requests
import base64
from datetime import date

from macros import run_macro_stats
from squadre import run_team_stats
from pre_match import run_pre_match
from correct_score_ev_sezione import run_correct_score_ev
from utils import load_data_from_supabase, load_data_from_file, label_match, SUPABASE_URL, SUPABASE_KEY
from supabase import create_client
from api_football_utils import get_fixtures_today_for_countries
from ai_inference import run_ai_inference
from analisi_live_minuto import run_live_minute_analysis
from partite_del_giorno import run_partite_del_giorno
from mappa_leghe_supabase import run_mappa_leghe_supabase
from reverse_engineering import run_reverse_engineering



def get_league_mapping():
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        data = supabase.table("league_mapping").select("*").execute().data
        return {r["code"]: r["league_name"] for r in data}
    except:
        return {}

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
        "Correct Score EV",
        "Analisi Live da Minuto",
        "Partite del Giorno",
        "🧠 Reverse Engineering EV+",
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
    league_dict = get_league_mapping()
    db_selected = league_dict.get(db_selected, db_selected)
else:
    df, db_selected = load_data_from_file()
    league_dict = get_league_mapping()
    db_selected = league_dict.get(db_selected, db_selected)
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
# MAPPING COLONNE COMPLETO E PULIZIA
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
    "cotaa": "Odd Home",
    "cotad": "Odd Away",
    "cotae": "Odd Draw",
    "cotao0": "Odd Over 0.5",
    "cotao1": "Odd Over 1.5",
    "cotao": "Odd Over 2.5",
    "cotao3": "Odd Over 3.5",
    "cotao4": "Odd Over 4.5",
    "cotau0": "Odd Under 0.5",
    "cotau1": "Odd Under 1.5",
    "cotau": "Odd Under 2.5",
    "cotau3": "Odd Under 3.5",
    "cotau4": "Odd Under 4.5",
    "gg": "GG",
    "ng": "NG",
    "elohomeo": "ELO Home",
    "eloawayo": "ELO Away",
    "formah": "Form Home",
    "formaa": "Form Away",
    "suth": "Tiri Totali Home FT",
    "suth1": "Tiri Home 1T",
    "suth2": "Tiri Home 2T",
    "suta": "Tiri Totali Away FT",
    "suta1": "Tiri Away 1T",
    "suta2": "Tiri Away 2T",
    "sutht": "Tiri in Porta Home FT",
    "sutht1": "Tiri in Porta Home 1T",
    "sutht2": "Tiri in Porta Home 2T",
    "sutat": "Tiri in Porta Away FT",
    "sutat1": "Tiri in Porta Away 1T",
    "sutat2": "Tiri in Porta Away 2T",
    "mgolh": "Minuti Goal Home",
    "gh1": "Home Goal 1 (min)",
    "gh2": "Home Goal 2 (min)",
    "gh3": "Home Goal 3 (min)",
    "gh4": "Home Goal 4 (min)",
    "gh5": "Home Goal 5 (min)",
    "gh6": "Home Goal 6 (min)",
    "gh7": "Home Goal 7 (min)",
    "gh8": "Home Goal 8 (min)",
    "gh9": "Home Goal 9 (min)",
    "mgola": "Minuti Goal Away",
    "ga1": "Away Goal 1 (min)",
    "ga2": "Away Goal 2 (min)",
    "ga3": "Away Goal 3 (min)",
    "ga4": "Away Goal 4 (min)",
    "ga5": "Away Goal 5 (min)",
    "ga6": "Away Goal 6 (min)",
    "ga7": "Away Goal 7 (min)",
    "ga8": "Away Goal 8 (min)",
    "ga9": "Away Goal 9 (min)",
    "stare": "Stare",
    "codechipa1": "CodeChipa1",
    "codechipa2": "CodeChipa2"
}
df.rename(columns=col_map, inplace=True)
df.columns = (
    df.columns
      .astype(str)
      .str.strip()
      .str.replace(r"[\n\r\t]", "", regex=True)
      .str.replace(r"\s+", " ", regex=True)
)
if "Label" not in df.columns:
    df["Label"] = df.apply(label_match, axis=1)

if "Stagione" in df.columns:
    stagioni_disponibili = sorted(df["Stagione"].dropna().unique())

    opzione_range = st.sidebar.selectbox(
        "Seleziona un intervallo stagioni predefinito:",
        ["Tutte", "Ultime 3", "Ultime 5", "Ultime 10", "Personalizza"]
    )

    if opzione_range == "Tutte":
        stagioni_scelte = stagioni_disponibili
    elif opzione_range == "Ultime 3":
        stagioni_scelte = stagioni_disponibili[-3:]
    elif opzione_range == "Ultime 5":
        stagioni_scelte = stagioni_disponibili[-5:]
    elif opzione_range == "Ultime 10":
        stagioni_scelte = stagioni_disponibili[-10:]
    else:
        stagioni_scelte = st.sidebar.multiselect(
            "Seleziona manualmente le stagioni da includere:",
            options=stagioni_disponibili,
            default=stagioni_disponibili
        )

    if stagioni_scelte:
        df = df[df["Stagione"].isin(stagioni_scelte)]

with st.expander("✅ Colonne presenti nel dataset", expanded=False):
    st.write(list(df.columns))

if "Home" not in df.columns:
    st.error("⚠️ La colonna 'Home' non esiste nel dataset selezionato.")
    st.stop()

if "Data" in df.columns:
    df["Data"] = pd.to_datetime(df["Data"], format="%Y-%m-%d", errors='coerce')
    today = pd.Timestamp.today().normalize()
    df = df[(df["Data"].isna()) | (df["Data"] <= today)]

if menu_option == "Macro Stats per Campionato":
    run_macro_stats(df, db_selected)
elif menu_option == "Statistiche per Squadre":
    run_team_stats(df, db_selected)
elif menu_option == "Confronto Pre Match":
    run_pre_match(df, db_selected)
elif menu_option == "Correct Score EV":
    run_correct_score_ev(df, db_selected)
elif menu_option == "Analisi Live da Minuto":
    run_live_minute_analysis(df)
elif menu_option == "Partite del Giorno":
    run_partite_del_giorno(df, db_selected)
elif menu_option == "📅 Reverse Engineering":
    run_reverse_engineering(df)


