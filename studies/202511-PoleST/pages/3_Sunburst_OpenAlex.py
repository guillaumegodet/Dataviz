# -*- coding: utf-8 -*-
"""
Created on Wed Nov 19 13:55:43 2025

@author: godet-g
"""

import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor
from matplotlib.colors import to_rgb, to_hex
import numpy as np
import warnings

# Supprimer le warning concernant l'utilisation future de to_rgb/to_hex
warnings.filterwarnings("ignore", category=FutureWarning)


# --------------------------------------------------------
# CONFIGURATION : LISTE DES INSTITUTIONS AUTORISÉES
# --------------------------------------------------------
INSTITUTIONS = {
    "I4210138474|I4210137520|I4210148006|I4210100151|I4210091049|I4392021119|I4210153365|I4210146808|I4210117005|I4210109587|I4210109007|I4387154840": "Pôle S&T",
    "i4210138474": "CEISAM",
    "i4210137520": "GeM",
    "i4210148006": "GEPEA",
    "i4210100151": "IETR",
    "i4210091049": "IMN",
    "i4392021119": "IREENA",
    "i4210153365": "LMJL",
    "i4210146808": "LPG",
    "i4210117005": "LS2N",
    "i4210109587": "LTeN",
    "i4210109007": "SUBATECH",
    "i4387154840": "US2B",
}

# Assurez-vous que les clés utilisent le 'i' en minuscule pour la cohérence
INSTITUTIONS = {k.lower(): v for k, v in INSTITUTIONS.items()}

BASE_WORKS_API = "https://api.openalex.org/works"
BASE_SUBFIELD_API = "https://api.openalex.org/subfields"

# Palette Domaines (Utilisation des 4 domaines spécifiés par l'utilisateur)
DOMAIN_COLORS = {
    "Physical Sciences": "#1E88E5", 
    "Life Sciences": "#43A047",      
    "Social Sciences": "#D32F2F",  
    "Health Sciences": "#FB8C00",    
}

DEFAULT_COLOR = "#6A5ACD"

# --------------------------------------------------------
# UTILITAIRES
# --------------------------------------------------------
def lighten(hex_color, factor):
    """Éclaircit une couleur hexadécimale."""
    try:
        r, g, b = to_rgb(hex_color)
    except ValueError:
        r, g, b = to_rgb(DEFAULT_COLOR)
        
    r, g, b = [np.clip(c + (1 - c) * factor, 0, 1) for c in (r, g, b)]
    return to_hex((r, g, b))


def color_scale(domain):
    """Retourne les nuances de couleurs pour Domain, Field, et Subfield."""
    base = DOMAIN_COLORS.get(domain, DEFAULT_COLOR) 
    
    # Domain (foncé), Field (moyen), Subfield (clair)
    return base, lighten(base, 0.4), lighten(base, 0.7)

# --------------------------------------------------------
# API
# --------------------------------------------------------
@st.cache_data(show_spinner=False)
def fetch_subfield_counts(inst, period):
    """Récupère les comptes de publication groupés par subfield."""
    url = f"{BASE_WORKS_API}?group_by=primary_topic.subfield.id&per_page=200&filter=authorships.institutions.lineage:{inst},publication_year:{period}"
    try:
        r = requests.get(url, timeout=30).json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur de connexion à l'API OpenAlex : {e}")
        return None
        
    if "group_by" not in r:
        return None
    
    data = r["group_by"]
    if not data:
        return None
        
    return pd.DataFrame([{ "subfield_id": x["key"], "count": x["count"] } for x in data])


