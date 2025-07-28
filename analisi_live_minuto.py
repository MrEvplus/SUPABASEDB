import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from utils import label_match, extract_minutes

def color_pct(val):
    """
    Colora le celle percentuali:
      - rosso se <50
      - giallo se 50–69
      - verde se ≥70
    """
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
        home_team = st.selectbox(
            "🏠 Squadra in casa",
            sorted(df["Home"].dropna().unique()),
            key="home_live"
        )
    with col2:
        away_team = st.selectbox(
            "🚪 Squadra in trasferta",
            sorted(df["Away"].dropna().unique()),
            key="away_live"
        )

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

    # --- Partite storiche con stesso live score al minuto ---
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

    # --- Espandi tabella partite matchate ---
    with st.expander("📑 Partite campionato considerate per l'analisi"):
        if not df_matched.empty:
            st.dataframe(
                df_matched[[
                    "Stagione", "Data", "Home", "Away",
                    "Home Goal FT", "Away Goal FT",
                    "minuti goal segnato home",
                    "minuti goal segnato away"
                ]]
                .sort_values(["Stagione", "Data"], ascending=[False, False])
                .reset_index(drop=True),
                use_container_width=True
            )
        else:
            st.write("Nessuna partita da mostrare.")

    # --- Statistiche Campionato ---
    matches = len(df_league)
    home_w = (df_league["Home Goal FT"] > df_league["Away Goal FT"]).mean() * 100
    draw_p = (df_league["Home Goal FT"] == df_league["Away Goal FT"]).mean() * 100
    opp_w = (df_league["Home Goal FT"] < df_league["Away Goal FT"]).mean() * 100

    stats_league = pd.DataFrame({
        "Home Teams": [matches, home_w, draw_p, opp_w],
        "Away Teams": [matches, opp_w, draw_p, home_w],
    }, index=["Matches", "Win %", "Draw %", "Loss %"])

    styled_league_home = (
        stats_league[["Home Teams"]]
        .style.format("{:.2f}")
        .applymap(color_pct, subset=pd.IndexSlice[["Win %","Draw %","Loss %"], :])
        .set_properties(**{"text-align": "center"})
        .set_table_styles([{"selector": "th","props":[("text-align","center")]}])
    )
    styled_league_away = (
        stats_league[["Away Teams"]]
        .style.format("{:.2f}")
        .applymap(color_pct, subset=pd.IndexSlice[["Win %","Draw %","Loss %"], :])
        .set_properties(**{"text-align": "center"})
        .set_table_styles([{"selector": "th","props":[("text-align","center")]}])
    )

    # --- Statistiche Squadra ---
    team = home_team if label.startswith("H_") else away_team
    df_team = df_matched[(df_matched["Home"] == team) | (df_matched["Away"] == team)]
    t_matches = len(df_team)
    if t_matches > 0:
        if label.startswith("H_"):
            t_w = (df_team["Home Goal FT"] > df_team["Away Goal FT"]).mean() * 100
            t_opp_w = (df_team["Home Goal FT"] < df_team["Away Goal FT"]).mean() * 100
        else:
            t_w = (df_team["Away Goal FT"] > df_team["Home Goal FT"]).mean() * 100
            t_opp_w = (df_team["Away Goal FT"] < df_team["Home Goal FT"]).mean() * 100
        t_draw = (df_team["Home Goal FT"] == df_team["Away Goal FT"]).mean() * 100
    else:
        t_w = t_draw = t_opp_w = 0.0

    stats_team = pd.DataFrame({
        team: [t_matches, t_w, t_draw, t_opp_w],
        "Opponents": [t_matches, t_opp_w, t_draw, t_w],
    }, index=["Matches", "Win %", "Draw %", "Loss %"])

    styled_team_home = (
        stats_team[[team]]
        .style.format("{:.2f}")
        .applymap(color_pct, subset=pd.IndexSlice[["Win %","Draw %","Loss %"], :])
        .set_properties(**{"text-align": "center"})
        .set_table_styles([{"selector": "th","props":[("text-align","center")]}])
    )
    styled_team_away = (
        stats_team[["Opponents"]]
        .style.format("{:.2f}")
        .applymap(color_pct, subset=pd.IndexSlice[["Win %","Draw %","Loss %"], :])
        .set_properties(**{"text-align": "center"})
        .set_table_styles([{"selector": "th","props":[("text-align","center")]}])
    )

    # --- Layout tabelle affiancate ---
    st.subheader("📊 Statistiche Campionato")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Home Teams**")
        st.dataframe(styled_league_home, use_container_width=True)
    with c2:
        st.markdown("**Away Teams**")
        st.dataframe(styled_league_away, use_container_width=True)

    st.subheader(f"📊 Statistiche Squadra – {team}")
    c3, c4 = st.columns(2)
    with c3:
        st.markdown(f"**{team}**")
        st.dataframe(styled_team_home, use_container_width=True)
    with c4:
        st.markdown("**Opponents**")
        st.dataframe(styled_team_away, use_container_width=True)

    # --- OVER dal minuto live (Campionato) ---
    st.subheader("📊 OVER dal minuto live (Campionato)")
    extra = (df_matched["Home Goal FT"] + df_matched["Away Goal FT"]) - (live_h + live_a)
    thresholds = [0.5, 1.5, 2.5, 3.5, 4.5]
    cols = st.columns(2)
    for i, thr in enumerate(thresholds):
        pct = (extra > thr).mean() * 100 if len(extra) > 0 else 0
        with cols[i % 2]:
            st.markdown(f"• **OVER {thr}:** {pct:.2f}%")

    # --- Risultati frequenti Campionato ---
    st.subheader("📋 Risultati finali (Campionato)")
    freq = (df_matched["Home Goal FT"].astype(int).astype(str) + "-" +
            df_matched["Away Goal FT"].astype(int).astype(str))
    freq_df = (freq.value_counts()
               .rename_axis("Risultato")
               .reset_index(name="Occorrenze"))
    freq_df["%"] = (freq_df["Occorrenze"] / len(df_matched) * 100).round(2)
    styled_freq = (freq_df.style
                   .format({"%": "{:.2f}%"})
                   .applymap(color_pct, subset=["%"])
                   .set_properties(**{"text-align": "center"})
                   .set_table_styles([{"selector": "th", "props": [("text-align", "center")]}]))
    st.dataframe(styled_freq, use_container_width=True)

    # --- Distribuzione goal per intervallo post-minuto live (Campionato) ---
    st.subheader("⏱️ Goal per intervallo post-minuto live (Campionato)")
    tf_bands = [(0,15), (16,30), (31,45), (46,60), (61,75), (76,90)]
    tf_labels = [f"{a}-{b}" for a,b in tf_bands]
    tf_fatti = {lbl:0 for lbl in tf_labels}
    tf_subiti = {lbl:0 for lbl in tf_labels}
    for _, r in df_matched.iterrows():
        mh = extract_minutes(pd.Series([r.get("minuti goal segnato home","")]))
        ma = extract_minutes(pd.Series([r.get("minuti goal segnato away","")]))
        for m in mh:
            if m > current_min:
                for lbl,(a,b) in zip(tf_labels,tf_bands):
                    if a < m <= b:
                        tf_fatti[lbl] += 1
                        break
        for m in ma:
            if m > current_min:
                for lbl,(a,b) in zip(tf_labels,tf_bands):
                    if a < m <= b:
                        tf_subiti[lbl] += 1
                        break
    df_tf = pd.DataFrame([{"Intervallo":lbl,"Fatti":tf_fatti[lbl],"Subiti":tf_subiti[lbl]} 
                          for lbl in tf_labels])
    df_tf["Totale"] = df_tf["Fatti"] + df_tf["Subiti"]
    df_tf["% Totale"] = (df_tf["Totale"]/df_tf["Totale"].sum()*100).round(2)
    styled_tf = (df_tf.style
                 .format({"% Totale":"{:.2f}%"})
                 .applymap(color_pct, subset=["% Totale"])
                 .set_properties(**{"text-align":"center"})
                 .set_table_styles([{"selector":"th","props":[("text-align","center")]}]))
    st.dataframe(styled_tf, use_container_width=True)

    # --- Grafico a barre Campionato ---
    fig, ax = plt.subplots(figsize=(8,4))
    ax.bar(df_tf["Intervallo"], df_tf["Fatti"], label="Fatti", alpha=0.8)
    ax.bar(df_tf["Intervallo"], df_tf["Subiti"], bottom=df_tf["Fatti"], label="Subiti", alpha=0.8)
    for i,row in df_tf.iterrows():
        ax.text(i, row.Totale+0.3, f'{row.Totale} ({row["% Totale"]}%)',
                ha="center", va="bottom", fontweight="bold")
    ax.set_title("Campionato: goal post-minuto per intervallo")
    ax.set_ylabel("N° goal")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    st.pyplot(fig)

    # --- Ripeti per la squadra selezionata ---
    st.markdown("---")
    st.subheader(f"📊 {team}: OVER dal minuto live")
    extra_t = (df_team["Home Goal FT"] + df_team["Away Goal FT"]) - (live_h + live_a)
    for thr in thresholds:
        pctt = (extra_t>thr).mean()*100 if len(extra_t)>0 else 0
        st.markdown(f"• **OVER {thr}:** {pctt:.2f}%")

    st.subheader(f"📋 {team}: risultati finali")
    freq_t = freq.loc[df_team.index]
    freq_df_t = (freq_t.value_counts()
                 .rename_axis("Risultato")
                 .reset_index(name="Occorrenze"))
    freq_df_t["%"] = (freq_df_t["Occorrenze"]/len(df_team)*100).round(2)
    styled_ft = (freq_df_t.style
                 .format({"%":"{:.2f}%"})
                 .applymap(color_pct, subset=["%"])
                 .set_properties(**{"text-align":"center"})
                 .set_table_styles([{"selector":"th","props":[("text-align","center")]}]))
    st.dataframe(styled_ft, use_container_width=True)

    st.subheader(f"⏱️ {team}: goal per intervallo post-minuto")
    tf_fatti_t = {lbl:0 for lbl in tf_labels}
    tf_subiti_t = {lbl:0 for lbl in tf_labels}
    for _,r in df_team.iterrows():
        mh=extract_minutes(pd.Series([r.get("minuti goal segnato home","")]))
        ma=extract_minutes(pd.Series([r.get("minuti goal segnato away","")]))
        for m in mh:
            if m>current_min:
                for lbl,(a,b) in zip(tf_labels,tf_bands):
                    if a<m<=b:
                        tf_fatti_t[lbl]+=1; break
        for m in ma:
            if m>current_min:
                for lbl,(a,b) in zip(tf_labels,tf_bands):
                    if a<m<=b:
                        tf_subiti_t[lbl]+=1; break
    df_t = pd.DataFrame([{"Intervallo":lbl,"Fatti":tf_fatti_t[lbl],"Subiti":tf_subiti_t[lbl]}
                         for lbl in tf_labels])
    df_t["Totale"]=df_t["Fatti"]+df_t["Subiti"]
    df_t["% Totale"]=(df_t["Totale"]/df_t["Totale"].sum()*100).round(2)
    styled_t = (df_t.style
                .format({"% Totale":"{:.2f}%"})
                .applymap(color_pct, subset=["% Totale"])
                .set_properties(**{"text-align":"center"})
                .set_table_styles([{"selector":"th","props":[("text-align","center")]}]))
    st.dataframe(styled_t, use_container_width=True)

    fig2, ax2 = plt.subplots(figsize=(8,4))
    ax2.bar(df_t["Intervallo"], df_t["Fatti"], label="Fatti", alpha=0.8)
    ax2.bar(df_t["Intervallo"], df_t["Subiti"], bottom=df_t["Fatti"], label="Subiti", alpha=0.8)
    for i,row in df_t.iterrows():
        ax2.text(i, row.Totale+0.3, f'{row.Totale} ({row["% Totale"]}%)',
                 ha="center", va="bottom", fontweight="bold")
    ax2.set_title(f"{team}: goal post-minuto per intervallo")
    ax2.set_ylabel("N° goal")
    ax2.legend()
    ax2.grid(axis="y", linestyle="--", alpha=0.3)
    st.pyplot(fig2)

