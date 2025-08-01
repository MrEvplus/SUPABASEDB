import streamlit as st
import pandas as pd
from utils import label_match
from squadre import compute_team_macro_stats
from macros import run_macro_stats

# --------------------------------------------------------
# FUNZIONE PER OTTENERE LEAGUE DATA BY LABEL
# --------------------------------------------------------
def get_league_data_by_label(df, label):
    if "Label" not in df.columns:
        df = df.copy()
        df["Label"] = df.apply(label_match, axis=1)

    df["match_result"] = df.apply(
        lambda row: "Home Win" if row["Home Goal FT"] > row["Away Goal FT"]
        else "Away Win" if row["Home Goal FT"] < row["Away Goal FT"]
        else "Draw",
        axis=1
    )

    group_label = df.groupby("Label").agg(
        Matches=("Home", "count"),
        HomeWin_pct=("match_result", lambda x: (x == "Home Win").mean() * 100),
        Draw_pct=("match_result", lambda x: (x == "Draw").mean() * 100),
        AwayWin_pct=("match_result", lambda x: (x == "Away Win").mean() * 100)
    ).reset_index()

    row = group_label[group_label["Label"] == label]
    if not row.empty:
        return row.iloc[0].to_dict()
    else:
        return None

# --------------------------------------------------------
# LABEL FROM ODDS
# --------------------------------------------------------
def label_from_odds(home_odd, away_odd):
    fake_row = {
        "Odd home": home_odd,
        "Odd Away": away_odd
    }
    return label_match(fake_row)

# --------------------------------------------------------
# DETERMINA TIPO DI LABEL
# --------------------------------------------------------
def get_label_type(label):
    if label and label.startswith("H_"):
        return "Home"
    elif label and label.startswith("A_"):
        return "Away"
    else:
        return "Both"

# --------------------------------------------------------
# FORMATTING COLORE
# --------------------------------------------------------
def format_value(val, is_roi=False):
    if val is None:
        val = 0
    suffix = "%" if is_roi else ""
    if val > 0:
        return f"🟢 +{val:.2f}{suffix}"
    elif val < 0:
        return f"🔴 {val:.2f}{suffix}"
    else:
        return f"0.00{suffix}"

# --------------------------------------------------------
# CALCOLO BACK / LAY STATS (versione corretta)
# --------------------------------------------------------
def calculate_back_lay(filtered_df):
    """
    Calcola:
    - profitti back e lay
    - ROI% back e lay
    per HOME, DRAW, AWAY su tutte le righe di filtered_df.
    Per il LAY, la responsabilità è fissa a 1 unità.
    """
    profits_back = {"HOME": 0, "DRAW": 0, "AWAY": 0}
    profits_lay = {"HOME": 0, "DRAW": 0, "AWAY": 0}
    matches = len(filtered_df)

    for _, row in filtered_df.iterrows():
        h_goals = row["Home Goal FT"]
        a_goals = row["Away Goal FT"]

        result = (
            "HOME" if h_goals > a_goals else
            "AWAY" if h_goals < a_goals else
            "DRAW"
        )

        for outcome in ["HOME", "DRAW", "AWAY"]:
            if outcome == "HOME":
                price = row.get("Odd home", None)
            elif outcome == "DRAW":
                price = row.get("Odd Draw", None)
            elif outcome == "AWAY":
                price = row.get("Odd Away", None)

            try:
                price = float(price)
            except:
                price = 2.00

            if price <= 1:
                price = 2.00

            # BACK
            if result == outcome:
                profits_back[outcome] += (price - 1)
            else:
                profits_back[outcome] -= 1

            # LAY corretto → responsabilità = 1
            stake = 1 / (price - 1)
            if result != outcome:
                profits_lay[outcome] += stake
            else:
                profits_lay[outcome] -= 1

    rois_back = {}
    rois_lay = {}
    for outcome in ["HOME", "DRAW", "AWAY"]:
        if matches > 0:
            rois_back[outcome] = round((profits_back[outcome] / matches) * 100, 2)
            rois_lay[outcome] = round((profits_lay[outcome] / matches) * 100, 2)
        else:
            rois_back[outcome] = 0
            rois_lay[outcome] = 0

    return profits_back, rois_back, profits_lay, rois_lay, matches