@st.cache_data(show_spinner=False)
def fetch_subfield_details(subfield_id):
    """Récupère la hiérarchie complète ET les IDs pour la construction des liens."""
    sid = subfield_id.split("/")[-1]
    
    # Dictionnaire par défaut pour éviter les N/A si l'API est injoignable ou l'ID est invalide
    default_result = {
        "subfield_id": subfield_id,
        "Subfield_Name": "Erreur API / Inconnu",
        "Field_Name": "Erreur API / Inconnu",
        "Domain_Name": "Erreur API / Inconnu",
        "Domain_ID": "N/A",
        "Field_ID": "N/A",
    }
    
    try:
        r = requests.get(f"{BASE_SUBFIELD_API}/{sid}", timeout=10).json()
        
        # S'assurer que la réponse contient les clés de niveau supérieur
        domain = r.get("domain", {})
        field = r.get("field", {})
        
        return {
            "subfield_id": r.get("id", subfield_id),
            "Subfield_Name": r.get("display_name", "N/A"),
            "Field_Name": field.get("display_name", "N/A"),
            "Domain_Name": domain.get("display_name", "N/A"),
            "Domain_ID": domain.get("id", "N/A"),
            "Field_ID": field.get("id", "N/A"),
        }
    except requests.exceptions.RequestException as e:
        # Gérer les erreurs de requête (Timeout, Connexion, etc.)
        # st.warning(f"Échec de la récupération des détails pour {subfield_id} : {e}")
        return default_result
    except Exception:
        # Gérer les autres exceptions (ex: problème de parsing JSON)
        return default_result

