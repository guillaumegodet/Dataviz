import streamlit as st
import pandas as pd
import plotly.express as px
import os
import requests
import re
import unicodedata

# Define a distinct and high-contrast color palette for the 4 strategic axes
AXIS_COLOR_MAP = {
    "Production et gestion des énergies renouvelables": "#FFD700", # Gold / Yellow
    "Mobilités décarbonnées": "#1E90FF",                         # Dodger Blue
    "Matériaux, procédés et process industriels durables": "#32CD32", # Lime Green
    "Ingénierie pour la santé": "#FF4500",                       # Orange Red
    "Autre / Non classé": "#A9A9A9"                              # Dark Gray
}

# --- PATH CONFIGURATION ---
# Use absolute path relative to this script for reliable loading on Streamlit Cloud
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE_PATH = os.path.join(SCRIPT_DIR, "centrale_axes_data.parquet")

# --- GRIST CONFIGURATION ---
GRIST_DOC_ID = "5aREUrB1kuFAcVY4GTUDfA"
GRIST_TABLE_NAME = "Publications_centrale_axes_strategiques"
GRIST_BASE_URL = f"https://grist.numerique.gouv.fr/api/docs/{GRIST_DOC_ID}/tables/{GRIST_TABLE_NAME}/records"
# Try to get API key from Streamlit secrets (local or cloud)
try:
    GRIST_API_KEY = st.secrets.get("GRIST_API_KEY") 
except Exception:
    GRIST_API_KEY = None

@st.cache_data(ttl=300) # Cache for 5 minutes
def load_grist_data():
    if not GRIST_API_KEY:
        return pd.DataFrame(), "Clé API absente"
    
    headers = {"Authorization": f"Bearer {GRIST_API_KEY}"}
    try:
        response = requests.get(GRIST_BASE_URL, headers=headers)
        if response.status_code == 200:
            records = response.json().get('records', [])
            if not records:
                return pd.DataFrame(), "Table Grist vide"
            # Extract fields from Grist records
            data = []
            for r in records:
                row = r['fields']
                row['grist_id'] = r['id']
                data.append(row)
            return pd.DataFrame(data), "OK"
        else:
            return pd.DataFrame(), f"Erreur {response.status_code}: {response.text}"
    except Exception as e:
        return pd.DataFrame(), f"Exception: {str(e)}"

def update_grist_axis(grist_id, new_axis):
    """Update the axis in Grist for a specific record."""
    if not GRIST_API_KEY:
        return False, "Clé API Grist manquante."
    if not grist_id or (isinstance(grist_id, float) and pd.isna(grist_id)):
        return False, "ID Grist manquant (la publication n'a pas été trouvée dans Grist)."
    
    headers = {"Authorization": f"Bearer {GRIST_API_KEY}"}
    # Grist API usually requires the field ID. 
    # Important: if you have 'Axe Retenu' in your CSV, it might be 'Axe_Retenu' OR 'Axe_Retenu_2'
    # We try 'Axe_Retenu' as it's the most common.
    payload = {
        "records": [
            {
                "id": grist_id,
                "fields": {"Axe_Retenu": new_axis}
            }
        ]
    }
    try:
        response = requests.patch(GRIST_BASE_URL, headers=headers, json=payload)
        if response.status_code == 200:
            return True, "Success"
        else:
            return False, f"Erreur API Grist ({response.status_code}): {response.text}"
    except Exception as e:
        return False, f"Exception lors de la mise à jour : {str(e)}"

st.set_page_config(page_title="Dashboard Axes Stratégiques Centrale Nantes", layout="wide")

def normalize_title(text):
    """Normalize title for matching: lowercase, no accents, no special chars."""
    if not isinstance(text, str):
        return ""
    # Lowercase
    text = text.lower()
    # Remove accents
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    # Keep only alphanumeric chars
    text = re.sub(r'[^a-zA-Z0-9]', '', text)
    return text

