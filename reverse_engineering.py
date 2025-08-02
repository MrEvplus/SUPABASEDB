
import streamlit as st
import pandas as pd
from datetime import datetime
from utils import label_match
from reverse_batch import run_reverse_batch


def run_single_analysis(df):
    from pre_match import run_pre_match

    df["Data"] = pd.to_datetime(df["Data"], errors="coerce").dt.normalize()
    selected_date = st.date_input("📅 Seleziona una data passata (singola partita):", value=datetime.today().date())

    df_giocate = df[df["Data"] == pd.to_datetime(selected_date)]
    if df_giocate.empty:
        st.warning("⚠️ Nessuna partita trovata in quella data.")
        return

    # Colonne dinamiche per evitare KeyError
    columns_to_show = [
        "Home", "Away", "Odd home", "Odd Draw", "Odd Away",
        "odd over 2,5", "odd under 2,5", "Home Goal FT", "Away Goal FT"
    ]
    columns_available = [col for col in columns_to_show if col in df_giocate.columns]
    st.dataframe(df_giocate[columns_available], use_container_width=True)

    partita_selezionata = st.selectbox("🎯 Seleziona una partita per analisi retrospettiva:",
                                       [f"{row['Home']} vs {row['Away']}" for _, row in df_giocate.iterrows()])

    selected_row = df_giocate.iloc[
        [i for i, r in enumerate(df_giocate.itertuples()) if f"{r.Home} vs {r.Away}" == partita_selezionata][0]
    ]

    # Prepara dataset pre-gara
    df_passato = df[df["Data"] < selected_row["Data"]].copy()
    if df_passato.empty:
        st.error("❌ Nessun dato disponibile fino al giorno prima.")
        return

    st.subheader("🔍 Simulazione pre-match con dati fino al giorno prima")

    # Set variabili in sessione
    st.session_state["squadra_casa"] = selected_row["Home"]
    st.session_state["squadra_ospite"] = selected_row["Away"]
    st.session_state["quota_home"] = selected_row.get("Odd home", 2.00)
    st.session_state["quota_draw"] = selected_row.get("Odd Draw", 3.20)
    st.session_state["quota_away"] = selected_row.get("Odd Away", 3.00)
    st.session_state["quota_over"] = selected_row.get("odd over 2,5", 2.00)
    st.session_state["quota_under"] = selected_row.get("odd under 2,5", 1.80)
    st.session_state["label_corrente"] = label_match(selected_row)

    st.markdown(f"**🎯 Label calcolata:** `{st.session_state['label_corrente']}`")

    run_pre_match(df_passato, db_selected=selected_row["country"])

    # Esito reale
    st.markdown("---")
    st.subheader("📈 Esito Reale")
    st.write(f"🏠 {selected_row['Home']} {selected_row['Home Goal FT']} - {selected_row['Away Goal FT']} {selected_row['Away']}")

def run_reverse_engineering(df):
    st.title("🧠 Reverse Engineering EV+")

    tab1, tab2, tab3 = st.tabs(["📅 Analisi Singola", "📦 Batch Giornaliero", "🔍 Pattern Ricorrenti"])

    with tab1:
        run_single_analysis(df)

    with tab2:
        run_reverse_batch(df)

    with tab3:
        run_pattern_analysis()



def run_pattern_analysis(uploaded_df=None):
    import pandas as pd
    st.subheader("🔍 Pattern Ricorrenti EV+")

    if uploaded_df is None:
        uploaded_file = st.file_uploader("📤 Carica il file CSV generato dal Reverse Batch:", type="csv")
        if uploaded_file is None:
            st.info("Carica un file per iniziare.")
            return
        df = pd.read_csv(uploaded_file)
    else:
        df = uploaded_df.copy()

    st.success(f"✅ {len(df)} righe caricate per l'analisi.")

    # Pulisci EV
    df["EV Over %"] = pd.to_numeric(df["EV Over %"], errors="coerce")
    df["Profitto"] = pd.to_numeric(df["Profitto"], errors="coerce")
    df["Label"] = df["Label"].fillna("Unknown")

    # Raggruppa per label
    group = df.groupby("Label").agg(
        Partite=("Match", "count"),
        EV_medio=("EV Over %", "mean"),
        ROI_totale=("Profitto", "sum"),
        ROI_medio=("Profitto", "mean"),
        WinOverPct=("Esito", lambda x: (x == "✅").mean() * 100)
    ).reset_index()

    group = group.round(2)
    group = group.sort_values(by="EV_medio", ascending=False)

    st.markdown("### 🧠 Pattern per Label")
    st.dataframe(group, use_container_width=True)

    st.markdown("### 🟢 Pattern EV+ con ROI medio positivo e almeno 5 partite")
    df_filtered = group[(group["Partite"] >= 5) & (group["ROI_medio"] > 0) & (group["EV_medio"] > 0)]
    st.dataframe(df_filtered, use_container_width=True)

    csv = df_filtered.to_csv(index=False).encode("utf-8")
    st.download_button("💾 Scarica Pattern EV+ CSV", data=csv, file_name="pattern_ev_plus.csv", mime="text/csv")
