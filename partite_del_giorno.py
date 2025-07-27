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
        # Lettura in base all'estensione con fallback encoding
        try:
            name = uploaded_file.name.lower()
            if name.endswith(('.xls', '.xlsx')):
                df_today = pd.read_excel(uploaded_file)
            else:
                try:
                    df_today = pd.read_csv(uploaded_file)
                except UnicodeDecodeError:
                    uploaded_file.seek(0)
                    df_today = pd.read_csv(uploaded_file, encoding='latin1')
        except Exception as e:
            st.error(f"Errore nel caricamento del file: {e}")
            st.stop()

        # Fall-back colonne Home/Away se mancanti
        if "Home" not in df_today.columns or "Away" not in df_today.columns:
            if "codechipa1" in df_today.columns and "codechipa2" in df_today.columns:
                df_today["Home"] = df_today["codechipa1"]
                df_today["Away"] = df_today["codechipa2"]
            else:
                st.error("⚠️ Il file deve contenere le colonne 'Home' e 'Away', o in alternativa 'codechipa1' e 'codechipa2'.")
                st.stop()

        # Creazione lista partite
        df_today["match_str"] = df_today.apply(
            lambda r: f"{r['Home']} vs {r['Away']}",
            axis=1
        )
        matches = df_today["match_str"].tolist()

        # Selezione partita
        selected = st.selectbox(
            "Seleziona la partita:",
            options=matches,
            key="selected_match"
        )

        if selected:
            casa, ospite = selected.split(" vs ")
            st.session_state["squadra_casa"] = casa
            st.session_state["squadra_ospite"] = ospite

            st.markdown(f"### Statistiche per {casa} vs {ospite}")
            # Richiama le funzioni principali con le due squadre impostate
            run_macro_stats(df, db_selected)
            run_team_stats(df, db_selected)
            run_pre_match(df, db_selected)
            run_correct_score_ev(df, db_selected)

            # Pulsante torni indietro
            if st.button("🔙 Torna indietro"):
                del st.session_state["selected_match"]
                st.session_state["squadra_casa"] = ""
                st.session_state["squadra_ospite"] = ""
                st.experimental_rerun()
    else:
        st.info("ℹ️ Carica un file per visualizzare le partite del giorno.")
