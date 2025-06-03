import streamlit as st
import pandas as pd
import numpy as np
import requests
from xgboost import XGBClassifier
from datetime import date, timedelta

# ================== CONFIGURATION ==================
ligues = {
    "Premier League (Angleterre)": "PL",
    "La Liga (Espagne)": "PD",
    "Serie A (Italie)": "SA",
    "Bundesliga (Allemagne)": "BL1",
    "Ligue 1 (France)": "FL1",
    "MLS (USA)": "MLS",
    "Eredivisie (Pays-Bas)": "DED",
    "Primeira Liga (Portugal)": "PPL",
    "Championship (Angleterre D2)": "ELC",
    "Saudi Pro League": "SAU"
}

competition_ids = {
    "PL": 2021,
    "PD": 2014,
    "SA": 2019,
    "BL1": 2002,
    "FL1": 2015,
    "MLS": 2016,
    "DED": 2003,
    "PPL": 2017,
    "ELC": 2016,
    "SAU": 3141  # Peut ne pas exister
}

# ================== PAGE STREAMLIT ==================
st.set_page_config(page_title="Pari Foot - Football-Data", layout="centered")
st.title("⚽ Prédiction Résultat Match - Analyse & Recommandation")

st.markdown("🔑 Entre ta clé API obtenue sur [football-data.org](https://www.football-data.org/)")

# 1. Clé API
api_key = st.text_input("Clé API Football-Data", type="password")
championnat = st.selectbox("📍 Choisis un championnat :", list(ligues.keys()))
code_compet = ligues[championnat]
compet_id = competition_ids.get(code_compet)

# 2. Récupération des matchs à venir
if api_key and compet_id:
    headers = {"X-Auth-Token": api_key}
    today = date.today()
    future = today + timedelta(days=7)
    url = f"https://api.football-data.org/v4/matches?competitions={code_compet}&dateFrom={today}&dateTo={future}"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        st.error(f"❌ Erreur API : {response.status_code}")
    else:
        data = response.json()
        matchs = data.get("matches", [])

        if not matchs:
            st.warning("Aucun match prévu dans les 7 jours.")
        else:
            options = [f"{m['homeTeam']['name']} vs {m['awayTeam']['name']} - {m['utcDate'][:10]}" for m in matchs]
            choix_match = st.selectbox("⚽ Choisis un match :", options)
            match_selection = matchs[options.index(choix_match)]

            if st.button("Analyser ce match"):

                st.subheader("📊 Analyse et Prédiction")

                # ========= Récupération des données réelles =========
                def get_team_stats(team_id):
                    url = f"https://api.football-data.org/v4/teams/{team_id}/matches?status=FINISHED&limit=5"
                    res = requests.get(url, headers=headers).json()
                    matchs = res.get("matches", [])
                    points = 0
                    buts_marques = []
                    buts_encaisses = []

                    for m in matchs:
                        h, a = m['score']['fullTime']['home'], m['score']['fullTime']['away']
                        team_home = m['homeTeam']['id'] == team_id
                        if team_home:
                            scored, conceded = h, a
                        else:
                            scored, conceded = a, h
                        buts_marques.append(scored)
                        buts_encaisses.append(conceded)
                        if (team_home and h > a) or (not team_home and a > h):
                            points += 3
                        elif h == a:
                            points += 1

                    return {
                        "form": points,
                        "avg_scored": round(np.mean(buts_marques), 2),
                        "avg_conceded": round(np.mean(buts_encaisses), 2)
                    }

                def get_rank(team_id, competition_id):
                    url = f"https://api.football-data.org/v4/competitions/{competition_id}/standings"
                    res = requests.get(url, headers=headers).json()
                    standings = res['standings'][0]['table']
                    for team in standings:
                        if team['team']['id'] == team_id:
                            return team['position']
                    return 20  # valeur par défaut

                # ==== Données du match ====
                home_id = match_selection['homeTeam']['id']
                away_id = match_selection['awayTeam']['id']
                home_name = match_selection['homeTeam']['name']
                away_name = match_selection['awayTeam']['name']

                home_stats = get_team_stats(home_id)
                away_stats = get_team_stats(away_id)
                home_rank = get_rank(home_id, compet_id)
                away_rank = get_rank(away_id, compet_id)

                features = pd.DataFrame([{
                    "home_team_form": home_stats["form"],
                    "away_team_form": away_stats["form"],
                    "home_avg_goals_scored": home_stats["avg_scored"],
                    "away_avg_goals_scored": away_stats["avg_scored"],
                    "home_avg_goals_conceded": home_stats["avg_conceded"],
                    "away_avg_goals_conceded": away_stats["avg_conceded"],
                    "rank_diff": away_rank - home_rank
                }])

                # ================== Modèle XGBoost (données fictives pour entraînement) ==================
                X_mock = pd.DataFrame([
                    [12, 6, 2.3, 1.1, 0.8, 1.9, 4],
                    [8, 10, 1.9, 1.6, 1.1, 1.3, -2],
                    [14, 5, 2.5, 1.0, 0.7, 2.1, 6],
                    [9, 8, 2.0, 1.5, 1.2, 1.0, 0],
                    [11, 7, 2.1, 1.2, 1.0, 1.5, 3],
                    [6, 11, 1.5, 1.8, 1.3, 1.2, -5]
                ], columns=features.columns)

                y_mock = [0, 2, 0, 1, 0, 2]  # 0 = domicile, 1 = nul, 2 = extérieur

                model = XGBClassifier(use_label_encoder=False, eval_metric="mlogloss")
                model.fit(X_mock, y_mock)

                # ================== Prédiction ==================
                proba = model.predict_proba(features)[0]
                classes = ["🏠 Victoire domicile", "🤝 Match nul", "🚶 Victoire extérieur"]

                for i, p in enumerate(proba):
                    st.write(f"{classes[i]} : **{round(p * 100, 1)}%**")

                conseil = classes[np.argmax(proba)]
                st.markdown(f"### 💬 Recommandation : Parier sur « {conseil} »")
else:
    st.info("Entrez votre clé API et sélectionnez un championnat.")
