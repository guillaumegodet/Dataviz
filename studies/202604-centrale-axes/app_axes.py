import streamlit as st
import pandas as pd
import plotly.express as px
import os
import requests
import re
import unicodedata
from pathlib import Path

# --- PERMANENT RESEARCHERS LIST ---
# Format: (LASTNAME, FIRSTNAME) — last name may be compound (e.g., "DA CUNHA")
PERMANENT_RESEARCHERS = [
    ("AGUADO LOPEZ", "Jose vicente"), ("ALAM", "Syed yasir"), ("ALAMICHEL", "Claire"),
    ("AUBRUN-SANCHES", "Sandrine"), ("AUGEREAU", "Olivier"), ("BABARIT", "Aurelien"),
    ("BERTHOME", "Vincent"), ("BINETRUY", "Christophe"), ("BONNEFOY", "Felicien"),
    ("BORZACCHIELLO", ""), ("BOURDIER", "Sylvain"), ("BOURGUIGNON", "Sebastien"),
    ("BOUSCASSE", "Benjamin"), ("BRECHETEAU", "Claire"), ("BRIDAY", "Mikael"),
    ("BURTIN", "Christian"), ("CALMET-GUIDONI", "Isabelle"), ("CANARD", "Maxime"),
    ("CAPDEVILLE", "Guy"), ("CARTRAUD", "Patrice"), ("CHALET", "David"),
    ("CHENOUARD", "Raphael"), ("CHERUBINI", "Andrea"), ("CHESSE", "Pascal"),
    ("CHRIETTE", "Abdelhamid"), ("COMAS-CARDONA", "Sebastien"), ("CONAN", "Boris"),
    ("CORET", "Michel"), ("COSSON", "Pascal"), ("DA CUNHA", "Catherine"),
    ("DELACROIX", "Sylvain"), ("DENG", "Ganbo"), ("DIGONNET", "Hugues"),
    ("DUBOUIL", "Remy"), ("DUCOIN", "Antoine"), ("DUCROZET", "Guillaume"),
    ("ESLAMI", "Yasamin"), ("FOUCHER", "Francoise"), ("FREMONT", "Vincent"),
    ("FRIBOURG", "Rebecca"), ("GARCIA", "Gaetan"), ("GENTAZ", "Lionel"),
    ("GHANES", "Malek"), ("GORNET", "Laurent"), ("GOUMY", "Guillaume"),
    ("GRONDIN", "Frederic"), ("GUZIOLOWSKI", "Carito"), ("HAMIDA", "Mohamed Assaad"),
    ("HAMON", "Arnaud"), ("HERY", "Elwan"), ("HETET", "Jean-Francois"),
    ("HILAIRET", "Mickael"), ("HILLOULIN", "Benoit"), ("HLADIK", "Pierre-Emmanuel"),
    ("HUNEAU", "Bertrand"), ("IBRAHIM", "Elkhatib"), ("KERMORGANT", "Olivier"),
    ("KOTRONIS", "Panagiotis"), ("LAROCHE", "Florent"), ("LE", "Benoit"),
    ("LE BRIZAUT", "Jean-sebastien"), ("LE CARPENTIER", "Eric"), ("LE NEEL", "Tugdual Amaury"),
    ("LE TOUZE", "David"), ("LEBRET", "Guy"), ("LEGOFF", "Olivier"),
    ("LEGRAIN", "Gregory"), ("LEGRAND", "Mathias"), ("LEROY", "Vincent"),
    ("LEROYER", "Alban"), ("LESAGE", "Matisse"), ("LESTANDI", "Lucas"),
    ("LI", "Zhe"), ("LIME", "Didier"), ("LIMOU", "Sophie"),
    ("LOUKILI", "Ahmed"), ("MAGNIN", "Morgan"), ("MAHE", "Vincent"),
    ("MAIBOOM", "Alain"), ("MARCKMANN", "Gilles"), ("MARINESCU", "Bogdan"),
    ("MARTIN", "Jean-yves"), ("MARTY", "Pierre"), ("MATEUS LAMUS", "Diana"),
    ("MERRIEN", "Arnaud"), ("MICHEL", "Bertrand"), ("MICHEL", "Julien"),
    ("MOUSSAOUI", "Said"), ("MURA", "Ernesto"), ("NORMAND", "Jean-Marie"),
    ("NOUY", "Anthony"), ("OGER", "Guillaume"), ("OHANA", "Jeremy"),
    ("OMMI", "Siddhartha Harsha"), ("OTHMAN", "Ramzi"), ("PARROT", "Remi"),
    ("PERRET", "Laurent"), ("PERROT", "Nicolas"), ("PETIOT", "Jean-francois"),
    ("PLESTAN", "Franck"), ("POIRSON", "Emilie"), ("RACINEUX", "Guillaume"),
    ("RAUCH", "Matthieu"), ("RIBATET", "Mathieu"), ("RIZKALLAH", "Mira"),
    ("ROCHA DA SILVA", "Luisa"), ("ROUSSET", "Jean-marc"), ("ROUX", "Olivier Henri"),
    ("ROZIERE", "Emmanuel"), ("ROZYCKI", "Patrick"), ("SAAD", "Mazen"),
    ("SALAMEH", "Georges"), ("SANDOVAL AREVALO", "JuanSebastian"), ("SCIARRA", "Giulio"),
    ("SERANDOUR", "Aurelien"), ("SERVIERES", "Myriam"), ("SIMON", "Loick"),
    ("STAINIER", "Laurent"), ("STAQUET", "Gaetan"), ("SYERKO", "Olena"),
    ("TARALOVA", "Ina"), ("THOMAS", "Vinu"), ("TOURRE", "Vincent"),
    ("TOUZE", "Stephane"), ("VERRON", "Erwan"), ("WACKERS", "Jeroen"),
    ("WEBER", "Matthieu"), ("METILLON", "Marceau"),
]

