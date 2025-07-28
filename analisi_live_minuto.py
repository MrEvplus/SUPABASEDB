import streamlit as st
import pandas as pd
from utils import label_match, extract_minutes

def color_pct(val):
    try:
        v = float(val)
    except:
        return ""
    if v < 50:
        color = "red"
    elif v < 70:
        color = "yellow"
    else:
        color = "green"
    return f"background-color: {color}; color: black;"

def run_live_minute_analysis(df):
    st.set_page_config(page_title="Analisi Live Minuto", layout="wide")
    st.title("⏱️ Analisi Live - Cosa succede da questo minuto?")

    # --- Selezione squadre ---
    col1, col2 = st.columns(2)
    with col1:
        home_team = st.selectbox("🏠 Squadra in casa", sorted(df["Home"].dropna().unique()), key="home_live")
    with col2:
        away_team = st.selectbox("🚪 Squadra in trasferta", sorted(df["Away"].dropna().unique()), key="away_live")

    # --- Inserimento quote ---
    c1, c2, c3 = st.columns(3)
    with c1:
        odd_home = st.number_input("📈 Quota Home", 1.01, 10.0, 2.00, key="odd_h")
    with c2:
        odd_draw = st.number_input("⚖️ Quota Pareggio", 1.01, 10.0, 3.20, key="odd_d")
    with c3:
        odd_away = st.number_input("📉 Quota Away", 1.01, 10.0, 3.80, key="odd_a")

    # --- Minuto e punteggio live ---
    current_min = st.slider("⏲️ Minuto attuale", 1, 120, 45, key="minlive")
    live_score = st.text_input("📟 Risultato live (es. 1-1)", "1-1", key="scorelive")
    try:
        live_h, live_a = map(int, live_score.split("-"))
    except:
        st.error("⚠️ Formato risultato non valido. Usa es. `1-1`.")
        return

    # --- Label e filtraggio campionato+label ---
    label = label_match({"Odd home": odd_home, "Odd Away": odd_away})
    st.markdown(f"🔖 **Label:** `{label}`")

    champ = st.session_state.get("campionato_corrente", df["country"].iloc[0])
    df["Label"] = df.apply(label_match, axis=1)
    df_league = df[(df["country"] == champ) & (df["Label"] == label)]
    if df_league.empty:
        st.warning("⚠️ Nessuna partita per questo label nel campionato.")
        return

    matched = []
    for _, r in df_league.iterrows():
        mh = extract_minutes(pd.Series([r.get("minuti goal segnato home", "")]))
        ma = extract_minutes(pd.Series([r.get("minuti goal segnato away", "")]))
        gh = sum(m <= current_min for m in mh)
        ga = sum(m <= current_min for m in ma)
        if gh == live_h and ga == live_a:
            matched.append(r)

    df_matched = pd.DataFrame(matched)
    st.success(f"✅ {len(df_matched)} partite trovate a {live_h}-{live_a}′ al minuto {current_min}’")

    left_col, right_col = st.columns(2)

    with left_col:
        st.subheader("📊 Statistiche Campionato")
        matches = len(df_league)
        home_w = (df_league["Home Goal FT"] > df_league["Away Goal FT"]).mean() * 100
        draw = (df_league["Home Goal FT"] == df_league["Away Goal FT"]).mean() * 100
        opp_w = (df_league["Home Goal FT"] < df_league["Away Goal FT"]).mean() * 100

        stats_league = pd.DataFrame({
            "Home Teams": [matches, home_w, draw, opp_w]
        }, index=["Matches", "Win %", "Draw %", "Loss %"])

        st.dataframe(stats_league.style.format("{:.2f}").applymap(color_pct, subset=pd.IndexSlice[["Win %", "Draw %", "Loss %"], :]), use_container_width=True)

    with right_col:
        st.subheader(f"📊 Statistiche Squadra - {home_team}")
        df_team = df_matched[(df_matched["Home"] == home_team) | (df_matched["Away"] == home_team)]
        t_matches = len(df_team)

        if t_matches > 0:
            t_w = (df_team["Home Goal FT"] > df_team["Away Goal FT"]).mean() * 100
            t_draw = (df_team["Home Goal FT"] == df_team["Away Goal FT"]).mean() * 100
            t_opp_w = (df_team["Home Goal FT"] < df_team["Away Goal FT"]).mean() * 100
        else:
            t_w = t_draw = t_opp_w = 0.0

        stats_team = pd.DataFrame({
            home_team: [t_matches, t_w, t_draw, t_opp_w]
        }, index=["Matches", "Win %", "Draw %", "Loss %"])

        st.dataframe(stats_team.style.format("{:.2f}").applymap(color_pct, subset=pd.IndexSlice[["Win %", "Draw %", "Loss %"], :]), use_container_width=True)

    st.markdown("---")

    st.header("🤖 Pronostico consigliato")
    thresholds = [0.5, 1.5, 2.5, 3.5, 4.5]
    evs = {}
    extra = (df_matched["Home Goal FT"] + df_matched["Away Goal FT"] - (live_h + live_a)).fillna(0)

    for thr in thresholds:
        colnm = f"odd over {str(thr).replace('.', ',')}"
        if colnm in df_matched:
            ev = (extra > thr).mean() * df_matched[colnm].mean() - 1
            evs[thr] = ev

    if evs:
        best, best_ev = max(evs.items(), key=lambda x: x[1])
        if best_ev > 0:
            st.success(f"💡 **OVER {best}** → EV: {best_ev:.2%}")
        else:
            st.info("ℹ️ Nessun EV positivo trovato.")
    else:
        st.info("ℹ️ Quote OVER non disponibili per EV.")
