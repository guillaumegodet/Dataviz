import streamlit as st
import pandas as pd
import altair as alt
import io
import re

# ==============================================================================
# 0. CONFIGURATION DE LA PAGE (DOIT ÊTRE LE PREMIER APPEL STREAMLIT !)
# ==============================================================================


# Nom du fichier à lire
FILE_NAME = "studies/202511-PoleST/data/scopus-subjectareas.csv"

# ==============================================================================
# 1. FONCTION DE PRÉPARATION DES DONNÉES (Adaptée pour le nouveau CSV)
# ==============================================================================

@st.cache_data
def load_and_transform_data(file_name):
    """
    Charge le CSV pivoté (avec ';' et ',' décimal) et le transforme au format long.
    Le regex est adapté au nouveau format de colonnes.
    """
    
    # 1. Chargement initial avec les bons séparateurs (';' pour colonne, ',' pour décimal)
    try:
        df_pivot = pd.read_csv(file_name, sep=';', decimal=',')
    except FileNotFoundError:
        st.error(f"Le fichier {file_name} est introuvable. Assurez-vous qu'il est bien au même endroit que le script.")
        return pd.DataFrame(), pd.DataFrame() # Retourne des DataFrames vides en cas d'erreur
        
    # Remplacer les valeurs manquantes/non valides (comme '#N/A' ou chaînes vides) par NaN
    df_pivot = df_pivot.replace(['#N/A', '#N/A N/A', r'^\s*$'], pd.NA, regex=True)
    
    # 2. Transformation (Melt) : Passage du format large au format long
    id_vars = ['Subject Area', 'Subcategory']
    df_long = df_pivot.melt(
        id_vars=id_vars,
        var_name='Metric_Perimeter',
        value_name='Value'
    ).dropna(subset=['Value'])
    
    # Assurer que les colonnes 'Subject Area' et 'Subcategory' sont des chaînes pour éviter l'erreur .strip()
    df_long['Subject Area'] = df_long['Subject Area'].astype(str)
    df_long['Subcategory'] = df_long['Subcategory'].astype(str)
    
    # Convertir 'Value' en numérique
    df_long['Value'] = pd.to_numeric(df_long['Value'], errors='coerce')
    
    # 3. Séparation de la métrique et du périmètre
    # NOUVEAU REGEX : cherche la métrique suivie d'un ou plusieurs espaces, puis de "Périmètre X"
    new_regex = r'(.+)\s+(Périmètre [ABC])' 
    df_long[['Metric', 'Perimeter']] = df_long['Metric_Perimeter'].str.extract(new_regex)
    
    # Nettoyage et s'assurer que Metric est une chaîne (en cas de succès du regex)
    df_long.drop(columns=['Metric_Perimeter'], inplace=True)
    df_long['Metric'] = df_long['Metric'].astype(str).str.strip()
    
    return df_long, df_pivot

# Charger les données depuis le fichier
df_long, df_pivot = load_and_transform_data(FILE_NAME)

# Vérification simple pour s'assurer que les données ont été chargées
if df_long.empty:
    st.stop()

# ==============================================================================
# 2. STRUCTURE DE L'APPLICATION STREAMLIT
# ==============================================================================

st.title("📊 Visualisation des disciplines Scopus (research areas) du Pôle S&T")
st.markdown("Utilisez la barre latérale pour filtrer et comparer les métriques des différents périmètres (A, B, C).")

# --- LÉGENDE DES PÉRIMÈTRES DANS LA BARRE LATÉRALE ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 Définition des Périmètres")
st.sidebar.markdown("""
* **Périmètre A :** Somme des 12 laboratoires.
* **Périmètre B :** Somme des chercheurs de l'annuaire Nantes U du Pôle.
* **Périmètre C :** Somme des chercheurs de l'annuaire en retirant les C/EC localisés ou employés par ECN et IMT.
""")
st.sidebar.markdown("---")
# --- FIN LÉGENDE ---

# --- BARRE LATÉRALE (Filtres de navigation) ---
st.sidebar.header("⚙️ Paramètres de l'Analyse")

# 1. Sélection de la Subject Area
all_subject_areas = df_long['Subject Area'].unique()
# Assurez-vous de n'avoir qu'une seule fois la valeur 'nan' si elle existe, et que les autres sont des chaînes.
all_subject_areas = [s for s in all_subject_areas if s != 'nan']

selected_subject_area = st.sidebar.selectbox(
    "1. Choisissez la Discipline (Subject Area):",
    all_subject_areas
)