_SPECIAL_CHARS = str.maketrans({
    'ł': 'l', 'ø': 'o', 'ð': 'd', 'þ': 't', 'æ': 'ae', 'œ': 'oe',
    'ß': 'ss', 'ĸ': 'k', 'ŋ': 'n', 'ı': 'i',
})

def _norm(text):
    """Normalize text: lowercase, transliterate special Latin chars, remove accents."""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = text.translate(_SPECIAL_CHARS)
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = re.sub(r'[^a-z]', '', text)
    return text

def _build_researcher_lookup():
    """Build {norm_last_word: [(norm_full_last, norm_first_initial, orig_last, orig_first)]}."""
    lookup = {}
    for last, first in PERMANENT_RESEARCHERS:
        norm_full_last = _norm(last)
        norm_first_init = _norm(first[0]) if first else ""
        for word in last.split():
            key = _norm(word)
            if len(key) >= 3:
                lookup.setdefault(key, []).append((norm_full_last, norm_first_init, last, first))
    return lookup

_RESEARCHER_LOOKUP = _build_researcher_lookup()

def _match_researcher(author_name):
    """Return (orig_last, orig_first) from PERMANENT_RESEARCHERS if matched, else None."""
    if not isinstance(author_name, str) or not author_name.strip():
        return None
    words = author_name.strip().split()
    if not words:
        return None
    norm_first_init = _norm(words[0][0]) if words[0] else ""
    for word in words:
        key = _norm(word)
        if len(key) < 3:
            continue
        if key in _RESEARCHER_LOOKUP:
            for norm_full_last, r_first_init, orig_last, orig_first in _RESEARCHER_LOOKUP[key]:
                if not r_first_init or norm_first_init == r_first_init:
                    return (orig_last, orig_first)
    return None

def get_canonical_name(author_name):
    """Return a display name like 'Jose Vicente Aguado Lopez' from the official list, or None."""
    match = _match_researcher(author_name)
    if match is None:
        return None
    orig_last, orig_first = match
    first_str = orig_first.title() if orig_first else ""
    last_str = orig_last.title()
    return f"{first_str} {last_str}".strip() if first_str else last_str

def is_permanent_researcher(author_name):
    return _match_researcher(author_name) is not None

def has_permanent_researcher(authors_str):
    """Return True if any author in a pipe-separated string is a permanent researcher."""
    if not isinstance(authors_str, str):
        return False
    return any(is_permanent_researcher(a.strip()) for a in authors_str.split('|'))

# Define a distinct and high-contrast color palette for the 4 strategic axes
AXIS_COLOR_MAP = {
    "Production et gestion des énergies renouvelables": "#FFD700", # Gold / Yellow
    "Mobilités décarbonnées": "#1E90FF",                         # Dodger Blue
    "Matériaux, procédés et process industriels durables": "#32CD32", # Lime Green
    "Ingénierie pour la santé": "#FF4500",                       # Orange Red
    "Autre / Non classé": "#A9A9A9"                              # Dark Gray
}

