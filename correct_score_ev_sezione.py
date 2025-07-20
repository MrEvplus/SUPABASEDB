
import streamlit as st
import pandas as pd
from utils import label_match

def run_correct_score_ev(df):
    st.title("🎯 Correct Score - Expected Value")

    if "squadra_casa" not in st.session_state or "squadra_ospite" not in st.session_state:
        st.warning("⚠️ Devi prima selezionare le squadre nella sezione 'Confronto Pre Match'.")
        return

    squadra_casa = st.session_state["squadra_casa"]
    squadra_ospite = st.session_state["squadra_ospite"]

    st.markdown(f"**Squadre selezionate:** `{squadra_casa}` vs `{squadra_ospite}`")

    if "Label" not in df.columns:
        df = df.copy()
        df["Label"] = df.apply(label_match, axis=1)

    if "quota_home" not in st.session_state or "quota_away" not in st.session_state:
                return

    # Ricava il label da quote già salvate
    from pre_match import label_from_odds
    label = label_from_odds(st.session_state["quota_home"], st.session_state["quota_away"])

    st.markdown(f"### 🏷️ Range di quota identificato (Label): `{label}`")

    df_cs = df.copy()
    df_cs["LabelTemp"] = df_cs.apply(label_match, axis=1)
    df_cs = df_cs[df_cs["LabelTemp"] == label]
    df_cs = df_cs[df_cs["Home Goal FT"].notna() & df_cs["Away Goal FT"].notna()]

    df_cs["CorrectScore"] = df_cs["Home Goal FT"].astype(int).astype(str) + "-" + df_cs["Away Goal FT"].astype(int).astype(str)

    top_cs = df_cs["CorrectScore"].value_counts().head(6).reset_index()
    top_cs.columns = ["Risultato", "Frequenza"]
    total_match = len(df_cs)

    top_cs["% su totale"] = top_cs["Frequenza"].apply(lambda x: round((x / total_match) * 100, 2))
    top_cs["Quota attuale"] = 0.0
    top_cs["EV"] = 0.0

    st.markdown(f"**Totale partite nel label `{label}`:** {total_match}")
    for i, row in top_cs.iterrows():
        col1, col2, col3, col4 = st.columns([1.5, 1, 1, 2])
        col1.markdown(f"**{row['Risultato']}**")
        col2.markdown(f"{row['Frequenza']} volte")
        col3.markdown(f"{row['% su totale']}%")
        quota = col4.number_input(f"Quota {row['Risultato']}", min_value=1.01, step=0.01, key=f"quota_cs_sezione_{label}_{i}")
        prob = row["% su totale"] / 100
        ev = (quota * prob) - 1
        top_cs.at[i, "Quota attuale"] = quota
        top_cs.at[i, "EV"] = round(ev, 3)

    st.markdown("### 🔍 Expected Value (EV) per Correct Score")
    def ev_label(ev):
        if ev > 0:
            return f"🟢 {ev} EV+"
        elif ev < 0:
            return f"🔴 {ev} EV-"
        return f"⚪️ {ev}"

    top_cs["EV Label"] = top_cs["EV"].apply(ev_label)
    st.dataframe(top_cs[["Risultato", "Frequenza", "% su totale", "Quota attuale", "EV Label"]], use_container_width=True)
