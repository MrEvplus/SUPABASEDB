import numpy as np
import pandas as pd
import streamlit as st
import duckdb
import pandas as pd
import streamlit as st


# ----------------------------------------------------------
# Variabili di connessione Supabase
# ----------------------------------------------------------
SUPABASE_URL = "https://dqqlaamfxaconepbdjek.supabase.co"
SUPABASE_KEY = "eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV9hNjUxZjNmOC02NTMyLTQ3M2UtYWVhMy01MmM1ZDc3MTAwMzUiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJwYXJ0aXRlLnBhcnF1ZXQvcGFydGl0ZS5wYXJxdWV0IiwiaWF0IjoxNzUyMzU2NjYxLCJleHAiOjQ5MDU5NTY2NjF9.z0ihpL899yh9taqhx1uWs3CJQehrySmca7VRYm_K-AI"

# ----------------------------------------------------------
# Caricamento da DuckDB + Parquet su Supabase Storage
# ----------------------------------------------------------


def load_data_from_supabase(parquet_label="Parquet file URL (Supabase Storage):"):
    st.sidebar.markdown("### 🌐 Origine: Supabase Storage (Parquet via DuckDB)")

    parquet_url = st.sidebar.text_input(
        parquet_label,
        value="https://dqqlaamfxaconepbdjek.supabase.co/storage/v1/object/sign/partite.parquet/partite.parquet?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV9hNjUxZjNmOC02NTMyLTQ3M2UtYWVhMy01MmM1ZDc3MTAwMzUiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJwYXJ0aXRlLnBhcnF1ZXQvcGFydGl0ZS5wYXJxdWV0IiwiaWF0IjoxNzUyMzU2NjYxLCJleHAiOjQ5MDU5NTY2NjF9.z0ihpL899yh9taqhx1uWs3CJQehrySmca7VRYm_K-AI"
    )
        value="https://dqqlaamfxaconepbdjek.supabase.co/storage/v1/object/sign/partite.parquet/partite.parquet?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV9hNjUxZjNmOC02NTMyLTQ3M2UtYWVhMy01MmM1ZDc3MTAwMzUiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJwYXJ0aXRlLnBhcnF1ZXQvcGFydGl0ZS5wYXJxdWV0IiwiaWF0IjoxNzUyMzU2NjYxLCJleHAiOjQ5MDU5NTY2NjF9.z0ihpL899yh9taqhx1uWs3CJQehrySmca7VRYm_K-AI"
    )

    # Carico TUTTO il parquet senza filtri
    query_all = f"""
        SELECT *
        FROM read_parquet('{parquet_url}')
    """

    try:
        df_all = duckdb.query(query_all).to_df()
    except Exception as e:
        st.error(f"❌ Errore DuckDB: {str(e)}")
        st.stop()

    if df_all.empty:
        st.warning("⚠️ Nessun dato trovato nel Parquet.")
        st.stop()

    # Campionati disponibili
    if "country" in df_all.columns:
        campionati_disponibili = sorted(df_all["country"].dropna().unique())
    else:
        campionati_disponibili = []

    # Seleziona campionato
    campionato_scelto = st.sidebar.selectbox(
        "Seleziona Campionato:",
        [""] + campionati_disponibili,
        index=1 if len(campionati_disponibili) > 0 else 0,
        key="selectbox_campionato_duckdb"
    )

    if campionato_scelto == "":
        st.info("ℹ️ Seleziona un campionato per procedere.")
        st.stop()

    # Filtra solo il campionato scelto
    df_filtered = df_all[df_all["country"] == campionato_scelto]

    # 🔥 Estrai stagioni disponibili da questo campionato
    if "sezonul" in df_filtered.columns:
        stagioni_disponibili = sorted(df_filtered["sezonul"].dropna().unique())
    else:
        stagioni_disponibili = []

    # Menu a tendina stagioni (anche se vuoto)
    stagioni_scelte = st.sidebar.multiselect(
        "Seleziona le stagioni da includere nell'analisi:",
        options=stagioni_disponibili,
        default=stagioni_disponibili,
        key="multiselect_stagioni_duckdb"
    )

    if stagioni_scelte:
        df_filtered = df_filtered[df_filtered["sezonul"].isin(stagioni_scelte)]

    # Mapping colonne
    col_map = {
        "country": "country",
        "sezonul": "Stagione",
        "txtechipa1": "Home",
        "txtechipa2": "Away",
        "scor1": "Home Goal FT",
        "scor2": "Away Goal FT",
        "scorp1": "Home Goal 1T",
        "scorp2": "Away Goal 1T",
        "cotaa": "Odd home",
        "cotad": "Odd Away",
        "cotae": "Odd Draw",
        "mgolh": "minuti goal segnato home",
        "mgola": "minuti goal segnato away"
    }
    df_filtered.rename(columns=col_map, inplace=True)

    for col in df_filtered.columns:
        if df_filtered[col].dtype == object:
            df_filtered[col] = df_filtered[col].str.replace(",", ".")

    df_filtered = df_filtered.apply(pd.to_numeric, errors="ignore")

    if "Data" in df_filtered.columns:
        df_filtered["Data"] = pd.to_datetime(df_filtered["Data"], errors="coerce")

    st.sidebar.write(f"✅ Righe caricate da Parquet: {len(df_filtered)}")

    return df_filtered, campionato_scelto