# --------------------------------------------------------
# RUN PRE MATCH PAGE
# --------------------------------------------------------
def run_pre_match(df, db_selected):
    st.title("⚔️ Confronto Pre Match")

    if "Label" not in df.columns:
        df = df.copy()
        df["Label"] = df.apply(label_match, axis=1)

    df["Home"] = df["Home"].str.strip()
    df["Away"] = df["Away"].str.strip()

    teams_available = sorted(
        set(df[df["country"] == db_selected]["Home"].dropna().unique()) |
        set(df[df["country"] == db_selected]["Away"].dropna().unique())
    )

    # ✅ Session State inizializzazione
    if "squadra_casa" not in st.session_state:
        st.session_state["squadra_casa"] = teams_available[0] if teams_available else ""

    if "squadra_ospite" not in st.session_state:
        st.session_state["squadra_ospite"] = teams_available[0] if teams_available else ""

    col1, col2 = st.columns(2)

    with col1:
        squadra_casa = st.selectbox(
            "Seleziona Squadra Casa",
            options=teams_available,
            index=teams_available.index(st.session_state["squadra_casa"]) if st.session_state["squadra_casa"] in teams_available else 0,
            key="squadra_casa"
        )

    with col2:
        squadra_ospite = st.selectbox(
            "Seleziona Squadra Ospite",
            options=teams_available,
            index=teams_available.index(st.session_state["squadra_ospite"]) if st.session_state["squadra_ospite"] in teams_available else 0,
            key="squadra_ospite"
        )

    col1, col2, col3 = st.columns(3)

    with col1:
        odd_home = st.number_input("Quota Vincente Casa", min_value=1.01, step=0.01, value=2.00)
        implied_home = round(100 / odd_home, 2)
        st.markdown(f"**Probabilità Casa ({squadra_casa}):** {implied_home}%")

    with col2:
        odd_draw = st.number_input("Quota Pareggio", min_value=1.01, step=0.01, value=3.20)
        implied_draw = round(100 / odd_draw, 2)
        st.markdown(f"**Probabilità Pareggio:** {implied_draw}%")

    with col3:
        odd_away = st.number_input("Quota Vincente Ospite", min_value=1.01, step=0.01, value=3.80)
        implied_away = round(100 / odd_away, 2)
        st.markdown(f"**Probabilità Ospite ({squadra_ospite}):** {implied_away}%")

    if squadra_casa and squadra_ospite and squadra_casa != squadra_ospite:
        implied_home = round(100 / odd_home, 2)
        implied_draw = round(100 / odd_draw, 2)
        implied_away = round(100 / odd_away, 2)

        label = label_from_odds(odd_home, odd_away)
        label_type = get_label_type(label)

        st.markdown(f"### 🎯 Range di quota identificato (Label): `{label}`")

        if label == "Others":
            st.info("⚠️ Le quote inserite non rientrano in nessun range di quota. Verranno calcolate statistiche su tutto il campionato.")
            label = None
        elif label not in df["Label"].unique() or df[df["Label"] == label].empty:
            st.info(f"⚠️ Nessuna partita trovata per il Label `{label}`. Verranno calcolate statistiche su tutto il campionato.")
            label = None

        rows = []

        # ---------------------------
        # League
        # ---------------------------
        if label:
            filtered_league = df[df["Label"] == label]
            profits_back, rois_back, profits_lay, rois_lay, matches_league = calculate_back_lay(filtered_league)

            league_stats = get_league_data_by_label(df, label)
            row_league = {
                "LABEL": "League",
                "MATCHES": matches_league,
                "BACK WIN% HOME": round(league_stats["HomeWin_pct"], 2) if league_stats else 0,
                "BACK WIN% DRAW": round(league_stats["Draw_pct"], 2) if league_stats else 0,
                "BACK WIN% AWAY": round(league_stats["AwayWin_pct"], 2) if league_stats else 0
            }
            for outcome in ["HOME", "DRAW", "AWAY"]:
                row_league[f"BACK PTS {outcome}"] = format_value(profits_back[outcome])
                row_league[f"BACK ROI% {outcome}"] = format_value(rois_back[outcome], is_roi=True)
                row_league[f"Lay pts {outcome}"] = format_value(profits_lay[outcome])
                row_league[f"lay ROI% {outcome}"] = format_value(rois_lay[outcome], is_roi=True)
            rows.append(row_league)

        # ---------------------------
        # Squadra Casa
        # ---------------------------
        row_home = {"LABEL": squadra_casa}
        if label and label_type in ["Home", "Both"]:
            filtered_home = df[(df["Label"] == label) & (df["Home"] == squadra_casa)]

            if filtered_home.empty:
                filtered_home = df[df["Home"] == squadra_casa]
                st.info(f"⚠️ Nessuna partita trovata per questo label. Calcolo eseguito su TUTTO il database per {squadra_casa}.")

            with st.expander(f"DEBUG - Partite Home per {squadra_casa}"):
                st.write(filtered_home)

            profits_back, rois_back, profits_lay, rois_lay, matches_home = calculate_back_lay(filtered_home)

            if matches_home > 0:
                wins_home = sum(filtered_home["Home Goal FT"] > filtered_home["Away Goal FT"])
                draws_home = sum(filtered_home["Home Goal FT"] == filtered_home["Away Goal FT"])
                losses_home = sum(filtered_home["Home Goal FT"] < filtered_home["Away Goal FT"])

                pct_win_home = round((wins_home / matches_home) * 100, 2)
                pct_draw = round((draws_home / matches_home) * 100, 2)
                pct_loss = round((losses_home / matches_home) * 100, 2)
            else:
                pct_win_home = pct_draw = pct_loss = 0

            row_home["MATCHES"] = matches_home
            row_home["BACK WIN% HOME"] = pct_win_home
            row_home["BACK WIN% DRAW"] = pct_draw
            row_home["BACK WIN% AWAY"] = pct_loss

            for outcome in ["HOME", "DRAW", "AWAY"]:
                row_home[f"BACK PTS {outcome}"] = format_value(profits_back[outcome])
                row_home[f"BACK ROI% {outcome}"] = format_value(rois_back[outcome], is_roi=True)
                row_home[f"Lay pts {outcome}"] = format_value(profits_lay[outcome])
                row_home[f"lay ROI% {outcome}"] = format_value(rois_lay[outcome], is_roi=True)
        else:
            row_home["MATCHES"] = "N/A"
            for outcome in ["HOME", "DRAW", "AWAY"]:
                row_home[f"BACK WIN% {outcome}"] = 0
                row_home[f"BACK PTS {outcome}"] = format_value(0)
                row_home[f"BACK ROI% {outcome}"] = format_value(0, is_roi=True)
                row_home[f"Lay pts {outcome}"] = format_value(0)
                row_home[f"lay ROI% {outcome}"] = format_value(0, is_roi=True)
        rows.append(row_home)

        # ---------------------------
        # Squadra Ospite
        # ---------------------------
        row_away = {"LABEL": squadra_ospite}
        if label and label_type in ["Away", "Both"]:
            filtered_away = df[(df["Label"] == label) & (df["Away"] == squadra_ospite)]

            if filtered_away.empty:
                filtered_away = df[df["Away"] == squadra_ospite]
                st.info(f"⚠️ Nessuna partita trovata per questo label. Calcolo eseguito su TUTTO il database per {squadra_ospite}.")

            with st.expander(f"DEBUG - Partite Away per {squadra_ospite}"):
                st.write(filtered_away)

            profits_back, rois_back, profits_lay, rois_lay, matches_away = calculate_back_lay(filtered_away)

            if matches_away > 0:
                wins_away = sum(filtered_away["Away Goal FT"] > filtered_away["Home Goal FT"])
                draws_away = sum(filtered_away["Away Goal FT"] == filtered_away["Home Goal FT"])
                losses_away = sum(filtered_away["Away Goal FT"] < filtered_away["Home Goal FT"])

                pct_win_away = round((wins_away / matches_away) * 100, 2)
                pct_draw = round((draws_away / matches_away) * 100, 2)
                pct_loss = round((losses_away / matches_away) * 100, 2)
            else:
                pct_win_away = pct_draw = pct_loss = 0

            row_away["MATCHES"] = matches_away
            row_away["BACK WIN% HOME"] = pct_loss
            row_away["BACK WIN% DRAW"] = pct_draw
            row_away["BACK WIN% AWAY"] = pct_win_away

            for outcome in ["HOME", "DRAW", "AWAY"]:
                row_away[f"BACK PTS {outcome}"] = format_value(profits_back[outcome])
                row_away[f"BACK ROI% {outcome}"] = format_value(rois_back[outcome], is_roi=True)
                row_away[f"Lay pts {outcome}"] = format_value(profits_lay[outcome])
                row_away[f"lay ROI% {outcome}"] = format_value(rois_lay[outcome], is_roi=True)
        else:
            row_away["MATCHES"] = "N/A"
            for outcome in ["HOME", "DRAW", "AWAY"]:
                row_away[f"BACK WIN% {outcome}"] = 0
                row_away[f"BACK PTS {outcome}"] = format_value(0)
                row_away[f"BACK ROI% {outcome}"] = format_value(0, is_roi=True)
                row_away[f"Lay pts {outcome}"] = format_value(0)
                row_away[f"lay ROI% {outcome}"] = format_value(0, is_roi=True)
        rows.append(row_away)

        # ------------------------------------------
        # CONVERSIONE TABELLA IN LONG FORMAT
        # ------------------------------------------
        rows_long = []
        for row in rows:
            for outcome in ["HOME", "DRAW", "AWAY"]:
                rows_long.append({
                    "LABEL": row["LABEL"],
                    "SEGNO": outcome,
                    "Matches": row["MATCHES"],
                    "Win %": row.get(f"BACK WIN% {outcome}", 0),
                    "Back Pts": row.get(f"BACK PTS {outcome}", format_value(0)),
                    "Back ROI %": row.get(f"BACK ROI% {outcome}", format_value(0, is_roi=True)),
                    "Lay Pts": row.get(f"Lay pts {outcome}", format_value(0)),
                    "Lay ROI %": row.get(f"lay ROI% {outcome}", format_value(0, is_roi=True))
                })

        df_long = pd.DataFrame(rows_long)
        df_long.loc[df_long.duplicated(subset=["LABEL"]), "LABEL"] = ""

        st.markdown(f"#### Range di quota identificato (Label): `{label}`")
        st.dataframe(df_long, use_container_width=True)

        # -------------------------------------------------------
        # CONFRONTO MACRO STATS
        # -------------------------------------------------------
        st.markdown("---")
        st.markdown("## 📊 Confronto Statistiche Pre-Match")

        stats_home = compute_team_macro_stats(df, squadra_casa, "Home")
        stats_away = compute_team_macro_stats(df, squadra_ospite, "Away")

        if not stats_home or not stats_away:
            st.info("⚠️ Una delle due squadre non ha partite disponibili per il confronto.")
            return

        df_comp = pd.DataFrame({
            squadra_casa: stats_home,
            squadra_ospite: stats_away
        })

        st.dataframe(df_comp, use_container_width=True)

        st.success("✅ Confronto Pre Match generato con successo!")
        st.markdown("---")