# --- GRIST CONFIGURATION ---
GRIST_DOC_ID = "5aREUrB1kuFAcVY4GTUDfA"
GRIST_TABLE_NAME = "Publications_centrale_axes_strategiques2"
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
    file_path = Path(__file__).parent / "centrale_axes_data.parquet"
    if not os.path.exists(file_path):
        st.error(f"Fichier de données {file_path} non trouvé. Exécutez d'abord `process_axes.py`.")
        return pd.DataFrame()
    df = pd.read_parquet(file_path)
    
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

    filter_permanent = st.sidebar.checkbox("👩‍🔬 Chercheurs permanents uniquement", value=True)
    show_only_corrected = st.sidebar.checkbox("👁️ Voir seulement les corrections", value=False)

    # Filter by Author — show canonical names when filter_permanent is on
    if filter_permanent:
        canonical_authors = set()
        for a_str in df_raw['authors'].dropna().unique():
            for a in a_str.split('|'):
                cn = get_canonical_name(a.strip())
                if cn:
                    canonical_authors.add(cn)
        author_options = sorted(canonical_authors)
    else:
        all_authors = set()
        for a_str in df_raw['authors'].dropna().unique():
            for a in a_str.split('|'):
                a = a.strip()
                if a:
                    all_authors.add(a)
        author_options = sorted(all_authors)
    selected_author = st.sidebar.selectbox("Chercheur :", ["Tous"] + author_options)

    # Applying filters
    df = df_raw.copy()
    if filter_permanent:
        df = df[df['authors'].apply(has_permanent_researcher)]
    df = df[(df['year'] >= selected_years[0]) & (df['year'] <= selected_years[1])]
    
    if show_only_corrected and 'is_corrected' in df.columns:
        df = df[df['is_corrected'] == True]
    
    if selected_lab != "Tous":
        df = df[df['labs'].str.contains(selected_lab, na=False, regex=False)]
    
    if selected_axis != "Tous":
        df = df[df['chosen_axis'] == selected_axis]
        
    if selected_author != "Tous":
        if filter_permanent:
            df = df[df['authors'].apply(lambda s: any(
                get_canonical_name(a.strip()) == selected_author
                for a in (s.split('|') if isinstance(s, str) else [])
            ))]
        else:
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
    
    c3, c4, c5 = st.columns(3)

    with c3:
        st.subheader("Dominance par Labo")
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
        author_df = df.copy()
        author_df = author_df.assign(author=author_df['authors'].str.split('|')).explode('author')
        author_df = author_df[author_df['author'].str.strip() != ""]

        if not author_df.empty:
            top_authors_list = author_df['author'].value_counts().head(15).index.tolist()
            author_axis_stats = author_df[author_df['author'].isin(top_authors_list)].groupby(['author', 'chosen_axis']).size().reset_index(name='Count')
            fig_auth = px.bar(author_axis_stats, x='Count', y='author', color='chosen_axis',
                             orientation='h', barmode='stack',
                             color_discrete_map=AXIS_COLOR_MAP)
            st.plotly_chart(fig_auth, width='stretch')
        else:
            st.write("Aucune donnée chercheur disponible.")

    with c5:
        st.subheader("Top Permanents Centrale Nantes")
        perm_df = df.copy()
        perm_df = perm_df.assign(author=perm_df['authors'].str.split('|')).explode('author')
        perm_df['author'] = perm_df['author'].str.strip()
        perm_df['canonical'] = perm_df['author'].apply(get_canonical_name)
        perm_df = perm_df[perm_df['canonical'].notna()]

        if not perm_df.empty:
            top_perm_list = perm_df['canonical'].value_counts().head(15).index.tolist()
            perm_axis_stats = perm_df[perm_df['canonical'].isin(top_perm_list)].groupby(['canonical', 'chosen_axis']).size().reset_index(name='Count')
            fig_perm = px.bar(perm_axis_stats, x='Count', y='canonical', color='chosen_axis',
                             orientation='h', barmode='stack',
                             color_discrete_map=AXIS_COLOR_MAP)
            fig_perm.update_layout(yaxis_title="")
            st.plotly_chart(fig_perm, width='stretch')
        else:
            st.write("Aucune donnée chercheur permanent disponible.")
            
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
                links = [f"[OpenAlex](https://openalex.org/{row['work_id']})"]
                if row.get('doi') and pd.notna(row['doi']):
                    links.append(f"[DOI]({row['doi']})")
                st.markdown("🔗 " + " · ".join(links))
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
