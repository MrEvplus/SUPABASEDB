import streamlit as st
import pandas as pd

from macros import run_macro_stats
from squadre import run_team_stats
from pre_match import run_pre_match
from correct_score_ev_sezione import run_correct_score_ev


def run_partite_del_giorno(df, db_selected):
    """
    Sezione per caricare e selezionare le partite del giorno.
    Accetta il dataframe completo e la chiave del db selezionato.
    """
    st.title("📅 Partite del Giorno - Upload File")
    uploaded_file = st.file_uploader(
        "Carica il file delle partite del giorno (CSV, XLSX, XLS):",
        type=["csv", "xlsx", "xls"],
        key="file_uploader_today"
    )

    if uploaded_file is not None:
        # Lettura del file con gestione di vari formati e delimitatori
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

        # Mapping colonne nome squadre
        if "txtechipa1" in df_today.columns and "txtechipa2" in df_today.columns:
            df_today["Home"] = df_today["txtechipa1"]
            df_today["Away"] = df_today["txtechipa2"]

        # Fallback colonne codechipa
        if "Home" not in df_today.columns or "Away" not in df_today.columns:
            if "codechipa1" in df_today.columns and "codechipa2" in df_today.columns:
                df_today["Home"] = df_today["codechipa1"]
                df_today["Away"] = df_today["codechipa2"]
            else:
                st.error("⚠️ Il file deve contenere 'txtechipa1'/'txtechipa2' o 'codechipa1'/'codechipa2'.")
                st.stop()

        # Creiamo la lista delle partite
        df_today["match_str"] = df_today.apply(lambda r: f"{r['Home']} vs {r['Away']}", axis=1)
        matches = df_today["match_str"].tolist()

        # Seleziona la partita
        selected = st.selectbox("Seleziona la partita:", options=matches, key="selected_match")

        if selected:
            casa, ospite = selected.split(" vs ")
            st.session_state["squadra_casa"] = casa
            st.session_state["squadra_ospite"] = ospite

            # Determina il campionato dalla riga selezionata, se disponibile
            # Usa colonne 'league' o 'country' come db_selected
            if 'league' in df_today.columns:
                match_db = df_today.loc[df_today['match_str']==selected, 'league'].iloc[0]
            elif 'country' in df_today.columns:
                match_db = df_today.loc[df_today['match_str']==selected, 'country'].iloc[0]
            else:
                match_db = db_selected

            # Mostriamo le statistiche filtrate sul campionato della partita
            st.markdown(f"### Statistiche per {casa} vs {ospite} ({match_db})")
            run_macro_stats(df, match_db)
            run_team_stats(df, match_db)
            run_pre_match(df, match_db)
            run_correct_score_ev(df, match_db)

            # Pulsante per tornare indietro
            if st.button("🔙 Torna indietro"):
                del st.session_state["selected_match"]
                st.session_state["squadra_casa"] = ""
                st.session_state["squadra_ospite"] = ""
                st.experimental_rerun()
    else:
        st.info("ℹ️ Carica un file per visualizzare le partite del giorno.")