sst.header("📈 ROI Back & Lay + EV Live (Over e BTTS)")

        commission = 0.045
        df_label_ev = df.copy()

        # -------------------------------
        # DEBUG - Partite analizzate
        # -------------------------------
        st.markdown("### 🔍 DEBUG - Match analizzati")
        st.write("Totali match filtrati (Label + Goal disponibili):", len(df_label_ev))
        righe_senza_quote = df_label_ev[
            (df_label_ev["cotao1"].isna()) &
            (df_label_ev["cotao"].isna()) &
            (df_label_ev["cotao3"].isna()) &
            (df_label_ev["gg"].isna())
        ]
        st.write("❌ Match esclusi per mancanza quote:", len(righe_senza_quote))
        with st.expander("📋 Visualizza match esclusi"):
            st.dataframe(righe_senza_quote[["Home", "Away", "Home Goal FT", "Away Goal FT", "cotao1", "cotao", "cotao3", "gg"]])

        df_label_ev["Label"] = df_label_ev.apply(label_match, axis=1)
        df_label_ev = df_label_ev[df_label_ev["Label"] == label]
        df_label_ev = df_label_ev.dropna(subset=["Home Goal FT", "Away Goal FT"])

        st.markdown("### 🎯 Calcolo ROI Back & Lay su Over 1.5, 2.5, 3.5 e BTTS")

        lines = {
            "Over 1.5": ("cotao1", 1.5),
            "Over 2.5": ("cotao", 2.5),
            "Over 3.5": ("cotao3", 3.5),
            "BTTS": ("gg", None)
        }

        table_data = []

        for label_text, (col_name, goal_line) in lines.items():
            total = 0
            back_profit = 0
            lay_profit = 0
            quote_list = []
            hits = 0

            for _, row in df_label_ev.iterrows():
                goals = row["Home Goal FT"] + row["Away Goal FT"]
                gg = row.get("gg", None)
                odd = row.get(col_name, None)

                if pd.isna(odd) or odd < 1.01:
                    continue

                quote_list.append(odd)
                total += 1

                if label_text == "BTTS":
                    if gg == 1:
                        hits += 1
                        back_profit += (odd - 1) * (1 - commission)
                        lay_profit -= 1
                    else:
                        lay_profit += 1 / (odd - 1)
                        back_profit -= 1
                else:
                    if goals > goal_line:
                        hits += 1
                        back_profit += (odd - 1) * (1 - commission)
                        lay_profit -= 1
                    else:
                        lay_profit += 1 / (odd - 1)
                        back_profit -= 1

            if total > 0:
                avg_quote = round(sum(quote_list) / len(quote_list), 2)
                pct = round((hits / total) * 100, 2)
                roi_back = round((back_profit / total) * 100, 2)
                roi_lay = round((lay_profit / total) * 100, 2)

                table_data.append({
                    "Mercato": label_text,
                    "Quota Media": avg_quote,
                    "Esiti %": f"{pct}%",
                    "ROI Back %": f"{roi_back}%",
                    "ROI Lay %": f"{roi_lay}%",
                    "Match Analizzati": total
                })

        df_ev = pd.DataFrame(table_data)
        st.dataframe(df_ev, use_container_width=True)

        # -------------------------------------------------------
        # 🧠 EV Live Manuale - Quote inserite dall'utente
        # -------------------------------------------------------
        st.markdown("## 🧠 Calcolo Expected Value (EV) Manuale")

        ev_rows = []
        for voce in ["Over 1.5", "Over 2.5", "Over 3.5", "BTTS"]:
            col1, col2 = st.columns(2)
            with col1:
                quota_live = st.number_input(f"Quota Live per {voce}", min_value=1.01, step=0.01, value=2.00, key=f"q_{voce}")
            with col2:
                prob_text = df_ev[df_ev["Mercato"] == voce]["Esiti %"].values[0].replace("%", "") if not df_ev.empty else "0"
                prob = float(prob_text)
                ev = round((quota_live * (prob / 100)) - 1, 3)
                colore = "🟢 EV+" if ev > 0 else "🔴 EV-" if ev < 0 else "⚪️ Neutro"
                ev_rows.append({
                    "Mercato": voce,
                    "Quota Inserita": quota_live,
                    "Probabilità Storica": f"{prob}%",
                    "EV": ev,
                    "Note": colore
                })

        st.dataframe(pd.DataFrame(ev_rows), use_container_width=True)        
        
        

        # -------------------------------------------------------
        # ⚖️ ROI OVER / UNDER 2.5 con quote reali dal database
        # -------------------------------------------------------
        st.markdown("## ⚖️ ROI Over / Under 2.5 Goals")

        apply_team_filter = st.checkbox("🔍 Calcola ROI solo sui match delle squadre selezionate che rientrano nel range (label)", value=True)

        commission = 0.045

        df_label = df.copy()
        df_label["LabelTemp"] = df_label.apply(label_match, axis=1)
        df_label = df_label[df_label["LabelTemp"] == label]

        if apply_team_filter:
            df_label = df_label[
                (df_label["Home"] == st.session_state["squadra_casa"]) | (df_label["Away"] == st.session_state["squadra_ospite"])
            ]

        st.markdown("### 🔍 DEBUG - Partite incluse nel ROI Over/Under")
        st.write("Totali partite filtrate (Label + Squadre):", len(df_label))

        excluded_df = df_label[
            df_label["Home Goal FT"].isna() | df_label["Away Goal FT"].isna()
        ]
        included_df = df_label[
            df_label["Home Goal FT"].notna() & df_label["Away Goal FT"].notna()
        ]

        st.write("✅ Partite incluse nel calcolo ROI (gol disponibili):", len(included_df))
        st.write("❌ Partite escluse (mancano i gol):", len(excluded_df))

        with st.expander("📋 Visualizza match esclusi"):
            st.dataframe(excluded_df[["Home", "Away", "Home Goal FT", "Away Goal FT"]])

        df_label = included_df.copy()

        total = 0
        profit_over = 0
        profit_under = 0
        over_hits = 0
        under_hits = 0
        quote_over_list = []
        quote_under_list = []

        for _, row in df_label.iterrows():
            goals = row["Home Goal FT"] + row["Away Goal FT"]
            quote_over = row.get("odd over 2,5", None)
            quote_under = row.get("odd under 2,5", None)

            if pd.isna(quote_over) or pd.isna(quote_under) or quote_over < 1.01 or quote_under < 1.01:
                continue

            quote_over_list.append(quote_over)
            quote_under_list.append(quote_under)
            total += 1

            if goals > 2.5:
                over_hits += 1
                profit_over += (quote_over - 1) * (1 - commission)
                profit_under -= 1
            else:
                under_hits += 1
                profit_under += (quote_under - 1) * (1 - commission)
                profit_over -= 1

        if total > 0:
            avg_quote_over = round(sum(quote_over_list) / len(quote_over_list), 2)
            avg_quote_under = round(sum(quote_under_list) / len(quote_under_list), 2)
            roi_over = round((profit_over / total) * 100, 2)
            roi_under = round((profit_under / total) * 100, 2)
            pct_over = round((over_hits / total) * 100, 2)
            pct_under = round((under_hits / total) * 100, 2)

            df_roi = pd.DataFrame([{
                "Linea": "2.5 Goals",
                "Quote Over": avg_quote_over,
                "Quote Under": avg_quote_under,
                "% Over": f"{pct_over}%",
                "% Under": f"{pct_under}%",
                "ROI Over": f"{roi_over}%",
                "ROI Under": f"{roi_under}%",
                "Profitto Over": round(profit_over, 2),
                "Profitto Under": round(profit_under, 2),
                "Match Analizzati": total
            }])
            st.dataframe(df_roi, use_container_width=True)

            # -------------------------------------------------------
            # 🧠 EV OVER / UNDER 2.5
            # -------------------------------------------------------
            st.markdown("## 🧠 Expected Value (EV) - Over/Under 2.5")

            col1, col2 = st.columns(2)
            with col1:
                quota_attuale_ov = st.number_input("📥 Quota attuale Over 2.5", min_value=1.01, step=0.01, value=2.00)
            with col2:
                quota_attuale_un = st.number_input("📥 Quota attuale Under 2.5", min_value=1.01, step=0.01, value=1.80)

            ev_over = round((quota_attuale_ov * (pct_over / 100)) - 1, 3)
            ev_under = round((quota_attuale_un * (pct_under / 100)) - 1, 3)

            st.markdown(f"**📈 EV Over 2.5:** `{ev_over}` {'🟢 EV+ (valore)' if ev_over > 0 else '🔴 EV- (no valore)' if ev_over < 0 else '⚪️ Neutro'}")
            st.markdown(f"**📉 EV Under 2.5:** `{ev_under}` {'🟢 EV+ (valore)' if ev_under > 0 else '🔴 EV- (no valore)' if ev_under < 0 else '⚪️ Neutro'}")

            st.caption("Formula EV = (Quota × Probabilità Storica) - 1")

        else:
            st.warning("⚠️ Nessuna partita valida trovata per il calcolo ROI Over/Under.")



