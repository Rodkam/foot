import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta


st.set_page_config(page_title="Prédiction Paris Foot", layout="wide")

st.title("📊 Paris Foot - Matchs à forte probabilité")
st.write("Affiche les matchs avec un écart de victoire ≥ seuil choisi dans les prochaines heures.")

# -----------------------------
# 1. Paramètres
# -----------------------------
API_TOKEN = "bb02b715d52b46b48f881df7f2205202"
headers = {"X-Auth-Token": API_TOKEN}

competitions = {
    "PL": "Premier League",
    "PD": "La Liga",
    "SA": "Serie A",
    "BL1": "Bundesliga",
    "FL1": "Ligue 1"
}

# Paramètres interactifs
DIFF_THRESHOLD = st.sidebar.slider("Écart minimum (%)", min_value=5, max_value=50, value=10)
TIME_WINDOW_HOURS = st.sidebar.slider("Prochaines heures à analyser", min_value=24, max_value=168, value=72)

# -----------------------------
# 2. Fonction de probabilité
# -----------------------------
def compute_prob(home_stats, away_stats):
    home_score = (home_stats['goalsFor'] / max(home_stats['matchesPlayed'],1)) / \
                 ((home_stats['goalsFor'] / max(home_stats['matchesPlayed'],1)) + 
                  (away_stats['goalsFor'] / max(away_stats['matchesPlayed'],1)))
    home_score = np.clip(home_score, 0.05, 0.95)
    return home_score, 1-home_score

# -----------------------------
# 3. Récupération des matchs
# -----------------------------
all_matches = []
now = datetime.utcnow()
time_limit = now + timedelta(hours=TIME_WINDOW_HOURS)

for comp_id, comp_name in competitions.items():
    # Info équipes
    url_teams = f"https://api.football-data.org/v4/competitions/{comp_id}/teams"
    resp_teams = requests.get(url_teams, headers=headers)
    if resp_teams.status_code != 200:
        st.warning(f"Erreur API Teams {comp_name}: {resp_teams.status_code}")
        continue
    teams_data = resp_teams.json()["teams"]
    teams_stats = {}
    for t in teams_data:
        teams_stats[t["name"]] = {
            "goalsFor": t.get("goalsFor", np.random.uniform(10,30)),
            "goalsAgainst": t.get("goalsAgainst", np.random.uniform(5,25)),
            "matchesPlayed": t.get("playedGames", 10)
        }

    # Matchs programmés
    url_matches = f"https://api.football-data.org/v4/competitions/{comp_id}/matches?status=SCHEDULED"
    resp_matches = requests.get(url_matches, headers=headers)
    if resp_matches.status_code != 200:
        st.warning(f"Erreur API Matches {comp_name}: {resp_matches.status_code}")
        continue
    matches = resp_matches.json().get("matches", [])

    for m in matches:
        match_time = datetime.strptime(m["utcDate"], "%Y-%m-%dT%H:%M:%SZ")
        if not (now <= match_time <= time_limit):
            continue

        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        if home not in teams_stats or away not in teams_stats:
            continue

        p_home, p_away = compute_prob(teams_stats[home], teams_stats[away])
        diff = abs(p_home - p_away)*100

        if diff >= DIFF_THRESHOLD:
            all_matches.append({
                "Championnat": comp_name,
                "Match": f"{home} vs {away}",
                "Victoire Home (%)": round(p_home*100,1),
                "Victoire Away (%)": round(p_away*100,1),
                "Différence (%)": round(diff,1),
                "Heure Match UTC": match_time.strftime("%Y-%m-%d %H:%M")
            })
