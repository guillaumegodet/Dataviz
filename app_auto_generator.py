# -*- coding: utf-8 -*-
"""
Created on Wed Nov 19 10:15:23 2025

@author: godet-g
"""

import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from concurrent.futures import ThreadPoolExecutor

# --- Configuration des URLs OpenAlex ---
BASE_WORKS_API = "https://https://api.openalex.org/works"
BASE_SUBFIELD_API = "https://api.openalex.org/subfields"

# --- Fonctions API et Logique ---

@st.cache_data(show_spinner=False)
def fetch_subfield_counts(institution_id, period):
    """
    Récupère les comptes de publication groupés par subfield.
    Note : L'API OpenAlex retourne par défaut les 200 premières catégories.
    """
    # Note: On interroge toujours pour 200 résultats car c'est la limite de l'API
    # On laisse Streamlit gérer la réduction des N résultats max.
    
    st.info(f"Étape 1/3 : Interrogation de l'API OpenAlex pour les travaux de l'institution ({period})...")
    
    # Construction du filtre
    filter_params = f"authorships.institutions.lineage:{institution_id},publication_year:{period}"
    
    # URL de l'API pour les travaux groupés par subfield (per_page=200 pour maximiser la récupération)
    url = f"{BASE_WORKS_API}?group_by=primary_topic.subfield.id&per_page=200&filter={filter_params}"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status() 
        data = response.json()
        
        if 'group_by' not in data or not data['group_by']:
            st.warning("Aucun résultat trouvé pour cette institution/période. Veuillez vérifier l'ID ou la période.")
            return None
        
        subfield_counts = [
            {'subfield_id': item['key'], 'count': item['count']} 
            for item in data['group_by']
        ]
        
        st.success(f"Récupération de {len(subfield_counts)} subfields (maximum possible) avec succès.")
        return subfield_counts
        
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur lors de l'appel à l'API Works OpenAlex: {e}")
        return None

def fetch_subfield_hierarchy(subfield_id):
    """
    Récupère la hiérarchie complète (Domain, Field) pour un seul Subfield ID.
    """
    short_id = subfield_id.split('/')[-1]
    url = f"{BASE_SUBFIELD_API}/{short_id}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        details = response.json()
        
        domain = details.get('domain', {})
        field = details.get('field', {})
        
        return {
            'subfield_id': subfield_id,
            'Subfield_Name': details.get('display_name', 'N/A'),
            'Field_Name': field.get('display_name', 'N/A'),
            'Domain_Name': domain.get('display_name', 'N/A'),
        }
    except requests.exceptions.RequestException:
        return {'subfield_id': subfield_id, 'Subfield_Name': 'N/A', 'Field_Name': 'N/A', 'Domain_Name': 'N/A'}


def get_full_data_and_generate_chart(institution_id, period, max_subfields):
    """
    Orchestre la récupération des données, la fusion, la réduction et la génération du graphique.
    """
    # 1. Récupération des comptes
    subfield_counts = fetch_subfield_counts(institution_id, period)
    if not subfield_counts:
        return

    df_counts = pd.DataFrame(subfield_counts)
    unique_subfield_ids = df_counts['subfield_id'].unique()
    
    # 2. Récupération de la Hiérarchie (en parallèle)
    st.info(f"Étape 2/3 : Récupération des détails hiérarchiques pour {len(unique_subfield_ids)} subfields...")

    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_subfield_hierarchy, subfield_id) for subfield_id in unique_subfield_ids]
        
        for future in futures:
            result = future.result()
            if result and result['Domain_Name'] != 'N/A':
                 results.append(result)

    if not results:
        st.error("Impossible de récupérer les détails hiérarchiques valides pour les subfields.")
        return

    # 3. Fusion, Préparation et Réduction des données
    st.info("Étape 3/3 : Agrégation, réduction et génération du graphique...")
    df_hierarchy = pd.DataFrame(results)
    
    df_final = pd.merge(df_counts, df_hierarchy, on='subfield_id')
    
    df_final = df_final[df_final['Domain_Name'] != 'N/A']
    
    if df_final.empty:
        st.warning("Le jeu de données final est vide après le nettoyage.")
        return
        
    # --- APPLICATION DU CURSEUR (NOUVEAUTÉ) ---
    df_final = df_final.sort_values(by='count', ascending=False)
    # Réduit le DataFrame aux N subfields les plus fréquents
    df_chart = df_final.head(max_subfields)
    
    st.success(f"Affichage des {len(df_chart)} subfields les plus fréquents (sur {len(df_final)} disponibles).")

    # 4. Génération du Sunburst Chart
    
    fig = px.sunburst(
        df_chart, # Utilisation du DataFrame réduit
        path=['Domain_Name', 'Field_Name', 'Subfield_Name'], 
        values='count',
        color='Domain_Name', 
        title=f"Cartographie de l'Institution ({institution_id}) : Période {period} (Top {max_subfields} Subfields)",
        height=750 
    )

    fig.update_layout(
        margin=dict(t=50, l=0, r=0, b=0),
        title_font_size=24
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.success("Génération du graphique terminée !")
    
    # Affichage des données brutes
    st.subheader(f"Données agrégées (Top {max_subfields})")
    st.dataframe(df_chart[['Domain_Name', 'Field_Name', 'Subfield_Name', 'count']])


# --- Interface Streamlit ---

st.set_page_config(
    page_title="Sunburst Chart - domaines OpenAlex",
    layout="wide"
)

st.title("Générateur de Diagramme Solaire (Sunburst Chart) sur les domaines OpenAlex")
st.markdown("Entrez l'identifiant OpenAlex d'une ou plusieurs institutions (Labo, Université) et une période pour visualiser la répartition de ses publications par **Domain**, **Field** et **Subfield**.")

# Inputs utilisateur
col1, col2 = st.columns(2)

with col1:
    institution_id = st.text_input(
        "Identifiant OpenAlex de l'Institution (i...) - séparez plusieurs identifiants par "|" (i4210138474|i4210137520) :",
        value="i4210117005", 
        help="Exemple : i4210138474 (CEISAM) ou i4210138474|i4210137520 pour interroger CEISAM ou GeM. Utilisez le format 'iXXXXXXXXXX' pour une institution."
    )

with col2:
    time_period = st.text_input(
        "Année ou Période (YYYY ou YYYY-YYYY) :",
        value="2020-2023",
        help="Exemples : 2022, 2020-2023."
    )

# 2. Curseur pour limiter le nombre de Subfields
max_subfields = st.slider(
    'Nombre maximum de Subfields à afficher (pour la lisibilité) :',
    min_value=10,
    max_value=200, # Max imposé par la requête API
    value=50,
    step=10,
    help="Utilisez un nombre plus petit pour un graphique plus lisible et concentré sur les sujets dominants."
)

# 3. Bouton de déclenchement
if st.button('Générer la Cartographie', type="primary"):
    if not institution_id.strip() or not time_period.strip():
        st.error("Veuillez saisir l'identifiant de l'institution et la période.")
    elif not institution_id.startswith('i'):
        st.error("L'identifiant OpenAlex d'une institution doit commencer par 'i'.")
    else:
        with st.spinner(f'Chargement des données OpenAlex et construction du graphique pour les {max_subfields} principaux subfields...'):
            get_full_data_and_generate_chart(
                institution_id.strip(), 
                time_period.strip(), 
                max_subfields # Transmission de la valeur du curseur
            )