@st.cache_data
def load_data():
    if not os.path.exists(DATA_FILE_PATH):
        st.error(f"Fichier de données {DATA_FILE_PATH} non trouvé. Exécutez d'abord `process_axes.py`.")
        return pd.DataFrame()
    df = pd.read_parquet(DATA_FILE_PATH)
    
    # Store the initial IA prediction
    df['prediction_ia'] = df['chosen_axis']
    df['is_corrected'] = False
    
    # Merge with Grist corrections if available
    grist_df, status = load_grist_data()
    if not grist_df.empty:
        # Find column names in Grist (case-insensitive search for IDs)
        # Grist API returns Column IDs, which might be 'work_id', 'workid', 'Work_id', etc.
        cols = grist_df.columns.tolist()
        
        work_id_col = next((c for c in cols if c.lower() == 'work_id'), None)
        title_col = next((c for c in cols if c.lower() == 'titre'), None)
        axis_col = next((c for c in cols if c.lower() in ['axe_retenu', 'axe retenu', 'axe_retenu_2']), None)
        
        if axis_col:
            if work_id_col:
                # Primary match: use work_id
                cols_to_match = [work_id_col, axis_col, 'grist_id']
                grist_clean = grist_df[cols_to_match].dropna(subset=[work_id_col])
                # Ensure work_id values are strings for matching
                grist_clean[work_id_col] = grist_clean[work_id_col].astype(str)
                df['work_id'] = df['work_id'].astype(str)
                
                grist_clean = grist_clean.rename(columns={axis_col: 'grist_val', work_id_col: 'work_id_grist'})
                grist_clean = grist_clean.drop_duplicates(subset=['work_id_grist'], keep='last')
                
                df = df.merge(grist_clean, left_on='work_id', right_on='work_id_grist', how='left')
            elif title_col:
                # Fallback match: use normalized titles
                df['title_norm'] = df['title'].apply(normalize_title)
                grist_df['title_norm_grist'] = grist_df[title_col].apply(normalize_title)
                
                cols_to_match = ['title_norm_grist', axis_col, 'grist_id']
                grist_clean = grist_df[cols_to_match].dropna(subset=['title_norm_grist'])
                grist_clean = grist_clean.rename(columns={axis_col: 'grist_val'})
                grist_clean = grist_clean.drop_duplicates(subset=['title_norm_grist'], keep='last')
                
                df = df.merge(grist_clean, left_on='title_norm', right_on='title_norm_grist', how='left')
                df = df.drop(columns=['title_norm', 'title_norm_grist'])
            
            # A record is "corrected" ONLY if the Grist value exists AND is different from the IA prediction
            if 'grist_val' in df.columns:
                df['is_corrected'] = df.apply(
                    lambda row: pd.notna(row['grist_val']) and row['grist_val'] != row['prediction_ia'], 
                    axis=1
                )
                
                # Update the axis to show: Grist value if it exists, else IA prediction
                df['chosen_axis'] = df['grist_val'].fillna(df['prediction_ia'])
    elif status != "OK":
        st.sidebar.error(f"⚠️ Grist Load Error: {status}")
        st.sidebar.info("Vérifiez GRIST_DOC_ID et GRIST_TABLE_NAME.")
        
    # Merge categories if needed (ensure uniform naming)
    df['chosen_axis'] = df['chosen_axis'].replace("Non classé", "Autre / Non classé")
        
    return df

df_raw = load_data()

if df_raw.empty:
    st.info("Aucune donnée à afficher.")
