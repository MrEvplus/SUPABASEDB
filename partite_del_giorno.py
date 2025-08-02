import streamlit as st
import pandas as pd

from macros import run_macro_stats
from squadre import run_team_stats
from pre_match import run_pre_match
from correct_score_ev_sezione import run_correct_score_ev
from supabase import create_client

def get_league_mapping():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        supabase = create_client(url, key)
        data = supabase.table("league_mapping").select("*").execute().data
        df_map = pd.DataFrame(data)
        df_map["key"] = df_map["excel_country"].astype(str).str.strip().str.upper() + "__" + df_map["excel_league"].astype(str).str.strip().str.upper()
        return dict(zip(df_map["key"], df_map["db_league_code"]))
    except Exception as e:
        st.error(f"Errore caricamento mapping: {e}")
        return {}

def run_partite_del_giorno(df, db_selected):
    st.title("Partite del Giorno - Upload File")
    uploaded_file = st.file_uploader(
        "Carica il file delle partite del giorno (CSV, XLSX, XLS):",
        type=["csv", "xlsx", "xls"],
        key="file_uploader_today"
    )

    league_dict = get_league_mapping()

    if uploaded_file is not None:
        try:
            filename = uploaded_file.name.lower()
            if filename.endswith(('.xls', '.xlsx')):
                df_today = pd.read_excel(uploaded_file)
            else:
                uploaded_file.seek(0)
                try:
                    df_today = pd.read_csv(uploaded_file)
                except Exception:
                    uploaded_file.seek(0)
                    df_today = pd.read_csv(uploaded_file, sep=';', engine='python')
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            df_today = pd.read_csv(uploaded_file, sep=';', encoding='latin1', engine='python')
        except Exception as e:
            st.error(f"Errore nel caricamento del file: {e}")
            st.stop()

        if "txtechipa1" in df_today.columns and "txtechipa2" in df_today.columns:
            df_today["Home"] = df_today["txtechipa1"]
            df_today["Away"] = df_today["txtechipa2"]

        if "Home" not in df_today.columns or "Away" not in df_today.columns:
            if "codechipa1" in df_today.columns and "codechipa2" in df_today.columns:
                df_today["Home"] = df_today["codechipa1"]
                df_today["Away"] = df_today["codechipa2"]
            else:
                st.error("⚠️ Il file deve contenere 'txtechipa1'/'txtechipa2' o 'codechipa1'/'codechipa2'.")
                st.stop()

        df_today["match_str"] = df_today.apply(lambda r: f"{r['Home']} vs {r['Away']}", axis=1)

        # ✅ MOSTRA LISTA PARTITE CON CAMPIONATO E DATA
        st.markdown("### 📋 Lista Partite del Giorno")

        colonne_presenti = pd.Series(df_today.columns).str.lower()
        col_data = next((c for c in colonne_presenti if "data" in c or "datameci" in c), None)
        col_ora = next((c for c in colonne_presenti if "orario" in c or "orameci" in c), None)
        col_league = next((c for c in colonne_presenti if "league" in c or "etapa" in c), None)

        if col_data:
            df_today["Data Match"] = pd.to_datetime(df_today[col_data], errors="coerce")
        else:
            df_today["Data Match"] = pd.NaT

        if col_ora:
            try:
                df_today["Orario"] = pd.to_datetime(df_today[col_ora], errors="coerce").dt.time
            except:
                df_today["Orario"] = ""
        else:
            df_today["Orario"] = ""

        if col_data:
            df_today["Data Ora"] = df_today["Data Match"].dt.strftime("%Y-%m-%d") + " " + df_today["Orario"].astype(str)
        else:
            df_today["Data Ora"] = ""

        if col_league:
            df_today["Campionato"] = df_today[col_league]
        else:
            df_today["Campionato"] = df_today.get("country", "N/A")

        df_lista = df_today[["Campionato", "Data Ora", "Home", "Away"]].copy()
        df_lista.columns = ["Campionato", "Data", "Squadra Casa", "Squadra Ospite"]
        st.dataframe(df_lista, use_container_width=True)

        # Dropdown partita
        matches = df_today["match_str"].tolist()
        selected = st.selectbox("Seleziona la partita:", options=matches, key="selected_match")

        if selected:
            casa, ospite = selected.split(" vs ")
            st.session_state["squadra_casa"] = casa
            st.session_state["squadra_ospite"] = ospite

            row = df_today[df_today['match_str'] == selected].iloc[0]
            excel_country = str(row.get("country", "")).strip().upper()
            excel_league = str(row.get("league", "")).strip().upper()
            lookup_key = f"{excel_country}__{excel_league}"
            match_db = league_dict.get(lookup_key)

            if not match_db:
                st.warning(f"⚠️ Mapping non trovato per: {excel_country} / {excel_league}")
                return

            db_selected = match_db

            st.info(f"🔍 lookup_key: {lookup_key}")
            st.info(f"📌 db_league_code trovato: {match_db}")

            st.markdown(f"### Statistiche per {casa} vs {ospite} ({match_db})")
            run_macro_stats(df, match_db)
            run_team_stats(df, match_db)
            run_pre_match(df, match_db)
            run_correct_score_ev(df, match_db)

            if st.button("🔙 Torna indietro"):
                del st.session_state["selected_match"]
                st.session_state["squadra_casa"] = ""
                st.session_state["squadra_ospite"] = ""
                st.experimental_rerun()
    else:
        st.info("ℹ️ Carica un file per visualizzare le partite del giorno.")