# --------------------------------------------------------
# SUNBURST
# --------------------------------------------------------
def build_chart(institution, period, max_subfields):

    df = fetch_subfield_counts(institution, period)
    if df is None or df.empty:
        st.error("Aucun résultat trouvé pour cette institution.")
        return

    st.info("Récupération des détails hiérarchiques et préparation des données...")
    
    with ThreadPoolExecutor(max_workers=12) as ex:
        details = list(filter(None, ex.map(fetch_subfield_details, df.subfield_id.unique()))) 

    dfh = pd.DataFrame(details)
    df_final = df.merge(dfh, on="subfield_id")
    
   
    
    df_final = df_final[df_final.Domain_Name != "N/A"].sort_values("count", ascending=False)
    
    df_chart = df_final.head(max_subfields).copy()
    

    

    # --- Préparation des couleurs et des IDs ---
   # --- Préparation des couleurs et des IDs ---
    cmap = {}
    node_info = {} 

    def generate_oa_url(node_id, level_type):
        """Génère l'URL de recherche OpenAlex avec le filtre approprié."""
        if node_id == "N/A":
            return f"https://openalex.org/works?filter=authorships.institutions.lineage:{institution},publication_year:{period}"
        
        short_id = node_id.split('/')[-1]
        filter_name = f"primary_topic.{level_type}.id"
        return f"https://openalex.org/works?page=1&filter=authorships.institutions.lineage:{institution},publication_year:{period},{filter_name}:{short_id}"

    # Utiliser un dictionnaire pour suivre les domaines et éviter les doublons
    domains = df_chart['Domain_Name'].unique().tolist()

    # Peupler la map des IDs et des couleurs en s'assurant que chaque niveau a sa bonne couleur
    # Basée UNIQUEMENT sur son Domain_Name dans le DF
    for _, r in df_chart.iterrows():
        dom = r['Domain_Name']; fld = r['Field_Name']; sub = r['Subfield_Name']
        
        # Calculer la palette spécifique à CE domaine
        c_dom, c_field, c_sub = color_scale(dom)
        
        # Peupler les infos et les couleurs
        if dom not in node_info:
            node_info[dom] = {'id': r['Domain_ID'], 'type': 'domain'}
            cmap[dom] = c_dom
        
        # Le Field doit toujours être associé à la couleur de SON domaine (Field color)
        if fld not in node_info:
             node_info[fld] = {'id': r['Field_ID'], 'type': 'field'}
             cmap[fld] = c_field
             
        # Le Subfield doit toujours être associé à la couleur de SON domaine (Subfield color)
        if sub not in node_info:
             node_info[sub] = {'id': r['subfield_id'], 'type': 'subfield'}
             cmap[sub] = c_sub

    # --- Reconstruction Sunburst AVEC hovertext SANS lien ---
    
    labels, parents, values, colors = [], [], [], [] 
    subfield_links = {} # Pour stocker les URLs des Subfields pour le tableau

    for dom in domains:
        count_dom = df_chart[df_chart.Domain_Name == dom]['count'].sum()
        
        # Domaine
        labels.append(dom); parents.append(""); values.append(count_dom); colors.append(cmap[dom])
        
        fields = df_chart[df_chart.Domain_Name == dom].Field_Name.unique()
        for fld in fields:
            count_fld = df_chart[df_chart.Field_Name == fld]['count'].sum()
            
            # Champ
            labels.append(fld); parents.append(dom); values.append(count_fld); colors.append(cmap[fld])
            
            subs = df_chart[(df_chart.Domain_Name == dom) & (df_chart.Field_Name == fld)].Subfield_Name.unique()
            for sub in subs:
                count_sub = df_chart[df_chart.Subfield_Name == sub]['count'].sum()
                info = node_info.get(sub, {'id': 'N/A', 'type': 'subfield'})
                url = generate_oa_url(info['id'], info['type'])

                # Sous-champ (pour le graphique)
                labels.append(sub); parents.append(fld); values.append(count_sub); colors.append(cmap[sub])
                
                # Stocker le lien pour le tableau
                subfield_links[sub] = url
    
    # Création de la figure Sunburst
    fig = go.Figure(go.Sunburst(
        labels=labels, 
        parents=parents, 
        values=values,
        marker=dict(colors=colors), 
        branchvalues="total",
        # FIX 1: Simplification du hovertemplate (pas de lien)
        hovertemplate=(
            '<b>%{label}</b><br>'
            '%{value} publications'
            '<extra></extra>' 
        ),
        hoverinfo="text" 
    ))
    
    fig.update_layout(margin=dict(t=40, l=0, r=0, b=0), height=750,
                      title=f"Domaines OpenAlex : {INSTITUTIONS.get(institution.lower(), institution)} ({period})")
    st.plotly_chart(fig, use_container_width=True)

    # --- FIX 2: Ajout du lien dans le DataFrame et affichage ---
    
    # Mapping des liens au DataFrame (niveau Subfield)
    df_chart['Lien OpenAlex'] = df_chart['Subfield_Name'].map(subfield_links)
    
    # Colonnes à afficher et renommer
    cols_to_display = ["Domain_Name", "Field_Name", "Subfield_Name", "count", "Lien OpenAlex"]
    df_display = df_chart[cols_to_display].rename(columns={
        'count': 'Publications', 
        'Domain_Name': 'Domaine', 
        'Field_Name': 'Champ',
        'Subfield_Name': 'Sous-champ'
    })

    st.subheader(f"Données agrégées (Top {len(df_chart)})")
    
    # Utilisation de st.data_editor avec LinkColumn pour un lien cliquable natif
    st.data_editor(
        df_display,
        column_config={
            "Lien OpenAlex": st.column_config.LinkColumn(
                "Lien OpenAlex", 
                display_text="Voir résultats", 
                width="small"
            )
        },
        hide_index=True
    )

# --------------------------------------------------------
# INTERFACE STREAMLIT
# --------------------------------------------------------

st.title("☀️ Visualisation des Domaines OpenAlex (domains/fields/subfields) du Pôle S&T")

# Sélecteur institution
inst_choice = st.selectbox("Choisissez un laboratoire (ou tout le Pôle)", list(INSTITUTIONS.keys()),
                           format_func=lambda x: f"{INSTITUTIONS[x]}")

period = st.text_input("Période (YYYY ou YYYY-YYYY)", "2023")
max_sf = st.slider("Nombre max de subfields", 10, 200, 50, 10)

if st.button("Générer le graphique"):
    inst_id = inst_choice.lower().strip()
    
    if not inst_id.startswith('i'):
        st.error("L'identifiant OpenAlex d'une institution doit commencer par 'i'.")
    else:
        with st.spinner(f'Chargement des données OpenAlex et construction du graphique pour les {max_sf} principaux subfields...'):
            build_chart(inst_id, period.strip(), max_sf)