# Filtrer les Subcategories disponibles pour la Subject Area sélectionnée
subcategories_for_area = df_long[df_long['Subject Area'] == selected_subject_area]['Subcategory'].unique()
selected_subcategory = st.sidebar.selectbox(
    "2. Choisissez la Sous-Catégorie:",
    subcategories_for_area
)

# 3. Sélection de la Métrique à visualiser
all_metrics = df_long['Metric'].unique()
# Mettre "Scholarly Output" par défaut
default_metric = 'Scholarly Output'
default_metric_index = list(all_metrics).index(default_metric) if default_metric in all_metrics else 0
selected_metric = st.sidebar.selectbox(
    "3. Choisissez la Métrique à Comparer:",
    all_metrics,
    index=default_metric_index
)

# --- CONTENU PRINCIPAL ---

# L'appel à .strip() est maintenant sûr car Metric, Subject Area et Subcategory ont été converties en str
st.header(f"Comparaison de la métrique : **{selected_metric.strip()}**")
st.subheader(f"Discipline : **{selected_subject_area.strip()}** / Sous-catégorie : **{selected_subcategory.strip()}**")

# Filtrer le DataFrame pour la visualisation
df_viz = df_long[
    (df_long['Subject Area'] == selected_subject_area) &
    (df_long['Subcategory'] == selected_subcategory) &
    (df_long['Metric'] == selected_metric)
].sort_values(by='Perimeter')

# Définir l'ordre des périmètres pour le graphique
perimeter_order = ['Périmètre A', 'Périmètre B', 'Périmètre C']
df_viz['Perimeter'] = pd.Categorical(df_viz['Perimeter'], categories=perimeter_order, ordered=True)
df_viz = df_viz.sort_values('Perimeter')


if df_viz.empty:
    st.warning(f"Aucune donnée '{selected_metric.strip()}' trouvée pour cette combinaison Subject Area/Subcategory dans les périmètres A, B ou C.")
else:
    # --- VISUALISATION ALTAIR ---
    
    metric_name = selected_metric.strip()
    # Déterminer si la métrique est un indicateur de ratio pour une échelle appropriée
    is_ratio = 'per Publication' in metric_name or 'Impact' in metric_name
    
    chart = alt.Chart(df_viz).mark_bar().encode(
        x=alt.X('Perimeter', title='Périmètre', sort=perimeter_order),
        y=alt.Y('Value', title=metric_name, scale=alt.Scale(zero=not is_ratio)),
        color=alt.Color('Perimeter', title='Périmètre'),
        tooltip=['Perimeter', alt.Tooltip('Value', title=metric_name)]
    ).properties(
        title=f"Comparaison {metric_name} par Périmètre"
    ).interactive()
    
    st.altair_chart(chart, use_container_width=True)

# --- AFFICHAGE DES DONNÉES BRUTES FILTRÉES ---

st.markdown("---")
st.header(f"🔍 Données Brutes pour la métrique : **{selected_metric.strip()}**")

# 1. Filtrer le DataFrame pivoté (df_pivot) sur les lignes Subject Area/Subcategory
df_raw = df_pivot[
    (df_pivot['Subject Area'] == selected_subject_area) &
    (df_pivot['Subcategory'] == selected_subcategory)
].copy() # Utilisation de .copy() pour éviter un SettingWithCopyWarning potentiel

if not df_raw.empty:
    
    # 2. Déterminer les colonnes à conserver
    # Les colonnes de référence (Subject Area, Subcategory)
    columns_to_keep = ['Subject Area', 'Subcategory'] 
    
    # Les colonnes de métriques spécifiques (ex: "Scholarly Output Périmètre A", etc.)
    metric_cols = [col for col in df_raw.columns if selected_metric in col]
    
    columns_to_keep.extend(metric_cols)
    
    # 3. Filtrer le DataFrame pour ne garder que les colonnes pertinentes
    df_display = df_raw[columns_to_keep]
    
    # 4. Préparer pour l'affichage : Transposer (pour que les périmètres soient en colonnes)
    # On va d'abord mettre les données dans un format plus clair pour la présentation
    
    # Exclure les colonnes Subject Area et Subcategory pour la transposition
    df_temp = df_display.drop(columns=['Subject Area', 'Subcategory'], errors='ignore').T
    
    # Nommer les colonnes et l'index pour la lisibilité
    df_temp.columns = [f"Valeur pour {selected_subcategory.strip()}"]
    df_temp.index.name = 'Métrique et Périmètre'
    
    # Remplacer les NaN pour l'affichage
    df_temp = df_temp.fillna('N/A')
    
    st.dataframe(df_temp, use_container_width=True)
else:
    st.info("Aucune donnée complète trouvée pour cette combinaison Subject Area/Subcategory.")