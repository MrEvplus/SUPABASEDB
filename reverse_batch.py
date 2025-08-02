
import streamlit as st
import pandas as pd
from utils import label_match
from squadre import compute_team_macro_stats
from datetime import datetime

def run_reverse_batch(df):
    st.title("🧠 Reverse Batch - Analisi multipla EV+")

    df["Data"] = pd.to_datetime(df["Data"], errors="coerce").dt.normalize()
    selected_date = st.date_input("📅 Seleziona una data da analizzare:", value=datetime.today().date())

    df_day = df[df["Data"] == pd.to_datetime(selected_date)]
    if df_day.empty:
        st.warning("⚠️ Nessuna partita trovata in questa data.")
        return

    st.info(f"📊 Partite trovate per il {selected_date.strftime('%d/%m/%Y')}: {len(df_day)}")

    risultati = []

    for _, row in df_day.iterrows():
        home = row["Home"]
        away = row["Away"]
        label = label_match(row)
        quota_over = row.get("odd over 2,5", None)
        quota_under = row.get("odd under 2,5", None)
        gol_home = row.get("Home Goal FT", 0)
        gol_away = row.get("Away Goal FT", 0)
        data_match = row["Data"]

        if pd.isna(quota_over) or pd.isna(quota_under):
            continue

        df_passato = df[df["Data"] < data_match].copy()
        df_passato["Label"] = df_passato.apply(label_match, axis=1)
        df_filtrato = df_passato[df_passato["Label"] == label]

        if df_filtrato.empty:
            continue

        df_validi = df_filtrato.dropna(subset=["Home Goal FT", "Away Goal FT"])
        if df_validi.empty:
            continue

        over_hits = (df_validi["Home Goal FT"] + df_validi["Away Goal FT"] > 2.5).sum()
        total_matches = len(df_validi)
        over_pct = over_hits / total_matches if total_matches > 0 else 0

        ev_over = (quota_over * over_pct) - 1
        match_result = "✅" if (gol_home + gol_away) > 2.5 else "❌"
        profitto = (quota_over - 1) if match_result == "✅" else -1

        risultati.append({
            "Match": f"{home} vs {away}",
            "Label": label,
            "Quota Over 2.5": quota_over,
            "Probabilità Over": round(over_pct * 100, 1),
            "EV Over": round(ev_over * 100, 1),
            "Risultato Reale": f"{gol_home}-{gol_away}",
            "Esito": match_result,
            "Profitto Over": round(profitto, 2)
        })

    if risultati:
        df_out = pd.DataFrame(risultati)
        st.dataframe(df_out, use_container_width=True)
        csv = df_out.to_csv(index=False).encode("utf-8")
        st.download_button("💾 Scarica CSV", data=csv, file_name="reverse_batch_output.csv", mime="text/csv")
    else:
        st.warning("⚠️ Nessun match valido per il calcolo EV+.")