else:
    st.sidebar.title("🔍 Filtres")
    
    # Range of years
    years = sorted(df_raw['year'].unique())
    selected_years = st.sidebar.select_slider("Années :", options=years, value=(min(years), max(years)))
    
    # Filter by Lab
    # Labs are pipe-separated in 'labs' column
    all_labs = set()
    for l_str in df_raw['labs'].dropna().unique():
        for l in l_str.split('|'):
            if l != "Inconnu":
                all_labs.add(l)
    
    selected_lab = st.sidebar.selectbox("Laboratoire :", ["Tous"] + sorted(list(all_labs)))
    
    # Filter by Strategic Axis
    all_axes = sorted(df_raw['chosen_axis'].unique())
    selected_axis = st.sidebar.selectbox("Axe Stratégique :", ["Tous"] + all_axes)
    
    # Filter by Author (only those appearing in 'authors' column)
    all_authors = set()
    for a_str in df_raw['authors'].dropna().unique():
        for a in a_str.split('|'):
            if a:
                all_authors.add(a)
    selected_author = st.sidebar.selectbox("Chercheur :", ["Tous"] + sorted(list(all_authors)))
    
    show_only_corrected = st.sidebar.checkbox("👁️ Voir seulement les corrections", value=False)

    # Applying filters
    df = df_raw.copy()
    df = df[(df['year'] >= selected_years[0]) & (df['year'] <= selected_years[1])]
    
    if show_only_corrected and 'is_corrected' in df.columns:
        df = df[df['is_corrected'] == True]
    
    if selected_lab != "Tous":
        df = df[df['labs'].str.contains(selected_lab, na=False, regex=False)]
    
    if selected_axis != "Tous":
        df = df[df['chosen_axis'] == selected_axis]
        
    if selected_author != "Tous":
        df = df[df['authors'].str.contains(selected_author, na=False, regex=False)]
    
    # --- Main Content ---
    st.title("📊 Dashboard des Axes Stratégiques Centrale Nantes")
    
    if not GRIST_API_KEY:
        st.warning("⚠️ Clé API Grist non configurée. Les corrections ne seront pas chargées.")
    elif 'is_corrected' in df.columns:
        st.info(f"✅ {df['is_corrected'].sum()} corrections chargées depuis Grist.")

    st.write(f"Analyse de {len(df)} publications identifiées sur la période sélectionnée.")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Répartition par Axes")
        axis_counts = df['chosen_axis'].value_counts().reset_index()
        axis_counts.columns = ['Axe', 'Nombre']
        fig_axis = px.pie(axis_counts, values='Nombre', names='Axe', hole=0.4, 
                         color='Axe', color_discrete_map=AXIS_COLOR_MAP)
        st.plotly_chart(fig_axis, width='stretch')
        
    with c2:
        st.subheader("Évolution Temporelle")
        evo_df = df.groupby(['year', 'chosen_axis']).size().reset_index(name='Publications')
        fig_evo = px.area(evo_df, x='year', y='Publications', color='chosen_axis', 
                         color_discrete_map=AXIS_COLOR_MAP)
        fig_evo.update_layout(xaxis_type='category')
        st.plotly_chart(fig_evo, width='stretch')
    
    st.markdown("---")
    
    c3, c4 = st.columns(2)
    
    with c3:
        st.subheader("Dominance par Labo")
        # Explode labs to count per lab/axis
        lab_df = df.copy()
        lab_df = lab_df.assign(lab=lab_df['labs'].str.split('|')).explode('lab')
        lab_df = lab_df[lab_df['lab'] != "Inconnu"]
        
        if not lab_df.empty:
            lab_axis_stats = lab_df.groupby(['lab', 'chosen_axis']).size().reset_index(name='Count')
            fig_lab = px.bar(lab_axis_stats, x='Count', y='lab', color='chosen_axis', 
                            orientation='h', barmode='stack',
                            color_discrete_map=AXIS_COLOR_MAP)
            st.plotly_chart(fig_lab, width='stretch')
        else:
            st.write("Aucune donnée labo disponible.")
            
    with c4:
        st.subheader("Top Chercheurs Nantais")
        # Explode authors to count per author/axis
        author_df = df.copy()
        author_df = author_df.assign(author=author_df['authors'].str.split('|')).explode('author')
        author_df = author_df[author_df['author'] != ""]
        
        if not author_df.empty:
            # We filter top 15 authors to keep it readable
            top_authors_list = author_df['author'].value_counts().head(15).index.tolist()
            author_axis_stats = author_df[author_df['author'].isin(top_authors_list)].groupby(['author', 'chosen_axis']).size().reset_index(name='Count')
            
            fig_auth = px.bar(author_axis_stats, x='Count', y='author', color='chosen_axis',
                             orientation='h', barmode='stack',
                             color_discrete_map=AXIS_COLOR_MAP)
            st.plotly_chart(fig_auth, width='stretch')
        else:
            st.write("Aucune donnée chercheur disponible.")
            
    st.markdown("---")
    st.subheader("📑 Détails et Correction des Publications")
    
    search_query = st.text_input("🔍 Rechercher une publication par titre ou auteur :", "")
    
    if search_query:
        df = df[df['title'].str.contains(search_query, case=False, na=False) | 
                df['authors'].str.contains(search_query, case=False, na=False)]

    # Pagination
    PAGE_SIZE = 10
    total_pages = (len(df) // PAGE_SIZE) + (1 if len(df) % PAGE_SIZE > 0 else 0)
    
    if total_pages > 0:
        c_page, c_info = st.columns([1, 4])
        with c_page:
            page = st.number_input("Page:", min_value=1, max_value=total_pages, step=1)
        with c_info:
            st.write(f"Affichage de {len(df)} publications (Page {page}/{total_pages})")
            
        start_idx = (page - 1) * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        df_page = df.iloc[start_idx:end_idx]

        for idx, row in df_page.iterrows():
            with st.expander(f"📌 {row['title']} ({row['year']})"):
                st.write(f"**👥 Auteurs :** {row['authors']}")
                st.write(f"**📖 Revue :** {row['journal']} (ISSN: {row['issn']})")
                st.write(f"**🎯 Axe actuel :** `{row['chosen_axis']}`")
                if row.get('is_corrected'):
                    st.success("✅ Cet axe a été validé/corrigé manuellement.")
                
                st.write(f"**🧠 Motivation IA :** {row['motivation']}")
                st.write(f"**🔬 Sujets / Disciplines :** {row['topics']} | {row['subfields']}")
                st.info(f"**📝 Résumé :** {row['abstract']}")
                
                # Correction part
                st.divider()
                st.write("✏️ **Modifier l'axe stratégique :**")
                
                # Create a key that is unique but stable
                new_axis = st.selectbox(
                    "Choisir un nouvel axe :",
                    options=list(AXIS_COLOR_MAP.keys()),
                    index=list(AXIS_COLOR_MAP.keys()).index(row['chosen_axis']) if row['chosen_axis'] in AXIS_COLOR_MAP else 0,
                    key=f"select_{row['work_id']}"
                )
                
                if st.button("Mettre à jour dans Grist", key=f"btn_{row['work_id']}"):
                    success, msg = update_grist_axis(row.get('grist_id'), new_axis)
                    if success:
                        st.balloons()
                        st.success("Synchronisation avec Grist réussie ! (L'affichage sera mis à jour au prochain rafraîchissement)")
                        st.cache_data.clear() # Clear cache to force reload
                    else:
                        st.error(f"⚠️ {msg}")
                        st.info("Vérifiez que le nom de la table et de la colonne 'Axe_Retenu' sont corrects dans Grist.")

    # Export remains available
    st.divider()
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Télécharger la sélection actuelle (CSV)",
        data=csv,
        file_name='publications_centrale_filtrees.csv',
        mime='text/csv',
    )
