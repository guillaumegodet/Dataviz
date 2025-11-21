# -*- coding: utf-8 -*-
"""
Created on Fri Nov 21 10:48:59 2025

@author: godet-g
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import io
import re

# ==============================================================================
# 0. CONFIGURATION DE LA PAGE
# ==============================================================================


# Nom du fichier à lire
FILE_NAME = "studies/202511-PoleST/data/scopus-subjectareas.csv"

DEFAULT_METRIC = 'Scholarly Output'
# Métriques à conserver
ALLOWED_METRICS = ['Scholarly Output', 'Citations']

# ==============================================================================
# 1. FONCTION DE PRÉPARATION DES DONNÉES
# ==============================================================================

@st.cache_data
def load_and_transform_data(file_name):
    """
    Charge le CSV, le transforme au format long, et extrait les métriques/périmètres.
    """
    
    try:
        # Chargement avec les bons séparateurs (';' pour colonne, ',' pour décimal)
        df_pivot = pd.read_csv(file_name, sep=';', decimal=',')
    except FileNotFoundError:
        st.error(f"Le fichier {file_name} est introuvable. Assurez-vous qu'il est bien au même endroit que le script.")
        return pd.DataFrame()
        
    # Remplacer les valeurs manquantes/non valides par NaN
    df_pivot = df_pivot.replace(['#N/A', r'^\s*$'], pd.NA, regex=True)
    
    # 2. Transformation (Melt) : Passage du format large au format long
    id_vars = ['Subject Area', 'Subcategory']
    df_long = df_pivot.melt(
        id_vars=id_vars,
        var_name='Metric_Perimeter',
        value_name='Value'
    ).dropna(subset=['Value'])
    
    # Assurer le typage en chaîne de caractères
    df_long['Subject Area'] = df_long['Subject Area'].astype(str)
    df_long['Subcategory'] = df_long['Subcategory'].astype(str)
    
    # Convertir 'Value' en numérique
    df_long['Value'] = pd.to_numeric(df_long['Value'], errors='coerce')
    
    # 3. Séparation de la métrique et du périmètre
    new_regex = r'(.+)\s+(Périmètre [ABC])' 
    df_long[['Metric', 'Perimeter']] = df_long['Metric_Perimeter'].str.extract(new_regex)
    
    # Nettoyage
    df_long.drop(columns=['Metric_Perimeter'], inplace=True)
    df_long['Metric'] = df_long['Metric'].astype(str).str.strip()
    
    # Filtres
    df_long = df_long[df_long['Subcategory'] != '-']
    df_long = df_long[df_long['Metric'] != 'nan']
    
    return df_long

# Charger les données depuis le fichier
df_long = load_and_transform_data(FILE_NAME)

if df_long.empty:
    st.stop()
    
# ==============================================================================
# 2. DICTIONNAIRE DE COULEURS FIXE
# ==============================================================================

@st.cache_data
def generate_color_map(df):
    """Crée et retourne un dictionnaire de couleurs pour toutes les Subject Area."""
    unique_areas = df['Subject Area'].unique()
    colors = px.colors.qualitative.T10
    color_map = {area: colors[i % len(colors)] for i, area in enumerate(unique_areas)}
    return color_map

# Générer le dictionnaire de couleurs
SUBJECT_AREA_COLOR_MAP = generate_color_map(df_long)

# ==============================================================================
# 3. FONCTION DE CRÉATION DU SUNBURST
# ==============================================================================

def create_sunburst(df, perimeter_name, metric, color_map):
    """Crée un Sunburst Chart pour un périmètre donné."""
    
    df_filtered = df[df['Perimeter'] == perimeter_name]
    df_filtered = df_filtered[df_filtered['Metric'] == metric]
    df_filtered = df_filtered[df_filtered['Value'] > 0]
    
    if df_filtered.empty:
        return None

    # Création du graphique Sunburst
    fig = px.sunburst(
        df_filtered,
        path=['Subject Area', 'Subcategory'],
        values='Value',
        color='Subject Area', 
        color_discrete_map=color_map, # Assure la cohérence des couleurs
        title=f"Répartition par Discipline pour {perimeter_name} ({metric})",
        height=700 # Augmenter la hauteur pour une meilleure lisibilité
    )
    
    fig.update_traces(hovertemplate='%{label}<br>Valeur: %{value:.1f}<br>Pourcentage: %{percentParent:.1%}<extra></extra>')
    
    return fig

# ==============================================================================
# 4. STRUCTURE DE L'APPLICATION STREAMLIT
# ==============================================================================

st.title("☀️ Visualisation des disciplines Scopus (research areas) du Pôle S&T")

# ----------------- BARRE LATÉRALE (Filtres et Légende) -----------------
st.sidebar.header("⚙️ Paramètres de l'Analyse")

# 1. Sélection du Périmètre (Nouveau)
perimeters_list = ['Périmètre A', 'Périmètre B', 'Périmètre C']
selected_perimeter = st.sidebar.selectbox(
    "1. Choisissez le Périmètre à Afficher:",
    perimeters_list
)

# 2. Sélection de la Métrique (Limitée)
all_metrics = [m for m in df_long['Metric'].unique() if m in ALLOWED_METRICS]

default_metric_index = list(all_metrics).index(DEFAULT_METRIC) if DEFAULT_METRIC in all_metrics else 0
selected_metric = st.sidebar.selectbox(
    "2. Choisissez la Métrique à Afficher:",
    all_metrics,
    index=default_metric_index
)

# Légende des périmètres
st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 Définition des Périmètres")
st.sidebar.markdown("""
* **Périmètre A :** Somme des 12 laboratoires.
* **Périmètre B :** Somme des chercheurs de l'annuaire Nantes U du Pôle.
* **Périmètre C :** Somme des chercheurs de l'annuaire en retirant les C/EC localisés ou employés par ECN et IMT.
""")
st.sidebar.markdown("---")


# ----------------- CONTENU PRINCIPAL : Sunburst Unique -----------------

st.markdown(f"**Périmètre sélectionné :** **{selected_perimeter}**")
st.markdown(f"**Métrique sélectionnée :** **{selected_metric}**")

# Création et affichage du Sunburst Chart unique
fig = create_sunburst(df_long, selected_perimeter, selected_metric, SUBJECT_AREA_COLOR_MAP)

if fig is not None:
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info(f"Visualisation non disponible pour **{selected_perimeter}** avec la métrique **{selected_metric}**.")

# ----------------- CONCLUSION -----------------

st.markdown("---")
st.markdown(f"Ce graphique Sunburst montre la répartition de la métrique **{selected_metric}** par discipline pour le **{selected_perimeter}**. L'anneau central correspond à la **Subject Area**, et l'anneau externe aux **Subcategory**.")