import streamlit as st
import pandas as pd
import numpy as np
import requests
from xgboost import XGBClassifier
from datetime import date, timedelta

# ================== CONFIG ==================
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
            st.warning("Aucun match prévu dans les 7