# ----------------------------------------------------------
# Upload Manuale (Excel o CSV)
# ----------------------------------------------------------

def load_data_from_file():
    st.sidebar.markdown("### 📂 Origine: Upload Manuale")

    uploaded_file = st.sidebar.file_uploader(
        "Carica il tuo file Excel o CSV:",
        type=["xls", "xlsx", "csv"],
        key="file_uploader_upload"
    )

    if uploaded_file is None:
        st.info("ℹ️ Carica un file per continuare.")
        st.stop()

    # Riconosce CSV o Excel
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        xls = pd.ExcelFile(uploaded_file)
        sheet_name = xls.sheet_names[0]
        df = pd.read_excel(xls, sheet_name=sheet_name)

    # CORREZIONE FONDAMENTALE anche per upload manuale
    df.columns = df.columns.str.strip().str.lower()

    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].str.replace(",", ".")

    df = df.apply(pd.to_numeric, errors="ignore")

    if "datameci" in df.columns:
        df["datameci"] = pd.to_datetime(df["datameci"], errors="coerce")

    if "country" in df.columns:
        campionati_disponibili = sorted(df["country"].dropna().unique())
    else:
        campionati_disponibili = []

    campionato_scelto = st.sidebar.selectbox(
        "Seleziona Campionato:",
        [""] + campionati_disponibili,
        key="selectbox_campionato_upload"
    )

    if campionato_scelto == "":
        st.info("ℹ️ Seleziona un campionato per procedere.")
        st.stop()

    df_filtered = df[df["country"] == campionato_scelto]

    if "sezonul" in df_filtered.columns:
        stagioni_disponibili = sorted(df_filtered["sezonul"].dropna().unique())
    else:
        stagioni_disponibili = []

    stagioni_scelte = st.sidebar.multiselect(
        "Seleziona le stagioni da includere nell'analisi:",
        options=stagioni_disponibili,
        default=stagioni_disponibili,
        key="multiselect_stagioni_upload"
    )

    if stagioni_scelte:
        df_filtered = df_filtered[df_filtered["sezonul"].isin(stagioni_scelte)]

    st.sidebar.write(f"✅ Righe caricate da Upload Manuale: {len(df_filtered)}")

    return df_filtered, campionato_scelto

# ----------------------------------------------------------
# label_match
# ----------------------------------------------------------

def label_match(row):
    """
    Classifica il match in una fascia di quote
    basata sulle quote odd home e odd away.
    """

    try:
        h = float(row.get("Odd home", np.nan))
        a = float(row.get("Odd Away", np.nan))
    except:
        return "Others"

    if np.isnan(h) or np.isnan(a):
        return "Others"

    # SuperCompetitive
    if h <= 3 and a <= 3:
        return "SuperCompetitive H<=3 A<=3"

    # Classificazione Home
    if h < 1.5:
        return "H_StrongFav <1.5"
    elif 1.5 <= h <= 2:
        return "H_MediumFav 1.5-2"
    elif 2 < h <= 3:
        return "H_SmallFav 2-3"

    # Classificazione Away
    if a < 1.5:
        return "A_StrongFav <1.5"
    elif 1.5 <= a <= 2:
        return "A_MediumFav 1.5-2"
    elif 2 < a <= 3:
        return "A_SmallFav 2-3"

    return "Others"

# ----------------------------------------------------------
# extract_minutes
# ----------------------------------------------------------

def extract_minutes(series):
    """
    Estrae i minuti di goal da colonne tipo 'mgolh' o 'mgola'
    anche se NULL, vuote o contenenti solo ';'
    """
    all_minutes = []

    # Sostituisci NaN con stringa vuota
    series = series.fillna("")

    for val in series:
        val = str(val).strip()
        if val == "" or val == ";":
            continue
        parts = val.replace(",", ";").split(";")
        for part in parts:
            part = part.strip()
            if part.replace(".", "", 1).isdigit():
                all_minutes.append(int(float(part)))
    return all_minutes
