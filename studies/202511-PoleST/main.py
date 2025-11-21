# -*- coding: utf-8 -*-
"""
Created on Fri Nov 21 12:03:44 2025

@author: godet-g
"""

# main_app.py

import streamlit as st

# ==============================================================================
# 0. CONFIGURATION DE LA PAGE (DOIT ÊTRE LE PREMIER APPEL STREAMLIT !)
# ==============================================================================
st.set_page_config(
    page_title="Analyse des Disciplines du Pôle S&T",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 1. PAGE D'ACCUEIL
# ==============================================================================

st.title("🔬 Tableau de Bord d'Analyse des Disciplines du Pôle S&T")

st.markdown("""
Bienvenue dans l'application unifiée d'exploration des données de publication du Pôle S&T. 
Utilisez la **barre latérale** pour naviguer entre les trois modes d'analyse :
""")

st.subheader("Modes d'Exploration :")
st.markdown("""
* **1. Comparaison Scopus :** Permet de comparer côte à côte les métriques (Scholarly Output, Citations, etc.) pour une sous-catégorie Scopus spécifique entre les trois périmètres (A, B, C).
* **2. Sunburst Scopus :** Visualisation en Sunburst de la répartition globale des publications Scopus par Discipline (`Subject Area`) et Sous-catégorie (`Subcategory`) pour un périmètre sélectionné.
* **3. Sunburst OpenAlex :** Visualisation en Sunburst de la répartition des publications OpenAlex par Domaine (`Domain`), Champ (`Field`) et Sous-champ (`Subfield`) pour un laboratoire ou l'ensemble du Pôle.
""")

st.markdown("---")
st.markdown("### 📌 Définition des Périmètres (Applicable aux analyses Scopus)")
st.markdown("""
* **Périmètre A :** Somme des 12 laboratoires.
* **Périmètre B :** Somme des chercheurs de l'annuaire Nantes U du Pôle.
* **Périmètre C :** Somme des chercheurs de l'annuaire en retirant les C/EC localisés ou employés par ECN et IMT.
""")