# -------------------------------------------------------
# CORRECT SCORE EV
# -------------------------------------------------------
st.markdown("---")
st.header("📊 Analisi Correct Score EV")

squadra_casa = st.session_state.get("squadra_casa")
squadra_ospite = st.session_state.get("squadra_ospite")
label = st.session_state.get("label_corrente")

if not squadra_casa or not squadra_ospite or not label:
    st.warning("⚠️ Seleziona prima le squadre e le quote nella sezione 'Confronto Pre Match'.")
else:
    st.markdown(f"**Match:** {squadra_casa} vs {squadra_ospite}")
    st.markdown(f"**Label attivo:** `{label}`")

    filtered_df = df.copy()
    filtered_df["Label"] = filtered_df.apply(label_match, axis=1)
    filtered_df = filtered_df[filtered_df["Label"] == label]
    filtered_df = filtered_df.dropna(subset=["Home Goal FT", "Away Goal FT"])

    if filtered_df.empty:
        st.warning("⚠️ Nessuna partita trovata per questo Label.")
    else:
        filtered_df["Correct Score"] = (
            filtered_df["Home Goal FT"].astype(int).astype(str)
            + "-"
            + filtered_df["Away Goal FT"].astype(int).astype(str)
        )

        cs_counts = filtered_df["Correct Score"].value_counts().reset_index()
        cs_counts.columns = ["Correct Score", "Count"]
        cs_counts["%"] = (cs_counts["Count"] / cs_counts["Count"].sum()) * 100
        cs_counts = cs_counts.head(6)

        def calculate_ev(prob, quota):
            try:
                quota = float(quota)
                ev = round((prob * quota) - 100, 2)
                return f"🟢 {ev}%" if ev > 0 else f"🔴 {ev}%"
            except:
                return ""

        cs_counts["Quota"] = ""
        cs_counts["EV"] = ""

        for i in cs_counts.index:
            quota_input = st.text_input(f"Quota per {cs_counts.at[i, 'Correct Score']}", key=f"quota_cs_{i}")
            cs_counts.at[i, "Quota"] = quota_input
            cs_counts.at[i, "EV"] = calculate_ev(cs_counts.at[i, "%"], quota_input)

        st.dataframe(cs_counts, use_container_width=True)

# -------------------------------------------------------
# 📈 ROI & EV LIVE - Over e BTTS
# -------------------------------------------------------
st.markdown("---")
