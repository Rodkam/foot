import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="Prédiction Paris Foot", layout="wide")

st.title("📊 Paris Foot - Matchs à forte probabilité")
st.write("Affiche les matchs avec un écart de victoire ≥ seuil choisi dans les prochaines heures.")

# -----------------------------
# Paramètres
# -----------------------------
API_TOKEN = "bb02b715d52b46b48f881df7f2205202"
headers = {"X-Auth-Token": API_TOKEN}

competitions = {
    "PL": "Premier League",
    "PD": "La Liga"
}

DIFF_THRESHOLD = st.sidebar.slider("Écart minimum (%)", min_value=5, max_value=50, value=10)
TIME_WINDOW_HOURS = st.sidebar.slider("Prochaines heures à analyser", min_value=24, max_value=168, value=72)

# -----------------------------
# Fonctions avec cache
# -----------------------------
@st.cache_data(ttl=3600)
def get_teams(comp_id):
    url_teams = f"https://api.football-data.org/v4/competitions/{comp_id}/teams"
    resp = requests.get(url_teams, headers=headers)
    if resp.status_code == 429:
        return "TOO_MANY_REQUESTS"
    if resp.status_code != 200:
        st.warning(f"Erreur API Teams {comp_id}: {resp.status_code}")
        return []
    return resp.json()["teams"]

@st.cache_data(ttl=3600)
def get_matches(comp_id):
    url_matches = f"https://api.football-data.org/v4/competitions/{comp_id}/matches?status=SCHEDULED"
    resp = requests.get(url_matches, headers=headers)
    if resp.status_code == 429:
        return "TOO_MANY_REQUESTS"
    if resp.status_code != 200:
        st.warning(f"Erreur API Matches {comp_id}: {resp.status_code}")
        return []
    return resp.json().get("matches", [])

def compute_prob(home_stats, away_stats):
    home_score = (home_stats['goalsFor'] / max(home_stats['matchesPlayed'],1)) / \
                 ((home_stats['goalsFor'] / max(home_stats['matchesPlayed'],1)) + 
                  (away_stats['goalsFor'] / max(away_stats['matchesPlayed'],1)))
    home_score = np.clip(home_score, 0.05, 0.95)
    return home_score, 1-home_score

# -----------------------------
# Récupération des matchs
# -----------------------------
all_matches = []
now = datetime.utcnow()
time_limit = now + timedelta(hours=TIME_WINDOW_HOURS)
api_blocked = False  # indicateur pour 429

for comp_id, comp_name in competitions.items():
    teams_data = get_teams(comp_id)
    if teams_data == "TOO_MANY_REQUESTS":
        api_blocked = True
        continue
    if not teams_data:
        continue

    teams_stats = {}
    for t in teams_data:
        teams_stats[t["name"]] = {
            "goalsFor": t.get("goalsFor", np.random.uniform(10,30)),
            "goalsAgainst": t.get("goalsAgainst", np.random.uniform(5,25)),
            "matchesPlayed": t.get("playedGames", 10)
        }

    matches = get_matches(comp_id)
    if matches == "TOO_MANY_REQUESTS":
        api_blocked = True
        continue

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

# -----------------------------
# Affichage
# -----------------------------
if api_blocked:
    st.error("⚠️ L'API a bloqué certaines requêtes (Erreur 429). Réessayez plus tard ou réduisez le nombre de championnats.")

df_matches = pd.DataFrame(all_matches)
if df_matches.empty and not api_blocked:
    st.info(f"Aucun match dans les prochaines {TIME_WINDOW_HOURS} heures avec un écart ≥ {DIFF_THRESHOLD}%.")
elif not df_matches.empty:
    st.dataframe(df_matches)
